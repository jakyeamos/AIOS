# Candidate Ledger

Date: 2026-06-24

Scoring model:

- behavioral specificity: `0` no behavior, `1` general intent, `2` explicit
  behavior or output, `3` executable/testable rule
- redundancy: `0` unique, `1` partial overlap, `2` effective duplicate, `3`
  inherited or repeated verbatim
- removal risk: `0` no plausible consequence, `1` presentation/quality, `2`
  workflow/correctness, `3` safety/security/compliance/authorization

| ID | File:line | Exact clause | Intended behavior | Equivalent/canonical source | Specificity | Redundancy | Risk | Evidence | Proposed disposition | Final disposition |
|---|---|---|---|---|---:|---:|---:|---|---|---|
| NOC-001 | `prompts/README.md:10` | `Capture repeatable high-quality prompting patterns.` | Explain prompt-library purpose. | Adjacent sections already require frontmatter, output contracts, eval cases, validation, versioning, and changelog updates. | 1 | 2 | 1 | Static review: "high-quality" adds no measurable requirement beyond existing concrete prompt-library contracts. | Rewrite | Rewritten to require frontmatter, output contracts, eval cases, and validation commands. |
| NOC-002 | `config/workflows/skills.json:728` | `"purpose": "Best practices for Remotion - Video creation in React",` | Preserve imported skill title. | Source/provenance value from imported Remotion skill metadata. | 2 | 0 | 2 | Static review: field is registry metadata, not an instruction clause; changing it would alter provenance. | Retain | Retained and allowlisted. |
| NOC-003 | `config/workflows/skills.json:742` | `"purpose_long": "Best practices for Remotion - Video creation in React"` | Preserve imported skill title. | Source/provenance value from imported Remotion skill metadata. | 2 | 0 | 2 | Static review: field is registry metadata, not an instruction clause; changing it would alter provenance. | Retain | Retained and allowlisted. |
| NOC-004 | `skills/operating-language/SKILL.md:57` | `Reject weak terms that sound good but do not alter behavior. Do not keep terms like "be careful," "high quality," "thoughtful," or "robust" unless the project gives them concrete behavioral meaning.` | Teach agents to reject behaviorally inert leading words. | `instruction_hygiene` module now mirrors this rule for broader prompt/skill cleanup. | 3 | 1 | 1 | Static review: terms appear as quoted anti-examples inside an executable rejection rule. | Retain | Retained and allowlisted. |
| NOC-005 | `skills/operating-language/SKILL.md:57` | Same line, `high quality` match. | Same as NOC-004. | Same as NOC-004. | 3 | 1 | 1 | Static review: quoted anti-example, not a directive. | Retain | Retained and allowlisted. |
| NOC-006 | `skills/operating-language/SKILL.md:57` | Same line, `robust` match. | Same as NOC-004. | Same as NOC-004. | 3 | 1 | 1 | Static review: quoted anti-example, not a directive. | Retain | Retained and allowlisted. |

## Scanner State

`pnpm tmcp:no-op-scan` now reports zero unallowlisted candidates.
