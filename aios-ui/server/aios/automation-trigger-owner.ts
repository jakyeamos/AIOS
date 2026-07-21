import { execFileSync } from "node:child_process";
import os from "node:os";
import path from "node:path";

import { resolveAiosRoot } from "@/server/aios/filesystem";

export type AutomationTriggerInput = {
  automationId: string;
  workflowKey: string;
  objective: string;
  projectId?: string | null;
};

type PythonRun = {
  id: string;
  project_id: string | null;
  project_name: string | null;
  session_id: string | null;
  objective: string;
  workflow_key: string;
  agent_key: string;
  status: string;
  rationale: string;
  assumptions: string[];
  context_trace: unknown[];
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  started_at: string | null;
  failed_at: string | null;
  canceled_at: string | null;
  backend_key: string | null;
  active_invocation_id: string | null;
  superseded_by_run_id: string | null;
  status_reason: Record<string, unknown>;
  result_summary: string | null;
  memory_update_id: string | null;
  packet_id: string | null;
  route_id: string | null;
  route_status: string | null;
  route_result: Record<string, unknown>;
};

type PythonPacket = {
  id: string;
  run_id: string;
  project_id: string | null;
  objective: string;
  workflow_key: string;
  agent_key: string;
  created_at: string;
  policy_mode: string;
  token_budget: number;
  markdown: string;
  sections: unknown[];
  selection_trace: unknown[];
  omitted_context: unknown[];
  route_id: string | null;
  route_result: Record<string, unknown>;
  contract_version: string;
};

type PythonInvocation = {
  id: string;
  status: string;
  backend_key: string;
  backend_label: string;
  session_id: string | null;
  handshake_token: string;
  pid: number | null;
  command: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
  updated_at: string;
};

type PythonRunDetail = {
  run: PythonRun;
  events: unknown[];
  invocations: PythonInvocation[];
  writebacks: unknown[];
  writeback_events: unknown[];
  evaluations: unknown[];
  inspection: Record<string, unknown>;
};

type PythonResult = {
  automation_id: string;
  recommended_workflow_key: string;
  plan: { run: PythonRun; packet: PythonPacket };
  invocation: { run_detail: PythonRunDetail };
};

type PythonEnvelope = {
  data?: PythonResult;
  error?: { message?: string };
};

type AutomationRun = {
  id: string;
  projectId: string | null;
  projectName: string;
  sessionId: string | null;
  objective: string;
  workflowKey: string;
  agentKey: string;
  status: string;
  rationale: string;
  assumptions: string[];
  contextTrace: unknown[];
  createdAt: string;
  updatedAt: string;
  completedAt: string | null;
  startedAt: string | null;
  failedAt: string | null;
  canceledAt: string | null;
  backendKey: string | null;
  activeInvocationId: string | null;
  supersededByRunId: string | null;
  statusReason: Record<string, unknown>;
  resultSummary: string | null;
  memoryUpdateId: string | null;
  packetId: string | null;
  routeId: string | null;
  routeStatus: string | null;
  routeResult: Record<string, unknown> | null;
};

type AutomationPacket = {
  id: string;
  runId: string;
  projectId: string | null;
  objective: string;
  workflowKey: string;
  agentKey: string;
  createdAt: string;
  markdown: string;
  sections: unknown[];
  policyMode: string;
  tokenBudget: number;
  selectionTrace: unknown[];
  omittedContext: unknown[];
  routeId: string | null;
  routeResult: Record<string, unknown> | null;
};

type AutomationInvocation = {
  id: string;
  runId: string;
  backendKey: string;
  backendLabel: string;
  status: string;
  handshakeToken: string;
  sessionId: string | null;
  pid: number | null;
  command: string[];
  metadata: Record<string, unknown>;
  createdAt: string;
  startedAt: string | null;
  endedAt: string | null;
  updatedAt: string;
};

export type AutomationTriggerResult = {
  automationId: string;
  recommendedWorkflowKey: string;
  plan: { run: AutomationRun; packet: AutomationPacket };
  invocation: {
    runDetail: {
      run: AutomationRun;
      events: unknown[];
      invocations: AutomationInvocation[];
      writebacks: unknown[];
      writebackEvents: unknown[];
      evaluations: unknown[];
      inspection: Record<string, unknown>;
    };
  };
};

const resolveDbPath = (): string => {
  const configuredPath = process.env.AIOS_DB?.trim();
  if (!configuredPath) {
    return path.join(os.homedir(), "AIOS", "data", "aios.db");
  }
  if (configuredPath === "~") {
    return os.homedir();
  }
  if (configuredPath.startsWith("~/")) {
    return path.join(os.homedir(), configuredPath.slice(2));
  }
  return path.resolve(configuredPath);
};

const mapRun = (run: PythonRun): AutomationRun => ({
  id: run.id,
  projectId: run.project_id,
  projectName: run.project_name ?? "Unscoped",
  sessionId: run.session_id,
  objective: run.objective,
  workflowKey: run.workflow_key,
  agentKey: run.agent_key,
  status: run.status,
  rationale: run.rationale,
  assumptions: run.assumptions,
  contextTrace: run.context_trace,
  createdAt: run.created_at,
  updatedAt: run.updated_at,
  completedAt: run.completed_at,
  startedAt: run.started_at,
  failedAt: run.failed_at,
  canceledAt: run.canceled_at,
  backendKey: run.backend_key,
  activeInvocationId: run.active_invocation_id,
  supersededByRunId: run.superseded_by_run_id,
  statusReason: run.status_reason,
  resultSummary: run.result_summary,
  memoryUpdateId: run.memory_update_id,
  packetId: run.packet_id,
  routeId: run.route_id,
  routeStatus: run.route_status,
  routeResult: run.route_result,
});

const mapPacket = (packet: PythonPacket): AutomationPacket => ({
  id: packet.id,
  runId: packet.run_id,
  projectId: packet.project_id,
  objective: packet.objective,
  workflowKey: packet.workflow_key,
  agentKey: packet.agent_key,
  createdAt: packet.created_at,
  markdown: packet.markdown,
  sections: packet.sections,
  policyMode: packet.policy_mode,
  tokenBudget: packet.token_budget,
  selectionTrace: packet.selection_trace,
  omittedContext: packet.omitted_context,
  routeId: packet.route_id,
  routeResult: packet.route_result,
});

const mapInvocation = (invocation: PythonInvocation, run: AutomationRun): AutomationInvocation => ({
  id: invocation.id,
  runId: run.id,
  backendKey: invocation.backend_key,
  backendLabel: invocation.backend_label,
  status: invocation.status,
  handshakeToken: invocation.handshake_token,
  sessionId: invocation.session_id,
  pid: invocation.pid,
  command: invocation.command,
  metadata: invocation.metadata,
  createdAt: invocation.created_at,
  startedAt: invocation.started_at,
  endedAt: invocation.ended_at,
  updatedAt: invocation.updated_at,
});

export const triggerAutomationViaPythonOwner = (
  input: AutomationTriggerInput,
): AutomationTriggerResult => {
  const root = resolveAiosRoot();
  const script = path.join(root, "bin", "aios.py");
  try {
    const output = execFileSync(
      "python3",
      [
        script,
        "--json",
        "--db",
        resolveDbPath(),
        "automation-trigger",
        "--payload-json",
        JSON.stringify(input),
      ],
      {
        cwd: root,
        encoding: "utf8",
        maxBuffer: 2 * 1024 * 1024,
      },
    );
    const envelope = JSON.parse(output) as PythonEnvelope;
    if (!envelope.data) {
      throw new Error(envelope.error?.message ?? "Python owner returned no automation trigger payload.");
    }
    const run = mapRun(envelope.data.plan.run);
    const packet = mapPacket(envelope.data.plan.packet);
    const runDetail = envelope.data.invocation.run_detail;
    return {
      automationId: envelope.data.automation_id,
      recommendedWorkflowKey: envelope.data.recommended_workflow_key,
      plan: { run, packet },
      invocation: {
        runDetail: {
          run,
          events: runDetail.events,
          invocations: runDetail.invocations.map((invocation) => mapInvocation(invocation, run)),
          writebacks: runDetail.writebacks,
          writebackEvents: runDetail.writeback_events,
          evaluations: runDetail.evaluations,
          inspection: runDetail.inspection,
        },
      },
    };
  } catch (error) {
    if (error instanceof Error && error.message.startsWith("Python owner returned")) {
      throw error;
    }
    throw new Error("Python automation owner rejected the trigger.", { cause: error });
  }
};
