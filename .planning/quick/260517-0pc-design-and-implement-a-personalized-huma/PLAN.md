# Quick Task Plan: Personalized Humanizer Skill

## Task

Design and implement a reusable AIOS personalized humanizer skill that uses bounded personal corpus evidence, versioned voice profiles, feedback-gated profile updates, audit/debug outputs, and lightweight evals.

## Context Loaded

- `pnpm context:compile --task "Design and implement a personalized humanizer voice skill with corpus-backed profiles, feedback, docs, and evals"`
- `config/workflows/skills.json`
- `config/workflows/registry.json`
- `services/workflow_orchestration.py`
- `services/divergent_strategy.py`
- `schema.sql`
- `docs/architecture/prompt-skill-promotion.md`
- `aios/context/features/skill-registry.md`
- `docs/aios/corpus/config.json`
- existing installed `humanizer` skill guidance

## Implementation Steps

1. Add versioned personalized humanizer configuration and voice profile data.
2. Add a repo-native `skills/personalized-humanizer/SKILL.md` packet.
3. Implement deterministic service primitives for classification, bounded retrieval, voice packet generation, conservative transform, quality scoring, feedback, profile update proposals, and evals.
4. Register the skill/workflow in AIOS workflow registries.
5. Add SQLite schema support for durable runs, feedback, proposed profile updates, and eval results.
6. Add focused tests and documentation.
7. Run targeted tests and validation.

## Acceptance Criteria

- Supports outreach, project/build-in-public, academic/reflective, prompt/PRD, and creative/narrative modes.
- Builds compact voice packets from versioned profile rules and bounded references.
- Preserves meaning and avoids adding unsupported personal facts.
- Supports debug/audit output.
- Feedback creates evidence-backed candidate updates rather than mutating canonical profile.
- Evals cover representative tasks and score meaning, voice, context, specificity, over-personalization risk, generic AI feel, and verbosity.
- Documentation explains usage, retrieval, privacy, feedback, evals, and inspection.
