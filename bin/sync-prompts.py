#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aios_paths import get_vault_subpath  # noqa: E402

from services.storage import connect as connect_storage  # noqa: E402


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _extract_body(markdown: str) -> str:
    if not markdown.startswith("---\n"):
        return markdown
    lines = markdown.splitlines()
    end_index = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_index = idx
            break
    if end_index is None:
        return markdown
    return "\n".join(lines[end_index + 1 :]).lstrip("\n")


def _body_hash(markdown: str) -> str:
    body = _extract_body(markdown)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _template_files(prompts_root: Path) -> list[Path]:
    files = [path for path in sorted(prompts_root.glob("*.md")) if path.name != "README.md"]
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync AIOS prompt templates to vault and DB links")
    parser.add_argument(
        "--prompts-root",
        default=str((Path.home() / "AIOS" / "prompts").resolve()),
        help="Path to prompts root (default: ~/AIOS/prompts)",
    )
    parser.add_argument(
        "--db",
        default=os.environ.get(
            "AIOS_DB", str((Path.home() / "AIOS" / "data" / "aios.db").resolve())
        ),
        help="SQLite DB path (default: ~/AIOS/data/aios.db or AIOS_DB)",
    )
    parser.add_argument(
        "--vault-dest",
        default=str(get_vault_subpath("07 Templates", "Prompts")),
        help="Vault destination directory",
    )
    args = parser.parse_args(argv)

    prompts_root = Path(args.prompts_root).expanduser().resolve()
    db_path = Path(args.db).expanduser().resolve()
    vault_dest = Path(args.vault_dest).expanduser().resolve()

    if not prompts_root.exists():
        print(f"prompts root not found: {prompts_root}")
        return 1
    if not db_path.exists():
        print(f"db not found: {db_path}")
        return 1

    vault_dest.mkdir(parents=True, exist_ok=True)
    files = _template_files(prompts_root)
    created = 0
    updated = 0
    copied = 0

    conn = connect_storage(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS prompt_library_links (
          id TEXT PRIMARY KEY,
          prompt_hash TEXT NOT NULL,
          obsidian_note_path TEXT,
          promoted_at TEXT
        )
        """
    )

    for path in files:
        markdown = path.read_text(encoding="utf-8")
        prompt_hash = _body_hash(markdown)
        destination = vault_dest / path.name
        shutil.copy2(path, destination)
        copied += 1

        now = _now_iso()
        existing = conn.execute(
            "SELECT id FROM prompt_library_links WHERE prompt_hash = ? LIMIT 1",
            (prompt_hash,),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE prompt_library_links
                SET obsidian_note_path = ?, promoted_at = ?
                WHERE id = ?
                """,
                (str(destination), now, existing[0]),
            )
            updated += 1
        else:
            conn.execute(
                """
                INSERT INTO prompt_library_links (id, prompt_hash, obsidian_note_path, promoted_at)
                VALUES (?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), prompt_hash, str(destination), now),
            )
            created += 1

    conn.commit()
    conn.close()

    summary = {
        "prompts_root": str(prompts_root),
        "vault_dest": str(vault_dest),
        "db_path": str(db_path),
        "copied": copied,
        "created_links": created,
        "updated_links": updated,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
