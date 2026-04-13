import { formatPercent, formatTokens } from "@/lib/format";
import type { CostSummary, Session } from "@/lib/types";

import { StatCard } from "@/components/primitives/StatCard";

type HealthGridProps = {
  sessions: Session[];
  costs: CostSummary;
};

export function HealthGrid({ sessions, costs }: HealthGridProps): React.JSX.Element {
  const openCount = sessions.filter((session) => session.status === "open").length;
  const abandonedCount = sessions.filter((session) => session.status === "abandoned").length;
  const abandonRate = sessions.length > 0 ? abandonedCount / sessions.length : 0;

  return (
    <section className="grid grid-4">
      <StatCard label="Open Runs" value={openCount} status={openCount > 0 ? "warning" : "healthy"} />
      <StatCard label="Abandon Rate" value={formatPercent(abandonRate)} status={abandonRate > 0.15 ? "error" : "healthy"} />
      <StatCard
        label="Total Tokens"
        value={formatTokens(costs.totalTokens)}
        delta={6.4}
        trend="up"
        status="warning"
      />
      <StatCard
        label="Failed-Run Tokens"
        value={formatTokens(costs.failedRunTokens)}
        delta={-3.1}
        trend="down"
        status="healthy"
      />
    </section>
  );
}
