import { randomUUID } from "node:crypto";

import type Database from "better-sqlite3";

import type {
  BriefingPacket,
  ConsistencyFinding,
  ControlPlaneRunDetail,
  ImprovementWriteback,
  OrchestrationRun,
  OrchestrationRunStatus,
} from "@/lib/control-plane";
import { agentProfiles, invocationBackends, workflowTemplates } from "@/server/aios/catalog";
import { assembleRankedPacket, expandPacketContext } from "@/server/aios/packet-assembly";
import { ensureControlPlaneSchema } from "@/server/aios/schema";
import {
  cancelManagedInvocation,
  getRunDetail,
  listConsistencyFindings,
  listInvocationBackends,
  registerStrictManualInvocation,
  resolveConsistencyFinding,
  reviewWriteback,
  startManagedInvocation,
} from "@/server/aios/runtime";
import { listImprovementWritebacks } from "@/server/aios/topic-graph";

type RunRow = {
  id: string;
  projectId: string | null;
  sessionId: string | null;
  projectName: string | null;
  objective: string;
  workflowKey: string;
  agentKey: string;
  status: OrchestrationRunStatus;
  rationale: string;
  assumptionsJson: string;
  contextTraceJson: string;
  createdAt: string;
  updatedAt: string;
  completedAt: string | null;
  startedAt: string | null;
  failedAt: string | null;
  canceledAt: string | null;
  backendKey: string | null;
  activeInvocationId: string | null;
  supersededByRunId: string | null;
  statusReasonJson: string | null;
  resultSummary: string | null;
  memoryUpdateId: string | null;
  packetId: string | null;
};

type PacketRow = {
  id: string;
  runId: string;
  projectId: string | null;
  objective: string;
  workflowKey: string;
  agentKey: string;
  packetMarkdown: string;
  sectionsJson: string;
  policyMode: BriefingPacket["policyMode"];
  tokenBudget: number;
  selectionTraceJson: string;
  omittedContextJson: string;
  createdAt: string;
};

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
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? (parsed as Record<string, unknown>) : {};
  } catch {
    return {};
  }
};

const supersedePendingRuns = (db: Database.Database, projectId: string | null, supersedingRunId: string): void => {
  if (!projectId) {
    return;
  }

  const rows = db
    .prepare(
      `
      SELECT id, status
      FROM orchestration_runs
      WHERE project_id = ?
        AND status IN ('planned', 'ready')
    `,
    )
    .all(projectId) as Array<{ id: string; status: OrchestrationRunStatus }>;

  const now = new Date().toISOString();
  for (const row of rows) {
    db.prepare(
      `
      UPDATE orchestration_runs
      SET status = 'superseded',
          superseded_by_run_id = ?,
          status_reason_json = ?,
          updated_at = ?
      WHERE id = ?
    `,
    ).run(
      supersedingRunId,
      JSON.stringify({ kind: "superseded", supersededByRunId: supersedingRunId }),
      now,
      row.id,
    );
    db.prepare(
      `
      INSERT INTO orchestration_run_events (
        id,
        run_id,
        project_id,
        event_type,
        from_status,
        to_status,
        summary,
        reason_json,
        metadata_json,
        created_at
      )
      VALUES (?, ?, ?, 'superseded', ?, 'superseded', ?, ?, '{}', ?)
    `,
    ).run(
      `run-event-${randomUUID()}`,
      row.id,
      projectId,
      row.status,
      `Superseded by newer run ${supersedingRunId}.`,
      JSON.stringify({ supersededByRunId: supersedingRunId }),
      now,
    );
  }
};

export const listControlPlaneRuns = (db: Database.Database): OrchestrationRun[] => {
  ensureControlPlaneSchema(db);

  const rows = db
    .prepare(
      `
      SELECT
        r.id,
        r.project_id AS projectId,
        r.session_id AS sessionId,
        p.name AS projectName,
        r.objective,
        r.workflow_key AS workflowKey,
        r.agent_key AS agentKey,
        r.status,
        r.rationale,
        r.assumptions_json AS assumptionsJson,
        r.context_trace_json AS contextTraceJson,
        r.created_at AS createdAt,
        r.updated_at AS updatedAt,
        r.completed_at AS completedAt,
        r.started_at AS startedAt,
        r.failed_at AS failedAt,
        r.canceled_at AS canceledAt,
        r.backend_key AS backendKey,
        r.active_invocation_id AS activeInvocationId,
        r.superseded_by_run_id AS supersededByRunId,
        r.status_reason_json AS statusReasonJson,
        r.result_summary AS resultSummary,
        r.memory_update_id AS memoryUpdateId,
        r.packet_id AS packetId
      FROM orchestration_runs r
      LEFT JOIN projects p ON p.id = r.project_id
      ORDER BY r.created_at DESC
      LIMIT 20
    `,
    )
    .all() as RunRow[];

  return rows.map((row) => ({
    id: row.id,
    projectId: row.projectId,
    sessionId: row.sessionId,
    projectName: row.projectName ?? "Unscoped",
    objective: row.objective,
    workflowKey: row.workflowKey,
    agentKey: row.agentKey,
    status: row.status,
    rationale: row.rationale,
    assumptions: parseJsonArray(row.assumptionsJson, []),
    contextTrace: parseJsonArray(row.contextTraceJson, []),
    createdAt: row.createdAt,
    updatedAt: row.updatedAt,
    completedAt: row.completedAt,
    startedAt: row.startedAt,
    failedAt: row.failedAt,
    canceledAt: row.canceledAt,
    backendKey: row.backendKey,
    activeInvocationId: row.activeInvocationId,
    supersededByRunId: row.supersededByRunId,
    statusReason: parseJsonRecord(row.statusReasonJson),
    resultSummary: row.resultSummary,
    memoryUpdateId: row.memoryUpdateId,
    packetId: row.packetId,
  }));
};

const listPacketRows = (db: Database.Database, limit = 12): BriefingPacket[] => {
  ensureControlPlaneSchema(db);

  const rows = db
    .prepare(
      `
      SELECT
        id,
        run_id AS runId,
        project_id AS projectId,
        objective,
        workflow_key AS workflowKey,
        agent_key AS agentKey,
        packet_markdown AS packetMarkdown,
        sections_json AS sectionsJson,
        policy_mode AS policyMode,
        token_budget AS tokenBudget,
        selection_trace_json AS selectionTraceJson,
        omitted_context_json AS omittedContextJson,
        created_at AS createdAt
      FROM briefing_packets
      ORDER BY created_at DESC
      LIMIT ?
    `,
    )
    .all(limit) as PacketRow[];

  return rows.map((row) => ({
    id: row.id,
    runId: row.runId,
    projectId: row.projectId,
    objective: row.objective,
    workflowKey: row.workflowKey,
    agentKey: row.agentKey,
    createdAt: row.createdAt,
    markdown: row.packetMarkdown,
    sections: parseJsonArray(row.sectionsJson, []),
    policyMode: row.policyMode,
    tokenBudget: row.tokenBudget,
    selectionTrace: parseJsonArray(row.selectionTraceJson, []),
    omittedContext: parseJsonArray(row.omittedContextJson, []),
  }));
};

export const getControlPlaneOverview = (db: Database.Database): {
  workflowTemplates: typeof workflowTemplates;
  agentProfiles: typeof agentProfiles;
  invocationBackends: typeof invocationBackends;
  runs: OrchestrationRun[];
  packets: BriefingPacket[];
  pendingWritebacks: ImprovementWriteback[];
  recentFindings: ConsistencyFinding[];
} => {
  const runs = listControlPlaneRuns(db);
  return {
    workflowTemplates,
    agentProfiles,
    invocationBackends: listInvocationBackends(),
    runs,
    packets: listPacketRows(db),
    pendingWritebacks: listImprovementWritebacks(db, { limit: 12 }).filter((writeback) => writeback.requiresApproval),
    recentFindings: listConsistencyFindings(db, { limit: 12 }),
  };
};

export const planTask = (
  db: Database.Database,
  input: { objective: string; projectId?: string | null; policyMode?: BriefingPacket["policyMode"]; tokenBudget?: number },
): { run: OrchestrationRun; packet: BriefingPacket } => {
  ensureControlPlaneSchema(db);

  const projectId = input.projectId ?? null;
  const assembledPacket = assembleRankedPacket(db, input);
  const runId = `run-${randomUUID()}`;
  const packetId = `packet-${randomUUID()}`;
  const backendKey =
    workflowTemplates.find((workflow) => workflow.key === assembledPacket.workflowKey)?.defaultBackendKey ??
    agentProfiles.find((agent) => agent.key === assembledPacket.agentKey)?.defaultBackendKey ??
    invocationBackends[0].key;

  supersedePendingRuns(db, projectId, runId);

  db.prepare(
    `
    INSERT INTO orchestration_runs (
      id,
      project_id,
      objective,
      workflow_key,
      agent_key,
      status,
      rationale,
      assumptions_json,
      context_trace_json,
      backend_key,
      status_reason_json,
      packet_id
    )
    VALUES (?, ?, ?, ?, ?, 'planned', ?, ?, ?, ?, '{}', ?)
  `,
  ).run(
    runId,
    projectId,
    input.objective,
    assembledPacket.workflowKey,
    assembledPacket.agentKey,
    assembledPacket.rationale,
    JSON.stringify(assembledPacket.assumptions),
    JSON.stringify(assembledPacket.contextTrace),
    backendKey,
    packetId,
  );

  db.prepare(
    `
    INSERT INTO orchestration_run_events (
      id,
      run_id,
      project_id,
      event_type,
      to_status,
      summary,
      reason_json,
      metadata_json,
      created_at
    )
    VALUES (?, ?, ?, 'planned', 'planned', ?, '{}', ?, ?)
  `,
  ).run(
    `run-event-${randomUUID()}`,
    runId,
    projectId,
    "Run record created before packet persistence.",
    JSON.stringify({ backendKey }),
    new Date().toISOString(),
  );

  db.prepare(
    `
    INSERT INTO briefing_packets (
      id,
      run_id,
      project_id,
      objective,
      workflow_key,
      agent_key,
      packet_markdown,
      sections_json,
      policy_mode,
      token_budget,
      selection_trace_json,
      omitted_context_json
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `,
  ).run(
    packetId,
    runId,
    projectId,
    input.objective,
    assembledPacket.workflowKey,
    assembledPacket.agentKey,
    assembledPacket.markdown,
    JSON.stringify(assembledPacket.sections),
    assembledPacket.policyMode,
    assembledPacket.tokenBudget,
      JSON.stringify(assembledPacket.selectionTrace),
      JSON.stringify(assembledPacket.omittedContext),
  );

  db.prepare(
    `
    UPDATE orchestration_runs
    SET status = 'ready',
        updated_at = ?,
        status_reason_json = ?
    WHERE id = ?
  `,
  ).run(
    new Date().toISOString(),
    JSON.stringify({
      kind: "packet_ready",
      backendKey,
      policyMode: assembledPacket.policyMode,
      tokenBudget: assembledPacket.tokenBudget,
    }),
    runId,
  );
  db.prepare(
    `
    INSERT INTO orchestration_run_events (
      id,
      run_id,
      project_id,
      event_type,
      from_status,
      to_status,
      summary,
      reason_json,
      metadata_json,
      created_at
    )
    VALUES (?, ?, ?, 'ready', 'planned', 'ready', ?, ?, ?, ?)
  `,
  ).run(
    `run-event-${randomUUID()}`,
    runId,
    projectId,
    "Briefing packet persisted and backend selected.",
    JSON.stringify({
      backendKey,
      policyMode: assembledPacket.policyMode,
      tokenBudget: assembledPacket.tokenBudget,
    }),
    JSON.stringify({
      packetId,
    }),
    new Date().toISOString(),
  );

  const run = listControlPlaneRuns(db).find((entry) => entry.id === runId);
  const packet = listPacketRows(db).find((entry) => entry.id === packetId);

  if (!run || !packet) {
    throw new Error("Failed to persist orchestration run.");
  }

  return { run, packet };
};

export const requestPacketExpansion = (
  db: Database.Database,
  input: {
    packetId: string;
    runId?: string | null;
    projectId?: string | null;
    requestKind: "topic" | "failure_pattern" | "code_area" | "policy" | "recent_run";
    requestTarget: string;
    tokenBudget?: number;
  },
) => expandPacketContext(db, input);

export const getControlPlaneRunDetail = (db: Database.Database, runId: string): ControlPlaneRunDetail | null => {
  const run = listControlPlaneRuns(db).find((entry) => entry.id === runId);
  if (!run) {
    return null;
  }
  return getRunDetail(db, run);
};

export const invokeControlPlaneRun = (
  db: Database.Database,
  input: { runId: string },
): { runDetail: ControlPlaneRunDetail } => {
  startManagedInvocation(db, input);
  const detail = getControlPlaneRunDetail(db, input.runId);
  if (!detail) {
    throw new Error("Run not found after invocation.");
  }
  return { runDetail: detail };
};

export const registerControlPlaneManualInvocation = (
  db: Database.Database,
  input: {
    runId: string;
    sessionId: string;
    invocationId?: string;
    backendKey?: "manual-session-legacy" | "codex-managed-runtime" | "claude-managed-runtime";
    actor?: string;
    note?: string | null;
  },
): { runDetail: ControlPlaneRunDetail } => {
  registerStrictManualInvocation(db, input);
  const detail = getControlPlaneRunDetail(db, input.runId);
  if (!detail) {
    throw new Error("Run not found after strict manual registration.");
  }
  return { runDetail: detail };
};

export const cancelControlPlaneRun = (
  db: Database.Database,
  input: { runId: string },
): { runDetail: ControlPlaneRunDetail } => {
  cancelManagedInvocation(db, input);
  const detail = getControlPlaneRunDetail(db, input.runId);
  if (!detail) {
    throw new Error("Run not found after cancellation.");
  }
  return { runDetail: detail };
};

export const reviewControlPlaneWriteback = (
  db: Database.Database,
  input: { writebackId: string; decision: "applied" | "rejected"; note?: string | null },
): ImprovementWriteback => reviewWriteback(db, input);

export const resolveControlPlaneFinding = (
  db: Database.Database,
  input: Parameters<typeof resolveConsistencyFinding>[1],
): ConsistencyFinding => resolveConsistencyFinding(db, input);
