from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.personalized_humanizer import (  # noqa: E402
    CorpusExample,
    build_voice_packet,
    classify_writing_task,
    ensure_personalized_humanizer_schema,
    humanize_text,
    record_feedback,
    record_rewrite_run,
    retrieve_relevant_examples,
    run_eval_suite,
    transition_profile_update,
)
from services.workflow_orchestration import (  # noqa: E402
    WorkflowExecutionContext,
    execute_workflow,
    load_skill_registry,
    load_workflow_registry,
    validate_workflow_bindings,
)


def test_classifies_required_voice_modes() -> None:
    assert classify_writing_task("Write a LinkedIn outreach note to a recruiter") == "professional_outreach"
    assert classify_writing_task("Draft a build in public post about AIOS evals") == "project_build_in_public"
    assert classify_writing_task("Turn this into a Codex implementation prompt") == "prompt_prd"
    assert classify_writing_task("Revise this academic reflection paragraph") == "academic_reflective"
    assert classify_writing_task("Rewrite this book scene with emotional realism") == "creative_narrative"


def test_retrieval_respects_mode_boundaries() -> None:
    profile = {
        "version": "test",
        "modes": {
            "professional_outreach": {
                "allowed_source_modes": ["professional_outreach"],
                "confidence": 0.5,
                "style_rules": [],
                "anti_style_rules": [],
            }
        },
    }
    examples = [
        CorpusExample("outreach-1", "professional_outreach", "Hi, quick note.", "approved_final"),
        CorpusExample("scene-1", "creative_narrative", "He stared at the dark house."),
    ]

    selected = retrieve_relevant_examples(examples, mode="professional_outreach", profile=profile)

    assert [example.source_id for example in selected] == ["outreach-1"]


def test_voice_packet_uses_provenance_without_storing_excerpts() -> None:
    profile = {
        "version": "test",
        "global_voice": {
            "style_rules": [{"rule": "Preserve useful structure."}],
            "anti_style_rules": [{"rule": "Do not invent personal facts."}],
        },
        "modes": {
            "prompt_prd": {
                "tone": "direct",
                "confidence": 0.7,
                "style_rules": ["Use acceptance criteria."],
                "anti_style_rules": ["No silent deletion of constraints."],
            }
        },
    }
    packet = build_voice_packet(
        profile,
        mode="prompt_prd",
        examples=[CorpusExample("prompt-1", "prompt_prd", "Audit first. Then implement.")],
    )

    assert packet.mode == "prompt_prd"
    assert "Preserve useful structure." in packet.rules
    assert packet.evidence_refs[0]["source_id"] == "prompt-1"
    assert packet.evidence_refs[0]["excerpt_stored"] is False
    assert "Audit first" not in str(packet.evidence_refs)


def test_humanize_prompt_preserves_constraints_and_structure() -> None:
    text = "Implement the feature. Check the current code first. Add tests and docs. Do not delete existing behavior."

    result = humanize_text(text, requested_mode="prompt_prd", debug=True)

    assert "- Implement the feature." in result.output
    assert "Do not delete existing behavior." in result.output
    assert result.scorecard["meaning_preservation"] >= 3
    assert result.scorecard["over_personalization_risk"] == 0
    assert result.debug is not None
    assert result.debug["selected_voice_profile"] == "prompt_prd"
    assert result.debug["pipeline_position"] == "standalone"
    assert result.debug["pipeline_contract"] == "generic_cleanup_plus_voice"


def test_after_generic_pipeline_step_applies_voice_without_reowning_generic_cleanup() -> None:
    text = (
        "AIOS marks a pivotal step forward. "
        "It helps agents check their own work before calling something done."
    )

    standalone = humanize_text(text, requested_mode="project_build_in_public")
    after_generic = humanize_text(
        text,
        requested_mode="project_build_in_public",
        pipeline_position="after_generic_humanizer",
        debug=True,
    )

    assert "pivotal" not in standalone.output
    assert "pivotal" in after_generic.output
    assert "The useful part is the gate" in after_generic.output
    assert after_generic.pipeline_position == "after_generic_humanizer"
    assert after_generic.debug is not None
    assert after_generic.debug["pipeline_contract"] == "voice_specific_only"


def test_unknown_pipeline_position_fails_explicitly() -> None:
    with pytest.raises(ValueError, match="Unknown personalized humanizer pipeline position"):
        humanize_text(
            "Make this sound like me.",
            requested_mode="project_build_in_public",
            pipeline_position="generic_replacement",  # type: ignore[arg-type]
        )


def test_feedback_creates_candidate_update_without_mutating_profile() -> None:
    conn = sqlite3.connect(":memory:")
    ensure_personalized_humanizer_schema(conn)
    result = humanize_text(
        "Audit first. Then implement only the smallest scoped fix.",
        requested_mode="prompt_prd",
    )
    run_id = record_rewrite_run(conn, result, input_text="Audit first. Then implement only the smallest scoped fix.")

    feedback = record_feedback(
        conn,
        run_id=run_id,
        verdict="approved",
        notes="User often wants implementation prompts to include audit-first steps.",
    )

    proposal = feedback["proposal"]
    assert proposal is not None
    assert proposal["status"] == "candidate"
    assert proposal["proposed_rule"].startswith("User often wants")

    row = conn.execute(
        "SELECT status, proposed_rule FROM personalized_humanizer_profile_updates WHERE id = ?",
        (proposal["id"],),
    ).fetchone()
    assert row == ("candidate", "User often wants implementation prompts to include audit-first steps.")


def test_profile_update_approval_requires_evidence() -> None:
    conn = sqlite3.connect(":memory:")
    ensure_personalized_humanizer_schema(conn)
    conn.execute(
        """
        INSERT INTO personalized_humanizer_profile_updates (
          id, created_at, updated_at, profile_id, profile_version, mode, status,
          proposed_rule, rationale, evidence_json
        ) VALUES ('one', 'now', 'now', 'profile', 'v1', 'prompt_prd', 'draft', 'rule', 'why', '[]')
        """
    )

    transition = transition_profile_update(conn, "one", requested_status="approved")

    assert transition["status"] == "candidate"
    assert "requires at least two evidence" in transition["decision_note"]


def test_eval_suite_runs_representative_cases() -> None:
    result = run_eval_suite()

    assert result["summary"]["case_count"] == 8
    assert result["summary"]["passed_count"] >= 6
    assert {row["id"] for row in result["results"]} >= {
        "cold-outreach",
        "linkedin-project-post",
        "codex-implementation-prompt",
        "academic-reflection",
        "creative-narrative",
        "technical-project-update",
        "generic-ai-paragraph",
        "do-not-overwrite",
    }


def test_workflow_registry_includes_personalized_humanizer() -> None:
    workflows = load_workflow_registry(ROOT / "config" / "workflows" / "registry.json")
    skills = load_skill_registry(ROOT / "config" / "workflows" / "skills.json")

    assert "personalized-humanizer" in workflows
    assert validate_workflow_bindings(workflows, skills) == []


def test_personalized_humanizer_workflow_executes() -> None:
    report = execute_workflow(
        WorkflowExecutionContext(
            objective="Humanize this Codex prompt: Implement the feature. Audit first. Add tests.",
            workflow_key="personalized-humanizer",
        )
    )

    assert report["status"] == "completed"
    assert report["artifacts"]["humanized_text"]
    validations = {row["validation_key"]: row for row in report["validations"]}
    assert validations["personalized_humanizer_quality_checker"]["passed"] is True
