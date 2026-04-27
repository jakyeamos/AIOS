import { z } from "zod";

import { seededCostSummary } from "@/lib/seed";
import type { CostBreakdownPoint, CostSummary } from "@/lib/types";
import { tableExists } from "@/server/db";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

type BreakdownRow = {
  key: string;
  label: string;
  tokens: number;
};

type ClassificationCountRow = {
  classification: string | null;
  count: number;
};

type RtkAggregateRow = {
  eventCount: number;
  rawTokens: number;
  compressedTokens: number;
  tokensSaved: number;
  ambiguousFailures: number;
};

type RtkWorkflowRow = {
  key: string | null;
  tokens: number;
};

const normalizePeriod = (period: string | undefined): CostSummary["period"] => {
  if (period === "day" || period === "week" || period === "month") {
    return period;
  }

  return "week";
};

const byClassificationFromCounts = (
  totalTokens: number,
  rows: ClassificationCountRow[],
): CostBreakdownPoint[] => {
  const totalPrompts = rows.reduce((acc, row) => acc + row.count, 0);

  if (totalPrompts === 0 || totalTokens === 0) {
    return seededCostSummary.byClassification;
  }

  return rows
    .map((row): CostBreakdownPoint => {
      const ratio = row.count / totalPrompts;
      const label = row.classification ?? "other";

      return {
        key: label,
        label,
        tokens: Math.round(totalTokens * ratio),
      };
    })
    .sort((a, b) => b.tokens - a.tokens);
};

const readMetricTotal = (ctxDb: ReturnType<typeof import("@/server/db").getDb>): number => {
  if (!tableExists("workflow_metrics")) {
    return 0;
  }

  const row = ctxDb
    .prepare(
      `
      SELECT COALESCE(SUM(metric_value), 0) AS total
      FROM workflow_metrics
      WHERE LOWER(metric_name) LIKE '%token%'
    `,
    )
    .get() as { total: number };

  return Number.isFinite(row.total) ? Math.round(row.total) : 0;
};

const readProjectBreakdown = (ctxDb: ReturnType<typeof import("@/server/db").getDb>): BreakdownRow[] => {
  if (!tableExists("workflow_metrics") || !tableExists("sessions") || !tableExists("projects")) {
    return [];
  }

  return ctxDb
    .prepare(
      `
      SELECT
        p.id AS key,
        p.name AS label,
        CAST(COALESCE(SUM(wm.metric_value), 0) AS INTEGER) AS tokens
      FROM workflow_metrics wm
      INNER JOIN sessions s ON s.id = wm.session_id
      INNER JOIN projects p ON p.id = s.project_id
      WHERE LOWER(wm.metric_name) LIKE '%token%'
      GROUP BY p.id, p.name
      ORDER BY tokens DESC
    `,
    )
    .all() as BreakdownRow[];
};

const readToolBreakdown = (ctxDb: ReturnType<typeof import("@/server/db").getDb>): BreakdownRow[] => {
  if (!tableExists("workflow_metrics") || !tableExists("sessions")) {
    return [];
  }

  return ctxDb
    .prepare(
      `
      SELECT
        s.tool AS key,
        s.tool AS label,
        CAST(COALESCE(SUM(wm.metric_value), 0) AS INTEGER) AS tokens
      FROM workflow_metrics wm
      INNER JOIN sessions s ON s.id = wm.session_id
      WHERE LOWER(wm.metric_name) LIKE '%token%'
      GROUP BY s.tool
      ORDER BY tokens DESC
    `,
    )
    .all() as BreakdownRow[];
};

const readClassificationCounts = (
  ctxDb: ReturnType<typeof import("@/server/db").getDb>,
): ClassificationCountRow[] => {
  if (!tableExists("prompts_used")) {
    return [];
  }

  return ctxDb
    .prepare(
      `
      SELECT
        classification,
        COUNT(*) AS count
      FROM prompts_used
      GROUP BY classification
      ORDER BY count DESC
    `,
    )
    .all() as ClassificationCountRow[];
};

const readRtkSummary = (ctxDb: ReturnType<typeof import("@/server/db").getDb>): CostSummary["rtk"] => {
  if (!tableExists("rtk_compression_events")) {
    return seededCostSummary.rtk;
  }

  const aggregate = ctxDb
    .prepare(
      `
      SELECT
        COUNT(*) AS eventCount,
        CAST(COALESCE(SUM(estimated_raw_tokens), 0) AS INTEGER) AS rawTokens,
        CAST(COALESCE(SUM(estimated_compressed_tokens), 0) AS INTEGER) AS compressedTokens,
        CAST(COALESCE(SUM(MAX(estimated_raw_tokens - estimated_compressed_tokens, 0)), 0) AS INTEGER) AS tokensSaved,
        CAST(COALESCE(SUM(ambiguous_failure), 0) AS INTEGER) AS ambiguousFailures
      FROM rtk_compression_events
    `,
    )
    .get() as RtkAggregateRow;

  const rawTokens = Number(aggregate.rawTokens) || 0;
  const tokensSaved = Number(aggregate.tokensSaved) || 0;
  const byWorkflow = ctxDb
    .prepare(
      `
      SELECT
        COALESCE(workflow_key, 'unclassified') AS key,
        CAST(COALESCE(SUM(MAX(estimated_raw_tokens - estimated_compressed_tokens, 0)), 0) AS INTEGER) AS tokens
      FROM rtk_compression_events
      GROUP BY COALESCE(workflow_key, 'unclassified')
      ORDER BY tokens DESC
      LIMIT 8
    `,
    )
    .all() as RtkWorkflowRow[];

  return {
    eventCount: Number(aggregate.eventCount) || 0,
    rawTokens,
    compressedTokens: Number(aggregate.compressedTokens) || 0,
    tokensSaved,
    reductionPercent: rawTokens > 0 ? Math.round((tokensSaved / rawTokens) * 1000) / 10 : 0,
    ambiguousFailures: Number(aggregate.ambiguousFailures) || 0,
    byWorkflow: byWorkflow.map((row) => ({
      key: row.key ?? "unclassified",
      label: row.key ?? "unclassified",
      tokens: Number(row.tokens) || 0,
    })),
  };
};

export const costsRouter = createTRPCRouter({
  summary: publicProcedure
    .input(z.object({ period: z.enum(["day", "week", "month"]).optional() }).optional())
    .query(({ ctx, input }): CostSummary => {
      const totalTokens = readMetricTotal(ctx.db);

      if (totalTokens <= 0) {
        return {
          ...seededCostSummary,
          period: normalizePeriod(input?.period),
          rtk: readRtkSummary(ctx.db),
        };
      }

      const byProject = readProjectBreakdown(ctx.db);
      const byTool = readToolBreakdown(ctx.db);
      const byClassification = byClassificationFromCounts(totalTokens, readClassificationCounts(ctx.db));

      return {
        period: normalizePeriod(input?.period),
        totalTokens,
        byProject: byProject.length > 0 ? byProject : seededCostSummary.byProject,
        byClassification,
        byTool: byTool.length > 0 ? byTool : seededCostSummary.byTool,
        abandonedSessionTokens: Math.round(totalTokens * 0.11),
        failedRunTokens: Math.round(totalTokens * 0.06),
        rtk: readRtkSummary(ctx.db),
      };
    }),
});
