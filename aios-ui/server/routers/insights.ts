import { randomUUID } from "node:crypto";

import { z } from "zod";

import type {
  ExpectationDirection,
  ExpectationMetricKey,
  ExpectationStatus,
  ExpectationTarget,
  ExplainabilitySnapshot,
  ImprovementRecommendation,
  MetricEvaluation,
  ProjectValueScore,
  RunValueScore,
  WorkflowValueScore,
} from "@/lib/types";
import { tableExists } from "@/server/db";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

type ExpectationRow = {
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

type SessionAggregateRow = {
  totalCount: number;
  abandonedCount: number;
  openCount: number;
};

type PromptAggregateRow = {
  totalCount: number;
  reusableCount: number;
};

type WorkflowAverageRow = {
  firstPassSuccess: number | null;
  followUpTurns: number | null;
};

type EventAggregateRow = {
  postToolCount: number;
  errorPostToolCount: number;
};

type SessionValueRow = {
  sessionId: string;
  projectId: string;
  projectName: string;
  objective: string | null;
  status: "open" | "closed" | "abandoned";
  promptCount: number;
  reusableCount: number;
  artifactCount: number;
  bugCount: number;
  errorCount: number;
  firstPassSuccess: number | null;
  followUpTurns: number | null;
};

type WorkflowScoreRow = {
  workflowName: string;
  runCount: number;
  averageValue: number;
};

type MetricDefinition = {
  key: ExpectationMetricKey;
  label: string;
};

const metricDefinitions: MetricDefinition[] = [
  { key: "abandon_rate", label: "Abandon Rate" },
  { key: "open_run_rate", label: "Open Run Rate" },
  { key: "first_pass_success", label: "First Pass Success" },
  { key: "follow_up_turns", label: "Follow-Up Turns" },
  { key: "prompt_reuse_rate", label: "Prompt Reuse Rate" },
  { key: "error_event_rate", label: "Error Event Rate" },
  { key: "avg_run_duration_minutes", label: "Avg Run Duration (min)" },
];

const defaultExpectationTargets: Array<
  Omit<ExpectationTarget, "id" | "updatedAt"> & { metricKey: ExpectationMetricKey }
> = [
  {
    scopeType: "global",
    scopeKey: "global",
    metricKey: "abandon_rate",
    targetValue: 0.12,
    warningDelta: 0.05,
    errorDelta: 0.12,
    direction: "min",
  },
  {
    scopeType: "global",
    scopeKey: "global",
    metricKey: "open_run_rate",
    targetValue: 0.08,
    warningDelta: 0.05,
    errorDelta: 0.1,
    direction: "min",
  },
  {
    scopeType: "global",
    scopeKey: "global",
    metricKey: "first_pass_success",
    targetValue: 0.82,
    warningDelta: 0.08,
    errorDelta: 0.2,
    direction: "max",
  },
  {
    scopeType: "global",
    scopeKey: "global",
    metricKey: "follow_up_turns",
    targetValue: 2.4,
    warningDelta: 0.9,
    errorDelta: 1.8,
    direction: "min",
  },
  {
    scopeType: "global",
    scopeKey: "global",
    metricKey: "prompt_reuse_rate",
    targetValue: 0.24,
    warningDelta: 0.08,
    errorDelta: 0.18,
    direction: "max",
  },
  {
    scopeType: "global",
    scopeKey: "global",
    metricKey: "error_event_rate",
    targetValue: 0.04,
    warningDelta: 0.03,
    errorDelta: 0.08,
    direction: "min",
  },
  {
    scopeType: "global",
    scopeKey: "global",
    metricKey: "avg_run_duration_minutes",
    targetValue: 18,
    warningDelta: 10,
    errorDelta: 22,
    direction: "min",
  },
];

const clamp = (value: number, min: number, max: number): number => {
  if (value < min) {
    return min;
  }

  if (value > max) {
    return max;
  }

  return value;
};

const normalizeRatio = (value: number | null): number | null => {
  if (value === null) {
    return null;
  }

  if (value > 1) {
    return value / 100;
  }

  if (value < 0) {
    return 0;
  }

  return value;
};

const ensureExpectationTable = (ctxDb: ReturnType<typeof import("@/server/db").getDb>): void => {
  ctxDb.exec(`
    CREATE TABLE IF NOT EXISTS expectation_targets (
      id TEXT PRIMARY KEY,
      scope_type TEXT NOT NULL,
      scope_key TEXT NOT NULL,
      metric_key TEXT NOT NULL,
      target_value REAL NOT NULL,
      warning_delta REAL NOT NULL,
      error_delta REAL NOT NULL,
      direction TEXT NOT NULL,
      updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
      UNIQUE(scope_type, scope_key, metric_key)
    );
    CREATE INDEX IF NOT EXISTS idx_expectation_targets_scope ON expectation_targets(scope_type, scope_key);
    CREATE INDEX IF NOT EXISTS idx_expectation_targets_metric ON expectation_targets(metric_key);
  `);

  const existing = ctxDb
    .prepare(
      `
      SELECT COUNT(*) AS count
      FROM expectation_targets
      WHERE scope_type = 'global'
        AND scope_key = 'global'
    `,
    )
    .get() as { count: number };

  if (existing.count > 0) {
    return;
  }

  const insertStatement = ctxDb.prepare(`
    INSERT INTO expectation_targets (
      id,
      scope_type,
      scope_key,
      metric_key,
      target_value,
      warning_delta,
      error_delta,
      direction
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `);

  const transaction = ctxDb.transaction(() => {
    for (const target of defaultExpectationTargets) {
      insertStatement.run(
        `expectation-${randomUUID()}`,
        target.scopeType,
        target.scopeKey,
        target.metricKey,
        target.targetValue,
        target.warningDelta,
        target.errorDelta,
        target.direction,
      );
    }
  });

  transaction();
};

const loadExpectations = (
  ctxDb: ReturnType<typeof import("@/server/db").getDb>,
  scopeType: ExpectationTarget["scopeType"] = "global",
  scopeKey = "global",
): ExpectationTarget[] => {
  ensureExpectationTable(ctxDb);

  return (
    ctxDb
      .prepare(
        `
        SELECT
          id,
          scope_type AS scopeType,
          scope_key AS scopeKey,
          metric_key AS metricKey,
          target_value AS targetValue,
          warning_delta AS warningDelta,
          error_delta AS errorDelta,
          direction,
          updated_at AS updatedAt
        FROM expectation_targets
        WHERE scope_type = ?
          AND scope_key = ?
        ORDER BY metric_key ASC
      `,
      )
      .all(scopeType, scopeKey) as ExpectationRow[]
  ).map((row) => ({
    id: row.id,
    scopeType: row.scopeType,
    scopeKey: row.scopeKey,
    metricKey: row.metricKey,
    targetValue: row.targetValue,
    warningDelta: row.warningDelta,
    errorDelta: row.errorDelta,
    direction: row.direction,
    updatedAt: row.updatedAt,
  }));
};

const evaluateMetric = (
  target: ExpectationTarget,
  label: string,
  actualValue: number | null,
): MetricEvaluation => {
  if (actualValue === null) {
    return {
      metricKey: target.metricKey,
      label,
      actualValue,
      targetValue: target.targetValue,
      warningDelta: target.warningDelta,
      errorDelta: target.errorDelta,
      direction: target.direction,
      deltaFromTarget: null,
      status: "warning",
      explanation: "No data available yet for this metric.",
    };
  }

  const deltaFromTarget = actualValue - target.targetValue;
  let severityDistance = 0;

  if (target.direction === "max") {
    severityDistance = target.targetValue - actualValue;
  } else if (target.direction === "min") {
    severityDistance = actualValue - target.targetValue;
  } else {
    severityDistance = Math.abs(deltaFromTarget);
  }

  let status: ExpectationStatus = "healthy";
  if (severityDistance > target.errorDelta) {
    status = "error";
  } else if (severityDistance > target.warningDelta) {
    status = "warning";
  }

  const explanation =
    status === "healthy"
      ? "Within expected range."
      : status === "warning"
        ? "Outside target range; monitor and tune."
        : "Breaching target significantly; action recommended.";

  return {
    metricKey: target.metricKey,
    label,
    actualValue,
    targetValue: target.targetValue,
    warningDelta: target.warningDelta,
    errorDelta: target.errorDelta,
    direction: target.direction,
    deltaFromTarget,
    status,
    explanation,
  };
};

const readMetricActuals = (
  ctxDb: ReturnType<typeof import("@/server/db").getDb>,
): Record<ExpectationMetricKey, number | null> => {
  const sessionAggregate = tableExists("sessions")
    ? (ctxDb
        .prepare(
          `
          SELECT
            COUNT(*) AS totalCount,
            SUM(CASE WHEN status = 'abandoned' THEN 1 ELSE 0 END) AS abandonedCount,
            SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) AS openCount
          FROM sessions
        `,
        )
        .get() as SessionAggregateRow)
    : { totalCount: 0, abandonedCount: 0, openCount: 0 };

  const avgDurationMinutes = tableExists("sessions")
    ? ((ctxDb
        .prepare(
          `
          SELECT
            AVG((julianday(ended_at) - julianday(started_at)) * 1440.0) AS avgDuration
          FROM sessions
          WHERE ended_at IS NOT NULL
        `,
        )
        .get() as { avgDuration: number | null }).avgDuration ?? null)
    : null;

  const promptAggregate = tableExists("prompts_used")
    ? (ctxDb
        .prepare(
          `
          SELECT
            COUNT(*) AS totalCount,
            SUM(CASE WHEN reusable_candidate = 1 THEN 1 ELSE 0 END) AS reusableCount
          FROM prompts_used
        `,
        )
        .get() as PromptAggregateRow)
    : { totalCount: 0, reusableCount: 0 };

  const workflowAverages = tableExists("workflow_metrics")
    ? (ctxDb
        .prepare(
          `
          SELECT
            AVG(CASE WHEN metric_name = 'first_pass_success' THEN metric_value END) AS firstPassSuccess,
            AVG(CASE WHEN metric_name = 'follow_up_turns' THEN metric_value END) AS followUpTurns
          FROM workflow_metrics
        `,
        )
        .get() as WorkflowAverageRow)
    : { firstPassSuccess: null, followUpTurns: null };

  const eventAggregate = tableExists("tool_events")
    ? (ctxDb
        .prepare(
          `
          SELECT
            SUM(CASE WHEN event_type = 'PostToolUse' THEN 1 ELSE 0 END) AS postToolCount,
            SUM(
              CASE
                WHEN event_type = 'PostToolUse'
                  AND (
                    payload_json LIKE '%"error"%'
                    OR payload_json LIKE '%"stderr"%'
                    OR payload_json LIKE '%"exitCode":%'
                  )
                THEN 1
                ELSE 0
              END
            ) AS errorPostToolCount
          FROM tool_events
        `,
        )
        .get() as EventAggregateRow)
    : { postToolCount: 0, errorPostToolCount: 0 };

  const sessionCount = sessionAggregate.totalCount;
  const promptCount = promptAggregate.totalCount;
  const postToolCount = eventAggregate.postToolCount;

  return {
    abandon_rate: sessionCount > 0 ? sessionAggregate.abandonedCount / sessionCount : null,
    open_run_rate: sessionCount > 0 ? sessionAggregate.openCount / sessionCount : null,
    first_pass_success: normalizeRatio(workflowAverages.firstPassSuccess),
    follow_up_turns: workflowAverages.followUpTurns,
    prompt_reuse_rate: promptCount > 0 ? promptAggregate.reusableCount / promptCount : null,
    error_event_rate: postToolCount > 0 ? eventAggregate.errorPostToolCount / postToolCount : null,
    avg_run_duration_minutes: avgDurationMinutes,
  };
};

const readRunValueScores = (
  ctxDb: ReturnType<typeof import("@/server/db").getDb>,
): RunValueScore[] => {
  if (!tableExists("sessions") || !tableExists("projects")) {
    return [];
  }

  const rows = ctxDb
    .prepare(
      `
      SELECT
        s.id AS sessionId,
        s.project_id AS projectId,
        p.name AS projectName,
        s.objective AS objective,
        s.status,
        COALESCE(prompt.promptCount, 0) AS promptCount,
        COALESCE(prompt.reusableCount, 0) AS reusableCount,
        COALESCE(artifact.artifactCount, 0) AS artifactCount,
        COALESCE(bug.bugCount, 0) AS bugCount,
        COALESCE(errorEvent.errorCount, 0) AS errorCount,
        workflow.firstPassSuccess AS firstPassSuccess,
        workflow.followUpTurns AS followUpTurns
      FROM sessions s
      INNER JOIN projects p ON p.id = s.project_id
      LEFT JOIN (
        SELECT
          session_id,
          COUNT(*) AS promptCount,
          SUM(CASE WHEN reusable_candidate = 1 THEN 1 ELSE 0 END) AS reusableCount
        FROM prompts_used
        GROUP BY session_id
      ) prompt ON prompt.session_id = s.id
      LEFT JOIN (
        SELECT
          session_id,
          COUNT(*) AS artifactCount
        FROM artifacts
        GROUP BY session_id
      ) artifact ON artifact.session_id = s.id
      LEFT JOIN (
        SELECT
          session_id,
          COUNT(*) AS bugCount
        FROM bug_log
        GROUP BY session_id
      ) bug ON bug.session_id = s.id
      LEFT JOIN (
        SELECT
          session_id,
          SUM(
            CASE
              WHEN event_type = 'PostToolUse'
                AND (
                  payload_json LIKE '%"error"%'
                  OR payload_json LIKE '%"stderr"%'
                  OR payload_json LIKE '%"exitCode":%'
                )
              THEN 1
              ELSE 0
            END
          ) AS errorCount
        FROM tool_events
        GROUP BY session_id
      ) errorEvent ON errorEvent.session_id = s.id
      LEFT JOIN (
        SELECT
          session_id,
          AVG(CASE WHEN metric_name = 'first_pass_success' THEN metric_value END) AS firstPassSuccess,
          AVG(CASE WHEN metric_name = 'follow_up_turns' THEN metric_value END) AS followUpTurns
        FROM workflow_metrics
        GROUP BY session_id
      ) workflow ON workflow.session_id = s.id
      ORDER BY s.started_at DESC
      LIMIT 400
    `,
    )
    .all() as SessionValueRow[];

  return rows.map((row) => {
    const normalizedFirstPass = normalizeRatio(row.firstPassSuccess) ?? 0;
    const followUpTurns = row.followUpTurns ?? 0;
    const statusPenalty = row.status === "abandoned" ? 12 : row.status === "open" ? 4 : 0;
    const bugPenalty = Math.min(row.bugCount, 6) * 8;
    const errorPenalty = Math.min(row.errorCount, 20) * 1.4;
    const followUpPenalty = Math.min(followUpTurns, 12) * 1.8;
    const reuseBonus = Math.min(row.reusableCount, 10) * 4.5;
    const artifactBonus = Math.min(row.artifactCount, 20) * 0.6;
    const firstPassBonus = normalizedFirstPass * 22;
    const promptSignal = Math.min(row.promptCount, 20) * 0.3;

    const score = clamp(
      52 + reuseBonus + artifactBonus + firstPassBonus + promptSignal - statusPenalty - bugPenalty - errorPenalty - followUpPenalty,
      0,
      100,
    );

    const estimatedTokensSaved = Math.max(
      0,
      Math.round(row.reusableCount * 160 + normalizedFirstPass * 320 - row.errorCount * 42 - row.bugCount * 80),
    );
    const estimatedMinutesSaved = Math.max(
      0,
      Math.round(row.reusableCount * 2 + normalizedFirstPass * 10 - row.bugCount * 4 - followUpTurns * 1.2),
    );

    return {
      sessionId: row.sessionId,
      projectId: row.projectId,
      projectName: row.projectName,
      objective: row.objective,
      status: row.status,
      score: Math.round(score * 10) / 10,
      estimatedTokensSaved,
      estimatedMinutesSaved,
    };
  });
};

const aggregateProjectValue = (runs: RunValueScore[]): ProjectValueScore[] => {
  const map = new Map<string, ProjectValueScore>();

  for (const run of runs) {
    const existing = map.get(run.projectId);
    if (!existing) {
      map.set(run.projectId, {
        projectId: run.projectId,
        projectName: run.projectName,
        runCount: 1,
        averageScore: run.score,
        estimatedTokensSaved: run.estimatedTokensSaved,
        estimatedMinutesSaved: run.estimatedMinutesSaved,
      });
      continue;
    }

    const nextRunCount = existing.runCount + 1;
    existing.averageScore =
      (existing.averageScore * existing.runCount + run.score) / nextRunCount;
    existing.runCount = nextRunCount;
    existing.estimatedTokensSaved += run.estimatedTokensSaved;
    existing.estimatedMinutesSaved += run.estimatedMinutesSaved;
  }

  return Array.from(map.values())
    .map((row) => ({
      ...row,
      averageScore: Math.round(row.averageScore * 10) / 10,
    }))
    .sort((left, right) => right.averageScore - left.averageScore);
};

const readWorkflowValue = (
  ctxDb: ReturnType<typeof import("@/server/db").getDb>,
): WorkflowValueScore[] => {
  if (!tableExists("workflow_metrics")) {
    return [];
  }

  const rows = ctxDb
    .prepare(
      `
      SELECT
        metric_name AS workflowName,
        COUNT(*) AS runCount,
        AVG(metric_value) AS averageValue
      FROM workflow_metrics
      GROUP BY metric_name
      ORDER BY runCount DESC
    `,
    )
    .all() as WorkflowScoreRow[];

  return rows.map((row) => {
    const normalizedAverage =
      row.workflowName === "first_pass_success"
        ? normalizeRatio(row.averageValue) ?? 0
        : row.averageValue;

    const score =
      row.workflowName === "first_pass_success"
        ? clamp(normalizedAverage * 100, 0, 100)
        : row.workflowName === "follow_up_turns"
          ? clamp(100 - normalizedAverage * 12, 0, 100)
          : clamp(100 - normalizedAverage * 8, 0, 100);

    return {
      workflowName: row.workflowName,
      runCount: row.runCount,
      score: Math.round(score * 10) / 10,
    };
  });
};

const recommendationFromMetric = (
  evaluation: MetricEvaluation,
  sessionCount: number,
): ImprovementRecommendation | null => {
  if (evaluation.status === "healthy") {
    return null;
  }

  const highPriority = evaluation.status === "error";
  const baseConfidence = highPriority ? 0.86 : 0.72;

  if (evaluation.metricKey === "abandon_rate") {
    return {
      id: `rec-${evaluation.metricKey}`,
      title: "Reduce abandonment in active runs",
      rationale: "Abandonment is above target and indicates unfinished or stalled sessions.",
      action: "Add timeout guardrails and mandatory next-step capture when a run goes idle.",
      confidence: baseConfidence,
      estimatedTokenRoi: Math.round(sessionCount * 220),
      estimatedMinutesRoi: Math.round(sessionCount * 5),
      priority: highPriority ? "high" : "medium",
    };
  }

  if (evaluation.metricKey === "open_run_rate") {
    return {
      id: `rec-${evaluation.metricKey}`,
      title: "Close or auto-archive stale runs",
      rationale: "Open-run backlog hides operational state and inflates context carry-over.",
      action: "Add a stale-run sweeper and explicit close workflow for sessions idle over threshold.",
      confidence: baseConfidence - 0.04,
      estimatedTokenRoi: Math.round(sessionCount * 140),
      estimatedMinutesRoi: Math.round(sessionCount * 4),
      priority: highPriority ? "high" : "medium",
    };
  }

  if (evaluation.metricKey === "first_pass_success") {
    return {
      id: `rec-${evaluation.metricKey}`,
      title: "Increase first-pass execution success",
      rationale: "Low first-pass success creates rework loops and adds avoidable turns.",
      action: "Introduce a preflight check step before execution and enforce explicit acceptance criteria in prompts.",
      confidence: baseConfidence + 0.02,
      estimatedTokenRoi: Math.round(sessionCount * 260),
      estimatedMinutesRoi: Math.round(sessionCount * 8),
      priority: highPriority ? "high" : "medium",
    };
  }

  if (evaluation.metricKey === "follow_up_turns") {
    return {
      id: `rec-${evaluation.metricKey}`,
      title: "Cut follow-up turns per objective",
      rationale: "Too many follow-up turns signal ambiguous initial plans or weak retrieval.",
      action: "Require a concise plan block and expected output contract before tool execution.",
      confidence: baseConfidence - 0.03,
      estimatedTokenRoi: Math.round(sessionCount * 180),
      estimatedMinutesRoi: Math.round(sessionCount * 6),
      priority: highPriority ? "high" : "medium",
    };
  }

  if (evaluation.metricKey === "prompt_reuse_rate") {
    return {
      id: `rec-${evaluation.metricKey}`,
      title: "Promote reusable prompt patterns",
      rationale: "Low reuse means successful patterns are not being captured as assets.",
      action: "Increase candidate promotion cadence and require approve/reject triage for top repeated patterns.",
      confidence: baseConfidence - 0.01,
      estimatedTokenRoi: Math.round(sessionCount * 200),
      estimatedMinutesRoi: Math.round(sessionCount * 7),
      priority: highPriority ? "high" : "medium",
    };
  }

  if (evaluation.metricKey === "error_event_rate") {
    return {
      id: `rec-${evaluation.metricKey}`,
      title: "Lower tool execution error rate",
      rationale: "Error-heavy tool execution drives retries and avoidable wasted tokens.",
      action: "Add command validation, environment checks, and retry policy tuning for common failure classes.",
      confidence: baseConfidence + 0.04,
      estimatedTokenRoi: Math.round(sessionCount * 240),
      estimatedMinutesRoi: Math.round(sessionCount * 9),
      priority: highPriority ? "high" : "medium",
    };
  }

  return {
    id: `rec-${evaluation.metricKey}`,
    title: "Reduce average run duration",
    rationale: "Run duration above target often indicates weak decomposition or broad objectives.",
    action: "Split objectives into smaller execution phases with explicit completion checkpoints.",
    confidence: baseConfidence - 0.05,
    estimatedTokenRoi: Math.round(sessionCount * 160),
    estimatedMinutesRoi: Math.round(sessionCount * 6),
    priority: highPriority ? "high" : "medium",
  };
};

const lowPerformingProjectRecommendations = (
  projects: ProjectValueScore[],
): ImprovementRecommendation[] =>
  projects
    .slice()
    .sort((left, right) => left.averageScore - right.averageScore)
    .slice(0, 2)
    .filter((project) => project.averageScore < 55)
    .map((project) => ({
      id: `rec-project-${project.projectId}`,
      title: `Stabilize ${project.projectName}`,
      rationale: `${project.projectName} has the lowest value score and likely contributes disproportionate rework.`,
      action: "Audit top failing run types for this project and create project-specific reusable prompt presets.",
      confidence: 0.7,
      estimatedTokenRoi: Math.round(project.runCount * 190),
      estimatedMinutesRoi: Math.round(project.runCount * 7),
      priority: "medium",
    }));

const workflowRecommendations = (
  workflows: WorkflowValueScore[],
): ImprovementRecommendation[] =>
  workflows
    .filter((workflow) => workflow.score < 60)
    .slice(0, 2)
    .map((workflow) => ({
      id: `rec-workflow-${workflow.workflowName}`,
      title: `Improve ${workflow.workflowName}`,
      rationale: `${workflow.workflowName} scores low against expected behavior and impacts downstream reliability.`,
      action: "Define tighter entry/exit criteria and add lightweight evaluation checks before promotion.",
      confidence: 0.68,
      estimatedTokenRoi: Math.round(workflow.runCount * 140),
      estimatedMinutesRoi: Math.round(workflow.runCount * 5),
      priority: "medium",
    }));

const rankRecommendations = (
  recommendations: ImprovementRecommendation[],
): ImprovementRecommendation[] =>
  recommendations
    .slice()
    .sort((left, right) => {
      const leftPriorityWeight = left.priority === "high" ? 3 : left.priority === "medium" ? 2 : 1;
      const rightPriorityWeight =
        right.priority === "high" ? 3 : right.priority === "medium" ? 2 : 1;

      const leftScore =
        (left.estimatedTokenRoi + left.estimatedMinutesRoi * 30) * left.confidence * leftPriorityWeight;
      const rightScore =
        (right.estimatedTokenRoi + right.estimatedMinutesRoi * 30) *
        right.confidence *
        rightPriorityWeight;

      return rightScore - leftScore;
    });

export const insightsRouter = createTRPCRouter({
  expectations: publicProcedure
    .input(
      z
        .object({
          scopeType: z.enum(["global", "project", "workflow"]).default("global"),
          scopeKey: z.string().min(1).default("global"),
        })
        .optional(),
    )
    .query(({ ctx, input }): ExpectationTarget[] =>
      loadExpectations(ctx.db, input?.scopeType ?? "global", input?.scopeKey ?? "global"),
    ),

  upsertExpectation: publicProcedure
    .input(
      z.object({
        scopeType: z.enum(["global", "project", "workflow"]).default("global"),
        scopeKey: z.string().min(1).default("global"),
        metricKey: z.enum([
          "abandon_rate",
          "open_run_rate",
          "first_pass_success",
          "follow_up_turns",
          "prompt_reuse_rate",
          "error_event_rate",
          "avg_run_duration_minutes",
        ]),
        targetValue: z.number().finite(),
        warningDelta: z.number().nonnegative(),
        errorDelta: z.number().nonnegative(),
        direction: z.enum(["max", "min", "exact"]),
      }),
    )
    .mutation(({ ctx, input }): { ok: boolean; id: string } => {
      ensureExpectationTable(ctx.db);

      const existing = ctx.db
        .prepare(
          `
          SELECT id
          FROM expectation_targets
          WHERE scope_type = ?
            AND scope_key = ?
            AND metric_key = ?
          LIMIT 1
        `,
        )
        .get(input.scopeType, input.scopeKey, input.metricKey) as { id: string } | undefined;

      if (existing) {
        ctx.db
          .prepare(
            `
            UPDATE expectation_targets
            SET
              target_value = ?,
              warning_delta = ?,
              error_delta = ?,
              direction = ?,
              updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
            WHERE id = ?
          `,
          )
          .run(
            input.targetValue,
            input.warningDelta,
            input.errorDelta,
            input.direction,
            existing.id,
          );

        return { ok: true, id: existing.id };
      }

      const id = `expectation-${randomUUID()}`;
      ctx.db
        .prepare(
          `
          INSERT INTO expectation_targets (
            id,
            scope_type,
            scope_key,
            metric_key,
            target_value,
            warning_delta,
            error_delta,
            direction
          )
          VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        `,
        )
        .run(
          id,
          input.scopeType,
          input.scopeKey,
          input.metricKey,
          input.targetValue,
          input.warningDelta,
          input.errorDelta,
          input.direction,
        );

      return { ok: true, id };
    }),

  snapshot: publicProcedure.query(({ ctx }): ExplainabilitySnapshot => {
    const expectations = loadExpectations(ctx.db, "global", "global");
    const actuals = readMetricActuals(ctx.db);

    const metrics = metricDefinitions.map((definition) => {
      const target =
        expectations.find((item) => item.metricKey === definition.key) ??
        ({
          id: `default-${definition.key}`,
          scopeType: "global",
          scopeKey: "global",
          metricKey: definition.key,
          targetValue: 0,
          warningDelta: 0,
          errorDelta: 0,
          direction: "exact",
          updatedAt: new Date().toISOString(),
        } satisfies ExpectationTarget);

      return evaluateMetric(target, definition.label, actuals[definition.key]);
    });

    const runScores = readRunValueScores(ctx.db);
    const valueByProject = aggregateProjectValue(runScores);
    const valueByWorkflow = readWorkflowValue(ctx.db);
    const topRuns = runScores.slice().sort((left, right) => right.score - left.score).slice(0, 10);
    const sessionCount = runScores.length;

    const recommendations = rankRecommendations(
      [
        ...metrics
          .map((metric) => recommendationFromMetric(metric, sessionCount))
          .filter((recommendation): recommendation is ImprovementRecommendation => recommendation !== null),
        ...lowPerformingProjectRecommendations(valueByProject),
        ...workflowRecommendations(valueByWorkflow),
      ].slice(0, 14),
    );

    return {
      metrics,
      expectations,
      valueByProject,
      valueByWorkflow,
      topRuns,
      recommendations,
    };
  }),
});
