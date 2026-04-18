import { z } from "zod";

import type { ChangeItem } from "@/lib/control-plane";
import { listRecentChanges } from "@/server/aios/changes";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

export const changesRouter = createTRPCRouter({
  list: publicProcedure
    .input(
      z.object({
        projectId: z.string().min(1).optional(),
        limit: z.number().int().min(1).max(20).default(8),
      }).optional(),
    )
    .query(({ ctx, input }): ChangeItem[] => listRecentChanges(ctx.db, input)),
});
