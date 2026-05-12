import Link from "next/link";

import { PageShell } from "@/components/layout/PageShell";
import { formatDateTime } from "@/lib/format";
import { getCaller } from "@/server/caller";

export const dynamic = "force-dynamic";

export default async function DivergentRunsPage(): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const runs = await caller.divergent.runs();

  return (
    <PageShell
      title="Divergent Strategy Runs"
      subtitle="Candidate portfolios, judge results, entropy signals, and gated memory proposals."
    >
      <section className="panel-card">
        <div className="table-head" style={{ gridTemplateColumns: "1.1fr 1.6fr 0.7fr 0.8fr 0.8fr 0.8fr" }}>
          <span>Created</span>
          <span>Task</span>
          <span>Mode</span>
          <span>Status</span>
          <span>Entropy</span>
          <span>Evidence</span>
        </div>
        {runs.length === 0 ? (
          <p className="panel-subtitle">
            No divergent strategy runs are stored yet. Create one through the workflow service or CLI wrapper.
          </p>
        ) : (
          runs.map((run) => (
            <div
              key={run.id}
              className="table-row"
              style={{ gridTemplateColumns: "1.1fr 1.6fr 0.7fr 0.8fr 0.8fr 0.8fr" }}
            >
              <span>{formatDateTime(run.createdAt)}</span>
              <span>
                <Link href={`/runs/divergent/${run.id}`}>{run.sourceTask}</Link>
              </span>
              <span>{run.mode}</span>
              <span title={run.statusExplanation}>{run.status}</span>
              <span title={run.entropyExplanation}>
                {run.entropyScore === null ? "unmeasured" : run.entropyScore.toFixed(2)}
              </span>
              <span>
                {run.candidateCount} candidates / {run.judgmentCount} judgments / {run.writebackCount} writebacks
              </span>
            </div>
          ))
        )}
      </section>
    </PageShell>
  );
}
