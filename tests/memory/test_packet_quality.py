from __future__ import annotations

import importlib.util
import sys
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from services.context_compiler import ContextCompiler  # noqa: E402
from services.memory_compiler import MemoryCompiler  # noqa: E402

VALIDATOR_PATH = ROOT / "scripts" / "validate-memory-packets.py"
validator_spec = importlib.util.spec_from_file_location("validate_memory_packets", VALIDATOR_PATH)
assert validator_spec is not None
validator = importlib.util.module_from_spec(validator_spec)
assert validator_spec.loader is not None
validator_spec.loader.exec_module(validator)


def _sources() -> list[dict[str, object]]:
    return [
        {"id": "raw-project", "source_type": "project_context", "source_path": "PROJECT.md"},
        {"id": "raw-rules", "source_type": "agent_rules", "source_path": "config/agent-rules.md"},
    ]


def _facts() -> list[dict[str, object]]:
    return [
        {
            "id": "fact-current",
            "fact_text": "AIOS memory packets preserve provenance.",
            "validity_status": "active",
            "project_scope": "aios",
            "source_id": "raw-project",
        },
        {
            "id": "fact-superseded",
            "fact_text": "AIOS memory packets can omit provenance.",
            "validity_status": "superseded",
            "project_scope": "aios",
            "source_id": "raw-project",
        },
        {
            "id": "fact-contradicted",
            "fact_text": "Graph rows should be dumped directly into prompts.",
            "validity_status": "contradicted",
            "project_scope": "aios",
            "source_id": "raw-rules",
        },
        {
            "id": "fact-constraint",
            "fact_text": "Project-specific tasks must include project constraints.",
            "predicate": "has_constraint",
            "validity_status": "active",
            "project_scope": "aios",
            "source_id": "raw-rules",
        },
        {
            "id": "fact-unrelated",
            "fact_text": "Unrelated memories should not be loaded just in case.",
            "validity_status": "active",
            "project_scope": "other-project",
            "source_id": "raw-project",
        },
    ]


def _compiler(facts: Sequence[dict[str, object]] | None = None) -> MemoryCompiler:
    return MemoryCompiler(raw_sources=_sources(), facts=facts or _facts(), relationships=[])


def test_provenance_present() -> None:
    packet = _compiler().compile({"fact_ids": ["fact-current"]}, token_budget=2_000)

    assert "## Sources / Provenance" in packet
    assert "- project_context: PROJECT.md" in packet
    assert validator.validate_packet(packet) == []


def test_superseded_not_in_current_truth() -> None:
    packet = _compiler().compile(
        {"fact_ids": ["fact-current", "fact-superseded"]},
        token_budget=2_000,
    )

    current_truth = packet.split("## Current Truth", maxsplit=1)[1].split("##", maxsplit=1)[0]
    assert "preserve provenance" in current_truth
    assert "omit provenance" not in current_truth


def test_contradictions_surfaced() -> None:
    packet = _compiler().compile({"fact_ids": ["fact-contradicted"]}, token_budget=2_000)

    assert "## Contradictions or Stale Information" in packet
    assert "- contradicted: Graph rows should be dumped directly into prompts." in packet
    assert validator.validate_packet(packet) == []


def test_project_constraints_included() -> None:
    packet = _compiler().compile({"fact_ids": ["fact-constraint"]}, token_budget=2_000)

    assert "## Constraints" in packet
    assert "Project-specific tasks must include project constraints." in packet


def test_stable_separated_from_dynamic() -> None:
    sections = ContextCompiler(
        system_instructions="Stable system.",
        aios_operating_rules=("Stable rule.",),
        user_preferences=("Stable preference.",),
        project_memory_summaries={"aios": "Stable project memory."},
        project_context_facts=[_facts()[0]],
        raw_sources=_sources(),
        retrieved_facts=[_facts()[3]],
    ).compile("Dynamic task.", "aios", 2_000)

    headings = [section["content"].splitlines()[0] for section in sections]
    assert headings.index("## Project Context Packet") < headings.index(
        "## Task-Specific Retrieved Memory"
    )


def test_no_raw_json_in_output() -> None:
    packet = _compiler().compile({"fact_ids": ["fact-current", "fact-contradicted"]})

    assert "{" not in packet
    assert "}" not in packet
    assert validator.check_no_raw_json(packet) == []


def test_token_budget_respected() -> None:
    many_facts: list[dict[str, object]] = [
        {
            "id": f"fact-{index}",
            "fact_text": f"Memory fact {index} contains enough detail to exceed a small budget.",
            "validity_status": "active",
            "source_id": "raw-project",
        }
        for index in range(20)
    ]
    packet = _compiler(many_facts).compile(
        {"fact_ids": [str(row["id"]) for row in many_facts]},
        token_budget=45,
    )

    assert "## Sources / Provenance" in packet
    assert len(packet) // 4 <= 45


def test_stable_prefix_deterministic() -> None:
    compiler = ContextCompiler(
        system_instructions="Stable system.",
        aios_operating_rules=("Stable rule.",),
        user_preferences=("Stable preference.",),
        project_memory_summaries={"aios": "Stable summary."},
        project_context_facts=[_facts()[0]],
    )

    first = compiler.compile("First task.", "aios", 2_000)
    second = compiler.compile("Second task.", "aios", 2_000)
    assert first[:5] == second[:5]


def test_no_bloat_unrelated_memories() -> None:
    packet = _compiler().compile(
        {"fact_ids": ["fact-current"]},
        token_budget=2_000,
    )

    assert "preserve provenance" in packet
    assert "Unrelated memories should not be loaded just in case." not in packet


def test_validator_reports_violations() -> None:
    packet = """# Relevant Memory Briefing
## Current Truth
- {"subject_id": "fact-1"}
## Sources / Provenance
"""

    violations = validator.validate_packet(packet, max_tokens=4)
    assert "Sources / Provenance section must contain at least one source row" in violations
    assert "packet appears to contain raw JSON or graph rows" in violations
    assert any("exceeds max" in violation for violation in violations)
