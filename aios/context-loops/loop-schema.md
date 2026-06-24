# Context Loop Schema

## Inner Loop Run

Required fields:

- `id`
- `workflow`
- `task_type`
- `task_input_hash`
- `triggering_event`
- `prompt_version`
- `guidance_version`
- `retrieved_context_json`
- `context_sources_json`
- `approved_lessons_json`
- `generated_output`
- `uncertainty_flags_json`
- `unsupported_claims_json`
- `assumptions_json`
- `handoff_notes`
- `reversible_artifact_json`

## Review Event

Required fields:

- `id`
- `run_id`
- `review_outcome`
- `original_output_hash`
- `final_output_hash`
- `final_output`
- `diff_text`
- `edit_distance_ratio`
- `reviewer_notes`

Supported outcomes:

- `sent_unchanged`
- `edited_and_sent`
- `edited_not_sent`
- `deleted`
- `rejected`
- `left_pending`
- `replaced_manually`
- `human_judgment_only`

## Learning Candidate

Required fields:

- `id`
- `workflow`
- `review_event_id`
- `observed_pattern`
- `likely_interpretation`
- `confidence`
- `affected_workflow`
- `proposed_change`
- `help_reason`
- `destination`
- `category`
- `evidence_json`
- `status`

Allowed destinations:

- `writing_guidance`
- `retrieval_policy`
- `source_list`
- `safety_check_policy`
- `human_handoff_rule`
- `project_memory`
- `personal_preference_memory`
- `no_durable_memory`

Only `approved` candidates may be applied to `approved-lessons.md`.
