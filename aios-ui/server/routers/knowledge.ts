import { z } from "zod";

import type { KnowledgePageDetail, KnowledgePageSummary, TruthKnowledgeBoundary } from "@/lib/control-plane";
import {
  getKnowledgePage,
  getProjectDossier,
  getTruthKnowledgeBoundary,
  listKnowledgeKinds,
  listKnowledgePages,
} from "@/server/aios/knowledge";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

export const knowledgeRouter = createTRPCRouter({
  index: publicProcedure.query(({ ctx }): KnowledgePageSummary[] => listKnowledgePages(ctx.db)),

  grouped: publicProcedure.query(({ ctx }) => listKnowledgeKinds(ctx.db)),

  truthBoundary: publicProcedure.query(({ ctx }): TruthKnowledgeBoundary => getTruthKnowledgeBoundary(ctx.db)),

  detail: publicProcedure
    .input(z.object({ slug: z.string().min(1) }))
    .query(({ ctx, input }): KnowledgePageDetail | null => getKnowledgePage(ctx.db, input.slug)),

  projectDossier: publicProcedure
    .input(z.object({ projectId: z.string().min(1) }))
    .query(({ ctx, input }): KnowledgePageDetail | null => getProjectDossier(ctx.db, input.projectId)),

  agentPacket: publicProcedure
    .input(z.object({ slug: z.string().min(1) }))
    .query(({ ctx, input }) => getKnowledgePage(ctx.db, input.slug)?.agentPacket ?? null),
});
