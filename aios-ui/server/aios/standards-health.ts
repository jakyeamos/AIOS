import type Database from "better-sqlite3";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import type {
  DeltaExplanation,
  RecommendedWorkflow,
  StandardsAssessmentStatus,
  StandardsBackfillTask,
  StandardsDeltaItem,
  StandardsDomainScore,
  StandardsHealthSummary,
  StandardsMigration,
} from "@/lib/control-plane";
import { backfillTaskPath, deltaItemPath, workflowPath } from "@/lib/drill-down";
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

type AssessmentExplanationRow = {
  standardId: string;
  status: StandardsAssessmentStatus;
  measuredStateJson: string;
  reason: string | null;
  evidenceJson: string;
  lastEvaluatedAt: string;
  evaluatorType: string;
  confidence: number;
  expectedStateJson: string;
  definitionExpectedStateJson: string;
  definitionRemediationPlaybookJson: string;
  relatedCriteriaJson: string;
  definitionEvaluationMethod: string;
  domain: string;
  remediationPlaybookJson: string | null;
  priorityScore: number | null;
  priorityBucket: StandardsDeltaItem["priorityBucket"] | null;
};

type WorkflowRegistryFile = {
  workflows?: Array<{
    key?: string;
  }>;
};

const parseJsonArray = <T>(raw: string, fallback: T): T => {
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
};

const tableExists = (db: Database.Database, tableName: string): boolean => {
  const row = db
    .prepare("SELECT 1 FROM sqlite_master WHERE type='table' AND name = ? LIMIT 1")
    .get(tableName) as { 1: number } | undefined;
  return row !== undefined;
};

const getLatestSnapshot = (db: Database.Database, projectId: string): SnapshotRow | undefined =>
  db
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

const recentFindingsByCriterion = (db: Database.Database, projectId: string): Record<string, number> => {
  const counts: Record<string, number> = {};
  if (tableExists(db, "success_criteria_findings") && tableExists(db, "success_criteria_evaluations")) {
    const rows = db
      .prepare(
        `
        SELECT f.criterion_id AS criterionId, COUNT(*) AS count
        FROM success_criteria_findings f
        INNER JOIN success_criteria_evaluations e ON e.id = f.evaluation_id
        WHERE e.project_id = ?
          AND COALESCE(f.resolution_status, 'open') = 'open'
          AND f.level IN ('warning', 'blocker')
          AND f.created_at >= datetime('now', '-14 days')
        GROUP BY f.criterion_id
      `,
      )
      .all(projectId) as Array<{ criterionId: string; count: number }>;
    for (const row of rows) {
      counts[row.criterionId] = (counts[row.criterionId] ?? 0) + Number(row.count);
    }
  }
  return counts;
};

const detectContradiction = (
  status: StandardsAssessmentStatus,
  confidence: number,
  relatedCriteria: string[],
  findingsByCriterion: Record<string, number>,
): string | null => {
  for (const criterionId of relatedCriteria) {
    const blockers = Number(findingsByCriterion[criterionId] ?? 0);
    if (status === "pass" && blockers > 0) {
      return `Standard reports pass but ${blockers} open finding(s) exist on related criterion '${criterionId}'.`;
    }
    if (status === "fail" && blockers === 0 && confidence < 0.5) {
      return `Standard reports fail with low confidence (${confidence}) but no findings recorded on related criterion '${criterionId}'.`;
    }
  }
  return null;
};

const classifyProvenance = (
  status: StandardsAssessmentStatus,
  confidence: number,
  evidence: string[],
  evaluatorType: string,
  contradiction: string | null,
): DeltaExplanation["provenance"] => {
  if (status === "unknown" || evidence.length === 0) {
    return "missing";
  }
  if (contradiction) {
    return "contradictory";
  }
  if (evaluatorType === "auto" && confidence >= 0.75) {
    return "confirmed";
  }
  return "inferred";
};

const buildDeltaExplanations = (
  db: Database.Database,
  snapshotId: string,
  projectId: string,
): DeltaExplanation[] => {
  const findingsByCriterion = recentFindingsByCriterion(db, projectId);
  const rows = db
    .prepare(
      `
      SELECT
        a.standard_id AS standardId,
        a.status,
        a.measured_state_json AS measuredStateJson,
        a.reason,
        a.evidence_json AS evidenceJson,
        a.last_evaluated_at AS lastEvaluatedAt,
        a.evaluator_type AS evaluatorType,
        a.confidence,
        a.expected_state_snapshot_json AS expectedStateJson,
        dfn.expected_state_json AS definitionExpectedStateJson,
        dfn.remediation_playbook_json AS definitionRemediationPlaybookJson,
        dfn.related_criteria_json AS relatedCriteriaJson,
        dfn.evaluation_method AS definitionEvaluationMethod,
        dfn.domain,
        di.remediation_playbook_json AS remediationPlaybookJson,
        di.priority_score AS priorityScore,
        di.priority_bucket AS priorityBucket
      FROM standards_assessments a
      INNER JOIN standards_definitions dfn
        ON dfn.standard_id = a.standard_id AND dfn.profile_id = a.profile_id AND dfn.version = a.standard_version
      LEFT JOIN standards_delta_items di
        ON di.snapshot_id = a.snapshot_id AND di.standard_id = a.standard_id
      WHERE a.snapshot_id = ?
      ORDER BY COALESCE(di.priority_score, 0) DESC, a.standard_id ASC
    `,
    )
    .all(snapshotId) as AssessmentExplanationRow[];

  return rows.map((row) => {
    const evidence = parseJsonArray<string[]>(row.evidenceJson, []);
    const relatedCriteria = parseJsonArray<string[]>(row.relatedCriteriaJson, []);
    const confidence = Number(row.confidence);
    const contradiction = detectContradiction(row.status, confidence, relatedCriteria, findingsByCriterion);
    const remediation = parseJsonArray<Record<string, unknown>>(
      row.remediationPlaybookJson ?? row.definitionRemediationPlaybookJson,
      {},
    );
    return {
      standardId: row.standardId,
      domain: row.domain,
      status: row.status,
      provenance: classifyProvenance(row.status, confidence, evidence, row.evaluatorType, contradiction),
      confidence,
      freshness: row.lastEvaluatedAt,
      evidence,
      contradiction,
      remediationSummary: String(remediation.summary ?? ""),
      remediationEffort: Number(remediation.effort ?? 1),
      remediationLeverage: Number(remediation.leverage ?? 1),
      priorityScore: Number(row.priorityScore ?? 0),
      priorityBucket: row.priorityBucket ?? "high_leverage",
      measuredState: parseJsonArray<Record<string, unknown>>(row.measuredStateJson, {}),
      expectedState: parseJsonArray<Record<string, unknown>>(
        row.expectedStateJson || row.definitionExpectedStateJson,
        {},
      ),
      reason: row.reason ?? "",
    };
  });
};

const loadWorkflowRegistryKeys = (): Set<string> => {
  const registryPath = resolve(process.cwd(), "config/workflows/registry.json");
  if (!existsSync(registryPath)) {
    return new Set();
  }
  try {
    const parsed = JSON.parse(readFileSync(registryPath, "utf8")) as WorkflowRegistryFile;
    return new Set((parsed.workflows ?? []).map((workflow) => workflow.key ?? "").filter(Boolean));
  } catch {
    return new Set();
  }
};

const workflowForDelta = (delta: StandardsDeltaItem): { workflowKey: string; rationale: string } | null => {
  if (delta.priorityBucket === "blocked" && delta.domain === "workflow_agent_control") {
    return {
      workflowKey: "failure-recovery",
      rationale: "Critical workflow-handshake blocker - recover handshake integrity before other work.",
    };
  }
  if (delta.domain === "security" && (delta.status === "fail" || delta.status === "partial")) {
    return {
      workflowKey: "security review",
      rationale: "Security domain has open delta - focused security review before broader work.",
    };
  }
  if (delta.domain === "architecture" && delta.status === "fail") {
    return {
      workflowKey: "codebase architecture review",
      rationale: "Architecture boundary failure - review before remediation work compounds.",
    };
  }
  if (delta.priorityBucket === "foundational" || delta.priorityBucket === "high_leverage") {
    return {
      workflowKey: "standards backfill",
      rationale: "Highest-leverage standards gap - backfill workflow targets foundational deltas.",
    };
  }
  if (delta.priorityBucket === "quick_wins") {
    return {
      workflowKey: "implementation-delivery",
      rationale: "Quick-win standards gap - implementation-delivery covers low-effort fixes.",
    };
  }
  return null;
};

const buildRecommendedWorkflows = (deltaItems: StandardsDeltaItem[]): RecommendedWorkflow[] => {
  const registryKeys = loadWorkflowRegistryKeys();
  const seen = new Set<string>();
  const recommendations: RecommendedWorkflow[] = [];
  for (const delta of [...deltaItems].sort((a, b) => b.priorityScore - a.priorityScore)) {
    const match = workflowForDelta(delta);
    if (!match || seen.has(match.workflowKey)) {
      continue;
    }
    seen.add(match.workflowKey);
    recommendations.push({
      workflowKey: match.workflowKey,
      rationale: match.rationale,
      availableInRegistry: registryKeys.has(match.workflowKey),
      requiresApproval: true,
      impactScope: "workflow-default",
      policyClass: "workflow-default_change",
      triggeredBy: {
        standardId: delta.standardId,
        domain: delta.domain,
        priorityBucket: delta.priorityBucket,
        priorityScore: delta.priorityScore,
      },
      drillDownPath: workflowPath(match.workflowKey),
    });
    if (recommendations.length >= 5) {
      break;
    }
  }
  return recommendations;
};

export const getProjectStandardsHealth = (
  db: Database.Database,
  projectId: string,
): StandardsHealthSummary | null => {
  ensureControlPlaneSchema(db);

  const snapshot = getLatestSnapshot(db, projectId);

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
    drillDownPath: deltaItemPath(projectId, row.id),
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
    drillDownPath: backfillTaskPath(projectId, row.id),
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
    deltaExplanations: buildDeltaExplanations(db, snapshot.id, projectId),
    recommendedWorkflows: buildRecommendedWorkflows(deltaItems),
    migration: parseMigration(snapshot.migrationJson, snapshot.attachedVersion, snapshot.latestVersion),
  };
};

export const getProjectDeltaExplanations = (
  db: Database.Database,
  projectId: string,
): DeltaExplanation[] => {
  ensureControlPlaneSchema(db);
  const snapshot = getLatestSnapshot(db, projectId);
  if (!snapshot) {
    return [];
  }
  return buildDeltaExplanations(db, snapshot.id, projectId);
};

export const getRecommendedWorkflowsFromHealth = (
  db: Database.Database,
  projectId: string,
): RecommendedWorkflow[] => {
  const summary = getProjectStandardsHealth(db, projectId);
  return summary?.recommendedWorkflows ?? [];
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
