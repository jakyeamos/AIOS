from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import services.aios_cli as aios_cli  # noqa: E402
from services.meta_learning_signals import (  # noqa: E402
    extract_meta_learning_signals,
    signals_to_dicts,
)


def _by_type(raw: dict, signal_type: str) -> list[dict]:
    return [
        signal
        for signal in signals_to_dicts(extract_meta_learning_signals(raw))
        if signal["type"] == signal_type
    ]


def test_extracts_explicit_corrections_with_target_layer() -> None:
    raw = {
        "session_id": "s1",
        "messages": [
            {
                "role": "user",
                "text": "In this repo, always use pnpm for JavaScript commands.",
                "timestamp": "2026-06-23T00:00:00Z",
            }
        ],
    }

    corrections = _by_type(raw, "explicit_correction")

    assert len(corrections) == 2
    assert {signal["recommended_target_layer"] for signal in corrections} == {
        "project_rule",
        "command_suggestion",
    }
    assert all(signal["source_sessions"] == ["s1"] for signal in corrections)


def test_repeated_corrections_are_aggregated_with_stable_ids() -> None:
    raw = {
        "sessions": [
            {
                "session_id": "s1",
                "messages": [{"role": "user", "text": "Never use npm in this repo."}],
            },
            {
                "session_id": "s2",
                "messages": [{"role": "user", "text": "Never use npm in this repo."}],
            },
        ]
    }

    first = _by_type(raw, "repeated_pattern")
    second = _by_type(raw, "repeated_pattern")

    assert len(first) == 1
    assert first[0]["signal_id"] == second[0]["signal_id"]
    assert first[0]["frequency"] == 2
    assert first[0]["source_sessions"] == ["s1", "s2"]


def test_extracts_approval_command_repetition_and_tool_friction() -> None:
    raw = {
        "session_id": "s1",
        "messages": [{"role": "user", "text": "Approved, ship it."}],
        "commands": ["pnpm test", "pnpm test"],
        "tool_events": [
            {"type": "tool_call", "tool": "bash", "summary": "pytest failed"},
            {"type": "tool_call", "tool": "bash", "summary": "pytest failed"},
        ],
    }

    signals = signals_to_dicts(extract_meta_learning_signals(raw))
    by_type = {signal["type"]: signal for signal in signals}

    assert by_type["approval"]["frequency"] == 1
    assert by_type["command_repetition"]["summary"] == "Repeated command: pnpm test"
    assert by_type["tool_friction"]["frequency"] == 2
    assert by_type["tool_friction"]["recommended_target_layer"] == "workflow_rule"


def test_extracts_assistant_tool_errors_and_candidate_skills() -> None:
    raw = {
        "session_id": "s1",
        "messages": [
            {"role": "assistant", "text": "FAILED tests/test_app.py::test_flow"},
            {"role": "assistant", "text": "FAILED tests/test_app.py::test_flow"},
        ],
        "candidate_skills_to_extract": ["Codex rollout review loop"],
    }

    signals = signals_to_dicts(extract_meta_learning_signals(raw))
    by_type = {signal["type"]: signal for signal in signals}

    assert by_type["tool_friction"]["frequency"] == 2
    assert by_type["candidate_skill"]["recommended_target_layer"] == "skill_or_agent_suggestion"
    assert by_type["candidate_skill"]["summary"] == "Candidate skill: Codex rollout review loop"


def test_extracts_context_miss_model_mismatch_and_scope_restatement() -> None:
    raw = {
        "session_id": "s1",
        "messages": [
            {"role": "user", "text": "You missed the context from the phase plan."},
            {"role": "user", "text": "That is not what I asked; stay in scope."},
            {
                "role": "user",
                "text": "This was a model mismatch; should have used a stronger model.",
            },
        ],
        "context_events": [
            {"type": "second_brain_miss", "summary": "second-brain miss for project convention"},
            {"type": "irrelevant_context", "summary": "loaded unrelated context packet"},
        ],
        "model_events": [{"type": "model_mismatch", "summary": "cheap model failed planning task"}],
    }

    signals = signals_to_dicts(extract_meta_learning_signals(raw))
    types = {signal["type"] for signal in signals}

    assert "context_miss" in types
    assert "model_mismatch" in types
    assert "repeated_pattern" in types
    assert any(signal["recommended_target_layer"] == "model_routing_policy" for signal in signals)


def test_extracts_contradictions_from_conflicting_directives() -> None:
    raw = {
        "session_id": "s1",
        "messages": [
            {"role": "user", "text": "Always use npm for scripts."},
            {"role": "user", "text": "Never use npm for scripts."},
        ],
    }

    contradictions = _by_type(raw, "contradiction")

    assert len(contradictions) == 1
    assert contradictions[0]["risk_level"] == "high"
    assert contradictions[0]["recommended_target_layer"] == "manual_review"


def test_cli_payload_analyzes_json_session_trace(tmp_path: Path) -> None:
    path = tmp_path / "session.json"
    path.write_text(
        json.dumps(
            {
                "session_id": "s1",
                "messages": [{"role": "user", "text": "Don't use broad global rules."}],
            }
        ),
        encoding="utf-8",
    )

    payload = aios_cli._meta_analyze_session_payload(argparse.Namespace(input=str(path)))

    assert payload["signal_count"] == 1
    assert payload["signals"][0]["type"] == "explicit_correction"
    assert payload["signals"][0]["signal_id"].startswith("meta-signal-")
