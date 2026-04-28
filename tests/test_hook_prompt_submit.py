from __future__ import annotations

import importlib.util
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_hook_module():
    module_path = ROOT / "bin" / "hook-prompt-submit.py"
    bin_path = str(ROOT / "bin")
    if bin_path not in sys.path:
        sys.path.insert(0, bin_path)
    spec = importlib.util.spec_from_file_location("hook_prompt_submit", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_best_prompt_template_scores_classification_and_tags(tmp_path: Path) -> None:
    module = _load_hook_module()
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "templates": [
                    {
                        "id": "coding_debug",
                        "name": "Coding Debug",
                        "version": "1.0",
                        "classification": "debug",
                        "tags": ["debug", "error", "fix"],
                        "purpose": "Debug failures",
                        "required_inputs": [{"symptom": "desc"}, {"context": "desc"}],
                    },
                    {
                        "id": "research",
                        "name": "Research",
                        "version": "1.0",
                        "classification": "plan",
                        "tags": ["research", "synthesize"],
                        "purpose": "Research synthesis",
                        "required_inputs": [{"topic": "desc"}, {"sources": "desc"}],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    module.PROMPT_REGISTRY_PATH = str(registry_path)
    module.PROMPTS_ROOT = str(tmp_path)

    match = module._best_prompt_template("debug", "please debug this error and propose fix")
    assert match is not None
    assert match["id"] == "coding_debug"


def test_retrieve_context_skips_template_hint_without_data_link(tmp_path: Path) -> None:
    module = _load_hook_module()
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "templates": [
                    {
                        "id": "reasoning",
                        "name": "Decision Reasoning",
                        "version": "1.0",
                        "classification": "plan",
                        "tags": ["reasoning", "decision"],
                        "purpose": "Turn ambiguity into recommendation.",
                        "required_inputs": [{"question": "desc"}, {"constraints": "desc"}],
                        "optional_inputs": [{"options": "desc"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    module.PROMPT_REGISTRY_PATH = str(registry_path)
    module.PROMPTS_ROOT = str(tmp_path)

    conn = sqlite3.connect(":memory:")
    context, source = module.retrieve_context(
        "plan",
        "Need reasoning for a decision under constraints",
        "AIOS",
        conn,
        {"prompt_retrieval": {"enabled": False}, "reusable_prompt_hint": {"enabled": False}},
    )
    conn.close()

    assert source == ""
    assert context == ""


def test_retrieve_context_includes_data_backed_template_hint(tmp_path: Path) -> None:
    module = _load_hook_module()
    template_body = "Use this decision workflow when constraints and tradeoffs matter.\n"
    (tmp_path / "reasoning.md").write_text(template_body, encoding="utf-8")
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "templates": [
                    {
                        "id": "reasoning",
                        "name": "Decision Reasoning",
                        "version": "1.0",
                        "classification": "plan",
                        "tags": ["reasoning", "decision"],
                        "purpose": "Turn ambiguity into recommendation.",
                        "required_inputs": [{"question": "desc"}, {"constraints": "desc"}],
                        "optional_inputs": [{"options": "desc"}],
                        "file": "reasoning.md",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    module.PROMPT_REGISTRY_PATH = str(registry_path)
    module.PROMPTS_ROOT = str(tmp_path)

    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE prompt_library_links (
          id TEXT PRIMARY KEY,
          prompt_hash TEXT NOT NULL,
          obsidian_note_path TEXT,
          promoted_at TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO prompt_library_links (id, prompt_hash) VALUES (?, ?)",
        ("link-1", hashlib.sha256(template_body.encode("utf-8")).hexdigest()),
    )
    context, source = module.retrieve_context(
        "plan",
        "Need reasoning for a decision under constraints",
        "AIOS",
        conn,
        {"prompt_retrieval": {"enabled": False}, "reusable_prompt_hint": {"enabled": False}},
    )
    conn.close()

    assert source == "prompt_library"
    assert "Prompt template match: Decision Reasoning v1.0" in context
    assert "Required: question, constraints" in context


def test_reusable_candidate_rejects_control_chatter() -> None:
    module = _load_hook_module()

    assert module.is_reusable_candidate("continue") == 0
    assert module.is_reusable_candidate("keep going") == 0
    assert module.is_reusable_candidate("/gsd-plan-phase 110") == 0


def test_reusable_candidate_requires_task_shape() -> None:
    module = _load_hook_module()

    assert module.is_reusable_candidate("please review this") == 0
    assert module.is_reusable_candidate("Please review this architecture proposal and identify the main risks") == 1
