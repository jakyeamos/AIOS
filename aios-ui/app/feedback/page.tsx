import { PageShell } from "@/components/layout/PageShell";
import { StatCard } from "@/components/primitives/StatCard";
import { StatusBadge } from "@/components/primitives/StatusBadge";
import { formatPercent } from "@/lib/format";
import { getCaller } from "@/server/caller";

export const dynamic = "force-dynamic";

const formatMetricValue = (metricKey: string, value: number | null): string => {
  if (value === null) {
    return "-";
  }

  if (
    metricKey === "abandon_rate" ||
    metricKey === "open_run_rate" ||
    metricKey === "first_pass_success" ||
    metricKey === "prompt_reuse_rate" ||
    metricKey === "error_event_rate"
  ) {
    return formatPercent(value);
  }

  return value.toFixed(2);
};

export default async function FeedbackPage(): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const snapshot = await caller.insights.snapshot();

  const errorCount = snapshot.metrics.filter((metric) => metric.status === "error").length;
  const warningCount = snapshot.metrics.filter((metric) => metric.status === "warning").length;
  const healthyCount = snapshot.metrics.filter((metric) => metric.status === "healthy").length;

  return (
    <PageShell
      title="Alignment"
      subtitle="Expectation gaps, value concentration, and ranked recommendations."
    >
      <div className="grid grid-4">
        <StatCard label="Healthy Metrics" value={healthyCount} status="healthy" />
        <StatCard label="Warning Metrics" value={warningCount} status="warning" />
        <StatCard label="Error Metrics" value={errorCount} status="error" />
        <StatCard label="Recommendations" value={snapshot.recommendations.length} />
      </div>

      <section className="panel-card">
        <h3 className="section-title">Expectation Health</h3>
        <div className="table-head table-metrics">
          <span>Metric</span>
          <span>Actual</span>
          <span>Target</span>
          <span>Status</span>
          <span>Delta</span>
          <span>Interpretation</span>
        </div>
        {snapshot.metrics.map((metric) => (
          <div key={metric.metricKey} className="table-row table-metrics">
            <span>{metric.label}</span>
            <span>{formatMetricValue(metric.metricKey, metric.actualValue)}</span>
            <span>{formatMetricValue(metric.metricKey, metric.targetValue)}</span>
            <span>
              <StatusBadge status={metric.status} />
            </span>
            <span>{metric.deltaFromTarget === null ? "-" : metric.deltaFromTarget.toFixed(3)}</span>
            <span>{metric.explanation}</span>
          </div>
        ))}
      </section>

      <div className="grid grid-2">
        <section className="panel-card">
          <h3 className="section-title">Value by Project</h3>
          <div className="table-head table-value-project">
            <span>Project</span>
            <span>Runs</span>
            <span>Score</span>
            <span>Token ROI</span>
            <span>Minute ROI</span>
          </div>
          {snapshot.valueByProject.map((project) => (
            <div key={project.projectId} className="table-row table-value-project">
              <span>{project.projectName}</span>
              <span>{project.runCount}</span>
              <span>{project.averageScore.toFixed(1)}</span>
              <span>{project.estimatedTokensSaved}</span>
              <span>{project.estimatedMinutesSaved}</span>
            </div>
          ))}
        </section>

        <section className="panel-card">
          <h3 className="section-title">Value by Workflow Signal</h3>
          <div className="table-head table-workflows">
            <span>Signal</span>
            <span>Runs</span>
            <span>Score</span>
          </div>
          {snapshot.valueByWorkflow.map((workflow) => (
            <div key={workflow.workflowName} className="table-row table-workflows">
              <span>{workflow.workflowName}</span>
              <span>{workflow.runCount}</span>
              <span>{workflow.score.toFixed(1)}</span>
            </div>
          ))}
        </section>
      </div>

      <section className="panel-card">
        <h3 className="section-title">Top Value Runs</h3>
        <div className="table-head table-runs-value">
          <span>Run</span>
          <span>Project</span>
          <span>Status</span>
          <span>Score</span>
          <span>Token ROI</span>
          <span>Minute ROI</span>
        </div>
        {snapshot.topRuns.map((run) => (
          <div key={run.sessionId} className="table-row table-runs-value">
            <span title={run.sessionId}>{run.objective ?? <span className="mono">{run.sessionId.slice(0, 8)}&hellip;</span>}</span>
            <span>{run.projectName}</span>
            <span>{run.status}</span>
            <span>{run.score.toFixed(1)}</span>
            <span>{run.estimatedTokensSaved}</span>
            <span>{run.estimatedMinutesSaved}</span>
          </div>
        ))}
      </section>

      <section className="panel-card">
        <h3 className="section-title">Priority Improvements</h3>
        <div className="table-head table-recommendations">
          <span>Priority</span>
          <span>Recommendation</span>
          <span>Rationale</span>
          <span>Action</span>
          <span>Confidence</span>
          <span>Token ROI</span>
          <span>Minute ROI</span>
          <span>Evidence</span>
        </div>
        {snapshot.recommendations.map((recommendation) => (
          <div key={recommendation.id} className="table-row table-recommendations">
            <span>{recommendation.priority}</span>
            <span>{recommendation.title}</span>
            <span>{recommendation.rationale}</span>
            <span>{recommendation.action}</span>
            <span>{recommendation.confidence.toFixed(2)}</span>
            <span>{recommendation.estimatedTokenRoi}</span>
            <span>{recommendation.estimatedMinutesRoi}</span>
            <span>
              {recommendation.sessionEvidence.slice(0, 2).map((item) => (
                <span key={item.sessionId} style={{ display: "block", whiteSpace: "nowrap" }}>
                  <a href={`/runs/${item.sessionId}`} title={item.sessionId}>
                    {item.sessionId.slice(0, 8)}&hellip;
                  </a>
                  {" "}
                  <span className="text-muted">{item.projectName}</span>
                  {" · "}
                  <span className="text-muted">{item.detail}</span>
                </span>
              ))}
              {recommendation.sessionEvidence.length === 0 && (
                <span className="text-muted">—</span>
              )}
            </span>
          </div>
        ))}
      </section>
    </PageShell>
  );
}
