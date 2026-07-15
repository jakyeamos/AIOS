#!/usr/bin/env python3
"""Ingest the receipt-backed M6 B/C rerun into a durable eval ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.eval_run_service import (
    create_eval_pair,
    create_eval_run,
    create_eval_task,
    ensure_eval_schema,
    finalize_eval_pair,
)

ROOT = Path(__file__).resolve().parents[1]
SHA = "4d8adbca3b89d6259e252f26aaad0db69a9bf102"
DEFAULT_B = Path("/private/tmp/aios-m6-promotion-rerun-b-20260715-v3/artifacts")
DEFAULT_C = Path("/private/tmp/aios-m6-promotion-rerun-c-20260715/artifacts")
REVIEW_REF = "docs/evals/M6_UNBLOCK_RERUN_ADVERSARIAL_REVIEW.md"
REPORT_REF = "docs/evals/M6_UNBLOCK_RERUN_REPORT.md"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def receipt(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    actual = sha256(path)
    expected = path.with_suffix(".json.sha256").read_text(encoding="utf-8").split()[0]
    if actual != expected:
        raise SystemExit(f"Receipt sidecar mismatch: {path}")
    if data["protected_start_sha"] != SHA or data["worktree_head_sha"] != SHA:
        raise SystemExit(f"Receipt SHA mismatch: {path}")
    return {**data, "receipt_sha256": actual}


def event_summary(path: Path) -> dict[str, Any]:
    commands: list[str] = []
    tests: list[str] = []
    failed = 0
    calls = 0
    blocked = False
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item") or {}
        if item.get("type") != "command_execution":
            continue
        calls += 1
        command = str(item.get("command") or "")
        commands.append(command)
        output = str(item.get("aggregated_output") or "")
        if any(token in command.lower() for token in ("pytest", "playwright", "eslint", "tsc", "ruff", "basedpyright", "build")):
            tests.append(command)
        if item.get("exit_code") not in (None, 0):
            failed += 1
        blocked = blocked or any(token in output.lower() for token in ("blocked", "eperm", "err_aborted", "enotfound"))
    return {"tool_calls": calls, "failed_commands": failed, "tests": list(dict.fromkeys(tests)), "commands": commands, "blocked": blocked}


def add_pair(
    conn: sqlite3.Connection,
    *,
    slug: str,
    title: str,
    control_receipt: Path,
    treatment_receipt: Path,
    control_events: Path,
    treatment_events: Path,
    control_worktree: Path,
    treatment_worktree: Path,
    context_hash: str,
    acceptance: list[str],
    contamination_evidence: dict[str, object],
) -> dict[str, Any]:
    control = receipt(control_receipt)
    treatment = receipt(treatment_receipt)
    if control["task_hash"] != treatment["task_hash"] or control["pair_prompt_hash"] != treatment["pair_prompt_hash"]:
        raise SystemExit(f"Pair identity mismatch: {slug}")
    if treatment.get("packet_sha256") is None:
        raise SystemExit(f"Treatment packet hash missing: {treatment_receipt}")
    task_id = create_eval_task(
        conn,
        repo_id="AIOS",
        source="codex_exec_receipt_backed_m6_rerun_v1",
        start_sha=SHA,
        context_profile="peer_repo_only",
        task_type="implementation",
        prompt_summary=title,
        acceptance_criteria=acceptance,
        success_criteria_files=[control["prompt_source_path"], treatment["prompt_source_path"]],
    )
    run_ids: dict[str, str] = {}
    for condition, data, events, worktree, profile in (
        ("baseline_repo_only", control, control_events, control_worktree, "peer_repo_only"),
        ("aios_portable_context_packet", treatment, treatment_events, treatment_worktree, "peer_portable_context_packet"),
    ):
        summary = event_summary(events)
        status = "partial" if summary["blocked"] else "success"
        run_id = create_eval_run(
            conn,
            task_id=task_id,
            condition=condition,
            mode="implementation",
            harness="codex_exec_jsonl_v2",
            model=data["model"],
            context_profile=profile,
            branch_name=str(worktree),
            duration_ms=None,
            total_tokens=None,
            estimated_cost_usd=None,
            tool_calls=summary["tool_calls"],
            failed_commands=summary["failed_commands"],
            files_changed=None,
            tests_run=summary["tests"],
            final_status=status,
        )
        run_ids[condition] = run_id
    pair_id = create_eval_pair(
        conn,
        task_id=task_id,
        control_run_id=run_ids["baseline_repo_only"],
        treatment_run_id=run_ids["aios_portable_context_packet"],
        protected_start_sha=SHA,
        task_hash=control["task_hash"],
        prompt_hash=control["pair_prompt_hash"],
        context_hash=context_hash,
        parity_metadata={
            "model": control["model"],
            "reasoning_effort": control["reasoning_effort"],
            "harness": control["harness"],
            "effort": control["reasoning_effort"],
            "budget": control["budget"],
            "tools": ["shell", "rg", "sed", "git", "python3", "pnpm", "pytest", "playwright"],
            "control_receipt": str(control_receipt),
            "treatment_receipt": str(treatment_receipt),
            "control_receipt_sha256": control["receipt_sha256"],
            "treatment_receipt_sha256": treatment["receipt_sha256"],
            "treatment_packet_id": treatment["packet_id"],
            "treatment_packet_sha256": treatment["packet_sha256"],
        },
        contamination_status="passed",
        contamination_evidence=contamination_evidence,
        independent_review_status="pending",
        independent_review_ref=None,
        report_path=REPORT_REF,
        limitations=["provider cost telemetry unavailable", "quantitative scores intentionally omitted pending independent review"],
    )
    finalized = finalize_eval_pair(
        conn,
        pair_id=pair_id,
        decision="defer",
        contamination_status="passed",
        contamination_evidence=contamination_evidence,
        independent_review_status="pending",
        report_path=REPORT_REF,
        limitations=["provider cost telemetry unavailable", "quantitative scores intentionally omitted pending independent review", "promotion remains deferred until review and score evidence are complete"],
    )
    return {"task_id": task_id, "pair_id": pair_id, "control_run_id": run_ids["baseline_repo_only"], "treatment_run_id": run_ids["aios_portable_context_packet"], "pair": finalized, "receipts": {"control": control, "treatment": treatment}}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--b-artifacts", type=Path, default=DEFAULT_B)
    parser.add_argument("--c-artifacts", type=Path, default=DEFAULT_C)
    args = parser.parse_args()
    if args.db.exists() or args.output.exists():
        raise SystemExit("Refusing to overwrite an existing rerun ledger or evidence file.")
    args.db.parent.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    ensure_eval_schema(conn)
    b = add_pair(
        conn,
        slug="task-b-shadow-approval-owner-rerun",
        title="Receipt-backed shadow-candidate approval owner rerun",
        control_receipt=args.b_artifacts / "receipts/b2-control.json",
        treatment_receipt=args.b_artifacts / "receipts/b2-treatment.json",
        control_events=args.b_artifacts / "b2-control-events.jsonl",
        treatment_events=args.b_artifacts / "b2-treatment-events.jsonl",
        control_worktree=Path("/private/tmp/aios-m6-promotion-rerun-b-20260715-v3/b-control"),
        treatment_worktree=Path("/private/tmp/aios-m6-promotion-rerun-b-20260715-v3/b-treatment"),
        context_hash=receipt(args.b_artifacts / "receipts/b2-treatment.json")["context_manifest_sha256"],
        acceptance=["Python owns the mutation", "ShadowCandidate-or-null is preserved", "source scan removes direct TypeScript update", "focused proof and runtime limits are reported"],
        contamination_evidence={"status": "passed", "protected_start_sha": SHA, "receipt_identity_verified": True, "root_worktree_untouched": True},
    )
    c = add_pair(
        conn,
        slug="task-c-browser-contract-rerun",
        title="Receipt-backed Verify to Review to Closeout browser contract rerun",
        control_receipt=args.c_artifacts / "receipts/c-rerun-control.json",
        treatment_receipt=args.c_artifacts / "receipts/c-rerun-treatment.json",
        control_events=args.c_artifacts / "c-rerun-control-events.jsonl",
        treatment_events=args.c_artifacts / "c-rerun-treatment-events.jsonl",
        control_worktree=Path("/private/tmp/aios-m6-promotion-rerun-c-20260715/c-control"),
        treatment_worktree=Path("/private/tmp/aios-m6-promotion-rerun-c-20260715/c-treatment"),
        context_hash=receipt(args.c_artifacts / "receipts/c-rerun-treatment.json")["context_manifest_sha256"],
        acceptance=["Verify, Review, and Closeout are seeded", "lifecycle and closeout artifact provenance are explicit", "stage rail and exact approval error path are covered", "lint/build/browser limits are reported honestly"],
        contamination_evidence={"status": "passed", "protected_start_sha": SHA, "receipt_identity_verified": True, "root_worktree_untouched": True, "post_rerun_protected_browser_proof": "AIOS_UI_TEST_PORT=3222 pnpm --dir aios-ui test:browser -- m6-verify-review-closeout.spec.ts"},
    )
    conn.commit()
    payload = {"schema": "aios-m6-unblock-rerun-v1", "protected_start_sha": SHA, "ledger_db": str(args.db), "decision": "defer", "pairs": [b, c], "promotion_ready": [], "limitations": ["provider cost telemetry unavailable", "scores intentionally omitted pending independent review"]}
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"ledger_db": str(args.db), "output": str(args.output), "pair_count": 2, "promotion_ready_count": 0}, indent=2))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
