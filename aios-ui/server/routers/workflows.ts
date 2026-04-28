import { readFileSync } from "node:fs";
import { join } from "node:path";

import { z } from "zod";

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
  workflowSpecJson: string;
  createdAt: string;
};

export type WorkflowStage = {
  key: string;
  kind: string;
  required_skills: string[];
  best_practices?: string[];
  notes?: string;
};

export type WorkflowProposalDetail = WorkflowProposalSummary & {
  stages: WorkflowStage[];
  workflowSpec: Record<string, unknown>;
};

const SKILLS_PATH = join(process.cwd(), "..", "config", "workflows", "skills.json");

const loadSkillKeys = (): string[] => {
  try {
    const raw = readFileSync(SKILLS_PATH, "utf8");
    const parsed = JSON.parse(raw) as { skills?: Array<{ key: string }> };
    return (parsed.skills ?? []).map((s) => s.key);
  } catch {
    return [];
  }
};

const parseWorkflowSpec = (raw: string): { stages: WorkflowStage[]; spec: Record<string, unknown> } => {
  try {
    const spec = JSON.parse(raw) as Record<string, unknown>;
    const rawStages = Array.isArray(spec.stages) ? spec.stages : [];
    const stages: WorkflowStage[] = rawStages.map((s: unknown) => {
      const stage = s as Record<string, unknown>;
      return {
        key: String(stage.key ?? ""),
        kind: String(stage.kind ?? ""),
        required_skills: Array.isArray(stage.required_skills)
          ? (stage.required_skills as unknown[]).map(String)
          : [],
        best_practices: Array.isArray(stage.best_practices)
          ? (stage.best_practices as unknown[]).map(String)
          : undefined,
        notes: typeof stage.notes === "string" ? stage.notes : undefined,
      };
    });
    return { stages, spec };
  } catch {
    return { stages: [], spec: {} };
  }
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
  skillKeys: publicProcedure.query((): string[] => loadSkillKeys()),

  detail: publicProcedure
    .input(z.object({ id: z.string().min(1) }))
    .query(({ ctx, input }): WorkflowProposalDetail | null => {
      if (!tableExists("workflow_synthesis_proposals")) {
        return null;
      }
      const row = ctx.db
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
            workflow_spec_json AS workflowSpecJson,
            created_at AS createdAt
          FROM workflow_synthesis_proposals
          WHERE id = ?
          LIMIT 1
        `,
        )
        .get(input.id) as WorkflowProposalRow | undefined;
      if (!row) return null;
      const { stages, spec } = parseWorkflowSpec(row.workflowSpecJson);
      return {
        id: row.id,
        proposalKey: row.proposalKey,
        title: row.title,
        summary: row.summary,
        status: row.status,
        sourcePatternIds: parseStringArray(row.sourcePatternIdsJson),
        evidence: parseStringArray(row.evidenceJson),
        createdAt: row.createdAt,
        stages,
        workflowSpec: spec,
      };
    }),

  updateStages: publicProcedure
    .input(
      z.object({
        id: z.string().min(1),
        stages: z.array(
          z.object({
            key: z.string().min(1),
            kind: z.string().min(1),
            required_skills: z.array(z.string()),
            best_practices: z.array(z.string()).optional(),
            notes: z.string().optional(),
          }),
        ),
      }),
    )
    .mutation(({ ctx, input }): { ok: boolean } => {
      if (!tableExists("workflow_synthesis_proposals")) {
        return { ok: false };
      }
      const row = ctx.db
        .prepare("SELECT workflow_spec_json FROM workflow_synthesis_proposals WHERE id = ? LIMIT 1")
        .get(input.id) as { workflow_spec_json: string } | undefined;
      if (!row) return { ok: false };
      let spec: Record<string, unknown> = {};
      try {
        spec = JSON.parse(row.workflow_spec_json) as Record<string, unknown>;
      } catch {
        spec = {};
      }
      spec.stages = input.stages;
      const updated = JSON.stringify(spec);
      ctx.db
        .prepare(
          `UPDATE workflow_synthesis_proposals
           SET workflow_spec_json = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
           WHERE id = ?`,
        )
        .run(updated, input.id);
      return { ok: true };
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
