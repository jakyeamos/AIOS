import type Database from "better-sqlite3";

import type { TaskiProjectSummary, TopicGraphMarker } from "@/lib/control-plane";
import { listControlPlaneRuns } from "@/server/aios/control-plane";
import { getProjectDossier } from "@/server/aios/knowledge";
import { proposeRunWritebacks } from "@/server/aios/learning";
import { listAiosProjectComponentSettings } from "@/server/aios/project-components";
import { getProjectQualityPipeline } from "@/server/aios/quality-pipeline";
import { listConsistencyFindings } from "@/server/aios/runtime";
import { getProjectStandardsHealth } from "@/server/aios/standards-health";
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
  const consistencyFindings = listConsistencyFindings(db, { projectId, limit: 8 }).slice(0, 6);
  const pendingApprovals = learnedPolicies.filter((policy) => policy.requiresApproval).slice(0, 6);
  const standardsHealth = getProjectStandardsHealth(db, projectId);
  const qualityPipeline = getProjectQualityPipeline(db, projectId);
  const aiosComponents = listAiosProjectComponentSettings(db, projectId);
  const suggestedNextActions = [
    "Use compact ranked packets before delegation.",
    ...(qualityPipeline.overallStatus === "error"
      ? ["Complete the missing or failing required quality pipeline gates before broadening project work."]
      : qualityPipeline.overallStatus === "blocked"
        ? [`Unblock the quality pipeline dependency: ${qualityPipeline.blockedReason ?? "missing project access"}.`]
        : []),
    ...(standardsHealth && standardsHealth.backfillTasks.length > 0
      ? [
          `Complete top standards backfill task first: ${standardsHealth.backfillTasks[0].title}.`,
        ]
      : []),
    ...(pendingApprovals.length > 0
      ? ["Review the queued approval proposals before broadening default behavior."]
      : blockers.length > 0
        ? ["Resolve the current blockers before broadening workflow scope."]
        : ["Promote the strongest recent run learning into approved project policy."]),
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
    consistencyFindings,
    pendingApprovals,
    suggestedNextActions,
    standardsHealth,
    qualityPipeline,
    aiosComponents,
  };
};
