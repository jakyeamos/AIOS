import { GroundedQueryStudio } from "@/components/query/GroundedQueryStudio";
import { DailyFlowTrace } from "@/components/daily-flow/DailyFlowTrace";
import { ShadowCandidateQueue } from "@/components/eval/ShadowCandidateQueue";
import { NextActionPanel } from "@/components/next-action/NextActionPanel";
import { PhaseStatusBanner } from "@/components/command-center/PhaseStatusBanner";
import { SeedDataBanner } from "@/components/command-center/SeedDataBanner";
import { PageShell } from "@/components/layout/PageShell";
import { ProvenanceBadge } from "@/components/primitives/ProvenanceBadge";
import { StatCard } from "@/components/primitives/StatCard";
import { StatusBadge } from "@/components/primitives/StatusBadge";
import { formatDateTime } from "@/lib/format";
import {
  assessRunStatus,
  assessWritebackStatus,
  buildAttentionAlerts,
  buildCommandCenterTimeline,
} from "@/lib/status-provenance";
import { getCaller } from "@/server/caller";

type SeedCatalogRow = {
  isSeedData?: boolean;
};

const countSeedDataRows = (overview: {
  workflowTemplates: SeedCatalogRow[];
  agentProfiles: SeedCatalogRow[];
  invocationBackends: SeedCatalogRow[];
}): number =>
  [
    ...overview.workflowTemplates,
    ...overview.agentProfiles,
    ...overview.invocationBackends,
  ].filter((row) => row.isSeedData === true).length;

export default async function CommandCenterPage(): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const [overview, changes, automations, experiments, shadowCandidates] = await Promise.all([
    caller.controlPlane.overview(),
    caller.changes.list({ limit: 12 }),
    caller.automations.list(),
    caller.experiments.list(),
    caller.eval.shadowCandidates(),
  ]);

  const referenceTimestamps = [
    ...overview.runs.map((run) => run.updatedAt ?? run.createdAt),
    ...overview.pendingWritebacks.map((writeback) => writeback.updatedAt),
    ...changes.map((change) => change.timestamp),
    ...experiments.map((experiment) => experiment.endedAt ?? experiment.startedAt),
  ]
    .map((value) => Date.parse(value))
    .filter((value) => Number.isFinite(value));
  const nowMs = referenceTimestamps.length > 0 ? Math.max(...referenceTimestamps) : 0;
  const runRows = overview.runs.map((run) => ({
    run,
    status: assessRunStatus(run, nowMs),
  }));
  const writebackRows = overview.pendingWritebacks.map((writeback) => ({
    writeback,
    status: assessWritebackStatus(writeback, nowMs),
  }));

  const alerts = buildAttentionAlerts(overview.runs, overview.pendingWritebacks, automations);
  const timeline = buildCommandCenterTimeline({
    runs: overview.runs,
    writebacks: overview.pendingWritebacks,
    changes,
    experiments,
  }).slice(0, 20);

  const activeRuns = overview.runs.filter((run) => ["planned", "ready", "in_progress"].includes(run.status));
  const staleRuns = runRows.filter((row) => row.status.provenance === "stale");
  const failedRuns = overview.runs.filter((run) => run.status === "failed");
  const erroredAutomations = automations.filter((automation) => automation.status === "error");
  const activeExperiments = experiments.filter((experiment) => experiment.endedAt === null);

  const systemTone: "healthy" | "warning" | "error" =
    failedRuns.length > 0 || erroredAutomations.length > 0
      ? "error"
      : staleRuns.length > 0 || writebackRows.length > 0
        ? "warning"
        : "healthy";

  return (
    <PageShell
      title="Command Center"
      subtitle="Source-backed system awareness across runs, approvals, experiments, automations, and recent change lineage."
    >
      <PhaseStatusBanner phaseStatus={overview.phaseStatus ?? []} />
      <SeedDataBanner seedDataCount={countSeedDataRows(overview)} />

      <div className="grid grid-4">
        <StatCard label="System Health" value={systemTone.toUpperCase()} status={systemTone} />
        <StatCard label="Active Runs" value={activeRuns.length} status={activeRuns.length > 0 ? "warning" : "healthy"} />
        <StatCard label="Pending Approvals" value={writebackRows.length} status={writebackRows.length > 0 ? "warning" : "healthy"} />
        <StatCard label="Stale Signals" value={staleRuns.length} status={staleRuns.length > 0 ? "warning" : "healthy"} />
      </div>

      <div className="grid grid-3">
        <StatCard label="Failed Runs" value={failedRuns.length} status={failedRuns.length > 0 ? "error" : "healthy"} />
        <StatCard
          label="Automation Errors"
          value={erroredAutomations.length}
          status={erroredAutomations.length > 0 ? "error" : "healthy"}
        />
        <StatCard
          label="Active Experiments"
          value={activeExperiments.length}
          status={activeExperiments.length > 0 ? "warning" : "healthy"}
        />
      </div>

      <div className="grid grid-2">
        <NextActionPanel actions={overview.nextActions ?? []} projectId={null} />
        {overview.dailyFlowSummary ? (
          <DailyFlowTrace trace={overview.dailyFlowSummary} />
        ) : (
          <section className="panel-card">
            <h3 className="section-title">Daily Flow Trace</h3>
            <p className="panel-subtitle">Daily-flow data is being populated. Open a run after execution to replay the trace.</p>
          </section>
        )}
      </div>

      <section className="panel-card">
        <h3 className="section-title">Learning Impact Rollup</h3>
        <div className="stack">
          {overview.learningImpactRollup.length > 0 ? (
            overview.learningImpactRollup.map((rollup) => (
              <article key={`${rollup.scope}-${rollup.key}`} className="entity-card">
                <div className="panel-row">
                  <p className="panel-title">{rollup.key}</p>
                  <a href={rollup.drillDownPath} className="button-secondary">Drill in</a>
                </div>
                <p className="entity-meta">
                  samples {rollup.sample_size} · trend {rollup.trend} · success{" "}
                  {rollup.success_rate_30d === null ? "insufficient data" : rollup.success_rate_30d.toFixed(2)}
                </p>
              </article>
            ))
          ) : (
            <article className="entity-card">
              <p className="panel-subtitle">Learning impact rows are being populated by workflow execution reports.</p>
            </article>
          )}
        </div>
      </section>

      <section className="panel-card">
        <h3 className="section-title">Needs Attention Now</h3>
        <div className="alert-list">
          {alerts.map((alert) => (
            <article key={alert.id} className={`alert-item alert-${alert.severity}`}>
              <div className="panel-row">
                <h4>{alert.title}</h4>
                <StatusBadge
                  status={alert.severity === "error" ? "error" : alert.severity === "warning" ? "warning" : "unknown"}
                  label={alert.severity}
                />
              </div>
              <p>{alert.detail}</p>
              <p className="entity-meta">source: {alert.source}</p>
            </article>
          ))}
        </div>
      </section>

      <ShadowCandidateQueue candidates={shadowCandidates} />

      <div className="grid grid-2">
        <section className="panel-card">
          <h3 className="section-title">Workflow + Run Observability</h3>
          <div className="stack">
            {runRows.slice(0, 10).map(({ run, status }) => (
              <article key={run.id} className="entity-card">
                <div className="panel-row">
                  <p className="panel-title">{run.objective}</p>
                  <div className="badge-row">
                    <StatusBadge status={status.tone} label={run.status} />
                    <ProvenanceBadge level={status.provenance} source={status.source} reason={status.reason} />
                  </div>
                </div>
                <p className="panel-subtitle">
                  {run.projectName} · {run.workflowKey} · {run.agentKey}
                </p>
                <p className="entity-meta">
                  run: {run.id} · invocation: {run.activeInvocationId ?? "none"} · session: {run.sessionId ?? "none"}
                </p>
                <p className="entity-meta">
                  last update: {formatDateTime(status.observedAt ?? run.updatedAt)}
                  {status.stalenessMinutes !== null ? ` · age ${status.stalenessMinutes}m` : ""}
                </p>
                {run.supersededByRunId ? <p className="entity-meta">superseded by: {run.supersededByRunId}</p> : null}
                {run.resultSummary ? <p className="entity-meta">result: {run.resultSummary}</p> : null}
              </article>
            ))}
          </div>
        </section>

        <section className="panel-card">
          <h3 className="section-title">Approvals + Interventions Inbox</h3>
          <div className="stack">
            {writebackRows.length > 0 ? (
              writebackRows.map(({ writeback, status }) => (
                <article key={writeback.id} className="entity-card">
                  <div className="panel-row">
                    <p className="panel-title">{writeback.title}</p>
                    <div className="badge-row">
                      <StatusBadge status={status.tone} label={writeback.status} />
                      <ProvenanceBadge level={status.provenance} source={status.source} reason={status.reason} />
                    </div>
                  </div>
                  <p className="panel-subtitle">{writeback.summary}</p>
                  <p className="entity-meta">
                    action: review decision needed · layer: {writeback.layerType}/{writeback.layerKey}
                  </p>
                  <p className="entity-meta">
                    updated: {formatDateTime(writeback.updatedAt)}
                    {status.stalenessMinutes !== null ? ` · age ${status.stalenessMinutes}m` : ""}
                  </p>
                  {writeback.approvalReason ? <p className="entity-meta">why gated: {writeback.approvalReason}</p> : null}
                </article>
              ))
            ) : (
              <article className="entity-card">
                <p className="panel-subtitle">No approvals are currently waiting for intervention.</p>
                <p className="entity-meta">source: improvement_writebacks</p>
              </article>
            )}
          </div>
        </section>
      </div>

      <section className="panel-card">
        <h3 className="section-title">Change Timeline</h3>
        <p className="panel-subtitle">Last 20 events across runs, writebacks, changes, and experiments — newest first.</p>
        <div className="stack">
          {timeline.map((entry) => (
            <article key={entry.id} className="timeline-entry">
              <div className="panel-row">
                <p className="panel-title">{entry.title}</p>
                <StatusBadge status="unknown" label={entry.kind} />
              </div>
              <p className="panel-subtitle">{entry.summary}</p>
              <p className="entity-meta">
                {formatDateTime(entry.timestamp)} · source: {entry.source}
              </p>
            </article>
          ))}
        </div>
      </section>

      <section className="panel-card">
        <h3 className="section-title">Ask AIOS</h3>
        <p className="panel-subtitle">Answers are derived from your AIOS database — facts, inferences, and citations from sessions, changes, and project state.</p>
        <GroundedQueryStudio
          projects={Array.from(
            new Map(
              overview.runs
                .filter((run) => run.projectId !== null)
                .map((run) => [run.projectId, { id: run.projectId as string, name: run.projectName }]),
            ).values(),
          )}
        />
      </section>
    </PageShell>
  );
}
