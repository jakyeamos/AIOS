import { z } from "zod";

import type { Session, SessionStatus, ToolEvent, ToolEventType } from "@/lib/types";
import { tableExists } from "@/server/db";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

type SessionRow = {
  id: string;
  projectId: string;
  projectName: string;
  tool: string;
  startedAt: string;
  endedAt: string | null;
  objective: string | null;
  status: string;
  cwd: string | null;
  durationMs: number | null;
  promptCount: number;
  toolEventCount: number;
  artifactCount: number;
};

type ToolEventRow = {
  id: string;
  sessionId: string;
  sourceTool: string;
  eventType: string;
  eventTime: string;
  payloadJson: string;
};

type PromptBreakdownRow = {
  classification: string | null;
  count: number;
};

type ArtifactRow = {
  id: string;
  artifactType: string;
  path: string | null;
  createdAt: string;
};

type BugRow = {
  id: string;
  symptom: string;
  rootCause: string | null;
  fix: string | null;
  status: string;
  createdAt: string;
};

const normalizeSessionStatus = (status: string): SessionStatus => {
  if (status === "open" || status === "closed" || status === "abandoned") {
    return status;
  }

  return "open";
};

const normalizeTool = (tool: string): Session["tool"] => {
  if (tool === "codex" || tool === "claude-code" || tool === "desktop-claude") {
    return tool;
  }

  return "codex";
};

const normalizeEventType = (eventType: string): ToolEventType => {
  if (
    eventType === "SessionStart" ||
    eventType === "UserPromptSubmit" ||
    eventType === "PreToolUse" ||
    eventType === "PostToolUse" ||
    eventType === "Stop" ||
    eventType === "SubagentStop" ||
    eventType === "PreCompact"
  ) {
    return eventType;
  }

  return "PreToolUse";
};

const parsePayload = (payloadJson: string): Record<string, unknown> => {
  try {
    const parsed = JSON.parse(payloadJson) as unknown;
    if (typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }

    return { value: parsed };
  } catch {
    return { raw: payloadJson };
  }
};

const mapSession = (row: SessionRow): Session => ({
  id: row.id,
  projectId: row.projectId,
  projectName: row.projectName,
  tool: normalizeTool(row.tool),
  startedAt: row.startedAt,
  endedAt: row.endedAt,
  objective: row.objective,
  status: normalizeSessionStatus(row.status),
  cwd: row.cwd,
  durationMs: row.durationMs,
  promptCount: row.promptCount,
  toolEventCount: row.toolEventCount,
  artifactCount: row.artifactCount,
});

const mapToolEvent = (row: ToolEventRow): ToolEvent => ({
  id: row.id,
  sessionId: row.sessionId,
  sourceTool: row.sourceTool,
  eventType: normalizeEventType(row.eventType),
  eventTime: row.eventTime,
  payloadJson: parsePayload(row.payloadJson),
});

type RootCauseSignal = {
  severity: "warning" | "error";
  signal: string;
  detail: string;
};

const hasEventError = (event: ToolEvent): boolean => {
  const payload = event.payloadJson;
  const errorText = typeof payload.error === "string" ? payload.error : null;
  const stderrText = typeof payload.stderr === "string" ? payload.stderr : null;
  const exitCode = typeof payload.exitCode === "number" ? payload.exitCode : null;

  if (errorText && errorText.trim().length > 0) {
    return true;
  }

  if (stderrText && stderrText.trim().length > 0) {
    return true;
  }

  return exitCode !== null && exitCode !== 0;
};

const inferRootCauseSignals = (
  session: Session,
  events: ToolEvent[],
  bugs: BugRow[],
): RootCauseSignal[] => {
  const signals: RootCauseSignal[] = [];
  const preToolCount = events.filter((event) => event.eventType === "PreToolUse").length;
  const postToolCount = events.filter((event) => event.eventType === "PostToolUse").length;
  const errorEventCount = events.filter(hasEventError).length;

  if (session.status === "abandoned") {
    signals.push({
      severity: "warning",
      signal: "Session was abandoned",
      detail: "Run ended without explicit completion.",
    });
  }

  if (preToolCount > postToolCount) {
    signals.push({
      severity: "warning",
      signal: "Tool imbalance",
      detail: `${preToolCount - postToolCount} tool call(s) started without a matching completion event.`,
    });
  }

  if (errorEventCount > 0) {
    signals.push({
      severity: "error",
      signal: "Error payloads detected",
      detail: `${errorEventCount} event(s) include error/stderr/exitCode signals.`,
    });
  }

  if (bugs.length > 0) {
    signals.push({
      severity: "error",
      signal: "Linked bug records",
      detail: `${bugs.length} bug log record(s) reference this run.`,
    });
  }

  return signals;
};

export const sessionsRouter = createTRPCRouter({
  list: publicProcedure
    .input(z.object({ limit: z.number().int().min(1).max(200).default(20) }).optional())
    .query(({ ctx, input }): Session[] => {
      if (!tableExists("sessions") || !tableExists("projects")) {
        return [];
      }

      const limit = input?.limit ?? 20;
      const rows = ctx.db
        .prepare(
          `
          SELECT
            s.id,
            s.project_id AS projectId,
            p.name AS projectName,
            s.tool,
            s.started_at AS startedAt,
            s.ended_at AS endedAt,
            s.objective,
            s.status,
            s.cwd,
            CASE
              WHEN s.ended_at IS NULL THEN NULL
              ELSE CAST((julianday(s.ended_at) - julianday(s.started_at)) * 86400000 AS INTEGER)
            END AS durationMs,
            (SELECT COUNT(*) FROM prompts_used pu WHERE pu.session_id = s.id) AS promptCount,
            (SELECT COUNT(*) FROM tool_events te WHERE te.session_id = s.id) AS toolEventCount,
            (SELECT COUNT(*) FROM artifacts a WHERE a.session_id = s.id) AS artifactCount
          FROM sessions s
          INNER JOIN projects p ON p.id = s.project_id
          ORDER BY s.started_at DESC
          LIMIT ?
        `,
        )
        .all(limit) as SessionRow[];

      return rows.map(mapSession);
    }),

  detail: publicProcedure
    .input(z.object({ id: z.string().min(1) }))
    .query(
      ({
        ctx,
        input,
      }): {
        session: Session | null;
        events: ToolEvent[];
        eventTypeBreakdown: Array<{ eventType: ToolEvent["eventType"]; count: number }>;
        sourceToolBreakdown: Array<{ sourceTool: string; count: number }>;
        promptBreakdown: Array<{ classification: string; count: number }>;
        artifacts: ArtifactRow[];
        bugRows: BugRow[];
        rootCauseSignals: RootCauseSignal[];
      } => {
      if (!tableExists("sessions") || !tableExists("projects")) {
        return {
          session: null,
          events: [],
          eventTypeBreakdown: [],
          sourceToolBreakdown: [],
          promptBreakdown: [],
          artifacts: [],
          bugRows: [],
          rootCauseSignals: [],
        };
      }

      const row = ctx.db
        .prepare(
          `
          SELECT
            s.id,
            s.project_id AS projectId,
            p.name AS projectName,
            s.tool,
            s.started_at AS startedAt,
            s.ended_at AS endedAt,
            s.objective,
            s.status,
            s.cwd,
            CASE
              WHEN s.ended_at IS NULL THEN NULL
              ELSE CAST((julianday(s.ended_at) - julianday(s.started_at)) * 86400000 AS INTEGER)
            END AS durationMs,
            (SELECT COUNT(*) FROM prompts_used pu WHERE pu.session_id = s.id) AS promptCount,
            (SELECT COUNT(*) FROM tool_events te WHERE te.session_id = s.id) AS toolEventCount,
            (SELECT COUNT(*) FROM artifacts a WHERE a.session_id = s.id) AS artifactCount
          FROM sessions s
          INNER JOIN projects p ON p.id = s.project_id
          WHERE s.id = ?
          LIMIT 1
        `,
        )
        .get(input.id) as SessionRow | undefined;

      const events = tableExists("tool_events")
        ? ((ctx.db
            .prepare(
              `
              SELECT
                id,
                session_id AS sessionId,
                source_tool AS sourceTool,
                event_type AS eventType,
                event_time AS eventTime,
                payload_json AS payloadJson
              FROM tool_events
              WHERE session_id = ?
              ORDER BY event_time ASC
            `,
            )
            .all(input.id) as ToolEventRow[])
            .map(mapToolEvent)
            .slice(-120))
        : [];

      const promptBreakdown = tableExists("prompts_used")
        ? ((ctx.db
            .prepare(
              `
              SELECT
                classification,
                COUNT(*) AS count
              FROM prompts_used
              WHERE session_id = ?
              GROUP BY classification
              ORDER BY count DESC
            `,
            )
            .all(input.id) as PromptBreakdownRow[]).map((promptRow) => ({
            classification: promptRow.classification ?? "other",
            count: promptRow.count,
          })))
        : [];

      const artifacts = tableExists("artifacts")
        ? (ctx.db
            .prepare(
              `
              SELECT
                id,
                artifact_type AS artifactType,
                path,
                created_at AS createdAt
              FROM artifacts
              WHERE session_id = ?
              ORDER BY created_at DESC
              LIMIT 40
            `,
            )
            .all(input.id) as ArtifactRow[])
        : [];

      const bugRows = tableExists("bug_log")
        ? (ctx.db
            .prepare(
              `
              SELECT
                id,
                symptom,
                root_cause AS rootCause,
                fix,
                status,
                created_at AS createdAt
              FROM bug_log
              WHERE session_id = ?
              ORDER BY created_at DESC
              LIMIT 20
            `,
            )
            .all(input.id) as BugRow[])
        : [];

      const eventTypeBreakdown = Array.from(
        events.reduce<Map<ToolEvent["eventType"], number>>((acc, event) => {
          acc.set(event.eventType, (acc.get(event.eventType) ?? 0) + 1);
          return acc;
        }, new Map()),
      )
        .map(([eventType, count]) => ({ eventType, count }))
        .sort((left, right) => right.count - left.count);

      const sourceToolBreakdown = Array.from(
        events.reduce<Map<string, number>>((acc, event) => {
          acc.set(event.sourceTool, (acc.get(event.sourceTool) ?? 0) + 1);
          return acc;
        }, new Map()),
      )
        .map(([sourceTool, count]) => ({ sourceTool, count }))
        .sort((left, right) => right.count - left.count);

      return {
        session: row ? mapSession(row) : null,
        events,
        eventTypeBreakdown,
        sourceToolBreakdown,
        promptBreakdown,
        artifacts,
        bugRows,
        rootCauseSignals: row ? inferRootCauseSignals(mapSession(row), events, bugRows) : [],
      };
    }),

  recentEvents: publicProcedure
    .input(z.object({ limit: z.number().int().min(1).max(100).default(20) }).optional())
    .query(({ ctx, input }): ToolEvent[] => {
      if (!tableExists("tool_events")) {
        return [];
      }

      const limit = input?.limit ?? 20;
      const rows = ctx.db
        .prepare(
          `
          SELECT
            id,
            session_id AS sessionId,
            source_tool AS sourceTool,
            event_type AS eventType,
            event_time AS eventTime,
            payload_json AS payloadJson
          FROM tool_events
          ORDER BY event_time DESC
          LIMIT ?
        `,
        )
        .all(limit) as ToolEventRow[];

      return rows.map(mapToolEvent);
    }),
});
