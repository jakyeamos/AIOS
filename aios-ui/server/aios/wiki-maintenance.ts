import path from "node:path";

import type {
  KnowledgePageKind,
  KnowledgeRelationship,
  KnowledgeSection,
  WikiAgentPacket,
  WikiConfidence,
  WikiMaintenanceMetadata,
  WikiPageStatus,
  WikiSourceCoverage,
  WikiSourceRef,
} from "@/lib/control-plane";

type MaintenanceInput = {
  status?: string;
  confidence?: string | number;
  lastIndexedAt?: string;
  lastValidatedAt?: string;
  validatedBy?: string;
  sourceRefs?: WikiSourceRef[];
  sourceCoverage?: string;
  knownStaleAreas?: string[];
  relatedPages?: string[];
};

type PacketInput = {
  slug: string;
  title: string;
  kind: KnowledgePageKind;
  summary: string;
  maintenance: WikiMaintenanceMetadata;
  relationships: KnowledgeRelationship[];
  sections: KnowledgeSection[];
  recentChanges: Array<{ title: string; summary: string }>;
};

const PAGE_STATUSES = new Set<WikiPageStatus>([
  "current",
  "planned",
  "deprecated",
  "historical",
  "experimental",
  "unverified",
]);

const CONFIDENCE_VALUES = new Set<WikiConfidence>(["high", "medium", "low", "unknown"]);
const COVERAGE_VALUES = new Set<WikiSourceCoverage>(["strong", "partial", "weak", "none"]);
const VALIDATED_BY_VALUES = new Set(["human", "agent", "script", "unknown"]);

const confidenceFromNumber = (value: number): WikiConfidence => {
  if (value >= 0.85) {
    return "high";
  }
  if (value >= 0.65) {
    return "medium";
  }
  if (value > 0) {
    return "low";
  }
  return "unknown";
};

export const normalizeWikiStatus = (value: string | undefined): WikiPageStatus => {
  if (value && PAGE_STATUSES.has(value as WikiPageStatus)) {
    return value as WikiPageStatus;
  }

  if (value === "active" || value === "accepted" || value === "approved") {
    return "current";
  }
  if (value === "draft" || value === "candidate" || value === "proposed") {
    return "planned";
  }
  if (value === "archived") {
    return "historical";
  }

  return "unverified";
};

export const normalizeWikiConfidence = (value: string | number | undefined): WikiConfidence => {
  if (typeof value === "number") {
    return confidenceFromNumber(value);
  }
  if (value && CONFIDENCE_VALUES.has(value as WikiConfidence)) {
    return value as WikiConfidence;
  }
  if (value) {
    const parsed = Number(value);
    if (!Number.isNaN(parsed)) {
      return confidenceFromNumber(parsed > 1 ? parsed / 100 : parsed);
    }
  }
  return "unknown";
};

const normalizeCoverage = (value: string | undefined, refs: WikiSourceRef[]): WikiSourceCoverage => {
  if (value && COVERAGE_VALUES.has(value as WikiSourceCoverage)) {
    return value as WikiSourceCoverage;
  }
  if (refs.length >= 3) {
    return "strong";
  }
  if (refs.length > 0) {
    return "partial";
  }
  return "none";
};

const normalizeValidatedBy = (
  value: string | undefined,
): WikiMaintenanceMetadata["validatedBy"] => {
  return value && VALIDATED_BY_VALUES.has(value) ? (value as WikiMaintenanceMetadata["validatedBy"]) : "unknown";
};

export const scoreWikiMaintenance = (
  metadata: Omit<WikiMaintenanceMetadata, "maintenanceScore">,
): number => {
  const hasSources = metadata.sourceRefs.length > 0;
  const hasFreshness = Boolean(metadata.lastIndexedAt || metadata.lastValidatedAt);
  const hasValidation = Boolean(metadata.lastValidatedAt);
  const hasState = metadata.status !== "unverified";
  const hasCoverage = metadata.sourceCoverage !== "none";
  const hasKnownStaleAreas = metadata.knownStaleAreas.length > 0;
  const checkedRefs = metadata.sourceRefs.filter((ref) => ref.lastCheckedAt).length;

  if (!hasSources && !hasFreshness) {
    return 0;
  }
  if (!hasSources) {
    return 1;
  }
  if (!hasValidation || metadata.confidence === "unknown") {
    return 2;
  }
  if (hasState && hasCoverage) {
    if (metadata.validatedBy === "script" && checkedRefs === metadata.sourceRefs.length) {
      return 5;
    }
    if (metadata.validatedBy && metadata.validatedBy !== "unknown" && !hasKnownStaleAreas) {
      return 4;
    }
    return 3;
  }
  return 2;
};

export const buildWikiMaintenanceMetadata = (input: MaintenanceInput): WikiMaintenanceMetadata => {
  const sourceRefs = input.sourceRefs ?? [];
  const metadata = {
    status: normalizeWikiStatus(input.status),
    confidence: normalizeWikiConfidence(input.confidence),
    lastIndexedAt: input.lastIndexedAt,
    lastValidatedAt: input.lastValidatedAt,
    validatedBy: normalizeValidatedBy(input.validatedBy),
    sourceRefs,
    sourceCoverage: normalizeCoverage(input.sourceCoverage, sourceRefs),
    knownStaleAreas: input.knownStaleAreas ?? [],
    relatedPages: input.relatedPages ?? [],
  } satisfies Omit<WikiMaintenanceMetadata, "maintenanceScore">;

  return {
    ...metadata,
    maintenanceScore: scoreWikiMaintenance(metadata),
  };
};

const sourceLabel = (ref: WikiSourceRef): string => {
  const basename = path.basename(ref.path);
  if (ref.label) {
    return `${ref.label} (${basename})`;
  }
  return basename;
};

const classifyRiskItems = (input: PacketInput): string[] => {
  const risks = [
    ...input.maintenance.knownStaleAreas.map((area) => `Known stale area: ${area}`),
    ...input.sections
      .flatMap((section) => section.items)
      .filter((item) => /\b(risk|stale|deprecated|warning|unknown|contradiction)\b/i.test(item))
      .slice(0, 4),
  ];

  if (input.maintenance.status !== "current") {
    risks.unshift(`Page is ${input.maintenance.status}; verify source before treating it as implemented behavior.`);
  }
  if (input.maintenance.sourceRefs.length === 0) {
    risks.unshift("No source refs are attached to this page.");
  }

  return risks.length > 0 ? risks : ["No page-specific risks are recorded yet."];
};

const classifyCurrentVsPlanned = (input: PacketInput): string[] => {
  const notes = input.sections
    .flatMap((section) => section.items)
    .filter((item) => /\b(current|planned|deprecated|historical|experimental|unverified|roadmap)\b/i.test(item))
    .slice(0, 5);

  return [
    `Page status is ${input.maintenance.status}.`,
    ...notes,
  ];
};

export const buildWikiAgentPacket = (input: PacketInput): WikiAgentPacket => {
  const sourceRefs = input.maintenance.sourceRefs;
  const standards = [
    "Use wiki/context pages as maps, not source of truth.",
    "Read referenced source files before editing behavior.",
    "Run relevant tests, typecheck, lint, or validation scripts after changes.",
  ];

  if (input.kind === "project" || input.kind === "system") {
    standards.push("Update optional project notes only when meaningful architecture/workflow context would otherwise be lost.");
  }

  return {
    subsystem: input.title,
    status: input.maintenance.status,
    confidence: input.maintenance.confidence,
    maintenanceScore: input.maintenance.maintenanceScore,
    lastValidated: input.maintenance.lastValidatedAt ?? "not validated",
    knownStaleAreas: input.maintenance.knownStaleAreas,
    relevantWikiPages: [
      { title: input.title, href: `/knowledge/${input.slug}`, status: input.maintenance.status },
      ...input.relationships.slice(0, 5).map((relationship) => ({
        title: relationship.label,
        href: relationship.href,
        status: "unverified" as const,
      })),
    ],
    sourceFilesToInspect: sourceRefs,
    applicableStandards: standards,
    knownRisks: classifyRiskItems(input),
    currentVsPlannedNotes: classifyCurrentVsPlanned(input),
    verificationChecklist: [
      "Use this packet to decide where to look; do not treat it as proof.",
      sourceRefs.length > 0
        ? `Inspect source refs: ${sourceRefs.map(sourceLabel).join(", ")}.`
        : "Find and attach source refs before using this page for task routing.",
      "Run `pnpm context:validate` when context packets or routing files change.",
      "Run `pnpm wiki:check` after wiki metadata, source refs, or context packets change.",
      "Run the relevant project tests/typecheck/lint for changed code.",
      "Update wiki metadata or optional project context when architecture, commands, APIs, workflows, rules, risks, or failure modes changed.",
    ],
  };
};

export const parseSourceRef = (value: string): WikiSourceRef | null => {
  const [head, label, checked] = value.split("|").map((part) => part.trim());
  const separator = head.indexOf(":");
  if (separator === -1) {
    return null;
  }

  const type = head.slice(0, separator).trim() as WikiSourceRef["type"];
  const rawPath = head.slice(separator + 1).trim();
  if (!rawPath) {
    return null;
  }

  const lineMatch = rawPath.match(/^(.*)#L(\d+)(?:-L?(\d+))?$/);
  return {
    type,
    path: lineMatch?.[1] ?? rawPath,
    label: label || undefined,
    lineStart: lineMatch?.[2] ? Number(lineMatch[2]) : undefined,
    lineEnd: lineMatch?.[3] ? Number(lineMatch[3]) : undefined,
    lastCheckedAt: checked || undefined,
  };
};
