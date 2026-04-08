CREATE TABLE projects (
  id         TEXT PRIMARY KEY,
  name       TEXT NOT NULL,
  repo_path  TEXT NOT NULL,
  obsidian_path TEXT NOT NULL,
  status     TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE TABLE sessions (
  id                     TEXT PRIMARY KEY,
  project_id             TEXT NOT NULL,
  tool                   TEXT NOT NULL,  -- claude-code | codex | desktop-claude
  started_at             TEXT NOT NULL,
  ended_at               TEXT,
  objective              TEXT,
  status                 TEXT NOT NULL DEFAULT 'open',  -- open | closed | abandoned
  cwd                    TEXT,
  summary_candidate_path TEXT,
  FOREIGN KEY(project_id) REFERENCES projects(id)
);
CREATE TABLE tool_events (
  id           TEXT PRIMARY KEY,
  session_id   TEXT NOT NULL,
  source_tool  TEXT NOT NULL,
  event_type   TEXT NOT NULL,  -- SessionStart | UserPromptSubmit | PreToolUse | PostToolUse | Stop | SubagentStop | PreCompact
  event_time   TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  FOREIGN KEY(session_id) REFERENCES sessions(id)
);
CREATE TABLE prompts_used (
  id                   TEXT PRIMARY KEY,
  session_id           TEXT NOT NULL,
  prompt_hash          TEXT,
  prompt_text          TEXT,
  classification       TEXT,  -- debugging | planning | refactor | review | explain | other
  outcome_score        INTEGER,
  reusable_candidate   INTEGER NOT NULL DEFAULT 0, retrieval_fired INTEGER NOT NULL DEFAULT 0, retrieval_source TEXT,
  FOREIGN KEY(session_id) REFERENCES sessions(id)
);
CREATE TABLE artifacts (
  id            TEXT PRIMARY KEY,
  session_id    TEXT NOT NULL,
  artifact_type TEXT NOT NULL,  -- patch | plan | summary | test-output | note-candidate
  path          TEXT,
  metadata_json TEXT,
  created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  FOREIGN KEY(session_id) REFERENCES sessions(id)
);
CREATE TABLE next_action_candidates (
  id         TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  text       TEXT NOT NULL,
  priority   TEXT,  -- high | medium | low
  status     TEXT NOT NULL DEFAULT 'pending_review',  -- pending_review | promoted | discarded
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  FOREIGN KEY(session_id) REFERENCES sessions(id)
);
CREATE TABLE prompt_library_links (
  id                TEXT PRIMARY KEY,
  prompt_hash       TEXT NOT NULL,
  obsidian_note_path TEXT,
  promoted_at       TEXT
);
CREATE INDEX idx_sessions_project ON sessions(project_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_tool_events_session ON tool_events(session_id);
CREATE INDEX idx_tool_events_type ON tool_events(event_type);
CREATE INDEX idx_prompts_session ON prompts_used(session_id);
CREATE INDEX idx_prompts_reusable ON prompts_used(reusable_candidate);
CREATE INDEX idx_artifacts_session ON artifacts(session_id);
CREATE INDEX idx_next_actions_status ON next_action_candidates(status);
CREATE TABLE bug_log (
  id          TEXT PRIMARY KEY,
  session_id  TEXT,
  project_id  TEXT,
  symptom     TEXT NOT NULL,
  root_cause  TEXT,
  fix         TEXT,
  status      TEXT NOT NULL DEFAULT 'open',
  created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  resolved_at TEXT,
  promoted    INTEGER DEFAULT 0,
  FOREIGN KEY(session_id) REFERENCES sessions(id),
  FOREIGN KEY(project_id) REFERENCES projects(id)
);
CREATE INDEX idx_bugs_project ON bug_log(project_id);
CREATE INDEX idx_bugs_status  ON bug_log(status);
CREATE TABLE ai_history_imports (
  id                TEXT PRIMARY KEY,
  batch_id          TEXT NOT NULL,
  source            TEXT NOT NULL,
  source_id         TEXT,
  model             TEXT,
  conversation_date TEXT NOT NULL,
  title             TEXT NOT NULL,
  slug              TEXT NOT NULL,
  topic_tags        TEXT NOT NULL DEFAULT '[]',
  vault_path        TEXT,
  quality           TEXT DEFAULT 'keep',
  status            TEXT DEFAULT 'staged',
  promoted_at       TEXT,
  created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX idx_imports_batch  ON ai_history_imports(batch_id);
CREATE INDEX idx_imports_status ON ai_history_imports(status);
CREATE INDEX idx_imports_source ON ai_history_imports(source);
CREATE INDEX idx_imports_date   ON ai_history_imports(conversation_date);
CREATE TABLE workflow_metrics (
  id TEXT PRIMARY KEY,
  session_id TEXT REFERENCES sessions(id),
  metric_name TEXT NOT NULL,
  metric_value REAL NOT NULL,
  recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  notes TEXT
);
CREATE TABLE experiments (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  surface TEXT NOT NULL,
  hypothesis TEXT NOT NULL,
  baseline_value REAL,
  challenger_value REAL,
  verdict TEXT,
  started_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  ended_at TEXT,
  notes TEXT
);
CREATE INDEX idx_metrics_session ON workflow_metrics(session_id);
CREATE INDEX idx_metrics_name ON workflow_metrics(metric_name);
CREATE INDEX idx_prompts_retrieval ON prompts_used(retrieval_fired);
