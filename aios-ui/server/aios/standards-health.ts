import type Database from "better-sqlite3";

import type {
  StandardsBackfillTask,
  StandardsDeltaItem,
  StandardsDomainScore,
  StandardsHealthSummary,
  StandardsMigration,
} from "@/lib/control-plane";
import { ensureControlPlaneSchema } from "@/server/aios/schema";

type SnapshotRow = {
  id: string;
  profileId: string;
  attachedVersion: string;
  latestVersion: string;
  overallScore: number;
  weightedDelta: number;
  unmetStandardsCount: number;
  criticalDeltaCount: number;
  regressionCount: number;
  unknownCount: number;
  unknownCoverage: number;
  evaluationConfidence: number;
  domainScoresJson: string;
  migrationJson: string;
  createdAt: string;
};

type DeltaRow = {
  id: string;
  standardId: string;
  domain: string;
  severity: number;
  status: StandardsDeltaItem["status"];
  summary: string;
  estimatedHealthImpact: number;
  blockersJson: string;
  foundational: number;
  linkedTaskIdsJson: string;
  priorityScore: number;
  priorityBucket: StandardsDeltaItem["priorityBucket"];
};

type BackfillTaskRow = {
  id: string;
  deltaItemId: string;
  standardId: string;
  title: string;
  problemStatement: string;
  expectedState: string;
  acceptanceCriteriaJson: string;
  effort: number;
  dependencyChainJson: string;
  expectedHealthImpact: number;
  owner: string | null;
  blockedReason: string | null;
  dueAt: string | null;
  reviewAt: string | null;
  priorityScore: number;
  priorityBucket: StandardsDeltaItem["priorityBucket"];
  blocked: number;
  status: string;
};

const parseJsonArray = <T>(raw: string, fallback: T): T => {
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
};

const parseDomainScores = (raw: string): StandardsDomainScore[] => {
  const parsed = parseJsonArray<Record<string, { score?: number; confidence?: number; weight?: number }>>(raw, {});
  return Object.entries(parsed)
    .map(([domain, value]) => ({
      domain,
      score: Number(value?.score ?? 0),
      confidence: Number(value?.confidence ?? 0),
      weight: Number(value?.weight ?? 0),
    }))
    .sort((a, b) => b.weight - a.weight);
};

const parseMigration = (raw: string, attachedVersion: string, latestVersion: string): StandardsMigration => {
  const parsed = parseJsonArray<{
    attached_version?: string;
    latest_version?: string;
    migration_delta_count?: number;
    migration_weight?: number;
    items?: Array<{
      standard_id?: string;
      title?: string;
      domain?: string;
      introduced_version?: string;
      weight?: number;
    }>;
  }>(raw, {});

  return {
    attachedVersion: parsed.attached_version ?? attachedVersion,
    latestVersion: parsed.latest_version ?? latestVersion,
    migrationDeltaCount: Number(parsed.migration_delta_count ?? 0),
    migrationWeight: Number(parsed.migration_weight ?? 0),
    items: (parsed.items ?? []).map((item) => ({
      standardId: item.standard_id ?? "",
      title: item.title ?? "",
      domain: item.domain ?? "",
      introducedVersion: item.introduced_version ?? "",
      weight: Number(item.weight ?? 0),
    })),
  };
};

export const getProjectStandardsHealth = (
  db: Database.Database,
  projectId: string,
): StandardsHealthSummary | null => {
  ensureControlPlaneSchema(db);

  const snapshot = db
    .prepare(
      `
      SELECT
        id,
        profile_id AS profileId,
        attached_version AS attachedVersion,
        latest_version AS latestVersion,
        overall_score AS overallScore,
        weighted_delta AS weightedDelta,
        unmet_standards_count AS unmetStandardsCount,
        critical_delta_count AS criticalDeltaCount,
        regression_count AS regressionCount,
        unknown_count AS unknownCount,
        unknown_coverage AS unknownCoverage,
        evaluation_confidence AS evaluationConfidence,
        domain_scores_json AS domainScoresJson,
        migration_json AS migrationJson,
        created_at AS createdAt
      FROM standards_health_snapshots
      WHERE project_id = ?
      ORDER BY created_at DESC
      LIMIT 1
    `,
    )
    .get(projectId) as SnapshotRow | undefined;

  if (!snapshot) {
    return null;
  }

  const deltaRows = db
    .prepare(
      `
      SELECT
        id,
        standard_id AS standardId,
        domain,
        severity,
        status,
        summary,
        estimated_health_impact AS estimatedHealthImpact,
        blockers_json AS blockersJson,
        foundational,
        linked_task_ids_json AS linkedTaskIdsJson,
        priority_score AS priorityScore,
        priority_bucket AS priorityBucket
      FROM standards_delta_items
      WHERE snapshot_id = ?
      ORDER BY priority_score DESC, created_at DESC
      LIMIT 200
    `,
    )
    .all(snapshot.id) as DeltaRow[];

  const deltaItems: StandardsDeltaItem[] = deltaRows.map((row) => ({
    id: row.id,
    standardId: row.standardId,
    domain: row.domain,
    severity: row.severity,
    status: row.status,
    summary: row.summary,
    estimatedHealthImpact: Number(row.estimatedHealthImpact),
    blockers: parseJsonArray<string[]>(row.blockersJson, []),
    foundational: row.foundational === 1,
    linkedTaskIds: parseJsonArray<string[]>(row.linkedTaskIdsJson, []),
    priorityScore: Number(row.priorityScore),
    priorityBucket: row.priorityBucket,
  }));

  const backfillRows = db
    .prepare(
      `
      SELECT
        id,
        delta_item_id AS deltaItemId,
        standard_id AS standardId,
        title,
        problem_statement AS problemStatement,
        expected_state AS expectedState,
        acceptance_criteria_json AS acceptanceCriteriaJson,
        effort,
        dependency_chain_json AS dependencyChainJson,
        expected_health_impact AS expectedHealthImpact,
        owner,
        blocked_reason AS blockedReason,
        due_at AS dueAt,
        review_at AS reviewAt,
        priority_score AS priorityScore,
        priority_bucket AS priorityBucket,
        blocked,
        status
      FROM standards_backfill_tasks
      WHERE snapshot_id = ?
      ORDER BY priority_score DESC, updated_at DESC
      LIMIT 200
    `,
    )
    .all(snapshot.id) as BackfillTaskRow[];

  const backfillTasks: StandardsBackfillTask[] = backfillRows.map((row) => ({
    id: row.id,
    deltaItemId: row.deltaItemId,
    standardId: row.standardId,
    title: row.title,
    problemStatement: row.problemStatement,
    expectedState: row.expectedState,
    acceptanceCriteria: parseJsonArray<string[]>(row.acceptanceCriteriaJson, []),
    effort: Number(row.effort),
    dependencyChain: parseJsonArray<string[]>(row.dependencyChainJson, []),
    expectedHealthImpact: Number(row.expectedHealthImpact),
    owner: row.owner,
    blockedReason: row.blockedReason,
    dueAt: row.dueAt,
    reviewAt: row.reviewAt,
    priorityScore: Number(row.priorityScore),
    priorityBucket: row.priorityBucket,
    blocked: row.blocked === 1,
    status: row.status,
  }));

  return {
    snapshotId: snapshot.id,
    profileId: snapshot.profileId,
    attachedVersion: snapshot.attachedVersion,
    latestVersion: snapshot.latestVersion,
    overallScore: Number(snapshot.overallScore),
    weightedDelta: Number(snapshot.weightedDelta),
    unmetStandardsCount: Number(snapshot.unmetStandardsCount),
    criticalDeltaCount: Number(snapshot.criticalDeltaCount),
    regressionCount: Number(snapshot.regressionCount),
    unknownCount: Number(snapshot.unknownCount),
    unknownCoverage: Number(snapshot.unknownCoverage),
    evaluationConfidence: Number(snapshot.evaluationConfidence),
    createdAt: snapshot.createdAt,
    domainScores: parseDomainScores(snapshot.domainScoresJson),
    deltaItems,
    backfillTasks,
    migration: parseMigration(snapshot.migrationJson, snapshot.attachedVersion, snapshot.latestVersion),
  };
};

export const updateStandardsBackfillTask = (
  db: Database.Database,
  input: {
    taskId: string;
    owner?: string | null;
    status?: string;
    priorityBucket?: StandardsBackfillTask["priorityBucket"];
    blocked?: boolean;
    blockedReason?: string | null;
    dueAt?: string | null;
    reviewAt?: string | null;
  },
): StandardsBackfillTask => {
  ensureControlPlaneSchema(db);
  const current = db
    .prepare(
      `
      SELECT project_id AS projectId, snapshot_id AS snapshotId
      FROM standards_backfill_tasks
      WHERE id = ?
      LIMIT 1
    `,
    )
    .get(input.taskId) as { projectId: string; snapshotId: string } | undefined;

  if (!current) {
    throw new Error("Standards backfill task not found.");
  }

  const updates: string[] = [];
  const values: Array<string | number | null> = [];
  const setIfPresent = (column: string, value: string | number | null | undefined): void => {
    if (value === undefined) {
      return;
    }
    updates.push(`${column} = ?`);
    values.push(value);
  };

  setIfPresent("owner", input.owner ?? undefined);
  setIfPresent("status", input.status);
  setIfPresent("priority_bucket", input.priorityBucket);
  setIfPresent("blocked", input.blocked === undefined ? undefined : input.blocked ? 1 : 0);
  setIfPresent("blocked_reason", input.blockedReason ?? undefined);
  setIfPresent("due_at", input.dueAt ?? undefined);
  setIfPresent("review_at", input.reviewAt ?? undefined);
  updates.push("updated_at = ?");
  values.push(new Date().toISOString());
  values.push(input.taskId);

  db.prepare(`UPDATE standards_backfill_tasks SET ${updates.join(", ")} WHERE id = ?`).run(...values);

  const summary = getProjectStandardsHealth(db, current.projectId);
  const task = summary?.backfillTasks.find((candidate) => candidate.id === input.taskId);
  if (!task) {
    throw new Error("Standards backfill task was updated but could not be reloaded.");
  }
  return task;
};
