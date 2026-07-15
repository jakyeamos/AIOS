#!/usr/bin/env python3
"""Freeze receipt-backed control/treatment inputs for the M6 C rerun."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHA = "4d8adbca3b89d6259e252f26aaad0db69a9bf102"
CONTEXT_FILES = (
    "docs/modernization/ADR-003-task-centred-ia-and-accessible-design-system.md",
    "docs/modernization/ADR-004-reproducible-ui-validation-contract.md",
    "docs/modernization/PROGRESS.md",
    ".tracker/PROJECT_TRUTH.md",
    ".wayfinder/aios-modernization/tickets/019-migrate-standards-backfill-write-owner.md",
    ".wayfinder/aios-modernization/tickets/020-migrate-project-component-settings-owner.md",
    ".wayfinder/aios-modernization/tickets/021-migrate-automation-trigger-owner.md",
    ".wayfinder/aios-modernization/tickets/022-migrate-pattern-approval-owner.md",
)


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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
    (args.artifact_root / "prompts").mkdir(parents=True)
    (args.artifact_root / "receipts").mkdir()
    sources = {
        "control": ROOT / "benchmark/m6-promotion-prompts/task-c-rerun-control.md",
        "treatment": ROOT / "benchmark/m6-promotion-prompts/task-c-rerun-treatment.md",
    }
    snapshots = {condition: args.artifact_root / "prompts" / f"task-c-{condition}.md" for condition in sources}
    for condition, source in sources.items():
        snapshots[condition].write_bytes(source.read_bytes())
    prompt_hashes = {condition: digest(snapshot.read_bytes()) for condition, snapshot in snapshots.items()}
    context_entries = [{"path": path, "sha256": digest(protected_bytes(path))} for path in CONTEXT_FILES]
    context_hash = json_digest([[entry["path"], entry["sha256"]] for entry in context_entries])
    task_hash = json_digest({"slug": "task-c-browser-contract-rerun", "prompt_hashes": prompt_hashes})
    pair_hash = json_digest(prompt_hashes)
    created_at = datetime.now(UTC).isoformat()
    for condition, worktree in (("control", args.control), ("treatment", args.treatment)):
        status = git(worktree, "status", "--porcelain=v1", "-uall")
        head = git(worktree, "rev-parse", "HEAD")
        if head != SHA or status:
            raise SystemExit(f"Worktree preflight failed for {worktree}: head={head!r} status={status!r}")
        packet_id = None if condition == "control" else "m6-browser-contract-rerun-v1"
        packet_hash = (
            json_digest({"packet_id": packet_id, "context_manifest_sha256": context_hash, "context_files": context_entries})
            if packet_id is not None
            else None
        )
        label = f"c-rerun-{condition}"
        receipt = {
            "schema": "aios-m6-c-pre-run-receipt-v1",
            "receipt_id": f"m6-c-rerun-{condition}",
            "created_at_utc": created_at,
            "protected_start_sha": SHA,
            "protected_sha": SHA,
            "worktree_head_sha": head,
            "worktree_path": str(worktree),
            "clean_status_before": status,
            "condition": "baseline_repo_only" if condition == "control" else "aios_portable_context_packet",
            "context_profile": "peer_repo_only" if condition == "control" else "peer_portable_context_packet",
            "packet_id": packet_id,
            "packet_sha256": packet_hash,
            "context_manifest_sha256": context_hash,
            "context_manifest_hash": context_hash,
            "context_files": context_entries,
            "task_slug": "task-c-browser-contract-rerun",
            "task_hash": task_hash,
            "prompt_source_path": str(sources[condition]),
            "prompt_snapshot_path": str(snapshots[condition]),
            "prompt_sha256": prompt_hashes[condition],
            "prompt_hash": prompt_hashes[condition],
            "pair_prompt_hash": pair_hash,
            "model": "gpt-5.6-luna",
            "reasoning_effort": "high",
            "budget": {"tokens": 20_000, "seconds": 900},
            "sandbox": "workspace-write",
            "harness": "codex_exec_jsonl_v2",
            "events_path": str(args.artifact_root / f"{label}-events.jsonl"),
            "final_path": str(args.artifact_root / f"{label}-final.md"),
            "stderr_path": str(args.artifact_root / f"{label}-stderr.log"),
        }
        receipt_path = args.artifact_root / "receipts" / f"{label}.json"
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        receipt_hash = digest(receipt_path.read_bytes())
        receipt_path.with_suffix(".json.sha256").write_text(f"{receipt_hash}  {receipt_path.name}\n", encoding="utf-8")
        event = {
            "type": "benchmark.pre_run_receipt",
            "receipt_id": receipt["receipt_id"],
            "receipt_path": str(receipt_path),
            "receipt_sha256": receipt_hash,
            "protected_start_sha": SHA,
            "task_hash": task_hash,
            "prompt_sha256": prompt_hashes[condition],
            "packet_sha256": packet_hash,
            "context_manifest_sha256": context_hash,
            "condition": receipt["condition"],
        }
        Path(receipt["events_path"]).write_text(json.dumps(event) + "\n", encoding="utf-8")
        print(json.dumps({"condition": condition, "receipt": str(receipt_path), "receipt_sha256": receipt_hash, "packet_sha256": packet_hash}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
