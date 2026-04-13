import type { Experiment } from "@/lib/types";
import { tableExists } from "@/server/db";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

type ExperimentRow = {
  id: string;
  name: string;
  surface: string;
  hypothesis: string;
  baselineValue: number | null;
  challengerValue: number | null;
  verdict: string | null;
  startedAt: string;
  endedAt: string | null;
  notes: string | null;
};

const mapExperiment = (row: ExperimentRow): Experiment => {
  const baseline = row.baselineValue;
  const challenger = row.challengerValue;
  const delta = baseline !== null && challenger !== null ? challenger - baseline : null;
  const winner =
    delta === null
      ? null
      : delta > 0
        ? "challenger"
        : delta < 0
          ? "baseline"
          : "inconclusive";

  return {
    id: row.id,
    name: row.name,
    surface: row.surface,
    hypothesis: row.hypothesis,
    baselineValue: row.baselineValue,
    challengerValue: row.challengerValue,
    verdict: row.verdict,
    startedAt: row.startedAt,
    endedAt: row.endedAt,
    notes: row.notes,
    delta,
    winner,
  };
};

export const experimentsRouter = createTRPCRouter({
  list: publicProcedure.query(({ ctx }): Experiment[] => {
    if (!tableExists("experiments")) {
      return [];
    }

    const rows = ctx.db
      .prepare(
        `
        SELECT
          id,
          name,
          surface,
          hypothesis,
          baseline_value AS baselineValue,
          challenger_value AS challengerValue,
          verdict,
          started_at AS startedAt,
          ended_at AS endedAt,
          notes
        FROM experiments
        ORDER BY started_at DESC
      `,
      )
      .all() as ExperimentRow[];

    return rows.map(mapExperiment);
  }),
});
