# Email Drafting Pilot

The current pilot is a local draft workflow. It does not fetch mail and cannot send.

## Inner Loop

1. Read approved lessons.
2. Accept manual email task input.
3. Create a draft-only output.
4. Flag unsupported commitments.
5. Save a run record.

## Human Review

The operator records whether the draft was sent unchanged, edited and sent, edited but not sent, deleted, rejected, left pending, replaced manually, or escalated to human-only judgment.

## Outer Loop

The outer loop compares the draft and final reviewed output, classifies edits, and creates learning candidates. Candidates require explicit approval and a separate apply step before future drafts can read them.

## Deferred

- Gmail fetching
- draft creation in a mail client
- send-state detection
- calendar and tracker retrieval
- relationship memory beyond approved lessons
