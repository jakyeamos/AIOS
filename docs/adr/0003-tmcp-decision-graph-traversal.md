# ADR 0003: TMCP Decision Graph Traversal

Date: 2026-06-11

## Status

Accepted

Tier-one candidate. TMCP is the default skill-composition architecture for AIOS-managed work, but the managed-run hard-default adoption gate is tracked in Phase 20 Plan 20-07 before it is claimed as fully tier-one.

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

The canonical local graph is `skills-library/skills.tmcp`. Tracked build intent lives in `config/tmcp/canonical-graph.json`; generated metadata lives in `skills.tmcp/graph.json`. Overlay packs such as `config/tmcp/portable-dev-process` are namespaces, not competing default graphs. Runtime traversal may load an overlay only when explicit namespace triggers match the prompt and the overlay contributes behavior not already present in canonical task/module/branch/source-skill nodes.

Runtime packet compilation must prefer structured graph traversal when `skills.tmcp/graph.json` is present. It records candidate scores for task, module, and source-skill nodes, selected source-skill hashes, selected nodes, skipped plausible nodes, overlay trigger evidence, and fallback warnings. If structured graph metadata is missing or invalid, runtime falls back to heuristic traversal and marks the packet warning explicitly.

TMCP is also a skill compiler. Graph nodes must expose behavior atoms, approximate token cost, behavior added, redundancy hints, and omission risk so runtime can build the smallest behavior-changing packet instead of concatenating matching files. The compiler may prune redundant low-risk modules when selected source skills already cover the same behavior atoms, and those negative selections become receipt evidence.

Source skills should be loaded as task-relevant excerpts where possible. Runtime prefers procedure, decision, tool-use, validation, failure-mode, trigger, and constraint sections over whole-file loading. Full source files remain available through provenance paths when a task needs deeper inspection.

Repeated successful traversal paths may be promoted into shortcut nodes. Shortcut promotion must be evidence-driven: the same traversal fingerprint must recur, validation must remain successful, token ROI must be positive often enough to justify reuse, and no unresolved repair or project-specific override may block the path. Once promoted, a shortcut becomes a top-level router node that future branches can build from.

Shortcut skills are cached compiled packets, not source of truth. They must preserve provenance, declare a source graph version, declare source tasks/modules/branches/source skills, store selected source hashes, carry selected behavior atoms and token estimates, and be revalidated when related source material changes. If graph version or source-hash freshness is uncertain, the agent must bypass the shortcut and fall back to router traversal.

TMCP superiority claims require eval evidence. AIOS may call TMCP a default routing architecture before benchmark superiority is proven, but it must not claim better quality, speed, token cost, or repair rate until repeated paired runs show quality non-inferiority plus positive token/runtime ROI.

## Consequences

TMCP traversal becomes a first-class AIOS learning surface. A run can record the path it took, skipped nodes, selected branches, source tiers used, validation evidence, token estimates, and outcome.

This enables later AIOS behavior:

- promote repeated successful traversal paths into shortcuts
- expose promoted shortcuts as top-level graph nodes
- branch from promoted shortcuts when a recurring variant appears
- repair paths that miss project-specific requirements
- demote shortcuts when token ROI or validation quality regresses
- revalidate, regenerate, split, conflict-branch, supersede, or deprecate shortcuts when source graph material changes
- demote nodes with poor instruction precision
- compare custom TMCP packets against broad baseline skill loading

The current implementation is graph-backed with heuristic scoring. It does not yet enforce the managed-run hard default in every non-trivial entrypoint; that adoption contract is planned in Phase 20 Plan 20-07. Semantic graph search can be added later, but the tier-one contract is already explicit about evidence, fallback, overlays, freshness, and benchmark claims.

## Validation

The current generator validates that:

- `skills.tmcp/design-decision.md` exists
- `skills.tmcp/traversal-receipt-schema.md` exists
- `skills.tmcp/evaluation-plan.md` exists
- `skills.tmcp/graph.json` exists or `aios skills graph-verify --repair` can regenerate it from existing generated-library metadata
- `skills.tmcp/shortcuts/candidate.md` exists
- every generated task includes transition edges and custom-skill construction sections
- TMCP references resolve
- runtime graph traversal selects task/module/source-skill nodes, records scores, and falls back with warnings
- stale selected source-skill hashes bypass promoted shortcuts
- overlays are skipped when they add no behavior beyond canonical graph nodes
- behavior atoms, token costs, redundancy hints, omission risk, node usefulness, omitted requirements, and negative selections appear in graph metadata, packets, or receipts
- source-skill loading prefers relevant sections instead of whole-file payloads

Targeted regression coverage lives in `tests/test_skills_harvest.py` and `tests/test_tmcp_runtime.py`.
