import { randomUUID } from "node:crypto";

import type Database from "better-sqlite3";

import type { BriefingPacket, OrchestrationRun, OrchestrationRunStatus } from "@/lib/control-plane";
import { agentProfiles, workflowTemplates } from "@/server/aios/catalog";
import { assembleRankedPacket, expandPacketContext } from "@/server/aios/packet-assembly";
import { ensureControlPlaneSchema } from "@/server/aios/schema";

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

const supersedePendingRuns = (db: Database.Database, projectId: string | null): void => {
  if (!projectId) {
    return;
  }

  db.prepare(
    `
    UPDATE orchestration_runs
    SET status = 'superseded',
        updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
    WHERE project_id = ?
      AND status IN ('planned', 'ready')
  `,
  ).run(projectId);
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
  runs: OrchestrationRun[];
  packets: BriefingPacket[];
} => ({
  workflowTemplates,
  agentProfiles,
  runs: listControlPlaneRuns(db),
  packets: listPacketRows(db),
});

export const planTask = (
  db: Database.Database,
  input: { objective: string; projectId?: string | null; policyMode?: BriefingPacket["policyMode"]; tokenBudget?: number },
): { run: OrchestrationRun; packet: BriefingPacket } => {
  ensureControlPlaneSchema(db);

  const projectId = input.projectId ?? null;
  const assembledPacket = assembleRankedPacket(db, input);
  const runId = `run-${randomUUID()}`;
  const packetId = `packet-${randomUUID()}`;

  supersedePendingRuns(db, projectId);

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
      packet_id
    )
    VALUES (?, ?, ?, ?, ?, 'ready', ?, ?, ?, ?)
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
    packetId,
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
