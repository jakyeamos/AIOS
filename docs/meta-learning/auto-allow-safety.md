# Meta-Learning Auto-Allow Safety

AIOS may observe repeated commands, but repeated use does not make a permission safe. Auto-allow recommendations are scored in a separate channel from ordinary meta-learning proposals: `meta_learning_auto_allow_recommendations`.

## Safe To Suggest

Commands may be suggested as low risk when they are deterministic, local, reversible, and do not write to the filesystem or external systems. Examples:

- read-only inspection such as `rg`, `ls`, `sed -n`, `wc`, and `pwd`
- local test commands such as `uv run pytest -q`
- local lint, typecheck, and format-check commands

## Manual Review Required

These commands are not auto-allowed from frequency alone:

- write-capable commands
- Git operations
- package installation or lockfile mutation
- network calls
- deployment-related commands
- file deletion or mutation
- credential-adjacent commands
- shell expansion, pipes, command substitution, redirects, or dynamic arguments

## Never Auto-Allow By Default

AIOS must never auto-allow these by default:

- destructive delete commands
- secret or credential access
- deploy, publish, release, or production commands
- external network writes
- credential modification

## Review Contract

Auto-allow assessments are recommendations only. Dangerous commands stay blocked for manual review even when they appear repeatedly. Ordinary meta-learning proposals may mention command repetition, but permission escalation belongs in the dedicated auto-allow safety channel.
