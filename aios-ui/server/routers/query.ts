import { z } from "zod";

import type { GroundedAnswer } from "@/lib/control-plane";
import { answerGroundedQuestion } from "@/server/aios/query";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

export const queryRouter = createTRPCRouter({
  ask: publicProcedure
    .input(
      z.object({
        question: z.string().min(5),
        projectId: z.string().min(1).optional(),
      }),
    )
    .mutation(({ ctx, input }): GroundedAnswer => answerGroundedQuestion(ctx.db, input)),
});
