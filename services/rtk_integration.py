from __future__ import annotations

import json
import re
import shlex
import shutil
import sqlite3
import subprocess
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES_PATH = REPO_ROOT / "config" / "rtk" / "rules.json"
DEFAULT_TEE_DIR = Path.home() / "AIOS" / "logs" / "rtk-raw"

RTKMode = Literal["compressed", "raw", "adaptive"]
RTKState = Literal["active", "inactive", "no_eligible_data", "token_regressive", "misconfigured"]
RTKBenefitState = Literal["beneficial", "no_benefit", "token_regressive", "no_eligible_data"]

ERROR_PATTERNS = re.compile(
    r"(Traceback \(most recent call last\)|"
    r"\b(error|failed|failure|fatal|panic|exception)\b|"
    r"AssertionError|SyntaxError|TypeError|ValueError|"
    r"ModuleNotFoundError|ImportError|NameError|"
    r"npm ERR!|ERR_PNPM|TS\d{4}|pytest.*FAILED|jest.*FAIL)",
    re.IGNORECASE,
)
STACK_OR_LOCATION = re.compile(
    r"(^\s*File \".+\", line \d+|^\s*at\s+\S+|"
    r"^[\w./-]+\.(py|ts|tsx|js|jsx|rs|go|java|rb):\d+)",
    re.IGNORECASE,
)
DIFF_HEADER = re.compile(r"^(diff --git|@@ |[+-]{3} |\+\+\+ |--- )")
CHANGED_FILE = re.compile(
    r"^(?:\s*(?:modified|new file|deleted|renamed|M|A|D|\?\?)\s*:?\s+|"
    r"(?:create|delete) mode \d+\s+)(?P<path>[\w./@{} -]+)$",
    re.IGNORECASE,
)
TEST_FAILURE = re.compile(
    r"(\bFAILED\b|\bFAIL\b|\bfailures?\b|"
    r"::test_|test_.*failed|expected .* received|AssertionError)",
    re.IGNORECASE,
)
BOILERPLATE = re.compile(
    r"^(?:\s*$|"
    r"Done in \d|"
    r"found \d+ vulnerabilities|"
    r"added \d+ packages|"
    r"changed \d+ packages|"
    r"Progress: resolved|"
    r"Collecting |Installing collected packages|"
    r"Requirement already satisfied|"
    r"Downloading |"
    r"Enumerating objects:|Counting objects:|Compressing objects:|Receiving objects:|Resolving deltas:|"
    r"\s*✓ |\s*PASS\s)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RTKRunResult:
    command: str
    mode: RTKMode
    effective_mode: RTKMode
    exit_code: int
    output: str
    raw_output: str
    raw_chars: int
    compressed_chars: int
    estimated_raw_tokens: int
    estimated_compressed_tokens: int
    token_reduction_percent: float
    ambiguous_failure: bool
    raw_output_path: str | None
    used_upstream_rtk: bool

    def to_dict(self, *, include_raw: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "command": self.command,
            "mode": self.mode,
            "effective_mode": self.effective_mode,
            "exit_code": self.exit_code,
            "output": self.output,
            "raw_chars": self.raw_chars,
            "compressed_chars": self.compressed_chars,
            "estimated_raw_tokens": self.estimated_raw_tokens,
            "estimated_compressed_tokens": self.estimated_compressed_tokens,
            "token_reduction_percent": self.token_reduction_percent,
            "ambiguous_failure": self.ambiguous_failure,
            "raw_output_path": self.raw_output_path,
            "used_upstream_rtk": self.used_upstream_rtk,
        }
        if include_raw:
            payload["raw_output"] = self.raw_output
        return payload


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, round(len(text) / 4))


def load_compression_rules(path: Path = DEFAULT_RULES_PATH) -> dict[str, Any]:
    if not path.exists():
        return {
            "default_mode": "compressed",
            "preserve": [],
            "reduce": [],
            "workflow_modes": {},
            "high_token_sources": [],
        }
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object JSON at {path}")
    return payload


def ensure_rtk_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rtk_compression_events (
          id TEXT PRIMARY KEY,
          session_id TEXT REFERENCES sessions(id),
          run_id TEXT REFERENCES orchestration_runs(id),
          workflow_key TEXT,
          source_kind TEXT NOT NULL,
          command TEXT,
          mode TEXT NOT NULL,
          effective_mode TEXT NOT NULL,
          exit_code INTEGER,
          raw_chars INTEGER NOT NULL,
          compressed_chars INTEGER NOT NULL,
          estimated_raw_tokens INTEGER NOT NULL,
          estimated_compressed_tokens INTEGER NOT NULL,
          token_reduction_percent REAL NOT NULL,
          ambiguous_failure INTEGER NOT NULL DEFAULT 0,
          raw_output_path TEXT,
          metadata_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_rtk_compression_events_session
          ON rtk_compression_events(session_id, created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_rtk_compression_events_workflow
          ON rtk_compression_events(workflow_key, created_at DESC)
        """
    )


def _write_raw_output(command: str, raw_output: str, tee_dir: Path = DEFAULT_TEE_DIR) -> str:
    tee_dir.mkdir(parents=True, exist_ok=True)
    safe_stem = re.sub(r"[^a-zA-Z0-9_.-]+", "_", command.strip())[:64] or "command"
    path = tee_dir / f"{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}_{safe_stem}.log"
    path.write_text(raw_output, encoding="utf-8", errors="replace")
    return str(path)


def _line_key(line: str) -> str:
    return re.sub(r"\d+", "#", line.strip())


def compress_output(
    raw_output: str,
    *,
    command: str,
    exit_code: int | None = None,
    max_lines: int = 80,
) -> tuple[str, bool]:
    lines = raw_output.splitlines()
    if not lines:
        header = f"$ {command}\nexit_code={exit_code if exit_code is not None else 'unknown'}"
        return header, bool(exit_code)

    preserved: list[str] = []
    changed_files: list[str] = []
    failures: list[str] = []
    counters: Counter[str] = Counter()

    for line in lines:
        stripped = line.rstrip()
        key = _line_key(stripped)
        counters[key] += 1

        changed = CHANGED_FILE.search(stripped)
        if changed:
            changed_files.append(changed.group("path").strip())
            continue

        if (
            ERROR_PATTERNS.search(stripped)
            or STACK_OR_LOCATION.search(stripped)
            or DIFF_HEADER.search(stripped)
            or TEST_FAILURE.search(stripped)
        ):
            if stripped not in preserved:
                preserved.append(stripped)
            if TEST_FAILURE.search(stripped):
                failures.append(stripped)
            continue

        if BOILERPLATE.search(stripped):
            continue

        if counters[key] <= 2 and len(preserved) < max_lines // 2:
            preserved.append(stripped)

    duplicate_notes = [
        f"{count}x {key}"
        for key, count in counters.most_common(8)
        if count >= 4 and key and not BOILERPLATE.search(key)
    ]

    sections = [
        f"$ {command}",
        f"exit_code={exit_code if exit_code is not None else 'unknown'}",
    ]
    if changed_files:
        sections.append("changed_files:\n" + "\n".join(f"- {path}" for path in sorted(set(changed_files))[:30]))
    if failures:
        sections.append("failing_tests_or_assertions:\n" + "\n".join(f"- {row}" for row in failures[:20]))
    if preserved:
        sections.append("signal:\n" + "\n".join(preserved[:max_lines]))
    if duplicate_notes:
        sections.append("deduplicated:\n" + "\n".join(f"- {row}" for row in duplicate_notes))

    ambiguous_failure = bool(exit_code and exit_code != 0 and not (failures or ERROR_PATTERNS.search(raw_output)))
    if ambiguous_failure:
        sections.append("warning: non-zero exit with weak error signal; expand with raw mode.")

    compressed = "\n\n".join(sections).strip()
    return compressed, ambiguous_failure


def _can_delegate_to_upstream(command: str) -> bool:
    if not shutil.which("rtk"):
        return False
    try:
        shlex.split(command)
    except ValueError:
        return False
    return any(command.strip().startswith(prefix) for prefix in ("git ", "pnpm ", "npm ", "pytest", "docker ", "tsc"))


def _execute(command: str, cwd: str | Path | None, timeout: int | None) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        shell=True,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    raw = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()
    return completed.returncode, raw


def rtk_run(
    command: str,
    mode: RTKMode = "compressed",
    *,
    cwd: str | Path | None = None,
    timeout: int | None = None,
    session_id: str | None = None,
    run_id: str | None = None,
    workflow_key: str | None = None,
    conn: sqlite3.Connection | None = None,
    source_kind: str = "rtk_run",
) -> RTKRunResult:
    if mode not in {"compressed", "raw", "adaptive"}:
        raise ValueError("mode must be one of: compressed, raw, adaptive")

    used_upstream = False
    effective_command = command
    if mode != "raw" and _can_delegate_to_upstream(command):
        effective_command = "rtk " + command
        used_upstream = True

    exit_code, raw_output = _execute(effective_command, cwd, timeout)
    if not used_upstream and mode != "raw" and exit_code == 0:
        threshold = _passthrough_threshold(command, load_compression_rules())
        if threshold > 0 and len(raw_output) < threshold:
            raw_tokens = estimate_tokens(raw_output)
            result = RTKRunResult(
                command=command,
                mode=mode,
                effective_mode="raw",
                exit_code=exit_code,
                output=raw_output,
                raw_output=raw_output,
                raw_chars=len(raw_output),
                compressed_chars=len(raw_output),
                estimated_raw_tokens=raw_tokens,
                estimated_compressed_tokens=raw_tokens,
                token_reduction_percent=0.0,
                ambiguous_failure=False,
                raw_output_path=None,
                used_upstream_rtk=False,
            )
            if conn is not None:
                record_rtk_event(
                    conn,
                    result=result,
                    session_id=session_id,
                    run_id=run_id,
                    workflow_key=workflow_key,
                    source_kind=source_kind,
                )
            return result
    if used_upstream:
        compressed = raw_output
        ambiguous_failure = bool(exit_code != 0 and not ERROR_PATTERNS.search(raw_output))
    else:
        compressed, ambiguous_failure = compress_output(raw_output, command=command, exit_code=exit_code)

    effective_mode: RTKMode = "raw" if mode == "raw" else "compressed"
    raw_output_path = None
    output = compressed

    if mode == "raw":
        output = raw_output
    elif mode == "adaptive" and ambiguous_failure:
        raw_output_path = _write_raw_output(command, raw_output)
        output = f"{compressed}\n\n[raw output saved: {raw_output_path}]"
        effective_mode = "adaptive"
    elif exit_code != 0 and raw_output:
        raw_output_path = _write_raw_output(command, raw_output)
        if raw_output_path not in output:
            output = f"{output}\n\n[raw output saved: {raw_output_path}]"

    raw_tokens = estimate_tokens(raw_output)
    compressed_tokens = estimate_tokens(output)
    reduction = 0.0
    if raw_tokens > 0:
        reduction = round(max(0.0, (raw_tokens - compressed_tokens) / raw_tokens * 100), 2)

    result = RTKRunResult(
        command=command,
        mode=mode,
        effective_mode=effective_mode,
        exit_code=exit_code,
        output=output,
        raw_output=raw_output,
        raw_chars=len(raw_output),
        compressed_chars=len(output),
        estimated_raw_tokens=raw_tokens,
        estimated_compressed_tokens=compressed_tokens,
        token_reduction_percent=reduction,
        ambiguous_failure=ambiguous_failure,
        raw_output_path=raw_output_path,
        used_upstream_rtk=used_upstream,
    )
    if conn is not None:
        record_rtk_event(
            conn,
            result=result,
            session_id=session_id,
            run_id=run_id,
            workflow_key=workflow_key,
            source_kind=source_kind,
        )
    return result


def _passthrough_threshold(command: str, rules: dict[str, Any]) -> int:
    """Return the raw-char floor below which compression is skipped.

    Checks per-command-prefix thresholds first (written by rtk-tune-thresholds.py),
    then falls back to the global default.  A return value of 0 means always compress.
    """
    cmd = command.strip()
    per_prefix: dict[str, int] = rules.get("min_chars_by_prefix", {})
    for prefix, threshold in per_prefix.items():
        if cmd.startswith(prefix):
            return int(threshold)
    return int(rules.get("min_chars_to_compress", 200))


def compress_tool_output(
    *,
    command: str,
    raw_output: str,
    exit_code: int | None,
    mode: RTKMode = "compressed",
) -> RTKRunResult:
    rules = load_compression_rules()
    # Pass-through small outputs: compressor header overhead exceeds savings.
    # Threshold is tuned by rtk-tune-thresholds.py from empirical event data.
    if mode != "raw" and exit_code == 0:
        threshold = _passthrough_threshold(command, rules)
        if threshold > 0 and len(raw_output) < threshold:
            raw_tokens = estimate_tokens(raw_output)
            return RTKRunResult(
                command=command,
                mode=mode,
                effective_mode="raw",
                exit_code=exit_code or 0,
                output=raw_output,
                raw_output=raw_output,
                raw_chars=len(raw_output),
                compressed_chars=len(raw_output),
                estimated_raw_tokens=raw_tokens,
                estimated_compressed_tokens=raw_tokens,
                token_reduction_percent=0.0,
                ambiguous_failure=False,
                raw_output_path=None,
                used_upstream_rtk=False,
            )

    compressed, ambiguous_failure = compress_output(raw_output, command=command, exit_code=exit_code)
    raw_output_path = None
    output = raw_output if mode == "raw" else compressed
    effective_mode: RTKMode = "raw" if mode == "raw" else "compressed"
    if mode == "adaptive" and ambiguous_failure:
        raw_output_path = _write_raw_output(command, raw_output)
        output = f"{compressed}\n\n[raw output saved: {raw_output_path}]"
        effective_mode = "adaptive"
    elif mode != "raw" and exit_code and exit_code != 0 and raw_output:
        raw_output_path = _write_raw_output(command, raw_output)
        output = f"{compressed}\n\n[raw output saved: {raw_output_path}]"

    raw_tokens = estimate_tokens(raw_output)
    compressed_tokens = estimate_tokens(output)
    reduction = round(max(0.0, (raw_tokens - compressed_tokens) / raw_tokens * 100), 2) if raw_tokens else 0.0
    return RTKRunResult(
        command=command,
        mode=mode,
        effective_mode=effective_mode,
        exit_code=exit_code or 0,
        output=output,
        raw_output=raw_output,
        raw_chars=len(raw_output),
        compressed_chars=len(output),
        estimated_raw_tokens=raw_tokens,
        estimated_compressed_tokens=compressed_tokens,
        token_reduction_percent=reduction,
        ambiguous_failure=ambiguous_failure,
        raw_output_path=raw_output_path,
        used_upstream_rtk=False,
    )


def record_rtk_event(
    conn: sqlite3.Connection,
    *,
    result: RTKRunResult,
    source_kind: str,
    session_id: str | None = None,
    run_id: str | None = None,
    workflow_key: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    ensure_rtk_schema(conn)
    event_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO rtk_compression_events (
          id, session_id, run_id, workflow_key, source_kind, command, mode, effective_mode, exit_code,
          raw_chars, compressed_chars, estimated_raw_tokens, estimated_compressed_tokens,
          token_reduction_percent, ambiguous_failure, raw_output_path, metadata_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            session_id,
            run_id,
            workflow_key,
            source_kind,
            result.command,
            result.mode,
            result.effective_mode,
            result.exit_code,
            result.raw_chars,
            result.compressed_chars,
            result.estimated_raw_tokens,
            result.estimated_compressed_tokens,
            result.token_reduction_percent,
            1 if result.ambiguous_failure else 0,
            result.raw_output_path,
            json.dumps(metadata or {}, sort_keys=True),
        ),
    )
    if session_id:
        for metric_name, value in (
            ("rtk.raw_tokens", result.estimated_raw_tokens),
            ("rtk.compressed_tokens", result.estimated_compressed_tokens),
            ("rtk.tokens_saved", max(0, result.estimated_raw_tokens - result.estimated_compressed_tokens)),
            ("rtk.token_reduction_percent", result.token_reduction_percent),
        ):
            conn.execute(
                """
                INSERT INTO workflow_metrics (id, session_id, metric_name, metric_value, recorded_at, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    session_id,
                    metric_name,
                    float(value),
                    _now_iso(),
                    f"source={source_kind}; command={result.command[:120]}",
                ),
            )
    return event_id


def rtk_metrics_log(conn: sqlite3.Connection, *, session_id: str | None = None) -> dict[str, Any]:
    ensure_rtk_schema(conn)
    where = "WHERE session_id = ?" if session_id else ""
    params: tuple[str, ...] = (session_id,) if session_id else ()
    rows = conn.execute(
        f"""
        SELECT
          command,
          exit_code,
          raw_chars,
          estimated_raw_tokens,
          estimated_compressed_tokens,
          token_reduction_percent,
          ambiguous_failure
        FROM rtk_compression_events
        {where}
        """,
        params,
    ).fetchall()
    rules = load_compression_rules()
    total_event_count = len(rows)
    total_raw_tokens = sum(int(row["estimated_raw_tokens"]) for row in rows)
    total_compressed_tokens = sum(int(row["estimated_compressed_tokens"]) for row in rows)
    ambiguous_failures = sum(int(row["ambiguous_failure"]) for row in rows)

    eligible_rows = [
        row
        for row in rows
        if int(row["exit_code"] or 0) != 0
        or int(row["raw_chars"]) >= _passthrough_threshold(str(row["command"] or ""), rules)
    ]
    raw_tokens = sum(int(row["estimated_raw_tokens"]) for row in eligible_rows)
    compressed_tokens = sum(int(row["estimated_compressed_tokens"]) for row in eligible_rows)
    tokens_saved = sum(
        max(int(row["estimated_raw_tokens"]) - int(row["estimated_compressed_tokens"]), 0)
        for row in eligible_rows
    )
    regressive_count = sum(
        1
        for row in eligible_rows
        if int(row["estimated_compressed_tokens"]) > int(row["estimated_raw_tokens"])
    )
    average_reduction = (
        round(sum(float(row["token_reduction_percent"]) for row in eligible_rows) / len(eligible_rows), 2)
        if eligible_rows
        else 0.0
    )
    reduction = 0.0
    if raw_tokens:
        reduction = round(max(0, raw_tokens - compressed_tokens) / raw_tokens * 100, 2)
    return {
        "event_count": total_event_count,
        "eligible_event_count": len(eligible_rows),
        "passthrough_or_ineligible_event_count": total_event_count - len(eligible_rows),
        "raw_tokens": raw_tokens,
        "compressed_tokens": compressed_tokens,
        "tokens_saved": tokens_saved,
        "total_raw_tokens": total_raw_tokens,
        "total_compressed_tokens": total_compressed_tokens,
        "average_reduction_percent": average_reduction,
        "weighted_reduction_percent": reduction,
        "ambiguous_failures": ambiguous_failures,
        "regressive_count": regressive_count,
    }


def classify_rtk_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    event_count = int(metrics.get("eligible_event_count", metrics.get("event_count", 0)))
    raw_tokens = int(metrics.get("raw_tokens", 0))
    compressed_tokens = int(metrics.get("compressed_tokens", 0))
    tokens_saved = int(metrics.get("tokens_saved", 0))

    if event_count == 0:
        return {
            "state": "no_eligible_data",
            "benefit_state": "no_eligible_data",
            "explanation": "RTK is wired, but no eligible command output has produced telemetry.",
            "missing_reason": "No eligible command output has produced an RTK telemetry event.",
        }

    if tokens_saved > 0:
        return {
            "state": "active",
            "benefit_state": "beneficial",
            "explanation": "RTK has recorded compression events with positive net token savings.",
            "missing_reason": None,
        }

    if compressed_tokens > raw_tokens:
        return {
            "state": "token_regressive",
            "benefit_state": "token_regressive",
            "explanation": "RTK has recorded events, but compressed output is larger than raw output; treat this as no-benefit telemetry.",
            "missing_reason": None,
        }

    return {
        "state": "inactive",
        "benefit_state": "no_benefit",
        "explanation": "RTK has recorded events, but the current event set shows no positive token savings.",
        "missing_reason": None,
    }
