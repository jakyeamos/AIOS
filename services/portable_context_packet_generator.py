from __future__ import annotations

import json
import sqlite3
import subprocess
import uuid
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKET_DIR = REPO_ROOT / "config" / "context-packets"
SENSITIVE_MARKERS = (".env", "secrets", "credentials", "personal/")


class PrivacyFilterError(ValueError):
    pass


def _packet_id() -> str:
    return f"packet-{uuid.uuid4()}"


def _check_private_text(value: str) -> None:
    lowered = value.lower()
    if any(marker in lowered for marker in SENSITIVE_MARKERS):
        raise PrivacyFilterError("Portable context packets cannot include personal or secret paths.")


def _repo_files(repo_path: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=repo_path,
            check=False,
            capture_output=True,
            text=True,
        )
        files = result.stdout.splitlines()
    except FileNotFoundError:
        files = [str(path.relative_to(repo_path)) for path in repo_path.rglob("*") if path.is_file()]
    allowed = {".py", ".ts", ".tsx", ".json", ".md"}
    selected = []
    for file_path in files:
        _check_private_text(file_path)
        if Path(file_path).suffix in allowed:
            selected.append(file_path)
        if len(selected) >= 20:
            break
    return selected


def _package_scripts(repo_path: Path) -> list[str]:
    package_json = repo_path / "package.json"
    if not package_json.exists():
        return []
    data = json.loads(package_json.read_text(encoding="utf-8"))
    scripts = data.get("scripts", {})
    if not isinstance(scripts, dict):
        return []
    return [f"pnpm {name}" for name in scripts if name in {"test", "lint", "typecheck", "build"}]


def _detect_conventions(repo_path: Path) -> list[str]:
    conventions = []
    if (repo_path / "package.json").exists():
        conventions.append("node-package")
    if (repo_path / "pyproject.toml").exists():
        conventions.append("python-pyproject")
    if (repo_path / "aios-ui" / "package.json").exists():
        conventions.append("nextjs-ui")
    return conventions


def generate_packet(
    conn: sqlite3.Connection,
    *,
    task_description: str,
    repo_path: str | Path,
    packet_id: str | None = None,
) -> dict[str, Any]:
    _check_private_text(task_description)
    repo = Path(repo_path).resolve()
    packet_id = packet_id or _packet_id()
    packet = {
        "packet_id": packet_id,
        "scope": "repo",
        "task_summary": task_description,
        "included_files": _repo_files(repo),
        "detected_conventions": _detect_conventions(repo),
        "test_commands": _package_scripts(repo),
        "success_criteria_refs": sorted(
            str(path.relative_to(repo))
            for path in (repo / "config" / "success-criteria").glob("**/*")
            if path.is_file()
        )
        if (repo / "config" / "success-criteria").exists()
        else [],
        "known_constraints": ["local-first", "exclude personal and secret sources"],
        "excluded_content_categories": ["personal_notes", "private_history", "secrets"],
        "privacy_review_status": "filtered",
        "staleness_notes": [],
    }
    DEFAULT_PACKET_DIR.mkdir(parents=True, exist_ok=True)
    (DEFAULT_PACKET_DIR / f"{packet_id}.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return packet
