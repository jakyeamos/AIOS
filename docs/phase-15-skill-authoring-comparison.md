# Phase 15 Skill Authoring Comparison

Generated: 2026-06-23

skill-authoring-comparison

## Decision

Create a new canonical global skill at `/Users/jakyeamos/.claude/skills/write-a-skill/SKILL.md`.

Rationale: existing plugin skills cover broad skill creation, evals, plugin packaging, hooks, agents, and commands, but no local global skill gives a compact always-available authoring route tuned for thin SKILL.md bodies, trigger discipline, progressive disclosure, deterministic scripts, and examples only when they improve agent behavior.

## Comparison Matrix

| Skill path | Strengths | Missing pieces relative to write-a-skill | Overlapping pieces | Recommended merge target |
|---|---|---|---|---|
| `/Users/jakyeamos/.claude/plugins/cache/claude-plugins-official/skill-creator/unknown/skills/skill-creator/SKILL.md` | Strong iterative creation/eval loop, prompt tests, benchmark framing, description optimization. | Too large for a quick global authoring route; description summarizes capability more than trigger discipline; eval machinery is more than most simple skill edits need. | Frontmatter, skill anatomy, testing, iterative improvement. | Source behavior for eval-heavy skill work; canonical route points to it when measurement is needed. |
| `/Users/jakyeamos/.codex/plugins/cache/openai-curated/superpowers/b4b39dbf/skills/writing-skills/SKILL.md` | Best discipline for skill TDD, pressure scenarios, concise descriptions, CSO, token efficiency, and anti-rationalization. | TDD pressure testing can be heavier than lightweight authoring tasks; does not focus on Claude Code plugin resource layout. | Trigger-rich descriptions, examples only when useful, reference routing, skill body concision. | Primary source for canonical global `write-a-skill`. |
| `/Users/jakyeamos/.claude/plugins/marketplaces/claude-plugins-official/plugins/plugin-dev/skills/skill-development/SKILL.md` | Strong plugin-specific structure, resources, scripts/references/assets, progressive disclosure, validation steps. | Plugin-centric; body is long for the default route; less explicit about examples only when behavior improves. | Skill anatomy, scripts, references, assets, description triggers, progressive disclosure. | Source for resource layout and script/reference guidance. |
| `/Users/jakyeamos/.claude/plugins/marketplaces/claude-plugins-official/plugins/plugin-dev/skills/skill-development/references/skill-creator-original.md` | Concise general skill creation guide and init/package workflow. | Init/package assumptions do not fit all global personal skills; less emphasis on keeping always-loaded context thin. | Skill structure, resources, validation. | Reference-only source; do not make primary. |
| `/Users/jakyeamos/.claude/plugins/marketplaces/claude-plugins-official/plugins/plugin-dev/skills/agent-development/SKILL.md` | Strong trigger-description thinking for subagents and system prompt design. | Agent-specific, not a skill authoring workflow. | Trigger descriptions and invocation boundaries. | Leave alone; borrow trigger wording discipline. |
| `/Users/jakyeamos/.claude/plugins/marketplaces/claude-plugins-official/plugins/plugin-dev/skills/command-development/SKILL.md` | Good command/frontmatter and plugin command organization guidance. | Command-specific, not skill-specific. | Frontmatter quality and trigger examples. | Leave alone; borrow only trigger specificity. |
| `/Users/jakyeamos/.claude/plugins/cache/claude-plugins-official/hookify/unknown/skills/writing-rules/SKILL.md` | Focused rule authoring for hooks. | Hookify-specific; not general skill creation. | Trigger wording and deterministic rule syntax. | Leave alone. |
| `/Users/jakyeamos/.claude/plugins/marketplaces/claude-plugins-official/plugins/hookify/skills/writing-rules/SKILL.md` | Marketplace duplicate of hook rule guidance. | Same as cache copy. | Same as cache copy. | Leave alone. |
| `/Users/jakyeamos/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/skills/writing-skills/SKILL.md` | Claude-side copy of the TDD/process-documentation approach. | Duplicates the Codex-visible superpowers version read during execution. | Same as writing-skills. | Leave alone; canonical global skill summarizes durable rules. |
| `/Users/jakyeamos/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/skills/writing-skills/anthropic-best-practices.md` | Official best-practice source for skill authoring. | Reference file, not triggerable route. | Frontmatter, progressive disclosure, resources. | Keep as reference. |
| `/Users/jakyeamos/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/skills/writing-skills/testing-skills-with-subagents.md` | Strong pressure-testing pattern for verifying skill behavior. | Reference file, not always needed. | Skill testing and eval discipline. | Keep as reference; canonical route mentions testing only when behavior is risky. |
| `/Users/jakyeamos/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/skills/writing-skills/examples/CLAUDE_MD_TESTING.md` | Concrete evidence that small prompt wording changes affect behavior. | Example artifact, not general workflow. | Trigger testing. | Keep as reference. |
| `/Users/jakyeamos/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/skills/writing-skills/persuasion-principles.md` | Useful psychology for prompt/skill compliance. | Can over-expand the canonical route if always included. | Description and instruction design. | Reference only; do not inline. |

## Merge Notes

- Canonical trigger discipline comes from `writing-skills`, `skill-development`, and `agent-development`.
- Canonical progressive disclosure rules come from `writing-skills` and `skill-development`.
- Canonical scripts/assets/reference guidance comes from `skill-development` and `skill-creator-original`.
- Canonical eval/pressure-test guidance comes from `writing-skills` and `skill-creator`, but remains conditional so lightweight edits stay lightweight.
- No existing skill-authoring skill was modified or retired in this plan. Existing plugin skills remain owned by their plugin caches or marketplaces.
