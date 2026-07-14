import type Database from "better-sqlite3";

const REQUIRED_TABLES = [
  "schema_migrations",
  "projects",
  "sessions",
  "orchestration_runs",
  "orchestration_invocations",
  "orchestration_run_events",
  "briefing_packets",
] as const;

const listMissingTables = (db: Database.Database): string[] => {
  const existing = new Set(
    (db
      .prepare("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
      .all() as Array<{ name: string }>).map((row) => row.name),
  );
  return REQUIRED_TABLES.filter((tableName) => !existing.has(tableName));
};

/**
 * Assert that the Python-owned migration ledger has prepared the UI's source
 * tables. The UI is a projection and must never create or alter the main
 * store at request time.
 */
export const assertControlPlaneSchema = (db: Database.Database): void => {
  const missingTables = listMissingTables(db);
  const userVersion = Number(db.pragma("user_version", { simple: true }));
  const ledgerRow = db
    .prepare("SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1")
    .get() as { version: number } | undefined;

  if (missingTables.length > 0 || userVersion < 1 || !ledgerRow || ledgerRow.version < 1) {
    const missing = missingTables.length > 0 ? ` Missing tables: ${missingTables.join(", ")}.` : "";
    throw new Error(
      `AIOS UI requires a Python-owned main-store migration before serving requests.${missing}`,
    );
  }
};

// Keep the existing import surface stable while callers migrate to the
// assertion name. This alias performs no DDL and cannot bootstrap the store.
export const ensureControlPlaneSchema = assertControlPlaneSchema;
