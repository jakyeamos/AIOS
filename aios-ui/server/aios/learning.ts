import { randomUUID } from "node:crypto";

import type Database from "better-sqlite3";

import type {
  ConservativeProposalRow,
  LearningImpactPerRun,
  LearningImpactRollup,
  LearningSignalKind,
  RecurringPattern,
} from "@/lib/types";
import {
  learningPatternPath,
  promptTemplatePath,
  skillPath,
  workflowPath,
  writebackPath,
} from "@/lib/drill-down";
import { ensureControlPlaneSchema } from "@/server/aios/schema";

const parseJsonArray = <T>(raw: string, fallback: T): T => {
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
};

const parseJsonRecord = (raw: string | null): Record<string, unknown> => {
  if (!raw) {
    return {};
  }
  try {
    const parsed = JSON.parse(raw) as unknown;
    return parsed && typeof parsed === "object" && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : {};
  } catch {
    return {};
  }
};

const numberOrNull = (value: unknown): number | null =>
  typeof value === "number" ? value : null;

const stringOrNull = (value: unknown): string | null =>
  typeof value === "string" ? value : null;

const tableExistsInDb = (db: Database.Database, tableName: string): boolean => {
  const row = db
    .prepare("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1")
    .get(tableName) as { name: string } | undefined;
  return Boolean(row?.name);
};

const rollupPath = (scope: "workflow" | "prompt" | "skill", key: string): string => {
  if (scope === "workflow") {
    return workflowPath(key);
  }
  if (scope === "prompt") {
    return promptTemplatePath(key);
  }
  return skillPath(key);
};

export const proposeRunWritebacks = (db: Database.Database, runId: string): void => {
  ensureControlPlaneSchema(db);

  const existing = db
    .prepare("SELECT COUNT(*) AS count FROM improvement_writebacks WHERE run_id = ?")
    .get(runId) as { count: number };
  if (existing.count > 0) {
    return;
  }

  const run = db
    .prepare(
      `
      SELECT
        r.id,
        r.project_id AS projectId,
        r.objective,
        r.workflow_key AS workflowKey,
        r.agent_key AS agentKey,
        r.status,
        r.result_summary AS resultSummary,
        m.summary AS memorySummary,
        m.changes_json AS changesJson,
        p.selection_trace_json AS selectionTraceJson
      FROM orchestration_runs r
      LEFT JOIN memory_updates m ON m.id = r.memory_update_id
      LEFT JOIN briefing_packets p ON p.id = r.packet_id
      WHERE r.id = ?
      LIMIT 1
    `,
    )
    .get(runId) as
    | {
        id: string;
        projectId: string | null;
        objective: string;
        workflowKey: string;
        agentKey: string;
        status: string;
        resultSummary: string | null;
        memorySummary: string | null;
        changesJson: string | null;
        selectionTraceJson: string | null;
      }
    | undefined;

  if (!run || !run.projectId) {
    return;
  }

  const selectionTrace = parseJsonArray<Array<{ label: string; section: string }>>(run.selectionTraceJson ?? "[]", []);
  const topContext = selectionTrace.slice(0, 3).map((item) => `${item.section}: ${item.label}`);
  const changeItems = parseJsonArray<string[]>(run.changesJson ?? "[]", []).slice(0, 3);
  const workflowApprovalRequired = selectionTrace.length > 6;

  const rows = [
    {
      layerType: "project",
      layerKey: run.projectId,
      title: `Project writeback from ${run.objective}`,
      summary: run.memorySummary ?? run.resultSummary ?? "Completed run captured without a detailed memory summary.",
      evidence: changeItems.length > 0 ? changeItems : [run.objective],
      requiresApproval: false,
      approvalReason: null,
      tokenRegressive: false,
      status: "proposed",
    },
    {
      layerType: "workflow",
      layerKey: run.workflowKey,
      title: `Workflow learning for ${run.workflowKey}`,
      summary:
        topContext.length > 0
          ? `Most useful compact context for this run: ${topContext.join("; ")}.`
          : "No packet-selection trace was available for this run.",
      evidence: topContext.length > 0 ? topContext : [run.objective],
      requiresApproval: workflowApprovalRequired,
      approvalReason: workflowApprovalRequired
        ? "This proposal may increase default packet breadth and needs review."
        : null,
      tokenRegressive: workflowApprovalRequired,
      status: workflowApprovalRequired ? "pending_approval" : "proposed",
    },
  ] as const;

  const insert = db.prepare(`
    INSERT INTO improvement_writebacks (
      id,
      run_id,
      project_id,
      layer_type,
      layer_key,
      title,
      summary,
      evidence_json,
      proposed_change_json,
      impact_scope,
      status,
      requires_approval,
      approval_reason,
      token_regressive,
      created_at,
      updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);
  const insertEvent = db.prepare(`
    INSERT INTO improvement_writeback_events (
      id,
      writeback_id,
      run_id,
      event_type,
      to_status,
      actor,
      note,
      metadata_json,
      created_at
    )
    VALUES (?, ?, ?, 'proposed', ?, 'system', ?, '{}', ?)
  `);

  for (const row of rows) {
    const writebackId = `writeback-${randomUUID()}`;
    const timestamp = new Date().toISOString();
    insert.run(
      writebackId,
      run.id,
      run.projectId,
      row.layerType,
      row.layerKey,
      row.title,
      row.summary,
      JSON.stringify(row.evidence),
      JSON.stringify({
        source: "legacy-backfill",
        workflowKey: run.workflowKey,
      }),
      row.layerType === "workflow" ? "workflow-default" : "project",
      row.status,
      row.requiresApproval ? 1 : 0,
      row.approvalReason,
      row.tokenRegressive ? 1 : 0,
      timestamp,
      timestamp,
    );
    insertEvent.run(
      `writeback-event-${randomUUID()}`,
      writebackId,
      run.id,
      row.status,
      row.summary,
      timestamp,
    );
  }
};

export const getLearningImpactForRun = (
  db: Database.Database,
  runId: string,
): LearningImpactPerRun | null => {
  ensureControlPlaneSchema(db);
  if (!tableExistsInDb(db, "orchestration_runs")) {
    return null;
  }
  const run = db
    .prepare("SELECT id, workflow_key AS workflowKey FROM orchestration_runs WHERE id = ? LIMIT 1")
    .get(runId) as { id: string; workflowKey: string | null } | undefined;
  if (!run) {
    return null;
  }
  const signalRows = tableExistsInDb(db, "workflow_learning_events")
    ? (db
        .prepare(
          `
          SELECT signal_kind AS signalKind
          FROM workflow_learning_events
          WHERE run_id = ? AND signal_kind IS NOT NULL
          ORDER BY created_at, id
        `,
        )
        .all(runId) as Array<{ signalKind: LearningSignalKind }>)
    : [];
  const signals = Array.from(new Set(signalRows.map((row) => row.signalKind)));
  const eventCount = tableExistsInDb(db, "workflow_learning_events")
    ? ((db
        .prepare("SELECT COUNT(*) AS count FROM workflow_learning_events WHERE run_id = ?")
        .get(runId) as { count: number }).count ?? 0)
    : 0;
  const proposals = listConservativeProposals(db, undefined, 200)
    .filter((proposal) => {
      const payload = parseJsonRecord(
        (
          db
            .prepare("SELECT proposed_change_json FROM improvement_writebacks WHERE id = ? LIMIT 1")
            .get(proposal.writeback_id) as { proposed_change_json: string | null } | undefined
        )?.proposed_change_json ?? null,
      );
      const evidence = (payload.metadata as Record<string, unknown> | undefined)?.evidence_run_ids;
      return Array.isArray(evidence) && evidence.includes(runId);
    })
    .map((proposal) => ({
      writeback_id: proposal.writeback_id,
      signal_kind: proposal.signal_kind,
      requires_approval: proposal.requires_approval,
      status: proposal.proposal_status,
    }));
  return {
    run_id: run.id,
    workflow_key: run.workflowKey,
    signals_emitted: signals,
    assets_evidenced: run.workflowKey
      ? [
          {
            asset_kind: "workflow",
            asset_key: run.workflowKey,
            delta_sample_size: 1,
            delta_success_count: 0,
            delta_blocker_count: 0,
          },
        ]
      : [],
    proposals_created: proposals,
    learning_events_persisted: eventCount,
    no_learning_reason: signals.length === 0 && proposals.length === 0 ? "one_off_task" : null,
  };
};

export const getLearningImpactRollup = (
  db: Database.Database,
  scope: "workflow" | "prompt" | "skill",
  key: string,
  since: string,
  projectId?: string | null,
): LearningImpactRollup => {
  ensureControlPlaneSchema(db);
  const rows = tableExistsInDb(db, "workflow_execution_reports")
    ? (db
        .prepare(
          `
          SELECT w.status AS status
          FROM workflow_execution_reports w
          LEFT JOIN orchestration_runs r ON r.id = w.run_id
          WHERE w.workflow_key = ?
            AND w.created_at >= ?
            AND (? IS NULL OR r.project_id = ?)
        `,
        )
        .all(key, since, projectId ?? null, projectId ?? null) as Array<{ status: string }>)
    : [];
  const sampleSize = rows.length;
  const failed = rows.filter((row) => row.status === "failed").length;
  const completed = rows.filter((row) => row.status === "completed").length;
  const reworkRate = sampleSize > 0 ? failed / sampleSize : null;
  const successRate = sampleSize > 0 ? completed / sampleSize : null;
  return {
    scope,
    key,
    since,
    sample_size: sampleSize,
    rework_rate_30d: reworkRate,
    rework_rate_90d: null,
    success_rate_30d: successRate,
    blocker_rate_30d: null,
    trend: sampleSize < 10 ? "insufficient_data" : "flat",
    rationale:
      sampleSize < 10
        ? `sample_size=${sampleSize} below trend threshold 10`
        : `sample_size=${sampleSize} has no prior comparison in UI projection`,
    project_id: projectId ?? null,
    drillDownPath: rollupPath(scope, key),
  };
};

export const listRecurringPatterns = (
  db: Database.Database,
  since: string,
  projectId?: string | null,
  limit = 50,
): RecurringPattern[] => {
  ensureControlPlaneSchema(db);
  if (!tableExistsInDb(db, "workflow_learning_events")) {
    return [];
  }
  const rows = db
    .prepare(
      `
      SELECT
        e.signal_kind AS signalKind,
        COALESCE(e.proposal_target, r.workflow_key, 'unknown') AS scopeKey,
        r.project_id AS projectId,
        COUNT(*) AS sampleSize,
        GROUP_CONCAT(e.run_id) AS runIds
      FROM workflow_learning_events e
      LEFT JOIN orchestration_runs r ON r.id = e.run_id
      WHERE e.signal_kind IS NOT NULL
        AND e.created_at >= ?
        AND (? IS NULL OR r.project_id = ?)
      GROUP BY e.signal_kind, COALESCE(e.proposal_target, r.workflow_key, 'unknown'), r.project_id
      ORDER BY sampleSize DESC
      LIMIT ?
    `,
    )
    .all(since, projectId ?? null, projectId ?? null, limit) as Array<{
    signalKind: LearningSignalKind;
    scopeKey: string;
    projectId: string | null;
    sampleSize: number;
    runIds: string | null;
  }>;
  return rows.map((row) => ({
    pattern_id: `ui-${row.signalKind}-${row.scopeKey}`,
    signal_kind: row.signalKind,
    scope_kind: "workflow",
    scope_key: row.scopeKey,
    project_id: row.projectId,
    sample_size: row.sampleSize,
    recurrence_count: row.sampleSize,
    confidence: 1,
    since,
    summary: `${row.signalKind} appeared ${row.sampleSize} times for ${row.scopeKey}`,
    evidence_run_ids: row.runIds ? row.runIds.split(",") : [],
    suggested_remediation_class: "review_learning_signal",
    metadata: { source: "workflow_learning_events" },
    drillDownPath: learningPatternPath(`ui-${row.signalKind}-${row.scopeKey}`),
  }));
};

export const listConservativeProposals = (
  db: Database.Database,
  status?: string,
  limit = 50,
): ConservativeProposalRow[] => {
  ensureControlPlaneSchema(db);
  if (!tableExistsInDb(db, "improvement_writebacks")) {
    return [];
  }
  const lifecycleJoin = tableExistsInDb(db, "promotion_lifecycle_items")
    ? "LEFT JOIN promotion_lifecycle_items p ON p.item_kind = w.layer_type AND p.item_key = w.layer_key"
    : "";
  const lifecycleStateSelect = tableExistsInDb(db, "promotion_lifecycle_items")
    ? "p.status AS currentLifecycleState"
    : "NULL AS currentLifecycleState";
  const rows = db
    .prepare(
      `
      SELECT
        w.id AS writebackId,
        w.layer_type AS layerType,
        w.layer_key AS layerKey,
        w.impact_scope AS impactScope,
        w.status AS proposalStatus,
        w.requires_approval AS requiresApproval,
        w.created_at AS createdAt,
        w.proposed_change_json AS proposedChangeJson,
        ${lifecycleStateSelect}
      FROM improvement_writebacks w
      ${lifecycleJoin}
      WHERE w.proposed_change_json LIKE ?
        AND (? IS NULL OR w.status = ?)
      ORDER BY w.created_at DESC
      LIMIT ?
    `,
    )
    .all('%"source": "learning_analysis"%', status ?? null, status ?? null, limit) as Array<{
    writebackId: string;
    layerType: string;
    layerKey: string;
    impactScope: string;
    proposalStatus: string;
    requiresApproval: number;
    createdAt: string;
    proposedChangeJson: string | null;
    currentLifecycleState: string | null;
  }>;
  return rows.map((row) => {
    const payload = parseJsonRecord(row.proposedChangeJson);
    const metadata = parseJsonRecord(JSON.stringify(payload.metadata ?? {}));
    return {
      writeback_id: row.writebackId,
      layer_type: row.layerType,
      layer_key: row.layerKey,
      impact_scope: row.impactScope,
      signal_kind: stringOrNull(payload.signal_kind) as LearningSignalKind | null,
      pattern_id: stringOrNull(metadata.pattern_id),
      proposal_status: row.proposalStatus,
      current_lifecycle_state: row.currentLifecycleState,
      requires_approval: row.requiresApproval === 1,
      created_at: row.createdAt,
      sample_size: numberOrNull(metadata.sample_size),
      recurrence_count: numberOrNull(metadata.recurrence_count),
      confidence: numberOrNull(metadata.confidence),
      drillDownPath: writebackPath(row.writebackId),
    };
  });
};
