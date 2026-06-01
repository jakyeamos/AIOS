import { changesRouter } from "@/server/routers/changes";
import { controlPlaneRouter } from "@/server/routers/control-plane";
import { createTRPCRouter } from "@/server/trpc";
import { automationsRouter } from "@/server/routers/automations";
import { costsRouter } from "@/server/routers/costs";
import { divergentRouter } from "@/server/routers/divergent";
import { experimentsRouter } from "@/server/routers/experiments";
import { insightsRouter } from "@/server/routers/insights";
import { knowledgeRouter } from "@/server/routers/knowledge";
import { learningRouter } from "@/server/routers/learning";
import { patternsRouter } from "@/server/routers/patterns";
import { projectsRouter } from "@/server/routers/projects";
import { promptsRouter } from "@/server/routers/prompts";
import { queryRouter } from "@/server/routers/query";
import { sessionsRouter } from "@/server/routers/sessions";
import { workflowsRouter } from "@/server/routers/workflows";

export const appRouter = createTRPCRouter({
  changes: changesRouter,
  controlPlane: controlPlaneRouter,
  sessions: sessionsRouter,
  prompts: promptsRouter,
  costs: costsRouter,
  divergent: divergentRouter,
  knowledge: knowledgeRouter,
  learning: learningRouter,
  patterns: patternsRouter,
  projects: projectsRouter,
  query: queryRouter,
  experiments: experimentsRouter,
  workflows: workflowsRouter,
  automations: automationsRouter,
  insights: insightsRouter,
});

export type AppRouter = typeof appRouter;
