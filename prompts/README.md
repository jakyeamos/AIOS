# AIOS Prompt Library

Repo source-of-truth for reusable prompt patterns used by AIOS hooks and the
`agentize` skill.
Phase 2 extends this into validation-driven execution strategy bundles under
`config/execution-strategies/`.

## Why this exists

- Capture repeatable prompt patterns with frontmatter, output contracts, eval
  cases, and validation commands.
- Keep templates versioned and inspectable.
- Provide supporting evidence for `agentize` request compilation.
- Enable deterministic template suggestions in `hook-prompt-submit` while that
  legacy path remains active.

## Role in agentized execution

`agentize` is the primary abstraction for turning freeform requests into
execution-ready agent task packets. The prompt library remains active, but its
role is pattern memory rather than mandatory one-to-one routing.

Prompt assets should be treated as:

- `prompt template`: a reusable full instruction contract with frontmatter,
  validation, and eval cases.
- `prompt fragment`: a reusable instruction section or wording pattern.
- `agentization pattern`: evidence that a request shape maps well to a task
  packet structure, execution mode, context plan, or verification plan.
- `execution packet`: the structured output produced by `agentize`.
- `skill`: a reusable capability with inputs, outputs, lifecycle, invariants,
  and validation expectations.

When no template matches a request, `agentize` should still produce a packet
from the request semantics and record that static template mapping was not
required.

## Files

- `prompts/*.md`: templates with YAML frontmatter + instructions.
- `prompts/registry.json`: generated index used by hooks.
- `prompts/evals/<id>/cases.md`: manual evaluation cases per template.

## Use a template manually

1. Open the template file.
2. Fill required inputs.
3. Follow the instruction sequence.
4. Check output against `output_contract` and `eval_criteria`.

## Add a new template

1. Copy an existing template.
2. Fill all required frontmatter fields.
3. Ensure `id` matches filename.
4. Add `prompts/evals/<id>/cases.md`.
5. Run `python3 bin/validate-prompts.py`.

## Revise an existing template

1. Update body and/or frontmatter.
2. Increment `version`.
3. Add a `changelog` item.
4. Re-run relevant eval cases.
5. Re-run validation to regenerate `registry.json`.

## Validation

Run:

```bash
python3 bin/validate-prompts.py
```

Validation enforces schema, duplicate IDs, filename alignment, and non-empty criteria contracts.

Execution strategy validation:

```bash
python3 bin/validate-execution-strategies.py
```

This validates canonical task specs + surface strategy bundles and regenerates
`config/execution-strategies/registry.json`.

## Evaluate a template

Use `prompts/evals/<id>/cases.md`.

Each case should record:
- inputs
- expected output shape
- pass criteria checkboxes
- last run date/result/notes

## Promote to Vault

Run:

```bash
python3 bin/sync-prompts.py
```

This copies templates to `07 Templates/Prompts` in the vault and updates `prompt_library_links`.

## When recurring work deserves a template

Create a template when a task family is:
- frequent,
- high impact,
- repeatedly framed with similar structure.

## Anti-patterns

- Template bloat with generic filler steps.
- Changing templates without version/changelog updates.
- Editing vault copies directly instead of repo source.
- Accepting a template without testable eval criteria.
- Treating template selection as more authoritative than the user's current
  request.
