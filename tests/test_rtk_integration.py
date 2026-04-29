from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.rtk_integration import (  # noqa: E402
    classify_rtk_metrics,
    compress_output,
    ensure_rtk_schema,
    record_rtk_event,
    rtk_metrics_log,
    rtk_run,
)


def test_compress_output_preserves_failure_signal() -> None:
    raw = "\n".join(
        [
            "Progress: resolved 100 packages",
            "tests/test_example.py::test_ok PASSED",
            "tests/test_example.py::test_bad FAILED",
            "Traceback (most recent call last):",
            '  File "tests/test_example.py", line 8, in test_bad',
            "AssertionError: expected 1 got 2",
            "Progress: resolved 101 packages",
        ]
    )

    compressed, ambiguous = compress_output(raw, command="pytest -q", exit_code=1)

    assert ambiguous is False
    assert "exit_code=1" in compressed
    assert "test_bad FAILED" in compressed
    assert "AssertionError" in compressed
    assert "Progress: resolved 100 packages" not in compressed


def test_rtk_run_records_metrics(tmp_path: Path) -> None:
    db_path = tmp_path / "aios.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE sessions (id TEXT PRIMARY KEY)")
    conn.execute(
        """
        CREATE TABLE workflow_metrics (
          id TEXT PRIMARY KEY,
          session_id TEXT,
          metric_name TEXT NOT NULL,
          metric_value REAL NOT NULL,
          recorded_at TEXT NOT NULL,
          notes TEXT
        )
        """
    )
    conn.execute("INSERT INTO sessions (id) VALUES ('s1')")
    ensure_rtk_schema(conn)

    result = rtk_run(
        f"{sys.executable} -c 'print(\"ok\")'",
        "compressed",
        conn=conn,
        session_id="s1",
        source_kind="test",
    )
    conn.commit()

    assert result.exit_code == 0
    assert result.effective_mode == "raw"
    assert result.output == "ok"
    metrics = rtk_metrics_log(conn, session_id="s1")
    assert metrics["event_count"] == 1
    assert metrics["raw_tokens"] >= 1
    assert metrics["compressed_tokens"] >= 1
    metric_rows = conn.execute("SELECT metric_name FROM workflow_metrics").fetchall()
    assert {row["metric_name"] for row in metric_rows} >= {
        "rtk.raw_tokens",
        "rtk.compressed_tokens",
        "rtk.tokens_saved",
        "rtk.token_reduction_percent",
    }
    conn.close()


def test_rtk_run_passes_through_short_success_output() -> None:
    result = rtk_run(f"{sys.executable} -c 'print(\"tiny\")'", "adaptive")

    assert result.effective_mode == "raw"
    assert result.output == "tiny"
    assert result.estimated_raw_tokens == result.estimated_compressed_tokens


def test_record_rtk_event_without_session(tmp_path: Path) -> None:
    conn = sqlite3.connect(tmp_path / "aios.db")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE workflow_metrics (
          id TEXT PRIMARY KEY,
          session_id TEXT,
          metric_name TEXT NOT NULL,
          metric_value REAL NOT NULL,
          recorded_at TEXT NOT NULL,
          notes TEXT
        )
        """
    )
    ensure_rtk_schema(conn)
    result = rtk_run(f"{sys.executable} -c 'print(\"line\")'", "compressed")

    event_id = record_rtk_event(conn, result=result, source_kind="unit")
    conn.commit()

    row = conn.execute("SELECT id, source_kind FROM rtk_compression_events").fetchone()
    assert row["id"] == event_id
    assert row["source_kind"] == "unit"
    assert conn.execute("SELECT COUNT(*) AS c FROM workflow_metrics").fetchone()["c"] == 0
    conn.close()


def test_classify_rtk_metrics_distinguishes_no_benefit_states() -> None:
    no_events = classify_rtk_metrics(
        {"event_count": 0, "raw_tokens": 0, "compressed_tokens": 0, "tokens_saved": 0}
    )
    assert no_events["state"] == "no_eligible_data"
    assert no_events["benefit_state"] == "no_eligible_data"

    regressive = classify_rtk_metrics(
        {"event_count": 2, "raw_tokens": 10, "compressed_tokens": 14, "tokens_saved": 0}
    )
    assert regressive["state"] == "token_regressive"
    assert regressive["benefit_state"] == "token_regressive"

    beneficial = classify_rtk_metrics(
        {"event_count": 2, "raw_tokens": 20, "compressed_tokens": 12, "tokens_saved": 8}
    )
    assert beneficial["state"] == "active"
    assert beneficial["benefit_state"] == "beneficial"
