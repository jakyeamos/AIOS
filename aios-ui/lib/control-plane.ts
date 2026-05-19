export type KnowledgePageKind = "project" | "decision" | "workflow" | "agent" | "system" | "concept";

export type HealthStatus = "healthy" | "warning" | "error" | "unknown";

export type KnowledgeRelationship = {
  label: string;
  href: string;
  kind: KnowledgePageKind;
  relation: string;
};

export type KnowledgeAuthorityState = "accepted" | "proposed" | "inferred";

export type KnowledgeAuthorityLink = {
  id: string;
  title: string;
  href: string;
  kind: KnowledgePageKind | "prompt" | "skill" | "research" | "truth";
  authority: KnowledgeAuthorityState;
  summary: string;
  evidence: string[];
};

export type TruthKnowledgeBoundary = {
  acceptedTruth: KnowledgeAuthorityLink[];
  proposedKnowledge: KnowledgeAuthorityLink[];
  inferredKnowledge: KnowledgeAuthorityLink[];
  linkRules: string[];
  summary: {
    acceptedCount: number;
    proposedCount: number;
    inferredCount: number;
    reviewRequired: boolean;
  };
};

export type KnowledgeReference = {
  label: string;
  href: string;
  detail: string;
};

export type WikiPageStatus =
  | "current"
  | "planned"
  | "deprecated"
  | "historical"
  | "experimental"
  | "unverified";

export type WikiConfidence = "high" | "medium" | "low" | "unknown";

export type WikiSourceRef = {
  type:
    | "code"
    | "doc"
    | "prd"
    | "test"
    | "task"
    | "agent_summary"
    | "external"
    | "pattern"
    | "session"
    | "run"
    | "packet"
    | "memory_update"
    | "knowledge_topic"
    | "vault_note"
    | "imported_conversation";
  path: string;
  label?: string;
  lineStart?: number;
  lineEnd?: number;
  lastCheckedAt?: string;
};

export type WikiSourceCoverage = "strong" | "partial" | "weak" | "none";

export type WikiMaintenanceMetadata = {
  status: WikiPageStatus;
  confidence: WikiConfidence;
  maintenanceScore: number;
  lastIndexedAt?: string;
  lastValidatedAt?: string;
  validatedBy?: "human" | "agent" | "script" | "unknown";
  sourceRefs: WikiSourceRef[];
  sourceCoverage: WikiSourceCoverage;
  knownStaleAreas: string[];
  relatedPages: string[];
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

export type OrchestrationInvocationStatus =
  | "queued"
  | "launching"
  | "running"
  | "completed"
  | "failed"
  | "canceled";

export type KnowledgePageSummary = {
  slug: string;
  title: string;
  kind: KnowledgePageKind;
  summary: string;
  status: HealthStatus;
  freshness: string;
  confidence: number;
  tags: string[];
  maintenance: WikiMaintenanceMetadata;
};

export type KnowledgePageDetail = KnowledgePageSummary & {
  references: KnowledgeReference[];
  relationships: KnowledgeRelationship[];
  backlinks: KnowledgeRelationship[];
  sections: KnowledgeSection[];
  recentChanges: ChangeItem[];
  agentPacket: WikiAgentPacket;
};

export type WikiAgentPacket = {
  subsystem: string;
  status: WikiPageStatus;
  confidence: WikiConfidence;
  maintenanceScore: number;
  lastValidated: string;
  knownStaleAreas: string[];
  relevantWikiPages: Array<{ title: string; href: string; status: WikiPageStatus }>;
  sourceFilesToInspect: WikiSourceRef[];
  applicableStandards: string[];
  knownRisks: string[];
  currentVsPlannedNotes: string[];
  verificationChecklist: string[];
};

export type AgentProfile = {
  key: string;
  name: string;
  summary: string;
  bestFor: string[];
  guardrails: string[];
  defaultBackendKey: string;
};

export type WorkflowTemplate = {
  key: string;
  name: string;
  summary: string;
  triggers: string[];
  deliverables: string[];
  validation: string[];
  defaultBackendKey: string;
};

export type InvocationBackend = {
  key: "codex-managed-runtime" | "claude-managed-runtime" | "manual-session-legacy";
  label: string;
  summary: string;
  transport: "managed_session" | "manual_session";
  supportsCancel: boolean;
  commandPreview: string[];
  surface: "codex" | "claude_code" | "manual";
  deprecated?: boolean;
  requiresStrictHandshake?: boolean;
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

export type RouteProjectCandidate = {
  id: string;
  name: string;
  repo_path: string;
  obsidian_path: string;
  status: string;
  score: number;
  match_kind: string;
  rationale: string;
};

export type RouteProjectResolution = {
  outcome: "exact" | "likely" | "ambiguous" | "unsupported";
  selected_project_id: string | null;
  rationale: string;
  candidates: RouteProjectCandidate[];
};

export type RouteRecommendation = {
  objective: string;
  surface: string;
  project: RouteProjectResolution;
  selected_workflow: Record<string, unknown> | null;
  workflow_candidates: Array<Record<string, unknown>>;
  prompt_recommendation: Record<string, unknown> | null;
  backend_recommendation: Record<string, unknown> | null;
  agent_recommendation: Record<string, unknown> | null;
  task_family: string | null;
  blocked_reason: string | null;
  rationale: string;
  route_id?: string;
  status?: string;
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
  routeId: string | null;
  routeResult: RouteRecommendation | null;
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
  routeResult: RouteRecommendation | null;
};

export type OrchestrationRunEvent = {
  id: string;
  runId: string;
  projectId: string | null;
  sessionId: string | null;
  invocationId: string | null;
  eventType: string;
  fromStatus: OrchestrationRunStatus | null;
  toStatus: OrchestrationRunStatus | null;
  summary: string;
  reason: Record<string, unknown>;
  metadata: Record<string, unknown>;
  createdAt: string;
};

export type OrchestrationInvocation = {
  id: string;
  runId: string;
  backendKey: string;
  backendLabel: string;
  status: OrchestrationInvocationStatus;
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
  proposedChange: Record<string, unknown>;
  impactScope: string;
  status: "proposed" | "pending_approval" | "applied" | "rejected";
  requiresApproval: boolean;
  approvalReason: string | null;
  tokenRegressive: boolean;
  createdAt: string;
  updatedAt: string;
  decisionNote: string | null;
  decisionActor: string | null;
  decisionAt: string | null;
};

export type ImprovementWritebackEvent = {
  id: string;
  writebackId: string;
  runId: string | null;
  eventType: string;
  fromStatus: ImprovementWriteback["status"] | null;
  toStatus: ImprovementWriteback["status"] | null;
  actor: string;
  note: string | null;
  metadata: Record<string, unknown>;
  createdAt: string;
};

export type ConsistencyFindingKind =
  | "direct_contradiction"
  | "likely_stale"
  | "soft_tension"
  | "workflow_state_gap"
  | "packet_result_delta"
  | "file_topic_delta"
  | "standards_evidence_gap";
export type ConsistencyFindingResolutionStatus =
  | "open"
  | "accepted_tradeoff"
  | "mitigated"
  | "dismissed"
  | "reopened";

export type ConsistencyFinding = {
  id: string;
  evaluationId: string;
  projectId: string | null;
  runId: string | null;
  packetId: string | null;
  topicSlug: string | null;
  findingKind: ConsistencyFindingKind;
  severity: "info" | "warning" | "error";
  ruleKey: string;
  summary: string;
  provenance: Array<Record<string, unknown>>;
  metadata: Record<string, unknown>;
  resolutionStatus: ConsistencyFindingResolutionStatus;
  resolutionActor: string | null;
  resolutionRationale: string | null;
  resolutionEvidence: Array<Record<string, unknown>>;
  resolvedAt: string | null;
  createdAt: string;
};

export type ConsistencyEvaluation = {
  id: string;
  projectId: string | null;
  runId: string | null;
  packetId: string | null;
  invocationId: string | null;
  triggerKind: string;
  evaluatorVersion: string;
  summary: string;
  createdAt: string;
  findings: ConsistencyFinding[];
};

export type ControlPlaneRunDetail = {
  run: OrchestrationRun;
  events: OrchestrationRunEvent[];
  invocations: OrchestrationInvocation[];
  writebacks: ImprovementWriteback[];
  writebackEvents: ImprovementWritebackEvent[];
  evaluations: ConsistencyEvaluation[];
  inspection: RunInspection;
};

export type RunInspection = {
  packetId: string | null;
  selectedSections: Array<{ title: string; itemCount: number }>;
  omittedContextCount: number;
  touchedFiles: string[];
  packetMentionedFiles: string[];
  unpredictedTouchedFiles: string[];
  standardsDeltas: Array<{
    standardId: string;
    status: StandardsAssessmentStatus;
    estimatedHealthImpact: number;
    priorityBucket: StandardsDeltaItem["priorityBucket"];
  }>;
  unresolvedFindings: Array<{
    id: string;
    ruleKey: string;
    severity: ConsistencyFinding["severity"];
    summary: string;
  }>;
  riskCarryover: string[];
};

export type StandardsAssessmentStatus = "pass" | "partial" | "fail" | "unknown" | "waived" | "not_applicable";

export type StandardsDomainScore = {
  domain: string;
  score: number;
  confidence: number;
  weight: number;
};

export type StandardsDeltaItem = {
  id: string;
  standardId: string;
  domain: string;
  severity: number;
  status: StandardsAssessmentStatus;
  summary: string;
  estimatedHealthImpact: number;
  blockers: string[];
  foundational: boolean;
  linkedTaskIds: string[];
  priorityScore: number;
  priorityBucket: "foundational" | "high_leverage" | "quick_wins" | "blocked" | "waived_deferred";
};

export type StandardsBackfillTask = {
  id: string;
  deltaItemId: string;
  standardId: string;
  title: string;
  problemStatement: string;
  expectedState: string;
  acceptanceCriteria: string[];
  effort: number;
  dependencyChain: string[];
  expectedHealthImpact: number;
  owner: string | null;
  blockedReason: string | null;
  dueAt: string | null;
  reviewAt: string | null;
  priorityScore: number;
  priorityBucket: StandardsDeltaItem["priorityBucket"];
  blocked: boolean;
  status: string;
};

export type StandardsMigration = {
  attachedVersion: string;
  latestVersion: string;
  migrationDeltaCount: number;
  migrationWeight: number;
  items: Array<{
    standardId: string;
    title: string;
    domain: string;
    introducedVersion: string;
    weight: number;
  }>;
};

export type StandardsHealthSummary = {
  snapshotId: string;
  profileId: string;
  attachedVersion: string;
  latestVersion: string;
  overallScore: number;
  weightedDelta: number;
  unmetStandardsCount: number;
  criticalDeltaCount: number;
  regressionCount: number;
  unknownCount: number;
  unknownCoverage: number;
  evaluationConfidence: number;
  createdAt: string;
  domainScores: StandardsDomainScore[];
  deltaItems: StandardsDeltaItem[];
  backfillTasks: StandardsBackfillTask[];
  migration: StandardsMigration;
};

export type QualityPipelineGateStatus = "pass" | "fail" | "running" | "stale" | "missing" | "blocked" | "unknown";

export type QualityPipelineOverallStatus = "healthy" | "warning" | "error" | "blocked" | "unknown";

export type QualityPipelineGateTier = "tier_1_core" | "production_app" | "domain_specific";

export type QualityPipelineGate = {
  key: string;
  label: string;
  tier: QualityPipelineGateTier;
  applicable: boolean;
  applicability: string[];
  required: boolean;
  configured: boolean;
  status: QualityPipelineGateStatus;
  command: string | null;
  workingDirectory: string | null;
  latestRunId: string | null;
  source: string | null;
  evidence: string[];
  completedAt: string | null;
  blockedReason: string | null;
};

export type QualityPipelineSummary = {
  projectId: string;
  standardVersion: string;
  fullPipeline: boolean;
  overallStatus: QualityPipelineOverallStatus;
  blockedReason: string | null;
  coverage: {
    required: number;
    configuredRequired: number;
    passingRequired: number;
    total: number;
  };
  coverageByTier: Record<QualityPipelineGateTier, {
    required: number;
    configuredRequired: number;
    passingRequired: number;
    total: number;
  }>;
  gates: QualityPipelineGate[];
};

export type AiosProjectComponentKey =
  | "taski_summary"
  | "knowledge_dossier"
  | "standards_health"
  | "quality_pipeline"
  | "learning_writebacks"
  | "active_runs";

export type AiosProjectComponentSetting = {
  key: AiosProjectComponentKey;
  label: string;
  summary: string;
  enabled: boolean;
  updatedAt: string | null;
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
  consistencyFindings: ConsistencyFinding[];
  pendingApprovals: ImprovementWriteback[];
  suggestedNextActions: string[];
  standardsHealth: StandardsHealthSummary | null;
  qualityPipeline: QualityPipelineSummary;
  aiosComponents: AiosProjectComponentSetting[];
};
