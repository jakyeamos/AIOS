import { AreaChart } from "@/components/charts/AreaChart";
import { BarChart } from "@/components/charts/BarChart";
import { PageShell } from "@/components/layout/PageShell";
import { CostBreakdown } from "@/components/panels/CostBreakdown";
import { StatCard } from "@/components/primitives/StatCard";
import { formatTokens } from "@/lib/format";
import { getCaller } from "@/server/caller";

export default async function CostsPage(): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const summary = await caller.costs.summary({ period: "week" });

  return (
    <PageShell title="Efficiency" subtitle="Token usage, waste signals, and trend by project/tool.">
      <div className="grid grid-3">
        <StatCard label="Total Tokens" value={formatTokens(summary.totalTokens)} />
        <StatCard label="Abandoned Session Tokens" value={formatTokens(summary.abandonedSessionTokens)} />
        <StatCard label="Failed Run Tokens" value={formatTokens(summary.failedRunTokens)} status="warning" />
      </div>
      <div className="grid grid-2">
        <BarChart
          data={summary.byProject.map((point) => ({ label: point.label, value: point.tokens }))}
          color="var(--chart-1)"
        />
        <AreaChart
          data={summary.byTool.map((point) => ({ label: point.label, value: point.tokens }))}
          color="var(--chart-2)"
        />
      </div>
      <div className="grid grid-3">
        <CostBreakdown title="By Project" rows={summary.byProject} />
        <CostBreakdown title="By Classification" rows={summary.byClassification} />
        <CostBreakdown title="By Tool" rows={summary.byTool} />
      </div>
    </PageShell>
  );
}
