CREATE TABLE IF NOT EXISTS session_provider_cursors (
  provider_id TEXT NOT NULL,
  source_path TEXT NOT NULL,
  last_mtime REAL,
  last_size INTEGER,
  last_hash TEXT,
  last_provider_session_id TEXT,
  last_scanned_at TEXT,
  PRIMARY KEY (provider_id, source_path)
);
