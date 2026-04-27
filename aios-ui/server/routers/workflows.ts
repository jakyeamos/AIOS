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

export type WorkflowProposalSummary = {
  id: string;
  proposalKey: string;
  title: string;
  summary: string;
  status: string;
  sourcePatternIds: string[];
  evidence: string[];
  createdAt: string;
};

type WorkflowProposalRow = {
  id: string;
  proposalKey: string;
  title: string;
  summary: string;
  status: string;
  sourcePatternIdsJson: string;
  evidenceJson: string;
  createdAt: string;
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

const parseStringArray = (raw: string): string[] => {
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed.filter((item): item is string => typeof item === "string");
  } catch {
    return [];
  }
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
  proposals: publicProcedure.query(({ ctx }): WorkflowProposalSummary[] => {
    if (!tableExists("workflow_synthesis_proposals")) {
      return [];
    }

    const rows = ctx.db
      .prepare(
        `
        SELECT
          id,
          proposal_key AS proposalKey,
          title,
          summary,
          status,
          source_pattern_ids_json AS sourcePatternIdsJson,
          evidence_json AS evidenceJson,
          created_at AS createdAt
        FROM workflow_synthesis_proposals
        ORDER BY
          CASE status
            WHEN 'pending_approval' THEN 0
            WHEN 'approved' THEN 1
            ELSE 2
          END,
          created_at DESC
        LIMIT 40
      `,
      )
      .all() as WorkflowProposalRow[];

    return rows.map(
      (row): WorkflowProposalSummary => ({
        id: row.id,
        proposalKey: row.proposalKey,
        title: row.title,
        summary: row.summary,
        status: row.status,
        sourcePatternIds: parseStringArray(row.sourcePatternIdsJson),
        evidence: parseStringArray(row.evidenceJson),
        createdAt: row.createdAt,
      }),
    );
  }),
});
