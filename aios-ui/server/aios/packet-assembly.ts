import { randomUUID } from "node:crypto";

import type Database from "better-sqlite3";

import type {
  BriefingPacket,
  ContextTrace,
  OmittedContextItem,
  PacketExpansion,
  PacketExpansionKind,
  PacketSelectionTraceItem,
  PacketSection,
} from "@/lib/control-plane";
import { agentProfiles, findAgentProfile, findWorkflowTemplate, workflowTemplates } from "@/server/aios/catalog";
import { getCtsContext } from "@/server/aios/cts";
import { getProjectDossier } from "@/server/aios/knowledge";
import { ensureControlPlaneSchema } from "@/server/aios/schema";
import {
  buildExpansionTrace,
  getTopicReferences,
  listImprovementWritebacks,
  searchTopicGraph,
} from "@/server/aios/topic-graph";

type RankedCandidate = {
  id: string;
  label: string;
  section: string;
  sourceKind: string;
  sourceHref: string;
  score: number;
  body: string;
  reason: string;
};

const parseJsonArray = <T>(raw: string, fallback: T): T => {
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
};

const estimateTokens = (value: string): number => Math.max(24, Math.ceil(value.split(/\s+/).filter(Boolean).length * 1.35));

const selectWithinBudget = (
  candidates: RankedCandidate[],
  tokenBudget: number,
): { selected: RankedCandidate[]; omitted: OmittedContextItem[] } => {
  const selected: RankedCandidate[] = [];
  const omitted: OmittedContextItem[] = [];
  let usedTokens = 0;

  for (const candidate of candidates.sort((left, right) => right.score - left.score)) {
    const nextCost = estimateTokens(candidate.body);
    if (usedTokens + nextCost <= tokenBudget) {
      selected.push(candidate);
      usedTokens += nextCost;
      continue;
    }

    omitted.push({
      label: candidate.label,
      sourceKind: candidate.sourceKind,
      score: candidate.score,
      reason: `Omitted because the compact packet budget would be exceeded after ${usedTokens} estimated tokens.`,
    });
  }

  return { selected, omitted };
};

const buildMarkdown = (
  objective: string,
  workflowName: string,
  agentName: string,
  sections: PacketSection[],
  policyMode: BriefingPacket["policyMode"],
): string => {
  const body = sections
    .map((section) => {
      const heading = `## ${section.title}`;
      const lead = section.body ? `${section.body}\n\n` : "";
      const items = section.items.map((item) => `- ${item}`).join("\n");
      return `${heading}\n\n${lead}${items}`;
    })
    .join("\n\n");

  return [
    "# Ranked Briefing Packet",
    "",
    `- Objective: ${objective}`,
    `- Workflow: ${workflowName}`,
    `- Agent: ${agentName}`,
    `- Context policy: ${policyMode}`,
    "- Default rule: use this packet first, then request traced targeted expansion only when needed.",
    "",
    body,
  ].join("\n");
};

const loadProjectRepoPath = (db: Database.Database, projectId: string | null): string | null => {
  if (!projectId) {
    return null;
  }

  const row = db
    .prepare("SELECT repo_path AS repoPath FROM projects WHERE id = ? LIMIT 1")
    .get(projectId) as { repoPath: string } | undefined;

  return row?.repoPath ?? null;
};

const loadRecentRuns = (db: Database.Database, projectId: string | null, objective: string): RankedCandidate[] => {
  const tokens = objective.toLowerCase().split(/\W+/).filter((token) => token.length >= 4);
  const rows = db
    .prepare(
      `
      SELECT id, objective, status, workflow_key AS workflowKey, agent_key AS agentKey, result_summary AS resultSummary, created_at AS createdAt
      FROM orchestration_runs
      WHERE (? IS NULL OR project_id = ?)
      ORDER BY created_at DESC
      LIMIT 12
    `,
    )
    .all(projectId, projectId) as Array<{
      id: string;
      objective: string;
      status: string;
      workflowKey: string;
      agentKey: string;
      resultSummary: string | null;
      createdAt: string;
    }>;

  return rows.map((row) => {
    const overlap = tokens.filter((token) => row.objective.toLowerCase().includes(token)).length;
    const score = overlap * 10 + (row.status === "completed" ? 8 : row.status === "failed" ? 9 : 3);
    const section = row.status === "failed" || row.status === "canceled" ? "Recent Related Failures" : "Recent Related Successes";

    return {
      id: row.id,
      label: row.objective,
      section,
      sourceKind: "run",
      sourceHref: "/control",
      score,
      body: `${row.objective} (${row.workflowKey}/${row.agentKey})${row.resultSummary ? `: ${row.resultSummary}` : ""}`,
      reason: overlap > 0 ? `Matched ${overlap} objective terms.` : "Recent run retained for local project continuity.",
    } satisfies RankedCandidate;
  });
};

const loadRecentMemoryCandidates = (db: Database.Database, projectId: string | null): RankedCandidate[] => {
  const rows = db
    .prepare(
      `
      SELECT id, summary, changes_json AS changesJson, risks_json AS risksJson, created_at AS createdAt
      FROM memory_updates
      WHERE (? IS NULL OR project_id = ?)
      ORDER BY created_at DESC
      LIMIT 8
    `,
    )
    .all(projectId, projectId) as Array<{
      id: string;
      summary: string;
      changesJson: string;
      risksJson: string;
      createdAt: string;
    }>;

  return rows.map((row) => ({
    id: row.id,
    label: row.summary,
    section: "Constraints / Stable Truths",
    sourceKind: "memory",
    sourceHref: "/control",
    score: 18,
    body: [
      row.summary,
      ...parseJsonArray<string[]>(row.changesJson, []).slice(0, 2),
      ...parseJsonArray<string[]>(row.risksJson, []).slice(0, 2),
    ].join(" "),
    reason: `Recent memory update from ${row.createdAt}.`,
  }));
};

const loadPolicyCandidates = (db: Database.Database, projectId: string | null, workflowKey: string, agentKey: string): RankedCandidate[] => {
  const workflow = workflowTemplates.find((entry) => entry.key === workflowKey) ?? workflowTemplates[1];
  const agent = agentProfiles.find((entry) => entry.key === agentKey) ?? agentProfiles[1];
  const writebacks = listImprovementWritebacks(db, { projectId, limit: 6 });

  const registryCandidates: RankedCandidate[] = [
    {
      id: `workflow-${workflow.key}`,
      label: workflow.name,
      section: "Instructions / Policies For This Task Type",
      sourceKind: "workflow",
      sourceHref: "/control",
      score: 28,
      body: [`Deliverables: ${workflow.deliverables.join("; ")}`, `Validation: ${workflow.validation.join("; ")}`].join(" "),
      reason: "Workflow template defines durable task-type instruction.",
    },
    {
      id: `agent-${agent.key}`,
      label: agent.name,
      section: "Instructions / Policies For This Task Type",
      sourceKind: "agent",
      sourceHref: "/control",
      score: 24,
      body: agent.guardrails.join(" "),
      reason: "Agent registry guardrails are stable constraints for this role.",
    },
  ];

  const learnedCandidates = writebacks.map((writeback) => ({
    id: writeback.id,
    label: writeback.title,
    section: "Instructions / Policies For This Task Type",
    sourceKind: "writeback",
    sourceHref: "/projects",
    score: writeback.status === "applied" ? 22 : writeback.requiresApproval ? 10 : 18,
    body: writeback.summary,
    reason: writeback.requiresApproval
      ? "Proposed learning retained as a non-default instruction because it still requires approval."
      : "Prior run learning retained as a reusable instruction signal.",
  }));

  return [...registryCandidates, ...learnedCandidates];
};

export const assembleRankedPacket = (
  db: Database.Database,
  input: { objective: string; projectId?: string | null; policyMode?: BriefingPacket["policyMode"]; tokenBudget?: number },
): Omit<BriefingPacket, "id" | "runId" | "createdAt"> & {
  contextTrace: ContextTrace[];
  rationale: string;
  assumptions: string[];
} => {
  ensureControlPlaneSchema(db);

  const policyMode = input.policyMode ?? "compact-ranked";
  const tokenBudget = input.tokenBudget ?? 900;
  const projectId = input.projectId ?? null;
  const dossier = projectId ? getProjectDossier(db, projectId) : null;
  const workflow = findWorkflowTemplate(input.objective);
  const agent = findAgentProfile(input.objective);
  const repoPath = loadProjectRepoPath(db, projectId);
  const ctsContext = getCtsContext(repoPath, input.objective);

  const topicMatches = searchTopicGraph(db, { projectId, query: input.objective, limit: 6 });
  const topicCandidates: RankedCandidate[] = topicMatches.map((match) => ({
    id: match.topic.id,
    label: match.topic.title,
    section: "Top Relevant Topics",
    sourceKind: "topic",
    sourceHref: match.topic.canonicalHref,
    score: Math.round(match.score),
    body: `${match.topic.title}: ${match.topic.summary}`,
    reason: match.why,
  }));
  const runCandidates = loadRecentRuns(db, projectId, input.objective);
  const memoryCandidates = loadRecentMemoryCandidates(db, projectId);
  const policyCandidates = loadPolicyCandidates(db, projectId, workflow.key, agent.key);
  const projectTruthCandidate: RankedCandidate[] = dossier
    ? [
        {
          id: `project-truth-${dossier.slug}`,
          label: `${dossier.title} dossier`,
          section: "Constraints / Stable Truths",
          sourceKind: "project-dossier",
          sourceHref: `/projects/${projectId}`,
          score: 32,
          body: dossier.summary,
          reason: "Direct project truth is always retained near the top of the compact packet.",
        },
      ]
    : [];
  const ctsCandidates: RankedCandidate[] =
    ctsContext && ctsContext.index_status === "current"
      ? [
          {
            id: "cts",
            label: "Code Topology Service",
            section: "Likely Files / Code Topology",
            sourceKind: "cts",
            sourceHref: "/knowledge/system-cts",
            score: 26,
            body: [
              `Architecture: ${ctsContext.architecture_summary ?? "Unavailable"}`,
              `Blast radius: ${ctsContext.estimated_blast_radius ?? 0} files`,
              ...(ctsContext.directly_relevant_nodes ?? []).slice(0, 5).map((node) => `Relevant node: ${node}`),
            ].join(" "),
            reason: "CTS provides compact structural narrowing before code exploration.",
          },
        ]
      : [];

  const allCandidates = [
    ...projectTruthCandidate,
    ...topicCandidates,
    ...memoryCandidates,
    ...runCandidates,
    ...policyCandidates,
    ...ctsCandidates,
  ];

  const { selected, omitted } = selectWithinBudget(allCandidates, tokenBudget);
  const bySection = (section: string): RankedCandidate[] => selected.filter((candidate) => candidate.section === section);
  const likelyFiles = dossier?.sections.find((section) => section.title === "Likely Files And Surfaces")?.items ?? [];
  const expansionHints = omitted
    .slice(0, 4)
    .map((item) => `Ask for more on ${item.sourceKind}: ${item.label}`)
    .concat("Use explore mode only for ambiguous or research-heavy tasks.");

  const sections: PacketSection[] = [
    {
      title: "Objective Summary",
      body: "Default operating mode is compact ranked delivery. Start here before requesting expansion.",
      items: [
        input.objective,
        `Project scope: ${dossier?.title ?? "Unscoped task"}`,
        `Workflow: ${workflow.name}`,
        `Agent: ${agent.name}`,
      ],
    },
    {
      title: "Top Relevant Topics",
      items: bySection("Top Relevant Topics").map((candidate) => candidate.body).slice(0, 4),
    },
    {
      title: "Constraints / Stable Truths",
      items: [...bySection("Constraints / Stable Truths").map((candidate) => candidate.body).slice(0, 4)],
    },
    {
      title: "Recent Related Failures / Successes",
      items: [
        ...bySection("Recent Related Failures").map((candidate) => candidate.body).slice(0, 2),
        ...bySection("Recent Related Successes").map((candidate) => candidate.body).slice(0, 2),
      ],
    },
    {
      title: "Instructions / Policies For This Task Type",
      items: bySection("Instructions / Policies For This Task Type").map((candidate) => candidate.body).slice(0, 4),
    },
    {
      title: "Likely Files / Code Topology",
      items: [
        ...likelyFiles.slice(0, 4),
        ...bySection("Likely Files / Code Topology").map((candidate) => candidate.body),
      ],
    },
    {
      title: "Expansion Hints",
      body: "Targeted expansion is allowed. Open corpus exploration is not the default.",
      items: expansionHints,
    },
  ].map((section) => ({
    ...section,
    items: section.items.length > 0 ? section.items : ["No high-signal context survived the compact packet budget for this section."],
  }));

  const selectionTrace: PacketSelectionTraceItem[] = selected.map((candidate) => ({
    section: candidate.section,
    label: candidate.label,
    sourceKind: candidate.sourceKind,
    sourceHref: candidate.sourceHref,
    score: candidate.score,
    reason: candidate.reason,
  }));

  const contextTrace: ContextTrace[] = [
    {
      source: "packet-policy",
      reason: policyMode === "compact-ranked" ? "Applied hardened compact ranked packet policy." : "Explore mode was explicitly requested.",
      freshness: "Runtime policy",
      confidence: 0.99,
    },
    ...topicMatches.slice(0, 3).map((match) => ({
      source: "topic-graph",
      reason: `Included topic ${match.topic.title}. ${match.why}`,
      freshness: match.topic.freshness,
      confidence: match.topic.confidence,
    })),
    ...(ctsContext && ctsContext.index_status === "current"
      ? [
          {
            source: "cts",
            reason: "Included CTS because structural narrowing beat broad code exploration for this task.",
            freshness: ctsContext.confidence_note ?? "CTS index current",
            confidence: 0.78,
          },
        ]
      : []),
  ];

  return {
    projectId,
    objective: input.objective,
    workflowKey: workflow.key,
    agentKey: agent.key,
    markdown: buildMarkdown(input.objective, workflow.name, agent.name, sections, policyMode),
    sections,
    policyMode,
    tokenBudget,
    routeId: null,
    routeResult: null,
    selectionTrace,
    omittedContext: omitted,
    contextTrace,
    rationale: `Selected ${workflow.name} with ${agent.name} because the objective matched ${topicMatches.length} indexed topics and the compact packet policy favors ranked context over open corpus access.`,
    assumptions: [
      "Broad retrieval happens inside AIOS, not inside the delegated agent by default.",
      "Compact ranked context should be exhausted before expansion is requested.",
      "Every expansion request must be traced so AIOS can learn what extra context was actually useful.",
    ],
  };
};

export const expandPacketContext = (
  db: Database.Database,
  input: {
    packetId: string;
    runId?: string | null;
    projectId?: string | null;
    requestKind: PacketExpansionKind;
    requestTarget: string;
    tokenBudget?: number;
  },
): PacketExpansion => {
  ensureControlPlaneSchema(db);

  const tokenBudget = input.tokenBudget ?? 180;
  const projectId = input.projectId ?? null;
  const references =
    input.requestKind === "topic"
      ? getTopicReferences(db, input.requestTarget, 6)
      : searchTopicGraph(db, { projectId, query: input.requestTarget, limit: 4 }).flatMap((match) =>
          getTopicReferences(db, match.topic.slug, 2),
        );

  const returnedContext = references
    .slice(0, Math.max(1, Math.floor(tokenBudget / 80)))
    .map((reference) => `${reference.label}: ${reference.excerpt}`);

  const trace = references.slice(0, 4).map((reference) =>
    buildExpansionTrace(
      reference.sourceKind,
      `Returned targeted ${input.requestKind} expansion for "${input.requestTarget}".`,
      reference.freshness,
      reference.confidence,
    ),
  );

  const id = `expand-${randomUUID()}`;

  db.prepare(`
    INSERT INTO packet_expansions (
      id,
      run_id,
      packet_id,
      project_id,
      request_kind,
      request_target,
      token_budget,
      status,
      returned_context_json,
      trace_json
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?)
  `).run(
    id,
    input.runId ?? null,
    input.packetId,
    projectId,
    input.requestKind,
    input.requestTarget,
    tokenBudget,
    JSON.stringify(returnedContext),
    JSON.stringify(trace),
  );

  return {
    id,
    runId: input.runId ?? null,
    packetId: input.packetId,
    projectId,
    requestKind: input.requestKind,
    requestTarget: input.requestTarget,
    tokenBudget,
    status: "completed",
    returnedContext,
    trace,
    createdAt: new Date().toISOString(),
  };
};
