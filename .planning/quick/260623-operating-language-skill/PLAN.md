# Quick Task 260623: Operating Language Skill

## Task

Install the requested `operating-language` skill and create the canonical AIOS `OPERATING_LANGUAGE.md` artifact.

## Scope

- Add `skills/operating-language/SKILL.md`.
- Add `skills/operating-language/agents/openai.yaml`.
- Add root `OPERATING_LANGUAGE.md`.
- Register the skill in `config/workflows/skills.json`.
- Update `PROJECT.md` and `.planning/STATE.md` with the durable state change.

## Verification

- Run `pnpm context:compile --task "Install operating-language skill and create canonical AIOS operating language artifact"` before editing.
- Run the skill validator for `skills/operating-language`.
- Run `pnpm context:validate`.
