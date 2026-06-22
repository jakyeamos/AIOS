import type Database from "better-sqlite3";

import type { EvalRun, EvalSummary, ShadowCandidate } from "@/lib/control-plane";

type Row = Record<string, unknown>;

const tableExists = (db: Database.Database, tableName: string): boolean => {
  const row = db
    .prepare("SELECT name FROM sqlite_master WHERE type='table' AND name=? LIMIT 1")
    .get(tableName) as { name: string } | undefined;
  return row !== undefined;
};

const text = (value: unknown): string => (value === null || value === undefined ? "" : String(value));

const nullableText = (value: unknown): string | null => {
  const valueText = text(value);
  return valueText.length > 0 ? valueText : null;
};

const numberOrNull = (value: unknown): number | null => {
  if (value === null || value === undefined) return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
};

const jsonList = (value: unknown): string[] => {
  if (!value) return [];
  try {
    const parsed = JSON.parse(String(value)) as unknown;
    return Array.isArray(parsed) ? parsed.map((item) => String(item)) : [];
  } catch {
    return [];
  }
};

const average = (rows: Row[], key: string): number | null => {
  const values = rows.map((row) => numberOrNull(row[key])).filter((value): value is number => value !== null);
  return values.length > 0 ? values.reduce((total, value) => total + value, 0) / values.length : null;
};

const evalTablesAvailable = (db: Database.Database): boolean =>
  tableExists(db, "eval_tasks") && tableExists(db, "eval_runs") && tableExists(db, "eval_scores");

const candidateTablesAvailable = (db: Database.Database): boolean => tableExists(db, "shadow_candidates");

const evalRunPath = (runId: string | null): string | null => (runId ? `/runs/${encodeURIComponent(runId)}` : null);

const summaryFromRows = (scopeId: string, rows: Row[]): EvalSummary | null => {
  if (rows.length === 0) return null;
  const latest = rows[0];
  const taskIds = new Set(rows.map((row) => nullableText(row.task_id)).filter((value): value is string => value !== null));
  return {
    scopeId,
    runCount: rows.length,
    taskCount: taskIds.size,
    overallScore: average(rows, "overall_score"),
    taskSuccess: average(rows, "task_success"),
    qualityAdherence: average(rows, "quality_adherence"),
    workflowSpeed: average(rows, "workflow_speed"),
    costEfficiency: average(rows, "cost_efficiency"),
    contextEffectiveness: average(rows, "context_effectiveness"),
    secondBrainEffectiveness: average(rows, "second_brain_effectiveness"),
    contextPortability: average(rows, "context_portability"),
    autonomy: average(rows, "autonomy"),
    userTrust: average(rows, "user_trust"),
    contextProfile: nullableText(latest.context_profile),
    secondBrainLift: average(rows, "second_brain_effectiveness"),
    portabilityGap: average(rows, "context_portability") === null ? null : 1 - Number(average(rows, "context_portability")),
    fullEvalRunPath: evalRunPath(nullableText(latest.id)),
  };
};

export const getEvalSummaryForProject = (db: Database.Database, projectId: string): EvalSummary | null => {
  if (!evalTablesAvailable(db)) return null;
  const rows = db
    .prepare(
      `
      SELECT r.*, s.task_success, s.quality_adherence, s.workflow_speed, s.cost_efficiency,
             s.context_effectiveness, s.second_brain_effectiveness, s.context_portability,
             s.autonomy, s.user_trust, s.overall_score
      FROM eval_runs r
      LEFT JOIN eval_tasks t ON t.id = r.task_id
      LEFT JOIN eval_scores s ON s.run_id = r.id
      WHERE t.repo_id = ?
      ORDER BY r.created_at DESC
      LIMIT 50
      `,
    )
    .all(projectId) as Row[];
  return summaryFromRows(projectId, rows);
};

export const getEvalRunsForRun = (db: Database.Database, runId: string): EvalRun[] => {
  if (!evalTablesAvailable(db)) return [];
  const rows = db
    .prepare(
      `
      SELECT r.*, s.overall_score
      FROM eval_runs r
      LEFT JOIN eval_scores s ON s.run_id = r.id
      WHERE r.id = ? OR r.task_id = ?
      ORDER BY r.created_at DESC
      LIMIT 20
      `,
    )
    .all(runId, runId) as Row[];
  return rows.map((row) => ({
    id: text(row.id),
    taskId: nullableText(row.task_id),
    condition: text(row.condition),
    mode: text(row.mode),
    harness: nullableText(row.harness),
    model: nullableText(row.model),
    contextProfile: text(row.context_profile),
    branchName: nullableText(row.branch_name),
    durationMs: numberOrNull(row.duration_ms),
    totalTokens: numberOrNull(row.total_tokens),
    estimatedCostUsd: numberOrNull(row.estimated_cost_usd),
    toolCalls: numberOrNull(row.tool_calls),
    failedCommands: numberOrNull(row.failed_commands),
    filesChanged: numberOrNull(row.files_changed),
    finalStatus: text(row.final_status),
    createdAt: nullableText(row.created_at),
    overallScore: numberOrNull(row.overall_score),
  }));
};

export const getEvalSummaryForRun = (db: Database.Database, runId: string): EvalSummary | null => {
  if (!evalTablesAvailable(db)) return null;
  const rows = db
    .prepare(
      `
      SELECT r.*, s.task_success, s.quality_adherence, s.workflow_speed, s.cost_efficiency,
             s.context_effectiveness, s.second_brain_effectiveness, s.context_portability,
             s.autonomy, s.user_trust, s.overall_score
      FROM eval_runs r
      LEFT JOIN eval_scores s ON s.run_id = r.id
      WHERE r.id = ? OR r.task_id = ?
      ORDER BY r.created_at DESC
      LIMIT 20
      `,
    )
    .all(runId, runId) as Row[];
  return summaryFromRows(runId, rows);
};

export const getShadowCandidateQueue = (db: Database.Database): ShadowCandidate[] => {
  if (!candidateTablesAvailable(db)) return [];
  const canJoinTasks = tableExists(db, "eval_tasks");
  const rows = db
    .prepare(
      `
      SELECT c.id, c.task_id, ${canJoinTasks ? "t.repo_id" : "NULL"} AS project_id,
             c.peer_session_id, c.score, c.recommendation, c.reasons_json, c.blockers_json,
             c.automation_state, c.state_updated_at, c.created_at
      FROM shadow_candidates c
      ${canJoinTasks ? "LEFT JOIN eval_tasks t ON t.id = c.task_id" : ""}
      WHERE c.automation_state IN ('TRACE_ONLY', 'CANDIDATE', 'READY_FOR_SHADOW', 'APPROVED_IN_PERSON')
      ORDER BY c.score DESC, c.created_at DESC
      LIMIT 25
      `,
    )
    .all() as Row[];
  return rows.map((row) => ({
    candidateId: text(row.id),
    taskId: nullableText(row.task_id),
    projectId: nullableText(row.project_id),
    peerSessionId: nullableText(row.peer_session_id),
    score: numberOrNull(row.score) ?? 0,
    recommendation: text(row.recommendation),
    reasons: jsonList(row.reasons_json),
    blockers: jsonList(row.blockers_json),
    automationState: text(row.automation_state),
    stateUpdatedAt: nullableText(row.state_updated_at),
    createdAt: nullableText(row.created_at),
  }));
};

export const approveShadowCandidate = (db: Database.Database, candidateId: string): ShadowCandidate | null => {
  if (!candidateTablesAvailable(db)) return null;
  const now = new Date().toISOString();
  db.prepare("UPDATE shadow_candidates SET automation_state = ?, state_updated_at = ? WHERE id = ?").run(
    "APPROVED_IN_PERSON",
    now,
    candidateId,
  );
  return getShadowCandidateQueue(db).find((candidate) => candidate.candidateId === candidateId) ?? null;
};
