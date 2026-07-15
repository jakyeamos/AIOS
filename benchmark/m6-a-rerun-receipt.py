#!/usr/bin/env python3
"""Freeze a receipt-backed workflow-skill owner benchmark pair."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SHA = "4d8adbca3b89d6259e252f26aaad0db69a9bf102"
CONTEXT_FILES = (
    "docs/modernization/ADR-002-canonical-state-and-migration-authority.md",
    "docs/modernization/ADR-005-subsystem-ownership-and-parallel-v2-strategy.md",
    "docs/modernization/PROGRESS.md",
    ".tracker/PROJECT_TRUTH.md",
    ".wayfinder/aios-modernization/tickets/019-migrate-standards-backfill-write-owner.md",
    ".wayfinder/aios-modernization/tickets/020-migrate-project-component-settings-owner.md",
    ".wayfinder/aios-modernization/tickets/021-migrate-automation-trigger-owner.md",
    ".wayfinder/aios-modernization/tickets/022-migrate-pattern-approval-owner.md",
)
ACCEPTANCE = [
    "validated Python service/CLI and typed server adapter own both mutations",
    "success, missing row, invalid payload, and skill-file behavior tests pass",
    "UI lint/typecheck, architecture, build, and relevant browser checks pass or are explicitly recorded as environment-blocked",
    "source scan proves the workflow router no longer owns direct updates",
    "report exact commands, actual protected parent SHA, and remaining risks",
]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_digest(value: object) -> str:
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def git(worktree: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(worktree), *args], check=True, capture_output=True, text=True)
    return result.stdout.strip()


def protected_bytes(path: str) -> bytes:
    return subprocess.run(["git", "-C", str(ROOT), "show", f"{SHA}:{path}"], check=True, capture_output=True).stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--treatment", type=Path, required=True)
    args = parser.parse_args()
    if args.artifact_root.exists():
        raise SystemExit(f"Refusing to overwrite existing artifact root: {args.artifact_root}")

    artifact_root = args.artifact_root
    (artifact_root / "prompts").mkdir(parents=True)
    (artifact_root / "receipts").mkdir()
    control_source = ROOT / "benchmark/m6-promotion-prompts/task-a-rerun-control.md"
    treatment_source = ROOT / "benchmark/m6-promotion-prompts/task-a-rerun-treatment.md"
    control_snapshot = artifact_root / "prompts/task-a-control.md"
    treatment_snapshot = artifact_root / "prompts/task-a-treatment.md"
    control_snapshot.write_bytes(control_source.read_bytes())
    treatment_snapshot.write_bytes(treatment_source.read_bytes())
    prompt_hashes = {"control": digest(control_snapshot.read_bytes()), "treatment": digest(treatment_snapshot.read_bytes())}
    pair_prompt_hash = json_digest(prompt_hashes)
    context_entries = [
        {"path": path, "sha256": digest(protected_bytes(path)), "byte_count": len(protected_bytes(path))}
        for path in CONTEXT_FILES
    ]
    context_manifest_hash = json_digest([[entry["path"], entry["sha256"]] for entry in context_entries])
    task_hash = json_digest({"slug": "task-a-workflow-skill-owner", "acceptance": ACCEPTANCE})
    created_at = datetime.now(UTC).isoformat()
    common: dict[str, Any] = {
        "schema": "aios-m6-a-pre-run-receipt-v1",
        "created_at_utc": created_at,
        "protected_start_sha": SHA,
        "task_slug": "task-a-workflow-skill-owner",
        "task_hash": task_hash,
        "model": "gpt-5.6-luna",
        "reasoning_effort": "high",
        "budget": {"tokens": 20_000, "seconds": 900},
        "sandbox": "workspace-write",
        "harness": "codex_exec_jsonl_v2",
        "tools": ["shell", "rg", "sed", "git", "python3", "pnpm", "pytest", "playwright"],
        "expected_dependency_mounts": [".venv", "aios-ui/node_modules"],
        "context_manifest_sha256": context_manifest_hash,
        "context_manifest_hash": context_manifest_hash,
        "treatment_context_files": context_entries,
        "pair_prompt_hash": pair_prompt_hash,
        "protected_sha": SHA,
    }
    specs = (
        ("control", args.control, control_snapshot, "peer_repo_only", None),
        ("treatment", args.treatment, treatment_snapshot, "peer_portable_context_packet", "m6-workflow-skill-owner-v1"),
    )
    for condition, worktree, prompt_snapshot, context_profile, packet_id in specs:
        status = git(worktree, "status", "--porcelain=v1", "-uall")
        head = git(worktree, "rev-parse", "HEAD")
        if head != SHA or status:
            raise SystemExit(f"Worktree preflight failed for {worktree}: head={head!r} status={status!r}")
        label = "a-control" if condition == "control" else "a-treatment"
        receipt_id = f"m6-a-rerun-{condition}"
        receipt_path = artifact_root / f"receipts/{label}.json"
        event_path = artifact_root / f"{label}-events.jsonl"
        packet_hash = (
            json_digest({"packet_id": packet_id, "context_manifest_sha256": context_manifest_hash, "context_files": context_entries})
            if packet_id is not None
            else None
        )
        receipt = {
            **common,
            "receipt_id": receipt_id,
            "condition": "baseline_repo_only" if condition == "control" else "aios_portable_context_packet",
            "context_profile": context_profile,
            "worktree_path": str(worktree),
            "worktree_head_sha": head,
            "clean_status_before": status,
            "prompt_source_path": str(control_source if condition == "control" else treatment_source),
            "prompt_snapshot_path": str(prompt_snapshot),
            "prompt_sha256": digest(prompt_snapshot.read_bytes()),
            "prompt_hash": digest(prompt_snapshot.read_bytes()),
            "packet_id": packet_id,
            "packet_sha256": packet_hash,
            "launch_command_argv": [
                "codex", "exec", "--json", "--model", "gpt-5.6-luna", "-c", "model_reasoning_effort=high",
                "-s", "workspace-write", "-C", str(worktree), "-o", str(artifact_root / f"{label}-final.md"), "-",
            ],
            "events_path": str(event_path),
            "final_path": str(artifact_root / f"{label}-final.md"),
            "stderr_path": str(artifact_root / f"{label}-stderr.log"),
        }
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        receipt_sha = digest(receipt_path.read_bytes())
        receipt_path.with_suffix(".json.sha256").write_text(f"{receipt_sha}  {receipt_path.name}\n", encoding="utf-8")
        event_path.write_text(
            json.dumps(
                {
                    "type": "benchmark.pre_run_receipt",
                    "receipt_id": receipt_id,
                    "receipt_path": str(receipt_path),
                    "receipt_sha256": receipt_sha,
                    "protected_start_sha": SHA,
                    "task_hash": task_hash,
                    "prompt_sha256": receipt["prompt_sha256"],
                    "packet_sha256": packet_hash,
                    "context_manifest_sha256": context_manifest_hash,
                    "condition": receipt["condition"],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        print(json.dumps({"condition": condition, "receipt": str(receipt_path), "receipt_sha256": receipt_sha, "events": str(event_path), "packet_sha256": packet_hash}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
