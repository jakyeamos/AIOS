import { z } from "zod";

import {
  approveShadowCandidate,
  getEvalRunsForRun,
  getEvalSummaryForRun,
  getEvalSummaryForProject,
  getShadowCandidateQueue,
} from "@/server/aios/eval-data";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

export const evalRouter = createTRPCRouter({
  summaryForProject: publicProcedure
    .input(z.object({ projectId: z.string().min(1) }))
    .query(({ ctx, input }) => getEvalSummaryForProject(ctx.db, input.projectId)),

  runsForRun: publicProcedure
    .input(z.object({ runId: z.string().min(1) }))
    .query(({ ctx, input }) => getEvalRunsForRun(ctx.db, input.runId)),

  summaryForRun: publicProcedure
    .input(z.object({ runId: z.string().min(1) }))
    .query(({ ctx, input }) => getEvalSummaryForRun(ctx.db, input.runId)),

  shadowCandidates: publicProcedure.query(({ ctx }) => getShadowCandidateQueue(ctx.db)),

  approveShadowCandidate: publicProcedure
    .input(z.object({ candidateId: z.string().min(1) }))
    .mutation(({ ctx, input }) => approveShadowCandidate(ctx.db, input.candidateId)),
});
