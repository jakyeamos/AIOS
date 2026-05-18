# Quick Task Plan: Personalized Humanizer Optional Voice Step

## Task

Improve the personalized humanizer as an optional voice-specific pipeline step, without treating it as a replacement for the generic humanizer.

## Context Loaded

- `pnpm context:compile --task "Improve personalized humanizer as optional voice-specific pipeline step after generic humanizer cleanup"`
- `skills/personalized-humanizer/SKILL.md`
- `services/personalized_humanizer.py`
- `services/workflow_orchestration.py`
- `tests/test_personalized_humanizer.py`
- `docs/architecture/personalized-humanizer.md`
- `PROJECT.md`
- existing installed generic `humanizer` skill guidance

## Implementation Steps

1. Add an explicit pipeline-position contract for personalized humanizer runs.
2. Preserve the existing standalone behavior while adding an `after_generic_humanizer` mode that limits the pass to personal voice adaptation.
3. Surface pipeline position in debug/audit output and durable run metadata.
4. Add tests proving the personalized step can run after generic cleanup without re-owning generic cleanup.
5. Update the skill/docs/project truth to describe the intended optional pipeline role.
6. Run targeted tests and validation.

## Acceptance Criteria

- Personalized humanizer remains optional and voice-specific.
- Existing standalone behavior remains compatible.
- A post-generic pipeline run does not try to replace the generic humanizer's broad anti-AI cleanup.
- Debug output makes the selected pipeline position explicit.
- Tests cover both existing and post-generic behavior.
