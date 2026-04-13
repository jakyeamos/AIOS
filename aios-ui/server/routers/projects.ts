import { z } from "zod";

import type { Project, ProjectStatus, Session } from "@/lib/types";
import { tableExists } from "@/server/db";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

type ProjectRow = {
  id: string;
  name: string;
  repoPath: string;
  status: string;
  createdAt: string;
  sessionCount: number;
  lastActiveAt: string | null;
  openBugs: number;
};

type ProjectSessionRow = {
  id: string;
  projectId: string;
  projectName: string;
  tool: string;
  startedAt: string;
  endedAt: string | null;
  objective: string | null;
  status: string;
  cwd: string | null;
  durationMs: number | null;
  promptCount: number;
  toolEventCount: number;
  artifactCount: number;
};

const normalizeStatus = (status: string): ProjectStatus => (status === "archived" ? "archived" : "active");

const normalizeSessionStatus = (status: string): Session["status"] => {
  if (status === "open" || status === "closed" || status === "abandoned") {
    return status;
  }

  return "open";
};

const normalizeTool = (tool: string): Session["tool"] => {
  if (tool === "codex" || tool === "claude-code" || tool === "desktop-claude") {
    return tool;
  }

  return "codex";
};

const mapProject = (row: ProjectRow): Project => ({
  id: row.id,
  name: row.name,
  repoPath: row.repoPath,
  status: normalizeStatus(row.status),
  createdAt: row.createdAt,
  sessionCount: row.sessionCount,
  lastActiveAt: row.lastActiveAt,
  openBugs: row.openBugs,
});

const mapSession = (row: ProjectSessionRow): Session => ({
  id: row.id,
  projectId: row.projectId,
  projectName: row.projectName,
  tool: normalizeTool(row.tool),
  startedAt: row.startedAt,
  endedAt: row.endedAt,
  objective: row.objective,
  status: normalizeSessionStatus(row.status),
  cwd: row.cwd,
  durationMs: row.durationMs,
  promptCount: row.promptCount,
  toolEventCount: row.toolEventCount,
  artifactCount: row.artifactCount,
});

export const projectsRouter = createTRPCRouter({
  list: publicProcedure
    .input(z.object({ limit: z.number().int().min(1).max(200).default(100) }).optional())
    .query(({ ctx, input }): Project[] => {
      if (!tableExists("projects")) {
        return [];
      }

      const limit = input?.limit ?? 100;
      const openBugSelect = tableExists("bug_log")
        ? "(SELECT COUNT(*) FROM bug_log b WHERE b.project_id = p.id AND b.status = 'open')"
        : "0";
      const rows = ctx.db
        .prepare(
          `
          SELECT
            p.id,
            p.name,
            p.repo_path AS repoPath,
            p.status,
            p.created_at AS createdAt,
            (SELECT COUNT(*) FROM sessions s WHERE s.project_id = p.id) AS sessionCount,
            (SELECT MAX(s.started_at) FROM sessions s WHERE s.project_id = p.id) AS lastActiveAt,
            ${openBugSelect} AS openBugs
          FROM projects p
          ORDER BY (lastActiveAt IS NULL) ASC, lastActiveAt DESC, p.name ASC
          LIMIT ?
        `,
        )
        .all(limit) as ProjectRow[];

      return rows.map(mapProject);
    }),

  detail: publicProcedure
    .input(z.object({ id: z.string().min(1) }))
    .query(({ ctx, input }): { project: Project | null; sessions: Session[] } => {
      if (!tableExists("projects")) {
        return { project: null, sessions: [] };
      }

      const openBugSelect = tableExists("bug_log")
        ? "(SELECT COUNT(*) FROM bug_log b WHERE b.project_id = p.id AND b.status = 'open')"
        : "0";
      const projectRow = ctx.db
        .prepare(
          `
          SELECT
            p.id,
            p.name,
            p.repo_path AS repoPath,
            p.status,
            p.created_at AS createdAt,
            (SELECT COUNT(*) FROM sessions s WHERE s.project_id = p.id) AS sessionCount,
            (SELECT MAX(s.started_at) FROM sessions s WHERE s.project_id = p.id) AS lastActiveAt,
            ${openBugSelect} AS openBugs
          FROM projects p
          WHERE p.id = ?
          LIMIT 1
        `,
        )
        .get(input.id) as ProjectRow | undefined;

      const sessionsRows = tableExists("sessions")
        ? (ctx.db
            .prepare(
              `
              SELECT
                s.id,
                s.project_id AS projectId,
                p.name AS projectName,
                s.tool,
                s.started_at AS startedAt,
                s.ended_at AS endedAt,
                s.objective,
                s.status,
                s.cwd,
                CASE
                  WHEN s.ended_at IS NULL THEN NULL
                  ELSE CAST((julianday(s.ended_at) - julianday(s.started_at)) * 86400000 AS INTEGER)
                END AS durationMs,
                (SELECT COUNT(*) FROM prompts_used pu WHERE pu.session_id = s.id) AS promptCount,
                (SELECT COUNT(*) FROM tool_events te WHERE te.session_id = s.id) AS toolEventCount,
                (SELECT COUNT(*) FROM artifacts a WHERE a.session_id = s.id) AS artifactCount
              FROM sessions s
              INNER JOIN projects p ON p.id = s.project_id
              WHERE s.project_id = ?
              ORDER BY s.started_at DESC
              LIMIT 25
            `,
            )
            .all(input.id) as ProjectSessionRow[])
        : [];

      return {
        project: projectRow ? mapProject(projectRow) : null,
        sessions: sessionsRows.map(mapSession),
      };
    }),
});
