# Divergent Strategy Skill

## When to Use

Use this when:

- the task has multiple plausible approaches
- the user asks "what do you think?"
- evaluating a repo, workflow, architecture, or product idea
- designing prompts, PRDs, standards, or agent workflows
- high-level strategy matters more than immediate code

Do not use this when:

- the task is a simple bug fix
- acceptance criteria are already clear
- the task is small and deterministic
- the user explicitly wants speed over exploration

## Procedure

1. Classify task.
2. Select mode.
3. Generate candidates.
4. Run judges.
5. Build portfolio.
6. Propose memory writebacks.
7. Emit final recommendation.
8. Track entropy.

## Required Output

- Task classification and selected mode.
- Candidate portfolio, not a single winner.
- Judge scores with rationale and uncertainty.
- HOW / WHAT / FAILURE / ENTROPY memory proposals.
- Entropy observation and recommendation.
- Promotion state for any prompt, skill, judge, or workflow candidate.

## Context Packets

Load only the reference file needed for the current task:

- `references/candidates.md`
- `references/judges.md`
- `references/memory-writebacks.md`
- `references/entropy.md`
- `references/promotion-gates.md`
