import type Database from "better-sqlite3";

import type { AiosProjectComponentKey, AiosProjectComponentSetting } from "@/lib/control-plane";
import { ensureControlPlaneSchema } from "@/server/aios/schema";

const componentDefinitions: Array<Omit<AiosProjectComponentSetting, "enabled" | "updatedAt">> = [
  {
    key: "taski_summary",
    label: "Taski summary",
    summary: "Operating summary, suggested actions, blockers, and recent outcomes.",
  },
  {
    key: "knowledge_dossier",
    label: "Knowledge dossier",
    summary: "Durable project memory, references, relationships, and recent changes.",
  },
  {
    key: "standards_health",
    label: "Standards health",
    summary: "Standards deltas, health scores, migration state, and backfill tasks.",
  },
  {
    key: "quality_pipeline",
    label: "Quality pipeline",
    summary: "Required gates, coverage by tier, commands, and latest gate results.",
  },
  {
    key: "learning_writebacks",
    label: "Learning writebacks",
    summary: "Learned policies, drift markers, structured findings, and approval queue.",
  },
  {
    key: "active_runs",
    label: "Active runs",
    summary: "Recent orchestration runs linked to this project.",
  },
];

const componentKeys = new Set<AiosProjectComponentKey>(componentDefinitions.map((definition) => definition.key));

type ComponentSettingRow = {
  componentKey: string;
  enabled: number;
  updatedAt: string;
};

export const isAiosProjectComponentKey = (key: string): key is AiosProjectComponentKey =>
  componentKeys.has(key as AiosProjectComponentKey);

export const listAiosProjectComponentSettings = (
  db: Database.Database,
  projectId: string,
): AiosProjectComponentSetting[] => {
  ensureControlPlaneSchema(db);
  const rows = db
    .prepare(
      `
      SELECT
        component_key AS componentKey,
        enabled,
        updated_at AS updatedAt
      FROM project_aios_component_settings
      WHERE project_id = ?
    `,
    )
    .all(projectId) as ComponentSettingRow[];

  const rowsByKey = new Map(rows.map((row) => [row.componentKey, row]));
  return componentDefinitions.map((definition) => {
    const row = rowsByKey.get(definition.key);
    return {
      ...definition,
      enabled: row ? row.enabled === 1 : true,
      updatedAt: row?.updatedAt ?? null,
    };
  });
};
