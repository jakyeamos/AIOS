import { z } from "zod";

import type { Prompt, PromptClassification } from "@/lib/types";
import { tableExists } from "@/server/db";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

type PromptRow = {
  id: string;
  sessionId: string;
  promptHash: string | null;
  promptText: string | null;
  classification: string | null;
  outcomeScore: number | null;
  reusableCandidate: number;
  retrievalFired: number;
  retrievalSource: string | null;
};

const normalizeClassification = (classification: string | null): PromptClassification => {
  if (classification === "debug") {
    return "debugging";
  }

  if (classification === "plan") {
    return "planning";
  }

  if (
    classification === "debugging" ||
    classification === "planning" ||
    classification === "refactor" ||
    classification === "review" ||
    classification === "explain" ||
    classification === "implement" ||
    classification === "other"
  ) {
    return classification;
  }

  return "other";
};

const mapPrompt = (row: PromptRow): Prompt => ({
  id: row.id,
  sessionId: row.sessionId,
  promptHash: row.promptHash,
  promptText: row.promptText,
  classification: normalizeClassification(row.classification),
  outcomeScore: row.outcomeScore,
  reusableCandidate: row.reusableCandidate === 1,
  retrievalFired: row.retrievalFired === 1,
  retrievalSource: row.retrievalSource,
});

export const promptsRouter = createTRPCRouter({
  list: publicProcedure
    .input(z.object({ limit: z.number().int().min(1).max(200).default(50) }).optional())
    .query(({ ctx, input }): Prompt[] => {
      if (!tableExists("prompts_used") || !tableExists("sessions")) {
        return [];
      }

      const limit = input?.limit ?? 50;
      const rows = ctx.db
        .prepare(
          `
          SELECT
            pu.id,
            pu.session_id AS sessionId,
            pu.prompt_hash AS promptHash,
            pu.prompt_text AS promptText,
            pu.classification,
            pu.outcome_score AS outcomeScore,
            pu.reusable_candidate AS reusableCandidate,
            pu.retrieval_fired AS retrievalFired,
            pu.retrieval_source AS retrievalSource
          FROM prompts_used pu
          INNER JOIN sessions s ON s.id = pu.session_id
          ORDER BY s.started_at DESC
          LIMIT ?
        `,
        )
        .all(limit) as PromptRow[];

      return rows.map(mapPrompt);
    }),

  byHash: publicProcedure
    .input(z.object({ hash: z.string().min(1), limit: z.number().int().min(1).max(200).default(50) }))
    .query(({ ctx, input }): Prompt[] => {
      if (!tableExists("prompts_used") || !tableExists("sessions")) {
        return [];
      }

      const rows = ctx.db
        .prepare(
          `
          SELECT
            pu.id,
            pu.session_id AS sessionId,
            pu.prompt_hash AS promptHash,
            pu.prompt_text AS promptText,
            pu.classification,
            pu.outcome_score AS outcomeScore,
            pu.reusable_candidate AS reusableCandidate,
            pu.retrieval_fired AS retrievalFired,
            pu.retrieval_source AS retrievalSource
          FROM prompts_used pu
          INNER JOIN sessions s ON s.id = pu.session_id
          WHERE pu.prompt_hash = ?
          ORDER BY s.started_at DESC
          LIMIT ?
        `,
        )
        .all(input.hash, input.limit) as PromptRow[];

      return rows.map(mapPrompt);
    }),
});
