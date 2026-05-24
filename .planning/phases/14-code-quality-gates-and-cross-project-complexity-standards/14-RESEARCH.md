# Phase 14: Code Quality Gates And Cross-Project Complexity Standards — Research

**Gathered:** 2026-05-23
**Status:** Ready for planning

<source_spec>
## Source Spec

Phase 14 is specified in the "Audit and implement: add a complexity + simplification quality gate to AIOS and every project workflow" prompt (ingested 2026-05-23). The spec adds a mandatory post-large-work quality gate to all agent workflows, adds pre-check implementation questions, integrates complexity-optimizer patterns, creates a root quality gate doc, and produces backfill hotspot inventories for every first-class project.

The source prompt is the authoritative design for this phase. This document distills the implementation-ready constraints and design decisions from that prompt.
</source_spec>

<domain>
## Phase Boundary

Phase 14 is a workflow governance and documentation layer. It does not:
- Remediate the hotspots it discovers (remediation is a follow-on pass)
- Rewrite or refactor existing code (additive only)
- Replace or duplicate the AIOS-internal quality script from Plan 10-08

Phase 14 adds agent workflow rules, pre-check habits, cross-project backfill inventories, and a root quality gate doc. It operates at the agent instruction layer (`config/agent-rules.md`, `AGENTS.md`, `~/.claude/CLAUDE.md`) and at the documentation layer (backfill docs per project, quality gate spec).

### Relationship to Plan 10-08

Plan 10-08 produced:
- `scripts/quality-eval.sh` — read-only shell script for AIOS-internal hotspot detection (file size, import violations, dead code, shellcheck)
- `docs/backfill/agent-eval-backfill.md` — AIOS-internal backfill inventory focused on eval instrumentation gaps

Phase 14 is additive and complementary:
- Adds algorithmic complexity and code simplification as explicit review dimensions (not just file-size metrics)
- Extends backfill coverage to all six linked projects beyond AIOS
- Elevates the gate from an optional script to a mandatory agent workflow rule
- Adds pre-check questions at implementation time (not just post-work audit)
</domain>

<projects>
## First-Class Projects

From `~/.claude/CLAUDE.md` project roots table:

| Alias | Path | Notes |
|-------|------|-------|
| AIOS | ~/AIOS | AI OS hooks / scripts / db — primary project |
| soundscape-app | ~/projects/soundscape-app | Music library manager |
| amos-saas | ~/projects/amos-saas | Amos SaaS platform |
| GitNexus | ~/projects/GitNexus | GitNexus framework |
| Terrace | ~/projects/Terrace | Terrace dev framework |
| tm | ~/projects/tm | Taski — local-first project tracker |
| portfolio | ~/projects/portfolio | Personal portfolio site |

Each project needs a backfill doc scoped to its risk surface. AIOS gets the most detailed treatment (Plan 14-05). The others are grouped by size and risk (Plans 14-06, 14-07, 14-08).
</projects>

<key_questions>
## Key Questions Resolved from Design Spec

### Q1: Should the gate be mandatory or advisory?
Mandatory. The rule must say agents MUST run the gate after large work — not "consider running." The definition of large work is the explicit trigger list from the spec (5+ files, 300+ lines, new feature, cross-package, DB/schema change, pipeline/model logic, UI with state, agent/workflow change, performance-sensitive path, infrastructure code).

### Q2: Should codex-complexity-optimizer be vendored, linked, or rewritten locally?
Prefer a local checklist. The repo at https://github.com/Kappaemme-git/codex-complexity-optimizer defines a set of review patterns. Creating a local `docs/quality/complexity-checklist.md` (and optionally a lightweight `scripts/complexity-check.sh`) avoids a fragile external dependency while preserving the patterns. The GitHub repo is referenced as a source of inspiration, not imported as a dependency.

### Q3: Where do the agent rule additions go?
Three locations:
1. `config/agent-rules.md` — new rule (Rule 10) for the AIOS agent context
2. `AGENTS.md` — top-level AIOS agent instructions get the gate section
3. `~/.claude/CLAUDE.md` — Quality Ladder extended with complexity+simplification as a standard gate step

Project-specific `AGENTS.md` files in linked projects get a short cross-reference pointing to the root gate doc.

### Q4: Do the pre-check questions belong in agent-rules.md or a separate checklist file?
Both. `config/agent-rules.md` gets the formal rule definition. A separate `docs/quality/implementation-pre-check.md` doc exposes them as a standalone checklist usable by Codex and Claude without loading full agent-rules context.

### Q5: How should backfill docs be structured?
Each backfill doc uses the hotspot template from the spec:
- Project name, date of audit, scope reviewed, commands attempted
- Complexity hotspots and simplification hotspots with the structured `### Hotspot:` format
- Test/coverage gaps blocking safe cleanup
- Suggested remediation order, risk level, agent-safe classification
- Definition of Done for quality standard

### Q6: Should remediation happen in this phase?
No. The spec is explicit: "Do not perform broad code refactors yet unless they are necessary to add the workflow/docs/checks." Every hotspot is recorded, classified, and assigned a remediation priority, but not fixed in this pass. A follow-on prompt/phase handles remediation in priority order with tests before each fix.

### Q7: How does this connect to AIOS Phase 6/7 (Standards + Delta Scoring)?
Phase 14 is an additive quality dimension. Once Phase 6/7 infrastructure is in place, the complexity+simplification findings recorded in backfill docs can feed into the delta scoring and health backfill system as a first-class quality dimension. Phase 14 does not wait for Phase 6/7 — it adds the documentation and workflow gate now so evidence accumulates before the scoring infrastructure is ready.
</key_questions>

<open_questions>
## Open Questions

All questions resolved from the design spec. No blockers for planning.
</open_questions>
