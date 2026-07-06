#!/usr/bin/env python3
"""
AIOS: score-patterns.py
Compute frequency_score + impact_score for all patterns, then auto-promote/demote.

Frequency score (0-1): how often/widely this pattern has been seen
Impact score (0-1):    how significant the signal source is

Gates:
  notice     → hypothesis: freq >= 0.3 OR impact >= 0.6
  hypothesis → rule:       freq >= 0.5 AND impact >= 0.4 AND body IS NOT NULL
  rule       → hypothesis: last_seen_at older than 60 days AND freq < 0.2 (demotion)

Run: python3 ~/AIOS/bin/score-patterns.py [--dry-run]
"""

import argparse
import os
import sqlite3
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

DB = os.path.expanduser("~/AIOS/data/aios.db")
BIN = Path(__file__).parent

# Impact weight by source type
IMPACT_BASE = {
    "handoff-learned": 0.55,
    "manual": 0.80,
    "tool-error": 0.40,
    "agent-synthesis": 0.30,
    "bigram": 0.05,
}

# Frequency score: normalised against these ceilings
FREQ_SESSION_CEIL = 10  # source_sessions ceiling for normalisation
FREQ_CONFIRM_CEIL = 8  # confirmation_count ceiling
FREQ_COUNT_CEIL = 20  # frequency_count ceiling

DEMOTION_DAYS = 60

# Recency decay: patterns not seen in this many days get a multiplier < 1
RECENCY_HALF_LIFE_DAYS = 90  # score halves every 90 days of silence


def now() -> str:
    return datetime.now(UTC).isoformat()


def _recency_multiplier(last_seen_at: str | None) -> float:
    """Return a 0.0–1.0 multiplier based on days since last observation."""
    if not last_seen_at:
        return 0.5  # no timestamp — moderate penalty
    try:
        last = datetime.fromisoformat(last_seen_at.rstrip("Z"))
        if last.tzinfo is None:
            last = last.replace(tzinfo=UTC)
        days_silent = (datetime.now(UTC) - last).days
        # Exponential decay: multiplier = 0.5 ^ (days / half_life)
        return round(0.5 ** (days_silent / RECENCY_HALF_LIFE_DAYS), 4)
    except Exception:
        return 1.0


def compute_scores(p: dict) -> tuple[float, float]:
    """Return (frequency_score, impact_score) for a pattern row."""

    # --- frequency (with recency decay) ---
    sessions_norm = min((p["source_sessions"] or 0) / FREQ_SESSION_CEIL, 1.0)
    confirm_norm = min((p["confirmation_count"] or 0) / FREQ_CONFIRM_CEIL, 1.0)
    count_norm = min((p["frequency_count"] or 0) / FREQ_COUNT_CEIL, 1.0)
    raw_freq = (sessions_norm * 0.5) + (confirm_norm * 0.3) + (count_norm * 0.2)
    # Apply recency decay to raw frequency — recently-active patterns score higher
    decay = _recency_multiplier(p.get("last_seen_at"))
    freq = round(raw_freq * decay, 4)

    # --- impact ---
    base = IMPACT_BASE.get(p["source_type"] or "", 0.2)
    # cross-project bonus: project_id is None means it appeared globally
    cross = 0.10 if not p.get("project_id") else 0.0
    # body quality: has actionable body text
    body_ok = 0.10 if (p.get("body") or "").strip() else 0.0
    # contradiction penalty
    contra = min((p["contradiction_count"] or 0) * 0.10, 0.30)
    impact = min(base + cross + body_ok - contra, 1.0)

    return round(freq, 4), round(impact, 4)


def _trigger_lab_pipeline(p: dict, conn: sqlite3.Connection) -> None:
    """Create rule artifact and generate eval bundle for a newly promoted rule."""
    try:
        import importlib.util as _ilu

        spec = _ilu.spec_from_file_location("rule_artifacts", BIN / "rule-artifacts.py")
        _ra = _ilu.module_from_spec(spec)
        spec.loader.exec_module(_ra)
        create_artifact = _ra.create_artifact
        write_artifact = _ra.write_artifact
        artifact = create_artifact(p)
        write_artifact(artifact)
        conn.execute("UPDATE patterns SET lab_status='pending' WHERE id=?", (p["id"],))
        # Generate bundle in a subprocess to keep score-patterns.py fast
        subprocess.Popen(
            ["python3", str(BIN / "generate-rule-bundle.py"), "--pattern-id", p["id"]],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"    → artifact created, bundle generation dispatched for {p['id'][:8]}")
    except Exception as exc:
        print(f"    [warn] lab pipeline trigger failed: {exc}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    patterns = conn.execute("SELECT * FROM patterns WHERE status != 'discarded'").fetchall()

    promoted = {"notice→hypothesis": 0, "hypothesis→rule": 0}
    demoted = {"rule→hypothesis": 0}
    scored = 0
    cutoff_str = (datetime.now(UTC) - timedelta(days=DEMOTION_DAYS)).isoformat()

    for row in patterns:
        p = dict(row)
        freq, impact = compute_scores(p)

        if not args.dry_run:
            conn.execute(
                "UPDATE patterns SET frequency_score=?, impact_score=? WHERE id=?",
                (freq, impact, p["id"]),
            )
        scored += 1

        state = p["state"]
        new_state = state

        if state == "notice":
            # Must appear more than once, OR single very high-impact source (manual/cross-project)
            multi_session = (p.get("source_sessions") or 0) >= 2
            high_impact_single = impact >= 0.75 and (p.get("frequency_count") or 0) >= 1
            if multi_session or (freq >= 0.3 and impact >= 0.4) or high_impact_single:
                new_state = "hypothesis"
                promoted["notice→hypothesis"] += 1

        elif state == "hypothesis":
            # Needs cross-session evidence, decent frequency, and actionable body
            if (
                (p.get("source_sessions") or 0) >= 2
                and freq >= 0.4
                and impact >= 0.4
                and (p.get("body") or "").strip()
            ):
                new_state = "rule"
                promoted["hypothesis→rule"] += 1

        elif state == "rule":
            last_seen = p.get("last_seen_at") or p.get("first_observed_at") or ""
            if last_seen < cutoff_str and freq < 0.2:
                new_state = "hypothesis"
                demoted["rule→hypothesis"] += 1

        if new_state != state:
            tag = "[DRY] " if args.dry_run else ""
            print(f"  {tag}{state} → {new_state}: {p['title'][:80]!r}")
            if not args.dry_run:
                extra = (
                    ", human_approved=0" if new_state == "hypothesis" and state == "rule" else ""
                )
                conn.execute(
                    f"UPDATE patterns SET state=?{extra} WHERE id=?",
                    (new_state, p["id"]),
                )
                # On hypothesis→rule promotion, create rule artifact and generate eval bundle
                if new_state == "rule":
                    _trigger_lab_pipeline(p, conn)

    if not args.dry_run:
        conn.commit()

    conn.close()
    prefix = "[DRY RUN] " if args.dry_run else ""
    print(f"\n{prefix}Scored {scored} patterns")
    print(f"  notice → hypothesis: {promoted['notice→hypothesis']}")
    print(f"  hypothesis → rule:   {promoted['hypothesis→rule']}")
    print(f"  rule → hypothesis:   {demoted['rule→hypothesis']} (demoted)")


if __name__ == "__main__":
    main()
