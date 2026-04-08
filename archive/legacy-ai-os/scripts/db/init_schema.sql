-- AI OS v1 Schema
-- ~/ai-os/scripts/db/init_schema.sql
-- Initialize: sqlite3 ~/ai-os/db/ops.db < ~/ai-os/scripts/db/init_schema.sql

CREATE TABLE IF NOT EXISTS sessions (
  id          TEXT    PRIMARY KEY,          -- UUID or slug
  tool        TEXT    NOT NULL,             -- claude-code | codex | cowork
  project_id  TEXT,                         -- FK to projects.id
  started_at  INTEGER NOT NULL,             -- Unix timestamp
  ended_at    INTEGER,
  summary     TEXT,                         -- Plain text, written by hook
  outcome     TEXT,                         -- completed | abandoned | handed-off
  promoted    INTEGER DEFAULT 0,            -- 1 once pushed to vault
  vault_path  TEXT,                         -- Path to vault note
  tags        TEXT                          -- JSON array
);

CREATE TABLE IF NOT EXISTS prompts (
  id          TEXT    PRIMARY KEY,
  slug        TEXT    UNIQUE NOT NULL,      -- e.g. refactor-to-hooks
  content     TEXT    NOT NULL,
  tool        TEXT,                         -- claude-code | codex | both
  project_id  TEXT,                         -- NULL = global
  use_count   INTEGER DEFAULT 0,
  last_used   INTEGER,
  promoted    INTEGER DEFAULT 0,
  vault_path  TEXT,
  created_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS tool_events (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id  TEXT,
  tool        TEXT    NOT NULL,
  event_type  TEXT    NOT NULL,             -- start | end | error | handoff
  payload     TEXT,                         -- JSON blob
  created_at  INTEGER NOT NULL,
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS task_outcomes (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id  TEXT,
  project_id  TEXT,
  description TEXT    NOT NULL,
  outcome     TEXT    NOT NULL,             -- completed | blocked | deferred
  next_steps  TEXT,                         -- JSON array of strings
  created_at  INTEGER NOT NULL,
  promoted    INTEGER DEFAULT 0,
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS bug_log (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id  TEXT,
  project_id  TEXT,
  symptom     TEXT    NOT NULL,
  root_cause  TEXT,
  fix         TEXT,
  status      TEXT    DEFAULT 'open',      -- open | fixed | wont-fix
  created_at  INTEGER NOT NULL,
  resolved_at INTEGER,
  promoted    INTEGER DEFAULT 0,
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS projects (
  id          TEXT    PRIMARY KEY,          -- slug, e.g. my-app
  name        TEXT    NOT NULL,
  repo_path   TEXT,                         -- Absolute path to git repo
  status      TEXT    DEFAULT 'active',    -- active | paused | archived
  vault_path  TEXT,                         -- Path to vault project note
  created_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS capture_queue (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  type        TEXT    NOT NULL,             -- session | prompt | bug | outcome
  source      TEXT,                         -- claude-code | codex | manual
  content     TEXT    NOT NULL,             -- JSON payload
  status      TEXT    DEFAULT 'pending',   -- pending | reviewed | promoted | discarded
  created_at  INTEGER NOT NULL,
  reviewed_at INTEGER
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_sessions_project   ON sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_sessions_tool      ON sessions(tool);
CREATE INDEX IF NOT EXISTS idx_sessions_promoted  ON sessions(promoted);
CREATE INDEX IF NOT EXISTS idx_events_session     ON tool_events(session_id);
CREATE INDEX IF NOT EXISTS idx_bugs_project       ON bug_log(project_id);
CREATE INDEX IF NOT EXISTS idx_bugs_status        ON bug_log(status);
CREATE INDEX IF NOT EXISTS idx_queue_status       ON capture_queue(status);
