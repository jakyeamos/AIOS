import fs from "node:fs";
import path from "node:path";

import type Database from "better-sqlite3";

import type {
  ChangeItem,
  KnowledgePageDetail,
  KnowledgePageKind,
  KnowledgePageSummary,
  KnowledgeReference,
  KnowledgeRelationship,
} from "@/lib/control-plane";
import { agentProfiles, workflowTemplates } from "@/server/aios/catalog";
import { listRecentChanges } from "@/server/aios/changes";
import {
  extractMarkdownTitle,
  extractSection,
  parseSimpleFrontmatter,
  resolveAiosRoot,
  stripFrontmatter,
  summarizeParagraph,
} from "@/server/aios/filesystem";
import { ensureControlPlaneSchema } from "@/server/aios/schema";
import { tableExists } from "@/server/db";

type ProjectRow = {
  id: string;
  name: string;
  repoPath: string;
  status: string;
  lastActiveAt: string | null;
  sessionCount: number;
  openBugs: number;
};

type PatternRow = {
  id: string;
  title: string;
  state: string;
  confidence: number | null;
  body: string | null;
};

type ArtifactRow = {
  path: string | null;
};

type MemoryRow = {
  summary: string;
  changesJson: string;
  risksJson: string;
  openQuestionsJson: string;
  createdAt: string;
};

type DecisionRecord = {
  slug: string;
  title: string;
  status: string;
  date: string;
  summary: string;
  context: string;
  decision: string;
  consequences: string;
  project: string;
  sourcePath: string;
  tags: string[];
};

type SystemRecord = {
  key: string;
  title: string;
  summary: string;
  sourcePath: string;
  relationships: KnowledgeRelationship[];
  sections: Array<{ title: string; items: string[]; body?: string }>;
};

const makeProjectSlug = (id: string): string => `project-${id}`;
const makeWorkflowSlug = (key: string): string => `workflow-${key}`;
const makeAgentSlug = (key: string): string => `agent-${key}`;
const makeSystemSlug = (key: string): string => `system-${key}`;

const freshnessLabel = (isoValue: string | null): string => {
  if (!isoValue) {
    return "No recent activity";
  }

  const now = Date.now();
  const deltaDays = Math.floor((now - new Date(isoValue).getTime()) / 86_400_000);

  if (deltaDays <= 1) {
    return "Updated in the last day";
  }

  if (deltaDays <= 7) {
    return `Updated ${deltaDays} days ago`;
  }

  return `Stale for ${deltaDays} days`;
};

const parseJsonArray = (raw: string): string[] => {
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (Array.isArray(parsed)) {
      return parsed.filter((value): value is string => typeof value === "string");
    }
  } catch {
    return [];
  }

  return [];
};

const loadDecisions = (): DecisionRecord[] => {
  const root = resolveAiosRoot();
  const adrDir = path.join(root, "docs", "adr");

  if (!fs.existsSync(adrDir)) {
    return [];
  }

  return fs
    .readdirSync(adrDir)
    .filter((name) => name.endsWith(".md"))
    .sort()
    .map((name) => {
      const fullPath = path.join(adrDir, name);
      const content = fs.readFileSync(fullPath, "utf8");
      const frontmatter = parseSimpleFrontmatter(content);
      const stripped = stripFrontmatter(content);

      return {
        slug: name.replace(/\.md$/, ""),
        title: extractMarkdownTitle(content, name.replace(/\.md$/, "")),
        status: frontmatter.status || "proposed",
        date: frontmatter.date || fs.statSync(fullPath).mtime.toISOString(),
        summary: summarizeParagraph(content),
        context: extractSection(stripped, "Context"),
        decision: extractSection(stripped, "Decision"),
        consequences: extractSection(stripped, "Consequences"),
        project: frontmatter.project || "AIOS",
        sourcePath: fullPath,
        tags: [frontmatter.status || "proposed", frontmatter.project || "AIOS"],
      };
    });
};

const loadSystems = (): SystemRecord[] => {
  const root = resolveAiosRoot();

  return [
    {
      key: "storage",
      title: "Storage Contract",
      summary: "Defines the durable boundary between SQLite, vault, CTS, and staging.",
      sourcePath: path.join(root, "docs", "STORES.md"),
      relationships: [
        {
          label: "Control Plane Architecture",
          href: `/knowledge/${makeSystemSlug("control-plane")}`,
          kind: "system",
          relation: "Constrained by",
        },
      ],
      sections: [
        {
          title: "Why It Matters",
          body: "This is the canonical state-separation contract AIOS already claims to follow.",
          items: [
            "SQLite owns machine-readable operational state.",
            "Vault owns curated human-readable knowledge.",
            "Staging is explicitly non-canonical.",
          ],
        },
      ],
    },
    {
      key: "cts",
      title: "Code Topology Service",
      summary: "Persistent structural context for codebases, with confidence and provenance requirements.",
      sourcePath: path.join(root, "docs", "superpowers", "specs", "2026-04-08-aios-code-topology-service-design.md"),
      relationships: [
        {
          label: "Storage Contract",
          href: `/knowledge/${makeSystemSlug("storage")}`,
          kind: "system",
          relation: "Reads from",
        },
      ],
      sections: [
        {
          title: "Role",
          items: [
            "Reduce rediscovery cost for large codebases.",
            "Provide blast-radius and architecture context.",
            "Never replace direct file reads when confidence is low.",
          ],
        },
      ],
    },
    {
      key: "control-plane",
      title: "AIOS Control Plane",
      summary: "The new orchestration surface that routes tasks, logs packets, and exposes retrieval traces.",
      sourcePath: path.join(root, "docs", "architecture", "2026-04-18-aios-control-plane-audit.md"),
      relationships: [
        {
          label: "Storage Contract",
          href: `/knowledge/${makeSystemSlug("storage")}`,
          kind: "system",
          relation: "Must respect",
        },
        {
          label: "Code Topology Service",
          href: `/knowledge/${makeSystemSlug("cts")}`,
          kind: "system",
          relation: "Can enrich",
        },
      ],
      sections: [
        {
          title: "Responsibilities",
          items: [
            "Select workflows and agent roles explicitly.",
            "Generate reusable task-specific briefing packets.",
            "Log orchestration state separately from durable knowledge.",
          ],
        },
      ],
    },
  ];
};

const listProjectRows = (db: Database.Database): ProjectRow[] => {
  if (!tableExists("projects")) {
    return [];
  }

  const openBugSelect = tableExists("bug_log")
    ? "(SELECT COUNT(*) FROM bug_log b WHERE b.project_id = p.id AND b.status = 'open')"
    : "0";

  return db
    .prepare(
      `
      SELECT
        p.id,
        p.name,
        p.repo_path AS repoPath,
        p.status,
        (SELECT MAX(s.started_at) FROM sessions s WHERE s.project_id = p.id) AS lastActiveAt,
        (SELECT COUNT(*) FROM sessions s WHERE s.project_id = p.id) AS sessionCount,
        ${openBugSelect} AS openBugs
      FROM projects p
      ORDER BY (lastActiveAt IS NULL) ASC, lastActiveAt DESC, p.name ASC
    `,
    )
    .all() as ProjectRow[];
};

const projectRelationships = (): KnowledgeRelationship[] => [
  {
    label: "Implementation Delivery",
    href: `/knowledge/${makeWorkflowSlug("implementation-delivery")}`,
    kind: "workflow",
    relation: "Executed through",
  },
  {
    label: "Knowledge OS Evolution",
    href: `/knowledge/${makeWorkflowSlug("knowledge-os-evolution")}`,
    kind: "workflow",
    relation: "Can use",
  },
  {
    label: "Implementation Lead",
    href: `/knowledge/${makeAgentSlug("implementation-lead")}`,
    kind: "agent",
    relation: "Usually delegated to",
  },
];

const agentBacklinks = (agentKey: string): KnowledgeRelationship[] =>
  workflowTemplates
    .filter((workflow) => workflow.key !== "failure-recovery" || agentKey === "debug-surgeon")
    .slice(0, 3)
    .map((workflow) => ({
      label: workflow.name,
      href: `/knowledge/${makeWorkflowSlug(workflow.key)}`,
      kind: "workflow" as const,
      relation: "Supports",
    }));

const workflowRelationships = (workflowKey: string): KnowledgeRelationship[] => {
  const preferredAgent =
    workflowKey === "failure-recovery"
      ? "debug-surgeon"
      : workflowKey === "knowledge-os-evolution"
        ? "principal-auditor"
        : "implementation-lead";

  return [
    {
      label: agentProfiles.find((profile) => profile.key === preferredAgent)?.name ?? "Implementation Lead",
      href: `/knowledge/${makeAgentSlug(preferredAgent)}`,
      kind: "agent",
      relation: "Primary owner",
    },
    {
      label: "AIOS Control Plane",
      href: `/knowledge/${makeSystemSlug("control-plane")}`,
      kind: "system",
      relation: "Managed by",
    },
  ];
};

export const listKnowledgePages = (db: Database.Database): KnowledgePageSummary[] => {
  const projectPages = listProjectRows(db).map((project) => {
    const status: KnowledgePageSummary["status"] =
      project.openBugs > 0 ? "warning" : project.status === "active" ? "healthy" : "unknown";

    return {
      slug: makeProjectSlug(project.id),
      title: project.name,
      kind: "project",
      summary: `${project.sessionCount} sessions, ${project.openBugs} open bugs, repo at ${project.repoPath}.`,
      status,
      freshness: freshnessLabel(project.lastActiveAt),
      confidence: project.openBugs > 0 ? 0.72 : 0.88,
      tags: ["project", project.status],
    } satisfies KnowledgePageSummary;
  });

  const decisionPages = loadDecisions().map((decision) => ({
    slug: decision.slug,
    title: decision.title,
    kind: "decision",
    summary: decision.summary,
    status: decision.status === "accepted" ? "healthy" : "warning",
    freshness: freshnessLabel(decision.date),
    confidence: 0.94,
    tags: decision.tags,
  } satisfies KnowledgePageSummary));

  const workflowPages = workflowTemplates.map((workflow) => ({
    slug: makeWorkflowSlug(workflow.key),
    title: workflow.name,
    kind: "workflow",
    summary: workflow.summary,
    status: "healthy",
    freshness: "Template",
    confidence: 0.76,
    tags: ["workflow", "control-plane"],
  } satisfies KnowledgePageSummary));

  const agentPages = agentProfiles.map((agent) => ({
    slug: makeAgentSlug(agent.key),
    title: agent.name,
    kind: "agent",
    summary: agent.summary,
    status: "healthy",
    freshness: "Registry entry",
    confidence: 0.7,
    tags: ["agent", "delegation"],
  } satisfies KnowledgePageSummary));

  const systemPages = loadSystems().map((system) => ({
    slug: makeSystemSlug(system.key),
    title: system.title,
    kind: "system",
    summary: system.summary,
    status: "healthy",
    freshness: "Reference document",
    confidence: 0.92,
    tags: ["system"],
  } satisfies KnowledgePageSummary));

  return [...projectPages, ...decisionPages, ...workflowPages, ...agentPages, ...systemPages].sort((left, right) =>
    left.title.localeCompare(right.title),
  );
};

const loadProjectPatterns = (db: Database.Database, projectId: string): PatternRow[] => {
  if (!tableExists("patterns")) {
    return [];
  }

  return db
    .prepare(
      `
      SELECT id, title, state, confidence, body
      FROM patterns
      WHERE project_id = ?
      ORDER BY confidence DESC, created_at DESC
      LIMIT 6
    `,
    )
    .all(projectId) as PatternRow[];
};

const loadLikelyFiles = (db: Database.Database, projectId: string): string[] => {
  if (!tableExists("artifacts") || !tableExists("sessions")) {
    return [];
  }

  const rows = db
    .prepare(
      `
      SELECT a.path
      FROM artifacts a
      INNER JOIN sessions s ON s.id = a.session_id
      WHERE s.project_id = ?
        AND a.path IS NOT NULL
      ORDER BY a.created_at DESC
      LIMIT 8
    `,
    )
    .all(projectId) as ArtifactRow[];

  const unique = new Set<string>();

  for (const row of rows) {
    if (row.path) {
      unique.add(row.path);
    }
  }

  return Array.from(unique).slice(0, 6);
};

const loadLatestMemory = (db: Database.Database, projectId: string): MemoryRow | null => {
  ensureControlPlaneSchema(db);
  const row = db
    .prepare(
      `
      SELECT
        summary,
        changes_json AS changesJson,
        risks_json AS risksJson,
        open_questions_json AS openQuestionsJson,
        created_at AS createdAt
      FROM memory_updates
      WHERE project_id = ?
      ORDER BY created_at DESC
      LIMIT 1
    `,
    )
    .get(projectId) as MemoryRow | undefined;

  return row ?? null;
};

const loadProject = (db: Database.Database, projectId: string): ProjectRow | null => {
  return listProjectRows(db).find((project) => project.id === projectId) ?? null;
};

const buildProjectDetail = (db: Database.Database, projectId: string): KnowledgePageDetail | null => {
  const project = loadProject(db, projectId);
  if (!project) {
    return null;
  }

  const patterns = loadProjectPatterns(db, projectId);
  const likelyFiles = loadLikelyFiles(db, projectId);
  const latestMemory = loadLatestMemory(db, projectId);
  const projectDecisions = loadDecisions().filter((decision) => decision.project.toLowerCase() === project.name.toLowerCase());
  const recentChanges = listRecentChanges(db, { projectId, limit: 6 });
  const relationships = projectRelationships();

  const sections = [
    {
      title: "Status",
      body: `${project.name} is ${project.status} with ${project.sessionCount} sessions recorded.`,
      items: [
        `Open bugs: ${project.openBugs}`,
        `Last active: ${project.lastActiveAt ?? "unknown"}`,
        `Repo path: ${project.repoPath}`,
      ],
    },
    {
      title: "Durable Memory",
      body: latestMemory?.summary ?? "No control-plane memory update has been captured yet.",
      items: latestMemory
        ? [
            ...parseJsonArray(latestMemory.changesJson).map((item) => `Change: ${item}`),
            ...parseJsonArray(latestMemory.risksJson).map((item) => `Risk: ${item}`),
            ...parseJsonArray(latestMemory.openQuestionsJson).map((item) => `Open question: ${item}`),
          ]
        : ["Post-run memory updates will appear here after executions close."],
    },
    {
      title: "Related Rules And Signals",
      items:
        patterns.length > 0
          ? patterns.map(
              (pattern) =>
                `${pattern.title} (${pattern.state}, ${(pattern.confidence ?? 0.5).toFixed(2)} confidence)`,
            )
          : ["No project-linked rules or hypotheses are currently attached."],
    },
    {
      title: "Likely Files And Surfaces",
      items: likelyFiles.length > 0 ? likelyFiles : ["No recent artifact paths were captured for this project."],
    },
    {
      title: "Decisions",
      items:
        projectDecisions.length > 0
          ? projectDecisions.map((decision) => `${decision.title} (${decision.status})`)
          : ["No ADRs are currently linked to this project."],
    },
  ];

  const references: KnowledgeReference[] = [
    {
      label: "Project dossier route",
      href: `/projects/${project.id}`,
      detail: "Project-specific knowledge view inside AIOS.",
    },
  ];

  if (projectDecisions.length > 0) {
    references.push(
      ...projectDecisions.map((decision) => ({
        label: decision.title,
        href: `/knowledge/${decision.slug}`,
        detail: decision.summary,
      })),
    );
  }

  return {
    slug: makeProjectSlug(project.id),
    title: project.name,
    kind: "project",
    summary: `${project.name} is represented as a dossier with operational history, rules, decisions, and control-plane context.`,
    status: project.openBugs > 0 ? "warning" : "healthy",
    freshness: freshnessLabel(project.lastActiveAt),
    confidence: project.openBugs > 0 ? 0.72 : 0.88,
    tags: ["project", project.status],
    references,
    relationships,
    backlinks: [
      {
        label: "AIOS Control Plane",
        href: `/knowledge/${makeSystemSlug("control-plane")}`,
        kind: "system",
        relation: "Managed by",
      },
    ],
    sections,
    recentChanges,
  };
};

const buildDecisionDetail = (db: Database.Database, slug: string): KnowledgePageDetail | null => {
  const decision = loadDecisions().find((entry) => entry.slug === slug);
  if (!decision) {
    return null;
  }

  const relationships: KnowledgeRelationship[] = [
    {
      label: decision.project,
      href:
        decision.project === "AIOS"
          ? `/projects/${listProjectRows(db).find((project) => project.name === "AIOS")?.id ?? ""}`
          : "#",
      kind: "project" as const,
      relation: "Applies to",
    },
    {
      label: "AIOS Control Plane",
      href: `/knowledge/${makeSystemSlug("control-plane")}`,
      kind: "system" as const,
      relation: "Shapes",
    },
  ].filter((relationship) => relationship.href !== "#" && relationship.href !== "/projects/");

  return {
    slug: decision.slug,
    title: decision.title,
    kind: "decision",
    summary: decision.summary,
    status: decision.status === "accepted" ? "healthy" : "warning",
    freshness: freshnessLabel(decision.date),
    confidence: 0.94,
    tags: decision.tags,
    references: [
      {
        label: path.basename(decision.sourcePath),
        href: `/knowledge/${decision.slug}`,
        detail: decision.sourcePath,
      },
    ],
    relationships,
    backlinks: [],
    sections: [
      { title: "Context", body: decision.context, items: decision.context ? [] : ["No explicit context section."] },
      { title: "Decision", body: decision.decision, items: decision.decision ? [] : ["No explicit decision section."] },
      {
        title: "Consequences",
        body: decision.consequences,
        items: decision.consequences ? [] : ["Consequences have not been documented yet."],
      },
    ],
    recentChanges: listRecentChanges(db, { limit: 4 }).filter((item) => item.kind === "decision"),
  };
};

const buildWorkflowDetail = (db: Database.Database, key: string): KnowledgePageDetail | null => {
  const workflow = workflowTemplates.find((entry) => entry.key === key);
  if (!workflow) {
    return null;
  }

  ensureControlPlaneSchema(db);
  const runCount = db
    .prepare("SELECT COUNT(*) AS count FROM orchestration_runs WHERE workflow_key = ?")
    .get(key) as { count: number };

  return {
    slug: makeWorkflowSlug(key),
    title: workflow.name,
    kind: "workflow",
    summary: workflow.summary,
    status: runCount.count > 0 ? "healthy" : "unknown",
    freshness: runCount.count > 0 ? `${runCount.count} logged planning runs` : "Template not used yet",
    confidence: 0.76,
    tags: ["workflow", "control-plane"],
    references: [],
    relationships: workflowRelationships(key),
    backlinks: [],
    sections: [
      {
        title: "Triggers",
        items: workflow.triggers,
      },
      {
        title: "Deliverables",
        items: workflow.deliverables,
      },
      {
        title: "Validation",
        items: workflow.validation,
      },
    ],
    recentChanges: listRecentChanges(db, { limit: 4 }).filter((item) => item.kind === "packet"),
  };
};

const buildAgentDetail = (db: Database.Database, key: string): KnowledgePageDetail | null => {
  const agent = agentProfiles.find((entry) => entry.key === key);
  if (!agent) {
    return null;
  }

  return {
    slug: makeAgentSlug(key),
    title: agent.name,
    kind: "agent",
    summary: agent.summary,
    status: "healthy",
    freshness: "Static registry entry",
    confidence: 0.7,
    tags: ["agent", "delegation"],
    references: [],
    relationships: agentBacklinks(key),
    backlinks: [],
    sections: [
      {
        title: "Best For",
        items: agent.bestFor,
      },
      {
        title: "Guardrails",
        items: agent.guardrails,
      },
    ],
    recentChanges: listRecentChanges(db, { limit: 4 }),
  };
};

const buildSystemDetail = (db: Database.Database, key: string): KnowledgePageDetail | null => {
  const system = loadSystems().find((entry) => entry.key === key);
  if (!system) {
    return null;
  }

  return {
    slug: makeSystemSlug(key),
    title: system.title,
    kind: "system",
    summary: system.summary,
    status: "healthy",
    freshness: "Reference document",
    confidence: 0.92,
    tags: ["system"],
    references: [
      {
        label: path.basename(system.sourcePath),
        href: `/knowledge/${makeSystemSlug(key)}`,
        detail: system.sourcePath,
      },
    ],
    relationships: system.relationships,
    backlinks: [],
    sections: system.sections,
    recentChanges: listRecentChanges(db, { limit: 5 }),
  };
};

export const getKnowledgePage = (db: Database.Database, slug: string): KnowledgePageDetail | null => {
  if (slug.startsWith("project-")) {
    return buildProjectDetail(db, slug.slice("project-".length));
  }

  if (slug.startsWith("workflow-")) {
    return buildWorkflowDetail(db, slug.slice("workflow-".length));
  }

  if (slug.startsWith("agent-")) {
    return buildAgentDetail(db, slug.slice("agent-".length));
  }

  if (slug.startsWith("system-")) {
    return buildSystemDetail(db, slug.slice("system-".length));
  }

  return buildDecisionDetail(db, slug);
};

export const getProjectDossier = (
  db: Database.Database,
  projectId: string,
): KnowledgePageDetail | null => buildProjectDetail(db, projectId);

export const listKnowledgeKinds = (db: Database.Database): Record<KnowledgePageKind, KnowledgePageSummary[]> => {
  const pages = listKnowledgePages(db);

  return {
    project: pages.filter((page) => page.kind === "project"),
    decision: pages.filter((page) => page.kind === "decision"),
    workflow: pages.filter((page) => page.kind === "workflow"),
    agent: pages.filter((page) => page.kind === "agent"),
    system: pages.filter((page) => page.kind === "system"),
  };
};
