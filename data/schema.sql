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
  status                 TEXT NOT NULL DEFAULT 'open',  -- open | closed | abandoned
  cwd                    TEXT,
  summary_candidate_path TEXT,
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
