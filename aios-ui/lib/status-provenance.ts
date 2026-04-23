import type {
  ChangeItem,
  HealthStatus,
  ImprovementWriteback,
  OrchestrationRun,
} from "@/lib/control-plane";
import type { AutomationHealth, Experiment } from "@/lib/types";

export type ProvenanceLevel = "confirmed" | "inferred" | "stale" | "missing";

export type SourceBackedStatus = {
  label: string;
  tone: HealthStatus;
  provenance: ProvenanceLevel;
  reason: string;
  source: string;
  observedAt: string | null;
  stalenessMinutes: number | null;
};

export type AttentionAlert = {
  id: string;
  severity: "error" | "warning" | "info";
  title: string;
  detail: string;
  source: string;
};

export type TimelineEntry = {
  id: string;
  kind: "run" | "approval" | "change" | "experiment";
  title: string;
  summary: string;
  timestamp: string;
  source: string;
};

const parseTimestamp = (value: string | null | undefined): number | null => {
  if (!value) {
    return null;
  }
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? null : parsed;
};

const ageMinutes = (value: string | null | undefined, nowMs: number): number | null => {
  const parsed = parseTimestamp(value);
  if (parsed === null) {
    return null;
  }
  return Math.max(0, Math.round((nowMs - parsed) / 60000));
};

const toneForRunStatus = (status: OrchestrationRun["status"]): HealthStatus => {
  if (status === "completed") {
    return "healthy";
  }
  if (status === "failed") {
    return "error";
  }
  if (status === "canceled" || status === "superseded") {
    return "warning";
  }
  return "unknown";
};

const runTerminalTimestamp = (run: OrchestrationRun): string | null => {
  if (run.status === "completed") {
    return run.completedAt;
  }
  if (run.status === "failed") {
    return run.failedAt;
  }
  if (run.status === "canceled") {
    return run.canceledAt;
  }
  if (run.status === "superseded") {
    return run.updatedAt;
  }
  return null;
};

export const assessRunStatus = (
  run: OrchestrationRun,
  nowMs = Date.now(),
): SourceBackedStatus => {
  const lastUpdated = run.updatedAt ?? run.startedAt ?? run.createdAt;
  const staleness = ageMinutes(lastUpdated, nowMs);
  const tone = toneForRunStatus(run.status);

  if (!lastUpdated) {
    return {
      label: run.status,
      tone: "unknown",
      provenance: "missing",
      reason: "Run has no usable timestamp metadata.",
      source: "orchestration_runs",
      observedAt: null,
      stalenessMinutes: null,
    };
  }

  const terminalTimestamp = runTerminalTimestamp(run);
  const isTerminal =
    run.status === "completed" ||
    run.status === "failed" ||
    run.status === "canceled" ||
    run.status === "superseded";

  if (isTerminal) {
    if (terminalTimestamp) {
      return {
        label: run.status,
        tone,
        provenance: "confirmed",
        reason: "Terminal run state has explicit timestamp evidence.",
        source: "orchestration_runs + orchestration_run_events",
        observedAt: terminalTimestamp,
        stalenessMinutes: staleness,
      };
    }

    return {
      label: run.status,
      tone,
      provenance: "inferred",
      reason: "Terminal run state exists without dedicated terminal timestamp.",
      source: "orchestration_runs",
      observedAt: lastUpdated,
      stalenessMinutes: staleness,
    };
  }

  if (staleness !== null && staleness > 90) {
    return {
      label: run.status,
      tone: "warning",
      provenance: "stale",
      reason: "Non-terminal run has not emitted updates in more than 90 minutes.",
      source: "orchestration_runs",
      observedAt: lastUpdated,
      stalenessMinutes: staleness,
    };
  }

  if (run.status === "in_progress" && !run.activeInvocationId) {
    return {
      label: run.status,
      tone: "warning",
      provenance: "inferred",
      reason: "Run is in_progress without an active invocation linkage.",
      source: "orchestration_runs",
      observedAt: lastUpdated,
      stalenessMinutes: staleness,
    };
  }

  return {
    label: run.status,
    tone,
    provenance: "confirmed",
    reason: "Run state is backed by active run metadata and recent updates.",
    source: "orchestration_runs",
    observedAt: lastUpdated,
    stalenessMinutes: staleness,
  };
};

const toneForWritebackStatus = (status: ImprovementWriteback["status"]): HealthStatus => {
  if (status === "applied") {
    return "healthy";
  }
  if (status === "rejected") {
    return "error";
  }
  if (status === "pending_approval") {
    return "warning";
  }
  return "unknown";
};

export const assessWritebackStatus = (
  writeback: ImprovementWriteback,
  nowMs = Date.now(),
): SourceBackedStatus => {
  const staleness = ageMinutes(writeback.updatedAt, nowMs);

  if (!writeback.updatedAt) {
    return {
      label: writeback.status,
      tone: "unknown",
      provenance: "missing",
      reason: "Writeback has no updated_at value.",
      source: "improvement_writebacks",
      observedAt: null,
      stalenessMinutes: null,
    };
  }

  if (writeback.status === "pending_approval") {
    if (staleness !== null && staleness > 1440) {
      return {
        label: writeback.status,
        tone: "warning",
        provenance: "stale",
        reason: "Pending approval has not been reviewed for more than 24 hours.",
        source: "improvement_writebacks",
        observedAt: writeback.updatedAt,
        stalenessMinutes: staleness,
      };
    }

    return {
      label: writeback.status,
      tone: "warning",
      provenance: writeback.requiresApproval ? "confirmed" : "inferred",
      reason: writeback.requiresApproval
        ? "Writeback is explicitly gated for human approval."
        : "Writeback appears pending without explicit approval requirement.",
      source: "improvement_writebacks",
      observedAt: writeback.updatedAt,
      stalenessMinutes: staleness,
    };
  }

  return {
    label: writeback.status,
    tone: toneForWritebackStatus(writeback.status),
    provenance: "confirmed",
    reason: "Writeback status is persisted with decision metadata.",
    source: "improvement_writebacks",
    observedAt: writeback.updatedAt,
    stalenessMinutes: staleness,
  };
};

export const buildAttentionAlerts = (
  runs: OrchestrationRun[],
  writebacks: ImprovementWriteback[],
  automations: AutomationHealth[],
): AttentionAlert[] => {
  const nowMs = Date.now();
  const alerts: AttentionAlert[] = [];

  const staleRuns = runs.filter((run) => assessRunStatus(run, nowMs).provenance === "stale");
  if (staleRuns.length > 0) {
    alerts.push({
      id: "stale-runs",
      severity: "warning",
      title: "Stale orchestration runs",
      detail: `${staleRuns.length} run(s) have no update in >90 minutes.`,
      source: "orchestration_runs",
    });
  }

  const failedRuns = runs.filter((run) => run.status === "failed");
  if (failedRuns.length > 0) {
    alerts.push({
      id: "failed-runs",
      severity: "error",
      title: "Failed runs need triage",
      detail: `${failedRuns.length} run(s) are currently failed.`,
      source: "orchestration_runs + orchestration_run_events",
    });
  }

  const pendingApprovals = writebacks.filter((writeback) => writeback.status === "pending_approval");
  if (pendingApprovals.length > 0) {
    alerts.push({
      id: "pending-approvals",
      severity: "warning",
      title: "Approvals waiting",
      detail: `${pendingApprovals.length} writeback proposal(s) require operator action.`,
      source: "improvement_writebacks",
    });
  }

  const brokenAutomations = automations.filter((automation) => automation.status === "error");
  if (brokenAutomations.length > 0) {
    alerts.push({
      id: "automation-errors",
      severity: "error",
      title: "Automation failures detected",
      detail: `${brokenAutomations.length} automation(s) are currently in error state.`,
      source: "automation health surface",
    });
  }

  if (alerts.length === 0) {
    alerts.push({
      id: "steady-state",
      severity: "info",
      title: "No immediate blockers",
      detail: "No high-severity failure, staleness, or approval backlog detected.",
      source: "command-center aggregate",
    });
  }

  return alerts;
};

export const buildCommandCenterTimeline = (params: {
  runs: OrchestrationRun[];
  writebacks: ImprovementWriteback[];
  changes: ChangeItem[];
  experiments: Experiment[];
}): TimelineEntry[] => {
  const runEntries: TimelineEntry[] = params.runs.map((run) => ({
    id: `run-${run.id}`,
    kind: "run",
    title: `Run ${run.status}: ${run.workflowKey}`,
    summary: run.resultSummary ?? run.objective,
    timestamp: run.updatedAt,
    source: "orchestration_runs",
  }));

  const writebackEntries: TimelineEntry[] = params.writebacks.map((writeback) => ({
    id: `approval-${writeback.id}`,
    kind: "approval",
    title: `Writeback ${writeback.status}: ${writeback.title}`,
    summary: `${writeback.layerType}/${writeback.layerKey} · ${writeback.impactScope}`,
    timestamp: writeback.updatedAt,
    source: "improvement_writebacks",
  }));

  const changeEntries: TimelineEntry[] = params.changes.map((change) => ({
    id: `change-${change.id}`,
    kind: "change",
    title: change.title,
    summary: change.summary,
    timestamp: change.timestamp,
    source: "changes feed",
  }));

  const experimentEntries: TimelineEntry[] = params.experiments.map((experiment) => ({
    id: `experiment-${experiment.id}`,
    kind: "experiment",
    title: `Experiment ${experiment.verdict ?? "active"}: ${experiment.name}`,
    summary: experiment.hypothesis,
    timestamp: experiment.endedAt ?? experiment.startedAt,
    source: "experiments",
  }));

  return [...runEntries, ...writebackEntries, ...changeEntries, ...experimentEntries]
    .filter((entry) => parseTimestamp(entry.timestamp) !== null)
    .sort((left, right) => (parseTimestamp(right.timestamp) ?? 0) - (parseTimestamp(left.timestamp) ?? 0));
};
