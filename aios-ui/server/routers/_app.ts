import { createTRPCRouter } from "@/server/trpc";
import { automationsRouter } from "@/server/routers/automations";
import { costsRouter } from "@/server/routers/costs";
import { experimentsRouter } from "@/server/routers/experiments";
import { insightsRouter } from "@/server/routers/insights";
import { patternsRouter } from "@/server/routers/patterns";
import { projectsRouter } from "@/server/routers/projects";
import { promptsRouter } from "@/server/routers/prompts";
import { sessionsRouter } from "@/server/routers/sessions";
import { workflowsRouter } from "@/server/routers/workflows";

export const appRouter = createTRPCRouter({
  sessions: sessionsRouter,
  prompts: promptsRouter,
  costs: costsRouter,
  patterns: patternsRouter,
  projects: projectsRouter,
  experiments: experimentsRouter,
  workflows: workflowsRouter,
  automations: automationsRouter,
  insights: insightsRouter,
});

export type AppRouter = typeof appRouter;
