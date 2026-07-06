from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.aios_cli import run_cli  # noqa: E402
from services.tmcp_runtime import (  # noqa: E402
    compile_tmcp_packet,
    diff_tmcp_packets,
    ensure_tmcp_schema,
    evaluate_tmcp_packet_adherence,
    expand_tmcp_packet_for_requirement_change,
    explain_tmcp_packet,
    persist_tmcp_packet_adherence,
    persist_tmcp_traversal_receipt,
    record_tmcp_intervention_event,
    record_tmcp_receipt_event,
    shortcut_governance_recommendation,
    tmcp_learning_summary,
    update_tmcp_receipt_feedback,
)


def _seed_tmcp_library(root: Path) -> Path:
    tmcp = root / "skills.tmcp"
    for directory in ("tasks", "modules", "branches", "shortcuts"):
        (tmcp / directory).mkdir(parents=True, exist_ok=True)
    (tmcp / "router.md").write_text("# Router\n\nLOAD task nodes.\n", encoding="utf-8")
    (tmcp / "tasks" / "implementation.md").write_text(
        "# Implementation\n\n## Transition Edges\n\n## Custom Skill Construction\n",
        encoding="utf-8",
    )
    for module in (
        "context_gathering",
        "evidence_first",
        "provenance_policy",
        "output_contract",
        "test_gate",
        "operating_language",
    ):
        (tmcp / "modules" / f"{module}.md").write_text(
            f"# Module {module}\n\nUse {module}.\n",
            encoding="utf-8",
        )
    (tmcp / "branches" / "direct_implementation.branch.md").write_text(
        "# Direct Implementation\n\nProceed when intent is explicit.\n",
        encoding="utf-8",
    )
    (tmcp / "shortcuts" / "candidate.md").write_text(
        "# Shortcut Candidate\n\n## Promotion Threshold\n",
        encoding="utf-8",
    )
    return root


def _seed_graph(root: Path) -> None:
    source_skill_dir = root / "skills" / "implementation-review"
    source_skill_dir.mkdir(parents=True, exist_ok=True)
    (source_skill_dir / "SKILL.md").write_text(
        "# Implementation Review\n\nWhen to use: implement features with validation evidence.\n",
        encoding="utf-8",
    )
    graph = {
        "schema": "tmcp-graph-v0.1",
        "tasks": {
            "implementation": {
                "id": "implementation",
                "path": "skills.tmcp/tasks/implementation.md",
                "triggers": ["implement", "build", "patch"],
                "required_modules": ["test_gate", "evidence_first"],
            },
            "agent_workflow": {
                "id": "agent_workflow",
                "path": "skills.tmcp/tasks/agent_workflow.md",
                "triggers": ["agent", "workflow", "tmcp"],
                "required_modules": ["context_gathering"],
            },
        },
        "modules": {
            "test_gate": {
                "id": "test_gate",
                "path": "skills.tmcp/modules/test_gate.md",
                "triggers": ["test", "validation", "verify"],
                "behavior_atoms": ["verification_gate", "claim_evidence"],
                "risk_if_omitted": "high",
                "token_cost": 180,
            },
            "evidence_first": {
                "id": "evidence_first",
                "path": "skills.tmcp/modules/evidence_first.md",
                "triggers": ["evidence", "inspect"],
                "behavior_atoms": ["read_before_edit"],
                "risk_if_omitted": "low",
                "token_cost": 160,
            },
        },
        "branches": {
            "direct_implementation": {
                "id": "direct_implementation",
                "path": "skills.tmcp/branches/direct_implementation.branch.md",
                "triggers": ["implement", "build", "patch"],
            }
        },
        "source_skills": {
            "implementation-review": {
                "id": "implementation-review",
                "node": "@source_skill:implementation-review",
                "path": "skills/implementation-review/SKILL.md",
                "concept_key": "active.implementation.review",
                "triggers": ["implement", "validation evidence"],
                "source_tiers": ["project_authoritative"],
                "behavior_atoms": ["read_before_edit", "source_specific_behavior"],
                "risk_if_omitted": "medium",
                "token_cost": 240,
            }
        },
    }
    (root / "skills.tmcp" / "graph.json").write_text(
        json.dumps(graph, indent=2),
        encoding="utf-8",
    )


def _seed_golden_graph(root: Path) -> None:
    tmcp = root / "skills.tmcp"
    for task in ("debugging", "planning", "research", "visual_polish"):
        (tmcp / "tasks" / f"{task}.md").write_text(f"# {task}\n", encoding="utf-8")
    for module in ("planning_contract", "research_grounding", "visual_polish_system"):
        (tmcp / "modules" / f"{module}.md").write_text(f"# {module}\n", encoding="utf-8")
    graph = {
        "schema": "tmcp-graph-v0.1",
        "tasks": {
            "implementation": {
                "id": "implementation",
                "path": "skills.tmcp/tasks/implementation.md",
                "triggers": ["implement", "feature"],
                "required_modules": ["test_gate"],
                "behavior_atoms": ["change_execution", "verification_gate"],
            },
            "debugging": {
                "id": "debugging",
                "path": "skills.tmcp/tasks/debugging.md",
                "triggers": ["debug", "failure", "root cause"],
                "required_modules": ["test_gate"],
                "behavior_atoms": ["reproduce_first", "root_cause_analysis"],
            },
            "planning": {
                "id": "planning",
                "path": "skills.tmcp/tasks/planning.md",
                "triggers": ["plan", "acceptance criteria"],
                "required_modules": ["planning_contract"],
                "behavior_atoms": ["execution_ready_plan", "acceptance_criteria"],
            },
            "research": {
                "id": "research",
                "path": "skills.tmcp/tasks/research.md",
                "triggers": ["research", "cite", "sources"],
                "required_modules": ["research_grounding"],
                "behavior_atoms": ["source_grounding", "citation_discipline"],
            },
            "agent_workflow": {
                "id": "agent_workflow",
                "path": "skills.tmcp/tasks/agent_workflow.md",
                "triggers": ["skill", "graph", "workflow"],
                "required_modules": ["operating_language"],
                "behavior_atoms": ["skill_routing", "workflow_selection"],
            },
            "visual_polish": {
                "id": "visual_polish",
                "path": "skills.tmcp/tasks/visual_polish.md",
                "triggers": ["visual", "polished", "browser"],
                "required_modules": ["visual_polish_system"],
                "behavior_atoms": ["ui_quality", "visual_verification"],
            },
        },
        "modules": {
            "test_gate": {
                "id": "test_gate",
                "path": "skills.tmcp/modules/test_gate.md",
                "triggers": ["test", "verify", "validation"],
                "behavior_atoms": ["verification_gate", "claim_evidence"],
                "risk_if_omitted": "high",
                "token_cost": 180,
            },
            "operating_language": {
                "id": "operating_language",
                "path": "skills.tmcp/modules/operating_language.md",
                "triggers": ["operating language", "canonical vocabulary"],
                "behavior_atoms": ["canonical_vocabulary", "term_consistency"],
                "risk_if_omitted": "medium",
                "token_cost": 180,
            },
            "planning_contract": {
                "id": "planning_contract",
                "path": "skills.tmcp/modules/planning_contract.md",
                "triggers": ["acceptance criteria", "execution-ready"],
                "behavior_atoms": ["execution_ready_plan", "acceptance_criteria"],
                "risk_if_omitted": "medium",
                "token_cost": 180,
            },
            "research_grounding": {
                "id": "research_grounding",
                "path": "skills.tmcp/modules/research_grounding.md",
                "triggers": ["sources", "cite", "research"],
                "behavior_atoms": ["source_grounding", "citation_discipline"],
                "risk_if_omitted": "high",
                "token_cost": 180,
            },
            "visual_polish_system": {
                "id": "visual_polish_system",
                "path": "skills.tmcp/modules/visual_polish_system.md",
                "triggers": ["visual", "browser", "polished"],
                "behavior_atoms": ["ui_quality", "visual_verification"],
                "risk_if_omitted": "medium",
                "token_cost": 180,
            },
        },
        "source_skills": {},
    }
    (tmcp / "graph.json").write_text(json.dumps(graph, indent=2), encoding="utf-8")


def test_compile_tmcp_packet_selects_task_and_stable_fingerprint(tmp_path: Path) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")

    packet = compile_tmcp_packet(
        objective="Implement the feature and run tests",
        project_path="/tmp/project",
        context_receipt_id="packet-1",
        skills_library_path=library,
    )
    again = compile_tmcp_packet(
        objective="Implement another feature and run tests",
        project_path="/tmp/project",
        context_receipt_id="packet-2",
        skills_library_path=library,
    )

    assert packet["status"] == "compiled"
    assert packet["task_id"] == "implementation"
    assert "@task:implementation" in packet["selected_nodes"]
    assert "@module:test_gate" in packet["selected_nodes"]
    assert packet["selected_branches"][0]["branch"] == "@branch:direct_implementation"
    assert "AIOS TMCP Custom Skill Packet" in packet["packet_markdown"]
    assert packet["source_graph_version"] != "missing"
    assert packet["shortcut_candidate"]["fallback"] == "router_traversal"
    assert packet["shortcut_candidate"]["status"] == "needs_revalidation"
    assert packet["shortcut_candidate"]["usable_as_default"] is False
    assert "stale_candidate" in packet["shortcut_governance"]["allowed_statuses"]
    assert "split_more_specific" in packet["shortcut_governance"]["rebuild_outcomes"]
    assert "Shortcut Freshness" in packet["packet_markdown"]
    assert packet["traversal_fingerprint"] == again["traversal_fingerprint"]
    assert packet["token_estimates"]["custom_skill_tokens"] > 0


def test_compile_tmcp_packet_uses_graph_metadata_and_source_skill(tmp_path: Path) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")
    _seed_graph(library)

    packet = compile_tmcp_packet(
        objective="Implement the feature with validation evidence",
        project_path="/tmp/project",
        skills_library_path=library,
    )

    assert packet["graph_metadata"]["matched"] is True
    assert packet["task_id"] == "implementation"
    assert "@source_skill:implementation-review" in packet["selected_nodes"]
    assert packet["source_skill_nodes"][0]["id"] == "implementation-review"
    assert packet["candidate_scores"]["source_skills"]["implementation-review"] > 3
    assert "Source skill implementation-review" in packet["packet_markdown"]
    assert "read_before_edit" in packet["behavior_atoms"]
    assert packet["packet_optimization"]["strategy"] == "behavior_atom_diff_then_token_cap"
    assert packet["node_usefulness"]["@source_skill:implementation-review"]["prior"] in {
        "high",
        "medium",
    }


def test_persist_tmcp_traversal_receipt_records_packet(tmp_path: Path) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")
    packet = compile_tmcp_packet(
        objective="Implement the feature",
        project_path="/tmp/project",
        skills_library_path=library,
    )
    conn = sqlite3.connect(":memory:")

    ensure_tmcp_schema(conn)
    receipt_id = persist_tmcp_traversal_receipt(
        conn,
        packet=packet,
        run_id="run-1",
        invocation_id="invoke-1",
        session_id="session-1",
    )

    row = conn.execute(
        """
        SELECT task_id, traversal_fingerprint, packet_json, execution_outcome,
               node_usefulness_json, omitted_requirements_json
        FROM tmcp_traversal_receipts
        WHERE id = ?
        """,
        (receipt_id,),
    ).fetchone()
    assert row is not None
    assert row[0] == "implementation"
    assert row[1] == packet["traversal_fingerprint"]
    assert json.loads(row[2])["entry_node"] == "@task:implementation"
    assert row[3] == "pending"
    assert json.loads(row[4])
    assert isinstance(json.loads(row[5]), list)


def test_compile_tmcp_packet_prunes_redundant_low_risk_module_for_source_skill(
    tmp_path: Path,
) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")
    _seed_graph(library)

    packet = compile_tmcp_packet(
        objective="Implement the feature with validation evidence",
        project_path="/tmp/project",
        skills_library_path=library,
    )

    assert "@source_skill:implementation-review" in packet["selected_nodes"]
    assert "@module:evidence_first" not in packet["selected_nodes"]
    assert any(
        row["node"] == "@module:evidence_first" and "behavior diff" in row["reason"]
        for row in packet["skipped_nodes"]
    )


def test_compile_tmcp_packet_promotes_repeated_successful_fingerprint(tmp_path: Path) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")
    conn = sqlite3.connect(":memory:")
    ensure_tmcp_schema(conn)
    seed_packet = compile_tmcp_packet(
        objective="Implement the feature and run tests",
        project_path="/tmp/project",
        skills_library_path=library,
    )
    seed_packet["token_estimates"] = {
        **seed_packet["token_estimates"],
        "estimated_token_delta": 120,
    }
    for index in range(3):
        persist_tmcp_traversal_receipt(
            conn,
            packet=seed_packet,
            run_id=f"run-{index}",
            invocation_id=f"invoke-{index}",
            session_id=f"session-{index}",
            execution_outcome="completed",
            validation_evidence=["scope_check passed"],
        )

    packet = compile_tmcp_packet(
        objective="Implement another feature and run tests",
        project_path="/tmp/project",
        skills_library_path=library,
        receipt_conn=conn,
    )

    assert packet["shortcut_candidate"]["matched"] is True
    assert packet["shortcut_candidate"]["status"] == "active"
    assert packet["shortcut_candidate"]["usable_as_default"] is True
    assert packet["shortcut_candidate"]["promotion_stats"]["successful_count"] == 3
    assert packet["entry_node"].startswith("@shortcut:implementation:")
    assert packet["selected_nodes"][0] == packet["entry_node"]
    shortcut_digest = str(packet["entry_node"]).rsplit(":", 1)[1]
    assert (library / "skills.tmcp" / "shortcuts" / f"implementation-{shortcut_digest}.md").exists()


def test_compile_tmcp_packet_bypasses_shortcut_when_source_skill_hash_changes(
    tmp_path: Path,
) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")
    _seed_graph(library)
    conn = sqlite3.connect(":memory:")
    ensure_tmcp_schema(conn)
    seed_packet = compile_tmcp_packet(
        objective="Implement the feature with validation evidence",
        project_path="/tmp/project",
        skills_library_path=library,
    )
    seed_packet["token_estimates"] = {
        **seed_packet["token_estimates"],
        "estimated_token_delta": 120,
    }
    for index in range(3):
        persist_tmcp_traversal_receipt(
            conn,
            packet=seed_packet,
            run_id=f"run-{index}",
            invocation_id=f"invoke-{index}",
            session_id=f"session-{index}",
            execution_outcome="completed",
            validation_evidence=["scope_check passed"],
        )
    (library / "skills" / "implementation-review" / "SKILL.md").write_text(
        "# Implementation Review\n\nWhen to use: implement features with changed validation rules.\n",
        encoding="utf-8",
    )

    packet = compile_tmcp_packet(
        objective="Implement the feature with validation evidence",
        project_path="/tmp/project",
        skills_library_path=library,
        receipt_conn=conn,
    )

    assert packet["shortcut_candidate"]["matched"] is False
    assert packet["entry_node"] == "@task:implementation"
    assert packet["shortcut_candidate"]["freshness"] == "uncertain"


def test_compile_tmcp_packet_can_cross_into_registered_portable_namespace(tmp_path: Path) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")

    packet = compile_tmcp_packet(
        objective="Make this generated SaaS dashboard feel polished instead of generic shadcn",
        project_path="/tmp/project",
        skills_library_path=library,
    )

    assert packet["task_id"] == "visual_polish"
    assert "@namespace:portable_dev_process/@task:visual_polish" in packet["selected_nodes"]
    assert (
        "@namespace:portable_dev_process/@module:visual_polish_system" in packet["selected_nodes"]
    )
    assert (
        "@namespace:portable_dev_process/@module:enterprise_saas_visual_polish"
        in packet["selected_nodes"]
    )
    assert packet["registry_overlay"]["matched"] is True
    assert packet["registry_overlay"]["namespaces"][0]["namespace"] == "portable_dev_process"
    assert "Namespace portable_dev_process task visual_polish" in packet["packet_markdown"]


def test_compile_tmcp_packet_routes_workflow_strategy_comparison_to_planning(
    tmp_path: Path,
) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")

    packet = compile_tmcp_packet(
        objective="Compare workflow promotion strategies",
        project_path="/tmp/project",
        skills_library_path=library,
    )

    assert packet["task_id"] == "planning"
    assert packet["entry_node"] == "@task:planning"
    assert "@task:agent_workflow" not in packet["selected_nodes"]
    assert packet["selected_branches"][0]["branch"] == "@branch:approval_before_edit"
    assert "@module:test_gate" in packet["selected_nodes"]
    assert "@namespace:portable_dev_process/@task:planning_review" in packet["selected_nodes"]
    assert "@namespace:portable_dev_process/@module:test_authoring" in packet["selected_nodes"]
    assert packet["registry_overlay"]["matched"] is True


def test_compile_tmcp_packet_keeps_tmcp_internal_review_on_canonical_graph(
    tmp_path: Path,
) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")

    packet = compile_tmcp_packet(
        objective="Review TMCP routing risks and explain why this manifest is default",
        project_path="/tmp/project",
        skills_library_path=library,
    )

    assert packet["task_id"] == "agent_workflow"
    assert packet["registry_overlay"]["matched"] is False
    assert not any(
        node.startswith("@namespace:portable_dev_process/") for node in packet["selected_nodes"]
    )
    assert packet["registry_overlay"]["skipped_namespaces"] == [
        {
            "namespace": "portable_dev_process",
            "reason": (
                "TMCP-internal routing work uses the canonical graph unless "
                "instruction hygiene is explicitly requested."
            ),
        }
    ]


def test_compile_tmcp_packet_allows_tmcp_instruction_hygiene_overlay(
    tmp_path: Path,
) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")

    packet = compile_tmcp_packet(
        objective=(
            "Review TMCP agent instructions, reduce prompt size, and check "
            "whether prose affects behavior"
        ),
        project_path="/tmp/project",
        skills_library_path=library,
    )

    assert packet["registry_overlay"]["matched"] is True
    assert "@namespace:portable_dev_process/@task:instruction_hygiene" in packet["selected_nodes"]


def test_compile_tmcp_packet_skips_overlay_when_no_behavior_is_added(
    tmp_path: Path,
) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")
    tmcp = library / "skills.tmcp"
    (tmcp / "tasks" / "planning.md").write_text("# Planning\n", encoding="utf-8")
    for module in ("command_discovery", "test_authoring", "quality_gate"):
        (tmcp / "modules" / f"{module}.md").write_text(f"# {module}\n", encoding="utf-8")
    graph = {
        "schema": "tmcp-graph-v0.1",
        "tasks": {
            "planning": {
                "id": "planning",
                "path": "skills.tmcp/tasks/planning.md",
                "triggers": ["compare", "strategy", "promotion"],
                "required_modules": ["command_discovery", "test_authoring", "quality_gate"],
            }
        },
        "modules": {
            module: {
                "id": module,
                "path": f"skills.tmcp/modules/{module}.md",
                "triggers": [module.replace("_", " ")],
            }
            for module in ("command_discovery", "test_authoring", "quality_gate")
        },
        "source_skills": {},
    }
    (tmcp / "graph.json").write_text(json.dumps(graph), encoding="utf-8")

    packet = compile_tmcp_packet(
        objective="Compare workflow promotion strategies",
        project_path="/tmp/project",
        skills_library_path=library,
    )

    assert packet["task_id"] == "planning"
    assert packet["registry_overlay"]["matched"] is False
    assert not any(
        node.startswith("@namespace:portable_dev_process/") for node in packet["selected_nodes"]
    )


def test_compile_tmcp_packet_routes_operating_language_to_canonical_module(
    tmp_path: Path,
) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")

    packet = compile_tmcp_packet(
        objective="Update the canonical vocabulary and operating language for this skill graph",
        project_path="/tmp/project",
        skills_library_path=library,
    )

    assert packet["task_id"] == "agent_workflow"
    assert "@module:operating_language" in packet["selected_nodes"]
    assert "Module operating_language" in packet["packet_markdown"]


def test_compile_tmcp_packet_selects_tenure_branch_only_when_intent_matches(
    tmp_path: Path,
) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")

    packet = compile_tmcp_packet(
        objective="Apply the Tenure visual polish system to this SOP search screen",
        project_path="/tmp/project",
        skills_library_path=library,
    )

    assert (
        "@namespace:portable_dev_process/@branch:tenure_visual_identity" in packet["selected_nodes"]
    )
    namespace = packet["registry_overlay"]["namespaces"][0]
    assert namespace["selected_branch"] == "tenure_visual_identity"


def test_golden_prompts_cover_required_behavior_atoms(tmp_path: Path) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")
    _seed_golden_graph(library)
    fixtures = json.loads((ROOT / "config" / "tmcp" / "golden-prompts.json").read_text())

    for case in fixtures["cases"]:
        packet = compile_tmcp_packet(
            objective=case["prompt"],
            project_path="/tmp/project",
            skills_library_path=library,
        )

        assert packet["task_id"] == case["expected_task"], case["id"]
        atoms = set(packet["behavior_atoms"])
        assert set(case["required_behavior_atoms"]) <= atoms, case["id"]
        assert not (set(case["forbidden_behavior_atoms"]) & atoms), case["id"]
        for node in case["expected_nodes"]:
            assert node in packet["selected_nodes"], case["id"]


def test_source_skill_excerpt_prefers_semantic_sections_over_examples(tmp_path: Path) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")
    _seed_graph(library)
    skill_path = library / "skills" / "implementation-review" / "SKILL.md"
    skill_path.write_text(
        "\n".join(
            [
                "# Implementation Review",
                "",
                "## Examples",
                "This long example should not be the selected excerpt.",
                "",
                "## Procedure",
                "Read the relevant code, make the change, and keep the patch bounded.",
                "",
                "## Validation",
                "Run the exact relevant tests and report failures.",
            ]
        ),
        encoding="utf-8",
    )

    packet = compile_tmcp_packet(
        objective="Implement the feature with validation evidence",
        project_path="/tmp/project",
        skills_library_path=library,
    )

    assert "## Procedure" in packet["packet_markdown"]
    assert "## Validation" in packet["packet_markdown"]
    assert "This long example should not be the selected excerpt" not in packet["packet_markdown"]


def test_receipt_feedback_updates_omissions_and_learning_summary(tmp_path: Path) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")
    _seed_graph(library)
    packet = compile_tmcp_packet(
        objective="Implement the feature with validation evidence",
        project_path="/tmp/project",
        skills_library_path=library,
    )
    packet["token_estimates"] = {**packet["token_estimates"], "estimated_token_delta": 100}
    conn = sqlite3.connect(":memory:")
    ensure_tmcp_schema(conn)
    receipt_id = persist_tmcp_traversal_receipt(
        conn,
        packet=packet,
        run_id="run-1",
        invocation_id="invoke-1",
        session_id="session-1",
        execution_outcome="completed",
        validation_evidence=["tests passed"],
    )

    feedback = update_tmcp_receipt_feedback(
        conn,
        receipt_id=receipt_id,
        node_usefulness={
            "@module:test_gate": {
                "observed": "useful",
                "behavior_atoms": ["verification_gate"],
            }
        },
        omitted_requirements=[
            {
                "requirement": "ui_quality",
                "reason": "A screenshot request was missed.",
            }
        ],
        validation_evidence=[{"kind": "missed_requirement", "requirement": "ui_quality"}],
    )
    summary = tmcp_learning_summary(conn, task_id="implementation")

    assert feedback["omitted_requirements"][0]["requirement"] == "ui_quality"
    assert feedback["repair_recommendations"][0]["requirement"] == "ui_quality"
    assert summary["node_roi"]["@module:test_gate"]["average_token_delta"] == 100
    assert summary["behavior_atom_roi"]["verification_gate"]["positive_token_roi_count"] == 1
    assert summary["missed_requirements"]["ui_quality"] == 1


def test_explain_tmcp_packet_reports_scores_atoms_and_token_roi(tmp_path: Path) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")
    _seed_graph(library)

    packet = compile_tmcp_packet(
        objective="Implement the feature with validation evidence",
        project_path="/tmp/project",
        skills_library_path=library,
    )
    explanation = explain_tmcp_packet(packet)

    assert explanation["task_id"] == "implementation"
    assert "@source_skill:implementation-review" in explanation["selected_nodes"]
    assert "read_before_edit" in explanation["behavior_atoms"]
    assert (
        explanation["estimated_token_roi"]["baseline_skill_tokens"]
        >= explanation["estimated_token_roi"]["custom_skill_tokens"]
    )
    assert explanation["candidate_scores"]["source_skills"]["implementation-review"] > 3


def test_tmcp_explain_cli_emits_debuggable_packet_explanation(
    tmp_path: Path,
    capsys: Any,
) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")
    _seed_graph(library)
    db_path = tmp_path / "aios.db"

    exit_code = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "tmcp",
            "explain",
            "Implement the feature with validation evidence",
            "--skills-library",
            str(library),
        ]
    )
    output = capsys.readouterr().out
    payload = json.loads(output)

    assert exit_code == 0
    assert payload["command"] == "tmcp-explain"
    assert payload["data"]["task_id"] == "implementation"
    assert "@source_skill:implementation-review" in payload["data"]["selected_nodes"]


def test_packet_adherence_distinguishes_ignored_required_behavior(tmp_path: Path) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")
    _seed_golden_graph(library)
    packet = compile_tmcp_packet(
        objective="Implement the feature and run tests",
        project_path="/tmp/project",
        skills_library_path=library,
        phase="implementation",
    )

    adherence = evaluate_tmcp_packet_adherence(
        packet=packet,
        final_summary="Changed the implementation file.",
        validation_commands=[],
        evidence=[],
    )

    assert adherence["status"] == "fail"
    ignored = {row["requirement"] for row in adherence["ignored_requirements"]}
    assert "verification_gate" in ignored
    assert all(
        row["failure_mode"] == "agent_compliance_failure"
        for row in adherence["ignored_requirements"]
    )


def test_packet_adherence_persists_granular_events(tmp_path: Path) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")
    _seed_golden_graph(library)
    packet = compile_tmcp_packet(
        objective="Implement the feature and run tests",
        project_path="/tmp/project",
        skills_library_path=library,
        phase="implementation",
    )
    conn = sqlite3.connect(":memory:")
    ensure_tmcp_schema(conn)
    receipt_id = persist_tmcp_traversal_receipt(
        conn,
        packet=packet,
        run_id="run-1",
        invocation_id="invoke-1",
        session_id="session-1",
    )
    adherence = evaluate_tmcp_packet_adherence(
        packet=packet,
        final_summary="Changed implementation. Tests were not run.",
        validation_commands=[],
    )

    persist_tmcp_packet_adherence(
        conn,
        receipt_id=receipt_id,
        adherence=adherence,
        run_id="run-1",
        invocation_id="invoke-1",
    )

    event_types = [
        row[0]
        for row in conn.execute(
            "SELECT event_type FROM tmcp_receipt_events WHERE receipt_id = ?",
            (receipt_id,),
        ).fetchall()
    ]
    row = conn.execute(
        "SELECT adherence_json, omitted_requirements_json FROM tmcp_traversal_receipts WHERE id = ?",
        (receipt_id,),
    ).fetchone()
    assert "packet_compiled" in event_types
    assert "node_selected" in event_types
    assert "required_behavior_ignored" in event_types
    assert json.loads(row[0])["schema"] == "tmcp-packet-adherence-v0.1"
    assert any(item["requirement"] == "verification_gate" for item in json.loads(row[1]))


def test_intervention_audit_trail_records_blockers_and_iterations(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    ensure_tmcp_schema(conn)

    receipt_event_id = record_tmcp_receipt_event(
        conn,
        receipt_id=None,
        run_id="run-1",
        invocation_id="invoke-1",
        event_type="validation_command_run",
        summary="Ran focused pytest command.",
        behavior_atom="verification_gate",
    )
    intervention_id = record_tmcp_intervention_event(
        conn,
        receipt_id=None,
        run_id="run-1",
        invocation_id="invoke-1",
        intervention_type="test_rerun",
        summary="TMCP test gate forced a rerun after failure.",
        behavior_atom="verification_gate",
        outcome="iteration_required",
    )

    assert receipt_event_id.startswith("tmcp-event-")
    assert intervention_id.startswith("tmcp-intervention-")
    intervention = conn.execute(
        "SELECT intervention_type, outcome FROM tmcp_intervention_events WHERE id = ?",
        (intervention_id,),
    ).fetchone()
    assert intervention == ("test_rerun", "iteration_required")


def test_negative_golden_prompts_protect_precision(tmp_path: Path) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")
    _seed_golden_graph(library)
    fixtures = json.loads((ROOT / "config" / "tmcp" / "golden-prompts.json").read_text())

    for case in fixtures["negative_cases"]:
        packet = compile_tmcp_packet(
            objective=case["prompt"],
            project_path="/tmp/project",
            skills_library_path=library,
        )
        atoms = set(packet["behavior_atoms"])
        assert not (set(case["forbidden_behavior_atoms"]) & atoms), case["id"]
        for forbidden_prefix in case["forbidden_node_prefixes"]:
            assert not any(
                str(node).startswith(forbidden_prefix) for node in packet["selected_nodes"]
            ), case["id"]


def test_phase_aware_packets_change_required_behavior(tmp_path: Path) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")
    _seed_golden_graph(library)

    planning = compile_tmcp_packet(
        objective="Implement the feature",
        project_path="/tmp/project",
        skills_library_path=library,
        phase="planning",
    )
    closeout = compile_tmcp_packet(
        objective="Implement the feature",
        project_path="/tmp/project",
        skills_library_path=library,
        phase="closeout",
    )
    diff = diff_tmcp_packets(planning, closeout)

    assert planning["phase"] == "planning"
    assert "acceptance_criteria" in planning["behavior_atoms"]
    assert closeout["phase"] == "closeout"
    assert "validation_reporting" in closeout["behavior_atoms"]
    assert diff["phase_changed"] is True
    assert "validation_reporting" in diff["behavior_atoms_gained"]


def test_domain_disambiguation_adds_ui_polish_behavior_without_generic_source_pack(
    tmp_path: Path,
) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")
    _seed_golden_graph(library)

    packet = compile_tmcp_packet(
        objective="Improve this dashboard button spacing",
        project_path="/tmp/project",
        skills_library_path=library,
        domain="ui_polish",
    )

    assert packet["domain"] == "ui_polish"
    assert "ui_quality" in packet["behavior_atoms"]
    assert "visual_verification" in packet["behavior_atoms"]
    assert not any(str(node).startswith("@source_skill:") for node in packet["selected_nodes"])


def test_packet_diff_reports_nodes_atoms_and_token_delta(tmp_path: Path) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")
    _seed_golden_graph(library)
    before = compile_tmcp_packet(
        objective="Plan the work",
        project_path="/tmp/project",
        skills_library_path=library,
        phase="planning",
    )
    after = compile_tmcp_packet(
        objective="Implement the work and run tests",
        project_path="/tmp/project",
        skills_library_path=library,
        phase="implementation",
    )

    diff = diff_tmcp_packets(before, after)

    assert diff["schema"] == "tmcp-packet-diff-v0.1"
    assert diff["phase_changed"] is True
    assert diff["nodes_added"] or diff["nodes_removed"]
    assert "phase changed" in diff["routing_change_reason"]


def test_runtime_requirement_expansion_persists_new_receipt_diff_and_intervention(
    tmp_path: Path,
) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")
    _seed_golden_graph(library)
    conn = sqlite3.connect(":memory:")
    ensure_tmcp_schema(conn)
    current = compile_tmcp_packet(
        objective="Plan the work",
        project_path="/tmp/project",
        skills_library_path=library,
        phase="planning",
    )
    current_receipt_id = persist_tmcp_traversal_receipt(
        conn,
        packet=current,
        run_id="run-1",
        invocation_id="invoke-1",
        session_id="session-1",
        execution_outcome="superseded_by_runtime_expansion",
    )
    current["receipt_id"] = current_receipt_id

    expansion = expand_tmcp_packet_for_requirement_change(
        conn,
        current_packet=current,
        objective="Implement the work and run tests",
        project_path="/tmp/project",
        run_id="run-1",
        invocation_id="invoke-1",
        session_id="session-1",
        phase="implementation",
        reason="workflow stage moved from planning to implementation",
    )

    assert expansion["schema"] == "tmcp-runtime-expansion-v0.1"
    assert expansion["previous_receipt_id"] == current_receipt_id
    assert expansion["active_packet"]["phase"] == "implementation"
    assert expansion["active_packet"]["receipt_id"] == expansion["receipt_id"]
    assert expansion["packet_diff"]["phase_changed"] is True
    assert "verification_gate" in expansion["active_packet"]["behavior_atoms"]

    receipt_row = conn.execute(
        """
        SELECT task_id, phase, packet_json, execution_outcome
        FROM tmcp_traversal_receipts
        WHERE id = ?
        """,
        (expansion["receipt_id"],),
    ).fetchone()
    assert receipt_row is not None
    assert receipt_row[1] == "implementation"
    assert json.loads(receipt_row[2])["receipt_id"] == expansion["receipt_id"]
    assert receipt_row[3] == "active_runtime_expansion"

    intervention = conn.execute(
        """
        SELECT intervention_type, outcome, metadata_json
        FROM tmcp_intervention_events
        WHERE id = ?
        """,
        (expansion["intervention_id"],),
    ).fetchone()
    assert intervention is not None
    assert intervention[0] == "runtime_packet_expansion"
    assert intervention[1] == "expanded_packet_required"
    metadata = json.loads(intervention[2])
    assert metadata["previous_receipt_id"] == current_receipt_id
    assert metadata["packet_diff"]["phase_changed"] is True


def test_shortcut_governance_demotes_quality_harming_shortcut() -> None:
    recommendation = shortcut_governance_recommendation(
        {
            "node": "@shortcut:implementation:abc",
            "status": "active",
            "promotion_stats": {
                "validation_success_rate": 0.9,
                "positive_token_roi_count": 3,
                "missed_requirement_count": 1,
            },
        }
    )

    assert recommendation["recommended_status"] == "demoted"
    assert "missed requirements" in recommendation["recommended_action"]
