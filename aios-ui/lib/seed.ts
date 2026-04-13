import type { AnomalyAlert, AutomationHealth, CostSummary, WorkflowMetric } from "@/lib/types";

export const seededCostSummary: CostSummary = {
  period: "week",
  totalTokens: 422_450,
  byProject: [
    { key: "soundscape", label: "soundscape", tokens: 166_120 },
    { key: "aios", label: "AIOS", tokens: 143_300 },
    { key: "bballedu", label: "Bballedu", tokens: 113_030 },
  ],
  byClassification: [
    { key: "implement", label: "implement", tokens: 198_700 },
    { key: "debugging", label: "debugging", tokens: 134_200 },
    { key: "review", label: "review", tokens: 89_550 },
  ],
  byTool: [
    { key: "codex", label: "codex", tokens: 243_250 },
    { key: "claude-code", label: "claude-code", tokens: 126_800 },
    { key: "desktop-claude", label: "desktop-claude", tokens: 52_400 },
  ],
  abandonedSessionTokens: 48_330,
  failedRunTokens: 25_920,
};

export const seededAnomalies: AnomalyAlert[] = [
  {
    id: "anomaly-1",
    type: "token_spike",
    severity: "warning",
    message: "Token usage on soundscape rose 29% vs prior 7-day window.",
    sessionId: null,
    detectedAt: new Date().toISOString(),
  },
  {
    id: "anomaly-2",
    type: "repeated_failure",
    severity: "error",
    message: "Three consecutive run failures in triage flow.",
    sessionId: null,
    detectedAt: new Date().toISOString(),
  },
];

export const seededAutomations: AutomationHealth[] = [
  {
    id: "automation-1",
    name: "Daily ingest status",
    trigger: "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=9;BYMINUTE=0",
    successRate: 0.97,
    status: "healthy",
  },
  {
    id: "automation-2",
    name: "PR health report",
    trigger: "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=11;BYMINUTE=30",
    successRate: 0.83,
    status: "warning",
  },
  {
    id: "automation-3",
    name: "Nightly import verify",
    trigger: "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR,SA,SU;BYHOUR=1;BYMINUTE=0",
    successRate: 0.62,
    status: "error",
  },
];

export const seededWorkflowMetrics: WorkflowMetric[] = [
  {
    id: "wf-1",
    name: "Triage bugs",
    successRate: 0.91,
    runs: 56,
    avgTokens: 4_200,
  },
  {
    id: "wf-2",
    name: "Prompt promotion",
    successRate: 0.86,
    runs: 31,
    avgTokens: 3_100,
  },
  {
    id: "wf-3",
    name: "Import review",
    successRate: 0.78,
    runs: 24,
    avgTokens: 5_010,
  },
];
