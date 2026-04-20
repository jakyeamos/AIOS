import type Database from "better-sqlite3";

import type { TaskiProjectSummary, TopicGraphMarker } from "@/lib/control-plane";
import { listControlPlaneRuns } from "@/server/aios/control-plane";
import { getProjectDossier } from "@/server/aios/knowledge";
import { proposeRunWritebacks } from "@/server/aios/learning";
import { getTopicMarkers, listImprovementWritebacks, searchTopicGraph } from "@/server/aios/topic-graph";

const parseRiskItems = (items: string[]): string[] =>
  items
    .filter((item) => item.startsWith("Risk: ") || item.startsWith("Open question: "))
    .map((item) => item.replace(/^(Risk|Open question):\s*/, ""));

export const getTaskiProjectSummary = (db: Database.Database, projectId: string): TaskiProjectSummary | null => {
  const dossier = getProjectDossier(db, projectId);
  if (!dossier) {
    return null;
  }

  const runs = listControlPlaneRuns(db).filter((run) => run.projectId === projectId).slice(0, 8);
  const completedRuns = runs.filter((run) => run.status === "completed");
  for (const run of completedRuns.slice(0, 3)) {
    proposeRunWritebacks(db, run.id);
  }

  const topTopics = searchTopicGraph(db, { projectId, query: dossier.title, limit: 6 })
    .filter((match) => match.topic.slug !== `project-${projectId}`)
    .map((match) => match.topic)
    .slice(0, 5);

  const learnedPolicies = listImprovementWritebacks(db, { projectId, limit: 6 });
  const durableMemory = dossier.sections.find((section) => section.title === "Durable Memory");
  const blockers = [
    ...parseRiskItems(durableMemory?.items ?? []),
    ...(dossier.status === "warning" ? ["Project remains operationally noisy and should be routed through compact packets."] : []),
  ].slice(0, 5);

  const recentFailures = runs
    .filter((run) => run.status === "failed" || run.status === "canceled")
    .map((run) => `${run.objective}${run.resultSummary ? `: ${run.resultSummary}` : ""}`)
    .slice(0, 3);

  const recentSuccesses = runs
    .filter((run) => run.status === "completed")
    .map((run) => `${run.objective}${run.resultSummary ? `: ${run.resultSummary}` : ""}`)
    .slice(0, 3);

  const driftMarkers: TopicGraphMarker[] = topTopics.flatMap((topic) => getTopicMarkers(db, topic.slug, 2)).slice(0, 4);
  const suggestedNextActions = [
    "Use compact ranked packets before delegation.",
    ...(blockers.length > 0 ? ["Resolve the current blockers before broadening workflow scope."] : ["Promote the strongest recent run learning into approved project policy."]),
    ...(topTopics.length > 0 ? [`Review the top linked topic first: ${topTopics[0].title}.`] : []),
  ];

  return {
    projectId,
    projectTitle: dossier.title,
    status: dossier.status,
    freshness: dossier.freshness,
    overview: dossier.summary,
    topTopics,
    activeRuns: runs,
    blockers,
    recentFailures,
    recentSuccesses,
    learnedPolicies,
    driftMarkers,
    suggestedNextActions,
  };
};
