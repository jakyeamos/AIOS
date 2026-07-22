import type { KnowledgePageDetail } from "@/lib/control-plane";
import type { Project } from "@/lib/types";

export type PortfolioTone = "healthy" | "warning" | "error" | "unknown";

export type PortfolioProofPoint = {
  label: string;
  value: string;
};

export type PortfolioProjectProjection = {
  projectId: string;
  projectName: string;
  statusLabel: string;
  statusTone: PortfolioTone;
  narrative: string;
  progress: string[];
  nextStep: string;
  proofPoints: PortfolioProofPoint[];
  updatedLabel: string;
  confidenceLabel: "High confidence" | "Review required";
  copyText: string;
};

const PRIVATE_MARKERS = [
  "prompt",
  "transcript",
  "credential",
  "secret",
  "api key",
  "access key",
  "repo path",
  "artifact path",
  "source path",
  "control plane",
  "workspace",
  "cwd",
  "writeback",
  "project id",
  "run id",
  "session id",
];

const cleanText = (value: string): string =>
  value
    .replace(/^\s*(?:\[[^\]]+\]\s*)+/, "")
    .replace(/^\s*(?:Session|Decision|Bug|Packet|Memory):\s*/i, "")
    .replace(/\s+/g, " ")
    .trim();

const isPublicSafe = (value: string): boolean => {
  const normalized = value.toLowerCase();
  return (
    !PRIVATE_MARKERS.some((marker) => normalized.includes(marker)) &&
    !/(?:\/Users\/|\/private\/|~\/|`|diff --|-----begin)/i.test(value)
  );
};

const publicText = (value: string, maxLength = 170): string | null => {
  const cleaned = cleanText(value);
  if (cleaned.length < 12 || !isPublicSafe(cleaned)) {
    return null;
  }

  if (cleaned.length <= maxLength) {
    return cleaned;
  }

  return `${cleaned.slice(0, maxLength - 1).trimEnd()}…`;
};

const healthTone = (score: number | null): PortfolioTone => {
  if (score === null) {
    return "unknown";
  }

  if (score >= 80) {
    return "healthy";
  }

  if (score >= 60) {
    return "warning";
  }

  return "error";
};

const formatUpdatedLabel = (timestamp: string | null): string => {
  if (!timestamp) {
    return "Update date unavailable";
  }

  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return "Update date unavailable";
  }

  return `Updated ${new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date)}`;
};

const qualityLabel = (project: Project): string => {
  if (project.pipelineRequired === 0) {
    return "No required checks mapped";
  }

  if (project.pipelineConfiguredRequired === 0) {
    return `0/${project.pipelineRequired} required checks configured`;
  }

  if (
    project.pipelineConfiguredRequired === project.pipelineRequired &&
    project.pipelineStatus === "healthy"
  ) {
    return `${project.pipelineConfiguredRequired}/${project.pipelineRequired} required checks passing`;
  }

  return `${project.pipelineConfiguredRequired}/${project.pipelineRequired} required checks configured`;
};

const progressItems = (
  project: Project,
  dossier: KnowledgePageDetail | null,
): string[] => {
  const recentChanges = (dossier?.recentChanges ?? [])
    .filter((change) => change.kind === "decision" || change.kind === "bug")
    .map((change) => publicText(`${change.title}: ${change.summary}`))
    .filter((change): change is string => change !== null)
    .slice(0, 2);

  if (recentChanges.length > 0) {
    return recentChanges;
  }

  const signals: string[] = [];
  if (project.healthTrend !== null && project.healthTrend !== 0) {
    const direction = project.healthTrend > 0 ? "improved" : "moved";
    signals.push(
      `The health signal ${direction} by ${Math.abs(project.healthTrend / 10).toFixed(1)} points since the prior snapshot.`,
    );
  }

  if (project.openBugs === 0) {
    signals.push("No open bugs are recorded in the latest project view.");
  } else {
    signals.push(`${project.openBugs} open issue${project.openBugs === 1 ? "" : "s"} remain in the latest project view.`);
  }

  if (project.sessionCount > 0) {
    signals.push(`${project.sessionCount} recorded work session${project.sessionCount === 1 ? "" : "s"} are linked to the project.`);
  }

  return signals.slice(0, 3).length > 0 ? signals.slice(0, 3) : ["No publishable milestone has been recorded yet."];
};

const nextStep = (project: Project): string => {
  if (project.status === "archived") {
    return "Keep the project record available as a reference for future work.";
  }

  if (project.pipelineStatus === "error" || project.pipelineStatus === "blocked") {
    return "Resolve the remaining quality-gate gap before the next milestone.";
  }

  if (project.openBugs > 0) {
    return `Close the ${project.openBugs} open issue${project.openBugs === 1 ? "" : "s"} before expanding the next milestone.`;
  }

  if (project.healthScore === null) {
    return "Capture the first health snapshot before making the next progress claim.";
  }

  if (project.criticalDeltaCount > 0) {
    return "Review the flagged quality changes before the next milestone.";
  }

  return "Continue the next verified milestone and capture its proof.";
};

const narrativeFor = (project: Project, tone: PortfolioTone): string => {
  if (project.status === "archived") {
    return `${project.name} is an archived project with a retained record of its work and decisions.`;
  }

  if (tone === "healthy") {
    return `${project.name} is an active project with a strong quality signal and a clear foundation for its next milestone.`;
  }

  if (tone === "warning") {
    return `${project.name} is moving forward, with a focused set of readiness items still to close.`;
  }

  if (tone === "error") {
    return `${project.name} is active but needs focused quality attention before its next milestone.`;
  }

  return `${project.name} is active, while its next quality signal is still being assembled.`;
};

const proofPointsFor = (project: Project): PortfolioProofPoint[] => {
  const healthValue = project.healthScore === null ? "Pending" : `${(project.healthScore / 10).toFixed(1)}/10`;
  const issueValue = project.openBugs === 0 ? "None recorded" : `${project.openBugs} open`;

  return [
    { label: "Health signal", value: healthValue },
    { label: "Quality readiness", value: qualityLabel(project) },
    { label: "Open issues", value: issueValue },
  ];
};

const copyTextFor = (
  projectName: string,
  narrative: string,
  progress: string[],
  proofPoints: PortfolioProofPoint[],
  next: string,
  updatedLabel: string,
): string => {
  const progressBlock = progress.map((item) => `- ${item}`).join("\n");
  const signalBlock = proofPoints.map((point) => `${point.label}: ${point.value}`).join(" · ");

  return [
    `## ${projectName}`,
    narrative,
    "",
    "Recent progress:",
    progressBlock,
    "",
    `Current signals: ${signalBlock}`,
    `Next: ${next}`,
    updatedLabel,
  ].join("\n");
};

export const buildPortfolioProjection = (input: {
  project: Project;
  dossier: KnowledgePageDetail | null;
}): PortfolioProjectProjection => {
  const { project, dossier } = input;
  const tone = project.status === "archived" ? "unknown" : healthTone(project.healthScore);
  const progress = progressItems(project, dossier);
  const next = nextStep(project);
  const proofPoints = proofPointsFor(project);
  const updatedLabel = formatUpdatedLabel(project.lastActiveAt);
  const confidenceLabel =
    dossier && dossier.confidence >= 0.8 && (project.healthScore !== null || project.lastActiveAt !== null)
      ? "High confidence"
      : "Review required";
  const projectName = cleanText(project.name) || "Untitled project";
  const narrative = narrativeFor({ ...project, name: projectName }, tone);

  return {
    projectId: project.id,
    projectName,
    statusLabel: project.status === "active" ? "Active project" : "Archived project",
    statusTone: tone,
    narrative,
    progress,
    nextStep: next,
    proofPoints,
    updatedLabel,
    confidenceLabel,
    copyText: copyTextFor(projectName, narrative, progress, proofPoints, next, updatedLabel),
  };
};
