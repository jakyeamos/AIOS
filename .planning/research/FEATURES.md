# AIOS Feature Research

Date: 2026-05-13

## Framing

AIOS is not just another agent runner. For this project, the useful feature set is the one that makes AIOS the default local operating layer for serious work: selecting the right context, routing to the right workflow, executing with durable state, scoring deltas against standards, and writing back improvements under governance. Features below are therefore judged by whether they strengthen that end-to-end loop.

## Table Stakes

| Feature | Why it is table stakes for AIOS | Complexity | Key dependencies | AIOS-specific notes |
|---|---|---:|---|---|
| Local-first runtime and storage | The system loses its identity if core state depends on a hosted control plane. | Medium | local filesystem, SQLite, operator CLI/UI, durable logs | Must treat local files, receipts, evaluations, and writebacks as first-class runtime assets. |
| Deterministic context compilation | Agents need the right project, packets, standards, and receipts without manual assembly. | High | context compiler, feature packets, standards registry, receipt format | AIOS already has the foundation; the product needs reliable project/task classification and explainable inclusion or skip reasons. |
| Workflow routing and agent handoff | A personal agent OS must decide what workflow to run, not just expose tools. | High | workflow registry, routing rules, skill mapping, invocation state | Routing should pick the smallest sufficient workflow and surface why that route beat nearby alternatives. |
| Durable run and invocation state | Multi-step work needs resumability, auditability, and post-run learning. | Medium | run model, invocation events, lifecycle audit, timestamps | Every meaningful execution should have inspectable state transitions and enough evidence for later evaluation. |
| Truth files and project memory | Without maintained truth, every session starts from partial amnesia. | High | project docs, writeback proposals, governance rules, diffing | Truth files should capture goals, architecture, risks, decisions, and next actions with freshness signals. |
| Standards and success-criteria evaluation | Raw completion is not enough; AIOS needs a way to score quality and drift. | High | standards registry, criteria evaluator, evidence capture, findings store | Delta scoring should be concrete, domain-aware, and tied to remediation, not just pass/fail labels. |
| Governed writeback pipeline | Learning must be reviewable or the system will silently corrupt its own memory. | High | writeback proposal model, approval flow, artifact store, provenance | Writebacks should cover truth files, standards, prompts, skills, workflows, and reusable context packets. |
| Explainable evidence trails | Operators and agents need to inspect why AIOS chose context, routing, and evaluations. | Medium | receipts, logs, event model, UI drill-down surfaces | Every major recommendation should point to source artifacts, not hidden heuristics. |
| Searchable operator knowledge surfaces | Users need to ask what changed, what is blocked, and what should run next. | Medium | indexed artifacts, query layer, UI views, grounding logic | This is the readable layer over runs, truth, criteria, and deltas. |
| Execution-first verification | For side-effecting or ambiguous tasks, AIOS must run the actual path, not only reason statically. | Medium | runner integration, test harnesses, command execution, observation capture | This should be a routing rule and evaluation requirement, not an optional habit. |
| Approval-aware automation | A personal OS must know when to stop for review versus proceed autonomously. | Medium | policy rules, approval checkpoints, workflow metadata | Especially important for destructive actions, truth edits, standards updates, and self-modification. |
| Failure recovery and resume | Real work spans interruptions, flaky tools, and partially completed runs. | Medium | checkpointing, durable state, retry semantics, run resumption UX | Resume should preserve context packet, current deltas, pending approvals, and next recommended action. |

## Differentiators

| Feature | Why it differentiates AIOS | Complexity | Key dependencies | AIOS-specific notes |
|---|---|---:|---|---|
| Context compiler as product core | Most agent tools treat context as prompts; AIOS can treat it as compiled, inspectable infrastructure. | High | context packets, receipts, standards selection, task classification | The compiler should become the default entrypoint for all non-trivial work. |
| Delta-from-expectation scoring | Most systems report events; few explain how reality diverges from expected quality. | High | criteria registry, architecture/testing/security/UX heuristics, evidence weighting | This can unify standards compliance, launch readiness, maintainability, and agent-readiness into one inspectable model. |
| Governed self-improvement loop | Many agent systems learn implicitly; AIOS can learn through reviewable writeback proposals with provenance. | High | writeback engine, proposal review, evaluation evidence, versioned assets | Strong candidate for AIOS's signature capability if it remains conservative and evidence-backed. |
| Truth maintenance as ongoing operations | Keeping project truth current is tedious and usually manual; AIOS can operationalize it. | High | project docs, drift detection, artifact linking, freshness scoring | Truth should be updated after meaningful commits, runs, and evaluation changes, not just planning sessions. |
| Workflow selection over tool selection | Most assistants stop at tool choice; AIOS can choose full workflows with gates and outputs. | High | workflow library, routing logic, success criteria, handoff templates | The unit of reuse should be a governed workflow, not a bag of prompts. |
| Cross-run memory that improves future routing | AIOS can learn which packets, standards, and workflows produce good outcomes in which contexts. | High | run history, evaluation outcomes, retrieval, policy rules | Memory should influence future recommendations while remaining reversible and inspectable. |
| Standards-aware project operating layer | AIOS can combine project standards, domain standards, and task-specific expectations before execution begins. | Medium | standards hierarchy, packet assembly, validation, scorecards | This is stronger than generic "best practices" because it is scoped and explicit. |
| Multi-surface governance | Prompts, skills, workflows, truth docs, and criteria can all be managed as lifecycle assets. | High | asset registry, versioning, proposal system, approvals | This broad governance model is rare and directly aligned with AIOS's operating-system ambition. |
| Brownfield codebase orientation | AIOS can become unusually effective in existing repos by preserving maps, receipts, deltas, and historical decisions. | Medium | codebase maps, truth files, context compiler, search | Strong fit for the project's own development loop and likely for future open-source users. |
| Operator-visible compounding | The system should show how each run improved reusable assets, not just that a task finished. | Medium | evaluation store, writeback links, UI summaries, provenance | This makes self-improvement inspectable rather than mystical. |

## Anti-Features

| Anti-feature | Why AIOS should avoid it | Risk if added | Preferred alternative |
|---|---|---|---|
| Opaque autonomous memory mutation | Silent learning degrades trust and makes regressions hard to unwind. | Corrupted truth, prompt drift, governance loss | Require governed writeback proposals with evidence and approval semantics. |
| Generic chat-first UX as the primary model | Chat alone hides routing, context selection, and evaluation state. | AIOS becomes another shell around a model | Make compiled context, workflow choice, run state, and deltas the primary surfaces. |
| Hosted-first architecture | It weakens local control, privacy posture, and product identity. | Vendor dependency, reduced inspectability, operational fragility | Keep local-first as the default and make remote integrations optional. |
| Unbounded semantic retrieval | Pulling in everything "related" destroys determinism and packet quality. | Noisy context, slower runs, inconsistent outputs | Use authoritative context selection with receipts and explicit skip reasons. |
| Tool sprawl without workflow governance | More tools do not equal better execution if routing and criteria remain weak. | Operational entropy, unreliable outcomes | Expand governed workflows and routing rules before expanding tool count. |
| Automatic truth-file overwrites | Project truth should not drift because a model was overconfident. | Loss of source credibility, hard-to-detect errors | Draft writebacks, compare against current truth, require review for meaningful changes. |
| Score inflation without evidence | Weak scoring turns standards into vibes. | False confidence, poor prioritization | Tie every score and delta to artifacts, observations, or exact rule hits. |
| Premature full autonomy on destructive paths | Local agent systems can do real damage quickly. | File loss, broken repos, unsafe self-modification | Use approval-aware workflows and explicit destructive-action policies. |
| UI-heavy polish before control-plane reliability | A polished dashboard does not compensate for weak routing or stale truth. | Misallocated effort, shallow adoption | Prioritize execution reliability, evaluation quality, and writeback correctness. |
| Self-improvement that edits everything equally | Not all assets deserve the same mutation frequency or autonomy. | Constant churn, degraded maintainability | Apply stricter governance to standards, prompts, truth files, and workflows than to ephemeral notes. |

## Prioritization Heuristic For AIOS

Features are worth building first when they do at least one of these:

1. Reduce manual assembly in the vague-goal to execution path.
2. Increase determinism or explainability of context, routing, or scoring.
3. Improve truth freshness without weakening governance.
4. Turn run evidence into reusable improvements for future runs.
5. Raise operator trust by making AIOS easier to inspect, resume, and correct.

## Suggested Ordering

1. Strengthen task classification, context compilation, and workflow routing.
2. Improve truth freshness, governed writeback, and evaluation evidence capture.
3. Expand standards and delta scoring across architecture, testing, security, UX, observability, and agent-readiness.
4. Close the self-improvement loop so routing, packets, and workflows learn from reviewed outcomes.
5. Deepen operator UX only after the underlying governance and evidence model is reliable.
