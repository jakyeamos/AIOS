"use client";

import { useMemo, useState } from "react";

import { StatusBadge } from "@/components/primitives/StatusBadge";
import type { ShadowCandidate } from "@/lib/control-plane";
import { trpc } from "@/lib/trpc";

type ShadowCandidateQueueProps = {
  candidates: ShadowCandidate[];
  projectId?: string | null;
};

const recommendationTone = (recommendation: string): "healthy" | "warning" | "error" | "unknown" => {
  if (recommendation.includes("excellent") || recommendation.includes("good")) return "healthy";
  if (recommendation.includes("possible")) return "warning";
  return "unknown";
};

export function ShadowCandidateQueue({ candidates, projectId = null }: ShadowCandidateQueueProps): React.JSX.Element | null {
  const utils = trpc.useUtils();
  const [expanded, setExpanded] = useState(false);
  const visibleCandidates = useMemo(
    () => candidates.filter((candidate) => projectId === null || candidate.projectId === projectId),
    [candidates, projectId],
  );
  const approval = trpc.eval.approveShadowCandidate.useMutation({
    onSuccess: async () => {
      await Promise.all([
        utils.eval.shadowCandidates.invalidate(),
        projectId ? utils.eval.summaryForProject.invalidate({ projectId }) : Promise.resolve(),
      ]);
    },
  });

  if (visibleCandidates.length === 0) return null;

  return (
    <section className="panel-card">
      <div className="panel-row">
        <div>
          <h3 className="section-title">Shadow Candidate Queue</h3>
          <p className="panel-subtitle">{visibleCandidates.length} candidate(s) awaiting trace, review, or approval.</p>
        </div>
        <button type="button" className="button-secondary" onClick={() => setExpanded((value) => !value)}>
          {expanded ? "Collapse" : "Expand"}
        </button>
      </div>
      {expanded ? (
        <div className="stack" style={{ marginTop: "0.75rem" }}>
          {visibleCandidates.map((candidate) => (
            <article key={candidate.candidateId} className="entity-card">
              <div className="panel-row">
                <div>
                  <p className="panel-title">{candidate.candidateId}</p>
                  <p className="panel-subtitle">
                    score {candidate.score.toFixed(2)} · state {candidate.automationState}
                  </p>
                </div>
                <StatusBadge status={recommendationTone(candidate.recommendation)} label={candidate.recommendation} />
              </div>
              {candidate.reasons.length > 0 ? (
                <p className="entity-meta">reasons: {candidate.reasons.join(", ")}</p>
              ) : null}
              {candidate.blockers.length > 0 ? (
                <p className="entity-meta">blockers: {candidate.blockers.join(", ")}</p>
              ) : null}
              <button
                type="button"
                className="button-primary"
                disabled={approval.isPending || candidate.automationState === "APPROVED_IN_PERSON"}
                onClick={() => {
                  const confirmed = window.confirm(
                    `Approve ${candidate.candidateId} for shadow execution? This records an explicit human gate before automation continues.`,
                  );
                  if (confirmed) {
                    approval.mutate({ candidateId: candidate.candidateId });
                  }
                }}
              >
                {candidate.automationState === "APPROVED_IN_PERSON" ? "Approved" : "Approve"}
              </button>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
