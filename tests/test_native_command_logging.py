from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.aios_cli import EXIT_OK, run_cli  # noqa: E402
from services.native_command_logging import (  # noqa: E402
    native_command_metadata,
    write_native_command_metadata,
)


def test_native_command_metadata_shape_with_optional_fields(tmp_path: Path) -> None:
    record = native_command_metadata(
        command_name="audit-security",
        repo_root=tmp_path,
        scope={"files": ["services/example.py"]},
        safety_class="read_only",
        status="pass",
        read_only=True,
        modifying=False,
        reviewer_lanes=["security"],
        files_touched=[],
        tests_run=["uv run pytest -q tests/test_native_commands.py"],
        user_confirmation_required=False,
        user_confirmation_received=False,
        model="gpt-test",
        reasoning_level="medium",
        token_cost_estimate=0.01,
        runtime_ms=123,
        run_id="run-1",
        session_id="session-1",
    )

    assert record["command_name"] == "audit-security"
    assert record["project"] == tmp_path.name
    assert record["scope"] == {"files": ["services/example.py"]}
    assert record["read_only"] is True
    assert record["modifying"] is False
    assert record["telemetry"] == "local_jsonl_only"
    assert record["model"] == "gpt-test"
    assert record["runtime_ms"] == 123


def test_native_command_metadata_allows_unavailable_optional_fields(tmp_path: Path) -> None:
    record = native_command_metadata(
        command_name="zoom-out",
        repo_root=tmp_path,
        scope={"target": "services"},
        safety_class="read_only",
        status="pass",
        read_only=True,
        modifying=False,
    )

    assert record["model"] is None
    assert record["reasoning_level"] is None
    assert record["token_cost_estimate"] is None
    assert record["runtime_ms"] is None
    assert record["run_id"] is None
    assert record["session_id"] is None


def test_write_native_command_metadata_is_local_jsonl_only(tmp_path: Path) -> None:
    record = native_command_metadata(
        command_name="prototype",
        repo_root=tmp_path,
        scope={"sandbox_path": ".planning/prototypes/demo"},
        safety_class="sandbox_write",
        status="pass",
        read_only=False,
        modifying=True,
        user_confirmation_required=True,
        user_confirmation_received=True,
    )

    path = write_native_command_metadata(record, repo_root=tmp_path)

    assert path == tmp_path / ".aios" / "native-command-metadata.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows == [record]
    assert "http" not in path.read_text(encoding="utf-8").lower()


def test_write_native_command_metadata_rejects_external_paths(tmp_path: Path) -> None:
    record = native_command_metadata(
        command_name="handoff",
        repo_root=tmp_path,
        scope={},
        safety_class="artifact_write",
        status="pass",
        read_only=False,
        modifying=True,
    )

    try:
        write_native_command_metadata(
            record,
            repo_root=tmp_path,
            log_path=tmp_path.parent / "outside.jsonl",
        )
    except ValueError as exc:
        assert "inside the repo root" in str(exc)
    else:
        raise AssertionError("external metadata log path was accepted")


def test_native_cli_can_write_explicit_local_metadata_log(tmp_path: Path, capsys) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    target = repo / "example.py"
    target.write_text("print('ok')\n", encoding="utf-8")

    assert (
        run_cli(
            [
                "--json",
                "zoom-out",
                str(target),
                "--repo-root",
                str(repo),
                "--log-metadata",
                "--metadata-log-path",
                ".aios/native-test.jsonl",
                "--run-id",
                "run-1",
                "--session-id",
                "session-1",
            ]
        )
        == EXIT_OK
    )
    payload = json.loads(capsys.readouterr().out)
    log_path = repo / ".aios" / "native-test.jsonl"
    assert payload["data"]["metadata_log_path"] == str(log_path)
    rows = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["command_name"] == "zoom-out"
    assert rows[0]["run_id"] == "run-1"
    assert rows[0]["session_id"] == "session-1"
    assert rows[0]["telemetry"] == "local_jsonl_only"
