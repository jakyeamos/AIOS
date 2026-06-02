import type { TrustedSignal } from "@/lib/trusted-signals";

export type SessionStatus = "open" | "closed" | "abandoned";

export type Session = {
  id: string;
  projectId: string;
  projectName: string;
  tool: "claude-code" | "codex" | "desktop-claude";
  startedAt: string;
  endedAt: string | null;
  objective: string | null;
  status: SessionStatus;
  cwd: string | null;
  durationMs: number | null;
  promptCount: number;
  toolEventCount: number;
  artifactCount: number;
};

export type ToolEventType =
  | "SessionStart"
  | "UserPromptSubmit"
  | "PreToolUse"
  | "PostToolUse"
  | "Stop"
  | "SubagentStop"
  | "PreCompact";

export type ToolEvent = {
  id: string;
  sessionId: string;
  sourceTool: string;
  eventType: ToolEventType;
  eventTime: string;
  payloadJson: Record<string, unknown>;
};

export type PromptClassification =
  | "debugging"
  | "planning"
  | "refactor"
  | "review"
  | "explain"
  | "implement"
  | "other";

export type Prompt = {
  id: string;
  sessionId: string;
  promptHash: string | null;
  promptText: string | null;
  classification: PromptClassification;
  outcomeScore: number | null;
  reusableCandidate: boolean;
  retrievalFired: boolean;
  retrievalSource: string | null;
};

export type PromptTemplate = {
  id: string;
  name: string;
  version: string;
  classification: string;
  tags: string[];
  purpose: string;
  requiredInputs: string[];
  optionalInputs: string[];
  lastUpdated: string;
  file: string;
  path: string;
};

export type PatternState = "notice" | "observation" | "hypothesis" | "rule";

export type Pattern = {
  id: string;
  label: string | null;
  state: PatternState;
  humanApproved: boolean;
  sessionCount: number;
  lastSeen: string;
};

export type ExperimentWinner = "baseline" | "challenger" | "inconclusive" | null;

export type Experiment = {
  id: string;
  name: string;
  surface: string;
  hypothesis: string;
  baselineValue: number | null;
  challengerValue: number | null;
  verdict: string | null;
  startedAt: string;
  endedAt: string | null;
  notes: string | null;
  delta: number | null;
  winner: ExperimentWinner;
};

export type ExperimentTestRepo = {
  id: string;
  name: string;
  profile: string;
  repoPath: string;
  status: "planned" | "ready" | "missing";
  purpose: string;
  setup: string;
  experimentUses: string[];
};

export type ProjectStatus = "active" | "archived";

export type Project = {
  id: string;
  name: string;
  repoPath: string;
  status: ProjectStatus;
  createdAt: string;
  sessionCount: number;
  lastActiveAt: string | null;
  openBugs: number;
  healthScore: number | null;
  healthScoreSignal: TrustedSignal<number | null>;
  criticalDeltaCount: number;
  criticalDeltaSignal: TrustedSignal<number>;
  unknownCoverage: number | null;
  unknownCoverageSignal: TrustedSignal<number | null>;
  healthTrend: number | null;
  healthTrendSignal: TrustedSignal<number | null>;
  pipelineStatus: "healthy" | "warning" | "error" | "blocked" | "unknown";
  pipelineConfiguredRequired: number;
  pipelineRequired: number;
  pipelineLabel: string;
  pipelineSignal: TrustedSignal<string>;
  statusSignal: TrustedSignal<ProjectStatus>;
};

export type CostBreakdownPoint = {
  key: string;
  label: string;
  tokens: number;
};

export type CostSummary = {
  period: "day" | "week" | "month";
  totalTokens: number;
  byProject: CostBreakdownPoint[];
  byClassification: CostBreakdownPoint[];
  byTool: CostBreakdownPoint[];
  abandonedSessionTokens: number;
  failedRunTokens: number;
  rtk: {
    state: "active" | "inactive" | "no_eligible_data" | "token_regressive" | "misconfigured";
    stateSignal: TrustedSignal<"active" | "inactive" | "no_eligible_data" | "token_regressive" | "misconfigured">;
    eventCount: number;
    rawTokens: number;
    compressedTokens: number;
    tokensSaved: number;
    reductionPercent: number;
    ambiguousFailures: number;
    byWorkflow: CostBreakdownPoint[];
  };
};

export type AnomalyAlertType =
  | "token_spike"
  | "abandon_rate"
  | "pattern_regression"
  | "long_session"
  | "repeated_failure";

export type AnomalyAlert = {
  id: string;
  type: AnomalyAlertType;
  severity: "warning" | "error";
  message: string;
  sessionId: string | null;
  detectedAt: string;
};

export type AutomationHealth = {
  id: string;
  name: string;
  trigger: string;
  triggerLabel: string;
  triggerSignal: TrustedSignal<string>;
  successRate: number | null;
  successRateSignal: TrustedSignal<number | null>;
  status: "healthy" | "warning" | "error" | "unknown";
  statusSignal: TrustedSignal<"healthy" | "warning" | "error" | "unknown">;
  urgency: "none" | "watch" | "action_required" | "blocked";
  lastRunAt: string | null;
  nextRunAt: string | null;
  lastFailureSummary: string | null;
  approvalBlockers: string[];
  writebackBlockers: string[];
};

export type WorkflowMetric = {
  id: string;
  name: string;
  successRate: number;
  runs: number;
  avgTokens: number;
};

export type ExpectationDirection = "max" | "min" | "exact";

export type ExpectationMetricKey =
  | "abandon_rate"
  | "open_run_rate"
  | "first_pass_success"
  | "follow_up_turns"
  | "prompt_reuse_rate"
  | "error_event_rate"
  | "avg_run_duration_minutes";

export type ExpectationTarget = {
  id: string;
  scopeType: "global" | "project" | "workflow";
  scopeKey: string;
  metricKey: ExpectationMetricKey;
  targetValue: number;
  warningDelta: number;
  errorDelta: number;
  direction: ExpectationDirection;
  updatedAt: string;
};

export type ExpectationStatus = "healthy" | "warning" | "error";

export type MetricEvaluation = {
  metricKey: ExpectationMetricKey;
  label: string;
  actualValue: number | null;
  targetValue: number;
  warningDelta: number;
  errorDelta: number;
  direction: ExpectationDirection;
  deltaFromTarget: number | null;
  status: ExpectationStatus;
  explanation: string;
};

export type RunValueScore = {
  sessionId: string;
  projectId: string;
  projectName: string;
  objective: string | null;
  status: SessionStatus;
  score: number;
  estimatedTokensSaved: number;
  estimatedMinutesSaved: number;
};

export type LearningSignalKind =
  | "repeated_failure"
  | "ignored_rule"
  | "bloated_packet"
  | "weak_prompt"
  | "weak_workflow"
  | "route_misroute"
  | "standards_regression"
  | "writeback_adopted"
  | "writeback_rejected"
  | "compounding_gain";

export interface RecurringPattern {
  pattern_id: string;
  signal_kind: LearningSignalKind;
  scope_kind: string;
  scope_key: string;
  project_id: string | null;
  sample_size: number;
  recurrence_count: number;
  confidence: number;
  since: string;
  summary: string;
  evidence_run_ids: readonly string[];
  suggested_remediation_class: string;
  metadata: Record<string, unknown>;
  drillDownPath?: string;
}

export interface AssetEvidenceDelta {
  asset_kind: "prompt" | "skill" | "workflow" | "standard" | "route";
  asset_key: string;
  delta_sample_size: number;
  delta_success_count: number;
  delta_blocker_count: number;
}

export interface ProposalCreated {
  writeback_id: string;
  signal_kind: LearningSignalKind | null;
  requires_approval: boolean;
  status: string;
}

export interface LearningImpactPerRun {
  run_id: string;
  workflow_key: string | null;
  signals_emitted: readonly LearningSignalKind[];
  assets_evidenced: readonly AssetEvidenceDelta[];
  proposals_created: readonly ProposalCreated[];
  learning_events_persisted: number;
  no_learning_reason: string | null;
}

export interface LearningImpactRollup {
  scope: "workflow" | "prompt" | "skill";
  key: string;
  since: string;
  sample_size: number;
  rework_rate_30d: number | null;
  rework_rate_90d: number | null;
  success_rate_30d: number | null;
  blocker_rate_30d: number | null;
  trend: "improving" | "flat" | "regressing" | "insufficient_data";
  rationale: string;
  project_id: string | null;
  drillDownPath?: string;
}

export interface ConservativeProposalRow {
  writeback_id: string;
  layer_type: string;
  layer_key: string;
  impact_scope: string;
  signal_kind: LearningSignalKind | null;
  pattern_id: string | null;
  proposal_status: string;
  current_lifecycle_state: string | null;
  requires_approval: boolean;
  created_at: string;
  sample_size: number | null;
  recurrence_count: number | null;
  confidence: number | null;
  drillDownPath?: string;
}

export type ProjectValueScore = {
  projectId: string;
  projectName: string;
  runCount: number;
  averageScore: number;
  estimatedTokensSaved: number;
  estimatedMinutesSaved: number;
};

export type WorkflowValueScore = {
  workflowName: string;
  runCount: number;
  score: number;
};

export type SessionEvidenceItem = {
  sessionId: string;
  projectName: string;
  objective: string | null;
  detail: string;
};

export type ImprovementRecommendation = {
  id: string;
  title: string;
  rationale: string;
  action: string;
  confidence: number;
  estimatedTokenRoi: number;
  estimatedMinutesRoi: number;
  priority: "high" | "medium" | "low";
  sessionEvidence: SessionEvidenceItem[];
};

export type ExplainabilitySnapshot = {
  metrics: MetricEvaluation[];
  expectations: ExpectationTarget[];
  valueByProject: ProjectValueScore[];
  valueByWorkflow: WorkflowValueScore[];
  topRuns: RunValueScore[];
  recommendations: ImprovementRecommendation[];
};
