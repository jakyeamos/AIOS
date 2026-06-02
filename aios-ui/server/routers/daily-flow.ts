import { z } from "zod";

import type { DailyFlowTrace } from "@/lib/control-plane";
import { previewDailyFlow, replayDailyFlow } from "@/server/aios/daily-flow";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

export const dailyFlowRouter = createTRPCRouter({
  preview: publicProcedure
    .input(
      z.object({
        objective: z.string().min(3).max(500),
        projectId: z.string().min(1).nullable().optional(),
      }),
    )
    .query(({ ctx, input }): DailyFlowTrace =>
      previewDailyFlow(ctx.db, { objective: input.objective, projectId: input.projectId ?? null }),
    ),

  replay: publicProcedure
    .input(z.object({ runId: z.string().min(1) }))
    .query(({ ctx, input }): DailyFlowTrace => replayDailyFlow(ctx.db, input)),
});
