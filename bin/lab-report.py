#!/usr/bin/env python3
"""
AIOS: lab-report.py
Summarize lab experiment results from aios.db.

Usage:
  python3 ~/AIOS/bin/lab-report.py
  python3 ~/AIOS/bin/lab-report.py --pattern-id <id>
  python3 ~/AIOS/bin/lab-report.py --outcome confirmed
  python3 ~/AIOS/bin/lab-report.py --patch-type verification_toggle
"""
import argparse
import os
import sqlite3
from collections import defaultdict

DB = os.path.expanduser("~/AIOS/data/aios.db")

OUTCOMES = {"confirmed", "contradicted", "inconclusive", "error"}


def _pct(n: int, total: int) -> str:
    return f"{100*n//total}%" if total else "—"


def _fmt_delta(v) -> str:
    if v is None:
        return "    N/A"
    return f"{v:+.3f}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pattern-id", help="Filter to one pattern")
    parser.add_argument("--outcome", choices=list(OUTCOMES), help="Filter by outcome")
    parser.add_argument("--patch-type", help="Filter by patch type")
    parser.add_argument("--limit", type=int, default=50, help="Max rows to show (default 50)")
    args = parser.parse_args()

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    # Build query
    where = []
    params = []
    if args.pattern_id:
        where.append("r.pattern_id = ?")
        params.append(args.pattern_id)
    if args.outcome:
        where.append("r.outcome = ?")
        params.append(args.outcome)
    if args.patch_type:
        where.append("r.patch_type = ?")
        params.append(args.patch_type)

    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    runs = conn.execute(
        f"""
        SELECT r.*, p.title, p.capability_class
        FROM lab_runs r
        LEFT JOIN (
            SELECT id,
                   title,
                   -- capability_class not stored on patterns, use lab_runs table
                   NULL AS capability_class
            FROM patterns
        ) p ON r.pattern_id = p.id
        {where_clause}
        ORDER BY r.created_at DESC
        LIMIT ?
        """,
        params + [args.limit],
    ).fetchall()

    # ── Aggregate stats ──────────────────────────────────────────────────────
    all_runs = conn.execute("SELECT * FROM lab_runs").fetchall()
    total = len(all_runs)

    by_outcome: dict[str, list] = defaultdict(list)
    by_patch:   dict[str, list] = defaultdict(list)
    for r in all_runs:
        by_outcome[r["outcome"] or "unknown"].append(r)
        by_patch[r["patch_type"] or "unknown"].append(r)

    print("=" * 65)
    print("AIOS Lab Report")
    print("=" * 65)
    print(f"Total experiments: {total}")
    if total:
        print()
        print("Outcome breakdown:")
        for outcome in ["confirmed", "contradicted", "inconclusive", "error"]:
            n = len(by_outcome.get(outcome, []))
            bar = "█" * (n * 20 // total) if total else ""
            print(f"  {outcome:<16} {n:>4}  {_pct(n,total):>4}  {bar}")

        print()
        print("By patch type:")
        for pt, pt_runs in sorted(by_patch.items()):
            confirmed = sum(1 for r in pt_runs if r["outcome"] == "confirmed")
            deltas = [r["score_delta"] for r in pt_runs if r["score_delta"] is not None]
            avg_delta = sum(deltas) / len(deltas) if deltas else None
            print(f"  {pt:<28}  runs={len(pt_runs):<4} "
                  f"confirmed={confirmed:<4} "
                  f"avg_delta={_fmt_delta(avg_delta)}")

    # ── Per-run table ────────────────────────────────────────────────────────
    print()
    print(f"{'Run ID':<28} {'Patch':<24} {'Core Δ':>8} {'Hold Δ':>8} {'Micro Δ':>8} {'Outcome'}")
    print("-" * 90)
    for r in runs:
        run_id   = (r["id"] or "")[:27]
        patch    = (r["patch_type"] or "")[:23]
        core_d   = _fmt_delta(r["score_delta"])
        hold_d   = _fmt_delta(r["holdout_delta"])
        micro_d  = _fmt_delta(r["micro_delta"])
        outcome  = (r["outcome"] or "").upper()
        print(f"{run_id:<28} {patch:<24} {core_d:>8} {hold_d:>8} {micro_d:>8}  {outcome}")

    if not runs:
        print("  (no runs match filters)")

    conn.close()


if __name__ == "__main__":
    main()
