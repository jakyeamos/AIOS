# Semantic Workflow Routing

## Purpose

AIOS workflow routing keeps deterministic scoring as the first pass, then can call a semantic
reasoner when deterministic evidence has no viable unique workflow. This avoids expanding
hard-coded keyword dictionaries for every natural-language phrasing while preserving governed
workflow safety.

## Configuration

Set this environment variable to enable the semantic fallback:

```text
AIOS_WORKFLOW_SEMANTIC_ROUTER_CMD="your-router-command --json"
```

The command receives one JSON object on stdin and must write one JSON object to stdout. It should
not mutate project files or runtime state.

## Request Shape

```json
{
  "objective": "User task objective",
  "available_workflows": [
    {
      "workflow_key": "implementation-delivery",
      "workflow_family": "audit_and_implement",
      "name": "Implementation Delivery",
      "purpose": "Default implementation workflow for scoped code changes.",
      "trigger_hints": ["implement", "build"],
      "applicability": ["audit_and_implement"],
      "lifecycle_state": "active"
    }
  ],
  "deterministic_candidates": [],
  "output_schema": {
    "selected_workflow": "string workflow_key or null",
    "confidence": "number from 0.0 to 1.0",
    "rationale": "short reason grounded in objective and available workflow metadata",
    "alternatives": "optional list of {workflow_key, confidence, rationale}"
  }
}
```

## Response Shape

```json
{
  "selected_workflow": "implementation-delivery",
  "confidence": 0.86,
  "rationale": "The objective asks for a scoped code change to routing behavior.",
  "alternatives": [
    {
      "workflow_key": "divergent-strategy",
      "confidence": 0.42,
      "rationale": "Could be used for design discussion, but the objective asks to implement."
    }
  ]
}
```

## Confidence Gate

- `confidence >= 0.75`: route through the selected workflow.
- `confidence < 0.75`: preserve the semantic recommendation but keep the route blocked.
- Unknown workflow keys are treated as invalid and do not route.
- Command failure, timeout, or non-JSON output is non-fatal; routing falls back to the normal blocked
  result with diagnostic evidence.

## Inspection

Route payloads include `semantic_recommendation` when the fallback runs. Semantic-selected workflows
also include:

- `routing_source: semantic_reasoner`
- `semantic_confidence`
- semantic rationale
