import { seededWorkflowMetrics } from "@/lib/seed";
import type { WorkflowMetric } from "@/lib/types";
import { tableExists } from "@/server/db";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

type WorkflowRow = {
  id: string;
  name: string;
  successRate: number;
  runs: number;
  avgTokens: number;
};

const clamp = (value: number): number => {
  if (value < 0) {
    return 0;
  }

  if (value > 1) {
    return 1;
  }

  return value;
};

export const workflowsRouter = createTRPCRouter({
  list: publicProcedure.query(({ ctx }): WorkflowMetric[] => {
    if (!tableExists("workflow_metrics")) {
      return seededWorkflowMetrics;
    }

    const rows = ctx.db
      .prepare(
        `
        SELECT
          metric_name AS name,
          metric_name AS id,
          COUNT(*) AS runs,
          AVG(metric_value) AS rawAverage,
          AVG(CASE WHEN LOWER(metric_name) LIKE '%token%' THEN metric_value END) AS avgTokens
        FROM workflow_metrics
        GROUP BY metric_name
        ORDER BY runs DESC
        LIMIT 12
      `,
      )
      .all() as Array<WorkflowRow & { rawAverage: number }>;

    if (rows.length === 0) {
      return seededWorkflowMetrics;
    }

    return rows.map((row): WorkflowMetric => ({
      id: row.id,
      name: row.name,
      runs: row.runs,
      successRate: clamp(row.rawAverage > 1 ? row.rawAverage / 100 : row.rawAverage),
      avgTokens: Number.isFinite(row.avgTokens) ? Math.round(row.avgTokens) : 0,
    }));
  }),
});
