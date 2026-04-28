import type Database from "better-sqlite3";

import type { GroundedAnswer, GroundedCitation } from "@/lib/control-plane";
import { getCtsContext } from "@/server/aios/cts";
import { getProjectDossier, listKnowledgePages } from "@/server/aios/knowledge";
import { listRecentChanges } from "@/server/aios/changes";
import { getTopicMarkers, getTopicReferences, searchTopicGraph } from "@/server/aios/topic-graph";

const tableExists = (db: Database.Database, name: string): boolean => {
  const row = db
    .prepare("SELECT 1 FROM sqlite_master WHERE type='table' AND name = ? LIMIT 1")
    .get(name) as { "1": number } | undefined;
  return row !== undefined;
};

const countRows = (db: Database.Database, table: string): number => {
  if (!tableExists(db, table)) {
    return 0;
  }
  const row = db.prepare(`SELECT COUNT(*) AS count FROM ${table}`).get() as { count: number };
  return Number(row.count) || 0;
};

const isCapabilityQuestion = (question: string): boolean => {
  const lower = question.toLowerCase();
  return (
    (lower.includes("why") || lower.includes("explain") || lower.includes("audit")) &&
    (
      lower.includes("capability") ||
      lower.includes("status") ||
      lower.includes("health") ||
      lower.includes("metric") ||
      lower.includes("rtk") ||
      lower.includes("automation") ||
      lower.includes("prompt library") ||
      lower.includes("knowledge")
    )
  );
};

const classifyIntent = (
  question: string,
): GroundedAnswer["intent"] => {
  const lower = question.toLowerCase();

  if (lower.includes("what changed")) {
    return "what_changed";
  }

  if (lower.includes("why") && (lower.includes("decision") || lower.includes("decid"))) {
    return "decision_why";
  }

  if (
    lower.includes("agent know") ||
    lower.includes("before doing this task") ||
    lower.includes("briefing")
  ) {
    return "agent_brief";
  }

  if (lower.includes("state of") || lower.includes("status of") || lower.includes("current state")) {
    return "project_state";
  }

  return "system_state";
};

const makeProjectCitations = (
  projectId: string,
  projectTitle: string,
  recentChanges: ReturnType<typeof listRecentChanges>,
  includeCts = false,
): GroundedCitation[] => [
  {
    label: `${projectTitle} dossier`,
    href: `/projects/${projectId}`,
    excerpt: `Project dossier for ${projectTitle}.`,
  },
  ...recentChanges.slice(0, 3).map((change) => ({
    label: change.title,
    href: change.href ?? "/knowledge",
    excerpt: change.summary,
  })),
  ...(includeCts
    ? [
        {
          label: "Code Topology Service",
          href: "/knowledge/system-cts",
          excerpt: "Structural code context used to ground likely files and blast-radius signals.",
        } satisfies GroundedCitation,
      ]
    : []),
];

const loadProjectRepoPath = (db: Database.Database, projectId: string | null): string | null => {
  if (!projectId) {
    return null;
  }

  const row = db
    .prepare("SELECT repo_path AS repoPath FROM projects WHERE id = ? LIMIT 1")
    .get(projectId) as { repoPath: string } | undefined;

  return row?.repoPath ?? null;
};

const answerCapabilityQuestion = (db: Database.Database, question: string): GroundedAnswer => {
  const projectCount = countRows(db, "projects");
  const healthSnapshotCount = countRows(db, "standards_health_snapshots");
  const rtkEventCount = countRows(db, "rtk_compression_events");
  const promptLinkCount = countRows(db, "prompt_library_links");
  const knowledgeTopicCount = countRows(db, "knowledge_topics");
  const knowledgeReferenceCount = countRows(db, "knowledge_references");

  const missingHealth = projectCount > 0 ? Math.max(projectCount - healthSnapshotCount, 0) : 0;
  const promptLibraryState = tableExists(db, "prompt_library_links")
    ? promptLinkCount > 0
      ? `${promptLinkCount} body-hash-backed template(s)`
      : "wired but empty"
    : "missing prompt_library_links";
  const knowledgeState =
    knowledgeTopicCount > 0
      ? `${knowledgeTopicCount} topic(s), ${knowledgeReferenceCount} reference(s)`
      : "no indexed topics";
  const rtkState = rtkEventCount > 0 ? `${rtkEventCount} compression event(s)` : "no eligible RTK telemetry events";

  return {
    question,
    intent: "system_state",
    answer:
      "AIOS capability truth is now represented as source-backed signals. The strongest current gaps are missing project health snapshots, seeded automation health, prompt-library visibility evidence, and knowledge source-reference coverage.",
    facts: [
      `Projects: ${projectCount} project(s), ${healthSnapshotCount} standards-health snapshot row(s), ${missingHealth} project(s) without a health snapshot.`,
      `RTK: ${rtkState}.`,
      "Automations: schedules are readable, but health and success-rate values are still seeded rather than durable run history.",
      `Prompt Library: ${promptLibraryState}.`,
      `Knowledge: ${knowledgeState}.`,
    ],
    inferences: [
      missingHealth > 0
        ? "Project health is not yet portfolio-trustworthy because many projects lack standards-health evidence."
        : "Project health has standards-health evidence for all tracked projects.",
      rtkEventCount === 0
        ? "RTK zero values mean no eligible telemetry events, not proven compression failure."
        : "RTK state can be interpreted from persisted compression events.",
      knowledgeTopicCount > 0 && knowledgeReferenceCount === 0
        ? "Knowledge can surface topics, but those topics are not yet sufficiently source-grounded."
        : "Knowledge has at least partial source-reference coverage.",
    ],
    recommendations: [
      "Use `aios capability-audit --json` as the Stage 1 gate before trusting downstream architecture or UI surfaces.",
    ],
    assumptions: [
      "Automation status remains inferred until durable automation run history is implemented.",
    ],
    citations: [
      {
        label: "Projects",
        href: "/projects",
        excerpt: "Project health, unknown coverage, pipeline state, and status signals.",
      },
      {
        label: "Efficiency",
        href: "/costs",
        excerpt: "RTK state and token telemetry.",
      },
      {
        label: "Automations",
        href: "/automations",
        excerpt: "Automation schedules, success rates, and seeded status signals.",
      },
      {
        label: "Prompt Library",
        href: "/prompts",
        excerpt: "Prompt templates visible only when backed by prompt_library_links evidence.",
      },
      {
        label: "Knowledge",
        href: "/knowledge",
        excerpt: "Knowledge topics, references, relationships, and source grounding.",
      },
    ],
    retrievalTrace: [
      {
        source: "capability-audit",
        reason: "Loaded Stage 1 trusted-signal counts for Projects, RTK, Automations, Prompt Library, and Knowledge.",
        freshness: "Live from SQLite at query time",
        confidence: 0.82,
      },
    ],
  };
};

export const answerGroundedQuestion = (
  db: Database.Database,
  input: { question: string; projectId?: string | null },
): GroundedAnswer => {
  const intent = classifyIntent(input.question);
  const projectId = input.projectId ?? null;
  const dossier = projectId ? getProjectDossier(db, projectId) : null;
  const repoPath = loadProjectRepoPath(db, projectId);
  const ctsContext = getCtsContext(repoPath, input.question);
  const recentChanges = listRecentChanges(db, { projectId: projectId ?? undefined, limit: 5 });
  const decisionPages = listKnowledgePages(db).filter((page) => page.kind === "decision").slice(0, 3);
  const topicMatches = searchTopicGraph(db, { projectId, query: input.question, limit: 4 });

  if (isCapabilityQuestion(input.question)) {
    return answerCapabilityQuestion(db, input.question);
  }

  if (intent === "what_changed") {
    return {
      question: input.question,
      intent,
      answer:
        recentChanges.length > 0
          ? `AIOS most recently changed through ${recentChanges[0].title.toLowerCase()}, with ${recentChanges.length} notable change signals available.`
          : "AIOS does not currently have recent change signals recorded in the control plane.",
      facts: recentChanges.map((change) => `${change.title}: ${change.summary}`),
      inferences: [
        "Recent changes are dominated by operational traces, so project memory capture still needs broader adoption.",
        ...(topicMatches.length > 0 ? [`Topic graph linked this question to ${topicMatches[0].topic.title}.`] : []),
      ],
      recommendations: [
        "Use the control plane packet flow before delegation so future runs produce richer change history.",
      ],
      assumptions: recentChanges.length === 0 ? ["No project-specific recent changes were available."] : [],
      citations: recentChanges.map((change) => ({
        label: change.title,
        href: change.href ?? "/control",
        excerpt: change.summary,
      })),
      retrievalTrace: [
        ...topicMatches.map((match) => ({
          source: "topic-graph",
          reason: `Matched topic ${match.topic.title}. ${match.why}`,
          freshness: match.topic.freshness,
          confidence: match.topic.confidence,
        })),
        ...recentChanges.map((change) => ({
          source: change.kind,
          reason: `Loaded ${change.kind} signal for recent changes.`,
          freshness: change.timestamp,
          confidence: change.confidence,
        })),
        ...(ctsContext && ctsContext.index_status === "current"
          ? [
              {
                source: "cts",
                reason: "Loaded CTS context while evaluating recent changes impact.",
                freshness: ctsContext.confidence_note ?? "CTS index current",
                confidence: 0.74,
              },
            ]
          : []),
      ],
    };
  }

  if (intent === "project_state" && dossier && projectId) {
    const memorySection = dossier.sections.find((section) => section.title === "Durable Memory");
    return {
      question: input.question,
      intent,
      answer: `${dossier.title} is ${dossier.status} with freshness "${dossier.freshness}". The strongest durable state signal is: ${memorySection?.body ?? dossier.summary}`,
      facts: [
        ...dossier.sections.flatMap((section) => section.items).slice(0, 6),
        ...topicMatches.flatMap((match) => getTopicReferences(db, match.topic.slug, 1).map((reference) => `${match.topic.title}: ${reference.excerpt}`)),
        ...(ctsContext && ctsContext.index_status === "current"
          ? [
              `CTS architecture: ${ctsContext.architecture_summary ?? "Unavailable"}`,
              ...(ctsContext.directly_relevant_nodes ?? []).slice(0, 3).map((node) => `CTS node: ${node}`),
            ]
          : []),
      ],
      inferences: [
        dossier.status === "warning"
          ? "Open bugs or weak memory signals are making this project operationally noisy."
          : "The project has enough recent state to support task-scoped delegation.",
        ...(topicMatches.length > 0 ? [`Most relevant indexed topic is ${topicMatches[0].topic.title}.`] : []),
        ...(ctsContext && ctsContext.index_status === "current"
          ? ["CTS context suggests the likely implementation surface can be narrowed before delegation."]
          : []),
      ],
      recommendations: [
        "Use the project dossier or control plane packet generator before delegating implementation work.",
      ],
      assumptions: [],
      citations: makeProjectCitations(projectId, dossier.title, recentChanges, Boolean(ctsContext && ctsContext.index_status === "current")),
      retrievalTrace: [
        {
          source: "project-dossier",
          reason: `Loaded durable project state for ${dossier.title}.`,
          freshness: dossier.freshness,
          confidence: dossier.confidence,
        },
        ...topicMatches.map((match) => ({
          source: "topic-graph",
          reason: `Matched topic ${match.topic.title}. ${match.why}`,
          freshness: match.topic.freshness,
          confidence: match.topic.confidence,
        })),
        ...(ctsContext && ctsContext.index_status === "current"
          ? [
              {
                source: "cts",
                reason: "Loaded CTS architecture and relevant node context for the project state answer.",
                freshness: ctsContext.confidence_note ?? "CTS index current",
                confidence: 0.76,
              },
            ]
          : []),
      ],
    };
  }

  if (intent === "decision_why") {
    return {
      question: input.question,
      intent,
      answer:
        decisionPages.length > 0
          ? `The strongest recent architectural decision is ${decisionPages[0].title}, which exists to make AIOS state boundaries and orchestration behavior explicit.`
          : "No decision records are currently available to explain this question.",
      facts: decisionPages.map((page) => `${page.title}: ${page.summary}`),
      inferences: [
        "AIOS is converging on inspectable state separation rather than hidden prompt behavior.",
      ],
      recommendations: [
        "Capture future control-plane changes as ADRs so decision provenance remains queryable.",
      ],
      assumptions: decisionPages.length === 0 ? ["No ADRs were present in the knowledge index."] : [],
      citations: decisionPages.map((page) => ({
        label: page.title,
        href: `/knowledge/${page.slug}`,
        excerpt: page.summary,
      })),
      retrievalTrace: decisionPages.map((page) => ({
        source: "decision-record",
        reason: `Loaded decision record ${page.title}.`,
        freshness: page.freshness,
        confidence: page.confidence,
      })),
    };
  }

  if (intent === "agent_brief" && dossier && projectId) {
    const likelyFiles = dossier.sections.find((section) => section.title === "Likely Files And Surfaces")?.items ?? [];

    return {
      question: input.question,
      intent,
      answer: `An agent working on ${dossier.title} should start from the project dossier, recent change signals, and likely files, then request a control-plane packet for task-specific constraints.`,
      facts: [
        dossier.summary,
        ...topicMatches.slice(0, 2).map((match) => `Topic: ${match.topic.title}`),
        ...likelyFiles.slice(0, 4).map((filePath) => `Likely file: ${filePath}`),
        ...(ctsContext && ctsContext.index_status === "current"
          ? (ctsContext.directly_relevant_nodes ?? []).slice(0, 4).map((node) => `CTS node: ${node}`)
          : []),
      ],
      inferences: [
        "Without a task-specific packet, the agent would receive too much low-signal operational history.",
        ...(topicMatches.length > 0 ? ["Ranked topics indicate which durable context should reach the packet first."] : []),
        ...(ctsContext && ctsContext.index_status === "current"
          ? ["CTS context can further narrow the likely code surface before execution starts."]
          : []),
      ],
      recommendations: [
        "Generate a packet from the Control Plane page with the exact task objective before delegation.",
      ],
      assumptions: [],
      citations: makeProjectCitations(projectId, dossier.title, recentChanges, Boolean(ctsContext && ctsContext.index_status === "current")),
      retrievalTrace: [
        {
          source: "project-dossier",
          reason: "Loaded project dossier for briefing context.",
          freshness: dossier.freshness,
          confidence: dossier.confidence,
        },
        ...topicMatches.map((match) => ({
          source: "topic-graph",
          reason: `Matched topic ${match.topic.title}. ${match.why}`,
          freshness: match.topic.freshness,
          confidence: match.topic.confidence,
        })),
        ...(ctsContext && ctsContext.index_status === "current"
          ? [
              {
                source: "cts",
                reason: "Loaded CTS nodes for agent-brief grounding.",
                freshness: ctsContext.confidence_note ?? "CTS index current",
                confidence: 0.76,
              },
            ]
          : []),
      ],
    };
  }

  return {
    question: input.question,
    intent: "system_state",
    answer:
      "AIOS currently has strong operational telemetry and documented storage boundaries, but it is only now becoming an explicit knowledge and orchestration control plane.",
    facts: [
      "The storage contract separates SQLite, vault, CTS, and staging.",
      "The UI was originally built as an observability dashboard.",
      "Control-plane runs and briefing packets are now tracked separately from durable knowledge.",
      ...topicMatches.slice(0, 2).map((match) => `Matched topic: ${match.topic.title}`),
    ],
    inferences: [
      "The main product risk is still architectural drift between documented intent and shipped surfaces.",
      ...(topicMatches.length > 0 ? ["The indexed topic graph is now a live retrieval substrate for grounded answers."] : []),
    ],
    recommendations: [
      "Prefer the knowledge, query, and control-plane routes over treating runs/prompts as the primary product.",
    ],
    assumptions: projectId ? ["Project-specific signals were not sufficient for a narrower answer."] : [],
    citations: [
      {
        label: "Control Plane",
        href: "/control",
        excerpt: "Inspect routing rationale, recent runs, and packet history.",
      },
      {
        label: "Knowledge Index",
        href: "/knowledge",
        excerpt: "Browse projects, decisions, workflows, agents, and systems.",
      },
    ],
    retrievalTrace: [
      ...topicMatches.map((match) => ({
        source: "topic-graph",
        reason: `Matched topic ${match.topic.title}. ${match.why}`,
        freshness: match.topic.freshness,
        confidence: match.topic.confidence,
      })),
      ...topicMatches.flatMap((match) =>
        getTopicMarkers(db, match.topic.slug, 1).map((marker) => ({
          source: marker.kind,
          reason: marker.summary,
          freshness: match.topic.freshness,
          confidence: 0.66,
        })),
      ),
      {
        source: "knowledge-index",
        reason: "Loaded system-level pages and current control-plane primitives.",
        freshness: "Live from local app state",
        confidence: 0.78,
      },
    ],
  };
};
