import type Database from "better-sqlite3";

const hasColumn = (db: Database.Database, tableName: string, columnName: string): boolean => {
  const rows = db.prepare(`PRAGMA table_info(${tableName})`).all() as Array<{ name: string }>;
  return rows.some((row) => row.name === columnName);
};

const ensureColumn = (
  db: Database.Database,
  tableName: string,
  columnName: string,
  definition: string,
): void => {
  if (!hasColumn(db, tableName, columnName)) {
    db.exec(`ALTER TABLE ${tableName} ADD COLUMN ${columnName} ${definition}`);
  }
};

export const ensureControlPlaneSchema = (db: Database.Database): void => {
  db.exec(`
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
      packet_id TEXT,
      memory_update_id TEXT,
      result_summary TEXT,
      completed_at TEXT,
      created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
      updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
    );

    CREATE INDEX IF NOT EXISTS idx_orchestration_runs_project
      ON orchestration_runs(project_id, created_at DESC);

    CREATE TABLE IF NOT EXISTS briefing_packets (
      id TEXT PRIMARY KEY,
      run_id TEXT NOT NULL REFERENCES orchestration_runs(id),
      project_id TEXT REFERENCES projects(id),
      objective TEXT NOT NULL,
      workflow_key TEXT NOT NULL,
      agent_key TEXT NOT NULL,
      packet_markdown TEXT NOT NULL,
      sections_json TEXT NOT NULL DEFAULT '[]',
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
  `);

  ensureColumn(db, "orchestration_runs", "memory_update_id", "TEXT");
  ensureColumn(db, "orchestration_runs", "result_summary", "TEXT");
  ensureColumn(db, "orchestration_runs", "completed_at", "TEXT");
  ensureColumn(db, "memory_updates", "run_id", "TEXT");
  ensureColumn(db, "memory_updates", "packet_id", "TEXT");
};
