import { randomUUID } from "node:crypto";

import type Database from "better-sqlite3";

import type {
  BriefingPacket,
  ConsistencyFinding,
  ControlPlaneRunDetail,
  DailyFlowTrace,
  GovernanceOverview,
  GovernanceProposalSummary,
  GovernanceRunGap,
  ImprovementWriteback,
  NextAction,
  OrchestrationRun,
  OrchestrationRunStatus,
  PhaseId,
  PhaseStatus,
  PhaseStatusReport,
  RouteRecommendation,
} from "@/lib/control-plane";
import type { LearningImpactRollup } from "@/lib/types";
import { getCatalogSnapshot } from "@/server/aios/catalog";
import { replayDailyFlow } from "@/server/aios/daily-flow";
import { getLearningImpactRollup } from "@/server/aios/learning";
import { getNextActions } from "@/server/aios/next-action";
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
  workflowTemplates: ReturnType<typeof getCatalogSnapshot>["workflowTemplates"];
  agentProfiles: ReturnType<typeof getCatalogSnapshot>["agentProfiles"];
  invocationBackends: ReturnType<typeof getCatalogSnapshot>["invocationBackends"];
  runs: OrchestrationRun[];
  packets: BriefingPacket[];
  pendingWritebacks: ImprovementWriteback[];
  governance: GovernanceOverview;
  recentFindings: ConsistencyFinding[];
  nextActions: NextAction[];
  dailyFlowSummary: DailyFlowTrace | null;
  learningImpactRollup: LearningImpactRollup[];
  phaseStatus: PhaseStatusReport[];
} => {
  const catalog = getCatalogSnapshot();
  const runs = listControlPlaneRuns(db);
  const governance = getGovernanceOverview(db);
  const nextActions = getNextActions(db, { limit: 8 });
  return {
    workflowTemplates: catalog.workflowTemplates,
    agentProfiles: catalog.agentProfiles,
    invocationBackends: catalog.invocationBackends.length > 0 ? catalog.invocationBackends : listInvocationBackends(),
    runs,
    packets: listPacketRows(db),
    pendingWritebacks: listImprovementWritebacks(db, { limit: 12 }).filter((writeback) => writeback.requiresApproval),
    governance,
    recentFindings: listConsistencyFindings(db, { limit: 12 }),
    nextActions,
    dailyFlowSummary: latestDailyFlowSummary(db, runs),
    learningImpactRollup: topLearningImpactRollups(db),
    phaseStatus: phaseCompletionAudit(db),
  };
};

const latestDailyFlowSummary = (db: Database.Database, runs: OrchestrationRun[]): DailyFlowTrace | null => {
  const run = runs.find((entry) => entry.status !== "planned") ?? runs[0];
  return run ? replayDailyFlow(db, { runId: run.id }) : null;
};

const topLearningImpactRollups = (db: Database.Database): LearningImpactRollup[] => {
  if (!tableExists(db, "orchestration_runs")) {
    return [];
  }
  const rows = db
    .prepare(
      `
      SELECT workflow_key AS workflowKey, COUNT(*) AS count
      FROM orchestration_runs
      WHERE workflow_key IS NOT NULL
      GROUP BY workflow_key
      ORDER BY count DESC, workflow_key ASC
      LIMIT 3
      `,
    )
    .all() as Array<{ workflowKey: string; count: number }>;
  return rows.map((row) =>
    getLearningImpactRollup(db, "workflow", row.workflowKey, "1970-01-01T00:00:00.000Z", null),
  );
};

const PHASE_TABLE_REQUIREMENTS: Record<PhaseId, readonly string[]> = {
  phase_01: ["projects", "sessions"],
  phase_02: ["orchestration_runs", "briefing_packets"],
  phase_03: ["success_criteria_evaluations", "success_criteria_findings"],
  phase_04: ["improvement_writebacks", "improvement_writeback_events"],
  phase_05: ["workflow_execution_reports", "workflow_learning_events"],
  phase_06: ["standards_health_snapshots", "standards_delta_items"],
  phase_07: ["quality_pipeline_runs", "quality_pipeline_checks"],
  phase_08: ["workflow_experiments"],
  phase_09: ["promotion_lifecycle_items"],
  phase_10: ["standards_backfill_tasks", "automation_run_history"],
};

export const phaseCompletionAudit = (db: Database.Database): PhaseStatusReport[] => {
  const services = {
    phase_01: ["projects-router"],
    phase_02: ["control-plane-router"],
    phase_03: ["success-criteria-engine"],
    phase_04: ["writeback-router"],
    phase_05: ["learning-router"],
    phase_06: ["standards-health"],
    phase_07: ["quality-pipeline"],
    phase_08: ["experiments-router"],
    phase_09: ["workflows-router"],
    phase_10: ["daily-flow-router", "operator-search-router", "next-action-router"],
  } satisfies Record<PhaseId, readonly string[]>;

  return Object.entries(PHASE_TABLE_REQUIREMENTS).map(([phase, tables]) => {
    const missingTables = tables.filter((table) => !tableExists(db, table));
    const status: PhaseStatus =
      missingTables.length === 0 ? "complete" : missingTables.length === tables.length ? "missing" : "partial";
    return {
      phase: phase as PhaseId,
      status,
      missingTables,
      missingServices: services[phase as PhaseId].length === 0 ? services[phase as PhaseId] : [],
    };
  });
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
  const policyClassDrillDowns = Object.fromEntries(
    policyClassCounts.map((row) => [
      row.policyClass,
      `/writebacks?policyClass=${encodeURIComponent(row.policyClass)}`,
    ]),
  );

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
    policyClassDrillDowns,
    terminalRunsMissingEvidence: terminal.gaps,
    linkRules: [
      "Approval-sensitive standards, prompt, skill, workflow, packet, global, project-context, and destructive-action changes must remain pending until reviewed.",
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
  const catalog = getCatalogSnapshot();
  const runId = `run-${randomUUID()}`;
  const packetId = `packet-${randomUUID()}`;
  const backendKey =
    catalog.workflowTemplates.find((workflow) => workflow.key === assembledPacket.workflowKey)?.defaultBackendKey ??
    catalog.agentProfiles.find((agent) => agent.key === assembledPacket.agentKey)?.defaultBackendKey ??
    catalog.invocationBackends[0]?.key ??
    "codex-managed-runtime";

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
