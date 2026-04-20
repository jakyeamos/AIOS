import { randomUUID } from "node:crypto";

import type Database from "better-sqlite3";

import { ensureControlPlaneSchema } from "@/server/aios/schema";

const parseJsonArray = <T>(raw: string, fallback: T): T => {
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
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
