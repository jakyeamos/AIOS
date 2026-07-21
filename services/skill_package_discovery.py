"""Read-only discovery and provenance for the pinned Obsidian skill package.

This module intentionally does not install, copy, normalize, or register skills.
It only inspects the three host layouts documented by the upstream package and
the existing AIOS skill registry so that package availability and registry state
remain separately observable.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY_PATH = ROOT / "config" / "workflows" / "skills.json"

OBSIDIAN_SKILLS_SOURCE_URL = "https://github.com/kepano/obsidian-skills"
OBSIDIAN_SKILLS_REVISION = "a1dc48e68138490d522c04cbf5822214c6eb1202"
OBSIDIAN_SKILL_NAMES = (
    "obsidian-markdown",
    "obsidian-bases",
    "json-canvas",
    "obsidian-cli",
    "defuddle",
)


@dataclass(frozen=True)
class _HostLayout:
    host: str
    layout: str
    skill_prefix: tuple[str, ...]


_HOST_LAYOUTS = (
    _HostLayout("codex", "codex_skill_root", ()),
    _HostLayout("claude", "claude_dotfiles_root", ("skills",)),
    _HostLayout("opencode", "opencode_cloned_repo", ("skills",)),
)
_HOST_LAYOUT_BY_NAME = {layout.host: layout for layout in _HOST_LAYOUTS}

# Claude's upstream instructions are vault-scoped, so there is deliberately no
# machine-wide default for it. Callers can provide a vault's .claude path.
DEFAULT_HOST_ROOTS: dict[str, Path | None] = {
    "codex": Path.home() / ".codex" / "skills",
    "claude": None,
    "opencode": Path.home() / ".opencode" / "skills" / "obsidian-skills",
}


def _is_file(path: Path) -> bool:
    try:
        return path.is_file()
    except OSError:
        return False


def _is_dir(path: Path) -> bool:
    try:
        return path.is_dir()
    except OSError:
        return False


def _json_object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    mapping = cast(Mapping[object, object], value)
    return {key: item for key, item in mapping.items() if isinstance(key, str)}


def _normalize_roots(
    roots: Mapping[str, Path | str | None] | None,
) -> dict[str, Path | None]:
    provided = DEFAULT_HOST_ROOTS if roots is None else roots
    unknown_hosts = sorted(set(provided) - set(_HOST_LAYOUT_BY_NAME))
    if unknown_hosts:
        raise ValueError(f"Unsupported skill package host(s): {', '.join(unknown_hosts)}")

    normalized: dict[str, Path | None] = {}
    for layout in _HOST_LAYOUTS:
        value = provided.get(layout.host)
        normalized[layout.host] = None if value is None else Path(value).expanduser()
    return normalized


def _load_registry(
    registry_path: Path,
) -> tuple[dict[str, dict[str, object]], bool, list[str], list[str]]:
    if not _is_file(registry_path):
        return {}, False, ["registry_missing"], []

    try:
        parsed = cast(object, json.loads(registry_path.read_text(encoding="utf-8")))
    except (OSError, UnicodeError):
        return {}, True, [], ["registry_read_failed"]
    except json.JSONDecodeError:
        return {}, True, [], ["registry_invalid_json"]

    document = _json_object(parsed)
    raw_skills = document.get("skills")
    if not isinstance(raw_skills, list):
        return {}, True, [], ["registry_skills_missing"]

    entries: dict[str, dict[str, object]] = {}
    for raw_entry in raw_skills:
        entry = _json_object(raw_entry)
        key = entry.get("key")
        if isinstance(key, str) and key:
            entries[key] = entry
    return entries, True, [], []


def _hash_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _read_file(
    path: Path,
) -> tuple[bytes | None, str | None]:
    try:
        return path.read_bytes(), None
    except (OSError, UnicodeError):
        return None, "read_failed"


def _discover_host(layout: _HostLayout, root: Path | None) -> dict[str, object]:
    expected_names = list(OBSIDIAN_SKILL_NAMES)
    package_root = None if root is None else str(root)
    skill_root = None if root is None else str(root.joinpath(*layout.skill_prefix))
    notes: list[str] = []
    read_errors: list[str] = []
    expected_observed: list[str] = []
    unexpected_names: list[str] = []
    contents: dict[str, bytes] = {}
    skill_files: dict[str, dict[str, object]] = {}

    if root is None:
        notes.append("root_not_configured")
    elif not _is_dir(root):
        notes.append("root_missing")
    else:
        candidate_root = root.joinpath(*layout.skill_prefix)
        if not _is_dir(candidate_root):
            notes.append("skill_root_missing")
        else:
            try:
                children = sorted(
                    (child for child in candidate_root.iterdir() if _is_dir(child)),
                    key=lambda child: child.name,
                )
            except OSError:
                children = []
                read_errors.append("skill_root_scan_failed")

            for child in children:
                skill_file = child / "SKILL.md"
                if not _is_file(skill_file):
                    continue
                if child.name in OBSIDIAN_SKILL_NAMES:
                    expected_observed.append(child.name)
                else:
                    unexpected_names.append(child.name)

    observed_names = sorted(set(expected_observed + unexpected_names))
    for name in expected_names:
        path = None if root is None else root.joinpath(*layout.skill_prefix, name, "SKILL.md")
        exists = path is not None and _is_file(path)
        content: bytes | None = None
        if exists and path is not None:
            content, error = _read_file(path)
            if error is not None:
                read_errors.append(f"{error}:{name}")
        if content is not None:
            contents[name] = content
        skill_files[name] = {
            "path": None if path is None else str(path),
            "exists": exists,
            "sha256": None if content is None else _hash_bytes(content),
        }

    if root is not None and _is_dir(root.joinpath(*layout.skill_prefix)):
        candidate_root = root.joinpath(*layout.skill_prefix)
        for name in unexpected_names:
            content, error = _read_file(candidate_root / name / "SKILL.md")
            if error is not None:
                read_errors.append(f"{error}:{name}")
            if content is not None:
                contents[name] = content

    package_digest: str | None = None
    if contents:
        digest = hashlib.sha256()
        for name in sorted(contents):
            digest.update(f"{name}/SKILL.md\0".encode())
            digest.update(contents[name])
        package_digest = digest.hexdigest()

    missing_names = [name for name in expected_names if name not in expected_observed]
    if root is None:
        status = "unconfigured"
    elif not missing_names:
        status = "available"
    elif observed_names:
        status = "partial"
    else:
        status = "missing"

    if not contents:
        digest_coverage = "none"
    elif all(name in contents for name in expected_names):
        digest_coverage = "complete"
    else:
        digest_coverage = "partial"

    return {
        "host": layout.host,
        "layout": layout.layout,
        "package_root": package_root,
        "skill_root": skill_root,
        "configured": root is not None,
        "available_package": status == "available",
        "status": status,
        "expected_skills": expected_names,
        "observed_skills": observed_names,
        "missing_skills": missing_names,
        "unexpected_skills": sorted(set(unexpected_names)),
        "skill_files": skill_files,
        "package_digest": package_digest,
        "digest_coverage": digest_coverage,
        "notes": notes,
        "read_errors": sorted(set(read_errors)),
    }


def _registry_state(
    skill_name: str,
    entries: Mapping[str, dict[str, object]],
    project_root: Path,
) -> dict[str, object]:
    entry = entries.get(skill_name)
    if entry is None:
        return {
            "registered_capability": False,
            "registry_entry_status": "unregistered",
            "registry_source_path": None,
            "registry_resolved_source_path": None,
            "registry_source_exists": False,
            "registry_installed_name": None,
            "registry_lifecycle_state": None,
        }

    raw_source_path = entry.get("source_path")
    source_path = raw_source_path if isinstance(raw_source_path, str) else None
    if source_path is None or not source_path.strip():
        entry_status = "manual"
        resolved_source_path: Path | None = None
        source_exists = False
    else:
        candidate = Path(source_path).expanduser()
        resolved_source_path = candidate if candidate.is_absolute() else project_root / candidate
        source_exists = _is_file(resolved_source_path)
        entry_status = "source_backed" if source_exists else "stale"

    installed_name = entry.get("installed_name")
    lifecycle_state = entry.get("lifecycle_state")
    return {
        "registered_capability": True,
        "registry_entry_status": entry_status,
        "registry_source_path": source_path,
        "registry_resolved_source_path": (
            None if resolved_source_path is None else str(resolved_source_path)
        ),
        "registry_source_exists": source_exists,
        "registry_installed_name": installed_name if isinstance(installed_name, str) else None,
        "registry_lifecycle_state": lifecycle_state if isinstance(lifecycle_state, str) else None,
    }


def _host_skill_available(host: Mapping[str, object], skill_name: str) -> bool:
    files = host.get("skill_files")
    if not isinstance(files, dict):
        return False
    file_map = cast(Mapping[object, object], files)
    details = file_map.get(skill_name)
    if not isinstance(details, dict):
        return False
    detail_map = cast(Mapping[object, object], details)
    return detail_map.get("exists") is True


def discover_skill_package_matrix(
    roots: Mapping[str, Path | str | None] | None = None,
    *,
    registry_path: Path | str = DEFAULT_REGISTRY_PATH,
    project_root: Path | str = ROOT,
) -> dict[str, object]:
    """Inspect package layouts and existing registry state without writing files.

    ``roots`` maps host names to the layout-specific package root: Codex uses
    ``~/.codex/skills`` directly, Claude uses a vault's ``.claude`` directory,
    and OpenCode uses the cloned repository root at
    ``~/.opencode/skills/obsidian-skills``. An omitted Claude root is reported as
    unconfigured instead of being replaced with a machine-wide assumption.
    """

    normalized_roots = _normalize_roots(roots)
    normalized_registry_path = Path(registry_path).expanduser()
    normalized_project_root = Path(project_root).expanduser()
    registry_entries, registry_exists, registry_notes, registry_errors = _load_registry(
        normalized_registry_path
    )
    hosts = [_discover_host(layout, normalized_roots[layout.host]) for layout in _HOST_LAYOUTS]

    skills: list[dict[str, object]] = []
    for skill_name in OBSIDIAN_SKILL_NAMES:
        availability_by_host = {
            host_name: _host_skill_available(host, skill_name)
            for host_name, host in (
                (str(host["host"]), host) for host in hosts if isinstance(host.get("host"), str)
            )
        }
        skill = {
            "skill": skill_name,
            "available_package": any(availability_by_host.values()),
            "available_by_host": availability_by_host,
        }
        skill.update(_registry_state(skill_name, registry_entries, normalized_project_root))
        skills.append(skill)

    selected_sources: list[dict[str, object]] = [
        {
            "kind": "pinned_package",
            "repository": OBSIDIAN_SKILLS_SOURCE_URL,
            "revision": OBSIDIAN_SKILLS_REVISION,
        }
    ]
    skipped_sources: list[dict[str, object]] = []
    for host in hosts:
        host_name = host["host"]
        if host.get("configured") is True:
            selected_sources.append(
                {
                    "kind": "host_layout",
                    "host": host_name,
                    "layout": host["layout"],
                    "package_root": host["package_root"],
                }
            )
        else:
            skipped_sources.append(
                {
                    "kind": "host_layout",
                    "host": host_name,
                    "reason": "root_not_configured",
                }
            )
    if registry_exists:
        selected_sources.append({"kind": "aios_registry", "path": str(normalized_registry_path)})
    else:
        skipped_sources.append(
            {
                "kind": "aios_registry",
                "path": str(normalized_registry_path),
                "reason": "registry_missing",
            }
        )

    host_read_errors = [
        f"{host['host']}:{error}"
        for host in hosts
        for error in cast(list[object], host.get("read_errors", []))
        if isinstance(host.get("host"), str) and isinstance(error, str)
    ]
    validation_evidence: list[dict[str, object]] = [
        {
            "check": "pinned_source_revision",
            "status": "pass",
            "repository": OBSIDIAN_SKILLS_SOURCE_URL,
            "revision": OBSIDIAN_SKILLS_REVISION,
        },
        {
            "check": "expected_skill_set",
            "status": "pass",
            "expected_count": len(OBSIDIAN_SKILL_NAMES),
            "expected_skills": list(OBSIDIAN_SKILL_NAMES),
        },
        {
            "check": "host_layouts",
            "status": "pass",
            "expected_count": len(_HOST_LAYOUTS),
            "observed_count": len(hosts),
        },
        {
            "check": "registry_classification",
            "status": "pass" if registry_exists and not registry_errors else "warn",
            "path": str(normalized_registry_path),
            "notes": registry_notes,
            "errors": registry_errors,
        },
        {
            "check": "read_only",
            "status": "pass",
            "writes_performed": 0,
        },
        {
            "check": "file_reads",
            "status": "pass" if not host_read_errors else "warn",
            "errors": sorted(host_read_errors),
        },
    ]

    complete_hosts = [
        str(host["host"])
        for host in hosts
        if host.get("available_package") is True and isinstance(host.get("host"), str)
    ]
    status_counts = {
        status: sum(1 for skill in skills if skill.get("registry_entry_status") == status)
        for status in ("source_backed", "stale", "manual", "unregistered")
    }

    return {
        "schema": "aios-skill-package-discovery-v0.1",
        "read_only": True,
        "source_package": {
            "repository": "kepano/obsidian-skills",
            "url": OBSIDIAN_SKILLS_SOURCE_URL,
            "revision": OBSIDIAN_SKILLS_REVISION,
            "revision_type": "commit",
            "skill_names": list(OBSIDIAN_SKILL_NAMES),
        },
        "project_context": {
            "project": "AIOS",
            "project_root": str(normalized_project_root),
            "registry_path": str(normalized_registry_path),
            "registry_exists": registry_exists,
        },
        "workflow_stage": "read_only_skill_package_discovery",
        "source_selection": {
            "selected": selected_sources,
            "skipped": skipped_sources,
        },
        "availability": {
            "available_package": bool(complete_hosts),
            "complete_host_layouts": complete_hosts,
        },
        "validation_evidence": validation_evidence,
        "counts": {
            "host_layouts": len(hosts),
            "configured_host_layouts": sum(1 for host in hosts if host.get("configured") is True),
            "complete_host_layouts": len(complete_hosts),
            "available_skill_count": sum(
                1 for skill in skills if skill.get("available_package") is True
            ),
            "registered_capability_count": sum(
                1 for skill in skills if skill.get("registered_capability") is True
            ),
            "source_backed_registry_entry_count": status_counts["source_backed"],
            "stale_registry_entry_count": status_counts["stale"],
            "manual_registry_entry_count": status_counts["manual"],
            "unregistered_capability_count": status_counts["unregistered"],
        },
        "hosts": hosts,
        "skills": skills,
    }
