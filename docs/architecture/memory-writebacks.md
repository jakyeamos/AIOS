# Memory Writebacks

AIOS memory writebacks are durable proposals for changing project, workflow, prompt, skill, standards, or personal memory.

The Divergent Strategy Workflow uses `memory_writeback_proposals` for typed proposals:

- `HOW`: reusable process preference or workflow knowledge.
- `WHAT`: project-specific fact, decision, or constraint.
- `FAILURE`: useful dead end, weak assumption, or non-viable candidate.
- `ENTROPY`: convergence risk or repeated pattern observation.

Writebacks must not silently mutate global memory. They need proposed content, rationale, evidence, status, and reviewer metadata. Approved writebacks are still evidence records; prompt or skill promotion requires the separate promotion lifecycle.

The older `improvement_writebacks` table remains available for control-plane learning. Divergent writebacks are separate because they need explicit memory categories and failure/entropy preservation.
