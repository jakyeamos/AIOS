export type KnowledgePageKind = "project" | "decision" | "workflow" | "agent" | "system";

export type HealthStatus = "healthy" | "warning" | "error" | "unknown";

export type KnowledgeRelationship = {
  label: string;
  href: string;
  kind: KnowledgePageKind;
  relation: string;
};

export type KnowledgeReference = {
  label: string;
  href: string;
  detail: string;
};

export type KnowledgeSection = {
  title: string;
  body?: string;
  items: string[];
};

export type ChangeItem = {
  id: string;
  title: string;
  summary: string;
  timestamp: string;
  href?: string;
  kind: "session" | "decision" | "packet" | "memory" | "bug";
  confidence: number;
};

export type KnowledgePageSummary = {
  slug: string;
  title: string;
  kind: KnowledgePageKind;
  summary: string;
  status: HealthStatus;
  freshness: string;
  confidence: number;
  tags: string[];
};

export type KnowledgePageDetail = KnowledgePageSummary & {
  references: KnowledgeReference[];
  relationships: KnowledgeRelationship[];
  backlinks: KnowledgeRelationship[];
  sections: KnowledgeSection[];
  recentChanges: ChangeItem[];
};

export type AgentProfile = {
  key: string;
  name: string;
  summary: string;
  bestFor: string[];
  guardrails: string[];
};

export type WorkflowTemplate = {
  key: string;
  name: string;
  summary: string;
  triggers: string[];
  deliverables: string[];
  validation: string[];
};

export type PacketSection = {
  title: string;
  body?: string;
  items: string[];
};

export type ContextTrace = {
  source: string;
  reason: string;
  freshness: string;
  confidence: number;
};

export type BriefingPacket = {
  id: string;
  runId: string;
  projectId: string | null;
  objective: string;
  workflowKey: string;
  agentKey: string;
  createdAt: string;
  markdown: string;
  sections: PacketSection[];
};

export type OrchestrationRun = {
  id: string;
  projectId: string | null;
  projectName: string;
  objective: string;
  workflowKey: string;
  agentKey: string;
  status: "planned" | "ready" | "executed" | "superseded";
  rationale: string;
  assumptions: string[];
  contextTrace: ContextTrace[];
  createdAt: string;
  packetId: string | null;
};

export type GroundedCitation = {
  label: string;
  href: string;
  excerpt: string;
};

export type GroundedAnswer = {
  question: string;
  intent: "what_changed" | "project_state" | "decision_why" | "agent_brief" | "system_state";
  answer: string;
  facts: string[];
  inferences: string[];
  recommendations: string[];
  assumptions: string[];
  citations: GroundedCitation[];
  retrievalTrace: ContextTrace[];
};
