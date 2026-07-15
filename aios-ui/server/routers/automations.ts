import { z } from "zod";

import { seededAutomations } from "@/lib/seed";
import type { AutomationHealth } from "@/lib/types";
import { trustedSignal } from "@/lib/trusted-signals";
import { triggerAutomationViaPythonOwner } from "@/server/aios/automation-trigger-owner";
import { ensureControlPlaneSchema } from "@/server/aios/schema";
import { tableExists } from "@/server/db";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

type AutomationStatus = AutomationHealth["status"];
type AutomationUrgency = AutomationHealth["urgency"];

type AutomationHistoryRow = {
  runCount: number;
  successCount: number;
  failureCount: number;
  lastRunAt: string | null;
  nextRunAt: string | null;
};

type LastAutomationRunRow = {
  status: string;
  failureSummary: string | null;
  approvalBlockersJson: string;
  writebackBlockersJson: string;
} | null;

const dayNames: Record<string, string> = {
  MO: "Mon",
  TU: "Tue",
  WE: "Wed",
  TH: "Thu",
  FR: "Fri",
  SA: "Sat",
  SU: "Sun",
};

const parseRrule = (trigger: string): Record<string, string> => {
  const entries = trigger
    .split(";")
    .map((part) => part.split("="))
    .filter((part): part is [string, string] => part.length === 2 && part[0].length > 0);
  return Object.fromEntries(entries);
};

const formatHour = (hour: string | undefined, minute: string | undefined): string => {
  const parsedHour = Number(hour ?? "0");
  const parsedMinute = Number(minute ?? "0");
  if (!Number.isInteger(parsedHour) || !Number.isInteger(parsedMinute)) {
    return "unknown time";
  }
  const suffix = parsedHour >= 12 ? "PM" : "AM";
  const displayHour = parsedHour % 12 === 0 ? 12 : parsedHour % 12;
  return `${displayHour}:${parsedMinute.toString().padStart(2, "0")} ${suffix}`;
};

const formatTrigger = (trigger: string): string => {
  const rule = parseRrule(trigger);
  const days = (rule.BYDAY ?? "").split(",").filter((day) => day.length > 0);
  const time = formatHour(rule.BYHOUR, rule.BYMINUTE);

  if (days.length === 5 && days.every((day) => ["MO", "TU", "WE", "TH", "FR"].includes(day))) {
    return `Weekdays at ${time}`;
  }
  if (days.length === 7) {
    return `Daily at ${time}`;
  }
  if (days.length > 0) {
    return `${days.map((day) => dayNames[day] ?? day).join(", ")} at ${time}`;
  }
  return trigger;
};

const parseBlockers = (value: string | null): string[] => {
  if (!value) {
    return [];
  }
  try {
    const parsed: unknown = JSON.parse(value);
    if (Array.isArray(parsed)) {
      return parsed.filter((item): item is string => typeof item === "string");
    }
  } catch {
    return [];
  }
  return [];
};

const normalizeRunStatus = (status: string | null): AutomationStatus => {
  if (status === "success" || status === "healthy" || status === "completed") {
    return "healthy";
  }
  if (status === "warning") {
    return "warning";
  }
  if (status === "error" || status === "failed" || status === "failure") {
    return "error";
  }
  return "unknown";
};

const latestRunFailed = (status: string | null): boolean => {
  return status !== null && !["success", "healthy", "completed", "warning"].includes(status);
};

const urgencyFor = (
  runCount: number,
  failureCount: number,
  latestStatus: string | null,
  blockers: string[],
): AutomationUrgency => {
  if (runCount === 0) {
    return "watch";
  }
  if (blockers.length > 0) {
    return "blocked";
  }
  if (latestRunFailed(latestStatus)) {
    return "action_required";
  }
  if (failureCount > 0) {
    return "watch";
  }
  return "none";
};

const enrichAutomation = (
  automation: AutomationHealth,
  history: AutomationHistoryRow,
  lastRun: LastAutomationRunRow,
): AutomationHealth => {
  const triggerLabel = formatTrigger(automation.trigger);
  const approvalBlockers = parseBlockers(lastRun?.approvalBlockersJson ?? null);
  const writebackBlockers = parseBlockers(lastRun?.writebackBlockersJson ?? null);
  const blockers = [...approvalBlockers, ...writebackBlockers];
  const successRate = history.runCount > 0 ? history.successCount / history.runCount : null;
  const status = history.runCount > 0 ? normalizeRunStatus(lastRun?.status ?? null) : "unknown";
  const missingHistory = history.runCount === 0 ? "No durable automation run history exists for this automation." : null;
  return {
    ...automation,
    triggerLabel,
    successRate,
    status,
    urgency: urgencyFor(history.runCount, history.failureCount, lastRun?.status ?? null, blockers),
    lastRunAt: history.lastRunAt,
    nextRunAt: history.nextRunAt,
    lastFailureSummary: lastRun?.failureSummary ?? null,
    approvalBlockers,
    writebackBlockers,
    triggerSignal: trustedSignal({
      value: triggerLabel,
      provenance: triggerLabel === automation.trigger ? "missing" : "inferred",
      confidence: triggerLabel === automation.trigger ? 0.3 : 0.8,
      source: { label: "Automation trigger", field: "trigger" },
      freshness: "seeded",
      explanation: triggerLabel === automation.trigger
        ? "Trigger is not recognized as a supported RRULE shape."
        : "Readable schedule is inferred from the persisted RRULE trigger.",
      missingReason: triggerLabel === automation.trigger ? "Unsupported trigger format." : null,
      contradiction: null,
    }),
    successRateSignal: trustedSignal({
      value: successRate,
      provenance: history.runCount > 0 ? "confirmed" : "missing",
      confidence: history.runCount > 0 ? 0.9 : 0,
      source: { label: "Automation run history", table: "automation_run_history", field: "status" },
      freshness: history.runCount > 0 ? `${history.runCount} durable run(s)` : "missing",
      explanation: "Success rate is derived from durable automation run history.",
      missingReason: missingHistory,
      contradiction: null,
    }),
    statusSignal: trustedSignal({
      value: status,
      provenance: history.runCount > 0 ? "confirmed" : "missing",
      confidence: history.runCount > 0 ? 0.9 : 0,
      source: { label: "Automation run history", table: "automation_run_history", field: "status" },
      freshness: history.runCount > 0 ? `${history.runCount} durable run(s)` : "missing",
      explanation: "Status is derived from durable automation run history.",
      missingReason: missingHistory,
      contradiction: null,
    }),
  };
};

export const automationsRouter = createTRPCRouter({
  list: publicProcedure.query(({ ctx }): AutomationHealth[] => {
    ensureControlPlaneSchema(ctx.db);
    const hasHistory = tableExists("automation_run_history");
    return seededAutomations.map((automation) => {
      const history = hasHistory
        ? ctx.db
            .prepare(
              `
              SELECT
                COUNT(*) AS runCount,
                COALESCE(SUM(CASE WHEN status IN ('success', 'healthy', 'completed') THEN 1 ELSE 0 END), 0) AS successCount,
                COALESCE(SUM(CASE WHEN status NOT IN ('success', 'healthy', 'completed') THEN 1 ELSE 0 END), 0) AS failureCount,
                MAX(started_at) AS lastRunAt,
                MAX(expected_next_run_at) AS nextRunAt
              FROM automation_run_history
              WHERE automation_id = ?
              `,
            )
            .get(automation.id) as AutomationHistoryRow
        : { runCount: 0, successCount: 0, failureCount: 0, lastRunAt: null, nextRunAt: null };
      const lastRun = hasHistory
        ? (ctx.db
            .prepare(
              `
              SELECT
                status,
                failure_summary AS failureSummary,
                approval_blockers_json AS approvalBlockersJson,
                writeback_blockers_json AS writebackBlockersJson
              FROM automation_run_history
              WHERE automation_id = ?
              ORDER BY COALESCE(started_at, created_at) DESC
              LIMIT 1
              `,
            )
            .get(automation.id) as LastAutomationRunRow)
        : null;
      return enrichAutomation(automation, history, lastRun);
    });
  }),

  triggerWorkflow: publicProcedure
    .input(
      z.object({
        automationId: z.string().min(1),
        workflowKey: z.string().min(1),
        objective: z.string().min(8).max(500),
        projectId: z.string().min(1).nullable().optional(),
      }),
    )
    .mutation(({ input }) => triggerAutomationViaPythonOwner(input)),
});
