# Context Loop System Audit

Date: 2026-06-23

## Existing Surfaces

- Workflow runners and CLI surfaces live in `services/aios_cli.py`, `services/workflow_orchestration.py`, hook scripts, and managed runtime entrypoints under `bin/`.
- Durable learning and writeback infrastructure already exists through `workflow_learning_events`, `improvement_writebacks`, `memory_writeback_proposals`, `services/learning_analysis.py`, and `services/conservative_optimizer.py`.
- Second-brain and memory integrations exist through context compiler packets, memory layers, NotebookLM routing, Obsidian routing docs, and local SQLite memory tables.
- Prompt, skill, quality, and lifecycle governance already exist through registries under `config/`, success criteria, verifier/evidence artifacts, and workflow reports.
- A close adjacent review-learning workflow exists in `services/personalized_humanizer.py`, which records outputs, feedback, and candidate updates without automatic profile mutation.
- Persistence is SQLite plus inspectable JSON/Markdown artifacts.
- Tests use `uv run pytest -q` for Python, Node's test runner for context compiler tests, and focused service tests under `tests/`.

## Missing

- No general inner-loop run record that answers what context a draft used.
- No workflow-general review-event model for pairing an AI output with a human-approved final output.
- No artifact-level approved/rejected lesson file dedicated to future inner-loop retrieval.
- No draft-only email context-loop primitive.
- No metrics report that ties inner-loop retrieval, review outcomes, candidates, and approvals together.

## Placement

The minimum safe implementation should live in `services/context_loops.py`, with CLI access through `python bin/aios.py context-loops ...` and human-readable contract artifacts under `aios/context-loops/`.

This avoids replacing Phase 9 learning infrastructure and instead adds a concrete run/review/candidate primitive that can later emit or consume governed writebacks.

## Minimum Safe Implementation

- Store inner-loop runs, review events, and learning candidates in SQLite.
- Keep approved lessons in a readable Markdown file.
- Require explicit candidate approval plus separate application before future runs read new lessons.
- Keep email as a local draft-only pilot.
- Flag unsupported commitments before human review.
- Preserve source references and approved lessons read by each run.

## Deferred

- Real Gmail/mailbox integration.
- Automatic draft insertion into email clients.
- Calendar, project-tracker, and CRM retrieval.
- Semantic diffing beyond deterministic textual diff plus taxonomy classification.
- Automatic integration with `improvement_writebacks`.
- UI surfaces for reviewing candidates.
