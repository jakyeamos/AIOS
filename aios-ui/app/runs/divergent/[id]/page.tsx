import { notFound } from "next/navigation";

import { PageShell } from "@/components/layout/PageShell";
import { formatDateTime } from "@/lib/format";
import { getCaller } from "@/server/caller";

const labelForPortfolioKey = (key: string): string =>
  key
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");

const score = (value: number): string => value.toFixed(2);

export default async function DivergentRunDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<React.JSX.Element> {
  const { id } = await params;
  const caller = await getCaller();
  const run = await caller.divergent.detail({ id });

  if (!run) {
    notFound();
  }

  const candidateById = new Map(run.candidates.map((candidate) => [candidate.id, candidate]));

  return (
    <PageShell title="Divergent Strategy Detail" subtitle={run.sourceTask}>
      <div className="grid grid-2">
        <section className="panel-card">
          <h3 className="section-title">Run State</h3>
          <div className="stack">
            <p className="panel-title">{run.status}</p>
            <p className="panel-subtitle">{run.statusExplanation}</p>
            <p className="panel-subtitle">Created {formatDateTime(run.createdAt)}</p>
            <p className="panel-subtitle">Mode: {run.mode}</p>
            <p className="panel-subtitle">Quality: {run.qualityScore?.toFixed(2) ?? "unmeasured"}</p>
            <p className="panel-subtitle">{run.qualityExplanation}</p>
          </div>
        </section>

        <section className="panel-card">
          <h3 className="section-title">Entropy</h3>
          {run.entropy ? (
            <div className="stack">
              <p className="panel-title">Diversity {score(run.entropy.diversityScore)}</p>
              <p className="panel-subtitle">Novelty {score(run.entropy.noveltyScore)}</p>
              <p className="panel-subtitle">{run.entropy.recommendation}</p>
              <p className="panel-subtitle">Formula: {run.entropy.formula}</p>
            </div>
          ) : (
            <p className="panel-subtitle">No entropy observation was stored for this run.</p>
          )}
        </section>
      </div>

      <section className="panel-card">
        <h3 className="section-title">Portfolio</h3>
        <div className="table-head" style={{ gridTemplateColumns: "1fr 1.5fr 2fr" }}>
          <span>Slot</span>
          <span>Candidate</span>
          <span>Why Inspect It</span>
        </div>
        {Object.entries(run.portfolio).map(([key, candidateId]) => {
          const candidate = candidateId ? candidateById.get(candidateId) : undefined;
          return (
            <div key={key} className="table-row" style={{ gridTemplateColumns: "1fr 1.5fr 2fr" }}>
              <span>{labelForPortfolioKey(key)}</span>
              <span>{candidate?.name ?? "not selected"}</span>
              <span>{candidate?.formulation ?? "No candidate stored for this portfolio slot."}</span>
            </div>
          );
        })}
      </section>

      <section className="panel-card">
        <h3 className="section-title">Candidates</h3>
        <div className="stack">
          {run.candidates.map((candidate) => (
            <article key={candidate.id} className="timeline-event">
              <div className="panel-row">
                <p className="panel-title">{candidate.name}</p>
                <span>{candidate.selectedStatus}</span>
              </div>
              <p className="panel-subtitle">{candidate.formulation}</p>
              <p className="panel-subtitle">
                Novelty {score(candidate.noveltyScore)} · Usefulness {score(candidate.usefulnessScore)} · Feasibility{" "}
                {score(candidate.feasibilityScore)} · Risk {score(candidate.riskScore)}
              </p>
              <p className="panel-subtitle">
                Risk evidence: {candidate.weaknesses.length > 0 ? candidate.weaknesses.join("; ") : "none stored"}
              </p>
            </article>
          ))}
        </div>
      </section>

      <section className="panel-card">
        <h3 className="section-title">Judgments</h3>
        <div className="table-head" style={{ gridTemplateColumns: "1fr 1fr 0.5fr 1fr 2fr" }}>
          <span>Judge</span>
          <span>Candidate</span>
          <span>Score</span>
          <span>Verdict</span>
          <span>Rationale</span>
        </div>
        {run.judgments.map((judgment) => (
          <div key={judgment.id} className="table-row" style={{ gridTemplateColumns: "1fr 1fr 0.5fr 1fr 2fr" }}>
            <span>{judgment.judgeName}</span>
            <span>{judgment.candidateId ? candidateById.get(judgment.candidateId)?.name ?? "run-level" : "run-level"}</span>
            <span>{score(judgment.score)}</span>
            <span>{judgment.verdict}</span>
            <span>{judgment.critique}</span>
          </div>
        ))}
      </section>

      <section className="panel-card">
        <h3 className="section-title">Writeback Proposals</h3>
        <div className="stack">
          {run.writebacks.map((proposal) => (
            <article key={proposal.id} className="timeline-event">
              <div className="panel-row">
                <p className="panel-title">
                  {proposal.proposalType} → {proposal.targetScope}
                </p>
                <span title={proposal.statusExplanation}>{proposal.status}</span>
              </div>
              <p className="panel-subtitle">{proposal.rationale}</p>
              <pre className="code-block">{proposal.proposedContent}</pre>
            </article>
          ))}
        </div>
      </section>
    </PageShell>
  );
}
