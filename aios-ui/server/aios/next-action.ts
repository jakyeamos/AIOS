/**
 * Per-project next-action fusion projection.
 *
 * Mirrors services/next_action.py shape; canonical NextActionKind set, bucket weights, and
 * sub-fetcher SQL shapes live in Python. This TypeScript implementation runs the same SQL via
 * better-sqlite3 prepared statements and attaches drillDownPath via aios-ui/lib/drill-down.ts.
 */

import type Database from "better-sqlite3";

import {
  backfillTaskPath,
  deltaItemPath,
  findingPath,
  promotionLifecycleItemPath,
  runPath,
  writebackPath,
} from "@/lib/drill-down";
import type { NextAction, PriorityBucket } from "@/lib/control-plane";

export const DEFAULT_LIMIT = 10;
export const MAX_LIMIT = 50;

const BUCKET_WEIGHTS: Record<PriorityBucket, number> = {
  foundational: 0,
  high_leverage: 1,
  quick_wins: 2,
  blocked: 3,
  waived_deferred: 4,
};

type Row = Record<string, unknown>;
type FetchArgs = { projectId: string | null };

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

const _selectable = (columns: Set<string>, column: string, fallback = "NULL"): string =>
  columns.has(column) ? column : `${fallback} AS ${column}`;

const _text = (value: unknown): string => (value === null || value === undefined ? "" : String(value));

const _nullableText = (value: unknown): string | null => {
  const text = _text(value);
  return text ? text : null;
};

const _bucketWeight = (bucket: PriorityBucket): number => BUCKET_WEIGHTS[bucket] ?? 99;

const _normalizeBucket = (value: unknown): PriorityBucket => {
  const bucket = _text(value);
  return bucket in BUCKET_WEIGHTS ? (bucket as PriorityBucket) : "quick_wins";
};

const _jsonRecord = (raw: unknown): Record<string, unknown> => {
  if (!raw) return {};
  try {
    const parsed = JSON.parse(String(raw)) as unknown;
    return parsed && typeof parsed === "object" && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : {};
  } catch {
    return {};
  }
};

const _fromHealthDeltas = (db: Database.Database, { projectId }: FetchArgs): NextAction[] => {
  if (!_safeTableExists(db, "standards_delta_items")) return [];
  const columns = _tableColumns(db, "standards_delta_items");
  const where: string[] = [];
  const params: unknown[] = [];
  if (columns.has("status")) {
    where.push("status IN ('open', 'pending')");
  }
  if (projectId && columns.has("project_id")) {
    where.push("project_id = ?");
    params.push(projectId);
  }
  const whereSql = where.length > 0 ? `WHERE ${where.join(" AND ")}` : "";
  const rows = db
    .prepare(
      `
      SELECT id,
             ${_selectable(columns, "project_id")},
             ${_selectable(columns, "domain", "''")},
             ${_selectable(columns, "priority_bucket", "'quick_wins'")},
             ${_selectable(columns, "severity", "5")},
             ${_selectable(columns, "summary", "''")},
             ${_selectable(columns, "remediation_playbook_json", "'{}'")}
      FROM standards_delta_items
      ${whereSql}
      ORDER BY priority_bucket, severity DESC
      LIMIT 20
      `,
    )
    .all(...params) as Row[];
  return rows.map((row) => {
    const rowProjectId = _nullableText(row.project_id);
    const playbook = _jsonRecord(row.remediation_playbook_json);
    const severity = Number(row.severity ?? 5);
    return {
      kind: "launch_remediation_workflow",
      title: `Remediate ${_text(row.domain || row.id)}`,
      rationale: _text(row.summary) || "Standards delta needs remediation.",
      projectId: rowProjectId,
      priorityBucket: _normalizeBucket(row.priority_bucket),
      recommendedWorkflowKey:
        typeof playbook.recommended_workflow_key === "string"
          ? playbook.recommended_workflow_key
          : null,
      evidenceIds: [_text(row.id)],
      drillDownPath: deltaItemPath(rowProjectId, _text(row.id)),
      confidence: Math.max(0, Math.min(severity / 10, 1)),
      metadata: { domain: row.domain },
    };
  });
};

const _fromPendingWritebacks = (db: Database.Database, { projectId }: FetchArgs): NextAction[] => {
  if (!_safeTableExists(db, "improvement_writebacks")) return [];
  const columns = _tableColumns(db, "improvement_writebacks");
  const where = ["status = 'pending_approval'", "requires_approval = 1"];
  const params: unknown[] = [];
  if (projectId && columns.has("project_id")) {
    where.push("project_id = ?");
    params.push(projectId);
  }
  const rows = db
    .prepare(
      `
      SELECT id,
             ${_selectable(columns, "run_id")},
             ${_selectable(columns, "project_id")},
             ${_selectable(columns, "layer_type", "''")},
             ${_selectable(columns, "layer_key", "''")},
             ${_selectable(columns, "title", "''")},
             ${_selectable(columns, "summary", "''")},
             ${_selectable(columns, "proposed_change_json", "'{}'")},
             ${_selectable(columns, "created_at", "''")}
      FROM improvement_writebacks
      WHERE ${where.join(" AND ")}
      ORDER BY created_at DESC
      LIMIT 20
      `,
    )
    .all(...params) as Row[];
  return rows.map((row) => {
    const proposedChange = _text(row.proposed_change_json);
    const isLearning = proposedChange.includes('"source": "learning_analysis"');
    const evidenceIds = [_text(row.id), _text(row.run_id)].filter(Boolean);
    return {
      kind: isLearning ? "review_learning_proposal" : "approve_pending_writeback",
      title: _text(row.title || row.id),
      rationale: _text(row.summary) || "Pending governed writeback requires review.",
      projectId: _nullableText(row.project_id),
      priorityBucket: isLearning ? "high_leverage" : "foundational",
      recommendedWorkflowKey: null,
      evidenceIds,
      drillDownPath: writebackPath(_text(row.id)),
      confidence: isLearning ? 0.8 : 0.85,
      metadata: { layerType: row.layer_type, layerKey: row.layer_key },
    };
  });
};

const _fromOpenBlockers = (db: Database.Database, { projectId }: FetchArgs): NextAction[] => {
  if (!_safeTableExists(db, "success_criteria_findings")) return [];
  const columns = _tableColumns(db, "success_criteria_findings");
  const runIdColumn = columns.has("run_id") ? "f.run_id AS run_id" : "NULL AS run_id";
  const criterionIdColumn = columns.has("criterion_id") ? "f.criterion_id AS criterion_id" : "NULL AS criterion_id";
  const messageColumn = columns.has("message") ? "f.message" : columns.has("summary") ? "f.summary" : "''";
  const createdAtColumn = columns.has("created_at") ? "f.created_at AS created_at" : "'' AS created_at";
  const canJoinRuns = columns.has("run_id") && _safeTableExists(db, "orchestration_runs");
  const where = ["f.level = 'blocker'", "f.resolution_status = 'open'"];
  const params: unknown[] = [];
  if (projectId && canJoinRuns) {
    where.push("r.project_id = ?");
    params.push(projectId);
  }
  const rows = db
    .prepare(
      `
      SELECT f.id,
             ${runIdColumn},
             ${criterionIdColumn},
             f.level,
             ${messageColumn} AS message,
             ${canJoinRuns ? "r.project_id" : "NULL"} AS project_id,
             ${createdAtColumn}
      FROM success_criteria_findings f
      ${canJoinRuns ? "LEFT JOIN orchestration_runs r ON r.id = f.run_id" : ""}
      WHERE ${where.join(" AND ")}
      ORDER BY f.created_at DESC
      LIMIT 20
      `,
    )
    .all(...params) as Row[];
  return rows.map((row) => {
    const runId = _text(row.run_id || row.id);
    return {
      kind: "resolve_open_blocker",
      title: `Resolve blocker ${_text(row.criterion_id)}`,
      rationale: _text(row.message) || "Open blocker needs resolution.",
      projectId: _nullableText(row.project_id),
      priorityBucket: "foundational",
      recommendedWorkflowKey: null,
      evidenceIds: [_text(row.id), _text(row.run_id)].filter(Boolean),
      drillDownPath: findingPath(runId, _text(row.id)),
      confidence: 0.9,
      metadata: { criterionId: row.criterion_id },
    };
  });
};

const _fromTerminalRunGaps = (db: Database.Database, { projectId }: FetchArgs): NextAction[] => {
  if (!_safeTableExists(db, "orchestration_runs")) return [];
  const hasLearning = _safeTableExists(db, "workflow_learning_events");
  const columns = _tableColumns(db, "orchestration_runs");
  const where = [
    "r.status IN ('completed', 'failed', 'partial', 'needs_follow_up', 'follow_up_needed')",
  ];
  const params: unknown[] = [];
  if (projectId && columns.has("project_id")) {
    where.push("r.project_id = ?");
    params.push(projectId);
  }
  const rows = db
    .prepare(
      `
      SELECT r.id, r.project_id, r.objective, r.status
      FROM orchestration_runs r
      ${hasLearning ? "LEFT JOIN workflow_learning_events e ON e.run_id = r.id" : ""}
      WHERE ${where.join(" AND ")} ${hasLearning ? "AND e.id IS NULL" : ""}
      ORDER BY COALESCE(r.updated_at, r.created_at) DESC
      LIMIT 20
      `,
    )
    .all(...params) as Row[];
  return rows.map((row) => ({
    kind: "fix_terminal_run_gap",
    title: `Record learning evidence for ${_text(row.id)}`,
    rationale: `Terminal run has status ${_text(row.status)} but no learning event.`,
    projectId: _nullableText(row.project_id),
    priorityBucket: "high_leverage",
    recommendedWorkflowKey: null,
    evidenceIds: [_text(row.id)],
    drillDownPath: runPath(_text(row.id)),
    confidence: 0.7,
    metadata: { status: row.status },
  }));
};

const _fromBackfillTasks = (db: Database.Database, { projectId }: FetchArgs): NextAction[] => {
  if (!_safeTableExists(db, "standards_backfill_tasks")) return [];
  const columns = _tableColumns(db, "standards_backfill_tasks");
  const where: string[] = [];
  const params: unknown[] = [];
  if (columns.has("status")) {
    where.push("status IN ('pending', 'in_progress')");
  }
  if (projectId && columns.has("project_id")) {
    where.push("project_id = ?");
    params.push(projectId);
  }
  const whereSql = where.length > 0 ? `WHERE ${where.join(" AND ")}` : "";
  const rows = db
    .prepare(
      `
      SELECT id,
             ${_selectable(columns, "project_id")},
             ${_selectable(columns, "summary", "''")},
             ${_selectable(columns, "status", "'pending'")},
             ${_selectable(columns, "priority_bucket", "'quick_wins'")},
             ${_selectable(columns, "created_at", "''")}
      FROM standards_backfill_tasks
      ${whereSql}
      ORDER BY priority_bucket, created_at
      LIMIT 20
      `,
    )
    .all(...params) as Row[];
  return rows.map((row) => {
    const rowProjectId = _nullableText(row.project_id);
    return {
      kind: "complete_backfill_task",
      title: `Complete backfill ${_text(row.id)}`,
      rationale: _text(row.summary) || "Backfill task needs completion.",
      projectId: rowProjectId,
      priorityBucket: _normalizeBucket(row.priority_bucket),
      recommendedWorkflowKey: null,
      evidenceIds: [_text(row.id)],
      drillDownPath: backfillTaskPath(rowProjectId, _text(row.id)),
      confidence: 0.6,
      metadata: { status: row.status },
    };
  });
};

const _fromPromotionCandidates = (db: Database.Database, _args: FetchArgs): NextAction[] => {
  if (!_safeTableExists(db, "promotion_lifecycle_items")) return [];
  const rows = db
    .prepare(
      `
      SELECT id, item_kind, item_key, status, created_at
      FROM promotion_lifecycle_items
      WHERE status = 'candidate'
      ORDER BY created_at DESC
      LIMIT 20
      `,
    )
    .all() as Row[];
  return rows.map((row) => ({
    kind: "promote_candidate_asset",
    title: `Review candidate ${_text(row.item_kind)} ${_text(row.item_key)}`,
    rationale: "Candidate asset is ready for promotion review.",
    projectId: null,
    priorityBucket: "quick_wins",
    recommendedWorkflowKey: null,
    evidenceIds: [_text(row.id)],
    drillDownPath: promotionLifecycleItemPath(_text(row.id)),
    confidence: 0.65,
    metadata: { itemKind: row.item_kind, itemKey: row.item_key },
  }));
};

export const getNextActions = (
  db: Database.Database,
  args: { projectId?: string | null; limit?: number } = {},
): NextAction[] => {
  const limit = args.limit ?? DEFAULT_LIMIT;
  if (limit < 1 || limit > MAX_LIMIT) {
    throw new Error(`limit ${limit} out of range [1, ${MAX_LIMIT}]`);
  }
  const projectId = args.projectId ?? null;
  const actions: NextAction[] = [
    ..._fromHealthDeltas(db, { projectId }),
    ..._fromPendingWritebacks(db, { projectId }),
    ..._fromOpenBlockers(db, { projectId }),
    ..._fromTerminalRunGaps(db, { projectId }),
    ..._fromBackfillTasks(db, { projectId }),
    ..._fromPromotionCandidates(db, { projectId }),
  ];
  return actions
    .sort((a, b) => {
      const bucketDelta = _bucketWeight(a.priorityBucket) - _bucketWeight(b.priorityBucket);
      return bucketDelta === 0 ? b.confidence - a.confidence : bucketDelta;
    })
    .slice(0, limit);
};
