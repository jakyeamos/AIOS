import { z } from "zod";

import { tableExists } from "@/server/db";
import { ensureControlPlaneSchema } from "@/server/aios/schema";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

type JsonRecord = Record<string, unknown>;

export type DivergentRunSummary = {
  id: string;
  createdAt: string;
  projectId: string | null;
  sourceTask: string;
  mode: string;
  status: string;
  statusExplanation: string;
  summary: string | null;
  entropyScore: number | null;
  entropyExplanation: string;
  qualityScore: number | null;
  qualityExplanation: string;
  candidateCount: number;
  judgmentCount: number;
  writebackCount: number;
};

export type DivergentCandidate = {
  id: string;
  name: string;
  role: string;
  formulation: string;
  output: JsonRecord;
  strengths: string[];
  weaknesses: string[];
  noveltyScore: number;
  usefulnessScore: number;
  feasibilityScore: number;
  riskScore: number;
  selectedStatus: string;
};

export type DivergentJudgment = {
  id: string;
  candidateId: string | null;
  judgeName: string;
  judgeRole: string;
  rubricUsed: string[];
  score: number;
  verdict: string;
  critique: string;
  recommendedAction: string;
};

export type MemoryWritebackProposal = {
  id: string;
  sourceRunId: string;
  targetScope: string;
  proposalType: string;
  proposedContent: string;
  rationale: string;
  evidence: unknown[];
  status: string;
  statusExplanation: string;
  createdAt: string;
  reviewedAt: string | null;
  reviewedBy: string | null;
};

export type EntropyObservation = {
  repeatedPatternDetected: boolean;
  repeatedJudges: boolean;
  repeatedCandidateShapes: boolean;
  noveltyScore: number;
  diversityScore: number;
  recommendation: string;
  formula: string;
};

export type PromotionLifecycleItem = {
  id: string;
  itemKind: string;
  itemKey: string;
  sourceRunId: string | null;
  status: string;
  evidence: unknown[];
  statusReason: string;
  updatedAt: string;
};

export type DivergentRunDetail = DivergentRunSummary & {
  taskClassification: JsonRecord;
  selectedWorkflowProfile: JsonRecord;
  finalRecommendation: string | null;
  portfolio: Record<string, string | null>;
  candidates: DivergentCandidate[];
  judgments: DivergentJudgment[];
  writebacks: MemoryWritebackProposal[];
  entropy: EntropyObservation | null;
};

const parseJson = (raw: string | null): unknown => {
  if (!raw) {
    return {};
  }

  try {
    return JSON.parse(raw) as unknown;
  } catch {
    return {};
  }
};

const parseRecord = (raw: string | null): JsonRecord => {
  const parsed = parseJson(raw);
  return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? (parsed as JsonRecord) : {};
};

const parseArray = (raw: string | null): unknown[] => {
  const parsed = parseJson(raw);
  return Array.isArray(parsed) ? parsed : [];
};

const parseStringArray = (raw: string | null): string[] =>
  parseArray(raw).filter((item): item is string => typeof item === "string");

const explainStatus = (status: string): string => {
  if (status === "completed") {
    return "Completed means candidates, judgments, entropy, and portfolio metadata were persisted.";
  }

  if (status === "proposed") {
    return "Proposed means no memory or prompt-library mutation has been applied yet.";
  }

  if (status === "approved") {
    return "Approved means a human or operator accepted the proposal; promotion still requires evidence.";
  }

  return "Inspect the linked evidence before treating this status as authoritative.";
};

type RunRow = {
  id: string;
  createdAt: string;
  projectId: string | null;
  sourceTask: string;
  mode: string;
  status: string;
  taskClassification: string;
  selectedWorkflowProfile: string;
  summary: string | null;
  finalRecommendation: string | null;
  entropyScore: number | null;
  qualityScore: number | null;
  metadataJson: string;
  candidateCount: number;
  judgmentCount: number;
  writebackCount: number;
};

const mapRunSummary = (row: RunRow): DivergentRunSummary => ({
  id: row.id,
  createdAt: row.createdAt,
  projectId: row.projectId,
  sourceTask: row.sourceTask,
  mode: row.mode,
  status: row.status,
  statusExplanation: explainStatus(row.status),
  summary: row.summary,
  entropyScore: row.entropyScore,
  entropyExplanation: "Heuristic diversity score: unique candidate shapes divided by total shapes.",
  qualityScore: row.qualityScore,
  qualityExplanation: "Heuristic average of persisted judge scores; not ground truth.",
  candidateCount: row.candidateCount,
  judgmentCount: row.judgmentCount,
  writebackCount: row.writebackCount,
});

const portfolioFromMetadata = (metadataJson: string): Record<string, string | null> => {
  const metadata = parseRecord(metadataJson);
  const portfolio = metadata.portfolio;
  if (!portfolio || typeof portfolio !== "object" || Array.isArray(portfolio)) {
    return {};
  }

  return Object.fromEntries(
    Object.entries(portfolio as Record<string, unknown>).map(([key, value]) => [
      key,
      typeof value === "string" ? value : null,
    ]),
  );
};

export const divergentRouter = createTRPCRouter({
  runs: publicProcedure.query(({ ctx }): DivergentRunSummary[] => {
    ensureControlPlaneSchema(ctx.db);
    if (!tableExists("divergent_runs")) {
      return [];
    }

    const rows = ctx.db
      .prepare(
        `
        SELECT
          r.id,
          r.created_at AS createdAt,
          r.project_id AS projectId,
          r.source_task AS sourceTask,
          r.mode,
          r.status,
          r.task_classification AS taskClassification,
          r.selected_workflow_profile AS selectedWorkflowProfile,
          r.summary,
          r.final_recommendation AS finalRecommendation,
          r.entropy_score AS entropyScore,
          r.quality_score AS qualityScore,
          r.metadata_json AS metadataJson,
          COUNT(DISTINCT c.id) AS candidateCount,
          COUNT(DISTINCT j.id) AS judgmentCount,
          COUNT(DISTINCT w.id) AS writebackCount
        FROM divergent_runs r
        LEFT JOIN divergent_candidates c ON c.run_id = r.id
        LEFT JOIN divergent_judgments j ON j.run_id = r.id
        LEFT JOIN memory_writeback_proposals w ON w.source_run_id = r.id
        GROUP BY r.id
        ORDER BY r.created_at DESC
        LIMIT 80
        `,
      )
      .all() as RunRow[];

    return rows.map(mapRunSummary);
  }),

  detail: publicProcedure
    .input(z.object({ id: z.string().min(1) }))
    .query(({ ctx, input }): DivergentRunDetail | null => {
      ensureControlPlaneSchema(ctx.db);
      const row = ctx.db
        .prepare(
          `
          SELECT
            r.id,
            r.created_at AS createdAt,
            r.project_id AS projectId,
            r.source_task AS sourceTask,
            r.mode,
            r.status,
            r.task_classification AS taskClassification,
            r.selected_workflow_profile AS selectedWorkflowProfile,
            r.summary,
            r.final_recommendation AS finalRecommendation,
            r.entropy_score AS entropyScore,
            r.quality_score AS qualityScore,
            r.metadata_json AS metadataJson,
            COUNT(DISTINCT c.id) AS candidateCount,
            COUNT(DISTINCT j.id) AS judgmentCount,
            COUNT(DISTINCT w.id) AS writebackCount
          FROM divergent_runs r
          LEFT JOIN divergent_candidates c ON c.run_id = r.id
          LEFT JOIN divergent_judgments j ON j.run_id = r.id
          LEFT JOIN memory_writeback_proposals w ON w.source_run_id = r.id
          WHERE r.id = ?
          GROUP BY r.id
          LIMIT 1
          `,
        )
        .get(input.id) as RunRow | undefined;

      if (!row) {
        return null;
      }

      const candidateRows = ctx.db
        .prepare(
          `
          SELECT
            id,
            candidate_name AS name,
            candidate_role AS role,
            formulation,
            output,
            strengths_json AS strengthsJson,
            weaknesses_json AS weaknessesJson,
            novelty_score AS noveltyScore,
            usefulness_score AS usefulnessScore,
            feasibility_score AS feasibilityScore,
            risk_score AS riskScore,
            selected_status AS selectedStatus
          FROM divergent_candidates
          WHERE run_id = ?
          ORDER BY selected_status, candidate_name
          `,
        )
        .all(row.id) as Array<{
        id: string;
        name: string;
        role: string;
        formulation: string;
        output: string;
        strengthsJson: string;
        weaknessesJson: string;
        noveltyScore: number;
        usefulnessScore: number;
        feasibilityScore: number;
        riskScore: number;
        selectedStatus: string;
      }>;

      const judgmentRows = ctx.db
        .prepare(
          `
          SELECT
            id,
            candidate_id AS candidateId,
            judge_name AS judgeName,
            judge_role AS judgeRole,
            rubric_used AS rubricUsed,
            score,
            verdict,
            critique,
            recommended_action AS recommendedAction
          FROM divergent_judgments
          WHERE run_id = ?
          ORDER BY judge_name, score DESC
          `,
        )
        .all(row.id) as DivergentJudgment[];

      const writebackRows = ctx.db
        .prepare(
          `
          SELECT
            id,
            source_run_id AS sourceRunId,
            target_scope AS targetScope,
            proposal_type AS proposalType,
            proposed_content AS proposedContent,
            rationale,
            evidence_json AS evidenceJson,
            status,
            created_at AS createdAt,
            reviewed_at AS reviewedAt,
            reviewed_by AS reviewedBy
          FROM memory_writeback_proposals
          WHERE source_run_id = ?
          ORDER BY created_at DESC
          `,
        )
        .all(row.id) as Array<Omit<MemoryWritebackProposal, "evidence" | "statusExplanation"> & { evidenceJson: string }>;

      const entropyRow = ctx.db
        .prepare(
          `
          SELECT
            repeated_pattern_detected AS repeatedPatternDetected,
            repeated_judges AS repeatedJudges,
            repeated_candidate_shapes AS repeatedCandidateShapes,
            novelty_score AS noveltyScore,
            diversity_score AS diversityScore,
            recommendation,
            metadata_json AS metadataJson
          FROM entropy_observations
          WHERE run_id = ?
          ORDER BY rowid DESC
          LIMIT 1
          `,
        )
        .get(row.id) as
        | {
            repeatedPatternDetected: number;
            repeatedJudges: number;
            repeatedCandidateShapes: number;
            noveltyScore: number;
            diversityScore: number;
            recommendation: string;
            metadataJson: string;
          }
        | undefined;

      return {
        ...mapRunSummary(row),
        taskClassification: parseRecord(row.taskClassification),
        selectedWorkflowProfile: parseRecord(row.selectedWorkflowProfile),
        finalRecommendation: row.finalRecommendation,
        portfolio: portfolioFromMetadata(row.metadataJson),
        candidates: candidateRows.map((candidate) => ({
          id: candidate.id,
          name: candidate.name,
          role: candidate.role,
          formulation: candidate.formulation,
          output: parseRecord(candidate.output),
          strengths: parseStringArray(candidate.strengthsJson),
          weaknesses: parseStringArray(candidate.weaknessesJson),
          noveltyScore: candidate.noveltyScore,
          usefulnessScore: candidate.usefulnessScore,
          feasibilityScore: candidate.feasibilityScore,
          riskScore: candidate.riskScore,
          selectedStatus: candidate.selectedStatus,
        })),
        judgments: judgmentRows.map((judgment) => ({
          ...judgment,
          rubricUsed: parseStringArray(String(judgment.rubricUsed)),
        })),
        writebacks: writebackRows.map((proposal) => ({
          id: proposal.id,
          sourceRunId: proposal.sourceRunId,
          targetScope: proposal.targetScope,
          proposalType: proposal.proposalType,
          proposedContent: proposal.proposedContent,
          rationale: proposal.rationale,
          evidence: parseArray(proposal.evidenceJson),
          status: proposal.status,
          statusExplanation: explainStatus(proposal.status),
          createdAt: proposal.createdAt,
          reviewedAt: proposal.reviewedAt,
          reviewedBy: proposal.reviewedBy,
        })),
        entropy: entropyRow
          ? {
              repeatedPatternDetected: entropyRow.repeatedPatternDetected === 1,
              repeatedJudges: entropyRow.repeatedJudges === 1,
              repeatedCandidateShapes: entropyRow.repeatedCandidateShapes === 1,
              noveltyScore: entropyRow.noveltyScore,
              diversityScore: entropyRow.diversityScore,
              recommendation: entropyRow.recommendation,
              formula:
                typeof parseRecord(entropyRow.metadataJson).formula === "string"
                  ? String(parseRecord(entropyRow.metadataJson).formula)
                  : "unique candidate shapes / total candidate shapes",
            }
          : null,
      };
    }),

  writebacks: publicProcedure.query(({ ctx }): MemoryWritebackProposal[] => {
    ensureControlPlaneSchema(ctx.db);
    const rows = ctx.db
      .prepare(
        `
        SELECT
          id,
          source_run_id AS sourceRunId,
          target_scope AS targetScope,
          proposal_type AS proposalType,
          proposed_content AS proposedContent,
          rationale,
          evidence_json AS evidenceJson,
          status,
          created_at AS createdAt,
          reviewed_at AS reviewedAt,
          reviewed_by AS reviewedBy
        FROM memory_writeback_proposals
        ORDER BY
          CASE status WHEN 'proposed' THEN 0 WHEN 'approved' THEN 1 ELSE 2 END,
          created_at DESC
        LIMIT 120
        `,
      )
      .all() as Array<Omit<MemoryWritebackProposal, "evidence" | "statusExplanation"> & { evidenceJson: string }>;

    return rows.map((row) => ({
      id: row.id,
      sourceRunId: row.sourceRunId,
      targetScope: row.targetScope,
      proposalType: row.proposalType,
      proposedContent: row.proposedContent,
      rationale: row.rationale,
      evidence: parseArray(row.evidenceJson),
      status: row.status,
      statusExplanation: explainStatus(row.status),
      createdAt: row.createdAt,
      reviewedAt: row.reviewedAt,
      reviewedBy: row.reviewedBy,
    }));
  }),

  promotionItems: publicProcedure.query(({ ctx }): PromotionLifecycleItem[] => {
    ensureControlPlaneSchema(ctx.db);
    const rows = ctx.db
      .prepare(
        `
        SELECT
          id,
          item_kind AS itemKind,
          item_key AS itemKey,
          source_run_id AS sourceRunId,
          status,
          evidence_json AS evidenceJson,
          status_reason AS statusReason,
          updated_at AS updatedAt
        FROM promotion_lifecycle_items
        ORDER BY updated_at DESC
        LIMIT 80
        `,
      )
      .all() as Array<Omit<PromotionLifecycleItem, "evidence"> & { evidenceJson: string }>;

    return rows.map((row) => ({
      id: row.id,
      itemKind: row.itemKind,
      itemKey: row.itemKey,
      sourceRunId: row.sourceRunId,
      status: row.status,
      evidence: parseArray(row.evidenceJson),
      statusReason: row.statusReason,
      updatedAt: row.updatedAt,
    }));
  }),
});
