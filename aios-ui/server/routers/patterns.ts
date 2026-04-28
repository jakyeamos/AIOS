import { randomUUID } from "node:crypto";

import { z } from "zod";

import type { Pattern, PatternState } from "@/lib/types";
import { tableExists } from "@/server/db";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

type PatternRow = {
  id: string;
  label: string | null;
  sessionCount: number;
  lastSeen: string;
  humanApproved: number;
};

type PatternRef =
  | {
      kind: "prompt";
      value: string;
    }
  | {
      kind: "hash";
      value: string;
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

  return {
    id: row.id,
    label: row.label ?? null,
    state: stateFromCount(row.sessionCount, approved),
    humanApproved: approved,
    sessionCount: row.sessionCount,
    lastSeen: row.lastSeen,
  };
};

const parsePatternRef = (id: string): PatternRef => {
  if (id.startsWith("id:")) {
    return {
      kind: "prompt",
      value: id.slice(3),
    };
  }

  return {
    kind: "hash",
    value: id,
  };
};

const ensurePromptLibraryLinks = (ctxDb: ReturnType<typeof import("@/server/db").getDb>): void => {
  if (tableExists("prompt_library_links")) {
    return;
  }

  ctxDb.exec(`
    CREATE TABLE IF NOT EXISTS prompt_library_links (
      id TEXT PRIMARY KEY,
      prompt_hash TEXT NOT NULL,
      obsidian_note_path TEXT,
      promoted_at TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_prompt_library_links_hash ON prompt_library_links(prompt_hash);
  `);
};

export const patternsRouter = createTRPCRouter({
  list: publicProcedure
    .input(z.object({ limit: z.number().int().min(1).max(200).default(40) }).optional())
    .query(({ ctx, input }): Pattern[] => {
      if (!tableExists("prompts_used") || !tableExists("sessions")) {
        return [];
      }

      const limit = input?.limit ?? 40;
      const hasLinks = tableExists("prompt_library_links");
      const rows = hasLinks
        ? (ctx.db
            .prepare(
              `
              SELECT
                CASE
                  WHEN pu.prompt_hash IS NULL THEN 'id:' || pu.id
                  ELSE pu.prompt_hash
                END AS id,
                MIN(pu.prompt_text) AS label,
                COUNT(*) AS sessionCount,
                MAX(s.started_at) AS lastSeen,
                MAX(
                  CASE
                    WHEN pu.reusable_candidate = 1 THEN 1
                    WHEN pu.prompt_hash IS NOT NULL AND pll.promoted_at IS NOT NULL THEN 1
                    ELSE 0
                  END
                ) AS humanApproved
              FROM prompts_used pu
              INNER JOIN sessions s ON s.id = pu.session_id
              LEFT JOIN prompt_library_links pll ON pll.prompt_hash = pu.prompt_hash
              GROUP BY
                CASE
                  WHEN pu.prompt_hash IS NULL THEN 'id:' || pu.id
                  ELSE pu.prompt_hash
                END
              ORDER BY sessionCount DESC
              LIMIT ?
            `,
            )
            .all(limit) as PatternRow[])
        : (ctx.db
            .prepare(
              `
              SELECT
                CASE
                  WHEN pu.prompt_hash IS NULL THEN 'id:' || pu.id
                  ELSE pu.prompt_hash
                END AS id,
                MIN(pu.prompt_text) AS label,
                COUNT(*) AS sessionCount,
                MAX(s.started_at) AS lastSeen,
                MAX(CASE WHEN pu.reusable_candidate = 1 THEN 1 ELSE 0 END) AS humanApproved
              FROM prompts_used pu
              INNER JOIN sessions s ON s.id = pu.session_id
              GROUP BY
                CASE
                  WHEN pu.prompt_hash IS NULL THEN 'id:' || pu.id
                  ELSE pu.prompt_hash
                END
              ORDER BY sessionCount DESC
              LIMIT ?
            `,
            )
            .all(limit) as PatternRow[]);

      return rows.map(mapPattern);
    }),

  approve: publicProcedure
    .input(z.object({ id: z.string().min(1) }))
    .mutation(({ ctx, input }): { ok: boolean; id: string; changedRows: number } => {
      if (!tableExists("prompts_used")) {
        return { ok: false, id: input.id, changedRows: 0 };
      }

      const patternRef = parsePatternRef(input.id);

      if (patternRef.kind === "prompt") {
        const result = ctx.db
          .prepare(
            `
            UPDATE prompts_used
            SET reusable_candidate = 1
            WHERE id = ?
          `,
          )
          .run(patternRef.value);

        return {
          ok: result.changes > 0,
          id: input.id,
          changedRows: result.changes,
        };
      }

      ensurePromptLibraryLinks(ctx.db);
      ctx.db
        .prepare(
          `
          DELETE FROM prompt_library_links
          WHERE prompt_hash = ?
        `,
        )
        .run(patternRef.value);

      ctx.db
        .prepare(
          `
          INSERT INTO prompt_library_links (id, prompt_hash, promoted_at)
          VALUES (?, ?, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        `,
        )
        .run(`pll-${randomUUID()}`, patternRef.value);

      const result = ctx.db
        .prepare(
          `
          UPDATE prompts_used
          SET reusable_candidate = 1
          WHERE prompt_hash = ?
        `,
        )
        .run(patternRef.value);

      return {
        ok: true,
        id: input.id,
        changedRows: result.changes,
      };
    }),

  reject: publicProcedure
    .input(z.object({ id: z.string().min(1) }))
    .mutation(({ ctx, input }): { ok: boolean; id: string; changedRows: number } => {
      if (!tableExists("prompts_used")) {
        return { ok: false, id: input.id, changedRows: 0 };
      }

      const patternRef = parsePatternRef(input.id);

      if (patternRef.kind === "prompt") {
        const result = ctx.db
          .prepare(
            `
            UPDATE prompts_used
            SET reusable_candidate = 0
            WHERE id = ?
          `,
          )
          .run(patternRef.value);

        return {
          ok: result.changes > 0,
          id: input.id,
          changedRows: result.changes,
        };
      }

      if (tableExists("prompt_library_links")) {
        ctx.db
          .prepare(
            `
            DELETE FROM prompt_library_links
            WHERE prompt_hash = ?
          `,
          )
          .run(patternRef.value);
      }

      const result = ctx.db
        .prepare(
          `
          UPDATE prompts_used
          SET reusable_candidate = 0
          WHERE prompt_hash = ?
        `,
        )
        .run(patternRef.value);

      return {
        ok: true,
        id: input.id,
        changedRows: result.changes,
      };
    }),
});
