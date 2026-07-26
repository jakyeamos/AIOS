from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from services.context_compiler import ContextCompiler  # noqa: E402


def _compiler() -> ContextCompiler:
    return ContextCompiler(
        system_instructions="Stable system instruction.",
        aios_operating_rules=("Stable operating rule.",),
        user_preferences=("Stable user preference.",),
        project_memory_summaries={"aios": "Stable memory summary."},
        project_context_facts=[
            {
                "id": "truth-1",
                "fact_text": "AIOS keeps stable truth before dynamic memory.",
                "validity_status": "active",
                "project_scope": "aios",
            }
        ],
        raw_sources=[{"id": "raw-1", "source_type": "project_context", "source_path": "PROJECT.md"}],
        retrieved_facts=[
            {
                "id": "dyn-duplicate",
                "fact_text": "AIOS keeps stable truth before dynamic memory.",
                "validity_status": "active",
                "project_scope": "aios",
                "source_id": "raw-1",
            },
            {
                "id": "dyn-unique",
                "fact_text": "Dynamic task memory follows the stable prefix.",
                "validity_status": "active",
                "project_scope": "aios",
                "source_id": "raw-1",
            },
        ],
    )


def test_stable_prefix_deterministic_across_calls() -> None:
    compiler = _compiler()

    first = compiler.compile("First task.", "aios", 2_000)
    second = compiler.compile("Second task.", "aios", 2_000)

    assert first[:5] == second[:5]
    assert first[6]["content"] != second[6]["content"]


def test_dynamic_after_stable() -> None:
    sections = _compiler().compile("Do the task.", "aios", 2_000)
    headings = [section["content"].splitlines()[0] for section in sections]

    assert headings[:5] == [
        "## System / Developer Instructions",
        "## AIOS Operating Rules",
        "## User Preferences",
        "## Project Memory Summary",
        "## Project Context Packet",
    ]
    assert headings[5] == "## Task-Specific Retrieved Memory"
    assert headings[6] == "## Current User Request / Task Description"


def test_dedup_prevents_duplicate_facts() -> None:
    sections = _compiler().compile("Do the task.", "aios", 2_000)
    packet = "\n\n".join(section["content"] for section in sections)

    assert packet.count("AIOS keeps stable truth before dynamic memory.") == 1
    assert "Dynamic task memory follows the stable prefix." in packet
