# Groundwork + Skillification System Design

**Date:** 2026-05-09
**Status:** Approved — ready for phase planning
**Approach:** D — Packets-first core, UI as control plane, service-ready architecture

---

## Problem Statement

AIOS has no mechanism to help agents decide when preflight research is warranted, find relevant prior art and skills before implementation work begins, or detect when repeated behaviors across sessions should become deterministic skills. These gaps cause repeated research overhead, missed reuse opportunities, and no durable record of what was studied before a decision was made.

---

## Architecture Overview

```
AIOS / Claude / Codex prompt
→ lightweight classifier (in skill prompt)
→ /groundwork or /skillify-patterns
→ durable packets / candidates / proposals (aios.db)
→ approval queue
→ skill registry / workflow registry
→ UI control plane (review, approve, govern)
→ optional separate research service (Phase 7, conditional)
```

**Core principle:** Packets and registry artifacts are the system of record. The UI is the review and control layer. A separate service is a future scaling boundary, not the starting point.

---

## Guiding Decisions

1. **Packets first.** The skill must produce durable artifacts before any UI exists. AIOS must work from Claude Code, Codex, CLI, cron, or the web app — the UI is never required.
2. **UI as control plane.** The UI answers: why did groundwork run, what did it find, what is AIOS asking me to approve, what will happen if I approve it.
3. **Service-ready, not service-now.** Python `Protocol` interfaces decouple the research engine from its host. Extract to `services/groundwork/` only when latency, background jobs, or scale demand it.
4. **Extend what exists.** `workflow_synthesis_proposals`, `patterns`, `orchestration_runs.packet_id`, and the JSON workflow/skill registries are all extended — not replaced.
5. **Fail closed.** If approval routing is uncertain, require approval. No silent global behavior changes.

---

## Data Layer

### New DB Tables

#### `groundwork_packets`
One row per `/groundwork` invocation.

```sql
CREATE TABLE groundwork_packets (
  id                    TEXT PRIMARY KEY,
  session_id            TEXT REFERENCES sessions(id),
  run_id                TEXT REFERENCES orchestration_runs(id),
  source_prompt         TEXT NOT NULL,
  project_id            TEXT REFERENCES projects(id),
  invocation_decision_json TEXT NOT NULL DEFAULT '{}',
  classification_json   TEXT NOT NULL DEFAULT '{}',
  prior_art_json        TEXT NOT NULL DEFAULT '{}',
  relevant_skills_json  TEXT NOT NULL DEFAULT '[]',
  missing_skill_opportunities_json TEXT NOT NULL DEFAULT '[]',
  recommendation_json   TEXT NOT NULL DEFAULT '{}',
  approval_routing_json TEXT NOT NULL DEFAULT '{}',
  writebacks_json       TEXT NOT NULL DEFAULT '{}',
  status                TEXT NOT NULL DEFAULT 'draft',
  created_at            TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX idx_groundwork_packets_session ON groundwork_packets(session_id, created_at DESC);
CREATE INDEX idx_groundwork_packets_project ON groundwork_packets(project_id, created_at DESC);
CREATE INDEX idx_groundwork_packets_status ON groundwork_packets(status, created_at DESC);
```

#### `skillification_candidates`
One row per detected repeated pattern.

```sql
CREATE TABLE skillification_candidates (
  id                          TEXT PRIMARY KEY,
  proposed_skill_name         TEXT NOT NULL,
  pattern_summary             TEXT NOT NULL,
  evidence_json               TEXT NOT NULL DEFAULT '[]',
  frequency_score             REAL NOT NULL DEFAULT 0,
  impact_score                REAL NOT NULL DEFAULT 0,
  repeatability_score         REAL NOT NULL DEFAULT 0,
  risk_score                  REAL NOT NULL DEFAULT 0,
  suggested_trigger_conditions_json TEXT NOT NULL DEFAULT '[]',
  suggested_inputs_json       TEXT NOT NULL DEFAULT '[]',
  suggested_outputs_json      TEXT NOT NULL DEFAULT '[]',
  suggested_workflow_placement TEXT,
  expected_token_savings      TEXT,
  expected_quality_improvement TEXT,
  approval_chain_json         TEXT NOT NULL DEFAULT '[]',
  status                      TEXT NOT NULL DEFAULT 'candidate',
  source_session_ids_json     TEXT NOT NULL DEFAULT '[]',
  project_id                  TEXT REFERENCES projects(id),
  detected_at                 TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  updated_at                  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX idx_skillification_candidates_status ON skillification_candidates(status, detected_at DESC);
CREATE INDEX idx_skillification_candidates_project ON skillification_candidates(project_id, detected_at DESC);
```

#### `skill_registry_entries`
Canonical skill lifecycle tracking.

```sql
CREATE TABLE skill_registry_entries (
  id                              TEXT PRIMARY KEY,
  name                            TEXT NOT NULL UNIQUE,
  description                     TEXT NOT NULL,
  status                          TEXT NOT NULL DEFAULT 'draft',
  trigger_conditions_json         TEXT NOT NULL DEFAULT '[]',
  inputs_json                     TEXT NOT NULL DEFAULT '[]',
  outputs_json                    TEXT NOT NULL DEFAULT '[]',
  owner                           TEXT,
  approval_chain_json             TEXT NOT NULL DEFAULT '[]',
  workflow_placements_json        TEXT NOT NULL DEFAULT '[]',
  version                         TEXT NOT NULL DEFAULT '0.1.0',
  source_groundwork_packet_ids_json    TEXT NOT NULL DEFAULT '[]',
  source_skillification_candidate_ids_json TEXT NOT NULL DEFAULT '[]',
  created_at                      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  updated_at                      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX idx_skill_registry_status ON skill_registry_entries(status, updated_at DESC);
```

Status lifecycle: `draft → candidate → approved → active → deprecated`

Rules:
- New skills enter as `candidate`.
- `candidate → approved` requires an approval event.
- `approved → active` requires explicit activation (separate action from approval).
- Deprecated skills remain visible for traceability.
- No silent activation.

#### `approval_events`
Append-only audit log.

```sql
CREATE TABLE approval_events (
  id           TEXT PRIMARY KEY,
  entity_kind  TEXT NOT NULL,  -- groundwork_packet | skillification_candidate | skill_registry_entry | workflow_proposal
  entity_id    TEXT NOT NULL,
  action       TEXT NOT NULL,  -- approve | reject | request_changes | activate | deprecate
  actor        TEXT,
  rationale    TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX idx_approval_events_entity ON approval_events(entity_kind, entity_id, created_at DESC);
```

#### `writeback_events`
Append-only writeback audit.

```sql
CREATE TABLE writeback_events (
  id           TEXT PRIMARY KEY,
  source_kind  TEXT NOT NULL,  -- groundwork_packet | skillification_candidate
  source_id    TEXT NOT NULL,
  target       TEXT NOT NULL,  -- knowledge_base | task_log | project_truth_file | skill_registry | workflow_registry | approval_queue
  status       TEXT NOT NULL,  -- success | skipped | failed
  notes        TEXT,
  created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX idx_writeback_events_source ON writeback_events(source_kind, source_id, created_at DESC);
```

### Extensions to Existing Tables

**`workflow_synthesis_proposals`** — add `kind` column:
```sql
ALTER TABLE workflow_synthesis_proposals ADD COLUMN kind TEXT NOT NULL DEFAULT 'pattern';
-- kind: pattern | groundwork_skill | skillification | manual
```

**`orchestration_runs.packet_id`** — already exists; now wired to `groundwork_packets.id`.

---

## Skill Architecture

### `/groundwork` — Claude Code skill + AIOS workflow skill entry

**Classifier logic** (runs inside the skill prompt, evaluated by Claude):

Invoke `/groundwork` when one or more scores exceed threshold:

| Signal | Threshold |
|---|---|
| novelty_score | ≥ 0.6 |
| complexity_score | ≥ 0.7 |
| risk_score | ≥ 0.5 |
| repeatability_score | ≥ 0.7 |
| expected_value_score | ≥ 0.65 |

Skip for: trivial edits, copy changes, direct answers, formatting, tasks already covered by an existing deterministic workflow.

**Research sequence** (internal-first):
1. Project truth file
2. AIOS `patterns` table
3. Session/prompt logs
4. `skill_registry_entries`
5. `config/workflows/registry.json`
6. External adapters (Phase 5): GitHub, official docs, prior implementations

**Output:** Groundwork Packet (JSON + markdown render), written to `groundwork_packets` via `bin/groundwork-write.py`.

**Guardrails:**
- Max 3 existing skill recommendations
- Max 5 external repo/example recommendations
- All claims require internal references or URLs
- Abandoned repos labeled as risky prior art only
- No skill activation — candidates only

**Workflow registry entry** (`config/workflows/skills.json`):
```json
{
  "key": "groundwork_preflight",
  "purpose": "Preflight research packet for novel, risky, or implementation-heavy tasks.",
  "allowed_stages": ["enrich_context"],
  "input_schema": { "objective": "string", "project_id": "string|null" },
  "output_schema": { "packet_id": "string", "recommendation": "string", "relevant_skills": "string[]" },
  "invariants": ["Never activate skills. Produce candidates only.", "Max 3 skill recommendations.", "Max 5 external repo recommendations."],
  "execution_mode": "deterministic"
}
```

### `/skillify-patterns` — Claude Code skill + AIOS workflow skill entry

**Inputs** (via `PatternSourceAdapter` interface):
- `patterns` table (notice/observation/hypothesis/rule states)
- `sessions` + `prompts_used` (repeated prompt structures)
- `tool_events` (repeated failure patterns)
- `bug_log` (recurring root causes)

**Detection threshold:** A pattern qualifies as a candidate when it appears across ≥ 3 sessions with frequency_score ≥ 0.5 and repeatability_score ≥ 0.6. One-off events never produce candidates.

**Output:** `skillification_candidates` rows written via `bin/skillify-write.py`.

### Python Interface Contracts

`bin/interfaces.py` (new) — Python `Protocol` classes, no inheritance:

```python
class ResearchProvider(Protocol): ...      # search internal/external sources
class PatternSourceAdapter(Protocol): ...  # load recent events from a source
class ApprovalRouter(Protocol): ...        # determine approval chain for an entity
class WritebackTarget(Protocol): ...       # execute a writeback
class PacketRenderer(Protocol): ...        # render packet to markdown
```

First implementations: internal-only (DB reads, file reads). GitHub/docs adapters are stubs in Phase 5.

---

## Approval Routing

| Approval type | Trigger condition |
|---|---|
| None (advisory) | Packet is read-only, no skill proposed, no workflow change |
| Operator | New skill candidate, workflow change, recurring automation, global AIOS behavior change |
| Architecture | Project structure change, new package, agent orchestration change, new cross-project primitive |
| Security | Auth, secrets, browser automation, scraping, tokens, permissions, cloud infra |
| Legal/data | Third-party scraping, ToS risk, personal corpus, user data, privacy logs, retention policy |
| Product | User-facing behavior change, UX default change, onboarding change |

If routing is uncertain: require operator approval. Fail closed.

---

## Writeback Behavior

| Target | What gets written | Condition |
|---|---|---|
| `task_log` (`artifacts`) | Full packet reference | Always |
| Knowledge base (Obsidian) | Durable research summary | When project-relevant and novel |
| Project truth file | Durable project-specific conclusions only | When project-specific and operator approves |
| `skill_registry_entries` | Candidate entry only | When missing_skill_opportunity proposed |
| `workflow_synthesis_proposals` | Proposal stub (kind=groundwork_skill) | When skill approved for workflow placement |
| `approval_queue` (approval_events) | Approval request | When approval_routing.requiresApproval is true |

Every writeback row references `source_kind` + `source_id`. No orphaned writebacks.

---

## UI / Control Plane

### New Routes

| Route | Phase | Content |
|---|---|---|
| `/groundwork` | 3 | List of packets: source prompt, classification, recommendation, status |
| `/groundwork/[id]` | 3 | Detail: classifier scores, prior art, skill recommendations, writebacks, approval routing |
| `/skills` | 3 | Skill Registry: name, status, workflow placements, source links |
| `/skills/[key]` | 3 | Skill detail: lifecycle history, approval events, workflow placements |
| `/candidates` | 3 | Skillification Candidates: proposed name, scores, evidence count, status |
| `/candidates/[id]` | 3 | Candidate detail: evidence excerpts, trigger conditions, approval chain |

Approval actions (Phase 4) live inline on detail pages — no separate approval UI.

### New tRPC Routers

- `groundworkRouter` — `list`, `get` (Phase 3); packet data read from `groundwork_packets`
- `skillRegistryRouter` — `list`, `get`, `updateStatus` (Phase 3/4)
- `skillCandidatesRouter` — `list`, `get` (Phase 3); wraps `skillification_candidates`
- `approvalRouter` — `create`, `list` (Phase 4); writes `approval_events`

`workflowsRouter` gets a `kind` filter on `proposals` to separate groundwork-sourced from pattern-sourced proposals.

**UI rule:** Every status badge links to a detail view with a definition. No orphaned "unknown %" or "active" labels without drill-down.

---

## Phase Breakdown

### Phase 1 — Durable Core
**Goal:** The system can persist artifacts before any UI or skill exists.

Deliverables:
- `schema.sql` additions: 5 new tables + `workflow_synthesis_proposals.kind` column
- `bin/interfaces.py`: Python Protocol contracts
- `bin/groundwork-write.py`: persists `groundwork_packets` row + `writeback_events`
- `bin/skillify-write.py`: persists `skillification_candidates` row + `writeback_events`
- `bin/skill-registry.py`: CRUD for `skill_registry_entries`
- Markdown renderers for Groundwork Packet and Skillification Candidate
- Tests: schema migration, writeback audit trail, candidate/packet persistence

### Phase 2 — Claude Code + Workflow Skills
**Goal:** Skills are operational from Claude Code, Codex, and managed runs.

Deliverables:
- `/groundwork` skill file (classifier logic, research sequence, packet assembly, writeback call)
- `/skillify-patterns` skill file (pattern source reads, candidate assembly, writeback call)
- `config/workflows/skills.json` entries: `groundwork_preflight`, `skillify_patterns`
- `config/workflows/registry.json` stage references
- Tests: classifier threshold logic, max-3-skills guardrail, max-5-repos guardrail, approval routing rules

### Phase 3 — Read-Only UI
**Goal:** Packets, candidates, and registry are inspectable in the UI.

Deliverables:
- `aios-ui/app/groundwork/page.tsx` + `[id]/page.tsx`
- `aios-ui/app/skills/page.tsx` + `[key]/page.tsx`
- `aios-ui/app/candidates/page.tsx` + `[id]/page.tsx`
- `groundworkRouter`, `skillRegistryRouter`, `skillCandidatesRouter` tRPC routers
- `workflowsRouter` kind filter
- Tests: routes render, status badges have definitions, tRPC queries return correct shape

### Phase 4 — Approval / Control UI
**Goal:** Operators can approve, reject, activate, and deprecate skills from the UI.

Deliverables:
- Inline approve/reject/request-changes on `/groundwork/[id]`, `/skills/[key]`, `/candidates/[id]`
- `approvalRouter` tRPC mutations
- Status transition enforcement (candidate → approved → active)
- `approval_events` audit writes
- Tests: status transitions, approval events created, activation guard (no direct candidate→active)

### Phase 5 — External Research Adapters
**Goal:** `/groundwork` can query GitHub, official docs, and internal files via `ResearchProvider`.

Deliverables:
- `bin/adapters/github.py`: repo search, scoring (confidence, license, last updated)
- `bin/adapters/docs.py`: official docs lookup
- `bin/adapters/internal.py`: project file and truth file search
- Adapter plugged into groundwork skill via `ResearchProvider` interface
- Caching layer: results cached by problem_type + domain + project_id
- Tests: adapter contracts, confidence scoring, abandoned-repo labeling, cache hit behavior

### Phase 6 — Pattern Mining + Scheduled Scans
**Goal:** `/skillify-patterns` becomes more powerful and can run automatically.

Deliverables:
- `bin/adapters/session-source.py`: `PatternSourceAdapter` over `sessions` + `prompts_used`
- `bin/adapters/bug-source.py`: over `bug_log`
- `bin/adapters/tool-event-source.py`: over `tool_events`
- `bin/skillify-scan.py`: scheduled scan entry point
- Cron/hook wiring for post-session pattern detection
- Tests: repeated events produce candidate, one-off events do not, frequency threshold enforcement

### Phase 7 — Service Extraction (conditional)
**Goal:** Move research + pattern mining into `services/groundwork/` when justified.

**Trigger gate** — proceed only when one or more are true:
- GitHub/docs crawling latency becomes a session blocker
- Pattern mining needs background jobs or queue processing
- Embeddings/vector search become necessary
- Multiple apps/workflows need the same research engine
- Next.js runtime is the wrong host for research workloads

Deliverables (when triggered):
- `services/groundwork/` package
- Research and pattern adapters moved from `bin/` to service
- `bin/` scripts become thin CLI wrappers calling the service
- tRPC routers call service instead of DB directly for research-heavy reads

---

## Testing Requirements

**Phase 1:**
- Schema migration applies cleanly
- `groundwork-write.py` creates packet row + writeback_events rows
- `skillify-write.py` creates candidate row + writeback_events rows
- Every writeback row references source_kind + source_id

**Phase 2:**
- Trivial prompt → classifier skips groundwork
- Novel implementation prompt → classifier invokes groundwork
- Security/risky prompt → routes to security approval
- Max 3 skills enforced in packet assembly
- Max 5 repos enforced in packet assembly
- One-off event → no skillification candidate created
- Repeated event (≥3 sessions) → candidate created

**Phase 3:**
- All 6 new routes render without error
- Every status badge has a linked detail view
- tRPC queries return correct shapes

**Phase 4:**
- Status transitions follow lifecycle (candidate → approved → active)
- Direct candidate → active blocked
- Approval events created on every action
- Deprecation preserves historical record

**Phase 5:**
- GitHub adapter returns confidence + risk notes
- Abandoned repos labeled as risky prior art only
- Cache hits prevent duplicate external searches
- Adapter failure falls back gracefully

**Phase 6:**
- Post-session scan produces candidates for ≥3-session patterns
- Single-occurrence events produce no candidate
- Frequency and repeatability scores calculated correctly

---

## Acceptance Criteria

1. AIOS can classify whether a prompt should invoke `/groundwork`.
2. `/groundwork` produces a `groundwork_packets` row with classification, prior art, skills, recommendation, approval routing, and writebacks.
3. Skill recommendations are capped at 3; repo recommendations at 5.
4. Candidate skills are proposed but not activated automatically.
5. `/skillify-patterns` produces `skillification_candidates` from repeated session patterns.
6. Candidates enter the approval queue and can become `skill_registry_entries`.
7. Approved skills can be activated and attached to workflow stages.
8. Packets, candidates, proposals, and registry status are inspectable in the UI.
9. Every approval and writeback is auditable via `approval_events` and `writeback_events`.
10. Research does not run for trivial prompts.
11. All new code passes: `ruff check .`, `ruff format --check .`, `basedpyright`, `pnpm lint`, `pnpm tsc --noEmit`, and targeted tests.
12. Project truth file updated after each phase.
13. No broad rewrites — extends existing tables, routers, and registries.

---

## Open Assumptions

- `orchestration_runs.packet_id` FK constraint will reference `groundwork_packets(id)` — verify SQLite FK enforcement is on before adding.
- `workflow_synthesis_proposals` `kind` column addition requires a migration script in `bin/`.
- Phase 7 trigger evaluation happens at Phase 6 retrospective; no pre-commitment to extracting the service.
- Personal corpus (Obsidian vault) writebacks require explicit operator approval per the existing `obsidian_corpus_retriever` precedent.
