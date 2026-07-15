#!/usr/bin/env python3
"""Validate authoritative provider telemetry before it can enter an M6 ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

SCHEMA = "aios-m6-provider-telemetry-v1"
SOURCE_KINDS = {"provider_api_response", "provider_usage_export"}
CONDITIONS = {"baseline_repo_only", "aios_portable_context_packet"}
REQUIRED_RUN_FIELDS = {
    "pair_id",
    "run_id",
    "condition",
    "provider_request_id",
    "model",
    "input_tokens",
    "output_tokens",
    "cached_input_tokens",
    "total_tokens",
    "cost_usd",
    "score",
    "score_source",
    "score_evidence_path",
    "score_evidence_sha256",
    "provider_response_path",
    "provider_response_sha256",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _required_string(value: object, label: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty string")


def _required_nonnegative_number(value: object, label: str, errors: list[str]) -> None:
    if not isinstance(value, int | float) or isinstance(value, bool) or value < 0:
        errors.append(f"{label} must be a non-negative number")


def _validate_hash(
    path_value: object,
    expected_value: object,
    label: str,
    errors: list[str],
) -> None:
    if not isinstance(path_value, str) or not path_value.strip():
        errors.append(f"{label}_path must be a non-empty string")
        return
    if not isinstance(expected_value, str) or len(expected_value) != 64:
        errors.append(f"{label}_sha256 must be a SHA-256 hex string")
        return
    path = Path(path_value).expanduser()
    if not path.is_file():
        errors.append(f"{label}_path does not exist: {path}")
        return
    actual = _sha256(path)
    if actual != expected_value.lower():
        errors.append(f"{label}_sha256 mismatch for {path}")


def _ledger_run_ids(ledger_path: Path) -> set[str]:
    uri = f"file:{ledger_path}?immutable=1"
    with sqlite3.connect(uri, uri=True) as conn:
        rows = conn.execute(
            """
            SELECT control_run_id AS run_id FROM eval_pairs
            UNION
            SELECT treatment_run_id AS run_id FROM eval_pairs
            """
        ).fetchall()
    return {str(row[0]) for row in rows}


def validate_manifest(manifest: dict[str, Any], *, ledger_path: Path | None = None) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema") != SCHEMA:
        errors.append(f"schema must equal {SCHEMA}")
    if manifest.get("status") != "complete":
        errors.append("status must be complete; templates and pending manifests are not evidence")

    source = manifest.get("source")
    if not isinstance(source, dict):
        errors.append("source must be an object")
        source = {}
    if source.get("kind") not in SOURCE_KINDS:
        errors.append(f"source.kind must be one of {sorted(SOURCE_KINDS)}")
    for field in ("provider", "captured_at", "export_path", "export_sha256"):
        _required_string(source.get(field), f"source.{field}", errors)
    _validate_hash(source.get("export_path"), source.get("export_sha256"), "source.export", errors)

    runs = manifest.get("runs")
    if not isinstance(runs, list) or not runs:
        errors.append("runs must contain at least one provider-backed run")
        runs = []
    seen_run_ids: set[str] = set()
    for index, run in enumerate(runs):
        label = f"runs[{index}]"
        if not isinstance(run, dict):
            errors.append(f"{label} must be an object")
            continue
        missing = sorted(REQUIRED_RUN_FIELDS - set(run))
        errors.extend(f"{label}.{field} is required" for field in missing)
        for field in ("pair_id", "run_id", "provider_request_id", "model", "score_source"):
            _required_string(run.get(field), f"{label}.{field}", errors)
        condition = run.get("condition")
        if condition not in CONDITIONS:
            errors.append(f"{label}.condition must be one of {sorted(CONDITIONS)}")
        run_id = run.get("run_id")
        if isinstance(run_id, str):
            if run_id in seen_run_ids:
                errors.append(f"duplicate run_id: {run_id}")
            seen_run_ids.add(run_id)
        for field in ("input_tokens", "output_tokens", "cached_input_tokens", "total_tokens", "cost_usd", "score"):
            _required_nonnegative_number(run.get(field), f"{label}.{field}", errors)
        score = run.get("score")
        if isinstance(score, (int, float)) and not isinstance(score, bool) and not 0 <= score <= 1:
            errors.append(f"{label}.score must be between 0 and 1")
        _validate_hash(run.get("score_evidence_path"), run.get("score_evidence_sha256"), f"{label}.score_evidence", errors)
        _validate_hash(run.get("provider_response_path"), run.get("provider_response_sha256"), f"{label}.provider_response", errors)

    if ledger_path is not None and ledger_path.is_file() and isinstance(runs, list):
        expected = _ledger_run_ids(ledger_path)
        supplied = {str(run.get("run_id")) for run in runs if isinstance(run, dict)}
        missing = sorted(expected - supplied)
        extra = sorted(supplied - expected)
        if missing:
            errors.append(f"manifest is missing ledger run_ids: {missing}")
        if extra:
            errors.append(f"manifest contains unknown ledger run_ids: {extra}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--ledger", type=Path, default=None)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"invalid manifest: {error}")
        return 2
    if not isinstance(manifest, dict):
        print("invalid manifest: top-level value must be an object")
        return 2
    errors = validate_manifest(manifest, ledger_path=args.ledger)
    if errors:
        print(json.dumps({"valid": False, "errors": errors}, indent=2))
        return 2
    print(json.dumps({"valid": True, "run_count": len(manifest["runs"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
