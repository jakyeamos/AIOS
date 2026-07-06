#!/usr/bin/env python3
"""
token-audit.py — Comprehensive Claude Code token usage analysis.

Reads all JSONL transcripts from ~/.claude/projects/, aggregates
input/output/cache tokens per project and per session, then prints
a breakdown with cost estimates (Sonnet 4.6 pricing).
"""

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

# ── Pricing (USD per 1M tokens, Sonnet 4.6) ──────────────────────────────────
PRICE = {
    "input": 3.00,
    "output": 15.00,
    "cache_write": 3.75,  # ephemeral cache creation
    "cache_read": 0.30,
}

# ── Helpers ───────────────────────────────────────────────────────────────────


def cost(inp, out, cache_write, cache_read):
    return (
        inp * PRICE["input"] / 1_000_000
        + out * PRICE["output"] / 1_000_000
        + cache_write * PRICE["cache_write"] / 1_000_000
        + cache_read * PRICE["cache_read"] / 1_000_000
    )


def project_label(path: Path) -> str:
    """Convert ~/.claude/projects/<slug>/<file> → readable project name."""
    slug = path.parent.name
    # strip leading '-Users-jakyeamos-' or '-Users-jakyeamos'
    label = slug.replace("-Users-jakyeamos-", "").replace("-Users-jakyeamos", "")
    return label or "(home)"


def fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def bar(pct: float, width: int = 20) -> str:
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


# ── Parse transcripts ─────────────────────────────────────────────────────────


class SessionStats:
    __slots__ = (
        "project",
        "session_id",
        "jsonl_path",
        "inp",
        "out",
        "cache_write",
        "cache_read",
        "turns",
        "first_ts",
        "last_ts",
        "models",
    )

    def __init__(self, project, session_id, jsonl_path):
        self.project = project
        self.session_id = session_id
        self.jsonl_path = jsonl_path
        self.inp = self.out = self.cache_write = self.cache_read = 0
        self.turns = 0
        self.first_ts = self.last_ts = None
        self.models = set()

    @property
    def total_tokens(self):
        return self.inp + self.out + self.cache_write + self.cache_read

    @property
    def cost_usd(self):
        return cost(self.inp, self.out, self.cache_write, self.cache_read)

    def merge_usage(self, usage: dict):
        self.inp += usage.get("input_tokens", 0)
        self.out += usage.get("output_tokens", 0)
        self.cache_write += usage.get("cache_creation_input_tokens", 0)
        self.cache_read += usage.get("cache_read_input_tokens", 0)
        self.turns += 1


def scan_projects(claude_dir: Path) -> list[SessionStats]:
    sessions: list[SessionStats] = []
    projects_dir = claude_dir / "projects"
    if not projects_dir.exists():
        print(f"ERROR: {projects_dir} not found", file=sys.stderr)
        sys.exit(1)

    seen_sessions: set[str] = set()

    for jsonl_file in sorted(projects_dir.rglob("*.jsonl")):
        session_id = jsonl_file.stem
        if session_id in seen_sessions:
            continue
        seen_sessions.add(session_id)

        project = project_label(jsonl_file)
        stats = SessionStats(project, session_id, str(jsonl_file))

        try:
            with open(jsonl_file, encoding="utf-8") as f:
                for raw in f:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        obj = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    msg = obj.get("message") or {}
                    usage = msg.get("usage")
                    if usage:
                        stats.merge_usage(usage)

                    model = msg.get("model")
                    if model:
                        stats.models.add(model)

                    ts = obj.get("timestamp")
                    if ts:
                        if stats.first_ts is None or ts < stats.first_ts:
                            stats.first_ts = ts
                        if stats.last_ts is None or ts > stats.last_ts:
                            stats.last_ts = ts

        except (OSError, PermissionError) as e:
            print(f"  WARN: cannot read {jsonl_file}: {e}", file=sys.stderr)
            continue

        if stats.total_tokens > 0:
            sessions.append(stats)

    return sessions


# ── Aggregation ───────────────────────────────────────────────────────────────


def aggregate_by_project(sessions: list[SessionStats]) -> dict:
    proj: dict = defaultdict(
        lambda: dict(inp=0, out=0, cache_write=0, cache_read=0, sessions=0, turns=0)
    )
    for s in sessions:
        p = proj[s.project]
        p["inp"] += s.inp
        p["out"] += s.out
        p["cache_write"] += s.cache_write
        p["cache_read"] += s.cache_read
        p["sessions"] += 1
        p["turns"] += s.turns
    return dict(proj)


# ── Reporting ─────────────────────────────────────────────────────────────────

SEP = "─" * 100


def print_section(title: str):
    print(f"\n{'━' * 100}")
    print(f"  {title}")
    print("━" * 100)


def report(sessions: list[SessionStats]):
    if not sessions:
        print("No token data found.")
        return

    by_project = aggregate_by_project(sessions)
    grand = dict(inp=0, out=0, cache_write=0, cache_read=0, sessions=0, turns=0)
    for p in by_project.values():
        for k in grand:
            grand[k] += p[k]

    grand_total_tok = grand["inp"] + grand["out"] + grand["cache_write"] + grand["cache_read"]
    grand_cost = cost(grand["inp"], grand["out"], grand["cache_write"], grand["cache_read"])

    # ── Header ────────────────────────────────────────────────────────────────
    print_section("TOKEN USAGE AUDIT  —  All Claude Code projects")
    print(f"  Scanned : {len(sessions)} sessions across {len(by_project)} projects")
    print(f"  Total   : {fmt_tokens(grand_total_tok)} tokens   est. ${grand_cost:.4f} USD")
    print(
        f"  Pricing : Sonnet 4.6  (input ${PRICE['input']}/Mtok · output ${PRICE['output']}/Mtok · "
        f"cache-write ${PRICE['cache_write']}/Mtok · cache-read ${PRICE['cache_read']}/Mtok)"
    )

    # ── Token composition ─────────────────────────────────────────────────────
    print_section("TOKEN COMPOSITION")
    components = [
        ("Input (fresh)", grand["inp"], "input"),
        ("Output", grand["out"], "output"),
        ("Cache write", grand["cache_write"], "cache_write"),
        ("Cache read", grand["cache_read"], "cache_read"),
    ]
    for label, tokens, pkey in components:
        pct = tokens / grand_total_tok * 100 if grand_total_tok else 0
        c = cost(
            tokens if pkey == "input" else 0,
            tokens if pkey == "output" else 0,
            tokens if pkey == "cache_write" else 0,
            tokens if pkey == "cache_read" else 0,
        )
        print(f"  {label:<18} {bar(pct)}  {pct:5.1f}%   {fmt_tokens(tokens):>8}   ${c:.4f}")

    cache_savings = grand["cache_read"] * (PRICE["input"] - PRICE["cache_read"]) / 1_000_000
    if grand["cache_read"] > 0:
        print(f"\n  Cache savings : ~${cache_savings:.4f} vs full input pricing")

    # ── By project ────────────────────────────────────────────────────────────
    print_section("BY PROJECT  (sorted by total tokens)")
    ranked = sorted(
        by_project.items(),
        key=lambda kv: kv[1]["inp"] + kv[1]["out"] + kv[1]["cache_write"] + kv[1]["cache_read"],
        reverse=True,
    )

    hdr = f"  {'PROJECT':<35} {'SESSIONS':>8} {'TURNS':>6} {'INPUT':>9} {'OUTPUT':>9} {'CACHE-W':>9} {'CACHE-R':>9} {'TOTAL':>10} {'COST':>10}"
    print(hdr)
    print(f"  {SEP}")

    for proj_name, p in ranked:
        tot = p["inp"] + p["out"] + p["cache_write"] + p["cache_read"]
        c = cost(p["inp"], p["out"], p["cache_write"], p["cache_read"])
        pct = tot / grand_total_tok * 100 if grand_total_tok else 0
        name = (proj_name[:33] + "..") if len(proj_name) > 35 else proj_name
        print(
            f"  {name:<35} {p['sessions']:>8} {p['turns']:>6} "
            f"{fmt_tokens(p['inp']):>9} {fmt_tokens(p['out']):>9} "
            f"{fmt_tokens(p['cache_write']):>9} {fmt_tokens(p['cache_read']):>9} "
            f"{fmt_tokens(tot):>10}  ${c:>8.4f}  {bar(pct, 12)} {pct:.1f}%"
        )

    # ── Top sessions ──────────────────────────────────────────────────────────
    print_section("TOP 20 SESSIONS BY TOTAL TOKENS")
    top = sorted(sessions, key=lambda s: s.total_tokens, reverse=True)[:20]
    hdr2 = f"  {'PROJECT':<30} {'SESSION':<38} {'TURNS':>5} {'TOTAL':>9} {'COST':>10}  FIRST"
    print(hdr2)
    print(f"  {SEP}")
    for s in top:
        name = (s.project[:28] + "..") if len(s.project) > 30 else s.project
        sid = s.session_id[:36]
        ts = (s.first_ts or "")[:10]
        print(
            f"  {name:<30} {sid:<38} {s.turns:>5} {fmt_tokens(s.total_tokens):>9}  ${s.cost_usd:>8.4f}  {ts}"
        )

    # ── Cache efficiency per project ──────────────────────────────────────────
    print_section("CACHE EFFICIENCY BY PROJECT  (cache_read / (inp+cache_read))")
    cache_proj = sorted(
        [(k, v) for k, v in by_project.items() if v["cache_read"] > 0],
        key=lambda kv: kv[1]["cache_read"] / max(kv[1]["inp"] + kv[1]["cache_read"], 1),
        reverse=True,
    )
    if cache_proj:
        for proj_name, p in cache_proj:
            denom = p["inp"] + p["cache_read"]
            eff = p["cache_read"] / denom * 100 if denom else 0
            name = (proj_name[:33] + "..") if len(proj_name) > 35 else proj_name
            print(
                f"  {name:<35}  {bar(eff, 25)} {eff:5.1f}%  "
                f"read={fmt_tokens(p['cache_read'])}  write={fmt_tokens(p['cache_write'])}"
            )
    else:
        print("  No cache reads recorded.")

    # ── Output/input ratio ────────────────────────────────────────────────────
    print_section("OUTPUT INTENSITY  (output / input — proxy for generation-heavy sessions)")
    intensity = sorted(
        [(k, v) for k, v in by_project.items() if v["inp"] > 0],
        key=lambda kv: kv[1]["out"] / max(kv[1]["inp"], 1),
        reverse=True,
    )
    for proj_name, p in intensity[:15]:
        ratio = p["out"] / max(p["inp"], 1)
        name = (proj_name[:33] + "..") if len(proj_name) > 35 else proj_name
        print(
            f"  {name:<35}  ratio={ratio:.2f}  out={fmt_tokens(p['out'])}  inp={fmt_tokens(p['inp'])}"
        )

    # ── Timeline: tokens by date ───────────────────────────────────────────────
    print_section("DAILY TOKEN SPEND  (last 30 days with activity)")
    daily: dict[str, int] = defaultdict(int)
    for s in sessions:
        ts = s.first_ts
        if ts and len(ts) >= 10:
            day = ts[:10]
            daily[day] += s.total_tokens

    recent = sorted(daily.items())[-30:]
    if recent:
        max_day_tok = max(t for _, t in recent)
        for day, tok in recent:
            pct = tok / max_day_tok * 100 if max_day_tok else 0
            print(f"  {day}  {bar(pct, 30)} {fmt_tokens(tok):>9}")

    # ── Footer ────────────────────────────────────────────────────────────────
    print(f"\n{'━' * 100}")
    print(
        f"  GRAND TOTAL: {fmt_tokens(grand_total_tok)} tokens  |  "
        f"input={fmt_tokens(grand['inp'])}  output={fmt_tokens(grand['out'])}  "
        f"cache-write={fmt_tokens(grand['cache_write'])}  cache-read={fmt_tokens(grand['cache_read'])}"
    )
    print(f"  Estimated cost: ${grand_cost:.4f} USD")
    print("━" * 100)
    print()


# ── JSON report ───────────────────────────────────────────────────────────────


def report_json(sessions: list[SessionStats]) -> None:
    """Machine-readable summary for agent consumption."""
    by_project = aggregate_by_project(sessions)
    grand = dict(inp=0, out=0, cache_write=0, cache_read=0, sessions=0, turns=0)
    for p in by_project.values():
        for k in grand:
            grand[k] += p[k]

    grand_total = grand["inp"] + grand["out"] + grand["cache_write"] + grand["cache_read"]
    grand_cost = cost(grand["inp"], grand["out"], grand["cache_write"], grand["cache_read"])

    daily: dict[str, int] = defaultdict(int)
    for s in sessions:
        ts = s.first_ts
        if ts and len(ts) >= 10:
            daily[ts[:10]] += s.total_tokens

    # Top 5 projects by token spend
    ranked_projects = sorted(
        by_project.items(),
        key=lambda kv: kv[1]["inp"] + kv[1]["out"] + kv[1]["cache_write"] + kv[1]["cache_read"],
        reverse=True,
    )[:10]

    # Last 14 days of daily spend
    recent_daily = [{"date": day, "tokens": tok} for day, tok in sorted(daily.items())[-14:]]

    output = {
        "ok": True,
        "total_sessions": len(sessions),
        "total_projects": len(by_project),
        "total_tokens": grand_total,
        "estimated_cost_usd": round(grand_cost, 4),
        "breakdown": {
            "input_tokens": grand["inp"],
            "output_tokens": grand["out"],
            "cache_write_tokens": grand["cache_write"],
            "cache_read_tokens": grand["cache_read"],
        },
        "pricing_model": "sonnet-4-6",
        "top_projects": [
            {
                "project": name,
                "sessions": p["sessions"],
                "tokens": p["inp"] + p["out"] + p["cache_write"] + p["cache_read"],
                "cost_usd": round(cost(p["inp"], p["out"], p["cache_write"], p["cache_read"]), 4),
            }
            for name, p in ranked_projects
        ],
        "daily_spend_14d": recent_daily,
    }
    print(json.dumps(output, indent=2))


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Claude Code token usage audit")
    ap.add_argument("--json", action="store_true", help="Output compact JSON for agent consumption")
    args = ap.parse_args()

    claude_dir = Path(os.environ.get("CLAUDE_DIR", Path.home() / ".claude"))
    if not args.json:
        print(f"Scanning {claude_dir}/projects …")
    sessions = scan_projects(claude_dir)
    if args.json:
        report_json(sessions)
    else:
        report(sessions)
