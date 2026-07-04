/**
 * Daily-flow projection for previewing and replaying operator work.
 *
 * Mirrors services/daily_flow.py. Preview mode is read-only: it does not call Python,
 * agentize, write orchestration rows, or persist packets. Replay mode reads persisted
 * run, packet, evaluation, writeback, delta, next-action, and read-only repo
 * closeout evidence.
 */

import { execFileSync } from "node:child_process";
import { resolve } from "node:path";

import type Database from "better-sqlite3";

import {
  deltaItemPath,
  goalSearchPath,
  packetPath,
  runPath,
  workflowPath,
  writebackPath,
} from "@/lib/drill-down";
import type { DailyFlowStep, DailyFlowStepKind, DailyFlowTrace } from "@/lib/control-plane";
import { getNextActions } from "@/server/aios/next-action";

export const CANONICAL_STEP_ORDER: readonly DailyFlowStepKind[] = [
  "goal",
  "route",
  "packet",
  "run",
  "evaluation",
  "writeback",
  "unresolved_delta",
  "next_action",
];

type Row = Record<string, unknown>;

type GitCommandResult = {
  ok: boolean;
  stdout: string;
};

type RepoCloseoutPayload = {
  schema: "aios-repo-closeout-v0.1";
  repo: string;
  git: {
    is_repo: boolean;
    branch: string | null;
    head: string | null;
    dirty: boolean;
    dirty_files: string[];
    recent_commits: Array<{ sha: string; title: string }>;
  };
  diff_stat: {
    lines: string[];
  };
};

const _safeTableExists = (db: Database.Database, tableName: string): boolean => {
  const row = db
    .prepare("SELECT name FROM sqlite_master WHERE type='table' AND name=? LIMIT 1")
    .get(tableName) as { name: string } | undefined;
  return row !== undefined;
};

const _tableColumns = (db: Database.Database, tableName: string): Set<string> => {
  if (!_safeTableExists(db, tableName)) {
    return new Set();
  }
  const rows = db.prepare(`PRAGMA table_info(${tableName})`).all() as Array<{ name: string }>;
  return new Set(rows.map((row) => row.name));
};

const _text = (value: unknown): string => (value === null || value === undefined ? "" : String(value));

const _nullableText = (value: unknown): string | null => {
  const text = _text(value);
  return text ? text : null;
};

const _runGit = (repoPath: string, args: readonly string[]): GitCommandResult => {
  try {
    const stdout = execFileSync("git", [...args], {
      cwd: repoPath,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
      timeout: 5000,
    });
    return { ok: true, stdout };
  } catch {
    return { ok: false, stdout: "" };
  }
};

const _rawLines = (stdout: string): string[] =>
  stdout.split(/\r?\n/u).filter((line) => line.length > 0);

const _trimmedLines = (stdout: string): string[] =>
  _rawLines(stdout)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);

const _gitRoot = (repoPath: string): string => {
  const candidate = resolve(repoPath);
  const result = _runGit(candidate, ["rev-parse", "--show-toplevel"]);
  const stdout = result.stdout.trim();
  return result.ok && stdout ? resolve(stdout) : candidate;
};

const _gitText = (repoPath: string, args: readonly string[]): string | null => {
  const result = _runGit(repoPath, args);
  const stdout = result.stdout.trim();
  return result.ok && stdout ? stdout : null;
};

const _gitStatusLines = (repoPath: string): string[] => {
  const result = _runGit(repoPath, ["status", "--short"]);
  return result.ok ? _rawLines(result.stdout) : [];
};

const _recentCommits = (repoPath: string, limit: number): Array<{ sha: string; title: string }> => {
  const result = _runGit(repoPath, ["log", "--oneline", `-${limit}`]);
  if (!result.ok) {
    return [];
  }
  return _rawLines(result.stdout).map((line) => {
    const separator = line.indexOf(" ");
    if (separator === -1) {
      return { sha: line, title: "" };
    }
    return { sha: line.slice(0, separator), title: line.slice(separator + 1) };
  });
};

const _repoCloseoutPayload = (repoPath: string, commitLimit = 5): RepoCloseoutPayload => {
  const repo = _gitRoot(repoPath);
  const isRepo = _runGit(repo, ["rev-parse", "--is-inside-work-tree"]).ok;
  const status = isRepo ? _gitStatusLines(repo) : [];
  const boundedLimit = Math.max(1, Math.min(commitLimit, 20));
  return {
    schema: "aios-repo-closeout-v0.1",
    repo,
    git: {
      is_repo: isRepo,
      branch: isRepo ? _gitText(repo, ["branch", "--show-current"]) : null,
      head: isRepo ? _gitText(repo, ["rev-parse", "HEAD"]) : null,
      dirty: status.length > 0,
      dirty_files: status,
      recent_commits: isRepo ? _recentCommits(repo, boundedLimit) : [],
    },
    diff_stat: {
      lines: isRepo ? _trimmedLines(_runGit(repo, ["diff", "--stat"]).stdout) : [],
    },
  };
};

const _projectRepoPath = (db: Database.Database, projectId: string | null): string | null => {
  if (!projectId || !_safeTableExists(db, "projects")) {
    return null;
  }
  const columns = _tableColumns(db, "projects");
  if (!columns.has("id") || !columns.has("repo_path")) {
    return null;
  }
  const row = db
    .prepare("SELECT repo_path AS repoPath FROM projects WHERE id = ? LIMIT 1")
    .get(projectId) as { repoPath?: unknown } | undefined;
  return _nullableText(row?.repoPath);
};

const _repoCloseoutForProject = (
  db: Database.Database,
  projectId: string | null,
): RepoCloseoutPayload | null => {
  const repoPath = _projectRepoPath(db, projectId);
  return repoPath ? _repoCloseoutPayload(repoPath) : null;
};

const _jsonRecord = (raw: unknown): Record<string, unknown> => {
  if (!raw) {
    return {};
  }
  try {
    const parsed = JSON.parse(String(raw)) as unknown;
    return parsed && typeof parsed === "object" && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : {};
  } catch {
    return {};
  }
};

const _step = (
  kind: DailyFlowStepKind,
  input: Omit<DailyFlowStep, "kind">,
): DailyFlowStep => ({
  kind,
  ...input,
});

const _missingStep = (kind: DailyFlowStepKind, summary: string): DailyFlowStep =>
  _step(kind, {
    summary,
    evidenceRef: {},
    drillDownPath: "/control",
    provenance: "missing",
    freshness: "missing",
    metadata: {},
  });

const _stepForGoal = (objective: string, projectId: string | null, isPreview: boolean): DailyFlowStep =>
  _step("goal", {
    summary: objective,
    evidenceRef: { objective, projectId },
    drillDownPath: goalSearchPath(objective),
    provenance: isPreview ? "inferred" : "confirmed",
    freshness: isPreview ? "preview" : "persisted run",
    metadata: { projectId },
  });

const _stepForRoute = (workflowKey: string | null, rationale: string | null): DailyFlowStep =>
  workflowKey
    ? _step("route", {
        summary: `Route recommends ${workflowKey}.`,
        evidenceRef: { workflowKey },
        drillDownPath: workflowPath(workflowKey),
        provenance: "inferred",
        freshness: "live projection",
        metadata: { rationale },
      })
    : _missingStep("route", "No route recommendation is available.");

const _stepForPacket = (packet: Row | null): DailyFlowStep =>
  packet
    ? _step("packet", {
        summary: `Packet ${_text(packet.id)} is available.`,
        evidenceRef: { packetId: packet.id, runId: packet.run_id },
        drillDownPath: packetPath(_text(packet.id)),
        provenance: "confirmed",
        freshness: _text(packet.created_at) || "persisted packet",
        metadata: { workflowKey: packet.workflow_key, agentKey: packet.agent_key },
      })
    : _missingStep("packet", "No persisted packet evidence is available.");

const _stepForRun = (run: Row | null, repoCloseout: RepoCloseoutPayload | null): DailyFlowStep => {
  if (!run) {
    return _missingStep("run", "No persisted run evidence is available.");
  }
  const metadata: Record<string, unknown> = {
    workflowKey: run.workflow_key,
    agentKey: run.agent_key,
    status: run.status,
  };
  if (repoCloseout) {
    metadata.repo_closeout = repoCloseout;
  }
  return _step("run", {
    summary: `Run ${_text(run.id)} is ${_text(run.status) || "unknown"}.`,
    evidenceRef: { runId: run.id },
    drillDownPath: runPath(_text(run.id)),
    provenance: "confirmed",
    freshness: _text(run.updated_at || run.created_at) || "persisted run",
    metadata,
  });
};

const _stepForEvaluation = (evaluation: Row | null, runId: string | null): DailyFlowStep =>
  evaluation
    ? _step("evaluation", {
        summary: `Evaluation ${_text(evaluation.id)} recorded ${_text(evaluation.status) || "status"}.`,
        evidenceRef: { evaluationId: evaluation.id, runId },
        drillDownPath: runId ? runPath(runId) : "/control",
        provenance: "confirmed",
        freshness: _text(evaluation.created_at || evaluation.updated_at) || "persisted evaluation",
        metadata: { status: evaluation.status },
      })
    : _missingStep("evaluation", "No success-criteria evaluation is attached.");

const _stepForWriteback = (writeback: Row | null): DailyFlowStep =>
  writeback
    ? _step("writeback", {
        summary: `Writeback ${_text(writeback.id)} is ${_text(writeback.status) || "unknown"}.`,
        evidenceRef: { writebackId: writeback.id, runId: writeback.run_id },
        drillDownPath: writebackPath(_text(writeback.id)),
        provenance: "confirmed",
        freshness: _text(writeback.updated_at || writeback.created_at) || "persisted writeback",
        metadata: { layerType: writeback.layer_type, layerKey: writeback.layer_key },
      })
    : _missingStep("writeback", "No writeback evidence is attached.");

const _stepForUnresolvedDelta = (delta: Row | null): DailyFlowStep =>
  delta
    ? _step("unresolved_delta", {
        summary: _text(delta.summary) || `Unresolved delta ${_text(delta.id)} remains.`,
        evidenceRef: { deltaId: delta.id, projectId: delta.project_id },
        drillDownPath: deltaItemPath(_nullableText(delta.project_id), _text(delta.id)),
        provenance: "confirmed",
        freshness: _text(delta.created_at || delta.updated_at) || "persisted delta",
        metadata: { priorityBucket: delta.priority_bucket, severity: delta.severity },
      })
    : _missingStep("unresolved_delta", "No unresolved delta evidence is attached.");

const _stepForNextAction = (db: Database.Database, projectId: string | null): DailyFlowStep => {
  const [action] = getNextActions(db, { projectId, limit: 1 });
  if (!action) {
    return _missingStep("next_action", "No next action is currently recommended.");
  }
  return _step("next_action", {
    summary: action.title,
    evidenceRef: { evidenceIds: action.evidenceIds },
    drillDownPath: action.drillDownPath,
    provenance: "inferred",
    freshness: "live projection",
    metadata: {
      kind: action.kind,
      priorityBucket: action.priorityBucket,
      recommendedWorkflowKey: action.recommendedWorkflowKey,
      confidence: action.confidence,
    },
  });
};

const _latestPacketForRun = (db: Database.Database, runId: string): Row | null => {
  if (!_safeTableExists(db, "briefing_packets")) {
    return null;
  }
  const columns = _tableColumns(db, "briefing_packets");
  const whereColumn = columns.has("run_id") ? "run_id" : null;
  if (!whereColumn) {
    return null;
  }
  return (
    db
      .prepare(
        `
        SELECT *
        FROM briefing_packets
        WHERE run_id = ?
        ORDER BY COALESCE(created_at, '') DESC
        LIMIT 1
        `,
      )
      .get(runId) as Row | undefined
  ) ?? null;
};

const _evaluationForRun = (db: Database.Database, runId: string): Row | null => {
  if (!_safeTableExists(db, "success_criteria_evaluations")) {
    return null;
  }
  const columns = _tableColumns(db, "success_criteria_evaluations");
  if (!columns.has("run_id")) {
    return null;
  }
  const orderExpr = columns.has("updated_at") && columns.has("created_at")
    ? "COALESCE(updated_at, created_at, '')"
    : columns.has("created_at")
      ? "created_at"
      : "''";
  return (
    db
      .prepare(
        `
        SELECT *
        FROM success_criteria_evaluations
        WHERE run_id = ?
        ORDER BY ${orderExpr} DESC
        LIMIT 1
        `,
      )
      .get(runId) as Row | undefined
  ) ?? null;
};

const _writebackForRun = (db: Database.Database, runId: string): Row | null => {
  if (!_safeTableExists(db, "improvement_writebacks")) {
    return null;
  }
  const columns = _tableColumns(db, "improvement_writebacks");
  if (!columns.has("run_id")) {
    return null;
  }
  return (
    db
      .prepare(
        `
        SELECT *
        FROM improvement_writebacks
        WHERE run_id = ?
        ORDER BY COALESCE(updated_at, created_at, '') DESC
        LIMIT 1
        `,
      )
      .get(runId) as Row | undefined
  ) ?? null;
};

const _unresolvedDeltaForProject = (db: Database.Database, projectId: string | null): Row | null => {
  if (!projectId || !_safeTableExists(db, "standards_delta_items")) {
    return null;
  }
  const columns = _tableColumns(db, "standards_delta_items");
  if (!columns.has("project_id")) {
    return null;
  }
  const statusSql = columns.has("status") ? "AND status IN ('open', 'pending')" : "";
  return (
    db
      .prepare(
        `
        SELECT *
        FROM standards_delta_items
        WHERE project_id = ?
        ${statusSql}
        ORDER BY COALESCE(priority_bucket, 'quick_wins'), COALESCE(severity, 0) DESC
        LIMIT 1
        `,
      )
      .get(projectId) as Row | undefined
  ) ?? null;
};

const _runForId = (db: Database.Database, runId: string): Row | null => {
  if (!_safeTableExists(db, "orchestration_runs")) {
    return null;
  }
  return (
    db
      .prepare(
        `
        SELECT *
        FROM orchestration_runs
        WHERE id = ?
        LIMIT 1
        `,
      )
      .get(runId) as Row | undefined
  ) ?? null;
};

export const previewDailyFlow = (
  db: Database.Database,
  input: { objective: string; projectId?: string | null },
): DailyFlowTrace => {
  const projectId = input.projectId ?? null;
  const [action] = getNextActions(db, { projectId, limit: 1 });
  const workflowKey = action?.recommendedWorkflowKey ?? null;
  const steps: DailyFlowStep[] = [
    _stepForGoal(input.objective, projectId, true),
    _stepForRoute(workflowKey, action?.rationale ?? null),
    _missingStep("packet", "Preview does not persist a packet."),
    _missingStep("run", "Preview does not create a run."),
    _missingStep("evaluation", "Preview does not run success criteria."),
    _missingStep("writeback", "Preview does not propose writebacks."),
    _stepForUnresolvedDelta(null),
    _stepForNextAction(db, projectId),
  ];
  return { projectId, objective: input.objective, isPreview: true, steps };
};

export const replayDailyFlow = (
  db: Database.Database,
  input: { runId: string },
): DailyFlowTrace => {
  const run = _runForId(db, input.runId);
  const objective = _text(run?.objective) || input.runId;
  const projectId = _nullableText(run?.project_id);
  const route = _jsonRecord(run?.route_result_json);
  const selectedWorkflow = route.selected_workflow as { workflow_key?: unknown } | undefined;
  const workflowKey = _text(selectedWorkflow?.workflow_key || run?.workflow_key) || null;
  const repoCloseout = _repoCloseoutForProject(db, projectId);
  const steps: DailyFlowStep[] = [
    _stepForGoal(objective, projectId, false),
    _stepForRoute(workflowKey, _text(run?.rationale) || null),
    _stepForPacket(_latestPacketForRun(db, input.runId)),
    _stepForRun(run, repoCloseout),
    _stepForEvaluation(_evaluationForRun(db, input.runId), input.runId),
    _stepForWriteback(_writebackForRun(db, input.runId)),
    _stepForUnresolvedDelta(_unresolvedDeltaForProject(db, projectId)),
    _stepForNextAction(db, projectId),
  ];
  return { projectId, objective, isPreview: false, steps };
};
