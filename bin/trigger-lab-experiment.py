#!/usr/bin/env python3
"""
AIOS: trigger-lab-experiment.py
Run a baseline→candidate Harbor benchmark comparison for eligible promoted rules.

For each eligible rule:
  1. Run Harbor baseline on core/ + holdout/ suites
  2. Apply the rule's patch to agent.py
  3. Run Harbor candidate on the same suites (+ rule-linked bundle if present)
  4. Revert patch
  5. Compute score deltas
  6. Determine outcome (never confirm solely on micro-suite gains)
  7. Write lab_run to aios.db, update pattern confirmation/contradiction counts
  8. Append run summary to rule artifact

Outcome rules:
  - CONFIRMED:     core_delta >= CONFIRM_THRESHOLD and holdout non-regression
  - CONTRADICTED:  core_delta <= CONTRADICT_THRESHOLD
  - INCONCLUSIVE:  everything else

Usage:
  python3 ~/AIOS/bin/trigger-lab-experiment.py [--pattern-id <id>] [--dry-run]
  python3 ~/AIOS/bin/trigger-lab-experiment.py --all [--dry-run]
"""
import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import importlib.util as _ilu

def _load_rule_artifacts():
    spec = _ilu.spec_from_file_location(
        "rule_artifacts",
        Path(__file__).parent / "rule-artifacts.py",
    )
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_ra = _load_rule_artifacts()
read_artifact  = _ra.read_artifact
append_lab_run = _ra.append_lab_run

DB          = Path.home() / "AIOS/data/aios.db"
LAB_DIR     = Path.home() / "projects/claude-improvement-lab"
APPLY_PATCH = LAB_DIR / "apply-patch.py"
TASKS_CORE  = LAB_DIR / "tasks/core"
TASKS_HOLD  = LAB_DIR / "tasks/holdout"
TASKS_MICRO = LAB_DIR / "tasks/rule-linked"

CONFIRM_THRESHOLD    =  0.05   # core delta needed to confirm
CONTRADICT_THRESHOLD = -0.05   # core delta floor before contradiction
HOLDOUT_FLOOR        = -0.05   # holdout must not drop more than this


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Harbor runner
# ---------------------------------------------------------------------------

def _run_harbor(tasks_dirs: list[Path], job_name: str, timeout: int = 600) -> Path:
    """
    Run harbor on the given task directories. Returns the job output directory.
    tasks_dirs: list of paths to task directories (each contains task subdirs)
    """
    jobs_dir = LAB_DIR / "jobs" / job_name
    jobs_dir.mkdir(parents=True, exist_ok=True)

    # Build -p flags for each task directory
    p_flags = []
    for d in tasks_dirs:
        if d.exists() and any(d.iterdir()):
            p_flags += ["-p", str(d)]

    if not p_flags:
        print("  [warn] No tasks found in any provided directory")
        return jobs_dir

    cmd = [
        "uv", "run", "harbor", "run",
        *p_flags,
        "-n", "4",
        "--agent-import-path", "agent:AutoAgent",
        "-o", str(LAB_DIR / "jobs"),
        "--job-name", job_name,
        "-y",
    ]

    print(f"  Running: {' '.join(cmd)}")
    proc = subprocess.run(
        cmd,
        cwd=str(LAB_DIR),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        print(f"  [warn] harbor exited {proc.returncode}: {proc.stderr[-500:]}")

    return jobs_dir


def _read_rewards(job_dir: Path) -> dict[str, float]:
    """
    Read all reward.txt files from a completed job.
    Returns {task_name: score, ...}
    """
    rewards: dict[str, float] = {}
    if not job_dir.exists():
        return rewards
    for reward_file in job_dir.glob("*/verifier/reward.txt"):
        trial_name = reward_file.parent.parent.name   # <task_name[:32]>__<uuid>
        task_name = trial_name.rsplit("__", 1)[0]     # strip the uuid suffix
        try:
            score = float(reward_file.read_text().strip())
            # If same task ran multiple times, take the last (only 1 trial here)
            rewards[task_name] = score
        except (ValueError, OSError):
            pass
    return rewards


def _avg_score(rewards: dict[str, float]) -> float:
    if not rewards:
        return 0.0
    return sum(rewards.values()) / len(rewards)


# ---------------------------------------------------------------------------
# Patch helpers
# ---------------------------------------------------------------------------

def _build_patch_spec(artifact: dict) -> dict:
    mutation_scope = artifact.get("mutation_scope", "prompt_overlay")
    rule_text = artifact.get("rule_text", "")

    if mutation_scope == "prompt_overlay":
        return {"patch_type": "prompt_overlay", "payload": {"text": rule_text}}
    elif mutation_scope == "verification_toggle":
        return {"patch_type": "verification_toggle", "payload": {"enabled": True}}
    elif mutation_scope == "planning_scaffold":
        return {"patch_type": "planning_scaffold", "payload": {"enabled": True}}
    elif mutation_scope == "orchestration_flag":
        return {"patch_type": "orchestration_flag", "payload": {"flags": {"MAX_TURNS": 40}}}
    else:
        return {"patch_type": "prompt_overlay", "payload": {"text": rule_text}}


def _apply_patch(spec: dict) -> bool:
    spec_file = LAB_DIR / ".tmp-patch-spec.json"
    spec_file.write_text(json.dumps(spec))
    result = subprocess.run(
        ["python3", str(APPLY_PATCH), "apply", str(spec_file)],
        capture_output=True, text=True, cwd=str(LAB_DIR),
    )
    spec_file.unlink(missing_ok=True)
    if result.returncode != 0:
        print(f"  [error] apply-patch failed: {result.stderr}")
        return False
    return True


def _revert_patch() -> None:
    subprocess.run(
        ["python3", str(APPLY_PATCH), "revert"],
        capture_output=True, text=True, cwd=str(LAB_DIR),
    )


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _get_eligible_patterns(conn: sqlite3.Connection, pattern_id: str | None) -> list[dict]:
    conn.row_factory = sqlite3.Row
    if pattern_id:
        rows = conn.execute(
            "SELECT * FROM patterns WHERE id=?", (pattern_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT * FROM patterns
               WHERE state='rule'
               AND human_approved=1
               AND (lab_dispatched_at IS NULL OR lab_status='pending' OR lab_status='bundle_ready')
            """
        ).fetchall()
    return [dict(r) for r in rows]


def _get_bundle_id(conn: sqlite3.Connection, pattern_id: str) -> str | None:
    row = conn.execute(
        "SELECT id FROM rule_eval_bundles WHERE pattern_id=? ORDER BY created_at DESC LIMIT 1",
        (pattern_id,)
    ).fetchone()
    return row[0] if row else None


def _write_lab_run(conn: sqlite3.Connection, run: dict) -> str:
    run_id = run["id"]
    conn.execute(
        """
        INSERT INTO lab_runs
          (id, pattern_id, rule_text_snapshot, bundle_id, patch_type, patch_payload,
           baseline_score, candidate_score, score_delta, pass_delta, holdout_delta,
           simplicity_delta, micro_delta, outcome, commit_hash, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run["id"],
            run["pattern_id"],
            run.get("rule_text_snapshot", ""),
            run.get("bundle_id"),
            run.get("patch_type"),
            json.dumps(run.get("patch_payload", {})),
            run.get("baseline_score"),
            run.get("candidate_score"),
            run.get("score_delta"),
            run.get("pass_delta"),
            run.get("holdout_delta"),
            None,  # simplicity_delta
            run.get("micro_delta"),
            run.get("outcome"),
            run.get("commit_hash"),
            run.get("notes", ""),
            run.get("created_at", _now()),
        ),
    )
    return run_id


def _update_pattern_post_run(conn: sqlite3.Connection, pattern_id: str, outcome: str, run_id: str) -> None:
    if outcome == "confirmed":
        conn.execute(
            """UPDATE patterns
               SET confirmation_count = COALESCE(confirmation_count, 0) + 1,
                   last_confirmed_at = ?,
                   lab_status = 'confirmed',
                   last_lab_run_id = ?
               WHERE id = ?""",
            (_now(), run_id, pattern_id),
        )
    elif outcome == "contradicted":
        conn.execute(
            """UPDATE patterns
               SET contradiction_count = COALESCE(contradiction_count, 0) + 1,
                   last_contradicted_at = ?,
                   lab_status = 'contradicted',
                   last_lab_run_id = ?
               WHERE id = ?""",
            (_now(), run_id, pattern_id),
        )
    else:
        conn.execute(
            """UPDATE patterns
               SET lab_status = 'inconclusive',
                   last_lab_run_id = ?
               WHERE id = ?""",
            (run_id, pattern_id),
        )


# ---------------------------------------------------------------------------
# Outcome determination
# ---------------------------------------------------------------------------

def _determine_outcome(
    core_delta: float,
    holdout_delta: float | None,
    micro_delta: float | None,
) -> str:
    """
    Determine outcome.
    - CONFIRMED:     core improved above threshold AND holdout didn't collapse
    - CONTRADICTED:  core dropped below contradict threshold
    - INCONCLUSIVE:  everything else (including micro-only improvements)
    """
    holdout_ok = holdout_delta is None or holdout_delta >= HOLDOUT_FLOOR

    if core_delta >= CONFIRM_THRESHOLD and holdout_ok:
        return "confirmed"
    elif core_delta <= CONTRADICT_THRESHOLD:
        return "contradicted"
    else:
        return "inconclusive"


# ---------------------------------------------------------------------------
# Main experiment runner
# ---------------------------------------------------------------------------

def run_experiment(
    pattern: dict,
    conn: sqlite3.Connection,
    dry_run: bool = False,
) -> dict:
    pattern_id = pattern["id"]
    artifact = read_artifact(pattern_id)

    if not artifact:
        print(f"  [skip] No artifact for pattern {pattern_id[:8]}")
        return {"outcome": "skip"}

    bundle_id = _get_bundle_id(conn, pattern_id)
    patch_spec = _build_patch_spec(artifact)
    run_id = f"run-{pattern_id[:8]}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

    print(f"\nExperiment: {run_id}")
    print(f"  pattern: {pattern.get('title', '')[:60]!r}")
    print(f"  cap_class: {artifact.get('capability_class')}  patch: {patch_spec['patch_type']}")

    if dry_run:
        print("  [DRY RUN] would run baseline + candidate, skipping actual Harbor calls")
        return {
            "id": run_id, "pattern_id": pattern_id, "outcome": "dry_run",
            "patch_type": patch_spec["patch_type"],
        }

    # ── Mark dispatched ─────────────────────────────────────────────────────
    conn.execute(
        "UPDATE patterns SET lab_dispatched_at=?, lab_status='running' WHERE id=?",
        (_now(), pattern_id),
    )
    conn.commit()

    baseline_job = f"{run_id}-baseline"
    candidate_job = f"{run_id}-candidate"

    # ── 1. Baseline run ──────────────────────────────────────────────────────
    print(f"\n  → Baseline: {baseline_job}")
    _run_harbor([TASKS_CORE, TASKS_HOLD], baseline_job)

    base_job_dir  = LAB_DIR / "jobs" / baseline_job
    base_core     = _read_rewards(base_job_dir / "core"  if (base_job_dir / "core").exists() else base_job_dir)
    base_hold     = _read_rewards(base_job_dir / "holdout" if (base_job_dir / "holdout").exists() else base_job_dir)

    # Separate core vs holdout by task name prefix (core tasks live in tasks/core/, holdout in tasks/holdout/)
    core_task_names  = {d.name for d in TASKS_CORE.iterdir() if d.is_dir()} if TASKS_CORE.exists() else set()
    hold_task_names  = {d.name for d in TASKS_HOLD.iterdir() if d.is_dir()} if TASKS_HOLD.exists() else set()
    all_base_rewards = _read_rewards(base_job_dir)

    base_core_rewards = {k: v for k, v in all_base_rewards.items() if k in core_task_names}
    base_hold_rewards = {k: v for k, v in all_base_rewards.items() if k in hold_task_names}

    baseline_core  = _avg_score(base_core_rewards)
    baseline_hold  = _avg_score(base_hold_rewards)
    print(f"  baseline  core={baseline_core:.3f}  holdout={baseline_hold:.3f}")

    # ── 2. Apply patch ───────────────────────────────────────────────────────
    print(f"\n  → Applying patch: {patch_spec['patch_type']}")
    if not _apply_patch(patch_spec):
        conn.execute("UPDATE patterns SET lab_status='error' WHERE id=?", (pattern_id,))
        conn.commit()
        return {"outcome": "error", "notes": "patch apply failed"}

    # ── 3. Candidate run ─────────────────────────────────────────────────────
    print(f"\n  → Candidate: {candidate_job}")
    micro_dirs = []
    if bundle_id:
        micro_dir = TASKS_MICRO / bundle_id
        if micro_dir.exists():
            micro_dirs = [micro_dir]

    _run_harbor([TASKS_CORE, TASKS_HOLD, *micro_dirs], candidate_job)

    cand_job_dir    = LAB_DIR / "jobs" / candidate_job
    all_cand_rewards = _read_rewards(cand_job_dir)

    cand_core_rewards = {k: v for k, v in all_cand_rewards.items() if k in core_task_names}
    cand_hold_rewards = {k: v for k, v in all_cand_rewards.items() if k in hold_task_names}

    if bundle_id:
        micro_task_names  = {d.name for d in (TASKS_MICRO / bundle_id).iterdir() if d.is_dir()} if (TASKS_MICRO / bundle_id).exists() else set()
        cand_micro_rewards = {k: v for k, v in all_cand_rewards.items() if k in micro_task_names}
    else:
        cand_micro_rewards = {}

    candidate_core = _avg_score(cand_core_rewards)
    candidate_hold = _avg_score(cand_hold_rewards)
    candidate_micro = _avg_score(cand_micro_rewards) if cand_micro_rewards else None

    print(f"  candidate core={candidate_core:.3f}  holdout={candidate_hold:.3f}"
          + (f"  micro={candidate_micro:.3f}" if candidate_micro is not None else ""))

    # ── 4. Revert patch ──────────────────────────────────────────────────────
    _revert_patch()
    print("  → Patch reverted")

    # ── 5. Compute deltas ────────────────────────────────────────────────────
    core_delta    = candidate_core - baseline_core
    holdout_delta = candidate_hold - baseline_hold if base_hold_rewards else None
    micro_delta   = (candidate_micro - 0.0) if candidate_micro is not None else None  # baseline micro=0 (no prior run)

    # ── 6. Determine outcome ─────────────────────────────────────────────────
    outcome = _determine_outcome(core_delta, holdout_delta, micro_delta)

    print(f"\n  core_delta={core_delta:+.3f}  holdout_delta={holdout_delta if holdout_delta is not None else 'N/A'}  outcome={outcome.upper()}")

    # ── 7. Build and write run record ────────────────────────────────────────
    run_record = {
        "id":                 run_id,
        "pattern_id":         pattern_id,
        "rule_text_snapshot": artifact.get("rule_text", ""),
        "bundle_id":          bundle_id,
        "patch_type":         patch_spec["patch_type"],
        "patch_payload":      patch_spec.get("payload", {}),
        "baseline_score":     baseline_core,
        "candidate_score":    candidate_core,
        "score_delta":        core_delta,
        "pass_delta":         len(cand_core_rewards) - len(base_core_rewards),
        "holdout_delta":      holdout_delta,
        "micro_delta":        micro_delta,
        "outcome":            outcome,
        "commit_hash":        None,
        "notes":              f"core tasks={len(core_task_names)}, holdout tasks={len(hold_task_names)}",
        "created_at":         _now(),
    }

    _write_lab_run(conn, run_record)
    _update_pattern_post_run(conn, pattern_id, outcome, run_id)
    conn.commit()

    # ── 8. Append run to artifact ────────────────────────────────────────────
    append_lab_run(pattern_id, run_record)

    return run_record


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _preflight_check() -> list[str]:
    """Return list of blocking issues. Empty list = clear to run."""
    issues = []
    # Docker running?
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, timeout=10)
        if r.returncode != 0:
            issues.append("Docker is not running (docker info failed)")
    except FileNotFoundError:
        issues.append("docker not found in PATH")
    except subprocess.TimeoutExpired:
        issues.append("docker info timed out — daemon may be unresponsive")

    # OPENAI_API_KEY set?
    import os
    if not os.environ.get("OPENAI_API_KEY"):
        issues.append("OPENAI_API_KEY not set in environment")

    # Lab directory exists?
    if not LAB_DIR.exists():
        issues.append(f"LAB_DIR not found: {LAB_DIR}")

    # apply-patch.py present?
    if not APPLY_PATCH.exists():
        issues.append(f"apply-patch.py not found: {APPLY_PATCH}")

    return issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--pattern-id", help="Run experiment for a specific pattern ID")
    group.add_argument("--all", action="store_true", help="Run experiments for all eligible patterns")
    parser.add_argument("--dry-run", action="store_true", help="Don't run Harbor or modify DB")
    parser.add_argument("--skip-preflight", action="store_true", help="Skip Docker/env checks")
    args = parser.parse_args()

    if not args.dry_run and not args.skip_preflight:
        issues = _preflight_check()
        if issues:
            print("Preflight checks failed — aborting:")
            for issue in issues:
                print(f"  ✗ {issue}")
            print("\nRun with --dry-run to skip Harbor calls, or --skip-preflight to bypass checks.")
            sys.exit(1)

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    patterns = _get_eligible_patterns(conn, args.pattern_id if not args.all else None)

    if not patterns:
        print("No eligible patterns found.")
        if args.pattern_id:
            print(f"  (pattern must have state='rule', human_approved=1)")
        conn.close()
        return

    print(f"Found {len(patterns)} eligible pattern(s)")

    results = []
    for pattern in patterns:
        try:
            result = run_experiment(pattern, conn, dry_run=args.dry_run)
            results.append(result)
        except subprocess.TimeoutExpired:
            print(f"  [timeout] experiment exceeded time limit for {pattern['id'][:8]}")
            conn.execute("UPDATE patterns SET lab_status='error' WHERE id=?", (pattern["id"],))
            conn.commit()
            _revert_patch()  # always revert
        except Exception as exc:
            print(f"  [error] {exc}")
            conn.execute("UPDATE patterns SET lab_status='error' WHERE id=?", (pattern["id"],))
            conn.commit()
            _revert_patch()  # always revert

    conn.close()

    # Summary
    print(f"\n{'='*50}")
    print(f"Experiments: {len(results)}")
    for r in results:
        outcome = r.get("outcome", "?")
        pid = r.get("pattern_id", "?")[:8]
        delta = r.get("score_delta")
        delta_str = f"{delta:+.3f}" if delta is not None else "N/A"
        print(f"  {pid}  {outcome.upper():<14}  core_delta={delta_str}")


if __name__ == "__main__":
    main()
