import { z } from "zod";

import type { NextAction } from "@/lib/control-plane";
import { getNextActions } from "@/server/aios/next-action";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

export const nextActionRouter = createTRPCRouter({
  getForProject: publicProcedure
    .input(
      z.object({
        projectId: z.string().min(1),
        limit: z.number().int().min(1).max(50).optional(),
      }),
    )
    .query(({ ctx, input }): NextAction[] =>
      getNextActions(ctx.db, { projectId: input.projectId, limit: input.limit }),
    ),

  topAcrossProjects: publicProcedure
    .input(z.object({ limit: z.number().int().min(1).max(50).optional() }).optional())
    .query(({ ctx, input }): NextAction[] =>
      getNextActions(ctx.db, { projectId: null, limit: input?.limit }),
    ),
});
