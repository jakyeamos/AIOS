import { z } from "zod";

import type { Pattern, PatternState } from "@/lib/types";
import { getDb, tableExists } from "@/server/db";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

type PatternRow = {
  id: string;
  label: string | null;
  state: string | null;
  sessionCount: number;
  lastSeen: string;
  humanApproved: number;
};

const stateFromCount = (sessionCount: number, approved: boolean): PatternState => {
  if (approved) {
    return "rule";
  }

  if (sessionCount >= 8) {
    return "hypothesis";
  }

  if (sessionCount >= 4) {
    return "observation";
  }

  return "notice";
};

const mapPattern = (row: PatternRow): Pattern => {
  const approved = row.humanApproved === 1;
  const state =
    row.state === "rule" || row.state === "hypothesis" || row.state === "observation" || row.state === "notice"
      ? row.state
      : stateFromCount(row.sessionCount, approved);

  return {
    id: row.id,
    label: row.label ?? null,
    state,
    humanApproved: approved,
    sessionCount: row.sessionCount,
    lastSeen: row.lastSeen,
  };
};

const columnExists = (tableName: string, columnName: string): boolean => {
  const rows = getDb().prepare(`PRAGMA table_info(${tableName})`).all() as Array<{ name: string }>;
  return rows.some((row) => row.name === columnName);
};

const countExpression = (): string => {
  const options = ["source_sessions", "frequency_count", "confirmation_count"].filter((column) =>
    columnExists("patterns", column),
  );
  return options.length > 0 ? `COALESCE(${options.join(", ")}, 0)` : "0";
};

const lastSeenExpression = (): string => {
  const options = ["last_seen_at", "last_confirmed_at", "created_at"].filter((column) =>
    columnExists("patterns", column),
  );
  if (options.length === 0) {
    return "created_at";
  }
  return options.length === 1 ? options[0] : `COALESCE(${options.join(", ")})`;
};

const stateExpression = (): string => (columnExists("patterns", "state") ? "state" : "'observation'");

const humanApprovedExpression = (): string => (columnExists("patterns", "human_approved") ? "human_approved" : "0");

const confidenceExpression = (): string => (columnExists("patterns", "confidence") ? "confidence" : "0");

export const patternsRouter = createTRPCRouter({
  list: publicProcedure
    .input(
      z
        .object({
          limit: z.number().int().min(1).max(200).default(40),
          minSessionCount: z.number().int().min(1).max(100).default(4),
        })
        .optional(),
    )
    .query(({ ctx, input }): Pattern[] => {
      if (!tableExists("patterns")) {
        return [];
      }

      const limit = input?.limit ?? 40;
      const minSessionCount = input?.minSessionCount ?? 4;
      const sourceCount = countExpression();
      const stateValue = stateExpression();
      const humanApproved = humanApprovedExpression();
      const confidence = confidenceExpression();
      const rows = ctx.db
        .prepare(
          `
          SELECT
            id,
            title AS label,
            ${stateValue} AS state,
            ${sourceCount} AS sessionCount,
            ${lastSeenExpression()} AS lastSeen,
            ${humanApproved} AS humanApproved
          FROM patterns
          WHERE status != 'discarded'
            AND class != 'prompt'
            AND (${stateValue} IN ('hypothesis', 'knowledge', 'rule') OR ${humanApproved} = 1 OR ${sourceCount} >= ?)
          ORDER BY ${humanApproved} DESC, ${confidence} DESC, sessionCount DESC, lastSeen DESC
          LIMIT ?
        `,
        )
        .all(minSessionCount, limit) as PatternRow[];

      return rows.map(mapPattern);
    }),

  approve: publicProcedure
    .input(z.object({ id: z.string().min(1) }))
    .mutation(({ ctx, input }): { ok: boolean; id: string; changedRows: number } => {
      if (!tableExists("patterns")) {
        return { ok: false, id: input.id, changedRows: 0 };
      }

      const result = ctx.db
        .prepare(
          `
          UPDATE patterns
          SET human_approved = 1,
              state = 'rule',
              status = 'active',
              promoted_at = COALESCE(promoted_at, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
          WHERE id = ?
        `,
        )
        .run(input.id);

      return {
        ok: result.changes > 0,
        id: input.id,
        changedRows: result.changes,
      };
    }),

  reject: publicProcedure
    .input(z.object({ id: z.string().min(1) }))
    .mutation(({ ctx, input }): { ok: boolean; id: string; changedRows: number } => {
      if (!tableExists("patterns")) {
        return { ok: false, id: input.id, changedRows: 0 };
      }

      const result = ctx.db
        .prepare(
          `
          UPDATE patterns
          SET human_approved = 0,
              status = 'discarded'
          WHERE id = ?
        `,
        )
        .run(input.id);

      return {
        ok: result.changes > 0,
        id: input.id,
        changedRows: result.changes,
      };
    }),
});
