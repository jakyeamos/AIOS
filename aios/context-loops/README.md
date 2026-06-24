# AIOS Context Loops

Context loops preserve what an AI workflow knew before producing work and what human review revealed afterward.

## Inner Loop

The inner loop records:

- task type, input, trigger, prompt version, and guidance version
- retrieved context and source refs
- approved lessons read from `approved-lessons.md`
- generated draft or output
- uncertainty flags, unsupported commitments, assumptions, and handoff notes

The key question is: what context did the AI use to produce this output?

## Outer Loop

The outer loop pairs an inner-loop draft with a human review event, computes a textual diff, classifies the evidence, and proposes a learning candidate.

Candidates are evidence, not rules. They stay in `candidate` state until a human approves, rejects, defers, marks one-off, or marks human-judgment-only. Only approved and applied candidates are appended to `approved-lessons.md`.

## Commands

```bash
python bin/aios.py context-loops email-draft --task-input "Reply that I'll review next week" --json
python bin/aios.py context-loops record-review --run-id <run-id> --outcome edited_and_sent --final-output-file final.txt
python bin/aios.py context-loops review --json
python bin/aios.py context-loops approve <candidate-id>
python bin/aios.py context-loops reject <candidate-id> --note "Too broad"
python bin/aios.py context-loops apply-approved
python bin/aios.py context-loops metrics --write-report
```

The email pilot is draft-only. No Gmail or send integration is wired.

## Extension Pattern

For decks, reports, briefs, code review, issue triage, PRDs, project planning, client updates, and research summaries, define:

- pre-work context to retrieve
- reversible output artifact
- human review outcome
- safe learning categories
- human-only judgment boundaries
- approved lesson destination
