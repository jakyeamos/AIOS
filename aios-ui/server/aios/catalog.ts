import type { AgentProfile, InvocationBackend, WorkflowTemplate } from "@/lib/control-plane";

export const invocationBackends: InvocationBackend[] = [
  {
    key: "codex-managed-runtime",
    label: "Codex Managed Runtime",
    summary: "Starts a managed Codex-oriented local session with explicit run/invocation handshake, lifecycle events, and cancel support.",
    transport: "managed_session",
    supportsCancel: true,
    commandPreview: ["python3", "bin/aios-managed-run.py", "--backend-key", "codex-managed-runtime"],
    surface: "codex",
  },
  {
    key: "claude-managed-runtime",
    label: "Claude Managed Runtime",
    summary: "Starts a managed Claude-oriented local session with the same strict handshake and workflow reporting contract.",
    transport: "managed_session",
    supportsCancel: true,
    commandPreview: ["python3", "bin/aios-managed-run.py", "--backend-key", "claude-managed-runtime"],
    surface: "claude_code",
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
  },
];

export const findInvocationBackend = (key: string): InvocationBackend =>
  invocationBackends.find((backend) => backend.key === key) ?? invocationBackends[0];

export const findWorkflowTemplate = (objective: string): WorkflowTemplate => {
  const lower = objective.toLowerCase();

  if (
    lower.includes("knowledge") ||
    lower.includes("control plane") ||
    lower.includes("orchestration") ||
    lower.includes("second brain")
  ) {
    return workflowTemplates[0];
  }

  if (lower.includes("debug") || lower.includes("fix") || lower.includes("broken")) {
    return workflowTemplates[2];
  }

  return workflowTemplates[1];
};

export const findAgentProfile = (objective: string): AgentProfile => {
  const lower = objective.toLowerCase();

  if (lower.includes("audit") || lower.includes("architecture")) {
    return agentProfiles[0];
  }

  if (lower.includes("debug") || lower.includes("fix") || lower.includes("failure")) {
    return agentProfiles[2];
  }

  if (lower.includes("memory") || lower.includes("decision") || lower.includes("handoff")) {
    return agentProfiles[3];
  }

  return agentProfiles[1];
};
