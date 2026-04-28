#!/usr/bin/env python3
"""
AIOS hook: PostToolUse
Logs tool events and detects artifact candidates.
"""

import json
import os
import re
import sqlite3
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rtk_integration import (  # noqa: E402
    compress_tool_output,
    load_compression_rules,
    record_rtk_event,
)

DB = os.path.expanduser("~/AIOS/data/aios.db")
LOG = os.path.expanduser("~/AIOS/logs/hooks.log")

# Tools whose outputs are worth tracking as artifacts
ARTIFACT_TOOLS = {"Write", "Edit", "MultiEdit", "Bash", "Task"}

# Error patterns that indicate a real bug (not noise like grep returning 0 results)
BUG_PATTERNS = re.compile(
    r"(Traceback \(most recent call last\)|"
    r"Error:|error:|SyntaxError|TypeError|ValueError|AttributeError|"
    r"ModuleNotFoundError|ImportError|NameError|KeyError|IndexError|"
    r"AssertionError|RuntimeError|FileNotFoundError|PermissionError|"
    r"FAILED|ENOENT|fatal:|command not found|No such file or directory|"
    r"npm ERR!|yarn error|tsc.*error TS|jest.*FAIL|pytest.*FAILED)",
    re.IGNORECASE,
)

# Patterns that indicate noise, not bugs
NOISE_PATTERNS = re.compile(
    r"^(usage:|help:|option|--help|warning:|hint:)",
    re.IGNORECASE | re.MULTILINE,
)

MIN_BUG_SYMPTOM_CHARS = 40


def log(msg: str) -> None:
    ts = datetime.now(UTC).isoformat()
    try:
        with open(LOG, "a") as f:
            f.write(f"{ts} [post-tool-use] {msg}\n")
    except Exception:
        pass


def extract_artifact(tool_name: str, tool_input: dict) -> dict | None:
    if tool_name in ("Write", "Edit", "MultiEdit"):
        path = tool_input.get("file_path", "")
        if path:
            return {"artifact_type": "patch", "path": path}
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")[:200]
        return {"artifact_type": "patch", "path": None, "metadata_json": json.dumps({"command": cmd})}
    return None


def parse_tool_response(raw) -> tuple[str, int | None]:
    """
    Normalise tool_response to (text, exit_code).
    Claude Code sends a dict for Bash; older/other formats send a plain string.
    """
    if isinstance(raw, dict):
        parts = []
        if raw.get("stderr"):
            parts.append(raw["stderr"])
        if raw.get("stdout"):
            parts.append(raw["stdout"])
        text = "\n".join(parts).strip()
        exit_code = raw.get("exit_code")
        return text, exit_code
    text = str(raw) if raw else ""
    return text, None


def detect_bug(tool_name: str, tool_input: dict, raw_response) -> str | None:
    """
    Returns a symptom string if this Bash response looks like a real bug, else None.
    """
    if tool_name != "Bash":
        return None
    text, exit_code = parse_tool_response(raw_response)
    cmd = tool_input.get("command", "")[:120]
    # Non-zero exit with no useful output → still worth recording
    if exit_code is not None and exit_code != 0 and not text:
        return f"Exit code {exit_code} [cmd: {cmd}]" if cmd else f"Exit code {exit_code}"
    if not text:
        return None
    # Non-zero exit: include exit code in symptom
    prefix = f"Exit code {exit_code}: " if (exit_code is not None and exit_code != 0) else ""
    if not BUG_PATTERNS.search(text) and not (exit_code is not None and exit_code != 0):
        return None
    if len(text) < MIN_BUG_SYMPTOM_CHARS and not prefix:
        return None
    if NOISE_PATTERNS.match(text.strip()):
        return None
    for line in text.splitlines():
        if BUG_PATTERNS.search(line) and len(line.strip()) > 10:
            symptom = (prefix + line.strip())[:300]
            return f"{symptom} [cmd: {cmd}]" if cmd else symptom
    symptom = (prefix + text.strip())[:300]
    return f"{symptom} [cmd: {cmd}]" if cmd else symptom


def query_matching_patterns(conn: sqlite3.Connection, symptom: str, cmd: str) -> list[dict]:
    """
    Find rules/hypotheses that are relevant to this error/command.
    Returns at most 3 matches, highest confidence first.
    Matches by keyword overlap between error text and pattern title/body.
    """
    # Extract 2-5 char tokens that are likely meaningful (skip stop words)
    STOP = {"the", "a", "an", "in", "on", "at", "is", "was", "for", "not", "and", "or",
            "to", "of", "it", "be", "by", "as", "if", "we", "do", "no", "so", "up",
            "cmd", "exit", "code", "error", "file"}
    combined = (symptom + " " + cmd).lower()
    tokens = {t for t in re.split(r"\W+", combined) if len(t) >= 4 and t not in STOP}
    if not tokens:
        return []

    try:
        rows = conn.execute(
            """SELECT id, title, body, confidence, state, class, domain
               FROM patterns
               WHERE state IN ('rule', 'hypothesis')
                 AND status != 'discarded'
                 AND confidence >= 0.4
               ORDER BY confidence DESC
               LIMIT 50"""
        ).fetchall()
    except Exception:
        return []

    scored = []
    for row in rows:
        text = ((row["title"] or "") + " " + (row["body"] or "")).lower()
        hits = sum(1 for t in tokens if t in text)
        if hits >= 2:
            scored.append((hits, dict(row)))

    scored.sort(key=lambda x: -x[0])
    return [r for _, r in scored[:3]]


def format_context_injection(patterns: list[dict], symptom: str) -> str:
    """
    Format matching patterns as a compact context block for Claude.
    Written to stdout — Claude Code PostToolUse hooks surface this as additional context.
    """
    lines = [
        "\n[AIOS] Relevant patterns for this error:",
    ]
    for p in patterns:
        state = p.get("state", "")
        conf  = p.get("confidence") or 0
        title = (p.get("title") or "")[:120]
        body  = (p.get("body") or "")[:160].strip()
        tag   = f"[{state} {conf:.0%}]"
        lines.append(f"  {tag} {title}")
        if body and body != title:
            lines.append(f"        → {body}")
    return "\n".join(lines)


def format_rtk_context(result) -> str:
    lines = [
        "\n[AIOS RTK] compressed command output:",
        result.output,
        (
            f"\n[AIOS RTK] tokens: {result.estimated_raw_tokens} -> "
            f"{result.estimated_compressed_tokens} "
            f"({result.token_reduction_percent:.1f}% reduction)"
        ),
    ]
    if result.raw_output_path:
        lines.append(f"[AIOS RTK] raw output: {result.raw_output_path}")
    return "\n".join(lines)


def get_project_id(conn: sqlite3.Connection, session_id: str) -> str:
    try:
        cur = conn.execute("SELECT project_id FROM sessions WHERE id = ?", (session_id,))
        row = cur.fetchone()
        return row[0] if row else ""
    except Exception:
        return ""


def bug_already_logged(conn: sqlite3.Connection, session_id: str, symptom: str) -> bool:
    """Prevent duplicate entries for the same error within one session."""
    try:
        cur = conn.execute(
            "SELECT 1 FROM bug_log WHERE session_id = ? AND symptom = ? LIMIT 1",
            (session_id, symptom),
        )
        return cur.fetchone() is not None
    except Exception:
        return False


def _safe_load_stdin() -> dict:
    """Read stdin and parse JSON, sanitizing control characters that Claude Code
    embeds in tool_response output (newlines in strings become literal \n etc.)."""
    raw = sys.stdin.buffer.read()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Attempt recovery: replace unescaped control characters inside string values.
    # Decode with replacement so we don't crash on bad bytes.
    text = raw.decode("utf-8", errors="replace")
    # Replace literal control chars (except \t \n \r which are valid JSON whitespace
    # outside strings — inside strings they must be escaped).
    # Strategy: use a regex to find string values and escape control chars within them.
    import re
    _CTRL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')

    def _escape_string(m: re.Match) -> str:
        return _CTRL.sub(lambda c: f"\\u{ord(c.group()):04x}", m.group())

    # Match JSON string tokens and sanitize their contents
    sanitized = re.sub(r'"(?:[^"\\]|\\.)*"', _escape_string, text)
    try:
        return json.loads(sanitized)
    except json.JSONDecodeError:
        # Last resort: strip all non-ASCII-printable chars
        clean = "".join(c if c >= " " or c in "\t\n\r" else " " for c in text)
        return json.loads(clean)


def main() -> None:
    try:
        data = _safe_load_stdin()
    except Exception as e:
        log(f"failed to parse stdin: {e}")
        sys.exit(0)

    session_id = data.get("session_id", "")
    tool_name = data.get("tool_name", "")

    if not session_id:
        sys.exit(0)

    try:
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
        if not cur.fetchone():
            conn.close()
            sys.exit(0)

        now = datetime.now(UTC).isoformat()

        # Log the event (strip large response bodies to keep DB small)
        payload = {
            "tool_name": tool_name,
            "tool_input_keys": list((data.get("tool_input") or {}).keys()),
        }
        conn.execute(
            """
            INSERT INTO tool_events (id, session_id, source_tool, event_type, event_time, payload_json)
            VALUES (?, ?, 'claude-code', 'PostToolUse', ?, ?)
            """,
            (str(uuid.uuid4()), session_id, now, json.dumps(payload)),
        )

        # Detect artifact candidate
        if tool_name in ARTIFACT_TOOLS:
            artifact = extract_artifact(tool_name, data.get("tool_input") or {})
            if artifact:
                conn.execute(
                    """
                    INSERT INTO artifacts (id, session_id, artifact_type, path, metadata_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        session_id,
                        artifact["artifact_type"],
                        artifact.get("path"),
                        artifact.get("metadata_json"),
                        now,
                    ),
                )

        # Auto-capture bugs from Bash failures
        tool_response = data.get("tool_response")
        rtk_result = None
        if tool_name == "Bash":
            command = (data.get("tool_input") or {}).get("command", "")
            raw_text, exit_code = parse_tool_response(tool_response)
            if raw_text:
                rules = load_compression_rules()
                mode = rules.get("default_mode", "compressed")
                if exit_code is not None and exit_code != 0:
                    mode = "adaptive"
                if mode not in {"compressed", "raw", "adaptive"}:
                    mode = "compressed"
                rtk_result = compress_tool_output(
                    command=command,
                    raw_output=raw_text,
                    exit_code=exit_code,
                    mode=mode,
                )
                record_rtk_event(
                    conn,
                    result=rtk_result,
                    session_id=session_id,
                    source_kind="PostToolUse",
                    metadata={"hook": "post-tool-use", "tool_name": tool_name},
                )

        symptom = detect_bug(tool_name, data.get("tool_input") or {}, tool_response)
        if symptom:
            project_id = get_project_id(conn, session_id)
            if not bug_already_logged(conn, session_id, symptom):
                bug_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO bug_log (id, session_id, project_id, symptom, status, promoted, created_at)
                    VALUES (?, ?, ?, ?, 'promoted', 1, ?)
                    """,
                    (bug_id, session_id, project_id or None, symptom, now),
                )
                # Check if this error pattern already exists (same title) from a prior session
                title = symptom[:200]
                existing = conn.execute(
                    """SELECT id, confirmation_count FROM patterns
                       WHERE title=? AND source_type='tool-error' AND status!='discarded' LIMIT 1""",
                    (title,),
                ).fetchone()
                if existing:
                    # Auto-confirm: same error recurred in a new session
                    new_count = (existing["confirmation_count"] or 0) + 1
                    conn.execute(
                        "UPDATE patterns SET confirmation_count=?, confidence=MIN(confidence+0.05,0.95) WHERE id=?",
                        (new_count, existing["id"]),
                    )
                    conn.execute(
                        """INSERT INTO pattern_events
                               (id, pattern_id, event_type, session_id, source_type, event_time)
                           VALUES (?, ?, 'confirmation', ?, 'tool-error', ?)""",
                        (str(uuid.uuid4()), existing["id"], session_id, now),
                    )
                    log(f"bug auto-confirmed (recurrence #{new_count}): {title[:60]}")
                else:
                    # New error — surface in pattern review with body pre-filled
                    conn.execute(
                        """
                        INSERT INTO patterns
                            (id, class, domain, title, body, evidence, confidence, state,
                             status, source_type, first_observed_at, created_at, project_id)
                        VALUES (?, 'error', 'tooling', ?, ?, ?, 0.3, 'observation',
                                'candidate', 'tool-error', ?, ?, ?)
                        """,
                        (
                            str(uuid.uuid4()),
                            title,
                            symptom,
                            json.dumps([{"bug_id": bug_id, "session_id": session_id}]),
                            now,
                            now,
                            project_id or None,
                        ),
                    )
                    log(f"bug auto-captured: {title[:60]}")

        # ── Reactive context injection ────────────────────────────────────────
        # If a bug was detected, surface matching patterns to Claude via stdout.
        # Claude Code PostToolUse hooks: stdout is surfaced as additional context.
        if symptom:
            try:
                matches = query_matching_patterns(
                    conn, symptom, (data.get("tool_input") or {}).get("command", "")
                )
                if matches:
                    print(format_context_injection(matches, symptom))
            except Exception:
                pass  # never let context injection block the hook

        if rtk_result and (
            rtk_result.estimated_raw_tokens >= 200
            or rtk_result.exit_code != 0
            or rtk_result.ambiguous_failure
        ):
            print(format_rtk_context(rtk_result))

        conn.commit()
        conn.close()
    except Exception as e:
        log(f"db error: {e}")


if __name__ == "__main__":
    main()
