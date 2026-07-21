import { execFileSync } from "node:child_process";
import os from "node:os";
import path from "node:path";

import type { StandardsBackfillTask } from "@/lib/control-plane";
import { backfillTaskPath } from "@/lib/drill-down";
import { resolveAiosRoot } from "@/server/aios/filesystem";

export type StandardsBackfillTaskUpdateInput = {
  taskId: string;
  owner?: string | null;
  status?: string;
  priorityBucket?: StandardsBackfillTask["priorityBucket"];
  blocked?: boolean;
  blockedReason?: string | null;
  dueAt?: string | null;
  reviewAt?: string | null;
};

type PythonBackfillTask = {
  id: string;
  project_id: string;
  snapshot_id: string;
  delta_item_id: string;
  standard_id: string;
  title: string;
  problem_statement: string;
  expected_state: string;
  acceptance_criteria_json: string;
  effort: number;
  dependency_chain_json: string;
  expected_health_impact: number;
  owner: string | null;
  blocked_reason: string | null;
  due_at: string | null;
  review_at: string | null;
  priority_score: number;
  priority_bucket: StandardsBackfillTask["priorityBucket"];
  blocked: boolean;
  status: string;
  updated_at: string;
};

type PythonEnvelope = {
  data?: PythonBackfillTask;
  error?: { message?: string };
};

const resolveDbPath = (): string => {
  const configuredPath = process.env.AIOS_DB?.trim();
  if (!configuredPath) {
    return path.join(os.homedir(), "AIOS", "data", "aios.db");
  }
  if (configuredPath === "~") {
    return os.homedir();
  }
  if (configuredPath.startsWith("~/")) {
    return path.join(os.homedir(), configuredPath.slice(2));
  }
  return path.resolve(configuredPath);
};

const parseStringArray = (raw: string): string[] => {
  try {
    const value: unknown = JSON.parse(raw);
    return Array.isArray(value) && value.every((item) => typeof item === "string")
      ? value
      : [];
  } catch {
    return [];
  }
};

const toBackfillTask = (task: PythonBackfillTask): StandardsBackfillTask => ({
  id: task.id,
  deltaItemId: task.delta_item_id,
  standardId: task.standard_id,
  title: task.title,
  problemStatement: task.problem_statement,
  expectedState: task.expected_state,
  acceptanceCriteria: parseStringArray(task.acceptance_criteria_json),
  effort: task.effort,
  dependencyChain: parseStringArray(task.dependency_chain_json),
  expectedHealthImpact: task.expected_health_impact,
  owner: task.owner,
  blockedReason: task.blocked_reason,
  dueAt: task.due_at,
  reviewAt: task.review_at,
  priorityScore: task.priority_score,
  priorityBucket: task.priority_bucket,
  blocked: task.blocked,
  status: task.status,
  drillDownPath: backfillTaskPath(task.project_id, task.id),
});

export const updateStandardsBackfillTaskViaPythonOwner = (
  input: StandardsBackfillTaskUpdateInput,
): StandardsBackfillTask => {
  const root = resolveAiosRoot();
  const script = path.join(root, "bin", "aios.py");
  try {
    const output = execFileSync(
      "python3",
      [
        script,
        "--json",
        "--db",
        resolveDbPath(),
        "standards-backfill-update",
        "--payload-json",
        JSON.stringify(input),
      ],
      {
        cwd: root,
        encoding: "utf8",
        maxBuffer: 1024 * 1024,
      },
    );
    const envelope = JSON.parse(output) as PythonEnvelope;
    if (!envelope.data) {
      throw new Error(envelope.error?.message ?? "Python owner returned no task payload.");
    }
    return toBackfillTask(envelope.data);
  } catch (error) {
    if (error instanceof Error && error.message.startsWith("Python owner returned")) {
      throw error;
    }
    throw new Error("Python standards owner rejected the backfill task mutation.", {
      cause: error,
    });
  }
};
