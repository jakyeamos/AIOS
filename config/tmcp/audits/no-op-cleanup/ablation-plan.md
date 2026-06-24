# Ablation Plan

Date: 2026-06-24

## Candidate Groups

| Group | Candidates | Proof method | Reason |
|---|---|---|---|
| Vague prompt-library purpose clause | NOC-001 | Static proof plus scanner validation | The clause was not a branch, output field, safety rule, tool call, or validation requirement. Existing adjacent rules define concrete prompt-library behavior. |
| Imported skill metadata | NOC-002, NOC-003 | Static proof | Registry fields preserve imported skill naming/provenance; removing or rewriting would be a metadata change, not no-op cleanup. |
| Quoted rejected-term examples | NOC-004 through NOC-006 | Static proof | The generic words occur inside a rejection rule and are not instructions to execute. |

## Behavioral Ablation

Executable paired model ablation was not run because every candidate was resolved
by static evidence:

- the only changed clause was rewritten to concrete requirements already used by
  prompt-library validation and eval records
- retained candidates were either metadata or anti-examples

Future uncertain removals should run at least three paired cases covering normal,
edge, and failure-path tasks with the same model, tools, context, task, and
configuration.
