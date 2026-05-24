# Phase 15: Agent Skill Portfolio Audit And External Library Integration — Research

**Gathered:** 2026-05-23
**Status:** Ready for planning

<source_spec>
## Source Spec

Phase 15 is specified in the "local AI workflow/skills migration agent" prompt (ingested 2026-05-23). The spec audits the local Claude Code skill portfolio against seven target skills from mattpocock/skills, produces a merge/add/skip decision for each, and delivers upgraded or new skill files with AIOS session/run integration for `to-issues` and `handoff`.

The source prompt is the authoritative design for this phase. This document distills the implementation-ready constraints and design decisions from that prompt.
</source_spec>

<domain>
## Phase Boundary

Phase 15 operates on the Claude Code skill layer (`~/.claude/skills/`, project-level `.claude/` directories, plugin-installed skills). It does not:
- Modify AIOS internal prompt/workflow/skill registries (Phase 8 owns those)
- Automate skill improvement via machine learning (Phase 9 owns that)
- Touch AIOS Python services, SQLite schema, or any runtime code except the DB write path for `handoff` and `to-issues` AIOS integration

Phase 15 adds, upgrades, or merges skill Markdown files and creates lightweight integration hooks that write handoff docs and issue breakdowns into `aios.db` or local markdown under a known AIOS path.

### Relationship to Phase 8

Phase 8 manages the AIOS internal skill registry (JSON, lifecycle states, promotion transitions). Phase 15 manages the agent-facing Claude Code skill files. They are complementary: Phase 8 handles what AIOS knows about skills; Phase 15 handles what skills agents actually invoke.

### Relationship to Phase 9

Phase 9 creates automated learning loops that surface skill upgrade candidates from runtime evidence. Phase 15 is a one-time manual audit seeded from an external library. Phase 9 will eventually monitor whether Phase 15's upgraded skills perform better.

### AIOS Integration Points

Two skills require AIOS wiring beyond plain Markdown:

1. **to-issues (Plan 15-05):** When a plan, PRD, or design spec is decomposed into issues, write each issue as a row into a lightweight `issues` table in `aios.db` (or a local markdown folder under `~/.aios/issues/` as fallback). Each issue row carries: title, description, acceptance criteria, AFK/HITL label, dependencies, linked run ID, source file path, created_at.

2. **handoff (Plan 15-08):** When a handoff document is produced, write it to `~/.aios/handoffs/<session-id>-handoff.md` (or equivalent AIOS-managed path) and optionally append a row to `aios.db` `handoffs` table with: session_id, project, focus, suggested_skills, source_run_id, redacted flag, created_at.
</domain>

<skill_inventory_surface>
## Known Local Skill Locations

Based on system configuration and known paths, the audit in Plan 15-01 must scan:

| Location | Type | Notes |
|----------|------|-------|
| `~/.claude/skills/` | Global Claude Code skills | Primary skill home |
| `~/.claude/plugins/` | Plugin-installed skills | skill-creator, claude-mem, commit-commands, hookify, frontend-design, superpowers, claude-md-management |
| `~/AIOS/.claude/` | Project-level AIOS skills | Any AIOS-specific overrides |
| `~/projects/Terrace/.claude/` | Terrace project skills | terrace-* skills referenced in skill list |
| `~/.claude/CLAUDE.md` | Global agent instructions | Not a skill but contains workflow patterns to avoid duplicating |
| `~/AIOS/AGENTS.md` | AIOS agent rules | Same |

Known likely existing skills to compare against:
- `interrogate` / `interrogate-terrace` — compare against `grill-with-docs`
- `simplify` / `simplifier` / `code-simplifier` — compare against `improve-codebase-architecture`
- `skill-creator:skill-creator` — compare against `write-a-skill`
- `humanizer` — no direct overlap, leave alone
- `systematic-debugging` (superpowers) — compare against `diagnose`
- Any handoff/session-continuation skill
- Any issue/task-breakdown skill
</skill_inventory_surface>

<source_skills>
## Source Skills From mattpocock/skills

Seven skills from `https://github.com/mattpocock/skills` are the upstream comparison targets:

| Skill | Key Behaviors |
|-------|--------------|
| `grill-with-docs` | Challenge plan against codebase/domain language; search code before asking questions code can answer; maintain CONTEXT.md domain glossary; create ADRs only for durable decisions; sharpen fuzzy terms into canonical language; cross-check user claims against actual code |
| `diagnose` | Fast deterministic feedback loop first; reproduce before hypothesizing; ranked falsifiable hypotheses; instrument one hypothesis at a time; regression tests at correct seam; remove debug artifacts; postmortem/commit explanation |
| `improve-codebase-architecture` | Deep vs shallow modules; deletion test; interface as test surface; seams, adapters, locality, leverage, AI navigability; report-first for major refactors (candidate, files, friction, simplification, test improvement, risk, confidence, user approval required) |
| `to-issues` | Vertical tracer-bullet slices; each issue independently demoable; AFK vs HITL labels; dependencies/blockers; acceptance criteria and test expectations; publish to GitHub CLI or create local markdown |
| `prototype` | Throwaway clearly marked code; logic/state or UI prototype based on question; one-command run; no persistence default; expose full relevant state; delete or absorb after question answered; must answer specific uncertainty not become second implementation |
| `write-a-skill` | Concise SKILL.md; strong description/trigger discipline; progressive disclosure; reference files for long instructions; scripts for deterministic operations; examples only when they improve agent behavior |
| `handoff` | Compact handoff docs for next agent/session; save outside current workspace; include suggested skills; reference PRDs/issues/ADRs/commits not duplicate; redact secrets; tailor to next session's intended focus |
</source_skills>

<key_decisions>
## Key Decisions From User

1. **to-issues** and **handoff** must wire into AIOS session/run infrastructure (not just produce standalone Markdown).
2. **Do not delete existing skills.** Create a timestamped backup before modifying any existing file.
3. **Prefer merging** over replacing when an existing skill already covers significant ground.
4. **Safety rules:** no remote dependencies, no arbitrary install scripts, no globalizing project-specific skills without reason.
5. **Final skills must be agent-usable**, not just human-readable: descriptions must be trigger-rich.
</key_decisions>
