from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
import subprocess
from pathlib import Path

from services.session_intelligence_loop import (
    HELPER_FAMILY_PRESETS,
    list_session_intelligence_candidates,
    list_session_intelligence_implementations,
)

HELPER_FAMILIES = tuple(sorted(HELPER_FAMILY_PRESETS))


def list_session_intelligence_helpers(conn: sqlite3.Connection) -> list[dict[str, object]]:
    helpers: list[dict[str, object]] = []
    for implementation in list_session_intelligence_implementations(conn):
        family = str(implementation["helper_family"])
        helpers.append(
            {
                "family": family,
                "description": HELPER_FAMILY_PRESETS.get(family, "Session intelligence helper."),
                "implemented": True,
                "candidate_count": int(implementation["candidate_count"]),
                "telemetry_status": implementation["telemetry_status"],
                "removal_status": implementation["removal_status"],
                "artifact_ref": implementation["implemented_artifact_ref"],
            }
        )
    return helpers


def run_session_intelligence_helper(
    conn: sqlite3.Connection,
    *,
    family: str,
    path: str | None = None,
    repo: str | None = None,
    start_line: int | None = None,
    end_line: int | None = None,
) -> dict[str, object]:
    if family not in HELPER_FAMILIES:
        raise ValueError(f"Unsupported session intelligence helper family: {family}")

    base: dict[str, object] = {
        "family": family,
        "description": HELPER_FAMILY_PRESETS[family],
        "implementation": _implementation_payload(conn, family),
    }
    if family == "doc_excerpt":
        return {**base, **_doc_excerpt(path, start_line=start_line, end_line=end_line)}
    if family == "artifact_probe":
        return {**base, **_artifact_probe(path)}
    if family == "repo_state":
        return {**base, **_repo_state(repo)}
    if family == "git_history":
        return {**base, **_git_history(repo)}
    if family == "package_check":
        return {**base, **_package_check(repo)}
    if family == "deployment_flow":
        return {**base, **_deployment_flow(repo)}
    if family in {"bespoke_review", "workflow_skill"}:
        return {**base, **_candidate_triage(conn, family)}
    raise ValueError(f"Unsupported session intelligence helper family: {family}")


def _implementation_payload(conn: sqlite3.Connection, family: str) -> dict[str, object] | None:
    for implementation in list_session_intelligence_implementations(conn):
        if implementation["helper_family"] == family:
            return {
                "id": implementation["id"],
                "lane": implementation["lane"],
                "candidate_count": implementation["candidate_count"],
                "telemetry_status": implementation["telemetry_status"],
                "removal_status": implementation["removal_status"],
                "artifact_ref": implementation["implemented_artifact_ref"],
            }
    return None


def _required_path(path: str | None) -> Path:
    if not path:
        raise ValueError("--path is required for this helper family")
    resolved = Path(path).expanduser().resolve()
    if not resolved.exists():
        raise FileNotFoundError(str(resolved))
    return resolved


def _repo_path(repo: str | None) -> Path:
    resolved = Path(repo or ".").expanduser().resolve()
    if not resolved.exists() or not resolved.is_dir():
        raise FileNotFoundError(str(resolved))
    return resolved


def _doc_excerpt(
    path: str | None,
    *,
    start_line: int | None,
    end_line: int | None,
) -> dict[str, object]:
    resolved = _required_path(path)
    start = max(1, start_line or 1)
    end = end_line or start + 119
    if end < start:
        raise ValueError("--end-line must be greater than or equal to --start-line")
    if end - start > 499:
        raise ValueError("doc_excerpt is capped at 500 lines per invocation")
    lines = resolved.read_text(encoding="utf-8", errors="replace").splitlines()
    excerpt = [
        {"line": line_number, "text": text}
        for line_number, text in enumerate(lines, start=1)
        if start <= line_number <= end
    ]
    return {
        "path": str(resolved),
        "start_line": start,
        "end_line": end,
        "line_count": len(excerpt),
        "lines": excerpt,
    }


def _artifact_probe(path: str | None) -> dict[str, object]:
    resolved = _required_path(path)
    payload: dict[str, object] = {
        "path": str(resolved),
        "size_bytes": resolved.stat().st_size,
        "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest(),
    }
    suffix = resolved.suffix.lower()
    if suffix == ".json":
        loaded = json.loads(resolved.read_text(encoding="utf-8"))
        payload["artifact"] = _json_summary(loaded)
    elif suffix == ".csv":
        payload["artifact"] = _csv_summary(resolved)
    else:
        payload["artifact"] = {"kind": suffix.removeprefix(".") or "file"}
    return payload


def _json_summary(loaded: object) -> dict[str, object]:
    if isinstance(loaded, dict):
        array_lengths = {
            str(key): len(value) for key, value in loaded.items() if isinstance(value, list)
        }
        return {
            "kind": "json",
            "shape": "object",
            "top_level_keys": sorted(str(key) for key in loaded),
            "array_lengths": dict(sorted(array_lengths.items())),
        }
    if isinstance(loaded, list):
        return {"kind": "json", "shape": "array", "item_count": len(loaded)}
    return {"kind": "json", "shape": type(loaded).__name__}


def _csv_summary(path: Path) -> dict[str, object]:
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        reader = csv.reader(handle)
        headers = next(reader, [])
        row_count = sum(1 for _ in reader)
    return {"kind": "csv", "headers": headers, "row_count": row_count}


def _repo_state(repo: str | None) -> dict[str, object]:
    repo_path = _repo_path(repo)
    return {
        "repo": str(repo_path),
        "git": {
            "branch": _git(repo_path, ["rev-parse", "--abbrev-ref", "HEAD"]),
            "status_short": _git(repo_path, ["status", "--short", "--branch"]),
            "diff_stat": _git(repo_path, ["diff", "--stat"]),
            "diff_check": _git(repo_path, ["diff", "--check"]),
        },
    }


def _git_history(repo: str | None) -> dict[str, object]:
    repo_path = _repo_path(repo)
    return {
        "repo": str(repo_path),
        "git": {
            "recent_commits": _git(repo_path, ["log", "--oneline", "--decorate", "-5"]),
            "latest_commit": _git(
                repo_path, ["show", "--stat", "--oneline", "--no-renames", "HEAD"]
            ),
            "recent_tags": _git(repo_path, ["tag", "--sort=-creatordate", "--merged", "HEAD"]),
        },
    }


def _git(repo_path: Path, args: list[str]) -> dict[str, object]:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_path,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    return {
        "command": ["git", *args],
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def _package_check(repo: str | None) -> dict[str, object]:
    repo_path = _repo_path(repo)
    package_json = repo_path / "package.json"
    if not package_json.exists():
        raise FileNotFoundError(str(package_json))
    loaded = json.loads(package_json.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("package.json must contain a JSON object")
    scripts = loaded.get("scripts", {})
    if not isinstance(scripts, dict):
        scripts = {}
    package_manager = _package_manager(repo_path, loaded)
    return {
        "repo": str(repo_path),
        "package_json": str(package_json),
        "package_manager": package_manager,
        "package_manager_field": loaded.get("packageManager"),
        "lockfiles": _lockfiles(repo_path),
        "scripts": {str(key): str(value) for key, value in sorted(scripts.items())},
        "quality_scripts": [
            name for name in ("lint", "typecheck", "test", "build", "verify") if name in scripts
        ],
    }


def _package_manager(repo_path: Path, package_json: dict[object, object]) -> str | None:
    package_manager = package_json.get("packageManager")
    if isinstance(package_manager, str) and package_manager:
        return package_manager.split("@", 1)[0]
    lockfiles = _lockfiles(repo_path)
    if "pnpm-lock.yaml" in lockfiles:
        return "pnpm"
    if "package-lock.json" in lockfiles:
        return "npm"
    if "yarn.lock" in lockfiles:
        return "yarn"
    return None


def _lockfiles(repo_path: Path) -> list[str]:
    return [
        name
        for name in ("pnpm-lock.yaml", "package-lock.json", "yarn.lock")
        if (repo_path / name).exists()
    ]


def _deployment_flow(repo: str | None) -> dict[str, object]:
    repo_path = _repo_path(repo)
    package_json = repo_path / "package.json"
    scripts: dict[str, str] = {}
    if package_json.exists():
        loaded = json.loads(package_json.read_text(encoding="utf-8"))
        if isinstance(loaded, dict) and isinstance(loaded.get("scripts"), dict):
            scripts = {str(key): str(value) for key, value in loaded["scripts"].items()}
    return {
        "repo": str(repo_path),
        "vercel_json": str(repo_path / "vercel.json")
        if (repo_path / "vercel.json").exists()
        else None,
        "deployment_scripts": {
            name: command
            for name, command in sorted(scripts.items())
            if "deploy" in name or "vercel" in command
        },
        "env_files_present": [
            name
            for name in (".env", ".env.local", ".env.production", ".env.preview")
            if (repo_path / name).exists()
        ],
    }


def _candidate_triage(conn: sqlite3.Connection, family: str) -> dict[str, object]:
    candidates = [
        candidate
        for candidate in list_session_intelligence_candidates(conn, status="implemented")
        if _candidate_matches_family(candidate, family)
    ]
    return {
        "candidate_count": len(candidates),
        "candidates": [
            {
                "id": candidate["id"],
                "lane": candidate["lane"],
                "title": candidate["title"],
                "impact_score": candidate["impact_score"],
                "updated_at": candidate["updated_at"],
            }
            for candidate in candidates[:25]
        ],
    }


def _candidate_matches_family(candidate: dict[str, object], family: str) -> bool:
    if family == "workflow_skill":
        return candidate["lane"] == "workflow_skill"
    title = str(candidate["title"]).lower()
    summary = str(candidate["summary"]).lower()
    if family == "bespoke_review":
        stable_tokens = (
            "sed -n",
            ".json",
            ".csv",
            "git status",
            "git diff",
            "git log",
            "git show",
            "package",
            "pnpm",
            "vercel",
        )
        return candidate["lane"] == "friction_tool" and not any(
            token in f"{title} {summary}" for token in stable_tokens
        )
    return False
