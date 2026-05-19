import { z } from "zod";

import {
  cancelControlPlaneRun,
  getControlPlaneOverview,
  getControlPlaneRunDetail,
  getGovernanceOverview,
  invokeControlPlaneRun,
  planTask,
  registerControlPlaneManualInvocation,
  requestPacketExpansion,
  resolveControlPlaneFinding,
  reviewControlPlaneWriteback,
} from "@/server/aios/control-plane";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

export const controlPlaneRouter = createTRPCRouter({
  overview: publicProcedure.query(({ ctx }) => getControlPlaneOverview(ctx.db)),

  governance: publicProcedure.query(({ ctx }) => getGovernanceOverview(ctx.db)),

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

  registerManualInvocation: publicProcedure
    .input(
      z.object({
        runId: z.string().min(1),
        sessionId: z.string().min(1),
        invocationId: z.string().min(1).optional(),
        backendKey: z.enum(["manual-session-legacy", "codex-managed-runtime", "claude-managed-runtime"]).optional(),
        actor: z.string().min(1).max(80).optional(),
        note: z.string().max(400).optional(),
      }),
    )
    .mutation(({ ctx, input }) => registerControlPlaneManualInvocation(ctx.db, input)),

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

  resolveFinding: publicProcedure
    .input(
      z.object({
        findingId: z.string().min(1),
        status: z.enum(["open", "accepted_tradeoff", "mitigated", "dismissed", "reopened"]),
        actor: z.string().min(1).max(80).optional(),
        rationale: z.string().max(500).optional(),
        evidence: z.array(z.record(z.string(), z.unknown())).optional(),
      }),
    )
    .mutation(({ ctx, input }) => resolveControlPlaneFinding(ctx.db, input)),
});
