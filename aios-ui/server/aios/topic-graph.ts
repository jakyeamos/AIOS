import { randomUUID } from "node:crypto";
import fs from "node:fs";
import path from "node:path";

import type Database from "better-sqlite3";

import type {
  ContextTrace,
  ImprovementWriteback,
  TopicGraphMarker,
  TopicGraphReference,
  TopicGraphRelationship,
  TopicGraphTopic,
} from "@/lib/control-plane";
import { agentProfiles, workflowTemplates } from "@/server/aios/catalog";
import {
  extractMarkdownTitle,
  extractWikiLinks,
  parseFrontmatterList,
  parseSimpleFrontmatter,
  resolveVaultRoot,
  summarizeParagraph,
} from "@/server/aios/filesystem";
import { ensureControlPlaneSchema } from "@/server/aios/schema";

type TopicRow = {
  id: string;
  slug: string;
  title: string;
  kind: TopicGraphTopic["kind"];
  summary: string;
  confidence: number;
  freshness: string;
  canonicalHref: string;
  tagsJson: string;
  referenceCount: number;
  markerCount: number;
};

type ReferenceRow = {
  sourceKind: string;
  sourceId: string | null;
  label: string;
  href: string;
  excerpt: string;
  freshness: string;
  confidence: number;
};

type MarkerRow = {
  markerKind: TopicGraphMarker["kind"];
  severity: TopicGraphMarker["severity"];
  summary: string;
  sourceRef: string | null;
};

type RelationshipRow = {
  relation: string;
  fromSlug: string;
  toSlug: string;
  fromTitle: string;
  toTitle: string;
  weight: number;
};

type TopicSeed = {
  slug: string;
  title: string;
  kind: TopicGraphTopic["kind"];
  summary: string;
  confidence: number;
  freshness: string;
  canonicalHref: string;
  projectId?: string | null;
  tags?: string[];
  metadata?: Record<string, unknown>;
};

type TopicGraphSearchOptions = {
  projectId?: string | null;
  query?: string;
  limit?: number;
};

type TopicGraphMatch = {
  topic: TopicGraphTopic;
  score: number;
  why: string;
};

type TopicCatalogEntry = TopicSeed & {
  id: string;
  tokens: string[];
};

type RunSourceRow = {
  id: string;
  projectId: string | null;
  projectName: string | null;
  objective: string;
  workflowKey: string;
  agentKey: string;
  status: string;
  rationale: string;
  resultSummary: string | null;
  createdAt: string;
};

type PacketSourceRow = {
  id: string;
  runId: string;
  projectId: string | null;
  objective: string;
  workflowKey: string;
  agentKey: string;
  sectionsJson: string;
  createdAt: string;
};

type MemorySourceRow = {
  id: string;
  projectId: string | null;
  summary: string;
  changesJson: string;
  risksJson: string;
  openQuestionsJson: string;
  createdAt: string;
};

type ProjectSourceRow = {
  id: string;
  name: string;
  status: string;
  repoPath: string;
  sessionCount: number;
  openBugs: number;
  lastActiveAt: string | null;
};

const GRAPH_KEY = "default";
const GRAPH_TTL_MS = 5 * 60 * 1000;

const parseJsonArray = <T>(raw: string, fallback: T): T => {
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
};

const normalizeText = (value: string): string =>
  value
    .toLowerCase()
    .replace(/[^a-z0-9\s/-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

const tokenize = (value: string): string[] => {
  const stopWords = new Set([
    "this",
    "that",
    "with",
    "from",
    "into",
    "then",
    "than",
    "what",
    "when",
    "where",
    "which",
    "task",
    "work",
    "project",
    "system",
    "aios",
    "into",
    "through",
    "about",
  ]);

  return normalizeText(value)
    .split(" ")
    .filter((token) => token.length >= 3 && !stopWords.has(token));
};

const estimateFreshnessLabel = (isoValue: string | null): string => {
  if (!isoValue) {
    return "Unknown freshness";
  }

  const timestamp = new Date(isoValue).getTime();
  if (Number.isNaN(timestamp)) {
    return isoValue;
  }

  const deltaDays = Math.floor((Date.now() - timestamp) / 86_400_000);
  if (deltaDays <= 1) {
    return "Updated in the last day";
  }
  if (deltaDays <= 7) {
    return `Updated ${deltaDays} days ago`;
  }
  return `Stale for ${deltaDays} days`;
};

const freshnessScore = (freshness: string): number => {
  if (freshness.includes("last day")) {
    return 1;
  }
  if (freshness.includes("days ago")) {
    return 0.7;
  }
  if (freshness.includes("Stale")) {
    return 0.3;
  }
  return 0.5;
};

const collectWikiSeeds = (): TopicSeed[] => {
  const wikiDir = path.join(resolveVaultRoot(), "06 Knowledge", "Wiki");
  if (!fs.existsSync(wikiDir)) {
    return [];
  }

  return fs
    .readdirSync(wikiDir)
    .filter((name) => name.endsWith(".md"))
    .sort()
    .flatMap((name) => {
      const fullPath = path.join(wikiDir, name);
      const content = fs.readFileSync(fullPath, "utf8");
      const frontmatter = parseSimpleFrontmatter(content);
      const reviewStatus = frontmatter["review-status"] ?? "current";
      const provenance = frontmatter.provenance ?? "human";
      const quality = frontmatter.quality ?? "human-curated";

      if (reviewStatus === "pending" || provenance === "agent-promoted" || quality === "draft") {
        return [];
      }

      const fileStem = name.replace(/\.md$/, "");
      const tags = parseFrontmatterList(content, "tags");

      return [
        {
          slug: `concept-${fileStem}`,
          title: extractMarkdownTitle(content, fileStem),
          kind: "concept",
          summary: summarizeParagraph(content),
          confidence: quality === "human-curated" ? 0.88 : 0.72,
          freshness: estimateFreshnessLabel(frontmatter.updated ?? frontmatter.created ?? fs.statSync(fullPath).mtime.toISOString()),
          canonicalHref: `/knowledge/concept-${fileStem}`,
          tags,
          metadata: {
            sourcePath: fullPath,
            wikiLinks: extractWikiLinks(content),
          },
        } satisfies TopicSeed,
      ];
    });
};

const collectProjectSeeds = (db: Database.Database): TopicSeed[] =>
  (
    db
      .prepare(
        `
        SELECT
          p.id,
          p.name,
          p.status,
          p.repo_path AS repoPath,
          (SELECT COUNT(*) FROM sessions s WHERE s.project_id = p.id) AS sessionCount,
          (SELECT COUNT(*) FROM bug_log b WHERE b.project_id = p.id AND b.status = 'open') AS openBugs,
          (SELECT MAX(s.started_at) FROM sessions s WHERE s.project_id = p.id) AS lastActiveAt
        FROM projects p
      `,
      )
      .all() as ProjectSourceRow[]
  ).map((project) => ({
    slug: `project-${project.id}`,
    title: project.name,
    kind: "project",
    summary: `${project.sessionCount} sessions, ${project.openBugs} open bugs, repo at ${project.repoPath}.`,
    confidence: project.openBugs > 0 ? 0.74 : 0.88,
    freshness: estimateFreshnessLabel(project.lastActiveAt),
    canonicalHref: `/projects/${project.id}`,
    projectId: project.id,
    tags: ["project", project.status],
    metadata: {
      repoPath: project.repoPath,
      sessionCount: project.sessionCount,
      openBugs: project.openBugs,
    },
  }));

const collectWorkflowSeeds = (): TopicSeed[] =>
  workflowTemplates.map((workflow) => ({
    slug: `workflow-${workflow.key}`,
    title: workflow.name,
    kind: "workflow",
    summary: workflow.summary,
    confidence: 0.76,
    freshness: "Registry entry",
    canonicalHref: `/knowledge/workflow-${workflow.key}`,
    tags: ["workflow", ...workflow.triggers],
    metadata: {
      key: workflow.key,
      validation: workflow.validation,
    },
  }));

const collectAgentSeeds = (): TopicSeed[] =>
  agentProfiles.map((agent) => ({
    slug: `agent-${agent.key}`,
    title: agent.name,
    kind: "agent",
    summary: agent.summary,
    confidence: 0.72,
    freshness: "Registry entry",
    canonicalHref: `/knowledge/agent-${agent.key}`,
    tags: ["agent", ...agent.bestFor],
    metadata: {
      key: agent.key,
      guardrails: agent.guardrails,
    },
  }));

const collectPolicySeeds = (): TopicSeed[] => [
  {
    slug: "policy-compact-ranked-context",
    title: "Compact Ranked Context",
    kind: "policy",
    summary: "Default policy: retrieve broadly inside AIOS, deliver only compact ranked context to agents, and trace every targeted expansion.",
    confidence: 0.98,
    freshness: "Locked product policy",
    canonicalHref: "/control",
    tags: ["policy", "context", "token-efficiency"],
  },
  {
    slug: "task-type-implementation-delivery",
    title: "Implementation Delivery",
    kind: "task_type",
    summary: "Task type for scoped implementation work with ranked packet delivery, validation, and durable writeback.",
    confidence: 0.8,
    freshness: "Derived from workflow registry",
    canonicalHref: "/control",
    tags: ["task-type", "implementation"],
  },
];

const createTopicCatalog = (db: Database.Database): TopicCatalogEntry[] => {
  const seeds = [
    ...collectProjectSeeds(db),
    ...collectWorkflowSeeds(),
    ...collectAgentSeeds(),
    ...collectPolicySeeds(),
    ...collectWikiSeeds(),
  ];

  return seeds.map((seed) => ({
    ...seed,
    id: `topic-${randomUUID()}`,
    tags: seed.tags ?? [],
    tokens: Array.from(new Set([...tokenize(seed.title), ...tokenize(seed.summary), ...(seed.tags ?? []).flatMap((tag) => tokenize(tag))])),
  }));
};

const findMatchingTopics = (catalog: TopicCatalogEntry[], text: string, limit = 4): Array<{ topicId: string; score: number }> => {
  const textTokens = new Set(tokenize(text));
  const normalized = normalizeText(text);

  return catalog
    .map((topic) => {
      const overlap = topic.tokens.filter((token) => textTokens.has(token)).length;
      const exactTitleMatch = normalized.includes(normalizeText(topic.title));
      const tagMatch = (topic.tags ?? []).some((tag) => normalized.includes(normalizeText(tag)));
      const score = overlap * 12 + (exactTitleMatch ? 18 : 0) + (tagMatch ? 8 : 0);
      return { topicId: topic.id, score };
    })
    .filter((entry) => entry.score > 0)
    .sort((left, right) => right.score - left.score)
    .slice(0, limit);
};

const upsertCatalog = (db: Database.Database, catalog: TopicCatalogEntry[]): void => {
  const insert = db.prepare(`
    INSERT INTO knowledge_topics (
      id,
      slug,
      title,
      kind,
      summary,
      confidence,
      freshness,
      project_id,
      canonical_href,
      tags_json,
      metadata_json,
      created_at,
      updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
  `);

  for (const topic of catalog) {
    insert.run(
      topic.id,
      topic.slug,
      topic.title,
      topic.kind,
      topic.summary,
      topic.confidence,
      topic.freshness,
      topic.projectId ?? null,
      topic.canonicalHref,
      JSON.stringify(topic.tags ?? []),
      JSON.stringify(topic.metadata ?? {}),
    );
  }
};

const addReference = (
  db: Database.Database,
  topicId: string,
  input: {
    sourceKind: string;
    sourceId: string | null;
    projectId?: string | null;
    label: string;
    href: string;
    excerpt: string;
    freshness: string;
    confidence: number;
    metadata?: Record<string, unknown>;
  },
): void => {
  db.prepare(`
    INSERT INTO knowledge_references (
      id,
      topic_id,
      source_kind,
      source_id,
      project_id,
      label,
      href,
      excerpt,
      freshness,
      confidence,
      metadata_json
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(
    `ref-${randomUUID()}`,
    topicId,
    input.sourceKind,
    input.sourceId,
    input.projectId ?? null,
    input.label,
    input.href,
    input.excerpt,
    input.freshness,
    input.confidence,
    JSON.stringify(input.metadata ?? {}),
  );
};

const addRelationship = (
  db: Database.Database,
  fromTopicId: string,
  toTopicId: string,
  relation: string,
  weight: number,
  provenanceKind: string,
  provenanceId: string | null,
): void => {
  db.prepare(`
    INSERT INTO knowledge_relationships (
      id,
      from_topic_id,
      to_topic_id,
      relation,
      weight,
      provenance_kind,
      provenance_id
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `).run(`rel-${randomUUID()}`, fromTopicId, toTopicId, relation, weight, provenanceKind, provenanceId);
};

const addMarker = (
  db: Database.Database,
  topicId: string,
  marker: TopicGraphMarker,
): void => {
  db.prepare(`
    INSERT INTO knowledge_markers (
      id,
      topic_id,
      marker_kind,
      severity,
      summary,
      source_ref
    )
    VALUES (?, ?, ?, ?, ?, ?)
  `).run(`marker-${randomUUID()}`, topicId, marker.kind, marker.severity, marker.summary, marker.sourceRef);
};

const ingestProjectReferences = (db: Database.Database, catalog: TopicCatalogEntry[]): void => {
  const projects = collectProjectSeeds(db);
  for (const project of projects) {
    const topic = catalog.find((entry) => entry.slug === project.slug);
    if (!topic) {
      continue;
    }

    addReference(db, topic.id, {
      sourceKind: "project",
      sourceId: project.projectId ?? null,
      projectId: project.projectId ?? null,
      label: `${project.title} state`,
      href: project.canonicalHref,
      excerpt: project.summary,
      freshness: project.freshness,
      confidence: project.confidence,
      metadata: project.metadata,
    });
  }
};

const ingestWikiReferences = (db: Database.Database, catalog: TopicCatalogEntry[]): void => {
  const wikiSeeds = collectWikiSeeds();
  for (const wiki of wikiSeeds) {
    const topic = catalog.find((entry) => entry.slug === wiki.slug);
    if (!topic) {
      continue;
    }

    addReference(db, topic.id, {
      sourceKind: "wiki",
      sourceId: wiki.slug,
      label: wiki.title,
      href: wiki.canonicalHref,
      excerpt: wiki.summary,
      freshness: wiki.freshness,
      confidence: wiki.confidence,
      metadata: wiki.metadata,
    });

    const rawWikiLinks = Array.isArray(wiki.metadata?.wikiLinks) ? wiki.metadata.wikiLinks : [];
    const wikiLinks = parseJsonArray<string[]>(JSON.stringify(rawWikiLinks), []);
    for (const link of wikiLinks) {
      const target = catalog.find((entry) => normalizeText(entry.title) === normalizeText(link));
      if (!target) {
        continue;
      }

      addRelationship(db, topic.id, target.id, "Links to", 0.92, "wiki", wiki.slug);
    }
  }
};

const ingestRunReferences = (db: Database.Database, catalog: TopicCatalogEntry[]): void => {
  const rows = db
    .prepare(
      `
      SELECT
        r.id,
        r.project_id AS projectId,
        p.name AS projectName,
        r.objective,
        r.workflow_key AS workflowKey,
        r.agent_key AS agentKey,
        r.status,
        r.rationale,
        r.result_summary AS resultSummary,
        r.created_at AS createdAt
      FROM orchestration_runs r
      LEFT JOIN projects p ON p.id = r.project_id
      ORDER BY r.created_at DESC
      LIMIT 80
    `,
    )
    .all() as RunSourceRow[];

  for (const row of rows) {
    const sourceText = [row.objective, row.rationale, row.resultSummary ?? ""].join(" ");
    const matches = [
      ...(row.projectId ? [{ topicId: catalog.find((entry) => entry.slug === `project-${row.projectId}`)?.id, score: 25 }] : []),
      { topicId: catalog.find((entry) => entry.slug === `workflow-${row.workflowKey}`)?.id, score: 20 },
      { topicId: catalog.find((entry) => entry.slug === `agent-${row.agentKey}`)?.id, score: 18 },
      ...findMatchingTopics(catalog, sourceText, 5),
    ].filter((match): match is { topicId: string; score: number } => Boolean(match.topicId));

    const uniqueMatches = matches.filter(
      (match, index, items) => items.findIndex((candidate) => candidate.topicId === match.topicId) === index,
    );

    for (const match of uniqueMatches) {
      addReference(db, match.topicId, {
        sourceKind: "run",
        sourceId: row.id,
        projectId: row.projectId,
        label: row.objective,
        href: "/control",
        excerpt: row.resultSummary ?? row.rationale,
        freshness: estimateFreshnessLabel(row.createdAt),
        confidence: row.status === "completed" ? 0.82 : 0.68,
        metadata: {
          status: row.status,
          workflowKey: row.workflowKey,
          agentKey: row.agentKey,
        },
      });
    }

    for (const left of uniqueMatches) {
      for (const right of uniqueMatches) {
        if (left.topicId === right.topicId) {
          continue;
        }
        addRelationship(db, left.topicId, right.topicId, "Co-mentioned in run", Math.min(0.95, (left.score + right.score) / 50), "run", row.id);
      }
    }
  }
};

const ingestPacketReferences = (db: Database.Database, catalog: TopicCatalogEntry[]): void => {
  const rows = db
    .prepare(
      `
      SELECT
        id,
        run_id AS runId,
        project_id AS projectId,
        objective,
        workflow_key AS workflowKey,
        agent_key AS agentKey,
        sections_json AS sectionsJson,
        created_at AS createdAt
      FROM briefing_packets
      ORDER BY created_at DESC
      LIMIT 80
    `,
    )
    .all() as PacketSourceRow[];

  for (const row of rows) {
    const sectionText = parseJsonArray<Array<{ title: string; body?: string; items: string[] }>>(row.sectionsJson, [])
      .flatMap((section) => [section.title, section.body ?? "", ...section.items])
      .join(" ");
    const matches = [
      ...(row.projectId ? [{ topicId: catalog.find((entry) => entry.slug === `project-${row.projectId}`)?.id, score: 25 }] : []),
      { topicId: catalog.find((entry) => entry.slug === `workflow-${row.workflowKey}`)?.id, score: 20 },
      { topicId: catalog.find((entry) => entry.slug === `agent-${row.agentKey}`)?.id, score: 18 },
      ...findMatchingTopics(catalog, `${row.objective} ${sectionText}`, 5),
    ].filter((match): match is { topicId: string; score: number } => Boolean(match.topicId));

    const uniqueMatches = matches.filter(
      (match, index, items) => items.findIndex((candidate) => candidate.topicId === match.topicId) === index,
    );

    for (const match of uniqueMatches) {
      addReference(db, match.topicId, {
        sourceKind: "packet",
        sourceId: row.id,
        projectId: row.projectId,
        label: row.objective,
        href: "/control",
        excerpt: sectionText.slice(0, 280),
        freshness: estimateFreshnessLabel(row.createdAt),
        confidence: 0.78,
        metadata: {
          runId: row.runId,
          workflowKey: row.workflowKey,
        },
      });
    }
  }
};

const ingestMemoryReferences = (db: Database.Database, catalog: TopicCatalogEntry[]): void => {
  const rows = db
    .prepare(
      `
      SELECT
        id,
        project_id AS projectId,
        summary,
        changes_json AS changesJson,
        risks_json AS risksJson,
        open_questions_json AS openQuestionsJson,
        created_at AS createdAt
      FROM memory_updates
      ORDER BY created_at DESC
      LIMIT 100
    `,
    )
    .all() as MemorySourceRow[];

  for (const row of rows) {
    const body = [
      row.summary,
      ...parseJsonArray<string[]>(row.changesJson, []),
      ...parseJsonArray<string[]>(row.risksJson, []),
      ...parseJsonArray<string[]>(row.openQuestionsJson, []),
    ].join(" ");
    const matches = [
      ...(row.projectId ? [{ topicId: catalog.find((entry) => entry.slug === `project-${row.projectId}`)?.id, score: 24 }] : []),
      ...findMatchingTopics(catalog, body, 5),
    ].filter((match): match is { topicId: string; score: number } => Boolean(match.topicId));

    const uniqueMatches = matches.filter(
      (match, index, items) => items.findIndex((candidate) => candidate.topicId === match.topicId) === index,
    );

    for (const match of uniqueMatches) {
      addReference(db, match.topicId, {
        sourceKind: "memory",
        sourceId: row.id,
        projectId: row.projectId,
        label: row.summary,
        href: "/control",
        excerpt: body.slice(0, 280),
        freshness: estimateFreshnessLabel(row.createdAt),
        confidence: 0.84,
      });
    }
  }
};

const updateTopicFreshness = (db: Database.Database): void => {
  const rows = db
    .prepare(
      `
      SELECT
        t.id AS topicId,
        AVG(r.confidence) AS avgConfidence,
        COUNT(r.id) AS referenceCount
      FROM knowledge_topics t
      LEFT JOIN knowledge_references r ON r.topic_id = t.id
      GROUP BY t.id
    `,
    )
    .all() as Array<{ topicId: string; avgConfidence: number | null; referenceCount: number }>;

  const update = db.prepare(`
    UPDATE knowledge_topics
    SET confidence = ?,
        updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
    WHERE id = ?
  `);

  for (const row of rows) {
    update.run(row.referenceCount > 0 ? Number(row.avgConfidence ?? 0.5).toFixed(2) : 0.5, row.topicId);
  }
};

const addDerivedMarkers = (db: Database.Database): void => {
  const topics = db.prepare("SELECT id, slug, title FROM knowledge_topics").all() as Array<{ id: string; slug: string; title: string }>;

  for (const topic of topics) {
    const refs = db
      .prepare(
        `
        SELECT source_kind AS sourceKind, label, freshness, metadata_json AS metadataJson
        FROM knowledge_references
        WHERE topic_id = ?
      `,
      )
      .all(topic.id) as Array<{ sourceKind: string; label: string; freshness: string; metadataJson: string }>;

    const hasFailure = refs.some((ref) => {
      const metadata = parseJsonArray<Record<string, string>>(ref.metadataJson, {});
      return metadata.status === "failed" || metadata.status === "canceled";
    });
    const hasSuccess = refs.some((ref) => {
      const metadata = parseJsonArray<Record<string, string>>(ref.metadataJson, {});
      return metadata.status === "completed";
    });
    if (hasFailure && hasSuccess) {
      addMarker(db, topic.id, {
        kind: "contradiction",
        severity: "warning",
        summary: `${topic.title} has both failure and completion evidence in recent runs.`,
        sourceRef: topic.slug,
      });
    }

    const hasOldWiki = refs.some((ref) => ref.sourceKind === "wiki" && ref.freshness.includes("Stale"));
    const hasFreshOperational = refs.some(
      (ref) => (ref.sourceKind === "run" || ref.sourceKind === "memory") && ref.freshness.includes("last day"),
    );
    if (hasOldWiki && hasFreshOperational) {
      addMarker(db, topic.id, {
        kind: "drift",
        severity: "info",
        summary: `${topic.title} has fresh operational evidence that may have outpaced the curated wiki page.`,
        sourceRef: topic.slug,
      });
    }
  }
};

export const refreshTopicGraph = (db: Database.Database, force = false): void => {
  ensureControlPlaneSchema(db);

  const state = db
    .prepare("SELECT last_refreshed_at AS lastRefreshedAt FROM knowledge_graph_state WHERE graph_key = ? LIMIT 1")
    .get(GRAPH_KEY) as { lastRefreshedAt: string } | undefined;

  if (!force && state?.lastRefreshedAt) {
    const age = Date.now() - new Date(state.lastRefreshedAt).getTime();
    if (!Number.isNaN(age) && age < GRAPH_TTL_MS) {
      return;
    }
  }

  const catalog = createTopicCatalog(db);

  const runRefresh = db.transaction(() => {
    db.exec(`
      DELETE FROM knowledge_markers;
      DELETE FROM knowledge_relationships;
      DELETE FROM knowledge_references;
      DELETE FROM knowledge_topics;
    `);

    upsertCatalog(db, catalog);
    ingestProjectReferences(db, catalog);
    ingestWikiReferences(db, catalog);
    ingestRunReferences(db, catalog);
    ingestPacketReferences(db, catalog);
    ingestMemoryReferences(db, catalog);
    updateTopicFreshness(db);
    addDerivedMarkers(db);

    db.prepare(`
      INSERT INTO knowledge_graph_state (graph_key, last_refreshed_at, note)
      VALUES (?, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), ?)
      ON CONFLICT(graph_key) DO UPDATE SET
        last_refreshed_at = excluded.last_refreshed_at,
        note = excluded.note
    `).run(GRAPH_KEY, "Refreshed from wiki, projects, runs, packets, and memory updates.");
  });

  runRefresh();
};

export const searchTopicGraph = (
  db: Database.Database,
  options: TopicGraphSearchOptions,
): TopicGraphMatch[] => {
  refreshTopicGraph(db);

  const rows = db
    .prepare(
      `
      SELECT
        t.id,
        t.slug,
        t.title,
        t.kind,
        t.summary,
        t.confidence,
        t.freshness,
        t.canonical_href AS canonicalHref,
        t.tags_json AS tagsJson,
        COUNT(DISTINCT r.id) AS referenceCount,
        COUNT(DISTINCT m.id) AS markerCount
      FROM knowledge_topics t
      LEFT JOIN knowledge_references r ON r.topic_id = t.id
      LEFT JOIN knowledge_markers m ON m.topic_id = t.id
      GROUP BY t.id
    `,
    )
    .all() as TopicRow[];

  const queryTokens = new Set(tokenize(options.query ?? ""));

  return rows
    .map((row) => {
      const tags = parseJsonArray<string[]>(row.tagsJson, []);
      const projectBoost = options.projectId && row.slug === `project-${options.projectId}` ? 28 : 0;
      const overlap = [...queryTokens].filter((token) =>
        tokenize([row.title, row.summary, ...tags].join(" ")).includes(token),
      ).length;
      const score = projectBoost + overlap * 12 + freshnessScore(row.freshness) * 10 + row.confidence * 15 + row.referenceCount;
      const why = projectBoost > 0 ? "Direct project topic match." : overlap > 0 ? `Matched ${overlap} query terms.` : "Retained by graph confidence and freshness.";

      return {
        topic: {
          id: row.id,
          slug: row.slug,
          title: row.title,
          kind: row.kind,
          summary: row.summary,
          confidence: row.confidence,
          freshness: row.freshness,
          tags,
          canonicalHref: row.canonicalHref,
          referenceCount: row.referenceCount,
          markerCount: row.markerCount,
        },
        score,
        why,
      } satisfies TopicGraphMatch;
    })
    .filter((match) => match.score > 0 || !options.query)
    .sort((left, right) => right.score - left.score)
    .slice(0, options.limit ?? 8);
};

export const getTopicReferences = (db: Database.Database, slug: string, limit = 8): TopicGraphReference[] => {
  refreshTopicGraph(db);

  const rows = db
    .prepare(
      `
      SELECT
        r.source_kind AS sourceKind,
        r.source_id AS sourceId,
        r.label,
        r.href,
        r.excerpt,
        r.freshness,
        r.confidence
      FROM knowledge_references r
      INNER JOIN knowledge_topics t ON t.id = r.topic_id
      WHERE t.slug = ?
      ORDER BY r.confidence DESC, r.created_at DESC
      LIMIT ?
    `,
    )
    .all(slug, limit) as ReferenceRow[];

  return rows.map((row) => ({
    sourceKind: row.sourceKind,
    sourceId: row.sourceId,
    label: row.label,
    href: row.href,
    excerpt: row.excerpt,
    freshness: row.freshness,
    confidence: row.confidence,
  }));
};

export const getTopicMarkers = (db: Database.Database, slug: string, limit = 6): TopicGraphMarker[] => {
  refreshTopicGraph(db);

  const rows = db
    .prepare(
      `
      SELECT
        m.marker_kind AS markerKind,
        m.severity,
        m.summary,
        m.source_ref AS sourceRef
      FROM knowledge_markers m
      INNER JOIN knowledge_topics t ON t.id = m.topic_id
      WHERE t.slug = ?
      ORDER BY m.created_at DESC
      LIMIT ?
    `,
    )
    .all(slug, limit) as MarkerRow[];

  return rows.map((row) => ({
    kind: row.markerKind,
    severity: row.severity,
    summary: row.summary,
    sourceRef: row.sourceRef,
  }));
};

export const getTopicRelationships = (db: Database.Database, slug: string, limit = 10): TopicGraphRelationship[] => {
  refreshTopicGraph(db);

  const rows = db
    .prepare(
      `
      SELECT
        r.relation,
        f.slug AS fromSlug,
        t.slug AS toSlug,
        f.title AS fromTitle,
        t.title AS toTitle,
        r.weight
      FROM knowledge_relationships r
      INNER JOIN knowledge_topics f ON f.id = r.from_topic_id
      INNER JOIN knowledge_topics t ON t.id = r.to_topic_id
      WHERE f.slug = ?
      ORDER BY r.weight DESC, r.created_at DESC
      LIMIT ?
    `,
    )
    .all(slug, limit) as RelationshipRow[];

  return rows.map((row) => ({
    relation: row.relation,
    fromSlug: row.fromSlug,
    toSlug: row.toSlug,
    fromTitle: row.fromTitle,
    toTitle: row.toTitle,
    weight: row.weight,
  }));
};

export const listImprovementWritebacks = (
  db: Database.Database,
  options: { projectId?: string | null; limit?: number } = {},
): ImprovementWriteback[] => {
  ensureControlPlaneSchema(db);

  const rows = db
    .prepare(
      `
      SELECT
        id,
        run_id AS runId,
        project_id AS projectId,
        layer_type AS layerType,
        layer_key AS layerKey,
        title,
        summary,
        evidence_json AS evidenceJson,
        status,
        requires_approval AS requiresApproval,
        approval_reason AS approvalReason,
        token_regressive AS tokenRegressive,
        created_at AS createdAt
      FROM improvement_writebacks
      WHERE (? IS NULL OR project_id = ?)
      ORDER BY created_at DESC
      LIMIT ?
    `,
    )
    .all(options.projectId ?? null, options.projectId ?? null, options.limit ?? 8) as Array<{
      id: string;
      runId: string | null;
      projectId: string | null;
      layerType: ImprovementWriteback["layerType"];
      layerKey: string;
      title: string;
      summary: string;
      evidenceJson: string;
      status: ImprovementWriteback["status"];
      requiresApproval: number;
      approvalReason: string | null;
      tokenRegressive: number;
      createdAt: string;
    }>;

  return rows.map((row) => ({
    id: row.id,
    runId: row.runId,
    projectId: row.projectId,
    layerType: row.layerType,
    layerKey: row.layerKey,
    title: row.title,
    summary: row.summary,
    evidence: parseJsonArray<string[]>(row.evidenceJson, []),
    status: row.status,
    requiresApproval: Boolean(row.requiresApproval),
    approvalReason: row.approvalReason,
    tokenRegressive: Boolean(row.tokenRegressive),
    createdAt: row.createdAt,
  }));
};

export const buildExpansionTrace = (source: string, reason: string, freshness: string, confidence: number): ContextTrace => ({
  source,
  reason,
  freshness,
  confidence,
});
