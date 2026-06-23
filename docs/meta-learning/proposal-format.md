# Meta-Learning Proposal Format

Meta-learning proposals are review artifacts. They are not applied automatically.

## Required Fields

- `proposal_id`
- `title`
- `summary`
- `target_layer`
- `target_file`
- `confidence_score`
- `risk_level`
- `evidence`
- `why_this_layer`
- `proposed_patch`
- `rollback`
- `requires_manual_approval`
- `source_signal_id`
- `status`
- `conflict`

## Approval And Rejection

Every generated proposal defaults to `pending_review` and `requires_manual_approval = true`. Rejection should preserve the evidence and reason so future runs do not rediscover the same weak proposal without new evidence.

## Rollback

Rollback text must name how to undo an approved change. Because proposal patches are review text, rollback is usually "revert the reviewed change in the target storage and mark the proposal rejected or superseded."

## Conflicts

Conflict records include:

- older rule
- newer signal
- recommended action
- rationale

Recommended actions are `replace`, `narrow`, `split_by_context`, or `ask_user`.

## Shadow Eval Expectations

Medium/high-impact proposals require a shadow eval plan or documented exemption before durable global promotion. Eval plans compare baseline behavior without the proposed rule against shadow behavior with the proposed rule.
