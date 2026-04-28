import { z } from "zod";
import type Database from "better-sqlite3";

import type { AiosProjectComponentKey, TaskiProjectSummary } from "@/lib/control-plane";
import {
  isAiosProjectComponentKey,
  setAiosProjectComponentEnabled,
} from "@/server/aios/project-components";
import type { Project, ProjectStatus, Session } from "@/lib/types";
import { trustedSignal } from "@/lib/trusted-signals";
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

const healthSource = {
  label: "Standards health snapshot",
  table: "standards_health_snapshots",
  field: "overall_score",
};

const projectStatusSignal = (status: ProjectStatus, sessionCount: number, lastActiveAt: string | null): Project["statusSignal"] =>
  trustedSignal({
    value: status,
    provenance: lastActiveAt ? "confirmed" : "inferred",
    confidence: lastActiveAt ? 0.9 : 0.55,
    source: { label: "Project inventory", table: "projects", field: "status" },
    freshness: lastActiveAt ?? "no session activity",
    explanation: lastActiveAt
      ? `Project status is persisted as ${status} and backed by ${sessionCount} recorded session(s).`
      : `Project status is persisted as ${status}, but no session activity is available to qualify recency.`,
    missingReason: lastActiveAt ? null : "No linked session activity has been recorded for this project.",
    contradiction: null,
  });

const healthSignal = (value: number | null): Project["healthScoreSignal"] =>
  trustedSignal({
    value,
    provenance: value === null ? "missing" : "confirmed",
    confidence: value === null ? 0 : 0.9,
    source: healthSource,
    freshness: value === null ? "missing" : "latest snapshot",
    explanation: value === null
      ? "No standards-health snapshot has been recorded for this project."
      : "Latest standards-health snapshot score on a 0-100 scale.",
    missingReason: value === null ? "No standards_health_snapshots row exists for this project." : null,
    contradiction: null,
  });

const trendSignal = (value: number | null): Project["healthTrendSignal"] =>
  trustedSignal({
    value,
    provenance: value === null ? "missing" : "confirmed",
    confidence: value === null ? 0 : 0.85,
    source: { label: "Standards health snapshot comparison", table: "standards_health_snapshots", field: "overall_score" },
    freshness: value === null ? "missing" : "latest two snapshots",
    explanation: value === null
      ? "No health trend is available because fewer than one standards snapshot exists."
      : "Difference between the latest health score and the previous snapshot.",
    missingReason: value === null ? "Insufficient standards-health snapshot history." : null,
    contradiction: null,
  });

const criticalDeltaSignal = (value: number): Project["criticalDeltaSignal"] =>
  trustedSignal({
    value,
    provenance: "confirmed",
    confidence: 0.85,
    source: { label: "Standards health snapshot", table: "standards_health_snapshots", field: "critical_delta_count" },
    freshness: "latest snapshot",
    explanation: "Count of critical standards deltas in the latest project health snapshot.",
    missingReason: null,
    contradiction: null,
  });

const unknownCoverageSignal = (value: number | null): Project["unknownCoverageSignal"] =>
  trustedSignal({
    value,
    provenance: value === null ? "missing" : "confirmed",
    confidence: value === null ? 0 : 0.85,
    source: { label: "Standards health snapshot", table: "standards_health_snapshots", field: "unknown_coverage" },
    freshness: value === null ? "missing" : "latest snapshot",
    explanation: value === null
      ? "Unknown coverage is missing because no standards-health snapshot exists."
      : "Fraction of applicable standards whose current state is unknown.",
    missingReason: value === null ? "No standards_health_snapshots row exists for this project." : null,
    contradiction: null,
  });

const pipelineLabel = (project: Pick<Project, "pipelineConfiguredRequired" | "pipelineRequired" | "pipelineStatus">): string => {
  if (project.pipelineRequired === 0) {
    return `${project.pipelineStatus} · no required checks`;
  }
  return `${project.pipelineConfiguredRequired}/${project.pipelineRequired} configured · ${project.pipelineStatus}`;
};

const pipelineSignal = (
  status: Project["pipelineStatus"],
  configuredRequired: number,
  required: number,
): Project["pipelineSignal"] => {
  const hasContradiction = status === "error" && configuredRequired === 0;
  const value = pipelineLabel({ pipelineStatus: status, pipelineConfiguredRequired: configuredRequired, pipelineRequired: required });
  return trustedSignal({
    value,
    provenance: hasContradiction ? "contradictory" : "confirmed",
    confidence: hasContradiction ? 0.35 : 0.85,
    source: { label: "Quality pipeline summary", table: "quality_pipeline_runs" },
    freshness: "latest gate state",
    explanation: hasContradiction
      ? "Pipeline status is error, but no required checks are configured. This is a backend finding instead of a silent status badge contradiction."
      : "Pipeline status is derived from required gate configuration and latest gate run state.",
    missingReason: required === 0 ? "No applicable required quality-pipeline gates were resolved for this project." : null,
    contradiction: hasContradiction ? "error status with zero configured required checks" : null,
  });
};

const aiosProjectComponentKeySchema = z.string().refine(
  (key): key is AiosProjectComponentKey => isAiosProjectComponentKey(key),
  "Unknown AIOS project component key.",
);

const mapProject = (db: Database.Database, row: ProjectRow): Project => {
  const qualityPipeline = getProjectQualityPipeline(db, row.id);
  const healthScore = row.healthScore === null ? null : Number(row.healthScore);
  const criticalDeltaCount = Number(row.criticalDeltaCount ?? 0);
  const unknownCoverage = row.unknownCoverage === null ? null : Number(row.unknownCoverage);
  const healthTrend = row.healthTrend === null ? null : Number(row.healthTrend);
  const status = normalizeStatus(row.status);
  const pipeline = {
    status: qualityPipeline.overallStatus,
    configuredRequired: qualityPipeline.coverage.configuredRequired,
    required: qualityPipeline.coverage.required,
  };
  return {
    id: row.id,
    name: row.name,
    repoPath: row.repoPath,
    status,
    createdAt: row.createdAt,
    sessionCount: row.sessionCount,
    lastActiveAt: row.lastActiveAt,
    openBugs: row.openBugs,
    healthScore,
    healthScoreSignal: healthSignal(healthScore),
    criticalDeltaCount,
    criticalDeltaSignal: criticalDeltaSignal(criticalDeltaCount),
    unknownCoverage,
    unknownCoverageSignal: unknownCoverageSignal(unknownCoverage),
    healthTrend,
    healthTrendSignal: trendSignal(healthTrend),
    pipelineStatus: pipeline.status,
    pipelineConfiguredRequired: pipeline.configuredRequired,
    pipelineRequired: pipeline.required,
    pipelineLabel: pipelineLabel({
      pipelineStatus: pipeline.status,
      pipelineConfiguredRequired: pipeline.configuredRequired,
      pipelineRequired: pipeline.required,
    }),
    pipelineSignal: pipelineSignal(pipeline.status, pipeline.configuredRequired, pipeline.required),
    statusSignal: projectStatusSignal(status, row.sessionCount, row.lastActiveAt),
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

  setAiosComponentEnabled: publicProcedure
    .input(
      z.object({
        projectId: z.string().min(1),
        componentKey: aiosProjectComponentKeySchema,
        enabled: z.boolean(),
      }),
    )
    .mutation(({ ctx, input }) =>
      setAiosProjectComponentEnabled(ctx.db, {
        projectId: input.projectId,
        componentKey: input.componentKey,
        enabled: input.enabled,
      }),
    ),

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
