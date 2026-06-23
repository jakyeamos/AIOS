# Meta-Learning Routing Policy

Routing decides where an accepted scored signal should be reviewed. It must prefer the narrowest layer that preserves the user's intent.

## Target Layers

- `global`: broad rules that affect every project. Use only with multi-project evidence and manual review.
- `project`: project-specific rules or context packets. Signals containing `in this repo` route here by default.
- `skill`: skill instructions when the signal is about a skill trigger, process, or output.
- `command`: repeated command behavior or command policy suggestions.
- `agent`: model-routing or sub-agent behavior.
- `second_brain`: personal memory notes when the evidence cites second-brain context.
- `eval`: regression fixtures or shadow eval tasks for repeated context/tool/model failures.
- `observe_only`: low-quality, rejected, conflicting, or insufficiently targeted signals.

## Safeguards

Project-specific evidence is routed away from global rules unless multi-project evidence justifies broader review. Global, skill, and agent routes require manual review because they have higher blast radius.

Contradictions do not route directly into rule files. They become review records that ask the user to replace, narrow, split by context, or decide manually.

## TMCP Placement

Routing policy is intent-specific. Always-loaded agent files should point to this document only when meta-learning proposal work is active.
