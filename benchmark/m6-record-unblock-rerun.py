#!/usr/bin/env python3
"""Ingest receipt-backed M6 benchmark pairs into a durable eval ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
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
DEFAULT_A = Path("/private/tmp/aios-m6-promotion-rerun-a-20260715-v1/artifacts")
REPORT_REF = "docs/evals/M6_UNBLOCK_THREE_TASK_REPORT.md"
REVIEW_REF = "docs/evals/M6_UNBLOCK_THREE_TASK_ADVERSARIAL_REVIEW.md"


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


def rollout_telemetry(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    tool_calls = 0
    failed_commands = 0
    tests: list[str] = []
    session_id: str | None = None
    duration_ms: int | None = None
    total_tokens: int | None = None
    blocked = False
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        payload = event.get("payload") or {}
        if event.get("type") == "session_meta":
            session_id = payload.get("id") or payload.get("session_id")
        if event.get("type") == "event_msg":
            event_type = payload.get("type")
            if event_type == "token_count":
                total_tokens = payload.get("info", {}).get("total_token_usage", {}).get("total_tokens")
            elif event_type == "task_complete":
                duration_ms = payload.get("duration_ms")
        if event.get("type") != "response_item":
            continue
        response_type = payload.get("type")
        if response_type == "custom_tool_call" and payload.get("name") == "exec":
            tool_calls += 1
            command = str(payload.get("input") or "")
            if any(token in command.lower() for token in ("pytest", "playwright", "eslint", "tsc", "ruff", "basedpyright", "build")):
                tests.append(command)
        if response_type != "custom_tool_call_output":
            continue
        raw_output = payload.get("output") or ""
        output = json.dumps(raw_output)
        if isinstance(raw_output, list):
            output = "\n".join(
                str(item.get("text", ""))
                for item in raw_output
                if isinstance(item, dict)
            )
        exit_codes = [
            int(value)
            for value in re.findall(
                r'(?:\\")?exit_code(?:\\")?\s*[:=]\s*(-?\d+)', output
            )
        ]
        exit_codes.extend(
            int(value)
            for value in re.findall(r'exit code\s+(-?\d+)', output.lower())
        )
        failed_commands += sum(code != 0 for code in exit_codes)
        blocked = blocked or any(token in output.lower() for token in ("blocked", "eperm", "err_aborted", "enotfound"))
    return {
        "session_id": session_id,
        "duration_ms": duration_ms,
        "total_tokens": total_tokens,
        "tool_calls": tool_calls,
        "failed_commands": failed_commands,
        "tests": list(dict.fromkeys(tests)),
        "blocked": blocked,
        "rollout_path": str(path),
    }


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
    control_rollout: Path | None = None,
    treatment_rollout: Path | None = None,
    report_ref: str = REPORT_REF,
    review_ref: str = REVIEW_REF,
    review_status: str = "failed",
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
        rollout = rollout_telemetry(control_rollout if condition == "baseline_repo_only" else treatment_rollout)
        telemetry = {**summary, **{key: value for key, value in rollout.items() if value not in (None, [], "")}}
        status = "partial" if telemetry["blocked"] else "success"
        run_id = create_eval_run(
            conn,
            task_id=task_id,
            condition=condition,
            mode="implementation",
            harness="codex_exec_jsonl_v2",
            model=data["model"],
            context_profile=profile,
            branch_name=str(worktree),
            duration_ms=telemetry.get("duration_ms"),
            total_tokens=telemetry.get("total_tokens"),
            estimated_cost_usd=None,
            tool_calls=telemetry["tool_calls"],
            failed_commands=telemetry["failed_commands"],
            files_changed=None,
            tests_run=telemetry["tests"],
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
            "control_rollout": str(control_rollout) if control_rollout else None,
            "treatment_rollout": str(treatment_rollout) if treatment_rollout else None,
            "control_rollout_telemetry": rollout_telemetry(control_rollout),
            "treatment_rollout_telemetry": rollout_telemetry(treatment_rollout),
        },
        contamination_status="passed",
        contamination_evidence=contamination_evidence,
        independent_review_status=review_status,
        independent_review_ref=review_ref,
        report_path=report_ref,
        limitations=["provider cost telemetry unavailable", "quantitative scores intentionally omitted; review found unresolved findings"],
    )
    finalized = finalize_eval_pair(
        conn,
        pair_id=pair_id,
        decision="defer",
        contamination_status="passed",
        contamination_evidence=contamination_evidence,
        independent_review_status=review_status,
        independent_review_ref=review_ref,
        report_path=report_ref,
        limitations=["provider cost telemetry unavailable", "quantitative scores intentionally omitted", "promotion remains deferred until score evidence and review findings are resolved"],
    )
    return {"task_id": task_id, "pair_id": pair_id, "control_run_id": run_ids["baseline_repo_only"], "treatment_run_id": run_ids["aios_portable_context_packet"], "pair": finalized, "receipts": {"control": control, "treatment": treatment}}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--a-artifacts", type=Path, default=DEFAULT_A)
    parser.add_argument("--b-artifacts", type=Path, default=DEFAULT_B)
    parser.add_argument("--c-artifacts", type=Path, default=DEFAULT_C)
    parser.add_argument(
        "--a-control-rollout",
        type=Path,
        default=Path(
            "/Users/jakyeamos/.codex/sessions/2026/07/15/"
            "rollout-2026-07-15T14-46-14-019f6719-d8a6-7f53-9729-f7ee2dfcf3ab.jsonl"
        ),
    )
    parser.add_argument(
        "--a-treatment-rollout",
        type=Path,
        default=Path(
            "/Users/jakyeamos/.codex/sessions/2026/07/15/"
            "rollout-2026-07-15T14-46-13-019f6719-d1d2-7710-a828-1fba50afcce6.jsonl"
        ),
    )
    args = parser.parse_args()
    if args.db.exists() or args.output.exists():
        raise SystemExit("Refusing to overwrite an existing rerun ledger or evidence file.")
    args.db.parent.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    ensure_eval_schema(conn)
    a = add_pair(
        conn,
        slug="task-a-workflow-skill-owner-rerun",
        title="Receipt-backed workflow skill-candidate owner rerun",
        control_receipt=args.a_artifacts / "receipts/a-control.json",
        treatment_receipt=args.a_artifacts / "receipts/a-treatment.json",
        control_events=args.a_artifacts / "a-control-events.jsonl",
        treatment_events=args.a_artifacts / "a-treatment-events.jsonl",
        control_worktree=Path("/private/tmp/aios-m6-promotion-rerun-a-20260715-v1/a-control"),
        treatment_worktree=Path("/private/tmp/aios-m6-promotion-rerun-a-20260715-v1/a-treatment"),
        context_hash=receipt(args.a_artifacts / "receipts/a-treatment.json")["context_manifest_sha256"],
        acceptance=[
            "Python owns workflow skill-candidate promote and dismiss mutations",
            "Existing tRPC response and skills.json behavior are preserved",
            "Direct TypeScript candidate mutation is removed",
            "Receipt verification, focused tests, and runtime limits are reported",
        ],
        contamination_evidence={
            "status": "passed",
            "protected_start_sha": SHA,
            "receipt_identity_verified": True,
            "root_worktree_untouched": True,
            "actual_rollback_parent_sha": "4cd4183f4cb890197507135579a877ac4ade046c",
            "control_rollout_path": str(args.a_control_rollout),
            "treatment_rollout_path": str(args.a_treatment_rollout),
            "treatment_report_rollback_parent_mismatch": True,
        },
        control_rollout=args.a_control_rollout,
        treatment_rollout=args.a_treatment_rollout,
    )
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
    payload = {
        "schema": "aios-m6-three-task-unblock-rerun-v1",
        "protected_start_sha": SHA,
        "ledger_db": str(args.db),
        "decision": "defer",
        "pairs": [a, b, c],
        "promotion_ready": [],
        "limitations": [
            "provider cost telemetry unavailable",
            "scores intentionally omitted; independent review is recorded separately",
            "A treatment report uses the protected start SHA as rollback parent; git confirms the actual parent SHA separately",
            "A UI verification was blocked by the external node_modules EPERM environment limit",
        ],
    }
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"ledger_db": str(args.db), "output": str(args.output), "pair_count": 3, "promotion_ready_count": 0}, indent=2))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
