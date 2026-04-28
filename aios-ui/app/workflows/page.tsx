import Link from "next/link";

import { PageShell } from "@/components/layout/PageShell";
import { StatCard } from "@/components/primitives/StatCard";
import { formatPercent, formatTokens } from "@/lib/format";
import { getCaller } from "@/server/caller";

export default async function WorkflowsPage(): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const workflows = await caller.workflows.list();
  const proposals = await caller.workflows.proposals();
  const pendingProposalCount = proposals.filter((proposal) => proposal.status === "pending_approval").length;

  return (
    <PageShell title="Workflows" subtitle="Reusable systems ranked by usage, reliability, and pending synthesis review.">
      <section className="panel-card">
        <h3 className="section-title">Workflow Proposals</h3>
        <div className="table-head">
          <span>Proposal</span>
          <span>Status</span>
          <span>Evidence</span>
          <span>Created</span>
        </div>
        {proposals.length > 0 ? (
          proposals.map((proposal) => (
            <div key={proposal.id} className="table-row">
              <span>
                <Link href={`/workflows/${proposal.id}`}>
                  <strong>{proposal.title}</strong>
                </Link>
                <br />
                <span className="text-muted">{proposal.summary}</span>
              </span>
              <span className="mono">{proposal.status}</span>
              <span className="text-muted">{proposal.evidence[0] ?? proposal.sourcePatternIds[0] ?? "No evidence recorded"}</span>
              <span className="mono">{new Date(proposal.createdAt).toLocaleString()}</span>
            </div>
          ))
        ) : (
          <div className="table-row">
            <span>Run workflow synthesis to create review proposals.</span>
            <span className="mono">action required</span>
            <span className="text-muted">Run `bin/synthesize-workflows.py` to create review candidates.</span>
            <span className="mono">-</span>
          </div>
        )}
      </section>
      <section className="panel-card">
        <h3 className="section-title">Registered Workflow Metrics</h3>
        <div className="table-head">
          <span>Name</span>
          <span>Runs</span>
          <span>Success</span>
          <span>Avg Tokens</span>
        </div>
        {workflows.map((workflow) => (
          <div key={workflow.id} className="table-row">
            <span>{workflow.name}</span>
            <span>{workflow.runs}</span>
            <span>{formatPercent(workflow.successRate)}</span>
            <span>{formatTokens(workflow.avgTokens)}</span>
          </div>
        ))}
      </section>
      <div className="grid grid-3">
        <StatCard label="Workflow Count" value={workflows.length} />
        <StatCard label="Pending Proposals" value={pendingProposalCount} />
        <StatCard
          label="Avg Success"
          value={
            formatPercent(
              workflows.length > 0
                ? workflows.reduce((total, workflow) => total + workflow.successRate, 0) / workflows.length
                : 0,
            )
          }
        />
      </div>
    </PageShell>
  );
}
