from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from typing import Literal, TypedDict

PatternDecision = Literal["approve", "reject"]
MUTABLE_FIELDS = {"id", "decision"}


class PatternApprovalUpdate(TypedDict):
    ok: bool
    id: str
    changed_rows: int


def _required_id(payload: Mapping[str, object]) -> str:
    value = payload.get("id")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("id is required")
    if len(value) > 200:
        raise ValueError("id exceeds the 200-character limit")
    return value


def _validate_payload(payload: Mapping[str, object]) -> tuple[str, PatternDecision]:
    unknown = set(payload) - MUTABLE_FIELDS
    if unknown:
        names = ", ".join(sorted(str(name) for name in unknown))
        raise ValueError(f"Unsupported pattern approval fields: {names}")

    pattern_id = _required_id(payload)
    decision = payload.get("decision")
    if decision not in ("approve", "reject"):
        raise ValueError("decision must be one of: approve, reject")
    return pattern_id, decision


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
        (name,),
    ).fetchone()
    return row is not None


def update_pattern_approval(
    conn: sqlite3.Connection,
    payload: Mapping[str, object],
) -> PatternApprovalUpdate:
    """Apply one pattern approval decision as the Python owner."""

    pattern_id, decision = _validate_payload(payload)
    if not _table_exists(conn, "patterns"):
        return {"ok": False, "id": pattern_id, "changed_rows": 0}

    if decision == "approve":
        statement = """
            UPDATE patterns
            SET human_approved = 1,
                state = 'rule',
                status = 'active',
                promoted_at = COALESCE(promoted_at, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            WHERE id = ?
        """
    else:
        statement = """
            UPDATE patterns
            SET human_approved = 0,
                status = 'discarded'
            WHERE id = ?
        """

    with conn:
        result = conn.execute(statement, (pattern_id,))
    changed_rows = max(0, int(result.rowcount))
    return {"ok": changed_rows > 0, "id": pattern_id, "changed_rows": changed_rows}
