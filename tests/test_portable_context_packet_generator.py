# ruff: noqa: E402

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.portable_context_packet_generator import (  # noqa: E402
    PrivacyFilterError,
    generate_packet,
)


def test_generate_packet_returns_template_fields_and_writes_json(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    packet_dir = tmp_path / "packets"
    repo.mkdir()
    (repo / "package.json").write_text(
        json.dumps({"scripts": {"test": "vitest", "lint": "eslint ."}}),
        encoding="utf-8",
    )
    (repo / "src.ts").write_text("export const value = 1;\n", encoding="utf-8")
    conn = sqlite3.connect(":memory:")

    with patch("services.portable_context_packet_generator.DEFAULT_PACKET_DIR", packet_dir):
        packet = generate_packet(
            conn,
            task_description="Implement portable packet generation.",
            repo_path=repo,
            packet_id="packet-test",
        )

    assert set(packet) == {
        "packet_id",
        "scope",
        "task_summary",
        "included_files",
        "detected_conventions",
        "test_commands",
        "success_criteria_refs",
        "known_constraints",
        "excluded_content_categories",
        "privacy_review_status",
        "staleness_notes",
    }
    assert "pnpm test" in packet["test_commands"]
    assert (packet_dir / "packet-test.json").exists()


def test_privacy_filter_rejects_env_file_path(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    with patch("services.portable_context_packet_generator.subprocess.run") as run:
        run.return_value.stdout = ".env\n"
        with pytest.raises(PrivacyFilterError):
            generate_packet(sqlite3.connect(":memory:"), task_description="Task", repo_path=repo)


def test_privacy_filter_rejects_personal_path_in_task_description(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    with pytest.raises(PrivacyFilterError):
        generate_packet(
            sqlite3.connect(":memory:"),
            task_description="Use personal/private vault material",
            repo_path=repo,
        )


def test_test_commands_are_extracted_from_package_scripts(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    packet_dir = tmp_path / "packets"
    repo.mkdir()
    (repo / "package.json").write_text(
        json.dumps({"scripts": {"test": "vitest", "typecheck": "tsc --noEmit"}}),
        encoding="utf-8",
    )

    with patch("services.portable_context_packet_generator.DEFAULT_PACKET_DIR", packet_dir):
        packet = generate_packet(
            sqlite3.connect(":memory:"),
            task_description="Task",
            repo_path=repo,
            packet_id="packet-scripts",
        )

    assert packet["test_commands"] == ["pnpm test", "pnpm typecheck"]
