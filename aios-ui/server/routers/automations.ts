import { seededAutomations } from "@/lib/seed";
import type { AutomationHealth } from "@/lib/types";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

export const automationsRouter = createTRPCRouter({
  list: publicProcedure.query((): AutomationHealth[] => seededAutomations),
});
