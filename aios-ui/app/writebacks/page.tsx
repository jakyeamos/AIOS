/* eslint-disable anti-slop/require-empty-state-action */
import Link from "next/link";

import { PageShell } from "@/components/layout/PageShell";
import { formatDateTime } from "@/lib/format";
import { getCaller } from "@/server/caller";

export const dynamic = "force-dynamic";

export default async function WritebacksPage(): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const proposals = await caller.divergent.writebacks();

  return (
    <PageShell
      title="Memory Writebacks"
      subtitle="Approval-gated HOW, WHAT, FAILURE, and ENTROPY proposals from divergent strategy runs."
    >
      <section className="panel-card">
        <div className="table-head" style={{ gridTemplateColumns: "0.9fr 0.7fr 0.7fr 0.8fr 1.5fr 1fr" }}>
          <span>Created</span>
          <span>Scope</span>
          <span>Type</span>
          <span>Status</span>
          <span>Rationale</span>
          <span>Run</span>
        </div>
        {proposals.length === 0 ? (
          <p className="panel-subtitle">No memory writeback proposals are stored yet.</p>
        ) : (
          proposals.map((proposal) => (
            <div
              key={proposal.id}
              className="table-row"
              style={{ gridTemplateColumns: "0.9fr 0.7fr 0.7fr 0.8fr 1.5fr 1fr" }}
            >
              <span>{formatDateTime(proposal.createdAt)}</span>
              <span>{proposal.targetScope}</span>
              <span>{proposal.proposalType}</span>
              <span title={proposal.statusExplanation}>{proposal.status}</span>
              <span>{proposal.rationale}</span>
              <span>
                <Link href={`/runs/divergent/${proposal.sourceRunId}`}>inspect evidence</Link>
              </span>
            </div>
          ))
        )}
      </section>
    </PageShell>
  );
}
