import { PageShell } from "@/components/layout/PageShell";
import { StatCard } from "@/components/primitives/StatCard";
import { formatPercent, formatTokens } from "@/lib/format";
import { getCaller } from "@/server/caller";

export default async function WorkflowsPage(): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const workflows = await caller.workflows.list();

  return (
    <PageShell title="Workflows" subtitle="Reusable systems ranked by usage and reliability.">
      <section className="panel-card">
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
        <StatCard
          label="Avg Tokens"
          value={
            formatTokens(
              workflows.length > 0
                ? Math.round(workflows.reduce((total, workflow) => total + workflow.avgTokens, 0) / workflows.length)
                : 0,
            )
          }
        />
      </div>
    </PageShell>
  );
}
