from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.context_compiler import ContextCompiler  # noqa: E402


def _compiler() -> ContextCompiler:
    return ContextCompiler(
        system_instructions="Follow the AIOS execution contract.",
        aios_operating_rules=("Keep project truth current.", "Preserve local-first behavior."),
        user_preferences=("Use pnpm for JavaScript.", "Commit coherent units."),
        project_memory_summaries={
            "aios": (
                "AIOS is a local-first agent operating system. "
                "It compiles context, workflow rules, evidence, and memory for agents."
            )
        },
            project_context_facts=[
            {
                "id": "truth-1",
                "fact_text": "AIOS uses graph-native memory layers.",
                "validity_status": "active",
                "project_scope": "aios",
            },
            {
                "id": "truth-2",
                "fact_text": "AIOS uses an obsolete flat memory packet.",
                "validity_status": "superseded",
                "project_scope": "aios",
            },
        ],
        raw_sources=[
            {
                "id": "raw-1",
                "source_type": "project_context",
                "source_path": "PROJECT.md",
            }
        ],
        retrieved_facts=[
            {
                "id": "dyn-duplicate",
                "fact_text": "AIOS uses graph-native memory layers.",
                "validity_status": "active",
                "project_scope": "aios",
                "source_id": "raw-1",
            },
            {
                "id": "dyn-unique",
                "fact_text": "MemoryCompiler formats retrieved rows as Markdown.",
                "validity_status": "active",
                "project_scope": "aios",
                "source_id": "raw-1",
            },
            {
                "id": "dyn-superseded",
                "fact_text": "Dynamic memory still uses raw edge rows.",
                "validity_status": "superseded",
                "project_scope": "aios",
                "source_id": "raw-1",
            },
        ],
        retrieved_relationships=[],
        scratchpad_results=("pytest passed",),
    )


def _headings(sections: list[dict[str, str]]) -> list[str]:
    return [section["content"].splitlines()[0] for section in sections]


def test_stable_sections_appear_before_dynamic() -> None:
    sections = _compiler().compile("Continue Phase 12.", "aios", 2_000)

    assert _headings(sections) == [
        "## System / Developer Instructions",
        "## AIOS Operating Rules",
        "## User Preferences",
        "## Project Memory Summary",
        "## Project Context Packet",
        "## Task-Specific Retrieved Memory",
        "## Current User Request / Task Description",
        "## Scratchpad / Tool Results",
    ]


def test_same_project_produces_deterministic_prefix() -> None:
    compiler = _compiler()

    first = compiler.compile("Task one.", "aios", 2_000)
    second = compiler.compile("Task two.", "aios", 2_000)

    assert first[:5] == second[:5]
    assert first[6]["content"] != second[6]["content"]


def test_token_budget_drops_dynamic_first() -> None:
    sections = _compiler().compile("Continue Phase 12.", "aios", 180)

    dynamic_memory = sections[5]["content"]
    project_context = sections[4]["content"]
    project_memory = sections[3]["content"]
    assert "Additional lower-priority context omitted for token budget." in dynamic_memory
    assert "AIOS uses graph-native memory layers." in project_context
    assert "AIOS is a local-first agent operating system." in project_memory


def test_deduplication_drops_dynamic_copy() -> None:
    sections = _compiler().compile("Continue Phase 12.", "aios", 2_000)
    packet = "\n\n".join(section["content"] for section in sections)

    assert packet.count("AIOS uses graph-native memory layers.") == 1
    assert "MemoryCompiler formats retrieved rows as Markdown." in packet


def test_staleness_filter_excludes_superseded() -> None:
    sections = _compiler().compile("Continue Phase 12.", "aios", 2_000)
    packet = "\n\n".join(section["content"] for section in sections)

    assert "obsolete flat memory packet" not in packet
    assert "raw edge rows" not in packet


def test_no_provider_specific_headers_by_default() -> None:
    sections = _compiler().compile("Continue Phase 12.", "aios", 2_000)

    assert all(set(section) == {"role", "content"} for section in sections)
    packet = "\n\n".join(section["content"] for section in sections).lower()
    assert "anthropic-beta" not in packet
    assert "cache-control" not in packet
    assert "prompt-caching" not in packet
