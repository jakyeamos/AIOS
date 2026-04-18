import { z } from "zod";

import type { KnowledgePageDetail, KnowledgePageSummary } from "@/lib/control-plane";
import { getKnowledgePage, getProjectDossier, listKnowledgeKinds, listKnowledgePages } from "@/server/aios/knowledge";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

export const knowledgeRouter = createTRPCRouter({
  index: publicProcedure.query(({ ctx }): KnowledgePageSummary[] => listKnowledgePages(ctx.db)),

  grouped: publicProcedure.query(({ ctx }) => listKnowledgeKinds(ctx.db)),

  detail: publicProcedure
    .input(z.object({ slug: z.string().min(1) }))
    .query(({ ctx, input }): KnowledgePageDetail | null => getKnowledgePage(ctx.db, input.slug)),

  projectDossier: publicProcedure
    .input(z.object({ projectId: z.string().min(1) }))
    .query(({ ctx, input }): KnowledgePageDetail | null => getProjectDossier(ctx.db, input.projectId)),
});
