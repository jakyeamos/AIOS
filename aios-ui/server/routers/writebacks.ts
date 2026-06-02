import { z } from "zod";

import { writebackPath } from "@/lib/drill-down";
import { tableExists } from "@/server/db";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

type WritebackListRow = {
  id: string;
  runId: string | null;
  projectId: string | null;
  layerType: string;
  layerKey: string;
  title: string;
  summary: string;
  impactScope: string;
  status: string;
  requiresApproval: number;
  createdAt: string;
  updatedAt: string;
};

type WritebackDetailRow = WritebackListRow & {
  evidenceJson: string;
  proposedChangeJson: string;
  approvalReason: string | null;
  decisionNote: string | null;
  decisionActor: string | null;
  decisionAt: string | null;
};

type WritebackEventRow = {
  id: string;
  writebackId: string;
  runId: string | null;
  eventType: string;
  fromStatus: string | null;
  toStatus: string | null;
  actor: string;
  note: string | null;
  metadataJson: string;
  createdAt: string;
};

const parseJson = <T>(raw: string | null, fallback: T): T => {
  if (!raw) {
    return fallback;
  }
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
};

const rowProjection = `
  id,
  run_id AS runId,
  project_id AS projectId,
  layer_type AS layerType,
  layer_key AS layerKey,
  title,
  summary,
  impact_scope AS impactScope,
  status,
  requires_approval AS requiresApproval,
  created_at AS createdAt,
  updated_at AS updatedAt
`;

const mapListRow = (row: WritebackListRow) => ({
  ...row,
  requiresApproval: row.requiresApproval === 1,
  drillDownPath: writebackPath(row.id),
});

export const writebacksRouter = createTRPCRouter({
  list: publicProcedure
    .input(
      z.object({
        status: z.string().min(1).max(40).optional(),
        projectId: z.string().min(1).nullable().optional(),
        policyClass: z.string().min(1).max(120).optional(),
        source: z.string().min(1).max(120).optional(),
        limit: z.number().int().min(1).max(200).default(50),
      }).optional(),
    )
    .query(({ ctx, input }) => {
      if (!tableExists("improvement_writebacks")) {
        return [];
      }
      const where: string[] = [];
      const params: unknown[] = [];
      if (input?.status) {
        where.push("status = ?");
        params.push(input.status);
      }
      if (input?.projectId) {
        where.push("project_id = ?");
        params.push(input.projectId);
      }
      if (input?.policyClass) {
        where.push("proposed_change_json LIKE ?");
        params.push(`%"policy_class"%${input.policyClass}%`);
      }
      if (input?.source) {
        where.push("proposed_change_json LIKE ?");
        params.push(`%"source"%${input.source}%`);
      }
      const whereSql = where.length > 0 ? `WHERE ${where.join(" AND ")}` : "";
      const rows = ctx.db
        .prepare(
          `
          SELECT ${rowProjection}
          FROM improvement_writebacks
          ${whereSql}
          ORDER BY updated_at DESC, created_at DESC
          LIMIT ?
          `,
        )
        .all(...params, input?.limit ?? 50) as WritebackListRow[];
      return rows.map(mapListRow);
    }),

  detail: publicProcedure
    .input(z.object({ id: z.string().min(1) }))
    .query(({ ctx, input }) => {
      if (!tableExists("improvement_writebacks")) {
        return null;
      }
      const row = ctx.db
        .prepare(
          `
          SELECT
            ${rowProjection},
            evidence_json AS evidenceJson,
            proposed_change_json AS proposedChangeJson,
            approval_reason AS approvalReason,
            decision_note AS decisionNote,
            decision_actor AS decisionActor,
            decision_at AS decisionAt
          FROM improvement_writebacks
          WHERE id = ?
          LIMIT 1
          `,
        )
        .get(input.id) as WritebackDetailRow | undefined;
      if (!row) {
        return null;
      }
      const events = tableExists("improvement_writeback_events")
        ? (ctx.db
            .prepare(
              `
              SELECT
                id,
                writeback_id AS writebackId,
                run_id AS runId,
                event_type AS eventType,
                from_status AS fromStatus,
                to_status AS toStatus,
                actor,
                note,
                metadata_json AS metadataJson,
                created_at AS createdAt
              FROM improvement_writeback_events
              WHERE writeback_id = ?
              ORDER BY created_at ASC
              `,
            )
            .all(input.id) as WritebackEventRow[])
        : [];
      return {
        ...mapListRow(row),
        evidence: parseJson<string[]>(row.evidenceJson, []),
        proposedChange: parseJson<Record<string, unknown>>(row.proposedChangeJson, {}),
        approvalReason: row.approvalReason,
        decisionNote: row.decisionNote,
        decisionActor: row.decisionActor,
        decisionAt: row.decisionAt,
        events: events.map((event) => ({
          ...event,
          metadata: parseJson<Record<string, unknown>>(event.metadataJson, {}),
        })),
      };
    }),
});
