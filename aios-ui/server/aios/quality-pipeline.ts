import fs from "node:fs";
import path from "node:path";

import type Database from "better-sqlite3";

import type {
  QualityPipelineGate,
  QualityPipelineGateStatus,
  QualityPipelineGateTier,
  QualityPipelineOverallStatus,
  QualityPipelineSummary,
} from "@/lib/control-plane";
import { ensureControlPlaneSchema } from "@/server/aios/schema";

const root = process.cwd().endsWith("aios-ui") ? path.dirname(process.cwd()) : process.cwd();
const configPath = path.join(root, "config", "quality-pipeline.json");

type GateConfig = {
  command?: string;
  working_directory?: string;
};

type StandardGateConfig = {
  key?: string;
  label?: string;
  tier?: string;
  applicability?: string[];
  required?: boolean;
};

type ProjectPipelineConfig = {
  project_id?: string;
  applies_to?: string[];
  full_pipeline?: boolean;
  blocked_reason?: string;
  gates?: Record<string, GateConfig>;
};

type QualityPipelineConfig = {
  standard?: {
    version?: string;
    gates?: StandardGateConfig[];
  };
  projects?: ProjectPipelineConfig[];
};

type PipelineRunRow = {
  id: string;
  gateKey: string;
  command: string | null;
  status: string;
  source: string;
  evidenceJson: string;
  completedAt: string | null;
};

type ProjectMatchRow = {
  name: string;
  repoPath: string;
};

const parseJsonArray = (raw: string): string[] => {
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter((item): item is string => typeof item === "string");
  } catch {
    return [];
  }
};

const loadConfig = (): QualityPipelineConfig => {
  try {
    const parsed = JSON.parse(fs.readFileSync(configPath, "utf8")) as unknown;
    if (!parsed || typeof parsed !== "object") {
      return {};
    }
    return parsed as QualityPipelineConfig;
  } catch {
    return {};
  }
};

const loadProjectRow = (db: Database.Database, projectId: string): ProjectMatchRow | null => {
  const row = db
    .prepare(
      `
      SELECT name, repo_path AS repoPath
      FROM projects
      WHERE id = ?
      LIMIT 1
    `,
    )
    .get(projectId) as ProjectMatchRow | undefined;
  return row ?? null;
};

const normalizeGateStatus = (status: string): QualityPipelineGateStatus => {
  if (
    status === "pass" ||
    status === "fail" ||
    status === "running" ||
    status === "stale" ||
    status === "missing" ||
    status === "blocked" ||
    status === "unknown"
  ) {
    return status;
  }
  return "unknown";
};

const normalizeGateTier = (tier: string | undefined): QualityPipelineGateTier => {
  if (tier === "tier_1_core" || tier === "production_app" || tier === "domain_specific") {
    return tier;
  }
  return "tier_1_core";
};

const stringList = (value: string[] | undefined, fallback: string[]): string[] => {
  const items = (value ?? []).map((item) => item.trim()).filter((item) => item.length > 0);
  return items.length > 0 ? items : fallback;
};

const isApplicable = (gateApplicability: string[], projectApplicability: string[]): boolean => {
  if (gateApplicability.includes("all")) {
    return true;
  }
  const projectKeys = new Set(projectApplicability);
  return gateApplicability.some((item) => projectKeys.has(item));
};

const latestRunsByGate = (db: Database.Database, projectId: string): Map<string, PipelineRunRow> => {
  ensureControlPlaneSchema(db);
  const rows = db
    .prepare(
      `
      SELECT
        id,
        gate_key AS gateKey,
        command,
        status,
        source,
        evidence_json AS evidenceJson,
        completed_at AS completedAt
      FROM quality_pipeline_runs
      WHERE project_id = ?
      ORDER BY COALESCE(completed_at, created_at) DESC
    `,
    )
    .all(projectId) as PipelineRunRow[];

  const latest = new Map<string, PipelineRunRow>();
  for (const row of rows) {
    if (!latest.has(row.gateKey)) {
      latest.set(row.gateKey, row);
    }
  }
  return latest;
};

const projectMatchKeys = (db: Database.Database, projectId: string): Set<string> => {
  const keys = new Set<string>([projectId, projectId.toLowerCase()]);
  const row = loadProjectRow(db, projectId);
  if (!row) {
    return keys;
  }
  const name = row.name.trim();
  if (name) {
    keys.add(name);
    keys.add(name.toLowerCase());
  }
  const basename = path.basename(row.repoPath.trim());
  if (basename) {
    keys.add(basename);
    keys.add(basename.toLowerCase());
  }
  return keys;
};

const readPackageScripts = (repoPath: string): Record<string, string> => {
  const packagePath = path.join(repoPath, "package.json");
  try {
    const parsed = JSON.parse(fs.readFileSync(packagePath, "utf8")) as unknown;
    if (!parsed || typeof parsed !== "object") {
      return {};
    }
    const scripts = (parsed as { scripts?: unknown }).scripts;
    if (!scripts || typeof scripts !== "object") {
      return {};
    }
    return Object.fromEntries(Object.entries(scripts).filter((entry): entry is [string, string] => typeof entry[1] === "string"));
  } catch {
    return {};
  }
};

const exists = (targetPath: string): boolean => {
  try {
    return fs.existsSync(targetPath);
  } catch {
    return false;
  }
};

const inferInstallCommand = (repoPath: string): string | null => {
  if (exists(path.join(repoPath, "pnpm-lock.yaml"))) {
    return "pnpm install --frozen-lockfile";
  }
  if (exists(path.join(repoPath, "package-lock.json")) || exists(path.join(repoPath, "package.json"))) {
    return "npm ci";
  }
  if (exists(path.join(repoPath, "uv.lock")) || exists(path.join(repoPath, "pyproject.toml"))) {
    return "uv sync";
  }
  if (exists(path.join(repoPath, "requirements.txt"))) {
    return "python -m pip install -r requirements.txt";
  }
  return null;
};

const scriptCommand = (scripts: Record<string, string>, key: string): string | null => {
  if (!scripts[key]) {
    return null;
  }
  return key === "test" ? "npm test" : `npm run ${key}`;
};

const inferProjectConfig = (db: Database.Database, projectId: string): ProjectPipelineConfig => {
  const row = loadProjectRow(db, projectId);
  if (!row) {
    return { project_id: projectId, applies_to: ["all"], full_pipeline: false, gates: {} };
  }
  const repoPath = row.repoPath.trim();
  const scripts = readPackageScripts(repoPath);
  const appliesTo: string[] = [];
  if (exists(path.join(repoPath, "package.json"))) {
    appliesTo.push("typescript_app");
  }
  if (exists(path.join(repoPath, "pyproject.toml")) || exists(path.join(repoPath, "requirements.txt"))) {
    appliesTo.push("python_service");
  }
  const gates: Record<string, GateConfig> = {};
  const install = inferInstallCommand(repoPath);
  if (install) {
    gates.install = { command: install, working_directory: "." };
  }
  for (const key of ["lint", "typecheck", "test", "build"]) {
    const command = scriptCommand(scripts, key);
    if (command) {
      gates[key] = { command, working_directory: "." };
    }
  }
  if (exists(path.join(repoPath, "scripts", "aios-architecture-check.mjs"))) {
    gates.architecture = { command: "node scripts/aios-architecture-check.mjs", working_directory: "." };
  }
  const workflowDir = path.join(repoPath, ".github", "workflows");
  if (exists(workflowDir)) {
    try {
      if (fs.readdirSync(workflowDir).some((file) => file.endsWith(".yml") || file.endsWith(".yaml"))) {
        gates.ci = { command: ".github/workflows", working_directory: "." };
      }
    } catch {
      // Ignore unreadable workflow directories; the gate remains missing.
    }
  }
  return {
    project_id: row.name.trim() || projectId,
    applies_to: appliesTo.length > 0 ? appliesTo : ["all"],
    full_pipeline: false,
    gates,
  };
};

const overallStatus = (gates: QualityPipelineGate[], blockedReason: string | null): QualityPipelineOverallStatus => {
  if (blockedReason) {
    return "blocked";
  }
  const required = gates.filter((gate) => gate.required);
  if (required.some((gate) => gate.status === "fail" || gate.status === "missing" || gate.status === "blocked")) {
    return "error";
  }
  if (required.some((gate) => gate.status === "running" || gate.status === "stale" || gate.status === "unknown")) {
    return "warning";
  }
  if (required.length > 0 && required.every((gate) => gate.status === "pass")) {
    return "healthy";
  }
  return "unknown";
};

export const getProjectQualityPipeline = (db: Database.Database, projectId: string): QualityPipelineSummary => {
  const config = loadConfig();
  const standard = config.standard ?? {};
  const matchKeys = projectMatchKeys(db, projectId);
  const projectConfig =
    (config.projects ?? []).find((project) => {
    const key = project.project_id?.trim();
    return key ? matchKeys.has(key) || matchKeys.has(key.toLowerCase()) : false;
    }) ?? inferProjectConfig(db, projectId);
  const projectGates = projectConfig?.gates ?? {};
  const projectApplicability = stringList(projectConfig?.applies_to, ["all"]);
  const latest = latestRunsByGate(db, projectId);
  const blockedReason = projectConfig?.blocked_reason ?? null;
  const gates: QualityPipelineGate[] = (standard.gates ?? [])
    .filter((gate): gate is Required<Pick<StandardGateConfig, "key">> & StandardGateConfig => typeof gate.key === "string" && gate.key.length > 0)
    .filter((gate) => isApplicable(stringList(gate.applicability, ["all"]), projectApplicability))
    .map((gate) => {
      const applicability = stringList(gate.applicability, ["all"]);
      const gateConfig = projectGates[gate.key];
      const latestRun = latest.get(gate.key);
      const configured = Boolean(gateConfig);
      const required = Boolean(gate.required);
      let status: QualityPipelineGateStatus = required && !configured ? "missing" : "stale";
      if (blockedReason && !configured) {
        status = "blocked";
      }
      if (latestRun) {
        status = normalizeGateStatus(latestRun.status);
      }
      return {
        key: gate.key,
        label: gate.label ?? gate.key,
        tier: normalizeGateTier(gate.tier),
        applicable: true,
        applicability,
        required,
        configured,
        status,
        command: gateConfig?.command ?? latestRun?.command ?? null,
        workingDirectory: gateConfig?.working_directory ?? null,
        latestRunId: latestRun?.id ?? null,
        source: latestRun?.source ?? (configured ? "configured" : null),
        evidence: latestRun ? parseJsonArray(latestRun.evidenceJson) : [],
        completedAt: latestRun?.completedAt ?? null,
        blockedReason: status === "blocked" ? blockedReason : null,
      };
    });
  const required = gates.filter((gate) => gate.required);
  const coverageByTier = {
    tier_1_core: {
      required: 0,
      configuredRequired: 0,
      passingRequired: 0,
      total: 0,
    },
    production_app: {
      required: 0,
      configuredRequired: 0,
      passingRequired: 0,
      total: 0,
    },
    domain_specific: {
      required: 0,
      configuredRequired: 0,
      passingRequired: 0,
      total: 0,
    },
  };
  for (const gate of gates) {
    const tierCoverage = coverageByTier[gate.tier];
    tierCoverage.total += 1;
    if (gate.required) {
      tierCoverage.required += 1;
      if (gate.configured) {
        tierCoverage.configuredRequired += 1;
      }
      if (gate.status === "pass") {
        tierCoverage.passingRequired += 1;
      }
    }
  }
  return {
    projectId,
    standardVersion: standard.version ?? "unknown",
    fullPipeline: Boolean(projectConfig?.full_pipeline),
    overallStatus: overallStatus(gates, blockedReason),
    blockedReason,
    coverage: {
      required: required.length,
      configuredRequired: required.filter((gate) => gate.configured).length,
      passingRequired: required.filter((gate) => gate.status === "pass").length,
      total: gates.length,
    },
    coverageByTier,
    gates,
  };
};
