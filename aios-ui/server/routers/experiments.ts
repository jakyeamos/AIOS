import fs from "node:fs";
import path from "node:path";

import type { Experiment, ExperimentTestRepo } from "@/lib/types";
import { tableExists } from "@/server/db";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

type ExperimentRow = {
  id: string;
  name: string;
  surface: string;
  hypothesis: string;
  baselineValue: number | null;
  challengerValue: number | null;
  verdict: string | null;
  startedAt: string;
  endedAt: string | null;
  notes: string | null;
};

type ExperimentTestRepoConfig = {
  test_repos?: Array<{
    id?: unknown;
    name?: unknown;
    profile?: unknown;
    repo_path?: unknown;
    purpose?: unknown;
    setup?: unknown;
    experiment_uses?: unknown;
  }>;
};

type WorkflowSkillExperimentRow = {
  id: string;
  workflowKey: string;
  skillKey: string;
  testRepoId: string;
  branchName: string;
  status: string;
  outcome: string | null;
  createdAt: string;
};

export type WorkflowSkillExperiment = {
  id: string;
  workflowKey: string;
  skillKey: string;
  testRepoId: string;
  branchName: string;
  status: string;
  outcome: string | null;
  createdAt: string;
};

const getAiosRoot = (): string => {
  return process.env.AIOS_ROOT ?? "/Users/jakyeamos/AIOS";
};

const mapExperiment = (row: ExperimentRow): Experiment => {
  const baseline = row.baselineValue;
  const challenger = row.challengerValue;
  const delta = baseline !== null && challenger !== null ? challenger - baseline : null;
  const winner =
    delta === null
      ? null
      : delta > 0
        ? "challenger"
        : delta < 0
          ? "baseline"
          : "inconclusive";

  return {
    id: row.id,
    name: row.name,
    surface: row.surface,
    hypothesis: row.hypothesis,
    baselineValue: row.baselineValue,
    challengerValue: row.challengerValue,
    verdict: row.verdict,
    startedAt: row.startedAt,
    endedAt: row.endedAt,
    notes: row.notes,
    delta,
    winner,
  };
};

export const experimentsRouter = createTRPCRouter({
  testRepos: publicProcedure.query((): ExperimentTestRepo[] => {
    const aiosRoot = getAiosRoot();
    const configPath = path.join(aiosRoot, "config", "experiments", "test-repos.json");
    if (!fs.existsSync(configPath)) {
      return [];
    }

    const config = JSON.parse(fs.readFileSync(configPath, "utf8")) as ExperimentTestRepoConfig;
    return (config.test_repos ?? []).map((repo) => {
      const repoPath = typeof repo.repo_path === "string" ? path.resolve(aiosRoot, repo.repo_path) : "";
      const status = repoPath.length === 0 ? "missing" : fs.existsSync(path.join(repoPath, ".git")) ? "ready" : "missing";

      return {
        id: typeof repo.id === "string" ? repo.id : "unknown",
        name: typeof repo.name === "string" ? repo.name : "Unnamed repo",
        profile: typeof repo.profile === "string" ? repo.profile : "unknown",
        repoPath,
        status,
        purpose: typeof repo.purpose === "string" ? repo.purpose : "",
        setup: typeof repo.setup === "string" ? repo.setup : "",
        experimentUses: Array.isArray(repo.experiment_uses)
          ? repo.experiment_uses.filter((item): item is string => typeof item === "string")
          : [],
      };
    });
  }),

  list: publicProcedure.query(({ ctx }): Experiment[] => {
    if (!tableExists("experiments")) {
      return [];
    }

    const rows = ctx.db
      .prepare(
        `
        SELECT
          id,
          name,
          surface,
          hypothesis,
          baseline_value AS baselineValue,
          challenger_value AS challengerValue,
          verdict,
          started_at AS startedAt,
          ended_at AS endedAt,
          notes
        FROM experiments
        ORDER BY started_at DESC
      `,
      )
      .all() as ExperimentRow[];

    return rows.map(mapExperiment);
  }),

  workflowSkillExperiments: publicProcedure.query(({ ctx }): WorkflowSkillExperiment[] => {
    if (!tableExists("workflow_skill_experiments")) {
      return [];
    }

    const rows = ctx.db
      .prepare(
        `
        SELECT
          id,
          workflow_key AS workflowKey,
          skill_key AS skillKey,
          test_repo_id AS testRepoId,
          branch_name AS branchName,
          status,
          outcome,
          created_at AS createdAt
        FROM workflow_skill_experiments
        ORDER BY created_at DESC, workflow_key, test_repo_id
      `,
      )
      .all() as WorkflowSkillExperimentRow[];

    return rows.map((row) => ({
      id: row.id,
      workflowKey: row.workflowKey,
      skillKey: row.skillKey,
      testRepoId: row.testRepoId,
      branchName: row.branchName,
      status: row.status,
      outcome: row.outcome,
      createdAt: row.createdAt,
    }));
  }),
});
