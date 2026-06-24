# Phase 15 Skill Authoring Comparison

Generated: 2026-06-23

skill-authoring-comparison

## Scope

This is the pre-review artifact for Phase 15 Plan 15-07. It compares the local skill-authoring inventory against the `mattpocock/write-a-skill` target principles before any final canonical merge decision.

No canonical skill rewrite is approved by this document. No plugin, cache, or global skill file should be modified until the recommendation set below is reviewed.

## Source Evidence

- Plan source: `.planning/phases/15-agent-skill-portfolio-audit-and-external-library-integration/15-07-PLAN.md`
- Inventory source: `docs/phase-15-skill-inventory.md`, especially the `write-a-skill` section and its `skill-creator`, `writing-skills`, and `skill-development` decision note.
- Local skill files inspected:
  - `/Users/jakyeamos/.claude/skills/write-a-skill/SKILL.md`
  - `/Users/jakyeamos/.codex/skills/.system/skill-creator/SKILL.md`
  - `/Users/jakyeamos/.codex/plugins/cache/openai-curated/superpowers/b4b39dbf/skills/writing-skills/SKILL.md`
  - `/Users/jakyeamos/.claude/plugins/marketplaces/claude-plugins-official/plugins/plugin-dev/skills/skill-development/SKILL.md`
  - `/Users/jakyeamos/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/skills/skill-creator/SKILL.md`
  - `/Users/jakyeamos/.claude/plugins/marketplaces/claude-plugins-official/plugins/plugin-dev/skills/agent-development/SKILL.md`
  - `/Users/jakyeamos/.claude/plugins/marketplaces/claude-plugins-official/plugins/plugin-dev/skills/command-development/SKILL.md`

## Comparison Matrix

| Skill path | Strengths | Missing pieces relative to `mattpocock/write-a-skill` | Overlapping pieces | Recommended merge target |
|---|---|---|---|---|
| `/Users/jakyeamos/.claude/skills/write-a-skill/SKILL.md` | Already gives a compact global route for skill creation, trigger-rich descriptions, progressive disclosure, scripts, assets, examples, and always-loaded-vs-intent-specific placement. It is the most appropriate final destination if a reviewed canonical skill is approved. | It currently reads as a settled canonical result instead of a reviewed merge product. It does not preserve enough source attribution from the comparison work, and it has no conditional route to heavier eval workflows. | Six Plan 15-07 principles, trigger descriptions, progressive disclosure, deterministic scripts, short examples. | Candidate destination only after review; do not treat as final canonical authority yet. |
| `/Users/jakyeamos/.codex/plugins/cache/openai-curated/superpowers/b4b39dbf/skills/writing-skills/SKILL.md` | Strongest behavior source. It treats skill authoring as TDD for process documentation, requires pressure scenarios, emphasizes discovery through descriptions, warns that workflow summaries in descriptions can cause agents to skip the body, and gives concrete token-efficiency rules. | Heavier than the upstream lightweight authoring target; the iron-law testing posture is too strict for every small local edit; it is not Claude plugin-layout-specific. | Trigger-rich descriptions, concise body, progressive disclosure, reference files, examples only when useful, verification pressure. | Strongest source to merge from; primary behavioral basis for canonical `write-a-skill`. |
| `/Users/jakyeamos/.codex/skills/.system/skill-creator/SKILL.md` | Best Codex-native structural guide. It covers degrees of freedom, validation integrity, `agents/openai.yaml`, scripts/references/assets, init and validation scripts, forward-testing, and generated interface metadata. | Less focused on Claude Code global skill ergonomics; frontmatter guidance includes what the skill does as well as when to use it; main body is too large for a compact default route. | Frontmatter, scripts, references, assets, progressive disclosure, validation, forward-testing. | Secondary source for Codex portability and validation details. |
| `/Users/jakyeamos/.claude/plugins/marketplaces/claude-plugins-official/plugins/plugin-dev/skills/skill-development/SKILL.md` | Strongest Claude plugin structure source. It explains plugin skill layout, imperative writing style, exact trigger phrase examples, scripts/references/assets, and plugin validation. | Plugin-centric; too broad for a lightweight global authoring route; less explicit than `writing-skills` about behavior pressure-testing and description shortcut failure modes. | Skill anatomy, trigger descriptions, progressive disclosure, scripts, references, examples, validation. | Secondary source for Claude plugin layout and bundled-resource guidance. |
| `/Users/jakyeamos/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/skills/skill-creator/SKILL.md` | Strongest eval-heavy authoring loop. It captures intent, writes test prompts, runs with-skill and baseline comparisons, grades results, opens review UI, iterates from feedback, and supports description optimization. | Too heavy and tool-specific for default use; much of the workflow should be conditional rather than inline in a concise global `write-a-skill` skill. | Trigger evals, skill iteration, user review, examples, scripts, references. | Conditional reference/source for high-risk or benchmarked skill work. |
| `/Users/jakyeamos/.claude/plugins/marketplaces/claude-plugins-official/plugins/plugin-dev/skills/agent-development/SKILL.md` | Best adjacent explanation of trigger descriptions as dispatch metadata, including proactive/reactive trigger scenarios and detailed body pointers. | Agent-specific; system prompts, model, color, and tool restrictions do not belong in a skill-authoring core except as analogies. | Trigger metadata, invocation boundaries, frontmatter discipline. | Borrow trigger wording discipline only; leave skill itself unchanged. |
| `/Users/jakyeamos/.claude/plugins/marketplaces/claude-plugins-official/plugins/plugin-dev/skills/command-development/SKILL.md` | Useful adjacent guidance that commands/skills are instructions for agent consumption and that frontmatter should be actionable. It also notes the legacy command-vs-skill layout boundary. | Command-specific; most YAML fields, arguments, and command mechanics do not belong in `write-a-skill`. | Agent-consumption writing style, frontmatter quality, reusable workflow packaging. | Borrow agent-consumption wording only; leave skill itself unchanged. |
| `/Users/jakyeamos/.claude/plugins/cache/claude-plugins-official/skill-creator/unknown/skills/skill-creator/SKILL.md` | Cache duplicate of the marketplace `skill-creator` route; useful as evidence that the eval-heavy authoring workflow exists in installed local skill sources. | Same heaviness and tool-specificity as marketplace `skill-creator`; cache ownership makes it a poor canonical target. | Same as marketplace `skill-creator`. | Do not modify; treat as duplicate evidence. |
| `/Users/jakyeamos/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/skills/writing-skills/SKILL.md` | Claude-side copy of the `writing-skills` process-documentation/TDD approach discovered in Plan 15-01. | Cache-owned duplicate; should not be edited as the canonical local route. | Same as `writing-skills`. | Do not modify; use as corroborating source. |
| `/Users/jakyeamos/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/skills/writing-skills/anthropic-best-practices.md` | Official best-practice reference for skills, especially progressive disclosure and discoverability. | Reference file, not a triggerable route or local merge target. | Frontmatter, progressive disclosure, resource organization. | Keep as reference; do not inline wholesale. |
| `/Users/jakyeamos/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/skills/writing-skills/testing-skills-with-subagents.md` | Strong pressure-testing reference for checking whether agents use a skill correctly under realistic prompts. | Reference file; too deep for default authoring route. | Verification, subagent testing, anti-rationalization. | Keep as conditional reference for risky behavior changes. |
| `/Users/jakyeamos/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/skills/writing-skills/examples/CLAUDE_MD_TESTING.md` | Concrete evidence that small instruction wording changes affect agent behavior. | Example artifact, not a general skill-authoring route. | Trigger testing and behavior comparison. | Keep as example evidence only. |
| `/Users/jakyeamos/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/skills/writing-skills/persuasion-principles.md` | Useful explanation of why authority, commitment, and rationalization-resistant wording can affect agent compliance. | Easy to overfit or over-expand the canonical route if included directly. | Instruction design and compliance psychology. | Reference only; do not inline into default route. |
| `/Users/jakyeamos/.claude/plugins/marketplaces/claude-plugins-official/plugins/hookify/skills/writing-rules/SKILL.md` and cache duplicate | Focused rule-authoring example with concrete trigger phrases and deterministic syntax. | Hookify-specific; not a general skill authoring workflow. | Trigger wording and rule syntax discipline. | Leave alone. |
| Terrace/GSD artifact-writing skills listed under `write-a-skill` overlap in Plan 15-01 | They show local conventions for writing durable agent-facing artifacts and keeping phase/state documents structured. | They are not skill-authoring skills; treating them as merge candidates would blur task-specific workflow writing with general skill creation. | Artifact discipline, state tracking, reviewable writebacks. | Do not merge into `write-a-skill`; use only as local style evidence if needed. |

## Strongest Merge Target

The strongest merge target is a reviewed global route at `/Users/jakyeamos/.claude/skills/write-a-skill/SKILL.md`, with `/Users/jakyeamos/.codex/plugins/cache/openai-curated/superpowers/b4b39dbf/skills/writing-skills/SKILL.md` as the strongest source of behavior and `/Users/jakyeamos/.claude/plugins/marketplaces/claude-plugins-official/plugins/plugin-dev/skills/skill-development/SKILL.md` as the strongest source of Claude plugin structure.

Reasoning:

1. A global `write-a-skill` route is the right destination because the task is cross-project and should be available without relying on plugin cache ownership.
2. `writing-skills` is the strongest content basis because it addresses the highest-risk failure mode: agents write plausible skill prose without verifying that future agents will actually trigger and obey it.
3. `skill-development` should not be the primary target because it is plugin-specific, but its scripts/references/assets and plugin layout guidance should be preserved.
4. `skill-creator` should not be the default target because its eval loop is valuable but too heavy for ordinary small skill edits.

## Recommendation Set For Review

1. Approve `/Users/jakyeamos/.claude/skills/write-a-skill/SKILL.md` as the destination path only after review, not as an already-final canonical authority.
2. Base the canonical content on `writing-skills` trigger discipline, concise body guidance, and pressure-testing rules, but soften the absolute TDD requirement into a risk-based rule for small edits.
3. Preserve `skill-development` guidance for Claude plugin resource layout: `scripts/`, `references/`, `assets/`, trigger phrase specificity, and imperative agent-consumption style.
4. Preserve `skill-creator` as a conditional escalation path for high-risk or measurable skill work: baseline runs, eval prompts, quantitative assertions, review UI, and description optimization should be referenced, not inlined.
5. Do not edit plugin cache or marketplace skill files. They are source evidence and upstream-owned artifacts, not retirement targets.
6. Do not merge Terrace/GSD artifact-writing skills into `write-a-skill`. They are useful local style examples but not general skill-authoring workflows.
7. Before a canonical rewrite, decide whether the final skill should be Claude-only, Codex-only, or dual-runtime. The source set currently contains both Claude and Codex conventions, and the final route should not silently mix incompatible paths.

## Open Review Questions

1. Should the final `write-a-skill` skill use Claude-style description language (`This skill should be used when...`) or Codex/superpowers language (`Use when...`)?
2. Should pressure testing be mandatory for every skill edit, or required only for new skills, discipline-enforcing skills, and risky behavior changes?
3. Should the final skill point to the existing eval-heavy `skill-creator` route by path, or summarize the escalation criteria without depending on plugin cache paths?
4. Should `/Users/jakyeamos/.claude/skills/write-a-skill/SKILL.md` remain the global destination, or should a Codex-visible peer skill also be created later under `/Users/jakyeamos/.agents/skills/` or `/Users/jakyeamos/.codex/skills/`?
