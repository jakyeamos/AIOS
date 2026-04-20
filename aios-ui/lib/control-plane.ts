export type KnowledgePageKind = "project" | "decision" | "workflow" | "agent" | "system" | "concept";

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

export type OrchestrationRunStatus =
  | "planned"
  | "ready"
  | "in_progress"
  | "completed"
  | "failed"
  | "canceled"
  | "superseded";

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

export type PacketPolicyMode = "compact-ranked" | "explore";

export type ContextTrace = {
  source: string;
  reason: string;
  freshness: string;
  confidence: number;
};

export type PacketSelectionTraceItem = {
  section: string;
  label: string;
  sourceKind: string;
  sourceHref: string;
  score: number;
  reason: string;
};

export type OmittedContextItem = {
  label: string;
  sourceKind: string;
  score: number;
  reason: string;
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
  policyMode: PacketPolicyMode;
  tokenBudget: number;
  selectionTrace: PacketSelectionTraceItem[];
  omittedContext: OmittedContextItem[];
};

export type OrchestrationRun = {
  id: string;
  projectId: string | null;
  projectName: string;
  sessionId: string | null;
  objective: string;
  workflowKey: string;
  agentKey: string;
  status: OrchestrationRunStatus;
  rationale: string;
  assumptions: string[];
  contextTrace: ContextTrace[];
  createdAt: string;
  updatedAt: string;
  completedAt: string | null;
  resultSummary: string | null;
  memoryUpdateId: string | null;
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

export type TopicGraphKind = KnowledgePageKind | "task_type" | "policy";

export type TopicGraphTopic = {
  id: string;
  slug: string;
  title: string;
  kind: TopicGraphKind;
  summary: string;
  confidence: number;
  freshness: string;
  tags: string[];
  canonicalHref: string;
  referenceCount: number;
  markerCount: number;
};

export type TopicGraphRelationship = {
  relation: string;
  fromSlug: string;
  toSlug: string;
  fromTitle: string;
  toTitle: string;
  weight: number;
};

export type TopicGraphReference = {
  sourceKind: string;
  sourceId: string | null;
  label: string;
  href: string;
  excerpt: string;
  freshness: string;
  confidence: number;
};

export type TopicGraphMarker = {
  kind: "contradiction" | "drift" | "stale";
  severity: "warning" | "error" | "info";
  summary: string;
  sourceRef: string | null;
};

export type PacketExpansionKind = "topic" | "failure_pattern" | "code_area" | "policy" | "recent_run";

export type PacketExpansion = {
  id: string;
  runId: string | null;
  packetId: string;
  projectId: string | null;
  requestKind: PacketExpansionKind;
  requestTarget: string;
  tokenBudget: number;
  status: "completed";
  returnedContext: string[];
  trace: ContextTrace[];
  createdAt: string;
};

export type ImprovementLayerType = "topic" | "project" | "workflow" | "task_type" | "global_policy";

export type ImprovementWriteback = {
  id: string;
  runId: string | null;
  projectId: string | null;
  layerType: ImprovementLayerType;
  layerKey: string;
  title: string;
  summary: string;
  evidence: string[];
  status: "proposed" | "pending_approval" | "applied" | "rejected";
  requiresApproval: boolean;
  approvalReason: string | null;
  tokenRegressive: boolean;
  createdAt: string;
};

export type TaskiProjectSummary = {
  projectId: string;
  projectTitle: string;
  status: HealthStatus;
  freshness: string;
  overview: string;
  topTopics: TopicGraphTopic[];
  activeRuns: OrchestrationRun[];
  blockers: string[];
  recentFailures: string[];
  recentSuccesses: string[];
  learnedPolicies: ImprovementWriteback[];
  driftMarkers: TopicGraphMarker[];
  suggestedNextActions: string[];
};
