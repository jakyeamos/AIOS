import { z } from "zod";

import type { EntityKind, OperatorSearchHit } from "@/lib/control-plane";
import { searchEntities } from "@/server/aios/operator-search";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

const entityKinds = [
  "run",
  "packet",
  "writeback",
  "finding",
  "prompt_template",
  "prompt_use",
  "skill",
  "workflow",
  "knowledge_object",
  "route_decision",
  "delta_item",
  "backfill_task",
  "automation",
  "experiment",
  "divergent_run",
  "learning_pattern",
  "promotion_lifecycle_item",
] as const satisfies readonly EntityKind[];

export const operatorSearchRouter = createTRPCRouter({
  search: publicProcedure
    .input(
      z.object({
        query: z.string().max(200).default(""),
        kinds: z.array(z.enum(entityKinds)).optional(),
        projectId: z.string().min(1).nullable().optional(),
        limit: z.number().int().min(1).max(200).optional(),
      }),
    )
    .query(({ ctx, input }): OperatorSearchHit[] =>
      searchEntities(ctx.db, {
        query: input.query,
        kinds: input.kinds,
        projectId: input.projectId ?? null,
        limit: input.limit,
      }),
    ),
});
