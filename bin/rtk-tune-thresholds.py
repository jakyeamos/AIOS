#!/usr/bin/env python3
"""
AIOS: rtk-tune-thresholds.py
Analyse rtk_compression_events and write empirical per-prefix
min_chars_to_compress thresholds back into config/rtk/rules.json.

Algorithm per command prefix:
  1. Collect all successful (exit_code=0) events for this prefix.
  2. Sort by raw_chars ascending.
  3. Walk the sorted list; find the smallest raw_chars value where the
     rolling median token_reduction_percent crosses 0 (i.e. compression
     starts saving tokens).  Call that the breakeven.
  4. Write breakeven * SAFETY_MARGIN as the threshold, rounded up to
     the nearest 50 chars to avoid noisy micro-updates.

Requires at least MIN_EVENTS events per prefix before writing a threshold.
Prefixes with insufficient data are left at the global default.

Usage:
  python3 ~/AIOS/bin/rtk-tune-thresholds.py [--db PATH] [--dry-run] [--verbose]

Cron: run weekly after enough events accumulate.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "aios.db"
RULES_PATH = ROOT / "config" / "rtk" / "rules.json"

# Minimum events needed per prefix before we trust the data
MIN_EVENTS = 20
# Multiply empirical breakeven by this before writing (conservative buffer)
SAFETY_MARGIN = 1.2
# Round threshold up to nearest N chars (avoids micro-updates on re-runs)
ROUND_TO = 50

# Command prefixes to analyse — ordered longest-first so more-specific
# prefixes match before general ones.
COMMAND_PREFIXES = [
    "pnpm test",
    "pnpm build",
    "pnpm lint",
    "pnpm typecheck",
    "pnpm tsc",
    "pnpm ",
    "npm run test",
    "npm run build",
    "npm run",
    "npm ",
    "pytest",
    "python3 -m pytest",
    "ruff check",
    "ruff format",
    "ruff ",
    "basedpyright",
    "mypy",
    "tsc ",
    "eslint",
    "git diff",
    "git log",
    "git show",
    "git status",
    "git ",
    "docker ",
    "cargo test",
    "cargo build",
    "cargo ",
    "find ",
    "ls ",
    "cat ",
    "grep ",
    "rg ",
    "sqlite3 ",
    "python3 ",
    "node ",
    "bash ",
    "sh ",
]


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def _round_up(value: float, step: int) -> int:
    return int(math.ceil(value / step) * step)


def _prefix_for(command: str) -> str | None:
    cmd = command.strip()
    for prefix in COMMAND_PREFIXES:
        if cmd.startswith(prefix):
            return prefix
    return None


def load_events(db_path: Path) -> list[dict]:
    if not db_path.exists():
        print(f"ERROR: DB not found: {db_path}", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT command, raw_chars, estimated_raw_tokens,
                   estimated_compressed_tokens, token_reduction_percent, exit_code
            FROM rtk_compression_events
            WHERE exit_code = 0
              AND command IS NOT NULL
              AND raw_chars > 0
            ORDER BY raw_chars ASC
            """
        ).fetchall()
    except sqlite3.OperationalError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()
    return [dict(row) for row in rows]


def analyse(events: list[dict], verbose: bool = False) -> dict[str, int]:
    """Return {prefix: threshold_chars} for prefixes with enough data."""
    by_prefix: dict[str, list[dict]] = defaultdict(list)
    unmatched = 0
    for ev in events:
        prefix = _prefix_for(ev["command"] or "")
        if prefix:
            by_prefix[prefix].append(ev)
        else:
            unmatched += 1

    if verbose:
        print(f"  Unmatched events (no prefix): {unmatched}")

    thresholds: dict[str, int] = {}

    for prefix in COMMAND_PREFIXES:
        evs = by_prefix.get(prefix, [])
        if len(evs) < MIN_EVENTS:
            if verbose:
                print(f"  [{prefix!r:<32}] skip — only {len(evs)} events (need {MIN_EVENTS})")
            continue

        # Sort by raw_chars (already sorted from DB but group may not be)
        evs_sorted = sorted(evs, key=lambda e: e["raw_chars"])

        # Find breakeven: smallest raw_chars window where rolling median reduction > 0
        # Use a sliding window of min(10, len/3) events
        window = max(5, min(10, len(evs_sorted) // 3))
        breakeven_chars: int | None = None

        for i in range(len(evs_sorted) - window + 1):
            chunk = evs_sorted[i : i + window]
            reductions = [e["token_reduction_percent"] for e in chunk]
            if _median(reductions) > 0:
                breakeven_chars = chunk[0]["raw_chars"]
                break

        if breakeven_chars is None:
            # Compression never helps for this prefix — set a high threshold
            # (just below max observed, so we still compress truly large outputs)
            max_chars = evs_sorted[-1]["raw_chars"]
            threshold = _round_up(max_chars * 0.9, ROUND_TO)
            if verbose:
                print(
                    f"  [{prefix!r:<32}] no breakeven found — "
                    f"threshold={threshold} (compression rarely helps)"
                )
        else:
            raw_threshold = breakeven_chars * SAFETY_MARGIN
            threshold = _round_up(raw_threshold, ROUND_TO)
            if verbose:
                n = len(evs_sorted)
                median_reduction = _median([e["token_reduction_percent"] for e in evs_sorted])
                print(
                    f"  [{prefix!r:<32}] n={n:>4}  breakeven={breakeven_chars:>6}  "
                    f"threshold={threshold:>6}  median_reduction={median_reduction:.1f}%"
                )

        thresholds[prefix] = threshold

    return thresholds


def apply_thresholds(thresholds: dict[str, int], dry_run: bool, verbose: bool) -> None:
    rules: dict = {}
    if RULES_PATH.exists():
        rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))

    old_by_prefix: dict[str, int] = rules.get("min_chars_by_prefix", {})
    changed: list[str] = []
    new_by_prefix = dict(old_by_prefix)

    for prefix, threshold in thresholds.items():
        old = old_by_prefix.get(prefix)
        if old != threshold:
            changed.append(f"  {prefix!r:<34} {old or '(new)':>8} → {threshold}")
        new_by_prefix[prefix] = threshold

    if not changed:
        print("No threshold changes needed.")
        return

    print(f"{'[DRY RUN] ' if dry_run else ''}Threshold changes:")
    for line in changed:
        print(line)

    if dry_run:
        return

    rules["min_chars_by_prefix"] = new_by_prefix
    RULES_PATH.write_text(json.dumps(rules, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Written → {RULES_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Tune RTK compression thresholds from event data.")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Path to aios.db")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print changes without writing rules.json"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Show per-prefix breakdown")
    args = parser.parse_args()

    print(f"Loading RTK events from {args.db}...")
    events = load_events(Path(args.db))
    print(f"  {len(events)} successful events loaded.")

    if len(events) < MIN_EVENTS:
        print(
            f"  Insufficient data — need at least {MIN_EVENTS} events total. Collect more data first."
        )
        sys.exit(0)

    print("Analysing per-prefix breakeven points...")
    thresholds = analyse(events, verbose=args.verbose)
    print(f"  {len(thresholds)} prefix(es) with enough data.")

    apply_thresholds(thresholds, dry_run=args.dry_run, verbose=args.verbose)


if __name__ == "__main__":
    main()
