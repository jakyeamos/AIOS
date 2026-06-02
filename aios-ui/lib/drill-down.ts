/**
 * Centralized drill-down URL construction for operator-visible entities.
 *
 * Mirrors services/operator_search.py:_drill_down_for, services/next_action.py:_drill_down_for,
 * and services/daily_flow.py:_drill_down_for_step. Keeping URL construction in one place per
 * language closes Pitfall 5: route renames touch one Python helper and one TypeScript module.
 *
 * Every function returns an absolute path string starting with "/" so it can be used directly
 * as a Next.js Link href or in a row's drillDownPath field.
 */

export const runPath = (id: string): string => `/runs/${encodeURIComponent(id)}`;

export const packetPath = (id: string): string => `/control?packet=${encodeURIComponent(id)}`;

export const writebackPath = (id: string): string => `/writebacks#${encodeURIComponent(id)}`;

export const findingPath = (runId: string, findingId: string): string =>
  `/runs/${encodeURIComponent(runId)}?finding=${encodeURIComponent(findingId)}`;

export const promptTemplatePath = (id: string): string => `/prompts#${encodeURIComponent(id)}`;

export const promptUsePath = (id: string): string => `/prompts#use-${encodeURIComponent(id)}`;

export const skillPath = (key: string): string => `/workflows?skill=${encodeURIComponent(key)}`;

export const workflowPath = (key: string): string => `/workflows#${encodeURIComponent(key)}`;

export const knowledgePath = (id: string): string => `/knowledge#${encodeURIComponent(id)}`;

export const routeDecisionPath = (runId: string, routeId: string): string =>
  `/runs/${encodeURIComponent(runId)}?route=${encodeURIComponent(routeId)}`;

export const deltaItemPath = (projectId: string | null, deltaId: string): string =>
  projectId
    ? `/projects/${encodeURIComponent(projectId)}?delta=${encodeURIComponent(deltaId)}`
    : `/projects?delta=${encodeURIComponent(deltaId)}`;

export const backfillTaskPath = (projectId: string | null, taskId: string): string =>
  projectId
    ? `/projects/${encodeURIComponent(projectId)}?backfill=${encodeURIComponent(taskId)}`
    : `/projects?backfill=${encodeURIComponent(taskId)}`;

export const automationPath = (id: string): string => `/automations#${encodeURIComponent(id)}`;

export const experimentPath = (id: string): string => `/experiments#${encodeURIComponent(id)}`;

export const divergentRunPath = (id: string): string => `/divergent#${encodeURIComponent(id)}`;

export const learningPatternPath = (id: string): string =>
  `/control?pattern=${encodeURIComponent(id)}`;

export const promotionLifecycleItemPath = (id: string): string =>
  `/workflows?promotion=${encodeURIComponent(id)}`;

export const goalSearchPath = (objective: string): string =>
  `/search?query=${encodeURIComponent(objective)}`;
