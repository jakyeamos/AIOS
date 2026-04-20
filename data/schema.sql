-- AIOS SQLite schema v1
-- ~/AIOS/data/aios.db

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS projects (
  id         TEXT PRIMARY KEY,
  name       TEXT NOT NULL,
  repo_path  TEXT NOT NULL,
  obsidian_path TEXT NOT NULL,
  status     TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS sessions (
  id                     TEXT PRIMARY KEY,
  project_id             TEXT NOT NULL,
  tool                   TEXT NOT NULL,  -- claude-code | codex | desktop-claude
  started_at             TEXT NOT NULL,
  ended_at               TEXT,
  objective              TEXT,
  run_id                 TEXT REFERENCES orchestration_runs(id),
  invocation_id          TEXT REFERENCES orchestration_invocations(id),
  runtime_metadata_json  TEXT NOT NULL DEFAULT '{}',
  status                 TEXT NOT NULL DEFAULT 'open',  -- open | closed | abandoned
  cwd                    TEXT,
  summary_candidate_path TEXT,
  handoff_path           TEXT,
  FOREIGN KEY(project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS tool_events (
  id           TEXT PRIMARY KEY,
  session_id   TEXT NOT NULL,
  source_tool  TEXT NOT NULL,
  event_type   TEXT NOT NULL,  -- SessionStart | UserPromptSubmit | PreToolUse | PostToolUse | Stop | SubagentStop | PreCompact
  event_time   TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS prompts_used (
  id                   TEXT PRIMARY KEY,
  session_id           TEXT NOT NULL,
  prompt_hash          TEXT,
  prompt_text          TEXT,
  classification       TEXT,  -- debugging | planning | refactor | review | explain | other
  outcome_score        INTEGER,
  reusable_candidate   INTEGER NOT NULL DEFAULT 0,
  retrieval_fired      INTEGER NOT NULL DEFAULT 0,
  retrieval_source     TEXT,
  FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS artifacts (
  id            TEXT PRIMARY KEY,
  session_id    TEXT NOT NULL,
  artifact_type TEXT NOT NULL,  -- patch | plan | summary | test-output | note-candidate
  path          TEXT,
  metadata_json TEXT,
  created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS next_action_candidates (
  id         TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  text       TEXT NOT NULL,
  priority   TEXT,  -- high | medium | low
  status     TEXT NOT NULL DEFAULT 'pending_review',  -- pending_review | promoted | discarded
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS prompt_library_links (
  id                TEXT PRIMARY KEY,
  prompt_hash       TEXT NOT NULL,
  obsidian_note_path TEXT,
  promoted_at       TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_tool_events_session ON tool_events(session_id);
CREATE INDEX IF NOT EXISTS idx_tool_events_type ON tool_events(event_type);
CREATE INDEX IF NOT EXISTS idx_prompts_session ON prompts_used(session_id);
CREATE INDEX IF NOT EXISTS idx_prompts_reusable ON prompts_used(reusable_candidate);
CREATE INDEX IF NOT EXISTS idx_artifacts_session ON artifacts(session_id);
CREATE INDEX IF NOT EXISTS idx_next_actions_status ON next_action_candidates(status);

CREATE TABLE IF NOT EXISTS patterns (
  id TEXT PRIMARY KEY,
  class TEXT NOT NULL,          -- prompt|bug_fix|architecture|workflow|failure|assumption
  title TEXT NOT NULL,
  evidence TEXT NOT NULL DEFAULT '[]',  -- JSON array of source IDs or note paths
  confidence REAL DEFAULT 0.5,          -- 0.0–1.0
  status TEXT DEFAULT 'candidate',      -- candidate|validated|promoted|discarded
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  promoted_at TEXT,
  vault_path TEXT
);
CREATE INDEX IF NOT EXISTS idx_patterns_class ON patterns(class);
CREATE INDEX IF NOT EXISTS idx_patterns_status ON patterns(status);
CREATE TABLE IF NOT EXISTS orchestration_runs (
  id TEXT PRIMARY KEY,
  project_id TEXT REFERENCES projects(id),
  session_id TEXT REFERENCES sessions(id),
  objective TEXT NOT NULL,
  workflow_key TEXT NOT NULL,
  agent_key TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'planned',
  rationale TEXT NOT NULL,
  assumptions_json TEXT NOT NULL DEFAULT '[]',
  context_trace_json TEXT NOT NULL DEFAULT '[]',
  backend_key TEXT,
  active_invocation_id TEXT REFERENCES orchestration_invocations(id),
  packet_id TEXT,
  memory_update_id TEXT,
  result_summary TEXT,
  started_at TEXT,
  completed_at TEXT,
  failed_at TEXT,
  canceled_at TEXT,
  superseded_by_run_id TEXT,
  status_reason_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_orchestration_runs_project
  ON orchestration_runs(project_id, created_at DESC);
CREATE TABLE IF NOT EXISTS orchestration_invocations (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES orchestration_runs(id),
  backend_key TEXT NOT NULL,
  backend_label TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  handshake_token TEXT NOT NULL,
  session_id TEXT REFERENCES sessions(id),
  pid INTEGER,
  command_json TEXT NOT NULL DEFAULT '[]',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  started_at TEXT,
  ended_at TEXT,
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_orchestration_invocations_run
  ON orchestration_invocations(run_id, created_at DESC);
CREATE TABLE IF NOT EXISTS orchestration_run_events (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES orchestration_runs(id),
  project_id TEXT REFERENCES projects(id),
  session_id TEXT REFERENCES sessions(id),
  invocation_id TEXT REFERENCES orchestration_invocations(id),
  event_type TEXT NOT NULL,
  from_status TEXT,
  to_status TEXT,
  summary TEXT NOT NULL,
  reason_json TEXT NOT NULL DEFAULT '{}',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_orchestration_run_events_run
  ON orchestration_run_events(run_id, created_at DESC);
CREATE TABLE IF NOT EXISTS briefing_packets (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES orchestration_runs(id),
  project_id TEXT REFERENCES projects(id),
  objective TEXT NOT NULL,
  workflow_key TEXT NOT NULL,
  agent_key TEXT NOT NULL,
  packet_markdown TEXT NOT NULL,
  sections_json TEXT NOT NULL DEFAULT '[]',
  policy_mode TEXT NOT NULL DEFAULT 'compact-ranked',
  token_budget INTEGER NOT NULL DEFAULT 900,
  selection_trace_json TEXT NOT NULL DEFAULT '[]',
  omitted_context_json TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_briefing_packets_project
  ON briefing_packets(project_id, created_at DESC);
CREATE TABLE IF NOT EXISTS memory_updates (
  id TEXT PRIMARY KEY,
  project_id TEXT REFERENCES projects(id),
  run_id TEXT REFERENCES orchestration_runs(id),
  packet_id TEXT REFERENCES briefing_packets(id),
  session_id TEXT REFERENCES sessions(id),
  source TEXT NOT NULL,
  summary TEXT NOT NULL,
  changes_json TEXT NOT NULL DEFAULT '[]',
  risks_json TEXT NOT NULL DEFAULT '[]',
  open_questions_json TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_memory_updates_project
  ON memory_updates(project_id, created_at DESC);
CREATE TABLE IF NOT EXISTS knowledge_topics (
  id TEXT PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  kind TEXT NOT NULL,
  summary TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 0.5,
  freshness TEXT NOT NULL DEFAULT 'Unknown',
  project_id TEXT REFERENCES projects(id),
  canonical_href TEXT NOT NULL,
  tags_json TEXT NOT NULL DEFAULT '[]',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_knowledge_topics_kind
  ON knowledge_topics(kind, updated_at DESC);
CREATE TABLE IF NOT EXISTS knowledge_relationships (
  id TEXT PRIMARY KEY,
  from_topic_id TEXT NOT NULL REFERENCES knowledge_topics(id),
  to_topic_id TEXT NOT NULL REFERENCES knowledge_topics(id),
  relation TEXT NOT NULL,
  weight REAL NOT NULL DEFAULT 0.5,
  provenance_kind TEXT NOT NULL,
  provenance_id TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_knowledge_relationships_from
  ON knowledge_relationships(from_topic_id, relation);
CREATE TABLE IF NOT EXISTS knowledge_references (
  id TEXT PRIMARY KEY,
  topic_id TEXT NOT NULL REFERENCES knowledge_topics(id),
  source_kind TEXT NOT NULL,
  source_id TEXT,
  project_id TEXT REFERENCES projects(id),
  label TEXT NOT NULL,
  href TEXT NOT NULL,
  excerpt TEXT NOT NULL,
  freshness TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 0.5,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_knowledge_references_topic
  ON knowledge_references(topic_id, created_at DESC);
CREATE TABLE IF NOT EXISTS knowledge_markers (
  id TEXT PRIMARY KEY,
  topic_id TEXT NOT NULL REFERENCES knowledge_topics(id),
  marker_kind TEXT NOT NULL,
  severity TEXT NOT NULL DEFAULT 'warning',
  summary TEXT NOT NULL,
  source_ref TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_knowledge_markers_topic
  ON knowledge_markers(topic_id, created_at DESC);
CREATE TABLE IF NOT EXISTS knowledge_graph_state (
  graph_key TEXT PRIMARY KEY,
  last_refreshed_at TEXT NOT NULL,
  note TEXT
);
CREATE TABLE IF NOT EXISTS packet_expansions (
  id TEXT PRIMARY KEY,
  run_id TEXT REFERENCES orchestration_runs(id),
  packet_id TEXT NOT NULL REFERENCES briefing_packets(id),
  project_id TEXT REFERENCES projects(id),
  request_kind TEXT NOT NULL,
  request_target TEXT NOT NULL,
  token_budget INTEGER NOT NULL DEFAULT 180,
  status TEXT NOT NULL DEFAULT 'completed',
  returned_context_json TEXT NOT NULL DEFAULT '[]',
  trace_json TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_packet_expansions_packet
  ON packet_expansions(packet_id, created_at DESC);
CREATE TABLE IF NOT EXISTS improvement_writebacks (
  id TEXT PRIMARY KEY,
  run_id TEXT REFERENCES orchestration_runs(id),
  project_id TEXT REFERENCES projects(id),
  layer_type TEXT NOT NULL,
  layer_key TEXT NOT NULL,
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  evidence_json TEXT NOT NULL DEFAULT '[]',
  proposed_change_json TEXT NOT NULL DEFAULT '{}',
  impact_scope TEXT NOT NULL DEFAULT 'scoped',
  status TEXT NOT NULL DEFAULT 'proposed',
  requires_approval INTEGER NOT NULL DEFAULT 0,
  approval_reason TEXT,
  token_regressive INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  decision_note TEXT,
  decision_actor TEXT,
  decision_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_improvement_writebacks_project
  ON improvement_writebacks(project_id, created_at DESC);
CREATE TABLE IF NOT EXISTS improvement_writeback_events (
  id TEXT PRIMARY KEY,
  writeback_id TEXT NOT NULL REFERENCES improvement_writebacks(id),
  run_id TEXT REFERENCES orchestration_runs(id),
  event_type TEXT NOT NULL,
  from_status TEXT,
  to_status TEXT,
  actor TEXT NOT NULL DEFAULT 'system',
  note TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_improvement_writeback_events_writeback
  ON improvement_writeback_events(writeback_id, created_at DESC);
CREATE TABLE IF NOT EXISTS consistency_evaluations (
  id TEXT PRIMARY KEY,
  project_id TEXT REFERENCES projects(id),
  run_id TEXT REFERENCES orchestration_runs(id),
  packet_id TEXT REFERENCES briefing_packets(id),
  invocation_id TEXT REFERENCES orchestration_invocations(id),
  trigger_kind TEXT NOT NULL,
  evaluator_version TEXT NOT NULL,
  summary TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_consistency_evaluations_project
  ON consistency_evaluations(project_id, created_at DESC);
CREATE TABLE IF NOT EXISTS consistency_findings (
  id TEXT PRIMARY KEY,
  evaluation_id TEXT NOT NULL REFERENCES consistency_evaluations(id),
  project_id TEXT REFERENCES projects(id),
  run_id TEXT REFERENCES orchestration_runs(id),
  packet_id TEXT REFERENCES briefing_packets(id),
  topic_slug TEXT,
  finding_kind TEXT NOT NULL,
  severity TEXT NOT NULL,
  rule_key TEXT NOT NULL,
  summary TEXT NOT NULL,
  provenance_json TEXT NOT NULL DEFAULT '[]',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_consistency_findings_project
  ON consistency_findings(project_id, created_at DESC);
