import { z } from "zod";

import {
  cancelControlPlaneRun,
  getControlPlaneOverview,
  getControlPlaneRunDetail,
  invokeControlPlaneRun,
  planTask,
  requestPacketExpansion,
  reviewControlPlaneWriteback,
} from "@/server/aios/control-plane";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

export const controlPlaneRouter = createTRPCRouter({
  overview: publicProcedure.query(({ ctx }) => getControlPlaneOverview(ctx.db)),

  runDetail: publicProcedure
    .input(z.object({ runId: z.string().min(1) }))
    .query(({ ctx, input }) => getControlPlaneRunDetail(ctx.db, input.runId)),

  plan: publicProcedure
    .input(
      z.object({
        objective: z.string().min(8),
        projectId: z.string().min(1).optional(),
        policyMode: z.enum(["compact-ranked", "explore"]).default("compact-ranked").optional(),
        tokenBudget: z.number().int().min(180).max(2200).optional(),
      }),
    )
    .mutation(({ ctx, input }) => planTask(ctx.db, input)),

  invoke: publicProcedure
    .input(
      z.object({
        runId: z.string().min(1),
      }),
    )
    .mutation(({ ctx, input }) => invokeControlPlaneRun(ctx.db, input)),

  cancel: publicProcedure
    .input(
      z.object({
        runId: z.string().min(1),
      }),
    )
    .mutation(({ ctx, input }) => cancelControlPlaneRun(ctx.db, input)),

  expand: publicProcedure
    .input(
      z.object({
        packetId: z.string().min(1),
        runId: z.string().min(1).optional(),
        projectId: z.string().min(1).optional(),
        requestKind: z.enum(["topic", "failure_pattern", "code_area", "policy", "recent_run"]),
        requestTarget: z.string().min(2),
        tokenBudget: z.number().int().min(60).max(600).optional(),
      }),
    )
    .mutation(({ ctx, input }) => requestPacketExpansion(ctx.db, input)),

  reviewWriteback: publicProcedure
    .input(
      z.object({
        writebackId: z.string().min(1),
        decision: z.enum(["applied", "rejected"]),
        note: z.string().max(400).optional(),
      }),
    )
    .mutation(({ ctx, input }) => reviewControlPlaneWriteback(ctx.db, input)),
});
