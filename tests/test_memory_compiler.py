from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.memory_compiler import MemoryCompiler  # noqa: E402


def _sources() -> list[dict[str, object]]:
    return [
        {
            "id": "raw-project",
            "source_type": "project_truth",
            "source_path": "PROJECT.md",
        },
        {
            "id": "raw-decision",
            "source_type": "decision_log",
            "source_path": "docs/decisions/memory.md",
        },
    ]


def _facts() -> list[dict[str, object]]:
    return [
        {
            "id": "fact-active",
            "fact_text": "AIOS uses layered memory packets.",
            "validity_status": "active",
            "source_id": "raw-project",
        },
        {
            "id": "fact-superseded",
            "fact_text": "AIOS uses a flat prompt memory list.",
            "validity_status": "superseded",
            "source_id": "raw-project",
        },
        {
            "id": "fact-constraint",
            "fact_text": "Memory packets must stay readable Markdown.",
            "predicate": "has_constraint",
            "validity_status": "active",
            "source_id": "raw-project",
        },
        {
            "id": "fact-decision",
            "fact_text": "Phase 12 chose graph-native memory layers.",
            "entity": "decision",
            "validity_status": "active",
            "source_id": "raw-decision",
        },
        {
            "id": "fact-question",
            "fact_text": "Which historical memories should be backfilled first?",
            "validity_status": "active",
            "source_id": "raw-decision",
        },
        {
            "id": "fact-uncertain",
            "fact_text": "Some older prompt packets may still miss provenance.",
            "validity_status": "uncertain",
            "source_id": "raw-decision",
        },
    ]


def _relationships() -> list[dict[str, object]]:
    return [
        {
            "id": "rel-1",
            "subject_id": "fact-active",
            "predicate": "depends_on",
            "object_id": "fact-constraint",
            "source_id": "raw-project",
        },
        {
            "id": "rel-2",
            "subject_id": "fact-constraint",
            "predicate": "caused_by",
            "object_id": "fact-decision",
            "source_id": "raw-decision",
        },
        {
            "id": "rel-3",
            "subject_id": "fact-decision",
            "predicate": "blocks",
            "object_id": "fact-question",
            "source_id": "raw-decision",
        },
        {
            "id": "rel-4",
            "subject_id": "fact-question",
            "predicate": "supersedes",
            "object_id": "fact-superseded",
            "source_id": "raw-project",
        },
    ]


def _compiler() -> MemoryCompiler:
    return MemoryCompiler(raw_sources=_sources(), facts=_facts(), relationships=_relationships())


def _all_fact_ids() -> list[str]:
    return [str(row["id"]) for row in _facts()]


def test_current_truth_excludes_superseded() -> None:
    packet = _compiler().compile({"fact_ids": _all_fact_ids()}, token_budget=2_000)

    current_truth = packet.split("## Current Truth", maxsplit=1)[1].split("##", maxsplit=1)[0]
    assert "AIOS uses layered memory packets." in current_truth
    assert "flat prompt memory list" not in current_truth


def test_contradictions_section_labels_validity() -> None:
    packet = _compiler().compile({"fact_ids": _all_fact_ids()}, token_budget=2_000)

    assert "## Contradictions or Stale Information" in packet
    assert "- superseded: AIOS uses a flat prompt memory list." in packet
    assert "- uncertain: Some older prompt packets may still miss provenance." in packet


def test_sources_always_included() -> None:
    packet = _compiler().compile(
        {"fact_ids": ["fact-active"], "source_ids": ["raw-project"]},
        token_budget=1,
    )

    assert "## Sources / Provenance" in packet
    assert "- project_truth: PROJECT.md" in packet


def test_causal_chain_depth_cap() -> None:
    packet = _compiler().compile(
        {"fact_ids": ["fact-active"], "relationship_ids": ["rel-1"]},
        token_budget=2_000,
    )

    assert (
        "AIOS uses layered memory packets. -- depends_on -> Memory packets must stay readable Markdown."
        in packet
    )
    assert (
        "Memory packets must stay readable Markdown. -- caused_by -> Phase 12 chose graph-native memory layers."
        in packet
    )
    assert (
        "Phase 12 chose graph-native memory layers. -- blocks -> Which historical memories should be backfilled first?"
        in packet
    )
    assert "Which historical memories should be backfilled first? -- supersedes" not in packet


def test_token_budget_truncates_lower_priority() -> None:
    packet = _compiler().compile(
        {"fact_ids": _all_fact_ids(), "relationship_ids": ["rel-1"]},
        token_budget=95,
    )

    assert "## Current Truth" in packet
    assert "## Sources / Provenance" in packet
    assert "## Open Questions" not in packet
    assert "## Contradictions or Stale Information" not in packet


def test_current_truth_only_mode_omits_history() -> None:
    packet = _compiler().compile(
        {"fact_ids": _all_fact_ids()},
        mode="current_truth_only",
        token_budget=2_000,
    )

    assert "## Current Truth" in packet
    assert "## Relevant Prior Decisions" not in packet
    assert "## Contradictions or Stale Information" not in packet
    assert "## Open Questions" not in packet


def test_compile_returns_no_raw_json() -> None:
    packet = _compiler().compile(
        {"fact_ids": _all_fact_ids(), "relationship_ids": ["rel-1"]},
        token_budget=2_000,
    )

    assert packet.startswith("# Relevant Memory Briefing")
    assert "{" not in packet
    assert "}" not in packet
    assert '"subject_id"' not in packet
