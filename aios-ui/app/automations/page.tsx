import { PageShell } from "@/components/layout/PageShell";
import { StatCard } from "@/components/primitives/StatCard";
import { StatusBadge } from "@/components/primitives/StatusBadge";
import { formatPercent } from "@/lib/format";
import { getCaller } from "@/server/caller";

export default async function AutomationsPage(): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const automations = await caller.automations.list();

  return (
    <PageShell title="Automations" subtitle="Hooks, triggers, and reliability over time.">
      <div className="grid grid-3">
        <StatCard label="Total Automations" value={automations.length} />
        <StatCard
          label="Healthy"
          value={automations.filter((automation) => automation.status === "healthy").length}
          status="healthy"
        />
        <StatCard
          label="Error"
          value={automations.filter((automation) => automation.status === "error").length}
          status="error"
        />
      </div>
      <section className="panel-card">
        <div className="table-head">
          <span>Name</span>
          <span>Trigger</span>
          <span>Success Rate</span>
          <span>Status</span>
        </div>
        {automations.map((automation) => (
          <div key={automation.id} className="table-row">
            <span>{automation.name}</span>
            <span className="mono">{automation.trigger}</span>
            <span>{formatPercent(automation.successRate)}</span>
            <span>
              <StatusBadge status={automation.status} />
            </span>
          </div>
        ))}
      </section>
    </PageShell>
  );
}
