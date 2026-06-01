import { z } from "zod";

import {
  getLearningImpactForRun,
  getLearningImpactRollup,
  listConservativeProposals,
  listRecurringPatterns,
} from "@/server/aios/learning";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

export const learningRouter = createTRPCRouter({
  getRunImpact: publicProcedure
    .input(z.object({ runId: z.string().min(1) }))
    .query(({ ctx, input }) => getLearningImpactForRun(ctx.db, input.runId)),

  getRollup: publicProcedure
    .input(
      z.object({
        scope: z.enum(["workflow", "prompt", "skill"]),
        key: z.string().min(1),
        since: z.string().min(1),
        projectId: z.string().nullable().optional(),
      }),
    )
    .query(({ ctx, input }) =>
      getLearningImpactRollup(ctx.db, input.scope, input.key, input.since, input.projectId ?? null),
    ),

  listPatterns: publicProcedure
    .input(
      z.object({
        since: z.string().min(1),
        projectId: z.string().nullable().optional(),
        limit: z.number().int().min(1).max(200).optional(),
      }),
    )
    .query(({ ctx, input }) =>
      listRecurringPatterns(ctx.db, input.since, input.projectId ?? null, input.limit ?? 50),
    ),

  listProposals: publicProcedure
    .input(
      z.object({
        status: z.string().optional(),
        limit: z.number().int().min(1).max(200).optional(),
      }),
    )
    .query(({ ctx, input }) => listConservativeProposals(ctx.db, input.status, input.limit ?? 50)),
});
