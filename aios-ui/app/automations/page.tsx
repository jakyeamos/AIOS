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
        <div className="table-head table-automations">
          <span>Name</span>
          <span>Trigger</span>
          <span>Success Rate</span>
          <span>Status</span>
        </div>
        {automations.map((automation) => (
          <div key={automation.id} className="table-row table-automations">
            <span>{automation.name}</span>
            <span title={automation.triggerSignal.explanation}>
              {automation.triggerLabel}
              <br />
              <span className="signal-note mono">{automation.trigger}</span>
            </span>
            <span title={automation.successRateSignal.explanation}>
              {automation.successRate === null ? "Inspect history table" : formatPercent(automation.successRate)}
              <br />
              <span className="signal-note">
                {automation.successRateSignal.missingReason ?? automation.successRateSignal.provenance}
              </span>
            </span>
            <span>
              <StatusBadge status={automation.status} />
              <br />
              <span className="signal-note">
                {automation.urgency}
                {automation.lastFailureSummary ? `: ${automation.lastFailureSummary}` : ""}
              </span>
            </span>
          </div>
        ))}
      </section>
    </PageShell>
  );
}
