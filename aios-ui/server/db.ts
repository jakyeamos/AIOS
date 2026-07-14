import Database from "better-sqlite3";
import os from "node:os";
import path from "node:path";

const defaultDbPath = path.join(os.homedir(), "AIOS", "data", "aios.db");

const resolveDbPath = (): string => {
  const configuredPath = process.env.AIOS_DB?.trim();
  if (!configuredPath) {
    return defaultDbPath;
  }
  if (configuredPath === "~") {
    return os.homedir();
  }
  if (configuredPath.startsWith("~/")) {
    return path.join(os.homedir(), configuredPath.slice(2));
  }
  return path.resolve(configuredPath);
};

declare global {
  var __aiosDb: Database.Database | undefined;
}

export const getDb = (): Database.Database => {
  if (!globalThis.__aiosDb) {
    const db = new Database(resolveDbPath());
    db.pragma("foreign_keys = ON");
    db.pragma("journal_mode = WAL");
    db.pragma("busy_timeout = 10000");
    globalThis.__aiosDb = db;
  }

  return globalThis.__aiosDb;
};

export const tableExists = (tableName: string): boolean => {
  const row = getDb()
    .prepare("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1")
    .get(tableName) as { name: string } | undefined;

  return Boolean(row?.name);
};
