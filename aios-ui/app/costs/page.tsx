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
      <div className="grid grid-3">
        <StatCard label="RTK State" value={summary.rtk.state.replaceAll("_", " ")} />
        <StatCard label="RTK Tokens Saved" value={formatTokens(summary.rtk.tokensSaved)} />
        <StatCard label="RTK Reduction" value={`${summary.rtk.reductionPercent.toFixed(1)}%`} />
      </div>
      <section className="panel-card">
        <p className="panel-title">RTK Signal</p>
        <p className="panel-subtitle">{summary.rtk.stateSignal.explanation}</p>
        <p className="entity-meta">
          {summary.rtk.stateSignal.provenance} · {summary.rtk.eventCount} event(s) · raw {formatTokens(summary.rtk.rawTokens)} · compressed {formatTokens(summary.rtk.compressedTokens)}
        </p>
      </section>
      <div className="grid grid-3">
        <StatCard label="RTK Ambiguous Failures" value={summary.rtk.ambiguousFailures} status="warning" />
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
      <div className="grid grid-2">
        <CostBreakdown title="RTK Savings By Workflow" rows={summary.rtk.byWorkflow} />
      </div>
    </PageShell>
  );
}
