#!/usr/bin/env python3
"""
AIOS: aios-pipeline.py
Daily automation orchestrator — run as a cron job or manually.

Phases (skipped individually on failure, pipeline continues):
  1. Codex ingest      — scan ~/.codex/sessions for new rollouts
  2. Score patterns    — recompute frequency/impact, auto-promote/demote
  3. Workflow synthesis — propose reusable workflows from recurring patterns
  4. Bundle new rules  — generate eval bundles for newly promoted rules
  5. Lab experiments   — run Harbor benchmarks (skipped if Docker unavailable)
  6. Personal extract  — mine sessions/prompts for personal patterns
  7. Vault report      — write lab-report summary to Obsidian
  8. iMessage ingest   — upsert contacts active in last 24h + vault files
  9. Apple Notes ingest — sync all notes to aios.db + vault markdown

Usage:
  python3 ~/AIOS/bin/aios-pipeline.py [--skip-lab] [--dry-run] [--verbose]

Cron (daily at 06:00):
  0 6 * * * python3 ~/AIOS/bin/aios-pipeline.py >> ~/AIOS/logs/pipeline.log 2>&1
"""
import argparse
import shlex
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from aios_paths import get_vault_subpath

from services.rtk_integration import rtk_run

BIN  = Path(__file__).parent
LOG  = Path.home() / "AIOS/logs/pipeline.log"
VAULT = get_vault_subpath("02 AI OS")

PHASES = [
    "codex-ingest",
    "score-patterns",
    "bundle-rules",
    "lab-experiments",
    "personal-extract",
    "vault-report",
    "ingest-imessage",
    "ingest-apple-notes",
]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _log(msg: str, verbose: bool = False) -> None:
    ts = _now()
    line = f"{ts} [pipeline] {msg}"
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a") as f:
            f.write(line + "\n")
    except Exception:
        pass
    print(line)


def _run(cmd: list[str], label: str, verbose: bool) -> tuple[bool, str]:
    """Run a subprocess through RTK, return (success, compressed output)."""
    try:
        result = rtk_run(
            shlex.join(cmd),
            "adaptive",
            timeout=600,
            source_kind=f"pipeline:{label}",
        )
        if result.exit_code != 0:
            return False, result.output[:800]
        return True, result.output
    except subprocess.TimeoutExpired:
        return False, "timeout after 600s"
    except Exception as exc:
        return False, str(exc)


def _docker_available() -> bool:
    try:
        result = subprocess.run(
            ["docker", "info"], capture_output=True, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


def _write_vault_report(report_text: str, verbose: bool) -> None:
    """Write lab report summary to Obsidian vault."""
    vault_dir = VAULT / "05 Tooling"
    vault_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    report_path = vault_dir / f"lab-report-{date_str}.md"
    report_path.write_text(
        f"# Lab Report — {date_str}\n\n"
        "```\n"
        f"{report_text}\n"
        "```\n"
    )
    if verbose:
        _log(f"  vault report written to {report_path}", verbose)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-lab", action="store_true",
                        help="Skip lab experiment phase")
    parser.add_argument("--dry-run", action="store_true",
                        help="Pass --dry-run to sub-scripts where supported")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    _log("=== AIOS daily pipeline starting ===")
    results: dict[str, str] = {}

    # ── Phase 1: Codex ingest ─────────────────────────────────────────────────
    _log("phase 1/7: Codex ingest")
    ok, out = _run(
        ["python3", str(BIN / "cron-ingest-codex.py")],
        "codex-ingest",
        args.verbose,
    )
    if ok:
        # Pull last line as summary
        summary = out.splitlines()[-1] if out else "ok"
        results["codex-ingest"] = f"ok — {summary}"
        _log(f"  {summary}")
    else:
        results["codex-ingest"] = f"FAILED: {out}"
        _log(f"  FAILED: {out}")

    # ── Phase 2: Score patterns ───────────────────────────────────────────────
    _log("phase 2/7: score patterns")
    score_cmd = ["python3", str(BIN / "score-patterns.py")]
    if args.dry_run:
        score_cmd.append("--dry-run")
    ok, out = _run(score_cmd, "score-patterns", args.verbose)
    if ok:
        summary = out.splitlines()[-3] if len(out.splitlines()) >= 3 else out[:120]
        results["score-patterns"] = f"ok — {summary}"
        _log(f"  {summary}")
        if args.verbose:
            for line in out.splitlines():
                _log(f"    {line}", verbose=True)
    else:
        results["score-patterns"] = f"FAILED: {out}"
        _log(f"  FAILED: {out}")

    # ── Phase 3: Workflow synthesis ───────────────────────────────────────────
    _log("phase 3/7: workflow synthesis")
    synth_cmd = ["python3", str(BIN / "synthesize-workflows.py")]
    if args.dry_run:
        synth_cmd.append("--dry-run")
    ok, out = _run(synth_cmd, "synthesize-workflows", args.verbose)
    if ok:
        summary = out.splitlines()[-1] if out else "ok"
        results["synthesize-workflows"] = f"ok — {summary}"
        _log(f"  {summary}")
    else:
        results["synthesize-workflows"] = f"FAILED: {out}"
        _log(f"  FAILED: {out}")

    # ── Phase 4: Bundle new rules ─────────────────────────────────────────────
    _log("phase 4/7: bundle new rules (lab_status=pending)")
    import sqlite3
    DB = Path.home() / "AIOS/data/aios.db"
    try:
        conn = sqlite3.connect(DB)
        pending = conn.execute(
            "SELECT id FROM patterns WHERE lab_status='pending' AND state='rule'"
        ).fetchall()
        conn.close()
        if pending:
            for (pid,) in pending:
                ok, out = _run(
                    ["python3", str(BIN / "generate-rule-bundle.py"),
                     "--pattern-id", pid],
                    "generate-rule-bundle",
                    args.verbose,
                )
                if ok:
                    results[f"bundle-{pid[:8]}"] = "ok"
                    _log(f"  bundle generated for {pid[:8]}")
                else:
                    results[f"bundle-{pid[:8]}"] = f"FAILED: {out}"
                    _log(f"  bundle FAILED for {pid[:8]}: {out}")
        else:
            results["bundle-rules"] = "skip — no pending rules"
            _log("  no pending rules to bundle")
    except Exception as exc:
        results["bundle-rules"] = f"FAILED: {exc}"
        _log(f"  FAILED: {exc}")

    # ── Phase 5: Lab experiments ──────────────────────────────────────────────
    _log("phase 5/7: lab experiments")
    if args.skip_lab:
        results["lab-experiments"] = "skip — --skip-lab"
        _log("  skipped (--skip-lab)")
    elif not _docker_available():
        results["lab-experiments"] = "skip — Docker not running"
        _log("  skipped (Docker not available)")
    else:
        lab_cmd = ["python3", str(BIN / "trigger-lab-experiment.py"), "--all"]
        if args.dry_run:
            lab_cmd.append("--dry-run")
        ok, out = _run(lab_cmd, "lab-experiments", args.verbose)
        if ok:
            summary = out.splitlines()[-1] if out else "ok"
            results["lab-experiments"] = f"ok — {summary}"
            _log(f"  {summary}")
        else:
            results["lab-experiments"] = f"FAILED: {out}"
            _log(f"  FAILED: {out}")

    # ── Phase 6: Personal pattern extraction ─────────────────────────────────
    _log("phase 6/7: personal pattern extraction")
    extract_bin = BIN / "extract-personal-patterns.py"
    if extract_bin.exists():
        ok, out = _run(
            ["python3", str(extract_bin)],
            "extract-personal",
            args.verbose,
        )
        if ok:
            summary = out.splitlines()[-1] if out else "ok"
            results["personal-extract"] = f"ok — {summary}"
            _log(f"  {summary}")
        else:
            results["personal-extract"] = f"FAILED: {out}"
            _log(f"  FAILED: {out}")
    else:
        results["personal-extract"] = "skip — extract-personal-patterns.py not found"
        _log("  skipped (extract-personal-patterns.py not found)")

    # ── Phase 7: Vault report ─────────────────────────────────────────────────
    _log("phase 7/7: vault report")
    ok, report_text = _run(
        ["python3", str(BIN / "lab-report.py"), "--limit", "20"],
        "lab-report",
        args.verbose,
    )
    if ok and report_text.strip():
        try:
            _write_vault_report(report_text, args.verbose)
            results["vault-report"] = "ok"
            _log("  lab report written to vault")
        except Exception as exc:
            results["vault-report"] = f"FAILED: {exc}"
            _log(f"  vault write FAILED: {exc}")
    else:
        results["vault-report"] = f"FAILED: {report_text}"
        _log(f"  lab-report FAILED: {report_text}")

    # ── Phase 8: iMessage ingest ─────────────────────────────────────────────
    _log("phase 8/9: iMessage ingest")
    imessage_cmd = ["python3", str(BIN / "ingest-imessage.py"), "--days", "1"]
    if args.dry_run:
        imessage_cmd.append("--dry-run")
    ok, out = _run(imessage_cmd, "ingest-imessage", args.verbose)
    if ok:
        summary = out.splitlines()[-1] if out else "ok"
        results["ingest-imessage"] = f"ok — {summary}"
        _log(f"  {summary}")
    else:
        results["ingest-imessage"] = f"FAILED: {out}"
        _log(f"  FAILED: {out}")

    # ── Phase 9: Apple Notes ingest ───────────────────────────────────────────
    _log("phase 9/9: Apple Notes ingest")
    notes_cmd = ["python3", str(BIN / "ingest-apple-notes.py")]
    if args.dry_run:
        notes_cmd.append("--dry-run")
    ok, out = _run(notes_cmd, "ingest-apple-notes", args.verbose)
    if ok:
        summary = next(
            (line for line in reversed(out.splitlines()) if "Notes processed" in line),
            out.splitlines()[-1] if out else "ok",
        )
        results["ingest-apple-notes"] = f"ok — {summary}"
        _log(f"  {summary}")
    else:
        results["ingest-apple-notes"] = f"FAILED: {out}"
        _log(f"  FAILED: {out}")

    # ── Summary ───────────────────────────────────────────────────────────────
    _log("=== pipeline complete ===")
    ok_count  = sum(1 for v in results.values() if v.startswith("ok"))
    skip_count = sum(1 for v in results.values() if v.startswith("skip"))
    fail_count = sum(1 for v in results.values() if v.startswith("FAILED"))
    _log(f"  {ok_count} ok, {skip_count} skipped, {fail_count} failed")
    for phase, status in results.items():
        _log(f"  {phase:<30} {status[:80]}")

    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()
