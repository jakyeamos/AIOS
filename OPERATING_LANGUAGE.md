# Operating Language

## Purpose

This file defines the canonical language for this project. Use these terms in prompts, specs, issues, code review, tests, docs, and agent workflows.

Terms are grouped into:

- Domain Language
- Architecture Language
- Agent-Control Leading Words
- Relationships
- Flagged Ambiguities
- Rejected Terms
- Migration Notes

## Domain Language

| Term | Definition | Use when | Aliases to avoid | Verification signal |
|---|---|---|---|---|
| **AIOS** | The local-first operating layer for work context, agent workflows, durable project memory, governance, and quality control. | Referring to the product as a whole. | dashboard, standards repo, helper scripts | The work preserves local-first state, agent workflow control, durable memory, and governance. |
| **Agent Operating System** | The product category AIOS is building toward: an execution layer that turns intent into governed, context-rich, verifiable agent work. | Describing the long-term product shape. | productivity app, automation bundle | Specs cover routing, context, execution, evidence, learning, and operator visibility. |
| **Operator** | The human supervising AIOS workflows, approvals, project truth, and inspection surfaces. | Naming the human role. | user, admin, viewer | Human-facing surfaces expose reviewable state and approval choices. |
| **Agent** | The machine executor that consumes packets, skills, standards, prompts, and gates to do work. | Naming the primary AIOS user. | bot, assistant, worker | Instructions optimize for executable context, not only human prose. |
| **Project Truth** | The durable narrative of what is currently shipped, intended, constrained, and known about a project. | Updating or reading `PROJECT.md` and related truth files. | status doc, summary, readme | Meaningful state changes are reflected in the truth file with current facts. |
| **Context Packet** | The smallest sufficient set of selected context, standards, receipts, risks, and acceptance criteria for a task. | Preparing work before execution. | briefing, dump, prompt context | Loaded and skipped context are explicit, scoped, and receipt-backed. |
| **Context Receipt** | The durable record explaining which context was loaded, skipped, missing, stale, or selected by score. | Auditing context selection. | context log, search result | The receipt explains selection reasons and preserves skipped alternatives. |
| **Writeback** | A proposed or approved update to durable truth, standards, prompts, skills, workflow metadata, or memory after learning. | Capturing reusable lessons or state changes. | memory update, note, sync | Promotion is reviewable and records target, reason, severity, and evidence. |
| **Workflow** | A governed multi-stage route for serious work with explicit skills, stages, evidence, and closeout expectations. | Selecting or designing execution paths. | process, flow, recipe | Stage boundaries, selected skills, and required evidence are machine-readable. |
| **Durable Workspace** | A persistent state surface for a recurring or long-running stream of agent work. | Managing release, quality gate, TMCP skill audit, repo adoption, documentation review, monitoring, or similar threads. | chat thread, running notes, transcript | Decisions, blockers, owners, dates, useful links, verification status, known pitfalls, and next actions survive across sessions. |
| **Goal Verifier** | The observable check that proves a goal reached its stopping condition. | Defining or closing a durable goal. | done, complete, looks good | Typecheck, lint, tests, build, validation matrix, repro, benchmark, deployment, artifact audit, or accepted blocker evidence is recorded. |
| **Steering Event** | An immediate correction to current execution direction that preserves the active goal unless explicitly changed. | The agent is actively going the wrong way. | new task, follow-up, queue item | The run log or durable workspace records the correction and the unchanged or explicitly changed goal. |
| **Queued Work** | Work recorded for after the current checkpoint completes. | A new instruction should not interrupt in-flight verification. | steering, interruption, backlog dump | Queued work is visible in durable state and runs only after the checkpoint or verifier reaches its stop condition. |
| **Work Surface** | A declared area an agent is allowed to touch or inspect for a workflow. | Scoping repo, artifact, UI, communication, monitoring, or memory reach. | tool access, context, environment | Allowed and out-of-scope surfaces are named before tool reach expands. |
| **Reviewable Artifact** | A durable source of truth for substantial work when chat is insufficient. | Tracking expected behavior, implementation status, test status, failures, fixes, and verification. | summary, transcript, note | Artifact links expectations, status, evidence, failures, fixes, and final verification. |
| **Quality Gate** | A blocking or warning criterion used to evaluate changed work against correctness, security, simplicity, tests, architecture, or deployment expectations. | Reviewing, committing, closing out, or deploying. | checklist, lint, best practices | Gate result records pass/fail/warn, evidence, and remediation. |
| **Truth File** | A durable source file that records canonical project state or planning state. | Changing shipped reality, project assumptions, or roadmap state. | doc, markdown, notes | The relevant file is updated in the same logical change set. |
| **Learning Candidate** | A possible reusable lesson extracted from a run, review, failure, or repeated friction but not yet promoted. | Evaluating whether behavior should become durable. | insight, memory, suggestion | Candidate has evidence, risk, target surface, and approval status. |

## Architecture Language

| Term | Definition | Use when | Aliases to avoid | Verification signal |
|---|---|---|---|---|
| **Local-First Spine** | AIOS's file and SQLite-backed control plane for private, inspectable, local workflow state. | Designing persistence or integrations. | cloud backend, hosted state | Core state remains in local files, SQLite, logs, and governed artifacts. |
| **Control Plane** | Python CLI, services, hooks, registries, and workflow engines that own AIOS behavior. | Modifying backend workflow behavior. | backend, scripts | Business behavior lives in `bin/`, `services/`, config, and schema surfaces. |
| **Operator Surface** | UI or CLI surfaces that inspect, explain, and trigger control-plane state without owning core business rules. | Building dashboard or CLI views. | frontend, dashboard, console | UI/server code reads projections and delegates mutations to governed control-plane paths. |
| **Skill Registry** | The AIOS metadata surface that makes skill capabilities, source paths, lifecycle state, and workflow applicability inspectable. | Adding or syncing skills. | skill list, plugin list | `config/workflows/skills.json` points to source artifacts and states lifecycle/applicability. |
| **Prompt Library** | The reusable prompt-template and prompt-fragment surface used as supporting evidence for workflow routing and agent packets. | Editing prompt assets. | prompts folder, templates | Prompt IDs, lifecycle state, registry output, and validation remain traceable. |
| **Memory Layer** | The layered raw-source, fact, relationship, and packet-receipt model used to compile model-facing memory. | Designing retrieval or durable memory. | knowledge base, vector memory | Raw sources, facts, relationships, and packet receipts keep separate ownership. |
| **Thin Display** | A UI surface that renders state from server/control-plane seams without owning business decisions. | Reviewing UI architecture. | smart component, fat page | Business rules remain in server/control-plane helpers and are testable outside rendering. |
| **Test Seam** | A boundary where behavior can be tested without UI or infrastructure noise. | Isolating business behavior from external systems. | mock point, hook | Tests exercise behavior through stable services, adapters, or CLI functions. |
| **Approval Gate** | A boundary where mutation, promotion, or risky action waits for explicit human or policy approval. | Designing writebacks, deployment, memory promotion, or destructive actions. | permission prompt, review step | Pending state and approval metadata are visible before promotion. |
| **Evidence Chain** | The linked artifacts proving what ran, what changed, what passed or failed, and what remains unresolved. | Claiming completion or debugging failures. | logs, proof, receipts | Checks, command evidence, verifier artifacts, and closeout records point to each other. |
| **Subsystem Posture** | The current keep, consolidate, package, or extract decision for an AIOS subsystem. | Changing boundaries or adding reusable infrastructure. | module status, architecture note | `.planning/SUBSYSTEM_EXTRACTION_PLAN.md` records evidence and next decision point. |

## Agent-Control Leading Words

| Leading word | Behavioral meaning | Trigger when | Do not use for | Completion criterion |
|---|---|---|---|---|
| **Context Compile** | Select the smallest sufficient authoritative context and preserve a receipt before non-trivial work. | A task touches repo behavior, workflows, standards, prompts, skills, architecture, or multiple files. | trivial read-only answers or single local commands | Receipt exists and loaded/skipped context is explainable. |
| **Truth First** | Verify claims against authoritative sources before accepting or building on them. | The user, code, docs, or prior state may be stale, conflicting, or asserted without evidence. | subjective preferences or explicitly hypothetical brainstorming | Answer or implementation cites checked source state and rejects false premises when needed. |
| **Tracer Bullet** | Build the thinnest real vertical slice through production-shaped boundaries to prove integration risk. | Starting uncertain implementation or validating cross-layer behavior. | throwaway mockups or broad prototypes | One real path works end-to-end through the actual architecture. |
| **Red Gate** | Produce or identify a failing signal before remediation when debugging or test-driven changes require proof. | Fixing bugs, adding behavior tests, or validating claimed regressions. | pure docs edits or impossible-to-execute environments | A failing test, reproduction, or logged failure is recorded before the fix passes. |
| **Thin Display** | Keep UI focused on rendering and interaction while moving business decisions to stable seams. | Building or reviewing operator UI. | purely visual one-off components | State and decisions can be tested outside the component. |
| **Execution-First** | Run the exact code path or closest real path before changing behavior or claiming success. | Side effects, cross-system behavior, core logic, or low-trust tests are involved. | text-only artifacts or design-only planning | Observed runtime evidence informs the change and final verification. |
| **Approval-First** | Treat risky writebacks, promotions, external effects, and destructive operations as review-gated. | A task mutates durable truth, standards, prompts, skills, memory, remotes, deployments, or user data. | local read-only analysis | Pending changes are proposed or explicitly approved before promotion. |
| **Clean Closeout** | Finish with verification evidence, truth/writeback updates, and no hidden dirty state for the scoped change. | Completing implementation, planning, or artifact updates. | exploratory investigation with no completion claim | Checks are run or blockers stated, truth artifacts are updated, and unrelated dirty work is not mixed in. |
| **Complexity Gate** | Evaluate whether the solution is simpler than necessary, duplicates concepts, or creates avoidable sprawl. | Large work, cross-layer changes, new infrastructure, or reusable abstractions. | tiny docs edits or narrow one-file fixes | Gate findings are reported and necessary simplifications are applied or recorded. |
| **Portable Boundary** | Separate AIOS-local behavior from portable/core behavior and label context-dependent wins accordingly. | Building benchmarks, skills, standards, or workflows meant for reuse outside AIOS. | personal-only local scripts | Output states whether evidence is AIOS-local, personalized, or portable. |

## Relationships

- **AIOS** serves both **Agents** and the **Operator**; agents are the primary execution user, while the operator governs and inspects.
- A **Workflow** consumes a **Context Packet**, selects skills from the **Skill Registry**, and produces an **Evidence Chain**.
- A **Durable Workspace** preserves long-running **Workflow** state; its **Goal Verifier** decides whether the active goal reached the stopping condition.
- A **Steering Event** changes current execution direction immediately, while **Queued Work** waits for the current checkpoint.
- A **Reviewable Artifact** is the source of truth for substantial durable work when the chat transcript is insufficient.
- A **Context Packet** must have a **Context Receipt**.
- A **Writeback** may update **Project Truth**, **Truth Files**, **Prompt Library**, **Skill Registry**, standards, or memory, but risky promotion passes through an **Approval Gate**.
- An **Operator Surface** should usually be a **Thin Display** over the **Control Plane** and **Local-First Spine**.
- **Learning Candidates** become durable behavior only after evidence and approval.
- **Clean Closeout** depends on **Execution-First** evidence, relevant **Quality Gates**, and truth-file updates.

## Flagged Ambiguities

- "User" is used for both the human operator and the agent consumer.
  - Recommendation: use **Operator** for the human and **Agent** for the executor unless external product copy requires "user."
  - Update needed in: prompts, UI labels, workflow docs, and issue text where role matters.
- "Context" can mean raw docs, selected packet content, model prompt content, or durable memory.
  - Recommendation: use **Context Packet**, **Context Receipt**, **Memory Layer**, or **Prompt Library** depending on the boundary.
  - Update needed in: context compiler docs, tests, and workflow summaries.
- "Gate" can mean quality evaluation, approval pause, or deployment completion.
  - Recommendation: use **Quality Gate**, **Approval Gate**, or deployment gate explicitly.
  - Update needed in: AGENTS.md-derived prompts, closeout summaries, and gate docs.
- "Skill" can mean a Codex skill folder, workflow skill metadata, or a general capability.
  - Recommendation: use **Skill Registry** for AIOS metadata and "skill file" for `SKILL.md` artifacts.
  - Update needed in: skill sync docs, workflow registry commentary, and prompts.
- "Truth" can mean project narrative, runtime evidence, or memory facts.
  - Recommendation: use **Project Truth**, **Evidence Chain**, or **Memory Layer**.
  - Update needed in: closeout reports and writeback proposals.

## Rejected Terms

| Rejected term | Reason rejected | Use instead |
|---|---|---|
| robust | Too vague; no observable behavior. | Quality Gate, Evidence Chain, tested failure path |
| thoughtful | Does not change agent behavior. | Context Compile, Truth First |
| smart component | Ambiguous and encourages UI-owned logic. | Thin Display |
| memory update | Hides approval and target boundary. | Writeback, Learning Candidate |
| dashboard | Narrows AIOS to UI instead of workflow control. | Operator Surface |
| prompt dump | Encourages broad ungoverned context loading. | Context Packet |
| best effort | Often hides incomplete verification. | explicit blocker, warning, or accepted tradeoff |

## Migration Notes

- Use **Operating Language** in future AIOS prompts when repeated prose would otherwise define project vocabulary, review language, or agent-control behavior.
- Prefer **Context Compile** over repeated bootloader prose when asking agents to prepare non-trivial work.
- Replace generic "context" in new docs with **Context Packet**, **Context Receipt**, **Memory Layer**, or **Prompt Library**.
- Replace "dashboard" with **Operator Surface** in architecture docs when the UI is an inspection or trigger surface.
- Replace "smart component" guidance with **Thin Display** in UI reviews and frontend standards.
- Register vocabulary-changing skills in the **Skill Registry** so routing can discover their source paths and lifecycle state.

## Example Dialogue

Developer: "This UI page needs smarter logic for workflow status."

Reviewer: "Use **Thin Display** here. The **Operator Surface** should render status from the **Control Plane**, not decide lifecycle rules."

Agent: "I will **Context Compile** first because this touches workflow metadata and skill routing. If I add a reusable behavior term, I will update **Operating Language** and propose any needed **Writeback**."

Reviewer: "Also avoid saying 'context' generically. This change updates the **Context Packet** behavior, and the **Context Receipt** should prove what was loaded."

## Quality Bar

- Every term has one canonical meaning.
- Every agent-control term changes behavior.
- Every leading word has a trigger and completion criterion.
- Every rejected synonym has a preferred replacement.
- No generic quality words remain unless made observable.
- The file helps both humans and agents make better decisions.
