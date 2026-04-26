import fs from "node:fs";
import path from "node:path";

import type Database from "better-sqlite3";

import type {
  QualityPipelineGate,
  QualityPipelineGateStatus,
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
  required?: boolean;
};

type ProjectPipelineConfig = {
  project_id?: string;
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
  const projectConfig = (config.projects ?? []).find((project) => {
    const key = project.project_id?.trim();
    return key ? matchKeys.has(key) || matchKeys.has(key.toLowerCase()) : false;
  });
  const projectGates = projectConfig?.gates ?? {};
  const latest = latestRunsByGate(db, projectId);
  const blockedReason = projectConfig?.blocked_reason ?? null;
  const gates: QualityPipelineGate[] = (standard.gates ?? [])
    .filter((gate): gate is Required<Pick<StandardGateConfig, "key">> & StandardGateConfig => typeof gate.key === "string" && gate.key.length > 0)
    .map((gate) => {
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
    gates,
  };
};
