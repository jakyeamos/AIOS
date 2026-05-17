# Quick Task Plan: Agentize Skill

## Objective

Audit the prompt library and workflow/skill architecture, then add a scoped `agentize` skill that compiles messy user requests into structured execution packets.

## Context Loaded

- `AGENTS.md`
- `PROJECT.md`
- `aios/context/compiled/latest.md`
- `aios/context/features/prompt-library.md`
- `aios/context/features/skill-registry.md`
- `services/workflow_orchestration.py`
- `config/workflows/registry.json`
- `config/workflows/skills.json`
- `prompts/README.md`
- `schema.sql`

## Implementation Scope

- Add deterministic `services.agentize` packet schema, classifier, mode selector, context planner, standards attachment, verification planner, and evaluation logging.
- Register the skill and workflow in existing workflow registries.
- Add a local `skills/agentize/SKILL.md` contract.
- Reframe prompt library docs as pattern/evidence corpus while preserving existing template behavior.
- Add architecture documentation and update project truth.
- Use existing `tests/test_agentize.py` as the behavior contract and expand only if needed.

## Verification

- `uv run pytest tests/test_agentize.py -q`
- Targeted regression for prompt/workflow surfaces if time permits.
