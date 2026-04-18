import type Database from "better-sqlite3";

import type { GroundedAnswer, GroundedCitation } from "@/lib/control-plane";
import { getProjectDossier, listKnowledgePages } from "@/server/aios/knowledge";
import { listRecentChanges } from "@/server/aios/changes";

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
];

export const answerGroundedQuestion = (
  db: Database.Database,
  input: { question: string; projectId?: string | null },
): GroundedAnswer => {
  const intent = classifyIntent(input.question);
  const projectId = input.projectId ?? null;
  const dossier = projectId ? getProjectDossier(db, projectId) : null;
  const recentChanges = listRecentChanges(db, { projectId: projectId ?? undefined, limit: 5 });
  const decisionPages = listKnowledgePages(db).filter((page) => page.kind === "decision").slice(0, 3);

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
      retrievalTrace: recentChanges.map((change) => ({
        source: change.kind,
        reason: `Loaded ${change.kind} signal for recent changes.`,
        freshness: change.timestamp,
        confidence: change.confidence,
      })),
    };
  }

  if (intent === "project_state" && dossier && projectId) {
    const memorySection = dossier.sections.find((section) => section.title === "Durable Memory");
    return {
      question: input.question,
      intent,
      answer: `${dossier.title} is ${dossier.status} with freshness "${dossier.freshness}". The strongest durable state signal is: ${memorySection?.body ?? dossier.summary}`,
      facts: dossier.sections.flatMap((section) => section.items).slice(0, 6),
      inferences: [
        dossier.status === "warning"
          ? "Open bugs or weak memory signals are making this project operationally noisy."
          : "The project has enough recent state to support task-scoped delegation.",
      ],
      recommendations: [
        "Use the project dossier or control plane packet generator before delegating implementation work.",
      ],
      assumptions: [],
      citations: makeProjectCitations(projectId, dossier.title, recentChanges),
      retrievalTrace: [
        {
          source: "project-dossier",
          reason: `Loaded durable project state for ${dossier.title}.`,
          freshness: dossier.freshness,
          confidence: dossier.confidence,
        },
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
        ...likelyFiles.slice(0, 4).map((filePath) => `Likely file: ${filePath}`),
      ],
      inferences: [
        "Without a task-specific packet, the agent would receive too much low-signal operational history.",
      ],
      recommendations: [
        "Generate a packet from the Control Plane page with the exact task objective before delegation.",
      ],
      assumptions: [],
      citations: makeProjectCitations(projectId, dossier.title, recentChanges),
      retrievalTrace: [
        {
          source: "project-dossier",
          reason: "Loaded project dossier for briefing context.",
          freshness: dossier.freshness,
          confidence: dossier.confidence,
        },
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
    ],
    inferences: [
      "The main product risk is still architectural drift between documented intent and shipped surfaces.",
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
      {
        source: "knowledge-index",
        reason: "Loaded system-level pages and current control-plane primitives.",
        freshness: "Live from local app state",
        confidence: 0.78,
      },
    ],
  };
};
