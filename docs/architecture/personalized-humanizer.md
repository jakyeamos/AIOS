# Personalized Humanizer Architecture

## Purpose

The personalized humanizer is an AIOS skill for rewriting text toward the
local user's approved writing voice without inventing personal facts, leaking
private corpus material, or flattening every context into one generic style.

It is intentionally not an AI-detector evasion tool. The objective is accurate
voice matching, clarity, and context-appropriate writing.

## Current Implementation

The first implementation is local-first and inspectable:

- Skill packet: `skills/personalized-humanizer/SKILL.md`
- Profile: `config/personalized-humanizer/profile.json`
- Retrieval policy: `config/personalized-humanizer/retrieval-policy.json`
- Eval cases: `config/personalized-humanizer/evals.json`
- Service: `services/personalized_humanizer.py`
- Workflow registry: `config/workflows/registry.json`
- Skill registry: `config/workflows/skills.json`

The service exposes deterministic primitives for task classification, bounded
example retrieval, voice packet generation, conservative transformation,
quality scoring, feedback capture, profile update proposals, and eval runs.

## Voice Model

The profile has four layers:

1. Global user voice: stable traits and global style/anti-style rules.
2. Contextual voice profiles: outreach, project updates, academic reflection,
   prompts/PRDs, and creative prose.
3. Task-specific constraints: audience, medium, length, tone, stakes, and
   requested polish.
4. User approval feedback: approved, edited, and rejected outputs become
   evidence for candidate profile updates.

The canonical profile is versioned. Feedback does not directly rewrite it.

## Corpus Retrieval

Retrieval must prefer approved final user-written examples over drafts and
AI-generated material. The current service accepts explicit `CorpusExample`
objects and records only hashes/provenance in voice packets. Future vault and
knowledge-topic retrieval should adapt into that same object shape.

Mode boundaries are strict by default:

- Creative/narrative sources are blocked from professional outreach.
- Professional/outreach sources are blocked from creative prose.
- Cross-mode use requires explicit opt-in.

The retrieval policy defaults to not storing excerpt text in durable records.

## Feedback And Profile Updates

The feedback loop stores:

- rewrite run hashes and scorecards
- user feedback verdicts
- optional user revision hashes
- candidate profile updates with evidence

Profile update lifecycle:

```text
draft -> candidate -> approved
draft -> candidate -> rejected
approved -> deprecated
```

Approval requires evidence. A single feedback note can create a candidate
update, but canonical profile mutation remains a separate reviewed action.

## Eval Suite

Run the focused tests with:

```bash
uv run pytest tests/test_personalized_humanizer.py -q
```

The eval suite covers:

- cold outreach message
- LinkedIn/project post
- Codex implementation prompt
- academic reflection
- creative/narrative paragraph
- technical project update
- generic AI-sounding paragraph
- text that should not be heavily rewritten

Each case produces a scorecard:

- meaning preservation: 0-5, higher is better
- voice match: 0-5, higher is better
- context fit: 0-5, higher is better
- specificity: 0-5, higher is better
- over-personalization risk: 0-5, lower is better
- generic AI feel: 0-5, lower is better
- verbosity: 0-5, lower is better

## Debug Mode

`humanize_text(..., debug=True)` returns:

- selected voice profile
- profile version
- style rules applied
- anti-style rules
- evidence refs
- confidence
- risks
- changed/not changed flag

Normal skill use should return only the rewritten output unless the user asks
for audit/debug details.

## Adding A New Mode

1. Add the mode to `VoiceMode` and `MODE_KEYWORDS` in
   `services/personalized_humanizer.py`.
2. Add a mode profile in `config/personalized-humanizer/profile.json`.
3. Add mode boundary rules in `retrieval-policy.json` if needed.
4. Add representative cases to `evals.json`.
5. Extend `tests/test_personalized_humanizer.py`.

## Privacy Rules

- Store hashes and provenance by default, not full private excerpts.
- Retrieve bounded examples only.
- Keep source mode boundaries explicit.
- Do not add personal facts unless the input already contains them or the user
  explicitly asks for them.
- Treat profile updates as reviewable proposals, not silent memory mutations.

## Example

Input:

```text
Implement the feature. Check the current code first. Add tests and docs. Do not delete existing behavior.
```

Mode: `prompt_prd`

Output:

```text
- Implement the feature.
- Check the current code first.
- Add tests and docs.
- Do not delete existing behavior.
```
