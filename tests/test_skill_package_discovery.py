from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.skill_package_discovery import (  # noqa: E402
    OBSIDIAN_SKILL_NAMES,
    OBSIDIAN_SKILLS_REVISION,
    discover_skill_package_matrix,
)


def _write_package(skill_root: Path, names: tuple[str, ...] = OBSIDIAN_SKILL_NAMES) -> None:
    for name in names:
        skill_file = skill_root / name / "SKILL.md"
        skill_file.parent.mkdir(parents=True, exist_ok=True)
        skill_file.write_text(
            f"---\nname: {name}\ndescription: synthetic fixture\n---\n\nFixture.\n",
            encoding="utf-8",
        )


def _write_registry(
    path: Path,
    *,
    project_root: Path,
    backed_source: Path,
) -> None:
    payload = {
        "version": "fixture",
        "skills": [
            {
                "key": "obsidian-markdown",
                "source_path": str(backed_source),
                "installed_name": "obsidian-markdown",
            },
            {
                "key": "obsidian-bases",
                "source_path": "skills/obsidian-bases/SKILL.md",
                "installed_name": "obsidian-bases",
            },
            {
                "key": "json-canvas",
                "installed_name": "json-canvas",
            },
        ],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    assert project_root.is_dir()


def test_matrix_preserves_pinned_provenance_and_separates_registry_states(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "aios"
    project_root.mkdir()
    backed_source = project_root / "skills" / "obsidian-markdown" / "SKILL.md"
    backed_source.parent.mkdir(parents=True)
    backed_source.write_text("source-backed fixture\n", encoding="utf-8")

    codex_root = tmp_path / "codex" / "skills"
    claude_root = tmp_path / "vault" / ".claude"
    opencode_root = tmp_path / "opencode" / "skills" / "obsidian-skills"
    _write_package(codex_root)
    _write_package(claude_root / "skills")
    _write_package(opencode_root / "skills")

    registry_path = tmp_path / "skills.json"
    _write_registry(registry_path, project_root=project_root, backed_source=backed_source)
    registry_before = registry_path.read_bytes()
    package_before = (codex_root / "obsidian-markdown" / "SKILL.md").read_bytes()

    result = discover_skill_package_matrix(
        {
            "codex": codex_root,
            "claude": claude_root,
            "opencode": opencode_root,
        },
        registry_path=registry_path,
        project_root=project_root,
    )

    assert result["schema"] == "aios-skill-package-discovery-v0.1"
    assert result["read_only"] is True
    assert result["workflow_stage"] == "read_only_skill_package_discovery"
    assert result["source_package"]["revision"] == OBSIDIAN_SKILLS_REVISION  # type: ignore[index]
    assert result["project_context"]["project"] == "AIOS"  # type: ignore[index]
    assert result["project_context"]["registry_exists"] is True  # type: ignore[index]

    availability = result["availability"]
    assert availability["available_package"] is True  # type: ignore[index]
    assert availability["complete_host_layouts"] == ["codex", "claude", "opencode"]  # type: ignore[index]

    counts = result["counts"]
    assert counts["host_layouts"] == 3  # type: ignore[index]
    assert counts["complete_host_layouts"] == 3  # type: ignore[index]
    assert counts["available_skill_count"] == 5  # type: ignore[index]
    assert counts["registered_capability_count"] == 3  # type: ignore[index]
    assert counts["source_backed_registry_entry_count"] == 1  # type: ignore[index]
    assert counts["stale_registry_entry_count"] == 1  # type: ignore[index]
    assert counts["manual_registry_entry_count"] == 1  # type: ignore[index]
    assert counts["unregistered_capability_count"] == 2  # type: ignore[index]

    hosts = {host["host"]: host for host in result["hosts"]}  # type: ignore[index]
    for host_name, package_root in {
        "codex": codex_root,
        "claude": claude_root,
        "opencode": opencode_root,
    }.items():
        host = hosts[host_name]
        assert host["available_package"] is True
        assert host["package_root"] == str(package_root)
        assert host["digest_coverage"] == "complete"
        assert len(host["package_digest"]) == 64

    skills = {skill["skill"]: skill for skill in result["skills"]}  # type: ignore[index]
    assert skills["obsidian-markdown"]["available_package"] is True
    assert skills["obsidian-markdown"]["registered_capability"] is True
    assert skills["obsidian-markdown"]["registry_entry_status"] == "source_backed"
    assert skills["obsidian-markdown"]["registry_source_exists"] is True
    assert skills["obsidian-bases"]["registered_capability"] is True
    assert skills["obsidian-bases"]["registry_entry_status"] == "stale"
    assert skills["obsidian-bases"]["registry_source_exists"] is False
    assert skills["json-canvas"]["registered_capability"] is True
    assert skills["json-canvas"]["registry_entry_status"] == "manual"
    assert skills["obsidian-cli"]["registered_capability"] is False
    assert skills["obsidian-cli"]["registry_entry_status"] == "unregistered"
    assert skills["defuddle"]["registry_entry_status"] == "unregistered"

    assert registry_path.read_bytes() == registry_before
    assert (codex_root / "obsidian-markdown" / "SKILL.md").read_bytes() == package_before


def test_matrix_reports_partial_and_unconfigured_layouts_without_writes(tmp_path: Path) -> None:
    partial_root = tmp_path / "codex" / "skills"
    _write_package(partial_root, ("obsidian-markdown",))
    unexpected = partial_root / "local-extra" / "SKILL.md"
    unexpected.parent.mkdir()
    unexpected.write_text("local fixture\n", encoding="utf-8")
    missing_registry = tmp_path / "missing-skills.json"

    result = discover_skill_package_matrix(
        {
            "codex": partial_root,
            "claude": None,
            "opencode": tmp_path / "missing-opencode" / "obsidian-skills",
        },
        registry_path=missing_registry,
        project_root=tmp_path,
    )

    assert result["availability"]["available_package"] is False  # type: ignore[index]
    assert result["counts"]["available_skill_count"] == 1  # type: ignore[index]
    assert result["counts"]["configured_host_layouts"] == 2  # type: ignore[index]
    assert not missing_registry.exists()

    hosts = {host["host"]: host for host in result["hosts"]}  # type: ignore[index]
    assert hosts["codex"]["status"] == "partial"
    assert hosts["codex"]["missing_skills"] == [
        "obsidian-bases",
        "json-canvas",
        "obsidian-cli",
        "defuddle",
    ]
    assert hosts["codex"]["unexpected_skills"] == ["local-extra"]
    assert hosts["codex"]["digest_coverage"] == "partial"
    assert hosts["claude"]["status"] == "unconfigured"
    assert hosts["claude"]["notes"] == ["root_not_configured"]
    assert hosts["opencode"]["status"] == "missing"
    assert hosts["opencode"]["notes"] == ["root_missing"]

    skipped = result["source_selection"]["skipped"]  # type: ignore[index]
    assert {item["host"] for item in skipped if item["kind"] == "host_layout"} == {"claude"}  # type: ignore[index]
    assert any(item["kind"] == "aios_registry" for item in skipped)  # type: ignore[index]


def test_matrix_rejects_unknown_host_layout() -> None:
    with pytest.raises(ValueError, match="Unsupported skill package host"):
        discover_skill_package_matrix({"windsurf": None})
