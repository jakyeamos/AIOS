# Provenance Map

Date: 2026-06-24

## Changed Instruction Text

| Change | Source | Destination | Provenance |
|---|---|---|---|
| Rewrote prompt-library purpose clause | `prompts/README.md:10` | Same file | Request-driven no-op cleanup; canonical behavior comes from existing prompt-library validation and eval-contract sections. |
| Added instruction-hygiene module | User request plus existing `skills/operating-language/SKILL.md` weak-term rule | `config/tmcp/portable-dev-process/modules/instruction_hygiene.md` | Consolidates no-op definition, scoring, evidence, disposition, safety exclusion, and validation rules for future instruction audits. |
| Added instruction-hygiene task | User request | `config/tmcp/portable-dev-process/tasks/instruction_hygiene.md` | Routes future prompt/skill/instruction cleanup to the module and required records. |
| Added advisory scanner | User request phase 5 optional scanner requirement | `tools/no-op-instruction-scan.mjs` | Implements candidate reporting with allowlist support and no automatic deletion. |
| Added scanner allowlist | Candidate ledger NOC-002 through NOC-006 | `config/tmcp/no-op-scan-allowlist.json` | Preserves imported metadata and anti-examples with line-level reasons. |

## Retained Candidate Provenance

- Remotion "Best practices" fields are imported workflow-skill metadata in
  `config/workflows/skills.json`.
- `skills/operating-language/SKILL.md:57` is a project skill source rule that
  rejects weak terms; quoted generic terms remain because they are examples of
  what not to preserve.
