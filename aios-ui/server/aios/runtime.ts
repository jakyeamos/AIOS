import { randomUUID } from "node:crypto";
import { spawn } from "node:child_process";
import path from "node:path";

import type Database from "better-sqlite3";

import type {
  ConsistencyEvaluation,
  ConsistencyFinding,
  ControlPlaneRunDetail,
  ImprovementWriteback,
  ImprovementWritebackEvent,
  InvocationBackend,
  OrchestrationInvocation,
  OrchestrationRun,
  OrchestrationRunEvent,
  OrchestrationRunStatus,
} from "@/lib/control-plane";
import { findInvocationBackend, invocationBackends } from "@/server/aios/catalog";
import { resolveAiosRoot } from "@/server/aios/filesystem";
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
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? (parsed as Record<string, unknown>) : {};
  } catch {
    return {};
  }
};

const nowIso = (): string => new Date().toISOString();

const recordRunEvent = (
  db: Database.Database,
  input: {
    runId: string;
    projectId?: string | null;
    sessionId?: string | null;
    invocationId?: string | null;
    eventType: string;
    fromStatus?: OrchestrationRunStatus | null;
    toStatus?: OrchestrationRunStatus | null;
    summary: string;
    reason?: Record<string, unknown>;
    metadata?: Record<string, unknown>;
    createdAt?: string;
  },
): void => {
  ensureControlPlaneSchema(db);
  db.prepare(
    `
    INSERT INTO orchestration_run_events (
      id,
      run_id,
      project_id,
      session_id,
      invocation_id,
      event_type,
      from_status,
      to_status,
      summary,
      reason_json,
      metadata_json,
      created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `,
  ).run(
    `run-event-${randomUUID()}`,
    input.runId,
    input.projectId ?? null,
    input.sessionId ?? null,
    input.invocationId ?? null,
    input.eventType,
    input.fromStatus ?? null,
    input.toStatus ?? null,
    input.summary,
    JSON.stringify(input.reason ?? {}),
    JSON.stringify(input.metadata ?? {}),
    input.createdAt ?? nowIso(),
  );
};

const transitionRun = (
  db: Database.Database,
  input: {
    runId: string;
    toStatus: OrchestrationRunStatus;
    eventType: string;
    summary: string;
    reason?: Record<string, unknown>;
    metadata?: Record<string, unknown>;
    sessionId?: string | null;
    invocationId?: string | null;
    resultSummary?: string | null;
    supersededByRunId?: string | null;
    createdAt?: string;
  },
): void => {
  ensureControlPlaneSchema(db);
  const current = db
    .prepare(
      `
      SELECT status, project_id AS projectId, session_id AS sessionId, active_invocation_id AS activeInvocationId
      FROM orchestration_runs
      WHERE id = ?
      LIMIT 1
    `,
    )
    .get(input.runId) as
    | {
        status: OrchestrationRunStatus;
        projectId: string | null;
        sessionId: string | null;
        activeInvocationId: string | null;
      }
    | undefined;

  if (!current) {
    throw new Error(`Unknown orchestration run: ${input.runId}`);
  }

  const eventTime = input.createdAt ?? nowIso();
  const fields = {
    status: input.toStatus,
    updated_at: eventTime,
    status_reason_json: JSON.stringify(input.reason ?? {}),
    session_id: input.sessionId ?? current.sessionId,
    active_invocation_id: input.invocationId ?? current.activeInvocationId,
    started_at: input.toStatus === "in_progress" ? eventTime : undefined,
    completed_at: input.toStatus === "completed" ? eventTime : undefined,
    failed_at: input.toStatus === "failed" ? eventTime : undefined,
    canceled_at: input.toStatus === "canceled" ? eventTime : undefined,
    superseded_by_run_id: input.toStatus === "superseded" ? input.supersededByRunId ?? null : undefined,
    result_summary: input.resultSummary ?? undefined,
  };

  const assignments = Object.entries(fields)
    .filter(([, value]) => value !== undefined)
    .map(([column]) => `${column} = ?`)
    .join(", ");
  const values = Object.values(fields).filter((value) => value !== undefined);

  db.prepare(`UPDATE orchestration_runs SET ${assignments} WHERE id = ?`).run(...values, input.runId);

  recordRunEvent(db, {
    runId: input.runId,
    projectId: current.projectId,
    sessionId: input.sessionId ?? current.sessionId,
    invocationId: input.invocationId ?? current.activeInvocationId,
    eventType: input.eventType,
    fromStatus: current.status,
    toStatus: input.toStatus,
    summary: input.summary,
    reason: input.reason,
    metadata: input.metadata,
    createdAt: eventTime,
  });
};

const recordWritebackEvent = (
  db: Database.Database,
  input: {
    writebackId: string;
    runId?: string | null;
    eventType: string;
    fromStatus?: ImprovementWriteback["status"] | null;
    toStatus?: ImprovementWriteback["status"] | null;
    actor: string;
    note?: string | null;
    metadata?: Record<string, unknown>;
  },
): void => {
  db.prepare(
    `
    INSERT INTO improvement_writeback_events (
      id,
      writeback_id,
      run_id,
      event_type,
      from_status,
      to_status,
      actor,
      note,
      metadata_json,
      created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `,
  ).run(
    `writeback-event-${randomUUID()}`,
    input.writebackId,
    input.runId ?? null,
    input.eventType,
    input.fromStatus ?? null,
    input.toStatus ?? null,
    input.actor,
    input.note ?? null,
    JSON.stringify(input.metadata ?? {}),
    nowIso(),
  );
};

export const listInvocationBackends = (): InvocationBackend[] => invocationBackends;

export const listRunEvents = (db: Database.Database, runId: string): OrchestrationRunEvent[] => {
  ensureControlPlaneSchema(db);
  const rows = db
    .prepare(
      `
      SELECT
        id,
        run_id AS runId,
        project_id AS projectId,
        session_id AS sessionId,
        invocation_id AS invocationId,
        event_type AS eventType,
        from_status AS fromStatus,
        to_status AS toStatus,
        summary,
        reason_json AS reasonJson,
        metadata_json AS metadataJson,
        created_at AS createdAt
      FROM orchestration_run_events
      WHERE run_id = ?
      ORDER BY created_at DESC
    `,
    )
    .all(runId) as Array<{
      id: string;
      runId: string;
      projectId: string | null;
      sessionId: string | null;
      invocationId: string | null;
      eventType: string;
      fromStatus: OrchestrationRunStatus | null;
      toStatus: OrchestrationRunStatus | null;
      summary: string;
      reasonJson: string;
      metadataJson: string;
      createdAt: string;
    }>;

  return rows.map((row) => ({
    id: row.id,
    runId: row.runId,
    projectId: row.projectId,
    sessionId: row.sessionId,
    invocationId: row.invocationId,
    eventType: row.eventType,
    fromStatus: row.fromStatus,
    toStatus: row.toStatus,
    summary: row.summary,
    reason: parseJsonRecord(row.reasonJson),
    metadata: parseJsonRecord(row.metadataJson),
    createdAt: row.createdAt,
  }));
};

export const listRunInvocations = (db: Database.Database, runId: string): OrchestrationInvocation[] => {
  ensureControlPlaneSchema(db);
  const rows = db
    .prepare(
      `
      SELECT
        id,
        run_id AS runId,
        backend_key AS backendKey,
        backend_label AS backendLabel,
        status,
        handshake_token AS handshakeToken,
        session_id AS sessionId,
        pid,
        command_json AS commandJson,
        metadata_json AS metadataJson,
        created_at AS createdAt,
        started_at AS startedAt,
        ended_at AS endedAt,
        updated_at AS updatedAt
      FROM orchestration_invocations
      WHERE run_id = ?
      ORDER BY created_at DESC
    `,
    )
    .all(runId) as Array<{
      id: string;
      runId: string;
      backendKey: string;
      backendLabel: string;
      status: OrchestrationInvocation["status"];
      handshakeToken: string;
      sessionId: string | null;
      pid: number | null;
      commandJson: string;
      metadataJson: string;
      createdAt: string;
      startedAt: string | null;
      endedAt: string | null;
      updatedAt: string;
    }>;

  return rows.map((row) => ({
    id: row.id,
    runId: row.runId,
    backendKey: row.backendKey,
    backendLabel: row.backendLabel,
    status: row.status,
    handshakeToken: row.handshakeToken,
    sessionId: row.sessionId,
    pid: row.pid,
    command: parseJsonArray<string[]>(row.commandJson, []),
    metadata: parseJsonRecord(row.metadataJson),
    createdAt: row.createdAt,
    startedAt: row.startedAt,
    endedAt: row.endedAt,
    updatedAt: row.updatedAt,
  }));
};

export const listWritebackEvents = (db: Database.Database, writebackIds: string[]): ImprovementWritebackEvent[] => {
  ensureControlPlaneSchema(db);
  if (writebackIds.length === 0) {
    return [];
  }
  const placeholders = writebackIds.map(() => "?").join(", ");
  const rows = db
    .prepare(
      `
      SELECT
        id,
        writeback_id AS writebackId,
        run_id AS runId,
        event_type AS eventType,
        from_status AS fromStatus,
        to_status AS toStatus,
        actor,
        note,
        metadata_json AS metadataJson,
        created_at AS createdAt
      FROM improvement_writeback_events
      WHERE writeback_id IN (${placeholders})
      ORDER BY created_at DESC
    `,
    )
    .all(...writebackIds) as Array<{
      id: string;
      writebackId: string;
      runId: string | null;
      eventType: string;
      fromStatus: ImprovementWriteback["status"] | null;
      toStatus: ImprovementWriteback["status"] | null;
      actor: string;
      note: string | null;
      metadataJson: string;
      createdAt: string;
    }>;

  return rows.map((row) => ({
    id: row.id,
    writebackId: row.writebackId,
    runId: row.runId,
    eventType: row.eventType,
    fromStatus: row.fromStatus,
    toStatus: row.toStatus,
    actor: row.actor,
    note: row.note,
    metadata: parseJsonRecord(row.metadataJson),
    createdAt: row.createdAt,
  }));
};

export const listConsistencyEvaluations = (
  db: Database.Database,
  options: { runId?: string; projectId?: string | null; limit?: number } = {},
): ConsistencyEvaluation[] => {
  ensureControlPlaneSchema(db);
  const rows = db
    .prepare(
      `
      SELECT
        id,
        project_id AS projectId,
        run_id AS runId,
        packet_id AS packetId,
        invocation_id AS invocationId,
        trigger_kind AS triggerKind,
        evaluator_version AS evaluatorVersion,
        summary,
        created_at AS createdAt
      FROM consistency_evaluations
      WHERE (? IS NULL OR run_id = ?)
        AND (? IS NULL OR project_id = ?)
      ORDER BY created_at DESC
      LIMIT ?
    `,
    )
    .all(
      options.runId ?? null,
      options.runId ?? null,
      options.projectId ?? null,
      options.projectId ?? null,
      options.limit ?? 12,
    ) as Array<{
      id: string;
      projectId: string | null;
      runId: string | null;
      packetId: string | null;
      invocationId: string | null;
      triggerKind: string;
      evaluatorVersion: string;
      summary: string;
      createdAt: string;
    }>;

  if (rows.length === 0) {
    return [];
  }

  const evaluationIds = rows.map((row) => row.id);
  const placeholders = evaluationIds.map(() => "?").join(", ");
  const findings = db
    .prepare(
      `
      SELECT
        id,
        evaluation_id AS evaluationId,
        project_id AS projectId,
        run_id AS runId,
        packet_id AS packetId,
        topic_slug AS topicSlug,
        finding_kind AS findingKind,
        severity,
        rule_key AS ruleKey,
        summary,
        provenance_json AS provenanceJson,
        metadata_json AS metadataJson,
        created_at AS createdAt
      FROM consistency_findings
      WHERE evaluation_id IN (${placeholders})
      ORDER BY created_at DESC
    `,
    )
    .all(...evaluationIds) as Array<{
      id: string;
      evaluationId: string;
      projectId: string | null;
      runId: string | null;
      packetId: string | null;
      topicSlug: string | null;
      findingKind: ConsistencyFinding["findingKind"];
      severity: ConsistencyFinding["severity"];
      ruleKey: string;
      summary: string;
      provenanceJson: string;
      metadataJson: string;
      createdAt: string;
    }>;

  const findingsByEvaluation = new Map<string, ConsistencyFinding[]>();
  for (const finding of findings) {
    const bucket = findingsByEvaluation.get(finding.evaluationId) ?? [];
    bucket.push({
      id: finding.id,
      evaluationId: finding.evaluationId,
      projectId: finding.projectId,
      runId: finding.runId,
      packetId: finding.packetId,
      topicSlug: finding.topicSlug,
      findingKind: finding.findingKind,
      severity: finding.severity,
      ruleKey: finding.ruleKey,
      summary: finding.summary,
      provenance: parseJsonArray<Array<Record<string, unknown>>>(finding.provenanceJson, []),
      metadata: parseJsonRecord(finding.metadataJson),
      createdAt: finding.createdAt,
    });
    findingsByEvaluation.set(finding.evaluationId, bucket);
  }

  return rows.map((row) => ({
    id: row.id,
    projectId: row.projectId,
    runId: row.runId,
    packetId: row.packetId,
    invocationId: row.invocationId,
    triggerKind: row.triggerKind,
    evaluatorVersion: row.evaluatorVersion,
    summary: row.summary,
    createdAt: row.createdAt,
    findings: findingsByEvaluation.get(row.id) ?? [],
  }));
};

export const listConsistencyFindings = (
  db: Database.Database,
  options: { projectId?: string | null; runId?: string; limit?: number } = {},
): ConsistencyFinding[] =>
  listConsistencyEvaluations(db, { projectId: options.projectId, runId: options.runId, limit: options.limit }).flatMap(
    (evaluation) => evaluation.findings,
  );

export const reviewWriteback = (
  db: Database.Database,
  input: { writebackId: string; decision: "applied" | "rejected"; note?: string | null; actor?: string },
): ImprovementWriteback => {
  ensureControlPlaneSchema(db);
  const current = db
    .prepare(
      `
      SELECT
        run_id AS runId,
        status,
        summary
      FROM improvement_writebacks
      WHERE id = ?
      LIMIT 1
    `,
    )
    .get(input.writebackId) as
    | {
        runId: string | null;
        status: ImprovementWriteback["status"];
        summary: string;
      }
    | undefined;

  if (!current) {
    throw new Error("Writeback not found.");
  }

  const decisionAt = nowIso();
  db.prepare(
    `
    UPDATE improvement_writebacks
    SET status = ?,
        decision_note = ?,
        decision_actor = ?,
        decision_at = ?,
        updated_at = ?
    WHERE id = ?
  `,
  ).run(input.decision, input.note ?? null, input.actor ?? "operator", decisionAt, decisionAt, input.writebackId);

  recordWritebackEvent(db, {
    writebackId: input.writebackId,
    runId: current.runId,
    eventType: input.decision === "applied" ? "approved" : "rejected",
    fromStatus: current.status,
    toStatus: input.decision,
    actor: input.actor ?? "operator",
    note: input.note ?? current.summary,
  });

  const row = db
    .prepare(
      `
      SELECT
        id,
        run_id AS runId,
        project_id AS projectId,
        layer_type AS layerType,
        layer_key AS layerKey,
        title,
        summary,
        evidence_json AS evidenceJson,
        proposed_change_json AS proposedChangeJson,
        impact_scope AS impactScope,
        status,
        requires_approval AS requiresApproval,
        approval_reason AS approvalReason,
        token_regressive AS tokenRegressive,
        created_at AS createdAt,
        updated_at AS updatedAt,
        decision_note AS decisionNote,
        decision_actor AS decisionActor,
        decision_at AS decisionAt
      FROM improvement_writebacks
      WHERE id = ?
      LIMIT 1
    `,
    )
    .get(input.writebackId) as {
    id: string;
    runId: string | null;
    projectId: string | null;
    layerType: ImprovementWriteback["layerType"];
    layerKey: string;
    title: string;
    summary: string;
    evidenceJson: string;
    proposedChangeJson: string;
    impactScope: string;
    status: ImprovementWriteback["status"];
    requiresApproval: number;
    approvalReason: string | null;
    tokenRegressive: number;
    createdAt: string;
    updatedAt: string;
    decisionNote: string | null;
    decisionActor: string | null;
    decisionAt: string | null;
  };

  return {
    id: row.id,
    runId: row.runId,
    projectId: row.projectId,
    layerType: row.layerType,
    layerKey: row.layerKey,
    title: row.title,
    summary: row.summary,
    evidence: parseJsonArray<string[]>(row.evidenceJson, []),
    proposedChange: parseJsonRecord(row.proposedChangeJson),
    impactScope: row.impactScope,
    status: row.status,
    requiresApproval: Boolean(row.requiresApproval),
    approvalReason: row.approvalReason,
    tokenRegressive: Boolean(row.tokenRegressive),
    createdAt: row.createdAt,
    updatedAt: row.updatedAt,
    decisionNote: row.decisionNote,
    decisionActor: row.decisionActor,
    decisionAt: row.decisionAt,
  };
};

export const startManagedInvocation = (
  db: Database.Database,
  input: { runId: string },
): { invocationId: string; backend: InvocationBackend } => {
  ensureControlPlaneSchema(db);
  const run = db
    .prepare(
      `
      SELECT
        id,
        project_id AS projectId,
        objective,
        workflow_key AS workflowKey,
        agent_key AS agentKey,
        status,
        backend_key AS backendKey,
        session_id AS sessionId
      FROM orchestration_runs
      WHERE id = ?
      LIMIT 1
    `,
    )
    .get(input.runId) as
    | {
        id: string;
        projectId: string | null;
        objective: string;
        workflowKey: string;
        agentKey: string;
        status: OrchestrationRunStatus;
        backendKey: string | null;
        sessionId: string | null;
      }
    | undefined;

  if (!run) {
    throw new Error("Run not found.");
  }
  if (run.status === "in_progress") {
    throw new Error("Run is already in progress.");
  }

  const backend = findInvocationBackend(run.backendKey ?? "aios-managed-runtime");
  const root = resolveAiosRoot();
  const scriptPath = path.join(root, "bin", "aios-managed-run.py");
  const invocationId = `invoke-${randomUUID()}`;
  const createdAt = nowIso();
  const command = ["python3", scriptPath, "--run-id", run.id, "--invocation-id", invocationId];

  db.prepare(
    `
    INSERT INTO orchestration_invocations (
      id,
      run_id,
      backend_key,
      backend_label,
      status,
      handshake_token,
      command_json,
      metadata_json,
      created_at,
      updated_at
    )
    VALUES (?, ?, ?, ?, 'launching', ?, ?, '{}', ?, ?)
  `,
  ).run(invocationId, run.id, backend.key, backend.label, run.id, JSON.stringify(command), createdAt, createdAt);

  db.prepare(
    `
    UPDATE orchestration_runs
    SET backend_key = ?,
        active_invocation_id = ?,
        updated_at = ?
    WHERE id = ?
  `,
  ).run(backend.key, invocationId, createdAt, run.id);

  recordRunEvent(db, {
    runId: run.id,
    projectId: run.projectId,
    invocationId,
    eventType: "invocation_requested",
    fromStatus: run.status,
    toStatus: run.status,
    summary: `Invocation requested via ${backend.label}.`,
    metadata: {
      backendKey: backend.key,
      command,
    },
    createdAt,
  });

  try {
    const child = spawn(command[0], command.slice(1), {
      cwd: root,
      detached: true,
      stdio: "ignore",
      env: {
        ...process.env,
        AIOS_RUN_ID: run.id,
        AIOS_INVOCATION_ID: invocationId,
        AIOS_BACKEND_KEY: backend.key,
      },
    });
    child.unref();

    db.prepare(
      `
      UPDATE orchestration_invocations
      SET pid = ?,
          metadata_json = ?,
          updated_at = ?
      WHERE id = ?
    `,
    ).run(
      child.pid,
      JSON.stringify({
        spawnedAt: createdAt,
        command,
      }),
      nowIso(),
      invocationId,
    );
  } catch (error) {
    db.prepare(
      `
      UPDATE orchestration_invocations
      SET status = 'failed',
          metadata_json = ?,
          ended_at = ?,
          updated_at = ?
      WHERE id = ?
    `,
    ).run(
      JSON.stringify({
        launchError: error instanceof Error ? error.message : String(error),
      }),
      nowIso(),
      nowIso(),
      invocationId,
    );
    transitionRun(db, {
      runId: run.id,
      toStatus: "failed",
      eventType: "failed",
      summary: "Managed invocation failed to launch.",
      invocationId,
      reason: {
        kind: "launch_error",
        message: error instanceof Error ? error.message : String(error),
      },
    });
    throw error;
  }

  return { invocationId, backend };
};

export const cancelManagedInvocation = (
  db: Database.Database,
  input: { runId: string },
): void => {
  ensureControlPlaneSchema(db);
  const current = db
    .prepare(
      `
      SELECT
        id,
        pid,
        status
      FROM orchestration_invocations
      WHERE run_id = ?
      ORDER BY created_at DESC
      LIMIT 1
    `,
    )
    .get(input.runId) as
    | {
        id: string;
        pid: number | null;
        status: OrchestrationInvocation["status"];
      }
    | undefined;

  if (!current || !current.pid) {
    throw new Error("No active managed invocation to cancel.");
  }

  process.kill(current.pid, "SIGTERM");

  db.prepare(
    `
    UPDATE orchestration_invocations
    SET metadata_json = ?,
        updated_at = ?
    WHERE id = ?
  `,
  ).run(
    JSON.stringify({
      cancelRequestedAt: nowIso(),
      priorStatus: current.status,
    }),
    nowIso(),
    current.id,
  );

  recordRunEvent(db, {
    runId: input.runId,
    invocationId: current.id,
    eventType: "cancel_requested",
    summary: "Cancellation signal sent to managed invocation.",
    metadata: { pid: current.pid },
  });
};

export const getRunDetail = (db: Database.Database, run: OrchestrationRun): ControlPlaneRunDetail => {
  const writebacks = db
    .prepare(
      `
      SELECT
        id,
        run_id AS runId,
        project_id AS projectId,
        layer_type AS layerType,
        layer_key AS layerKey,
        title,
        summary,
        evidence_json AS evidenceJson,
        proposed_change_json AS proposedChangeJson,
        impact_scope AS impactScope,
        status,
        requires_approval AS requiresApproval,
        approval_reason AS approvalReason,
        token_regressive AS tokenRegressive,
        created_at AS createdAt,
        updated_at AS updatedAt,
        decision_note AS decisionNote,
        decision_actor AS decisionActor,
        decision_at AS decisionAt
      FROM improvement_writebacks
      WHERE run_id = ?
      ORDER BY created_at DESC
    `,
    )
    .all(run.id) as Array<{
      id: string;
      runId: string | null;
      projectId: string | null;
      layerType: ImprovementWriteback["layerType"];
      layerKey: string;
      title: string;
      summary: string;
      evidenceJson: string;
      proposedChangeJson: string;
      impactScope: string;
      status: ImprovementWriteback["status"];
      requiresApproval: number;
      approvalReason: string | null;
      tokenRegressive: number;
      createdAt: string;
      updatedAt: string;
      decisionNote: string | null;
      decisionActor: string | null;
      decisionAt: string | null;
    }>;

  const hydratedWritebacks = writebacks.map((row) => ({
    id: row.id,
    runId: row.runId,
    projectId: row.projectId,
    layerType: row.layerType,
    layerKey: row.layerKey,
    title: row.title,
    summary: row.summary,
    evidence: parseJsonArray<string[]>(row.evidenceJson, []),
    proposedChange: parseJsonRecord(row.proposedChangeJson),
    impactScope: row.impactScope,
    status: row.status,
    requiresApproval: Boolean(row.requiresApproval),
    approvalReason: row.approvalReason,
    tokenRegressive: Boolean(row.tokenRegressive),
    createdAt: row.createdAt,
    updatedAt: row.updatedAt,
    decisionNote: row.decisionNote,
    decisionActor: row.decisionActor,
    decisionAt: row.decisionAt,
  }));

  return {
    run,
    events: listRunEvents(db, run.id),
    invocations: listRunInvocations(db, run.id),
    writebacks: hydratedWritebacks,
    writebackEvents: listWritebackEvents(
      db,
      hydratedWritebacks.map((writeback) => writeback.id),
    ),
    evaluations: listConsistencyEvaluations(db, { runId: run.id, limit: 6 }),
  };
};
