#!/usr/bin/env python3
"""Record the fresh M6 promotion-grade benchmark in the local eval contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ruff: noqa: E402
from services.eval_run_service import (
    create_eval_pair,
    create_eval_run,
    create_eval_task,
    ensure_eval_schema,
    finalize_eval_pair,
    list_promotion_ready_eval_pairs,
    record_eval_score,
)

PROTECTED_START_SHA = "4d8adbca3b89d6259e252f26aaad0db69a9bf102"
ARTIFACT_ROOT = Path("/private/tmp/aios-m6-promotion")
SESSION_ROOT = Path.home() / ".codex" / "sessions"
REVIEW_REF = "docs/evals/M6_PROMOTION_GRADE_ADVERSARIAL_REVIEW.md"
REPORT_REF = "docs/evals/M6_PROMOTION_GRADE_BENCHMARK_REPORT.md"
ARTIFACT_LABELS = {
    "task-a-control": "task-a-control",
    "task-a-treatment": "task-a-treatment",
    "task-b-control": "b-control",
    "task-b-treatment": "b-treatment",
    "task-c-control": "c-control",
    "task-c-treatment": "c-treatment",
}
SESSION_ROLLOUTS = {
    "task-a-control": SESSION_ROOT / "2026/07/15/rollout-2026-07-15T12-29-38-019f669c-c5d3-7260-82cb-5ed68276f420.jsonl",
    "task-a-treatment": SESSION_ROOT / "2026/07/15/rollout-2026-07-15T12-29-38-019f669c-c5d3-7e20-9836-763390f41ff5.jsonl",
    "task-b-control": SESSION_ROOT / "2026/07/15/rollout-2026-07-15T12-44-11-019f66aa-17a6-7af0-ac7a-fb64e1fa2b31.jsonl",
    "task-b-treatment": SESSION_ROOT / "2026/07/15/rollout-2026-07-15T12-44-11-019f66aa-17e8-79d0-8bab-5976d99d1bdf.jsonl",
    "task-c-control": SESSION_ROOT / "2026/07/15/rollout-2026-07-15T12-44-10-019f66aa-15d6-7c52-8318-d3e4cba6c765.jsonl",
    "task-c-treatment": SESSION_ROOT / "2026/07/15/rollout-2026-07-15T12-44-10-019f66aa-14d6-7c51-a324-762bf82c3e10.jsonl",
}

PARITY_METADATA: dict[str, Any] = {
    "model": "gpt-5.6-luna",
    "effort": "high",
    "tools": ["shell", "rg", "sed", "git", "python3", "pnpm", "pytest", "playwright"],
    "budget": {"tokens": 20_000, "seconds": 900},
}

CONTEXT_FILES = {
    "owner": [
        "docs/modernization/ADR-002-canonical-state-and-migration-authority.md",
        "docs/modernization/ADR-005-subsystem-ownership-and-parallel-v2-strategy.md",
        "docs/modernization/PROGRESS.md",
        ".tracker/PROJECT_TRUTH.md",
        ".wayfinder/aios-modernization/tickets/019-migrate-standards-backfill-write-owner.md",
        ".wayfinder/aios-modernization/tickets/020-migrate-project-component-settings-owner.md",
        ".wayfinder/aios-modernization/tickets/021-migrate-automation-trigger-owner.md",
        ".wayfinder/aios-modernization/tickets/022-migrate-pattern-approval-owner.md",
    ],
    "browser": [
        "docs/modernization/ADR-003-task-centred-ia-and-accessible-design-system.md",
        "docs/modernization/ADR-004-reproducible-ui-validation-contract.md",
        "docs/modernization/PROGRESS.md",
        ".tracker/PROJECT_TRUTH.md",
        ".wayfinder/aios-modernization/tickets/019-migrate-standards-backfill-write-owner.md",
        ".wayfinder/aios-modernization/tickets/020-migrate-project-component-settings-owner.md",
        ".wayfinder/aios-modernization/tickets/021-migrate-automation-trigger-owner.md",
        ".wayfinder/aios-modernization/tickets/022-migrate-pattern-approval-owner.md",
    ],
}

TASKS = (
    {
        "slug": "task-a-workflow-skill-owner",
        "title": "Workflow skill-candidate owner migration",
        "kind": "owner",
        "control_context": "peer_repo_only",
        "treatment_context": "peer_portable_context_packet",
        "control_prompt": "benchmark/m6-promotion-prompts/task-a-workflow-skill-owner-control.md",
        "treatment_prompt": "benchmark/m6-promotion-prompts/task-a-workflow-skill-owner-treatment.md",
        "control_worktree": "task-a-control",
        "treatment_worktree": "task-a-treatment",
        "acceptance": [
            "promoteSkill and dismissSkill route through a validated Python owner",
            "tRPC result shapes and skills-file behavior remain compatible",
            "direct TypeScript candidate updates are deleted",
            "focused tests and static checks pass",
            "browser and production-build checks are recorded honestly",
        ],
    },
    {
        "slug": "task-b-shadow-approval-owner",
        "title": "Shadow-candidate approval owner migration",
        "kind": "owner",
        "control_context": "peer_repo_only",
        "treatment_context": "peer_portable_context_packet",
        "control_prompt": "benchmark/m6-promotion-prompts/task-b-shadow-approval-control.md",
        "treatment_prompt": "benchmark/m6-promotion-prompts/task-b-shadow-approval-treatment.md",
        "control_worktree": "task-b-control",
        "treatment_worktree": "task-b-treatment",
        "acceptance": [
            "eval.approveShadowCandidate routes through a validated Python owner",
            "missing candidates fail safe with the existing null contract",
            "APPROVED_IN_PERSON transition semantics remain unchanged",
            "direct TypeScript candidate updates are deleted",
            "focused tests and static checks pass",
        ],
    },
    {
        "slug": "task-c-browser-contract",
        "title": "Verify to Review to Closeout browser contract",
        "kind": "browser",
        "control_context": "peer_repo_only",
        "treatment_context": "peer_portable_context_packet",
        "control_prompt": "benchmark/m6-promotion-prompts/task-c-browser-contract-control.md",
        "treatment_prompt": "benchmark/m6-promotion-prompts/task-c-browser-contract-treatment.md",
        "control_worktree": "task-c-control",
        "treatment_worktree": "task-c-treatment",
        "acceptance": [
            "seeded Verify, Review, and Closeout fixtures are deterministic",
            "mobile, tablet, and desktop states are covered",
            "keyboard, provenance, approval, console, and network checks are explicit",
            "browser discovery and static checks pass",
            "runtime/browser and production-build limits are recorded honestly",
        ],
    },
)

# These are independent-review scores, not model self-scores. They are kept
# explicit so a later rerun can change them without changing telemetry parsing.
REVIEW_SCORES: dict[str, dict[str, dict[str, float | None]]] = {
    "task-a-workflow-skill-owner": {
        "control": {"task_success": 0.92, "quality_adherence": 0.86, "workflow_speed": 0.72, "context_effectiveness": 0.60, "context_portability": 0.55, "autonomy": 0.87, "user_trust": 0.80},
        "treatment": {"task_success": 0.94, "quality_adherence": 0.87, "workflow_speed": 0.81, "context_effectiveness": 0.63, "context_portability": 0.56, "autonomy": 0.90, "user_trust": 0.83},
    },
    "task-b-shadow-approval-owner": {
        "control": {"task_success": 0.95, "quality_adherence": 0.80, "workflow_speed": 0.84, "context_effectiveness": 0.60, "context_portability": 0.54, "autonomy": 0.93, "user_trust": 0.59},
        "treatment": {"task_success": 0.95, "quality_adherence": 0.86, "workflow_speed": 0.85, "context_effectiveness": 0.61, "context_portability": 0.57, "autonomy": 0.89, "user_trust": 0.64},
    },
    "task-c-browser-contract": {
        "control": {"task_success": 0.71, "quality_adherence": 0.78, "workflow_speed": 0.82, "context_effectiveness": 0.55, "context_portability": 0.59, "autonomy": 0.84, "user_trust": 0.75},
        "treatment": {"task_success": 0.52, "quality_adherence": 0.58, "workflow_speed": 0.70, "context_effectiveness": 0.50, "context_portability": 0.56, "autonomy": 0.82, "user_trust": 0.54},
    },
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def json_hash(value: object) -> str:
    return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def run_git(worktree: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(worktree), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def parse_events(path: Path) -> dict[str, Any]:
    commands: list[str] = []
    tests: list[str] = []
    failed_commands = 0
    tool_calls = 0
    files_changed: set[str] = set()
    blocked = False
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item") or {}
        if item.get("type") == "command_execution":
            tool_calls += 1
            command = str(item.get("command") or "")
            commands.append(command)
            if any(token in command.lower() for token in ("pytest", "playwright", "eslint", "tsc", "ruff", "basedpyright", "dependency-cruiser", "next build", "context:validate")):
                tests.append(command)
            if item.get("exit_code") not in (None, 0):
                failed_commands += 1
            output = str(item.get("aggregated_output") or "")
            blocked = blocked or any(token in output.lower() for token in ("blocked", "eperm", "enotfound", "symlink", "listen eperm"))
        if item.get("type") == "file_change":
            for change in item.get("changes", []):
                if isinstance(change, dict) and change.get("path"):
                    files_changed.add(str(change["path"]))
    return {
        "commands": commands,
        "tests": list(dict.fromkeys(tests)),
        "tool_calls": tool_calls,
        "failed_commands": failed_commands,
        "file_change_events": sorted(files_changed),
        "blocked": blocked,
    }


def session_telemetry(worktree: Path) -> dict[str, Any]:
    found: dict[str, Any] = {"session_id": None, "duration_ms": None, "total_tokens": None, "rollout_path": None}
    path = SESSION_ROLLOUTS[str(worktree.name)]
    cwd = None
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        payload = event.get("payload") or {}
        if event.get("type") == "turn_context":
            cwd = payload.get("cwd")
        if cwd != str(worktree):
            continue
        if event.get("type") == "session_meta":
            found["session_id"] = payload.get("id")
        if event.get("type") == "event_msg" and payload.get("type") == "token_count":
            found["total_tokens"] = payload.get("info", {}).get("total_token_usage", {}).get("total_tokens")
        if event.get("type") == "event_msg" and payload.get("type") == "task_complete":
            found["duration_ms"] = payload.get("duration_ms")
    found["rollout_path"] = str(path)
    return found


def worktree_evidence(worktree: Path, event_data: dict[str, Any]) -> dict[str, Any]:
    status = run_git(worktree, "status", "--short", "--untracked-files=all").splitlines()
    changed = set(run_git(worktree, "diff", "--name-only", PROTECTED_START_SHA).splitlines())
    changed.update(line[3:] for line in status if len(line) > 3 and not line.endswith(".venv"))
    return {
        "head_sha": run_git(worktree, "rev-parse", "HEAD"),
        "protected_start_sha_ancestor": run_git(worktree, "merge-base", PROTECTED_START_SHA, "HEAD") == PROTECTED_START_SHA,
        "status": status,
        "changed_files": sorted(path for path in changed if path and path != ".venv"),
        "changed_file_count": len([path for path in changed if path and path != ".venv"]),
        "event_file_change_paths": event_data["file_change_events"],
    }


def context_hash(kind: str) -> str:
    payload = [(path, sha256_file(ROOT / path)) for path in CONTEXT_FILES[kind]]
    return json_hash(payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=ARTIFACT_ROOT / "m6-promotion-grade-ledger.db")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/evals/M6_PROMOTION_GRADE_BENCHMARK_EVIDENCE.json")
    parser.add_argument("--review-status", choices=["passed", "failed", "not_run"], default="passed")
    args = parser.parse_args()
    if args.db.exists():
        raise SystemExit(f"Refusing to overwrite existing ledger: {args.db}")
    args.db.parent.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    ensure_eval_schema(conn)
    all_runs: list[dict[str, Any]] = []
    all_pairs: list[dict[str, Any]] = []
    for task in TASKS:
        task_hash = json_hash({"slug": task["slug"], "title": task["title"], "acceptance": task["acceptance"]})
        control_prompt = ROOT / task["control_prompt"]
        treatment_prompt = ROOT / task["treatment_prompt"]
        prompt_hash = json_hash({"control": sha256_file(control_prompt), "treatment": sha256_file(treatment_prompt)})
        treatment_context_hash = context_hash(str(task["kind"]))
        task_id = create_eval_task(
            conn,
            repo_id="AIOS",
            source="codex_exec_matched_benchmark_v1",
            start_sha=PROTECTED_START_SHA,
            context_profile="peer_repo_only",
            task_type="implementation",
            prompt_summary=str(task["title"]),
            acceptance_criteria=list(task["acceptance"]),
            success_criteria_files=[str(task["control_prompt"]), str(task["treatment_prompt"])],
        )
        run_ids: dict[str, str] = {}
        for condition, context_profile, _prompt_key, worktree_key in (
            ("baseline_repo_only", str(task["control_context"]), "control_prompt", "control_worktree"),
            ("aios_portable_context_packet", str(task["treatment_context"]), "treatment_prompt", "treatment_worktree"),
        ):
            worktree = ARTIFACT_ROOT / str(task[worktree_key])
            artifact_label = ARTIFACT_LABELS[str(task[worktree_key])]
            event_path = ARTIFACT_ROOT / f"{artifact_label}-events.jsonl"
            report_path = ARTIFACT_ROOT / f"{artifact_label}-final.md"
            event_data = parse_events(event_path)
            telemetry = session_telemetry(worktree)
            evidence = worktree_evidence(worktree, event_data)
            run_id = create_eval_run(
                conn,
                task_id=task_id,
                condition=condition,
                mode="implementation",
                harness="codex_exec_jsonl_v1",
                model="gpt-5.6-luna",
                context_profile=context_profile,
                branch_name=str(task[worktree_key]),
                duration_ms=telemetry["duration_ms"],
                total_tokens=telemetry["total_tokens"],
                estimated_cost_usd=None,
                tool_calls=event_data["tool_calls"],
                failed_commands=event_data["failed_commands"],
                files_changed=evidence["changed_file_count"],
                tests_run=event_data["tests"],
                final_status="partial" if event_data["blocked"] else "success",
            )
            run_ids[condition] = run_id
            score = REVIEW_SCORES[task["slug"]]["control" if condition == "baseline_repo_only" else "treatment"]
            record_eval_score(
                conn,
                run_id=run_id,
                **score,
                cost_efficiency=None,
                reviewer_notes="Independent adversarial review score; cost unavailable and intentionally null. Browser/build environment limits are recorded as P2 evidence where applicable.",
            )
            all_runs.append({
                "run_id": run_id,
                "task_id": task_id,
                "condition": condition,
                "context_profile": context_profile,
                "worktree": str(worktree),
                "event_path": str(event_path),
                "event_sha256": sha256_file(event_path),
                "final_report_path": str(report_path),
                "final_report_sha256": sha256_file(report_path),
                "session": telemetry,
                "event_summary": event_data,
                "worktree_evidence": evidence,
            })
        contamination = {
            "status": "failed",
            "protected_start_sha": PROTECTED_START_SHA,
            "same_start_sha_ancestor": all(run["worktree_evidence"]["protected_start_sha_ancestor"] for run in all_runs[-2:]),
            "control_worktree": str(ARTIFACT_ROOT / str(task["control_worktree"])),
            "treatment_worktree": str(ARTIFACT_ROOT / str(task["treatment_worktree"])),
            "root_worktree_untouched": True,
            "context_provenance_verified": False,
            "context_provenance_reason": "The treatment packet was supplied to the run but its identity was not independently captured in the run receipt; context hashes are recorded here for the next gate.",
            "treatment_only_context_files": CONTEXT_FILES[str(task["kind"])],
        }
        pair_id = create_eval_pair(
            conn,
            task_id=task_id,
            control_run_id=run_ids["baseline_repo_only"],
            treatment_run_id=run_ids["aios_portable_context_packet"],
            protected_start_sha=PROTECTED_START_SHA,
            task_hash=task_hash,
            prompt_hash=prompt_hash,
            context_hash=treatment_context_hash,
            parity_metadata={**PARITY_METADATA, "control_prompt": str(task["control_prompt"]), "treatment_prompt": str(task["treatment_prompt"])},
            contamination_status="failed",
            contamination_evidence=contamination,
            independent_review_status="pending",
            independent_review_ref=None,
            report_path=REPORT_REF,
            limitations=["cost telemetry unavailable", "browser/build runtime blocked by isolated environment", "three-task bounded corpus"],
        )
        pair = finalize_eval_pair(
            conn,
            pair_id=pair_id,
            decision="defer",
            contamination_status="failed",
            contamination_evidence=contamination,
            independent_review_status=args.review_status,
            independent_review_ref=REVIEW_REF if args.review_status == "passed" else None,
            report_path=REPORT_REF,
            limitations=["cost telemetry unavailable", "browser/build runtime blocked by isolated environment", "three-task bounded corpus", "M6 promotion remains deferred until browser proof and cutover evidence are complete"],
        )
        all_pairs.append(pair)
    conn.commit()
    promotion_ready = list_promotion_ready_eval_pairs(conn)
    payload = {
        "schema": "aios-m6-promotion-grade-benchmark-v1",
        "protected_start_sha": PROTECTED_START_SHA,
        "parity_metadata": PARITY_METADATA,
        "ledger_db": str(args.db),
        "review_ref": REVIEW_REF,
        "report_path": REPORT_REF,
        "runs": all_runs,
        "pairs": all_pairs,
        "promotion_ready": promotion_ready,
        "decision": "defer",
        "limitations": ["provider cost unavailable", "browser/build runtime unavailable in isolated worktrees", "bounded three-task implementation corpus"],
    }
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"ledger_db": str(args.db), "output": str(args.output), "pair_count": len(all_pairs), "promotion_ready_count": len(promotion_ready)}, indent=2))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
