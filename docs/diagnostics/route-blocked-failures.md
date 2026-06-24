# Route-Blocked Failure Diagnostics

## Purpose

`route-blocked` means AIOS could not select a governed workflow safely enough for an objective.
For explicit governed `/aios` work, this remains a blocker. For automatic Codex shadow lanes, the
baseline task should continue and the failure should be retained as routing evidence.

Automatic shadow route failure is not the same as shadow setup failure. If the helper exits `0` and
prints `ok: true`, `governed_route: false`, `aios_route.status: "route_failed"`, and
`aios_route.blocking: false`, no user approval is required to continue baseline work. Approval is
only required when automatic shadow setup exits nonzero or cannot record diagnostic evidence, such
as project resolution failure, helper failure, or shadow worktree creation failure.

## Runtime Record

Automatic shadow routing failures are appended to:

```text
data/aios-route-failures.jsonl
```

Each line is a JSON object with:

- `recorded_at`: UTC timestamp for the failure record.
- `mode`: `automatic-shadow` or `governed-route`.
- `blocking`: whether the failure should stop baseline work.
- `objective`: the original task objective.
- `project`: resolved AIOS project id, name, and repo path.
- `returncode`: process return code from the route attempt.
- `code`: route error code, usually `route-blocked`.
- `message`: route error message.
- `payload`: original JSON payload returned by the route command.

The helper payload also includes `baseline.approval_required` and
`baseline.can_continue_without_shadow` so agents can enforce this policy without interpreting prose.

## Initial Triage

Use these questions when reviewing failures:

- Did project inference select the expected project?
- Did the objective name a task family already covered by `config/workflows/registry.json`?
- Did workflow scoring return weak candidates or no candidates?
- Was the objective too vague for governed execution but still fine for ordinary Codex work?
- Is this a repeated gap that should become a workflow, prompt route, or context packet?

## Failure Classes

- `project-resolution`: cwd, explicit project, or active project registry did not identify a safe project.
- `workflow-coverage`: no governed workflow matches a legitimate repeated task type.
- `objective-ambiguity`: the prompt is underspecified for governed workflow selection.
- `registry-drift`: a workflow exists conceptually but registry terms, prompts, or route primitives are stale.
- `maturity-gate`: a workflow candidate was selected but blocked by eligibility or readiness checks.

## Review Loop

1. Group records by `message` and similar objective wording.
2. Compare repeated objectives with workflow registry coverage.
3. Promote recurring legitimate gaps into a workflow, prompt route, or documented non-governed exemption.
4. Keep one-off vague prompts as evidence, but do not add broad catch-all workflows to silence noise.
5. When a route class is fixed, cite the JSONL examples in the implementation or truth-file update.
