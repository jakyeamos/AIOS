# ADR 0003: TMCP Decision Graph Traversal

Date: 2026-06-11

## Status

Accepted

## Context

AIOS now generates a local skills library and `skills.tmcp/` layer from project, personal-agent, local-agent-config, plugin-reference, history-reference, and general reference sources.

The initial TMCP shape used task-first markdown files with IF/ELSE routing. That made routing inspectable, but it risked treating TMCP as a rigid decision tree. The intended product behavior is richer: an agent should be able to explore thin task, module, branch, provenance, and output nodes, then assemble a task-specific custom skill packet.

Two risks need explicit design treatment:

- raw concatenation of thin nodes may produce incoherent instructions unless transition edges explain why one node follows another
- graph traversal may cost more tokens and latency than loading an existing broad skill unless quality or precision improves enough to justify it

## Decision

TMCP is a thin, agent-explorable markdown decision graph, not a rigid IF/ELSE script and not a single flattened skill.

Generated TMCP nodes must support:

- `LOAD`: select an entry task or required node
- `CONSIDER`: inspect adjacent task/module/branch nodes that may add task-specific value
- `USE`: include a behavior-changing node in the custom skill packet
- `SKIP`: reject a plausible node with a reason
- `EXIT`: stop traversal after the smallest sufficient custom skill packet is assembled
- `WHY`: record the reason for node and branch choices
- `EVIDENCE`: cite source/provenance or runtime validation
- `OUTCOME`: record execution result and repair recommendations

Generated task files must include transition edges and custom-skill construction rules. Generated modules and branches must include transition hooks. Generated TMCP must include a traversal receipt schema and evaluation plan.

## Consequences

TMCP traversal becomes a first-class AIOS learning surface. A run can record the path it took, skipped nodes, selected branches, source tiers used, validation evidence, token estimates, and outcome.

This enables later AIOS behavior:

- promote repeated successful traversal paths into shortcuts
- repair paths that miss project-specific requirements
- demote nodes with poor instruction precision
- compare custom TMCP packets against broad baseline skill loading

The current implementation remains heuristic. It does not yet execute semantic graph search or persist traversal receipts into SQLite. The generated markdown defines the contract that future runtime work should implement.

## Validation

The current generator validates that:

- `skills.tmcp/design-decision.md` exists
- `skills.tmcp/traversal-receipt-schema.md` exists
- `skills.tmcp/evaluation-plan.md` exists
- every generated task includes transition edges and custom-skill construction sections
- TMCP references resolve

Targeted regression coverage lives in `tests/test_skills_harvest.py`.
