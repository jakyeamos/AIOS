import { randomUUID } from "node:crypto";

import type Database from "better-sqlite3";

import type {
  BriefingPacket,
  ConsistencyFinding,
  ControlPlaneRunDetail,
  GovernanceOverview,
  GovernanceProposalSummary,
  GovernanceRunGap,
  ImprovementWriteback,
  OrchestrationRun,
  OrchestrationRunStatus,
  RouteRecommendation,
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
  routeId: string | null;
  routeStatus: string | null;
  routeResultJson: string | null;
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
  routeId: string | null;
  routeResultJson: string | null;
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

const parseJsonRecord = <T extends Record<string, unknown>>(raw: string | null): T | null => {
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as unknown;
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return Object.keys(parsed as Record<string, unknown>).length > 0 ? (parsed as T) : null;
    }
    return null;
  } catch {
    return null;
  }
};

const tableExists = (db: Database.Database, tableName: string): boolean => {
  const row = db
    .prepare("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1")
    .get(tableName) as { name: string } | undefined;
  return Boolean(row?.name);
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

const approvalPolicyClass = (writeback: ImprovementWriteback): string => {
  const policy = writeback.proposedChange.approval_policy;
  if (policy && typeof policy === "object" && !Array.isArray(policy)) {
    const policyClass = (policy as { policy_class?: unknown }).policy_class;
    if (typeof policyClass === "string" && policyClass.length > 0) {
      return policyClass;
    }
  }
  if (writeback.requiresApproval) {
    return "legacy_approval_required";
  }
  return "not_required";
};

const toGovernanceProposal = (writeback: ImprovementWriteback): GovernanceProposalSummary => ({
  id: writeback.id,
  source: "improvement_writebacks",
  title: writeback.title,
  targetType: writeback.layerType,
  targetKey: writeback.layerKey,
  status: writeback.status,
  requiresApproval: writeback.requiresApproval,
  approvalPolicyClass: approvalPolicyClass(writeback),
  href: writeback.runId ? `/runs/${writeback.runId}` : "/control",
  createdAt: writeback.createdAt,
});

const runHasGovernanceEvidence = (db: Database.Database, runId: string): boolean => {
  const checks = [
    ["improvement_writebacks", "run_id"],
    ["workflow_learning_events", "run_id"],
    ["workflow_execution_reports", "run_id"],
  ] as const;

  return checks.some(([table, column]) => {
    if (!tableExists(db, table)) {
      return false;
    }
    const row = db.prepare(`SELECT 1 FROM ${table} WHERE ${column} = ? LIMIT 1`).get(runId);
    return row !== undefined;
  });
};

const terminalRunGaps = (db: Database.Database): { terminalCount: number; gaps: GovernanceRunGap[] } => {
  if (!tableExists(db, "orchestration_runs")) {
    return { terminalCount: 0, gaps: [] };
  }

  const rows = db
    .prepare(
      `
      SELECT id AS runId, objective, workflow_key AS workflowKey, status, updated_at AS updatedAt
      FROM orchestration_runs
      WHERE status IN ('partial', 'needs_follow_up', 'completed', 'failed', 'canceled', 'superseded')
      ORDER BY updated_at DESC
      LIMIT 100
    `,
    )
    .all() as GovernanceRunGap[];

  return {
    terminalCount: rows.length,
    gaps: rows.filter((run) => !runHasGovernanceEvidence(db, run.runId)),
  };
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
        r.packet_id AS packetId,
        r.route_id AS routeId,
        r.route_status AS routeStatus,
        r.route_result_json AS routeResultJson
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
    statusReason: parseJsonRecord<Record<string, unknown>>(row.statusReasonJson) ?? {},
    resultSummary: row.resultSummary,
    memoryUpdateId: row.memoryUpdateId,
    packetId: row.packetId,
    routeId: row.routeId,
    routeStatus: row.routeStatus,
    routeResult: parseJsonRecord<RouteRecommendation>(row.routeResultJson),
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
        route_id AS routeId,
        route_result_json AS routeResultJson,
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
    routeId: row.routeId,
    routeResult: parseJsonRecord<RouteRecommendation>(row.routeResultJson),
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
  governance: GovernanceOverview;
  recentFindings: ConsistencyFinding[];
} => {
  const runs = listControlPlaneRuns(db);
  const governance = getGovernanceOverview(db);
  return {
    workflowTemplates,
    agentProfiles,
    invocationBackends: listInvocationBackends(),
    runs,
    packets: listPacketRows(db),
    pendingWritebacks: listImprovementWritebacks(db, { limit: 12 }).filter((writeback) => writeback.requiresApproval),
    governance,
    recentFindings: listConsistencyFindings(db, { limit: 12 }),
  };
};

export const getGovernanceOverview = (db: Database.Database): GovernanceOverview => {
  ensureControlPlaneSchema(db);
  const writebacks = listImprovementWritebacks(db, { limit: 100 });
  const proposals = writebacks.map(toGovernanceProposal);
  const pendingApprovals = proposals.filter(
    (proposal) => proposal.requiresApproval || proposal.status === "pending_approval",
  );
  const policyClassCounts = Array.from(
    proposals.reduce((counts, proposal) => {
      counts.set(proposal.approvalPolicyClass, (counts.get(proposal.approvalPolicyClass) ?? 0) + 1);
      return counts;
    }, new Map<string, number>()),
  )
    .map(([policyClass, count]) => ({ policyClass, count }))
    .sort((left, right) => right.count - left.count || left.policyClass.localeCompare(right.policyClass));
  const terminal = terminalRunGaps(db);

  return {
    summary: {
      proposalCount: proposals.length,
      pendingApprovalCount: pendingApprovals.length,
      terminalRunCount: terminal.terminalCount,
      terminalRunsMissingEvidenceCount: terminal.gaps.length,
      policyClassCount: policyClassCounts.length,
    },
    pendingApprovals,
    recentProposals: proposals.slice(0, 20),
    policyClassCounts,
    terminalRunsMissingEvidence: terminal.gaps,
    linkRules: [
      "Approval-sensitive truth, standards, prompt, skill, workflow, packet, global, project-truth, and destructive-action changes must remain pending until reviewed.",
      "Terminal runs should have writeback, workflow-learning, closeout, or no-learning evidence before being treated as complete.",
      "Scoped project-memory writebacks may remain proposed, but they do not become accepted truth without a truth update.",
    ],
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
      route_id,
      route_status,
      route_result_json,
      status_reason_json,
      packet_id
    )
    VALUES (?, ?, ?, ?, ?, 'planned', ?, ?, ?, ?, ?, ?, ?, '{}', ?)
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
    assembledPacket.routeId,
    assembledPacket.routeResult ? "ready" : null,
    JSON.stringify(assembledPacket.routeResult ?? {}),
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
      route_id,
      route_result_json,
      selection_trace_json,
      omitted_context_json
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    assembledPacket.routeId,
    JSON.stringify(assembledPacket.routeResult ?? {}),
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
      packetContractVersion: "governed-handoff-v1",
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
