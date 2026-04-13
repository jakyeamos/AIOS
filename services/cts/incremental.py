from __future__ import annotations

import hashlib
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .parser import SUPPORTED_EXTENSIONS


def _run_git(repo_path: Path, args: list[str]) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo_path), *args],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def git_head(repo_path: Path) -> str | None:
    out = _run_git(repo_path, ["rev-parse", "HEAD"])
    return out or None


def detect_changed_files(repo_path: Path, base: str = "HEAD~1") -> list[Path]:
    output = _run_git(repo_path, ["diff", "--name-only", f"{base}...HEAD"])
    if not output:
        return []
    files: list[Path] = []
    for line in output.splitlines():
        candidate = (repo_path / line.strip()).resolve()
        if candidate.is_file() and candidate.suffix in SUPPORTED_EXTENSIONS:
            files.append(candidate)
    return sorted(set(files))


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def changed_files_by_hash(repo_path: Path, known_hashes: dict[str, str]) -> list[str]:
    changed: list[str] = []
    for rel, old_hash in known_hashes.items():
        full = (repo_path / rel).resolve()
        if not full.exists():
            changed.append(rel)
            continue
        if file_hash(full) != old_hash:
            changed.append(rel)
    return sorted(changed)


@dataclass(slots=True)
class WatchEvent:
    changed_files: list[Path]
    reason: str


def watch_repo(
    repo_path: Path,
    callback: Callable[[WatchEvent], None],
    debounce_ms: int = 300,
    poll_interval_seconds: float = 0.35,
) -> None:
    pending: set[Path] = set()
    last_event_at = 0.0
    last_mtimes: dict[Path, float] = {}

    tracked = [
        p
        for p in repo_path.rglob("*")
        if p.is_file() and p.suffix in SUPPORTED_EXTENSIONS and ".git" not in p.parts
    ]
    for path in tracked:
        try:
            last_mtimes[path] = path.stat().st_mtime
        except OSError:
            continue

    while True:
        current_files = [
            p
            for p in repo_path.rglob("*")
            if p.is_file() and p.suffix in SUPPORTED_EXTENSIONS and ".git" not in p.parts
        ]
        current_set = set(current_files)
        for missing in list(last_mtimes):
            if missing not in current_set:
                pending.add(missing)
                del last_mtimes[missing]
                last_event_at = time.time()
        for path in current_files:
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            prev = last_mtimes.get(path)
            if prev is None or mtime != prev:
                pending.add(path)
                last_event_at = time.time()
            last_mtimes[path] = mtime
        if pending and (time.time() - last_event_at) * 1000 >= debounce_ms:
            callback(WatchEvent(changed_files=sorted(pending), reason="polling-watch"))
            pending.clear()
        time.sleep(poll_interval_seconds)

