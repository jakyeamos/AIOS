# Meta-Learning Layer

AIOS meta-learning turns session-level evidence into reviewable improvement proposals. It is review-first: the system may detect a pattern, score it, route it, and format a proposal, but it must not silently mutate rules, skills, commands, agent routing, second-brain notes, or permissions.

## Workflow

1. Extract signals from JSON session traces with `services.meta_learning_signals`.
2. Score and filter signals with `services.meta_learning_scoring`.
3. Route accepted signals with `services.meta_learning_router`.
4. Generate reviewable proposals with `services.meta_learning_proposals`.
5. Keep permission recommendations separate with `services.meta_learning_auto_allow`.
6. Generate shadow eval plans for medium/high-impact proposals with `services.meta_learning_shadow_eval`.

## Supported Inputs

The extractor accepts a single session mapping, a list of session mappings, or a mapping with `sessions`. It reads user messages, command lists, tool events, context events, and model events.

Detected signals include explicit corrections, repeated patterns, approvals, repeated commands, tool friction, context misses, model mismatch, scope restatements, second-brain misses, irrelevant context, and contradictions.

## Example

Input user message:

```text
From now on, always use pnpm in this repo.
```

AIOS can extract an explicit correction, score it as high confidence, route it to the project layer, and generate a proposal whose patch text asks a reviewer whether to add a narrow project-specific rule.

## Lifecycle

Proposals are stored as review artifacts. They include evidence, confidence, target layer, rollback text, manual approval status, and conflict information. Apply/reject behavior is intentionally governed; the fallback meta CLI returns review records but does not bypass approval.

## Limitations

- Signal extraction is pattern based and conservative.
- Central `aios meta` CLI integration is deferred when `services/aios_cli.py` has unrelated dirty changes; use `scripts/meta-learning-cli.py` as the fallback surface.
- Proposal patches are review text, not automatic file edits.
- Auto-allow recommendations are not ordinary learning proposals and must remain in the dedicated permission-safety channel.

## Next Iteration

- Promote the fallback meta CLI into `aios meta` after the central CLI file is clean.
- Add real session-ingestion adapters as Phase 13 surfaces mature.
- Add proposal lifecycle persistence for approved/rejected states.
