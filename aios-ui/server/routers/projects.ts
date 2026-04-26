import { z } from "zod";
import type Database from "better-sqlite3";

import type { TaskiProjectSummary } from "@/lib/control-plane";
import type { Project, ProjectStatus, Session } from "@/lib/types";
import { getProjectQualityPipeline } from "@/server/aios/quality-pipeline";
import { ensureControlPlaneSchema } from "@/server/aios/schema";
import { updateStandardsBackfillTask } from "@/server/aios/standards-health";
import { getTaskiProjectSummary } from "@/server/aios/taski";
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
  healthScore: number | null;
  criticalDeltaCount: number | null;
  unknownCoverage: number | null;
  healthTrend: number | null;
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

const mapProject = (db: Database.Database, row: ProjectRow): Project => {
  const qualityPipeline = getProjectQualityPipeline(db, row.id);
  return {
    id: row.id,
    name: row.name,
    repoPath: row.repoPath,
    status: normalizeStatus(row.status),
    createdAt: row.createdAt,
    sessionCount: row.sessionCount,
    lastActiveAt: row.lastActiveAt,
    openBugs: row.openBugs,
    healthScore: row.healthScore === null ? null : Number(row.healthScore),
    criticalDeltaCount: Number(row.criticalDeltaCount ?? 0),
    unknownCoverage: row.unknownCoverage === null ? null : Number(row.unknownCoverage),
    healthTrend: row.healthTrend === null ? null : Number(row.healthTrend),
    pipelineStatus: qualityPipeline.overallStatus,
    pipelineConfiguredRequired: qualityPipeline.coverage.configuredRequired,
    pipelineRequired: qualityPipeline.coverage.required,
  };
};

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
      ensureControlPlaneSchema(ctx.db);
      if (!tableExists("projects")) {
        return [];
      }

      const limit = input?.limit ?? 100;
      const openBugSelect = tableExists("bug_log")
        ? "(SELECT COUNT(*) FROM bug_log b WHERE b.project_id = p.id AND b.status = 'open')"
        : "0";
      const healthScoreSelect = tableExists("standards_health_snapshots")
        ? "(SELECT overall_score FROM standards_health_snapshots sh WHERE sh.project_id = p.id ORDER BY sh.created_at DESC LIMIT 1)"
        : "NULL";
      const criticalDeltaSelect = tableExists("standards_health_snapshots")
        ? "(SELECT critical_delta_count FROM standards_health_snapshots sh WHERE sh.project_id = p.id ORDER BY sh.created_at DESC LIMIT 1)"
        : "0";
      const unknownCoverageSelect = tableExists("standards_health_snapshots")
        ? "(SELECT unknown_coverage FROM standards_health_snapshots sh WHERE sh.project_id = p.id ORDER BY sh.created_at DESC LIMIT 1)"
        : "NULL";
      const healthTrendSelect = tableExists("standards_health_snapshots")
        ? `(
            SELECT COALESCE(latest.overall_score, 0) - COALESCE(previous.overall_score, latest.overall_score, 0)
            FROM (SELECT overall_score FROM standards_health_snapshots WHERE project_id = p.id ORDER BY created_at DESC LIMIT 1) latest
            LEFT JOIN (
              SELECT overall_score
              FROM standards_health_snapshots
              WHERE project_id = p.id
              ORDER BY created_at DESC
              LIMIT 1 OFFSET 1
            ) previous ON 1=1
          )`
        : "NULL";
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
            ${openBugSelect} AS openBugs,
            ${healthScoreSelect} AS healthScore,
            ${criticalDeltaSelect} AS criticalDeltaCount,
            ${unknownCoverageSelect} AS unknownCoverage,
            ${healthTrendSelect} AS healthTrend
          FROM projects p
          ORDER BY (lastActiveAt IS NULL) ASC, lastActiveAt DESC, p.name ASC
          LIMIT ?
        `,
        )
        .all(limit) as ProjectRow[];

      return rows.map((row) => mapProject(ctx.db, row));
    }),

  detail: publicProcedure
    .input(z.object({ id: z.string().min(1) }))
    .query(({ ctx, input }): { project: Project | null; sessions: Session[] } => {
      ensureControlPlaneSchema(ctx.db);
      if (!tableExists("projects")) {
        return { project: null, sessions: [] };
      }

      const openBugSelect = tableExists("bug_log")
        ? "(SELECT COUNT(*) FROM bug_log b WHERE b.project_id = p.id AND b.status = 'open')"
        : "0";
      const healthScoreSelect = tableExists("standards_health_snapshots")
        ? "(SELECT overall_score FROM standards_health_snapshots sh WHERE sh.project_id = p.id ORDER BY sh.created_at DESC LIMIT 1)"
        : "NULL";
      const criticalDeltaSelect = tableExists("standards_health_snapshots")
        ? "(SELECT critical_delta_count FROM standards_health_snapshots sh WHERE sh.project_id = p.id ORDER BY sh.created_at DESC LIMIT 1)"
        : "0";
      const unknownCoverageSelect = tableExists("standards_health_snapshots")
        ? "(SELECT unknown_coverage FROM standards_health_snapshots sh WHERE sh.project_id = p.id ORDER BY sh.created_at DESC LIMIT 1)"
        : "NULL";
      const healthTrendSelect = tableExists("standards_health_snapshots")
        ? `(
            SELECT COALESCE(latest.overall_score, 0) - COALESCE(previous.overall_score, latest.overall_score, 0)
            FROM (SELECT overall_score FROM standards_health_snapshots WHERE project_id = p.id ORDER BY created_at DESC LIMIT 1) latest
            LEFT JOIN (
              SELECT overall_score
              FROM standards_health_snapshots
              WHERE project_id = p.id
              ORDER BY created_at DESC
              LIMIT 1 OFFSET 1
            ) previous ON 1=1
          )`
        : "NULL";
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
            ${openBugSelect} AS openBugs,
            ${healthScoreSelect} AS healthScore,
            ${criticalDeltaSelect} AS criticalDeltaCount,
            ${unknownCoverageSelect} AS unknownCoverage,
            ${healthTrendSelect} AS healthTrend
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
        project: projectRow ? mapProject(ctx.db, projectRow) : null,
        sessions: sessionsRows.map(mapSession),
      };
    }),

  taskiSummary: publicProcedure
    .input(z.object({ projectId: z.string().min(1) }))
    .query(({ ctx, input }): TaskiProjectSummary | null => getTaskiProjectSummary(ctx.db, input.projectId)),

  updateBackfillTask: publicProcedure
    .input(
      z.object({
        taskId: z.string().min(1),
        owner: z.string().max(120).nullable().optional(),
        status: z.string().min(1).max(40).optional(),
        priorityBucket: z.enum(["foundational", "high_leverage", "quick_wins", "blocked", "waived_deferred"]).optional(),
        blocked: z.boolean().optional(),
        blockedReason: z.string().max(400).nullable().optional(),
        dueAt: z.string().max(40).nullable().optional(),
        reviewAt: z.string().max(40).nullable().optional(),
      }),
    )
    .mutation(({ ctx, input }) => updateStandardsBackfillTask(ctx.db, input)),
});
