import { z } from "zod";

import { planTask, getControlPlaneOverview } from "@/server/aios/control-plane";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

export const controlPlaneRouter = createTRPCRouter({
  overview: publicProcedure.query(({ ctx }) => getControlPlaneOverview(ctx.db)),

  plan: publicProcedure
    .input(
      z.object({
        objective: z.string().min(8),
        projectId: z.string().min(1).optional(),
      }),
    )
    .mutation(({ ctx, input }) => planTask(ctx.db, input)),
});
