import fs from "node:fs";
import path from "node:path";

import type Database from "better-sqlite3";

import type { ChangeItem } from "@/lib/control-plane";
import { extractMarkdownTitle, resolveAiosRoot, summarizeParagraph } from "@/server/aios/filesystem";
import { ensureControlPlaneSchema } from "@/server/aios/schema";
import { tableExists } from "@/server/db";

type SessionChangeRow = {
  id: string;
  projectName: string;
  startedAt: string;
  objective: string | null;
};

type MemoryUpdateRow = {
  id: string;
  summary: string;
  createdAt: string;
};

type PacketChangeRow = {
  id: string;
  objective: string;
  workflowKey: string;
  createdAt: string;
};

type BugRow = {
  id: string;
  symptom: string;
  createdAt: string;
};

export const listRecentChanges = (
  db: Database.Database,
  options?: { projectId?: string; limit?: number },
): ChangeItem[] => {
  const projectId = options?.projectId;
  const limit = options?.limit ?? 8;
  const items: ChangeItem[] = [];

  if (tableExists("sessions") && tableExists("projects")) {
    const sessionWhere = projectId ? "WHERE s.project_id = ?" : "";
    const sessionRows = db
      .prepare(
        `
        SELECT
          s.id,
          p.name AS projectName,
          s.started_at AS startedAt,
          s.objective
        FROM sessions s
        INNER JOIN projects p ON p.id = s.project_id
        ${sessionWhere}
        ORDER BY s.started_at DESC
        LIMIT ?
      `,
      )
      .all(...(projectId ? [projectId, limit] : [limit])) as SessionChangeRow[];

    for (const row of sessionRows) {
      items.push({
        id: `session-${row.id}`,
        title: `${row.projectName} session`,
        summary: row.objective ?? "Session captured operational changes and artifacts.",
        timestamp: row.startedAt,
        href: `/runs/${row.id}`,
        kind: "session",
        confidence: 0.82,
      });
    }
  }

  ensureControlPlaneSchema(db);

  const memoryWhere = projectId ? "WHERE project_id = ?" : "";
  const memoryRows = db
    .prepare(
      `
      SELECT id, summary, created_at AS createdAt
      FROM memory_updates
      ${memoryWhere}
      ORDER BY created_at DESC
      LIMIT ?
    `,
    )
    .all(...(projectId ? [projectId, limit] : [limit])) as MemoryUpdateRow[];

  for (const row of memoryRows) {
    items.push({
      id: `memory-${row.id}`,
      title: "Post-run memory update",
      summary: row.summary,
      timestamp: row.createdAt,
      kind: "memory",
      confidence: 0.88,
    });
  }

  const packetRows = db
    .prepare(
      `
      SELECT
        id,
        objective,
        workflow_key AS workflowKey,
        created_at AS createdAt
      FROM briefing_packets
      ORDER BY created_at DESC
      LIMIT ?
    `,
    )
    .all(Math.max(2, Math.floor(limit / 2))) as PacketChangeRow[];

  for (const row of packetRows) {
    items.push({
      id: `packet-${row.id}`,
      title: "Briefing packet generated",
      summary: `${row.objective} via ${row.workflowKey}.`,
      timestamp: row.createdAt,
      href: "/control",
      kind: "packet",
      confidence: 0.9,
    });
  }

  if (tableExists("bug_log")) {
    const bugWhere = projectId ? "WHERE project_id = ?" : "";
    const bugRows = db
      .prepare(
        `
        SELECT id, symptom, created_at AS createdAt
        FROM bug_log
        ${bugWhere}
        ORDER BY created_at DESC
        LIMIT ?
      `,
      )
      .all(...(projectId ? [projectId, Math.max(2, Math.floor(limit / 2))] : [Math.max(2, Math.floor(limit / 2))])) as BugRow[];

    for (const row of bugRows) {
      items.push({
        id: `bug-${row.id}`,
        title: "Bug log update",
        summary: row.symptom,
        timestamp: row.createdAt,
        kind: "bug",
        confidence: 0.74,
      });
    }
  }

  const adrItems = listRecentDecisionChanges(limit);
  items.push(...adrItems);

  return items
    .sort((left, right) => right.timestamp.localeCompare(left.timestamp))
    .slice(0, limit);
};

const listRecentDecisionChanges = (limit: number): ChangeItem[] => {
  const root = resolveAiosRoot();
  const adrDir = path.join(root, "docs", "adr");

  if (!fs.existsSync(adrDir)) {
    return [];
  }

  return fs
    .readdirSync(adrDir)
    .filter((name) => name.endsWith(".md"))
    .map((name) => {
      const fullPath = path.join(adrDir, name);
      const content = fs.readFileSync(fullPath, "utf8");
      const stats = fs.statSync(fullPath);
      const slug = name.replace(/\.md$/, "");

      return {
        id: `decision-${slug}`,
        title: extractMarkdownTitle(content, slug),
        summary: summarizeParagraph(content),
        timestamp: stats.mtime.toISOString(),
        href: `/knowledge/${slug}`,
        kind: "decision",
        confidence: 0.94,
      } satisfies ChangeItem;
    })
    .sort((left, right) => right.timestamp.localeCompare(left.timestamp))
    .slice(0, limit);
};
