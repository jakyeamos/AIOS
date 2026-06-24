# Duplication, Drift, And Risk Report

Date: 2026-06-24

## Duplicates

- `prompts/README.md` contained a vague purpose clause that overlapped with
  existing prompt-library contracts for frontmatter, output contracts, eval
  cases, and validation. It was rewritten instead of deleted so the purpose
  section keeps a concrete behavioral requirement.
- No exact duplicate instruction clauses were removed.

## Drift Risks

- `config/workflows/skills.json` contains imported skill metadata. Generic terms
  in imported titles can be false positives; they now require allowlist reasons
  rather than silent retention.
- `skills/operating-language/SKILL.md` intentionally quotes generic terms as
  rejected examples. The scanner ignores fenced examples and supports line-level
  allowlist entries for anti-examples that appear in normal prose.

## Conflict Risks

- No safety, security, authorization, privacy, compliance, destructive-action,
  package-manager, or explicit user-preference instructions were removed.
- No higher-priority instruction conflict was found in the six candidates.

## Future Drift Control

- `tools/no-op-instruction-scan.mjs` reports exact file/line candidates.
- `config/tmcp/no-op-scan-allowlist.json` requires a reason for retained
  candidates.
- `config/tmcp/portable-dev-process/modules/instruction_hygiene.md` defines the
  scoring and evidence rules for future instruction reviews.
