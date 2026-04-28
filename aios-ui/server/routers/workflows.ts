import { readFileSync, writeFileSync } from "node:fs";
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

export type ApprovedWorkflowSummary = {
  id: string;
  key: string;
  name: string;
  purpose: string;
  stageCount: number;
  validationCount: number;
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

type WorkflowRegistry = {
  workflows?: Array<Record<string, unknown>>;
};

const REGISTRY_PATH = join(process.cwd(), "..", "config", "workflows", "registry.json");
const SKILLS_PATH = join(process.cwd(), "..", "config", "workflows", "skills.json");

const loadWorkflowRegistry = (): WorkflowRegistry => {
  try {
    return JSON.parse(readFileSync(REGISTRY_PATH, "utf8")) as WorkflowRegistry;
  } catch {
    return { workflows: [] };
  }
};

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

export type GitHubSkillCandidate = {
  id: string;
  workflowKey: string;
  skillKey: string;
  name: string;
  githubUrl: string;
  repo: string;
  path: string | null;
  summary: string;
  tags: string[];
  detail: Record<string, unknown>;
  status: string;
  createdAt: string;
};

type GitHubSkillCandidateRow = {
  id: string;
  workflowKey: string;
  skillKey: string;
  name: string;
  githubUrl: string;
  repo: string;
  path: string | null;
  summary: string;
  tagsJson: string;
  detailJson: string;
  status: string;
  createdAt: string;
};

const mapCandidate = (row: GitHubSkillCandidateRow): GitHubSkillCandidate => {
  let tags: string[] = [];
  let detail: Record<string, unknown> = {};
  try { tags = JSON.parse(row.tagsJson) as string[]; } catch { /* empty */ }
  try { detail = JSON.parse(row.detailJson) as Record<string, unknown>; } catch { /* empty */ }
  return {
    id: row.id,
    workflowKey: row.workflowKey,
    skillKey: row.skillKey,
    name: row.name,
    githubUrl: row.githubUrl,
    repo: row.repo,
    path: row.path,
    summary: row.summary,
    tags,
    detail,
    status: row.status,
    createdAt: row.createdAt,
  };
};

const stagesFromSpec = (spec: Record<string, unknown>): WorkflowStage[] => {
  const rawStages = Array.isArray(spec.stages) ? spec.stages : [];
  return rawStages.map((s: unknown) => {
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

  approved: publicProcedure.query((): ApprovedWorkflowSummary[] => {
    const registry = loadWorkflowRegistry();
    return (registry.workflows ?? []).map((workflow) => {
      const key = String(workflow.key ?? "");
      const stages = Array.isArray(workflow.stages) ? workflow.stages : [];
      const validations = Array.isArray(workflow.required_validations) ? workflow.required_validations : [];

      return {
        id: key,
        key,
        name: String(workflow.name ?? key),
        purpose: String(workflow.purpose ?? ""),
        stageCount: stages.length,
        validationCount: validations.length,
      };
    });
  }),

  detail: publicProcedure
    .input(z.object({ id: z.string().min(1) }))
    .query(({ input }): WorkflowProposalDetail | null => {
      const registry = loadWorkflowRegistry();
      const workflow = (registry.workflows ?? []).find((item) => item.key === input.id);
      if (!workflow) return null;
      const key = String(workflow.key ?? input.id);

      return {
        id: key,
        proposalKey: key,
        title: String(workflow.name ?? key),
        summary: String(workflow.purpose ?? ""),
        status: "approved",
        sourcePatternIds: [],
        evidence: Array.isArray(workflow.trigger_hints) ? (workflow.trigger_hints as unknown[]).map(String) : [],
        createdAt: "",
        stages: stagesFromSpec(workflow),
        workflowSpec: workflow,
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
    .mutation(({ input }): { ok: boolean } => {
      const registry = loadWorkflowRegistry();
      const workflows = registry.workflows ?? [];
      const workflow = workflows.find((item) => item.key === input.id);
      if (!workflow) return { ok: false };

      workflow.stages = input.stages;
      writeFileSync(REGISTRY_PATH, `${JSON.stringify(registry, null, 2)}\n`);
      return { ok: true };
    }),

  skillCandidates: publicProcedure
    .input(z.object({ workflowKey: z.string().optional() }).optional())
    .query(({ ctx, input }): GitHubSkillCandidate[] => {
      if (!tableExists("github_skill_candidates")) return [];
      const rows = input?.workflowKey
        ? (ctx.db
            .prepare(
              `SELECT id, workflow_key AS workflowKey, skill_key AS skillKey, name,
                      github_url AS githubUrl, repo, path, summary, tags_json AS tagsJson,
                      detail_json AS detailJson, status, created_at AS createdAt
               FROM github_skill_candidates
               WHERE status = 'candidate' AND workflow_key = ?
               ORDER BY created_at DESC LIMIT 40`,
            )
            .all(input.workflowKey) as GitHubSkillCandidateRow[])
        : (ctx.db
            .prepare(
              `SELECT id, workflow_key AS workflowKey, skill_key AS skillKey, name,
                      github_url AS githubUrl, repo, path, summary, tags_json AS tagsJson,
                      detail_json AS detailJson, status, created_at AS createdAt
               FROM github_skill_candidates
               WHERE status = 'candidate'
               ORDER BY created_at DESC LIMIT 60`,
            )
            .all() as GitHubSkillCandidateRow[]);
      return rows.map(mapCandidate);
    }),

  promoteSkill: publicProcedure
    .input(z.object({ id: z.string().min(1) }))
    .mutation(({ ctx, input }): { ok: boolean; skillKey: string } => {
      if (!tableExists("github_skill_candidates")) return { ok: false, skillKey: "" };
      const row = ctx.db
        .prepare(
          `SELECT skill_key AS skillKey, name, summary, tags_json AS tagsJson, detail_json AS detailJson
           FROM github_skill_candidates WHERE id = ? LIMIT 1`,
        )
        .get(input.id) as { skillKey: string; name: string; summary: string; tagsJson: string; detailJson: string } | undefined;
      if (!row) return { ok: false, skillKey: "" };

      let detail: Record<string, unknown> = {};
      try { detail = JSON.parse(row.detailJson) as Record<string, unknown>; } catch { /* empty */ }
      let tags: string[] = [];
      try { tags = JSON.parse(row.tagsJson) as string[]; } catch { /* empty */ }

      const newSkill = {
        key: row.skillKey,
        purpose: row.summary,
        allowed_stages: tags,
        input_schema: {},
        output_schema: {},
        invariants: (detail.invariants as string[] | undefined) ?? [],
        failure_conditions: (detail.failure_conditions as string[] | undefined) ?? [],
        side_effects: [],
        execution_mode: (detail.execution_mode as string | undefined) ?? "heuristic",
      };

      try {
        const existing = JSON.parse(readFileSync(SKILLS_PATH, "utf8")) as { skills: unknown[] };
        const skills = existing.skills ?? [];
        if (!skills.some((s) => (s as { key?: string }).key === row.skillKey)) {
          skills.push(newSkill);
          writeFileSync(SKILLS_PATH, `${JSON.stringify({ ...existing, skills }, null, 2)}\n`);
        }
      } catch { /* skills.json missing or malformed — skip file write */ }

      ctx.db
        .prepare(
          `UPDATE github_skill_candidates SET status = 'promoted',
           updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id = ?`,
        )
        .run(input.id);
      return { ok: true, skillKey: row.skillKey };
    }),

  dismissSkill: publicProcedure
    .input(z.object({ id: z.string().min(1) }))
    .mutation(({ ctx, input }): { ok: boolean } => {
      if (!tableExists("github_skill_candidates")) return { ok: false };
      ctx.db
        .prepare(
          `UPDATE github_skill_candidates SET status = 'dismissed',
           updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id = ?`,
        )
        .run(input.id);
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
        WHERE status != 'discarded'
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
