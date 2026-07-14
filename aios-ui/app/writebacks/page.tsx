import Link from "next/link";

import { PageShell } from "@/components/layout/PageShell";
import { formatDateTime } from "@/lib/format";
import { getCaller } from "@/server/caller";

export const dynamic = "force-dynamic";

type SearchParams = Record<string, string | string[] | undefined>;

const firstValue = (value: string | string[] | undefined): string | undefined =>
  Array.isArray(value) ? value[0] : value;

export default async function WritebacksPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const query = await searchParams;
  const status = firstValue(query.status) ?? "pending_approval";
  const policyClass = firstValue(query.policyClass);
  const source = firstValue(query.source);
  const projectId = firstValue(query.projectId);
  const proposals = await caller.writebacks.list({
    status,
    policyClass,
    source,
    projectId,
    limit: 100,
  });

  return (
    <PageShell
      title="Memory Writebacks"
      subtitle="Approval-gated writebacks from governed runs, learning proposals, and promotion workflows."
    >
      <form className="toolbar" method="get">
        <label>
          Status
          <select name="status" defaultValue={status}>
            <option value="pending_approval">pending approval</option>
            <option value="proposed">proposed</option>
            <option value="applied">applied</option>
            <option value="rejected">rejected</option>
          </select>
        </label>
        <label>
          Policy Class
          <input name="policyClass" defaultValue={policyClass} placeholder="truth_update" />
        </label>
        <label>
          Source
          <input name="source" defaultValue={source} placeholder="learning_analysis" />
        </label>
        <label>
          Project
          <input name="projectId" defaultValue={projectId} placeholder="optional project id" />
        </label>
        <button type="submit">Apply filters</button>
      </form>
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
          <p className="panel-subtitle">No pending approvals match these filters. Adjust status, policy class, or source.</p>
        ) : (
          proposals.map((proposal) => (
            <div
              key={proposal.id}
              className="table-row"
              style={{ gridTemplateColumns: "0.9fr 0.7fr 0.7fr 0.8fr 1.5fr 1fr" }}
            >
              <span>{formatDateTime(proposal.createdAt)}</span>
              <span>{proposal.impactScope}</span>
              <span>{proposal.layerType}</span>
              <span>{proposal.status}</span>
              <span>{proposal.summary}</span>
              <span>
                <Link href={proposal.drillDownPath}>inspect evidence</Link>
              </span>
            </div>
          ))
        )}
      </section>
    </PageShell>
  );
}
