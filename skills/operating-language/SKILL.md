---
name: operating-language
description: Extract and maintain a project operating language: domain terms, architecture terms, and agent-control leading words that improve human alignment, skill invocation, implementation consistency, and review behavior. Use when a project needs a glossary, ubiquitous language, design vocabulary, quality-gate language, agent prompt vocabulary, repeated behavioral hooks, or a canonical OPERATING_LANGUAGE.md artifact.
---

# Operating Language

Create or update a project-level operating language that agents and humans can use consistently across prompts, specs, code, issues, docs, tests, and review gates.

This is not only a glossary. It is a behavioral control surface.

A strong operating language contains:

- domain terms: what the product means
- architecture terms: how the system is shaped
- agent-control leading words: compact concepts that cause predictable agent behavior

## Goal

Produce or update a canonical `OPERATING_LANGUAGE.md` that makes the project easier to reason about, implement, test, review, and automate.

The file should reduce ambiguity, collapse repeated instruction prose into strong leading words, and give agents reusable handles for expected behavior.

## Process

1. Scan the smallest sufficient set of conversation, docs, specs, issues, README files, architecture notes, tests, and existing prompts.
2. Extract candidate terms from three layers:
   - Domain language: product nouns, lifecycle states, user roles, business concepts, workflows, events, permissions, and source-of-truth concepts.
   - Architecture language: system boundaries, modules, integration seams, data ownership, service responsibilities, UI/data split, test seams, and repo-specific architectural concepts.
   - Agent-control language: repeated behavioral ideas that agents should execute predictably, especially concepts used in prompts, quality gates, review comments, skills, or workflow docs.
3. Identify terminology problems:
   - one word used for multiple concepts
   - multiple words used for one concept
   - vague terms that cannot guide implementation
   - catchy terms that do not change behavior
   - local names that should become canonical
   - canonical names that are being ignored in code/docs/tests
   - missing leading words where prose repeats the same idea
4. Run the Leading Word Test for each candidate agent-control term.
5. Reject weak leading words.
6. Pick canonical terms opinionatedly.
7. Include trigger phrasing for every agent-control leading word.
8. Write or update `OPERATING_LANGUAGE.md`.
9. Output a short summary of new terms, rejected terms, resolved ambiguities, leading words introduced, and docs/prompts/code areas that should migrate.

## Leading Word Test

A leading word qualifies only if it is:

- compact: shorter than repeatedly explaining the behavior
- pretrained: likely already meaningful to the model
- behavioral: changes what the agent does
- reusable: useful across prompts, docs, code review, or gates
- observable: reviewers can tell whether it happened
- non-overlapping: not redundant with another canonical term

Reject weak terms that sound good but do not alter behavior. Do not keep terms like "be careful," "high quality," "thoughtful," or "robust" unless the project gives them concrete behavioral meaning.

## Output Format

Write `OPERATING_LANGUAGE.md` using this structure:

```markdown
# Operating Language

## Purpose

This file defines the canonical language for this project. Use these terms in prompts, specs, issues, code review, tests, docs, and agent workflows.

Terms are grouped into:
- Domain Language
- Architecture Language
- Agent-Control Leading Words
- Relationships
- Flagged Ambiguities
- Rejected Terms
- Migration Notes

## Domain Language

| Term | Definition | Use when | Aliases to avoid | Verification signal |
|---|---|---|---|---|

## Architecture Language

| Term | Definition | Use when | Aliases to avoid | Verification signal |
|---|---|---|---|---|

## Agent-Control Leading Words

| Leading word | Behavioral meaning | Trigger when | Do not use for | Completion criterion |
|---|---|---|---|---|

## Relationships

## Flagged Ambiguities

## Rejected Terms

| Rejected term | Reason rejected | Use instead |
|---|---|---|

## Migration Notes

## Example Dialogue

## Quality Bar
```

## Rules

- Define what each concept is, not every thing it does.
- Prefer domain expert language over implementation language.
- Do not include generic programming terms unless the product gives them special meaning.
- Include code/module terms only when they shape implementation or review behavior.
- Prefer terms that clarify ownership, boundaries, dependencies, or testing strategy.
- If a term appears in code but not docs, note the mismatch.
- For agent-control terms, include the stop condition. A term without a stop condition invites premature completion.
- If the agent would behave the same without the term, remove it.

## Quality Bar

Before finishing, check:

- Every term has one canonical meaning.
- Every agent-control term changes behavior.
- Every leading word has a trigger and completion criterion.
- Every rejected synonym has a preferred replacement.
- No generic quality words remain unless made observable.
- The file helps both humans and agents make better decisions.
