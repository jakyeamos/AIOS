from __future__ import annotations

import hashlib
import json
from pathlib import Path

from benchmark.m6_provider_telemetry import validate_manifest


def _write_evidence(path: Path, content: str) -> str:
    path.write_text(content, encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_pending_template_is_rejected(tmp_path: Path) -> None:
    manifest = {
        "schema": "aios-m6-provider-telemetry-v1",
        "status": "pending",
        "source": {},
        "runs": [],
    }

    errors = validate_manifest(manifest)

    assert "status must be complete; templates and pending manifests are not evidence" in errors
    assert "runs must contain at least one provider-backed run" in errors


def test_complete_manifest_requires_matching_hashed_evidence(tmp_path: Path) -> None:
    export = tmp_path / "provider-response.json"
    score = tmp_path / "score-review.json"
    export_sha = _write_evidence(export, '{"id":"provider-response-1"}\n')
    score_sha = _write_evidence(score, '{"score":0.9,"review":"independent"}\n')
    manifest = {
        "schema": "aios-m6-provider-telemetry-v1",
        "status": "complete",
        "source": {
            "kind": "provider_api_response",
            "provider": "example-provider",
            "captured_at": "2026-07-15T00:00:00Z",
            "export_path": str(export),
            "export_sha256": export_sha,
        },
        "runs": [
            {
                "pair_id": "pair-1",
                "run_id": "run-1",
                "condition": "baseline_repo_only",
                "provider_request_id": "req-1",
                "model": "example-model",
                "input_tokens": 100,
                "output_tokens": 50,
                "cached_input_tokens": 0,
                "total_tokens": 150,
                "cost_usd": 0.01,
                "score": 0.9,
                "score_source": "independent_review",
                "score_evidence_path": str(score),
                "score_evidence_sha256": score_sha,
                "provider_response_path": str(export),
                "provider_response_sha256": export_sha,
            }
        ],
    }

    assert validate_manifest(manifest) == []


def test_hash_mismatch_is_rejected(tmp_path: Path) -> None:
    export = tmp_path / "provider-response.json"
    score = tmp_path / "score-review.json"
    _write_evidence(export, "provider\n")
    _write_evidence(score, "score\n")
    manifest = json.loads(
        json.dumps(
            {
                "schema": "aios-m6-provider-telemetry-v1",
                "status": "complete",
                "source": {
                    "kind": "provider_api_response",
                    "provider": "example-provider",
                    "captured_at": "2026-07-15T00:00:00Z",
                    "export_path": str(export),
                    "export_sha256": "0" * 64,
                },
                "runs": [],
            }
        )
    )

    errors = validate_manifest(manifest)

    assert any("source.export_sha256 mismatch" in error for error in errors)
