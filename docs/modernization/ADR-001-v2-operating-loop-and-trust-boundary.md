# ADR-001: V2 Operating Loop and Trust Boundary

**Status:** Accepted v2 default<br>
**Date:** 2026-07-10<br>
**Scope:** Product operating model and authority boundary; no runtime behavior
changes are made by this decision.

## Decision

AIOS v2 is a **single-user, local-first control plane**. It runs for the local
OS user and binds all control-plane mutation access to the local machine. The
Next UI is a local operator client and read model, not an authenticated remote
application or a remote process-control surface.

The local operator is the only authority that can approve durable promotions,
configuration or policy changes, privileged runs, external egress,
deployments, migrations, linked-repository writes, or destructive actions.
Agents may perform work inside the granted project scope, create bounded run
evidence, and propose changes; they cannot self-approve a privileged effect.

The v2 loop is:

```text
doctor → human intent → route/start scoped work → execute → verify
       → human review when gated → closeout → daily-flow / next-action replay
```

`daily-flow` and `next-action` are durable evidence and follow-up projections.
They are not substitutes for verification, approval, or closeout.

## Authority Model

| Activity | May happen automatically | Requires local human approval |
| --- | --- | --- |
| Read-only routing, status, trace replay, and packet generation | Yes | No |
| Scoped agent work and bounded operational evidence | Yes, after a ready local run exists | No |
| Start, cancel, or resume a local run | Requested through the local control plane | Local operator initiation/capability |
| Durable truth, standards, global/default configuration, workflow, prompt, skill, or vault promotion | Proposal only | Yes |
| LLM or connector egress, external communication, deployment, migration, linked-repo write, or destructive operation | No | Explicit, target-bound confirmation |

V2 must consolidate mutation authority behind one local control-plane owner.
The UI may request and display actions, but it must not remain a competing
SQLite/schema/process owner. Mutations will be POST-only, loopback-only, and
bound to a per-launch local capability plus explicit local confirmation where
the table requires it. Loopback is a containment boundary, not sufficient
authorization by itself.

## Compatibility Contract

- Preserve the local CLI and hook entry points, including their `AIOS_DB` run,
  packet, invocation, session, evidence, and closeout semantics.
- Keep the UI's local read surfaces, but reclassify current direct UI mutation
  routes as internal implementation details rather than public API contracts.
- Unify the UI and Python configuration/path contract before moving state
  ownership; the UI must no longer independently choose a database or execute
  authoritative schema changes.
- Replace broad child-process environment inheritance with a minimal,
  documented allowlist when the local control-plane boundary is implemented.
- Preserve local raw data, prompt, event, artifact, vault, and CTS privacy;
  external egress remains opt-in and must become enforced, redacted, and
  durably audited.

## Explicit Non-Goals

- No hosted or remotely reachable authoritative AIOS control plane in v2.
- No multi-user sharing, identity/RBAC system, tenant model, remote worker
  fleet, bidirectional synchronization, or public connector surface in v2.
- No direct remote access to local SQLite, files, vault content, raw prompts,
  host Git, credentials, or process execution.
- No claim of backup, recovery, or migration readiness before the state and
  migration authority decision resolves the baseline's integrity blockers.

A future remote observer is a separate product decision. It may begin only as
a redacted, derived, read-only projection after a proven user need and a new
identity, authorization, data-classification, recovery, and local-agent
command-broker design.

## Why This Is the Smallest Coherent V2

AIOS currently describes and executes a local operating loop, uses local
SQLite/filesystem/vault state, and its UI is explicitly designed for local
development. The UI currently uses unauthenticated `publicProcedure` routes,
opens the local database, and can invoke a detached host process. Making that
surface remote would expose sensitive operator data and privileged host effects
without the required identity, authorization, worker isolation, remote-state,
secret, recovery, or tenant architecture.

This decision keeps the proven local value while giving tickets 003, 004, and
005 a stable authority boundary. It does not treat the existing state store as
safe or ready: schema divergence, 555 copied-database foreign-key violations,
and the lack of a restore drill remain release blockers for mutation-owner and
migration work.

## Success Signals and Implementation Gates

A v2 terminal run is successful only when it has a durable route/packet/run
linkage, verifier or criteria evidence, no unresolved blocker (or an
evidence-backed accepted tradeoff), a governed closeout with changed artifacts
and checks, and a next action or explicit no-follow-up state.

Before a redesigned mutation surface can be accepted, it must prove that
non-loopback launch and missing/invalid local capabilities fail without
database or process side effects; gated approvals are enforced rather than
merely labeled; privileged actions are attributed to actor, capability, target,
and outcome; and egress is blocked, consented, or redacted as specified.

## Evidence

- [Baseline audit](AUDIT.md) — daily-loop evidence, data-integrity/recovery
  blockers, local-path coupling, and current UI verification limits.
- [README](../../README.md) — local product framing and operator loop.
- [tRPC setup](../../aios-ui/server/trpc.ts) and [route handler](../../aios-ui/app/api/trpc/%5Btrpc%5D/route.ts) — database-only context and public GET/POST
  procedures.
- [UI database access](../../aios-ui/server/db.ts) and
  [managed runtime](../../aios-ui/server/aios/runtime.ts) — direct local
  SQLite access and detached local process invocation.
- [Storage contract](../STORES.md) and [privacy contract](../PRIVACY.md) —
  local/sensitive data and egress expectations.
- TMCP expert-rubric review `tmcp-review-plan-e903d12d` — cited source,
  risk-priority, verification, and scope review. Its packet was process-only,
  so this decision is grounded in the repository evidence above rather than a
  generic TMCP playbook.
