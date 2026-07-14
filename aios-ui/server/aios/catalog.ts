import type { AgentProfile, InvocationBackend, WorkflowTemplate } from "@/lib/control-plane";
import { workflowTemplateCatalog } from "@/server/generated/workflow-catalog";

export const invocationBackends: InvocationBackend[] = [
  {
    key: "codex-managed-runtime",
    label: "Codex Managed Runtime",
    summary: "Starts a managed Codex-oriented local session with explicit run/invocation handshake, lifecycle events, and cancel support.",
    transport: "managed_session",
    supportsCancel: true,
    commandPreview: ["python3", "bin/aios-managed-run.py", "--backend-key", "codex-managed-runtime"],
    surface: "codex",
    isSeedData: true,
  },
  {
    key: "claude-managed-runtime",
    label: "Claude Managed Runtime",
    summary: "Starts a managed Claude-oriented local session with the same strict handshake and workflow reporting contract.",
    transport: "managed_session",
    supportsCancel: true,
    commandPreview: ["python3", "bin/aios-managed-run.py", "--backend-key", "claude-managed-runtime"],
    surface: "claude_code",
    isSeedData: true,
  },
  {
    key: "manual-session-legacy",
    label: "Manual Session (Legacy)",
    summary: "Deprecated manual path. New external/manual sessions must register a strict run/invocation/session handshake.",
    transport: "manual_session",
    supportsCancel: false,
    commandPreview: ["manual", "strict-handshake-required"],
    surface: "manual",
    deprecated: true,
    requiresStrictHandshake: true,
    isSeedData: true,
  },
];

export const agentProfiles: AgentProfile[] = [
  {
    key: "principal-auditor",
    name: "Principal Auditor",
    summary: "Audits architecture, state boundaries, and system risks before implementation.",
    bestFor: [
      "architecture review",
      "product/system gap analysis",
      "control-plane redesign",
    ],
    guardrails: [
      "Prefer removing weak abstractions over preserving them.",
      "Write architectural rationale and tradeoffs as durable artifacts.",
    ],
    defaultBackendKey: "claude-managed-runtime",
    isSeedData: true,
  },
  {
    key: "implementation-lead",
    name: "Implementation Lead",
    summary: "Turns approved architecture into maintainable modules, routes, and UI surfaces.",
    bestFor: [
      "refactors",
      "feature implementation",
      "state-model changes",
    ],
    guardrails: [
      "Favor thin pages and concentrated server-side helper logic.",
      "Expose inspectability instead of hiding behavior in prompts.",
    ],
    defaultBackendKey: "codex-managed-runtime",
    isSeedData: true,
  },
  {
    key: "debug-surgeon",
    name: "Debug Surgeon",
    summary: "Focuses on failed runs, brittle integrations, regressions, and recovery paths.",
    bestFor: [
      "bug fixes",
      "workflow failures",
      "run-forensics",
    ],
    guardrails: [
      "Use existing evidence before proposing new abstraction.",
      "Record failure mode and recovery path into durable memory.",
    ],
    defaultBackendKey: "codex-managed-runtime",
    isSeedData: true,
  },
  {
    key: "memory-curator",
    name: "Memory Curator",
    summary: "Captures decisions, drift, continuity notes, and reusable knowledge after execution.",
    bestFor: [
      "post-run updates",
      "decision capture",
      "knowledge maintenance",
    ],
    guardrails: [
      "Separate durable knowledge from transient workflow state.",
      "Do not elevate staging content into canonical knowledge.",
    ],
    defaultBackendKey: "claude-managed-runtime",
    isSeedData: true,
  },
];

export const workflowTemplates: WorkflowTemplate[] = [
  {
    key: "knowledge-os-evolution",
    name: "Knowledge OS Evolution",
    summary: "Audit and refactor AIOS into explicit knowledge, memory, and control-plane layers.",
    triggers: [
      "knowledge system redesign",
      "second brain architecture work",
      "control-plane productization",
    ],
    deliverables: [
      "audit artifact",
      "target architecture changes",
      "briefing packet",
      "handoff update",
    ],
    validation: [
      "Schema and UI boundaries are explicit.",
      "Routing, retrieval, and packet generation are inspectable.",
    ],
    defaultBackendKey: "codex-managed-runtime",
    isSeedData: true,
  },
  {
    key: "implementation-delivery",
    name: "Implementation Delivery",
    summary: "Curate the minimum context needed to implement a scoped feature or refactor.",
    triggers: [
      "feature work",
      "refactor",
      "build request",
    ],
    deliverables: [
      "task-specific packet",
      "likely files list",
      "acceptance criteria",
      "validation checklist",
    ],
    validation: [
      "Packet includes constraints, non-goals, and escalation conditions.",
      "Relevant architecture and prior decisions are cited.",
    ],
    defaultBackendKey: "codex-managed-runtime",
    isSeedData: true,
  },
  {
    key: "failure-recovery",
    name: "Failure Recovery",
    summary: "Route debugging work through failure evidence, prior attempts, and risk containment.",
    triggers: [
      "debugging",
      "failed run",
      "broken workflow",
    ],
    deliverables: [
      "failure brief",
      "root cause trail",
      "risk list",
      "retest plan",
    ],
    validation: [
      "Original symptom is captured.",
      "Recovery steps and unresolved questions are logged.",
    ],
    defaultBackendKey: "codex-managed-runtime",
    isSeedData: true,
  },
];

export type CatalogSnapshot = {
  workflowTemplates: WorkflowTemplate[];
  agentProfiles: AgentProfile[];
  invocationBackends: InvocationBackend[];
};

export const getCatalogSnapshot = (): CatalogSnapshot => ({
  workflowTemplates: workflowTemplateCatalog,
  agentProfiles,
  invocationBackends,
});

export const findInvocationBackend = (key: string): InvocationBackend =>
  getCatalogSnapshot().invocationBackends.find((backend) => backend.key === key) ?? invocationBackends[0];

export const findWorkflowTemplate = (objective: string): WorkflowTemplate => {
  const lower = objective.toLowerCase();
  const snapshot = getCatalogSnapshot();

  if (
    lower.includes("knowledge") ||
    lower.includes("control plane") ||
    lower.includes("orchestration") ||
    lower.includes("second brain")
  ) {
    return snapshot.workflowTemplates.find((workflow) => workflow.key === "knowledge-os-evolution") ?? workflowTemplates[0];
  }

  if (lower.includes("debug") || lower.includes("fix") || lower.includes("broken")) {
    return snapshot.workflowTemplates.find((workflow) => workflow.key === "failure-recovery") ?? workflowTemplates[2];
  }

  return snapshot.workflowTemplates.find((workflow) => workflow.key === "implementation-delivery") ?? workflowTemplates[1];
};

export const findAgentProfile = (objective: string): AgentProfile => {
  const lower = objective.toLowerCase();
  const snapshot = getCatalogSnapshot();

  if (lower.includes("audit") || lower.includes("architecture")) {
    return snapshot.agentProfiles[0];
  }

  if (lower.includes("debug") || lower.includes("fix") || lower.includes("failure")) {
    return snapshot.agentProfiles[2];
  }

  if (lower.includes("memory") || lower.includes("decision") || lower.includes("handoff")) {
    return snapshot.agentProfiles[3];
  }

  return snapshot.agentProfiles[1];
};
