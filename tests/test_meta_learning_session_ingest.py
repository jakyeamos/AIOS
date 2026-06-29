from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.meta_learning_proposals import read_proposals_jsonl  # noqa: E402
from services.meta_learning_session_ingest import propose_session_meta_learning  # noqa: E402


def _load_cron_module() -> Any:
    path = ROOT / "bin" / "cron-ingest-codex.py"
    spec = importlib.util.spec_from_file_location("cron_ingest_codex", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_session_meta_learning_writes_reviewable_proposals(tmp_path: Path) -> None:
    result = propose_session_meta_learning(
        {
            "id": "codex-session-1",
            "messages": [
                {"role": "user", "text": "In this repo, always use pnpm for scripts."},
                {"role": "assistant", "text": "FAILED tests/test_cli.py::test_command"},
                {"role": "assistant", "text": "FAILED tests/test_cli.py::test_command"},
            ],
            "candidate_skills_to_extract": ["Codex rollout review loop"],
        },
        proposal_root=tmp_path,
    )

    assert result.signal_count >= 3
    assert result.proposal_count >= 3
    assert result.proposal_path == str(tmp_path / "codex-session-proposals.jsonl")
    records = read_proposals_jsonl(tmp_path / "codex-session-proposals.jsonl")
    assert {record.target_layer for record in records} >= {"project", "eval", "skill"}
    assert all(record.requires_manual_approval for record in records)


def test_cron_emit_meta_learning_proposals_uses_codex_proposal_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cron = _load_cron_module()
    monkeypatch.setattr(cron, "META_LEARNING_PROPOSAL_DIR", tmp_path)
    monkeypatch.setattr(cron, "_log", lambda _msg: None)

    cron._emit_meta_learning_proposals(
        {
            "id": "codex-session-2",
            "messages": [
                {"role": "user", "text": "In this repo, always use pnpm for scripts."},
            ],
        }
    )

    output_path = tmp_path / "codex-session-proposals.jsonl"
    payload = json.loads(output_path.read_text(encoding="utf-8").splitlines()[0])
    assert payload["proposal_id"].startswith("meta-proposal-")
    assert payload["status"] == "pending_review"
    assert payload["requires_manual_approval"] is True


def test_cron_total_words_uses_normalized_message_text() -> None:
    cron = _load_cron_module()

    assert cron._total_words({"messages": [{"role": "user", "text": "one two three"}]}) == 3
