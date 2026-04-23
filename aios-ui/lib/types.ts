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

export type PatternState = "notice" | "observation" | "hypothesis" | "rule";

export type Pattern = {
  id: string;
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
  criticalDeltaCount: number;
  unknownCoverage: number | null;
  healthTrend: number | null;
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
  successRate: number;
  status: "healthy" | "warning" | "error";
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
  status: SessionStatus;
  score: number;
  estimatedTokensSaved: number;
  estimatedMinutesSaved: number;
};

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

export type ImprovementRecommendation = {
  id: string;
  title: string;
  rationale: string;
  action: string;
  confidence: number;
  estimatedTokenRoi: number;
  estimatedMinutesRoi: number;
  priority: "high" | "medium" | "low";
};

export type ExplainabilitySnapshot = {
  metrics: MetricEvaluation[];
  expectations: ExpectationTarget[];
  valueByProject: ProjectValueScore[];
  valueByWorkflow: WorkflowValueScore[];
  topRuns: RunValueScore[];
  recommendations: ImprovementRecommendation[];
};
