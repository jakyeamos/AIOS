/**
 * Cross-entity operator search projection.
 *
 * Mirrors services/operator_search.py shape; canonical scoring, EntityKind set, and drill-down
 * path map live in Python. This TypeScript implementation executes the same bounded per-kind
 * LIKE search via better-sqlite3 prepared statements and attaches drillDownPath via
 * aios-ui/lib/drill-down.ts so CLI and UI projections stay aligned.
 *
 * Safe-column projection: dispatchers project only ids, titles, summaries, keys, statuses, and
 * timestamps. proposed_change_json, evidence_json, and prompt body text are never returned.
 */

import type Database from "better-sqlite3";

import {
  automationPath,
  backfillTaskPath,
  deltaItemPath,
  divergentRunPath,
  experimentPath,
  findingPath,
  knowledgePath,
  learningPatternPath,
  packetPath,
  promotionLifecycleItemPath,
  promptTemplatePath,
  promptUsePath,
  routeDecisionPath,
  runPath,
  skillPath,
  workflowPath,
  writebackPath,
} from "@/lib/drill-down";
import type { EntityKind, OperatorSearchHit } from "@/lib/control-plane";

export const MAX_QUERY_LENGTH = 200;
export const DEFAULT_LIMIT = 50;
export const PER_KIND_CAP = 20;

const MAX_LIMIT = 200;
const RECENCY_BOOST_HALF_LIFE_DAYS = 14;
const EXACT_KEY_BOOST = 0.3;

type Row = Record<string, unknown>;
type SearchArgs = { query: string; projectId: string | null; now: Date };
type Searcher = (db: Database.Database, args: SearchArgs) => OperatorSearchHit[];

const ENTITY_KINDS: readonly EntityKind[] = [
  "run",
  "packet",
  "writeback",
  "finding",
  "prompt_template",
  "prompt_use",
  "skill",
  "workflow",
  "knowledge_object",
  "route_decision",
  "delta_item",
  "backfill_task",
  "automation",
  "experiment",
  "divergent_run",
  "learning_pattern",
  "promotion_lifecycle_item",
];

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

const _selectable = (columns: Set<string>, column: string, fallback = "''"): string =>
  columns.has(column) ? column : `${fallback} AS ${column}`;

const _lastUpdatedExpr = (columns: Set<string>): string => {
  if (columns.has("updated_at") && columns.has("created_at")) {
    return "COALESCE(updated_at, created_at)";
  }
  if (columns.has("updated_at")) {
    return "updated_at";
  }
  if (columns.has("created_at")) {
    return "created_at";
  }
  return "''";
};

const _text = (value: unknown): string => (value === null || value === undefined ? "" : String(value));

const _nullableText = (value: unknown): string | null => {
  const text = _text(value);
  return text ? text : null;
};

const _matchesQuery = (query: string, ...values: string[]): boolean => {
  if (!query) {
    return true;
  }
  const normalized = query.toLowerCase();
  return values.some((value) => value.toLowerCase().includes(normalized));
};

const _scoreHit = ({
  query,
  title,
  summary,
  key,
  lastUpdatedAt,
  now,
}: {
  query: string;
  title: string;
  summary: string;
  key: string;
  lastUpdatedAt: string;
  now: Date;
}): number => {
  const normalized = query.trim().toLowerCase();
  let base = 0;
  if (normalized) {
    if (title.toLowerCase().includes(normalized)) {
      base += 0.5;
    }
    if (summary.toLowerCase().includes(normalized)) {
      base += 0.3;
    }
    if (normalized === key.toLowerCase()) {
      base += EXACT_KEY_BOOST;
    }
  }
  const parsed = Date.parse(lastUpdatedAt.replace("Z", "+00:00"));
  const recency = Number.isNaN(parsed)
    ? 0
    : 0.2 *
      Math.pow(
        0.5,
        Math.max(0, now.getTime() - parsed) / 86_400_000 / RECENCY_BOOST_HALF_LIFE_DAYS,
      );
  return Math.min(base + recency, 1);
};

const _makeHit = ({
  kind,
  id,
  title,
  summary,
  projectId,
  sourceTable,
  lastUpdatedAt,
  query,
  key,
  now,
  drillDownPath,
  metadata = {},
}: {
  kind: EntityKind;
  id: string;
  title: string;
  summary: string;
  projectId: string | null;
  sourceTable: string;
  lastUpdatedAt: string;
  query: string;
  key: string;
  now: Date;
  drillDownPath: string;
  metadata?: Record<string, unknown>;
}): OperatorSearchHit => ({
  kind,
  id,
  title: title || id,
  summary,
  projectId,
  score: _scoreHit({ query, title: title || id, summary, key: key || id, lastUpdatedAt, now }),
  sourceTable,
  lastUpdatedAt,
  drillDownPath,
  metadata,
});

const _fetchRows = (
  db: Database.Database,
  table: string,
  columns: string,
  whereSql: string,
  params: unknown[],
  orderExpr: string,
): Row[] =>
  db
    .prepare(`SELECT ${columns} FROM ${table}${whereSql} ORDER BY ${orderExpr} DESC LIMIT ?`)
    .all(...params, PER_KIND_CAP) as Row[];

const _projectWhere = (columns: Set<string>, projectId: string | null): { sql: string; params: unknown[] } =>
  projectId && columns.has("project_id")
    ? { sql: " WHERE project_id = ?", params: [projectId] }
    : { sql: "", params: [] };

const _searchRuns: Searcher = (db, { query, projectId, now }) => {
  if (!_safeTableExists(db, "orchestration_runs")) return [];
  const columns = _tableColumns(db, "orchestration_runs");
  const lastExpr = _lastUpdatedExpr(columns);
  const { sql, params } = _projectWhere(columns, projectId);
  return _fetchRows(
    db,
    "orchestration_runs",
    `id, ${_selectable(columns, "objective")}, ${_selectable(columns, "project_id", "NULL")}, ${_selectable(columns, "status")}, ${lastExpr} AS last_updated_at`,
    sql,
    params,
    "last_updated_at",
  )
    .filter((row) => _matchesQuery(query, _text(row.id), _text(row.objective), _text(row.status)))
    .map((row) =>
      _makeHit({
        kind: "run",
        id: _text(row.id),
        title: _text(row.objective),
        summary: `status: ${_text(row.status) || "unknown"}`,
        projectId: _nullableText(row.project_id),
        sourceTable: "orchestration_runs",
        lastUpdatedAt: _text(row.last_updated_at),
        query,
        key: _text(row.id),
        now,
        drillDownPath: runPath(_text(row.id)),
        metadata: { status: row.status },
      }),
    );
};

const _searchPackets: Searcher = (db, { query, projectId, now }) => {
  if (!_safeTableExists(db, "briefing_packets")) return [];
  const columns = _tableColumns(db, "briefing_packets");
  const lastExpr = _lastUpdatedExpr(columns);
  const { sql, params } = _projectWhere(columns, projectId);
  return _fetchRows(
    db,
    "briefing_packets",
    `id, ${_selectable(columns, "summary")}, ${_selectable(columns, "project_id", "NULL")}, ${_selectable(columns, "run_id", "NULL")}, ${lastExpr} AS last_updated_at`,
    sql,
    params,
    "last_updated_at",
  )
    .filter((row) => _matchesQuery(query, _text(row.id), _text(row.summary)))
    .map((row) =>
      _makeHit({
        kind: "packet",
        id: _text(row.id),
        title: `Packet ${_text(row.id)}`,
        summary: _text(row.summary),
        projectId: _nullableText(row.project_id),
        sourceTable: "briefing_packets",
        lastUpdatedAt: _text(row.last_updated_at),
        query,
        key: _text(row.id),
        now,
        drillDownPath: packetPath(_text(row.id)),
        metadata: { runId: row.run_id },
      }),
    );
};

const _searchWritebacks: Searcher = (db, { query, projectId, now }) =>
  _simpleSearch(db, {
    table: "improvement_writebacks",
    kind: "writeback",
    projectId,
    query,
    now,
    columnsSql: (columns, lastExpr) =>
      `id, ${_selectable(columns, "title")}, ${_selectable(columns, "summary")}, ${_selectable(columns, "project_id", "NULL")}, ${_selectable(columns, "layer_key")}, ${_selectable(columns, "status")}, ${lastExpr} AS last_updated_at`,
    title: (row) => _text(row.title),
    summary: (row) => _text(row.summary),
    key: (row) => _text(row.layer_key || row.id),
    path: (row) => writebackPath(_text(row.id)),
    metadata: (row) => ({ status: row.status, layerKey: row.layer_key }),
  });

const _searchFindings: Searcher = (db, { query, now }) => {
  if (!_safeTableExists(db, "success_criteria_findings")) return [];
  const columns = _tableColumns(db, "success_criteria_findings");
  const lastExpr = _lastUpdatedExpr(columns);
  const messageExpr = columns.has("message") ? "message" : columns.has("summary") ? "summary" : "''";
  return _fetchRows(
    db,
    "success_criteria_findings",
    `id, ${_selectable(columns, "run_id", "NULL")}, ${_selectable(columns, "criterion_id")}, ${_selectable(columns, "level")}, ${messageExpr} AS message, ${lastExpr} AS last_updated_at`,
    "",
    [],
    "last_updated_at",
  )
    .filter((row) => _matchesQuery(query, _text(row.id), _text(row.criterion_id), _text(row.message)))
    .map((row) => {
      const runId = _text(row.run_id || row.id);
      return _makeHit({
        kind: "finding",
        id: _text(row.id),
        title: `${_text(row.level)} ${_text(row.criterion_id)}`.trim(),
        summary: _text(row.message),
        projectId: null,
        sourceTable: "success_criteria_findings",
        lastUpdatedAt: _text(row.last_updated_at),
        query,
        key: _text(row.criterion_id || row.id),
        now,
        drillDownPath: findingPath(runId, _text(row.id)),
        metadata: { runId: row.run_id, level: row.level },
      });
    });
};

const _searchPromptTemplates: Searcher = (db, { query, now }) => {
  if (!_safeTableExists(db, "prompts")) return [];
  const columns = _tableColumns(db, "prompts");
  const lastExpr = _lastUpdatedExpr(columns);
  const titleExpr = columns.has("title") ? "title" : "id";
  const summaryExpr = columns.has("summary") ? "summary" : columns.has("classification") ? "classification" : "''";
  return _fetchRows(
    db,
    "prompts",
    `id, ${titleExpr} AS title, ${summaryExpr} AS summary, ${lastExpr} AS last_updated_at`,
    "",
    [],
    "last_updated_at",
  )
    .filter((row) => _matchesQuery(query, _text(row.id), _text(row.title), _text(row.summary)))
    .map((row) =>
      _makeHit({
        kind: "prompt_template",
        id: _text(row.id),
        title: _text(row.title),
        summary: _text(row.summary),
        projectId: null,
        sourceTable: "prompts",
        lastUpdatedAt: _text(row.last_updated_at),
        query,
        key: _text(row.id),
        now,
        drillDownPath: promptTemplatePath(_text(row.id)),
      }),
    );
};

const _searchPromptUses: Searcher = (db, { query, now }) => {
  if (!_safeTableExists(db, "prompts_used")) return [];
  const columns = _tableColumns(db, "prompts_used");
  const lastExpr = _lastUpdatedExpr(columns);
  return _fetchRows(
    db,
    "prompts_used",
    `${_selectable(columns, "id", "rowid")}, ${_selectable(columns, "template_id")}, ${_selectable(columns, "classification")}, ${_selectable(columns, "outcome_score", "NULL")}, ${lastExpr} AS last_updated_at`,
    "",
    [],
    "last_updated_at",
  )
    .filter((row) => _matchesQuery(query, _text(row.id), _text(row.template_id), _text(row.classification)))
    .map((row) =>
      _makeHit({
        kind: "prompt_use",
        id: _text(row.id),
        title: `Prompt use ${_text(row.template_id || row.classification)}`,
        summary: `classification: ${_text(row.classification)}`,
        projectId: null,
        sourceTable: "prompts_used",
        lastUpdatedAt: _text(row.last_updated_at),
        query,
        key: _text(row.template_id || row.classification || row.id),
        now,
        drillDownPath: promptUsePath(_text(row.id)),
        metadata: { outcomeScore: row.outcome_score },
      }),
    );
};

const _searchSkills: Searcher = (db, { query, now }) => {
  if (!_safeTableExists(db, "workflow_skill_experiments")) return [];
  const columns = _tableColumns(db, "workflow_skill_experiments");
  if (!columns.has("skill_key")) return [];
  const lastExpr = _lastUpdatedExpr(columns);
  const rows = _fetchRows(
    db,
    "workflow_skill_experiments",
    `skill_key AS id, skill_key, ${_selectable(columns, "workflow_key")}, ${lastExpr} AS last_updated_at`,
    "",
    [],
    "last_updated_at",
  );
  const seen = new Set<string>();
  return rows.flatMap((row) => {
    const skillKey = _text(row.skill_key);
    if (!skillKey || seen.has(skillKey)) return [];
    seen.add(skillKey);
    const summary = `workflow: ${_text(row.workflow_key)}`;
    if (!_matchesQuery(query, skillKey, summary)) return [];
    return [
      _makeHit({
        kind: "skill",
        id: skillKey,
        title: skillKey,
        summary,
        projectId: null,
        sourceTable: "workflow_skill_experiments",
        lastUpdatedAt: _text(row.last_updated_at),
        query,
        key: skillKey,
        now,
        drillDownPath: skillPath(skillKey),
        metadata: { workflowKey: row.workflow_key },
      }),
    ];
  });
};

const _searchWorkflows: Searcher = (db, { query, projectId, now }) => {
  if (!_safeTableExists(db, "orchestration_runs")) return [];
  const columns = _tableColumns(db, "orchestration_runs");
  if (!columns.has("workflow_key")) return [];
  const lastExpr = _lastUpdatedExpr(columns);
  const where = projectId && columns.has("project_id") ? " WHERE workflow_key IS NOT NULL AND project_id = ?" : " WHERE workflow_key IS NOT NULL";
  const params = projectId && columns.has("project_id") ? [projectId] : [];
  const rows = db
    .prepare(
      `SELECT workflow_key AS id, workflow_key, ${_selectable(columns, "project_id", "NULL")}, MAX(${lastExpr}) AS last_updated_at FROM orchestration_runs${where} GROUP BY workflow_key ORDER BY last_updated_at DESC LIMIT ?`,
    )
    .all(...params, PER_KIND_CAP) as Row[];
  return rows
    .filter((row) => _matchesQuery(query, _text(row.workflow_key)))
    .map((row) =>
      _makeHit({
        kind: "workflow",
        id: _text(row.id),
        title: _text(row.workflow_key),
        summary: "Workflow observed in orchestration runs",
        projectId: _nullableText(row.project_id),
        sourceTable: "orchestration_runs",
        lastUpdatedAt: _text(row.last_updated_at),
        query,
        key: _text(row.workflow_key),
        now,
        drillDownPath: workflowPath(_text(row.workflow_key)),
      }),
    );
};

const _searchKnowledge: Searcher = (db, args) => _searchKnowledgeTable(db, "knowledge_objects", args);

const _searchRouteDecisions: Searcher = (db, { query, projectId, now }) => {
  if (!_safeTableExists(db, "orchestration_runs")) return [];
  const columns = _tableColumns(db, "orchestration_runs");
  if (!columns.has("route_id")) return [];
  const lastExpr = _lastUpdatedExpr(columns);
  const { sql, params } = _projectWhere(columns, projectId);
  return _fetchRows(
    db,
    "orchestration_runs",
    `id, route_id, ${_selectable(columns, "objective")}, ${_selectable(columns, "project_id", "NULL")}, ${lastExpr} AS last_updated_at`,
    sql,
    params,
    "last_updated_at",
  )
    .filter((row) => _text(row.route_id) && _matchesQuery(query, _text(row.id), _text(row.route_id), _text(row.objective)))
    .map((row) =>
      _makeHit({
        kind: "route_decision",
        id: _text(row.route_id),
        title: `Route ${_text(row.route_id)}`,
        summary: _text(row.objective),
        projectId: _nullableText(row.project_id),
        sourceTable: "orchestration_runs",
        lastUpdatedAt: _text(row.last_updated_at),
        query,
        key: _text(row.route_id),
        now,
        drillDownPath: routeDecisionPath(_text(row.id), _text(row.route_id)),
        metadata: { runId: row.id },
      }),
    );
};

const _searchDeltaItems: Searcher = (db, args) =>
  _simpleSearch(db, {
    ...args,
    table: "standards_delta_items",
    kind: "delta_item",
    columnsSql: (columns, lastExpr) =>
      `id, ${_selectable(columns, "domain")}, ${_selectable(columns, "summary")}, ${_selectable(columns, "project_id", "NULL")}, ${_selectable(columns, "priority_bucket")}, ${lastExpr} AS last_updated_at`,
    title: (row) => _text(row.domain || row.id),
    summary: (row) => _text(row.summary),
    key: (row) => _text(row.id),
    path: (row) => deltaItemPath(_nullableText(row.project_id), _text(row.id)),
    metadata: (row) => ({ priorityBucket: row.priority_bucket }),
  });

const _searchBackfillTasks: Searcher = (db, args) =>
  _simpleSearch(db, {
    ...args,
    table: "standards_backfill_tasks",
    kind: "backfill_task",
    columnsSql: (columns, lastExpr) =>
      `id, ${_selectable(columns, "title")}, ${_selectable(columns, "summary")}, ${_selectable(columns, "project_id", "NULL")}, ${_selectable(columns, "status")}, ${lastExpr} AS last_updated_at`,
    title: (row) => _text(row.title || row.id),
    summary: (row) => _text(row.summary),
    key: (row) => _text(row.id),
    path: (row) => backfillTaskPath(_nullableText(row.project_id), _text(row.id)),
    metadata: (row) => ({ status: row.status }),
  });

const _searchAutomations: Searcher = (db, args) =>
  _simpleSearch(db, {
    ...args,
    table: "automation_status",
    kind: "automation",
    columnsSql: (columns, lastExpr) =>
      `id, ${_selectable(columns, "name")}, ${_selectable(columns, "status")}, NULL AS project_id, ${lastExpr} AS last_updated_at`,
    title: (row) => _text(row.name || row.id),
    summary: (row) => `status: ${_text(row.status)}`,
    key: (row) => _text(row.id),
    path: (row) => automationPath(_text(row.id)),
    metadata: (row) => ({ status: row.status }),
  });

const _searchExperiments: Searcher = (db, args) =>
  _simpleSearch(db, {
    ...args,
    table: "workflow_experiments",
    kind: "experiment",
    columnsSql: (columns, lastExpr) =>
      `id, ${_selectable(columns, "workflow_key")}, ${_selectable(columns, "status")}, NULL AS project_id, ${lastExpr} AS last_updated_at`,
    title: (row) => `Experiment ${_text(row.workflow_key || row.id)}`,
    summary: (row) => `status: ${_text(row.status)}`,
    key: (row) => _text(row.workflow_key || row.id),
    path: (row) => experimentPath(_text(row.id)),
    metadata: (row) => ({ status: row.status }),
  });

const _searchDivergentRuns: Searcher = (db, args) =>
  _simpleSearch(db, {
    ...args,
    table: "divergent_runs",
    kind: "divergent_run",
    columnsSql: (columns, lastExpr) =>
      `id, ${_selectable(columns, "objective")}, ${_selectable(columns, "winner_agent")}, ${_selectable(columns, "project_id", "NULL")}, ${lastExpr} AS last_updated_at`,
    title: (row) => _text(row.objective || row.id),
    summary: (row) => `winner: ${_text(row.winner_agent)}`,
    key: (row) => _text(row.id),
    path: (row) => divergentRunPath(_text(row.id)),
    metadata: (row) => ({ winnerAgent: row.winner_agent }),
  });

const _searchLearningPatterns: Searcher = (db, args) =>
  _simpleSearch(db, {
    ...args,
    table: "workflow_learning_events",
    kind: "learning_pattern",
    columnsSql: (columns, lastExpr) =>
      `${_selectable(columns, "id", "rowid")}, ${_selectable(columns, "signal_kind")}, ${_selectable(columns, "proposal_target")}, NULL AS project_id, ${lastExpr} AS last_updated_at`,
    title: (row) => _text(row.signal_kind || row.id),
    summary: (row) => `target: ${_text(row.proposal_target)}`,
    key: (row) => _text(row.signal_kind || row.id),
    path: (row) => learningPatternPath(_text(row.id)),
    metadata: (row) => ({ proposalTarget: row.proposal_target }),
  });

const _searchPromotionLifecycleItems: Searcher = (db, args) =>
  _simpleSearch(db, {
    ...args,
    table: "promotion_lifecycle_items",
    kind: "promotion_lifecycle_item",
    columnsSql: (columns, lastExpr) =>
      `id, ${_selectable(columns, "item_kind")}, ${_selectable(columns, "item_key")}, ${_selectable(columns, "status")}, NULL AS project_id, ${lastExpr} AS last_updated_at`,
    title: (row) => `${_text(row.item_kind)} ${_text(row.item_key)}`.trim(),
    summary: (row) => `status: ${_text(row.status)}`,
    key: (row) => _text(row.item_key || row.id),
    path: (row) => promotionLifecycleItemPath(_text(row.id)),
    metadata: (row) => ({ itemKind: row.item_kind, itemKey: row.item_key, status: row.status }),
  });

const _simpleSearch = (
  db: Database.Database,
  args: SearchArgs & {
    table: string;
    kind: EntityKind;
    columnsSql: (columns: Set<string>, lastExpr: string) => string;
    title: (row: Row) => string;
    summary: (row: Row) => string;
    key: (row: Row) => string;
    path: (row: Row) => string;
    metadata?: (row: Row) => Record<string, unknown>;
  },
): OperatorSearchHit[] => {
  if (!_safeTableExists(db, args.table)) return [];
  const columns = _tableColumns(db, args.table);
  const lastExpr = _lastUpdatedExpr(columns);
  const { sql, params } = _projectWhere(columns, args.projectId);
  return _fetchRows(db, args.table, args.columnsSql(columns, lastExpr), sql, params, "last_updated_at")
    .filter((row) => _matchesQuery(args.query, _text(row.id), args.title(row), args.summary(row), args.key(row)))
    .map((row) =>
      _makeHit({
        kind: args.kind,
        id: _text(row.id),
        title: args.title(row),
        summary: args.summary(row),
        projectId: _nullableText(row.project_id),
        sourceTable: args.table,
        lastUpdatedAt: _text(row.last_updated_at),
        query: args.query,
        key: args.key(row),
        now: args.now,
        drillDownPath: args.path(row),
        metadata: args.metadata?.(row) ?? {},
      }),
    );
};

const _searchKnowledgeTable = (
  db: Database.Database,
  table: string,
  { query, projectId, now }: SearchArgs,
): OperatorSearchHit[] => {
  if (!_safeTableExists(db, table)) return [];
  const columns = _tableColumns(db, table);
  const lastExpr = _lastUpdatedExpr(columns);
  const { sql, params } = _projectWhere(columns, projectId);
  return _fetchRows(
    db,
    table,
    `id, ${_selectable(columns, "title")}, ${_selectable(columns, "summary")}, ${_selectable(columns, "key")}, ${_selectable(columns, "kind")}, ${_selectable(columns, "project_id", "NULL")}, ${lastExpr} AS last_updated_at`,
    sql,
    params,
    "last_updated_at",
  )
    .filter((row) => _matchesQuery(query, _text(row.id), _text(row.title), _text(row.summary), _text(row.key)))
    .map((row) =>
      _makeHit({
        kind: "knowledge_object",
        id: _text(row.id),
        title: _text(row.title),
        summary: _text(row.summary),
        projectId: _nullableText(row.project_id),
        sourceTable: table,
        lastUpdatedAt: _text(row.last_updated_at),
        query,
        key: _text(row.key || row.id),
        now,
        drillDownPath: knowledgePath(_text(row.id)),
        metadata: { knowledgeKind: row.kind },
      }),
    );
};

const _DISPATCH: Record<EntityKind, Searcher> = {
  run: _searchRuns,
  packet: _searchPackets,
  writeback: _searchWritebacks,
  finding: _searchFindings,
  prompt_template: _searchPromptTemplates,
  prompt_use: _searchPromptUses,
  skill: _searchSkills,
  workflow: _searchWorkflows,
  knowledge_object: _searchKnowledge,
  route_decision: _searchRouteDecisions,
  delta_item: _searchDeltaItems,
  backfill_task: _searchBackfillTasks,
  automation: _searchAutomations,
  experiment: _searchExperiments,
  divergent_run: _searchDivergentRuns,
  learning_pattern: _searchLearningPatterns,
  promotion_lifecycle_item: _searchPromotionLifecycleItems,
};

export const searchEntities = (
  db: Database.Database,
  args: { query: string; kinds?: readonly EntityKind[]; projectId?: string | null; limit?: number },
): OperatorSearchHit[] => {
  const query = args.query ?? "";
  if (query.length > MAX_QUERY_LENGTH) {
    throw new Error(`query length ${query.length} exceeds max ${MAX_QUERY_LENGTH}`);
  }
  const limit = args.limit ?? DEFAULT_LIMIT;
  if (limit < 1 || limit > MAX_LIMIT) {
    throw new Error(`limit ${limit} out of range [1, ${MAX_LIMIT}]`);
  }
  const targetKinds = args.kinds && args.kinds.length > 0 ? args.kinds : ENTITY_KINDS;
  const now = new Date();
  return targetKinds
    .flatMap((kind) => _DISPATCH[kind]?.(db, { query: query.trim(), projectId: args.projectId ?? null, now }) ?? [])
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
};
