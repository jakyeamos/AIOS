import Database from "better-sqlite3";
import os from "node:os";
import path from "node:path";

const dbPath = path.join(os.homedir(), "AIOS", "data", "aios.db");

declare global {
  var __aiosDb: Database.Database | undefined;
}

export const getDb = (): Database.Database => {
  if (!globalThis.__aiosDb) {
    globalThis.__aiosDb = new Database(dbPath);
  }

  return globalThis.__aiosDb;
};

export const tableExists = (tableName: string): boolean => {
  const row = getDb()
    .prepare("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1")
    .get(tableName) as { name: string } | undefined;

  return Boolean(row?.name);
};
