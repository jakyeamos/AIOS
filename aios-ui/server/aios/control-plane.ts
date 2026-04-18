import { randomUUID } from "node:crypto";

import type Database from "better-sqlite3";

import type {
  BriefingPacket,
  ContextTrace,
  OrchestrationRun,
  PacketSection,
} from "@/lib/control-plane";
import { agentProfiles, findAgentProfile, findWorkflowTemplate, workflowTemplates } from "@/server/aios/catalog";
import { getProjectDossier, listKnowledgePages } from "@/server/aios/knowledge";
import { listRecentChanges } from "@/server/aios/changes";
import { ensureControlPlaneSchema } from "@/server/aios/schema";

type RunRow = {
  id: string;
  projectId: string | null;
  projectName: string | null;
  objective: string;
  workflowKey: string;
  agentKey: string;
  status: "planned" | "ready" | "executed" | "superseded";
  rationale: string;
  assumptionsJson: string;
  contextTraceJson: string;
  createdAt: string;
  packetId: string | null;
};

type PacketRow = {
  id: string;
  runId: string;
  projectId: string | null;
  objective: string;
  workflowKey: string;
  agentKey: string;
  packetMarkdown: string;
  sectionsJson: string;
  createdAt: string;
};

const parseJsonArray = <T>(raw: string, fallback: T): T => {
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
};

const packetToMarkdown = (
  objective: string,
  workflowName: string,
  agentName: string,
  sections: PacketSection[],
): string => {
  const body = sections
    .map((section) => {
      const heading = `## ${section.title}`;
      const lead = section.body ? `${section.body}\n\n` : "";
      const items = section.items.map((item) => `- ${item}`).join("\n");
      return `${heading}\n\n${lead}${items}`;
    })
    .join("\n\n");

  return `# Briefing Packet\n\n- Objective: ${objective}\n- Workflow: ${workflowName}\n- Agent: ${agentName}\n\n${body}`;
};

const deriveAssumptions = (objective: string, projectName: string): string[] => {
  const assumptions = [
    "Use curated project context instead of raw context dumps.",
    "Escalate when required context is missing or conflicting.",
  ];

  if (projectName === "AIOS") {
    assumptions.push("Preserve the documented storage contract while making AIOS the control plane.");
  }

  if (objective.toLowerCase().includes("refactor")) {
    assumptions.push("Prefer structural simplification over compatibility with weak abstractions.");
  }

  return assumptions;
};

const deriveContextTrace = (
  projectName: string,
  projectSummary: string,
  decisionCount: number,
  recentChangeCount: number,
  likelyFiles: string[],
): ContextTrace[] => [
  {
    source: "project-dossier",
    reason: `Loaded current project state for ${projectName}.`,
    freshness: "Derived from latest sessions and memory updates",
    confidence: 0.88,
  },
  {
    source: "decisions",
    reason: `Included ${decisionCount} decision records to prevent architecture drift.`,
    freshness: "ADR-backed",
    confidence: 0.94,
  },
  {
    source: "recent-changes",
    reason: `Attached ${recentChangeCount} recent change signals to keep context current.`,
    freshness: "Live from operational state",
    confidence: 0.82,
  },
  {
    source: "likely-files",
    reason: likelyFiles.length > 0 ? `Surfaced ${likelyFiles.length} likely files.` : "No artifact-backed likely files were available.",
    freshness: projectSummary,
    confidence: likelyFiles.length > 0 ? 0.7 : 0.45,
  },
];

const buildPacketSections = (input: {
  projectName: string;
  objective: string;
  workflowName: string;
  agentName: string;
  dossierSummary: string;
  decisions: string[];
  likelyFiles: string[];
  recentChanges: string[];
  risks: string[];
}): PacketSection[] => [
  {
    title: "Project Overview",
    body: input.dossierSummary,
    items: [
      `Project: ${input.projectName}`,
      `Workflow: ${input.workflowName}`,
      `Primary owner: ${input.agentName}`,
    ],
  },
  {
    title: "Task Objective",
    body: "Solve the requested task with the minimum context required for reliable execution.",
    items: [
      input.objective,
      "Update durable state after execution instead of leaving context only in the chat transcript.",
    ],
  },
  {
    title: "Why This Matters",
    items: [
      "AIOS should be the canonical source of truth for workflow context and decisions.",
      "Delegated work should receive curated context, not a giant transcript dump.",
      "State boundaries must remain explicit and inspectable.",
    ],
  },
  {
    title: "Relevant Architecture",
    items: [
      "Separate durable knowledge, project memory, live orchestration state, briefing packets, and grounded query logic.",
      "Use server-side repositories for retrieval and routing decisions.",
      "Keep UI routes thin and render inspectable traces.",
    ],
  },
  {
    title: "Prior Decisions",
    items: input.decisions.length > 0 ? input.decisions : ["No formal ADRs were linked to this task."],
  },
  {
    title: "Likely Files Or Surfaces",
    items: input.likelyFiles.length > 0 ? input.likelyFiles : ["No artifact-backed likely files were found."],
  },
  {
    title: "Acceptance Criteria",
    items: [
      "Routing rationale is explicit.",
      "Briefing packet is inspectable and reusable.",
      "Relevant knowledge and memory are exposed in the UI with citations or references.",
      "Changes are durable and queryable after execution.",
    ],
  },
  {
    title: "Validation Requirements",
    items: [
      "Run lint/typecheck for the UI changes.",
      "Verify packet and query flows render without runtime errors.",
      "Confirm schema initialization is idempotent against the live SQLite database.",
    ],
  },
  {
    title: "Non-Goals",
    items: [
      "Do not collapse all state into one catch-all abstraction.",
      "Do not treat staging or drafts as canonical knowledge.",
      "Do not hide retrieval or routing behavior inside opaque prompts.",
    ],
  },
  {
    title: "Known Risks",
    items: input.risks.length > 0 ? input.risks : ["Schema drift and sparse data may leave some sections partially populated."],
  },
  {
    title: "Recent Change Signals",
    items: input.recentChanges.length > 0 ? input.recentChanges : ["No recent change signals were attached."],
  },
  {
    title: "Escalation Conditions",
    items: [
      "Conflicting durable knowledge versus operational state.",
      "No project or packet context can be grounded from AIOS state.",
      "A required source is only available in staging or a stale derived index.",
    ],
  },
];

export const listControlPlaneRuns = (db: Database.Database): OrchestrationRun[] => {
  ensureControlPlaneSchema(db);

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
        r.assumptions_json AS assumptionsJson,
        r.context_trace_json AS contextTraceJson,
        r.created_at AS createdAt,
        r.packet_id AS packetId
      FROM orchestration_runs r
      LEFT JOIN projects p ON p.id = r.project_id
      ORDER BY r.created_at DESC
      LIMIT 20
    `,
    )
    .all() as RunRow[];

  return rows.map((row) => ({
    id: row.id,
    projectId: row.projectId,
    projectName: row.projectName ?? "Unscoped",
    objective: row.objective,
    workflowKey: row.workflowKey,
    agentKey: row.agentKey,
    status: row.status,
    rationale: row.rationale,
    assumptions: parseJsonArray<string[]>(row.assumptionsJson, []),
    contextTrace: parseJsonArray<ContextTrace[]>(row.contextTraceJson, []),
    createdAt: row.createdAt,
    packetId: row.packetId,
  }));
};

const listPacketRows = (db: Database.Database, limit = 12): BriefingPacket[] => {
  ensureControlPlaneSchema(db);
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
        packet_markdown AS packetMarkdown,
        sections_json AS sectionsJson,
        created_at AS createdAt
      FROM briefing_packets
      ORDER BY created_at DESC
      LIMIT ?
    `,
    )
    .all(limit) as PacketRow[];

  return rows.map((row) => ({
    id: row.id,
    runId: row.runId,
    projectId: row.projectId,
    objective: row.objective,
    workflowKey: row.workflowKey,
    agentKey: row.agentKey,
    createdAt: row.createdAt,
    markdown: row.packetMarkdown,
    sections: parseJsonArray<PacketSection[]>(row.sectionsJson, []),
  }));
};

export const getControlPlaneOverview = (db: Database.Database): {
  workflowTemplates: typeof workflowTemplates;
  agentProfiles: typeof agentProfiles;
  runs: OrchestrationRun[];
  packets: BriefingPacket[];
} => ({
  workflowTemplates,
  agentProfiles,
  runs: listControlPlaneRuns(db),
  packets: listPacketRows(db),
});

export const planTask = (
  db: Database.Database,
  input: { objective: string; projectId?: string | null },
): { run: OrchestrationRun; packet: BriefingPacket } => {
  ensureControlPlaneSchema(db);

  const projectId = input.projectId ?? null;
  const dossier = projectId ? getProjectDossier(db, projectId) : null;
  const projectName = dossier?.title ?? "Unscoped AIOS work";
  const workflow = findWorkflowTemplate(input.objective);
  const agent = findAgentProfile(input.objective);
  const decisionPages = listKnowledgePages(db)
    .filter((page) => page.kind === "decision")
    .slice(0, 3)
    .map((page) => page.title);
  const likelyFiles =
    dossier?.sections.find((section) => section.title === "Likely Files And Surfaces")?.items ?? [];
  const recentChanges = (dossier?.recentChanges ?? listRecentChanges(db, { projectId: projectId ?? undefined, limit: 4 }))
    .slice(0, 4)
    .map((change) => change.title);
  const risks =
    dossier?.sections.find((section) => section.title === "Durable Memory")?.items.filter((item) => item.startsWith("Risk: ")) ?? [];
  const assumptions = deriveAssumptions(input.objective, projectName);
  const contextTrace = deriveContextTrace(
    projectName,
    dossier?.freshness ?? "Derived from knowledge index",
    decisionPages.length,
    dossier?.recentChanges.length ?? 0,
    likelyFiles,
  );
  const rationale = `Selected ${workflow.name} with ${agent.name} because the objective emphasizes ${workflow.triggers[0]}.`;
  const packetSections = buildPacketSections({
    projectName,
    objective: input.objective,
    workflowName: workflow.name,
    agentName: agent.name,
    dossierSummary: dossier?.summary ?? "No project dossier was available; use system-level knowledge and recent decisions.",
    decisions: decisionPages,
    likelyFiles,
    recentChanges,
    risks,
  });

  const runId = `run-${randomUUID()}`;
  const packetId = `packet-${randomUUID()}`;
  const markdown = packetToMarkdown(input.objective, workflow.name, agent.name, packetSections);

  db.prepare(
    `
    INSERT INTO orchestration_runs (
      id,
      project_id,
      objective,
      workflow_key,
      agent_key,
      status,
      rationale,
      assumptions_json,
      context_trace_json,
      packet_id
    )
    VALUES (?, ?, ?, ?, ?, 'ready', ?, ?, ?, ?)
  `,
  ).run(
    runId,
    projectId,
    input.objective,
    workflow.key,
    agent.key,
    rationale,
    JSON.stringify(assumptions),
    JSON.stringify(contextTrace),
    packetId,
  );

  db.prepare(
    `
    INSERT INTO briefing_packets (
      id,
      run_id,
      project_id,
      objective,
      workflow_key,
      agent_key,
      packet_markdown,
      sections_json
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `,
  ).run(
    packetId,
    runId,
    projectId,
    input.objective,
    workflow.key,
    agent.key,
    markdown,
    JSON.stringify(packetSections),
  );

  const run = listControlPlaneRuns(db).find((entry) => entry.id === runId);
  const packet = listPacketRows(db).find((entry) => entry.id === packetId);

  if (!run || !packet) {
    throw new Error("Failed to persist orchestration run.");
  }

  return { run, packet };
};
