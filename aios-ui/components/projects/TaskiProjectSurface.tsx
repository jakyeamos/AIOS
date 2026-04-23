"use client";

import { useState } from "react";

import type { KnowledgePageDetail, TaskiProjectSummary } from "@/lib/control-plane";
import { KnowledgePageView } from "@/components/knowledge/KnowledgePageView";
import { StatusBadge } from "@/components/primitives/StatusBadge";

const bucketLabel: Record<string, string> = {
  foundational: "foundational",
  high_leverage: "high leverage",
  quick_wins: "quick wins",
  blocked: "blocked",
  waived_deferred: "waived/deferred",
};

const standardsStatusTone = (status: string): "healthy" | "warning" | "error" | "unknown" => {
  if (status === "pass" || status === "waived") {
    return "healthy";
  }
  if (status === "fail") {
    return "error";
  }
  if (status === "partial") {
    return "warning";
  }
  return "unknown";
};

export function TaskiProjectSurface({
  summary,
  dossier,
}: {
  summary: TaskiProjectSummary;
  dossier: KnowledgePageDetail;
}): React.JSX.Element {
  const [tab, setTab] = useState<"taski" | "dossier">("taski");

  return (
    <div className="page-content">
      <section className="panel-card">
        <div className="panel-row">
          <div>
            <p className="topbar-eyebrow">Taski Project Surface</p>
            <h3 className="section-title">{summary.projectTitle}</h3>
            <p className="panel-subtitle">{summary.overview}</p>
          </div>
          <StatusBadge status={summary.status} label={summary.freshness} />
        </div>
        <div className="panel-row" style={{ gap: "0.75rem", marginTop: "1rem" }}>
          <button type="button" className={tab === "taski" ? "button-primary" : "button-secondary"} onClick={() => setTab("taski")}>
            Taski Summary
          </button>
          <button type="button" className={tab === "dossier" ? "button-primary" : "button-secondary"} onClick={() => setTab("dossier")}>
            Knowledge Dossier
          </button>
        </div>
      </section>

      {tab === "taski" ? (
        <div className="detail-grid">
          <section className="panel-card">
            <h3 className="section-title">Operating Summary</h3>
            <div className="stack">
              <article className="entity-card">
                <p className="panel-title">Suggested Next Actions</p>
                <ul className="detail-list">
                  {summary.suggestedNextActions.map((action) => (
                    <li key={action}>{action}</li>
                  ))}
                </ul>
              </article>
              <article className="entity-card">
                <p className="panel-title">Blockers</p>
                <ul className="detail-list">
                  {summary.blockers.length > 0 ? summary.blockers.map((blocker) => <li key={blocker}>{blocker}</li>) : <li>No active blockers surfaced.</li>}
                </ul>
              </article>
              <article className="entity-card">
                <p className="panel-title">Recent Failures / Successes</p>
                <ul className="detail-list">
                  {summary.recentFailures.map((failure) => (
                    <li key={failure}>Failure: {failure}</li>
                  ))}
                  {summary.recentSuccesses.map((success) => (
                    <li key={success}>Success: {success}</li>
                  ))}
                  {summary.recentFailures.length === 0 && summary.recentSuccesses.length === 0 ? <li>No completed or failed runs are linked yet.</li> : null}
                </ul>
              </article>
            </div>
          </section>

          <section className="panel-card">
            <h3 className="section-title">Knowledge + Learning</h3>
            <div className="stack">
              <article className="entity-card">
                <p className="panel-title">Top Topics</p>
                <ul className="detail-list">
                  {summary.topTopics.map((topic) => (
                    <li key={topic.id}>
                      {topic.title}: {topic.summary}
                    </li>
                  ))}
                </ul>
              </article>
              <article className="entity-card">
                <p className="panel-title">Learned Policies</p>
                <ul className="detail-list">
                  {summary.learnedPolicies.length > 0 ? (
                    summary.learnedPolicies.map((policy) => (
                      <li key={policy.id}>
                        {policy.title}: {policy.summary}
                        {policy.requiresApproval ? " (approval required)" : ""}
                      </li>
                    ))
                  ) : (
                    <li>No learning writebacks have been proposed yet.</li>
                  )}
                </ul>
              </article>
              <article className="entity-card">
                <p className="panel-title">Drift Markers</p>
                <ul className="detail-list">
                  {summary.driftMarkers.length > 0 ? (
                    summary.driftMarkers.map((marker) => (
                      <li key={`${marker.kind}-${marker.summary}`}>
                        {marker.kind}: {marker.summary}
                      </li>
                    ))
                  ) : (
                    <li>No drift or contradiction markers were surfaced for the top topics.</li>
                  )}
                </ul>
              </article>
              <article className="entity-card">
                <p className="panel-title">Structured Findings</p>
                <ul className="detail-list">
                  {summary.consistencyFindings.length > 0 ? (
                    summary.consistencyFindings.map((finding) => (
                      <li key={finding.id}>
                        {finding.findingKind}: {finding.summary}
                      </li>
                    ))
                  ) : (
                    <li>No structured evaluator findings are attached to this project yet.</li>
                  )}
                </ul>
              </article>
              <article className="entity-card">
                <p className="panel-title">Approval Queue</p>
                <ul className="detail-list">
                  {summary.pendingApprovals.length > 0 ? (
                    summary.pendingApprovals.map((proposal) => (
                      <li key={proposal.id}>
                        {proposal.title}: {proposal.approvalReason ?? proposal.summary}
                      </li>
                    ))
                  ) : (
                    <li>No pending approval proposals are blocking this project right now.</li>
                  )}
                </ul>
              </article>
            </div>
          </section>

          <section className="panel-card">
            <h3 className="section-title">Standards Delta / Health</h3>
            {summary.standardsHealth ? (
              <div className="stack">
                <article className="entity-card">
                  <div className="panel-row">
                    <p className="panel-title">Health Header</p>
                    <StatusBadge
                      status={
                        summary.standardsHealth.overallScore >= 80
                          ? "healthy"
                          : summary.standardsHealth.overallScore >= 60
                            ? "warning"
                            : "error"
                      }
                      label={`${summary.standardsHealth.overallScore.toFixed(2)} / 100`}
                    />
                  </div>
                  <ul className="detail-list">
                    <li>Critical deltas: {summary.standardsHealth.criticalDeltaCount}</li>
                    <li>Unknown standards: {summary.standardsHealth.unknownCount}</li>
                    <li>Regression count: {summary.standardsHealth.regressionCount}</li>
                    <li>Evaluation confidence: {summary.standardsHealth.evaluationConfidence.toFixed(2)}</li>
                    <li>Last evaluated: {summary.standardsHealth.createdAt}</li>
                  </ul>
                </article>

                <article className="entity-card">
                  <p className="panel-title">Domain Breakdown</p>
                  <ul className="detail-list">
                    {summary.standardsHealth.domainScores.map((domain) => (
                      <li key={domain.domain}>
                        {domain.domain}: {domain.score.toFixed(2)} (confidence {domain.confidence.toFixed(2)})
                      </li>
                    ))}
                    {summary.standardsHealth.domainScores.length === 0 ? <li>No domain-level scores were persisted.</li> : null}
                  </ul>
                </article>

                <article className="entity-card">
                  <p className="panel-title">Delta Matrix</p>
                  <ul className="detail-list">
                    {summary.standardsHealth.deltaItems.slice(0, 10).map((delta) => (
                      <li key={delta.id}>
                        <span style={{ marginRight: "0.5rem" }}>
                          <StatusBadge status={standardsStatusTone(delta.status)} label={delta.status} />
                        </span>
                        {delta.standardId} ({delta.domain}) · impact {delta.estimatedHealthImpact.toFixed(2)} · {delta.summary}
                      </li>
                    ))}
                    {summary.standardsHealth.deltaItems.length === 0 ? <li>No active delta items were generated.</li> : null}
                  </ul>
                </article>

                <article className="entity-card">
                  <p className="panel-title">Backfill Lane</p>
                  <ul className="detail-list">
                    {summary.standardsHealth.backfillTasks.slice(0, 10).map((task) => (
                      <li key={task.id}>
                        {task.title} · {bucketLabel[task.priorityBucket] ?? task.priorityBucket} · priority {task.priorityScore.toFixed(2)}
                        {task.blocked ? " · blocked" : ""}
                      </li>
                    ))}
                    {summary.standardsHealth.backfillTasks.length === 0 ? (
                      <li>No remediation tasks were generated from the latest standards snapshot.</li>
                    ) : null}
                  </ul>
                </article>

                <article className="entity-card">
                  <p className="panel-title">Standards Migration</p>
                  <ul className="detail-list">
                    <li>
                      Attached version {summary.standardsHealth.migration.attachedVersion} vs latest{" "}
                      {summary.standardsHealth.migration.latestVersion}
                    </li>
                    <li>Migration delta count: {summary.standardsHealth.migration.migrationDeltaCount}</li>
                    {summary.standardsHealth.migration.items.slice(0, 6).map((item) => (
                      <li key={`${item.standardId}-${item.introducedVersion}`}>
                        {item.standardId} introduced in {item.introducedVersion} ({item.domain})
                      </li>
                    ))}
                  </ul>
                </article>
              </div>
            ) : (
              <article className="entity-card">
                <p className="panel-subtitle">
                  No standards health snapshot is available yet. Run a linked session to generate assessments and remediation tasks.
                </p>
              </article>
            )}
          </section>

          <section className="panel-card">
            <h3 className="section-title">Active Runs</h3>
            <div className="stack">
              {summary.activeRuns.map((run) => (
                <article key={run.id} className="entity-card">
                  <div className="panel-row">
                    <p className="panel-title">{run.objective}</p>
                    <StatusBadge
                      status={
                        run.status === "completed"
                          ? "healthy"
                          : run.status === "failed"
                            ? "error"
                            : run.status === "canceled" || run.status === "superseded"
                              ? "warning"
                              : "unknown"
                      }
                      label={run.status}
                    />
                  </div>
                  <p className="panel-subtitle">
                    {run.workflowKey} · {run.agentKey}
                  </p>
                  {run.resultSummary ? <p className="entity-meta">{run.resultSummary}</p> : null}
                </article>
              ))}
            </div>
          </section>
        </div>
      ) : (
        <KnowledgePageView page={dossier} />
      )}
    </div>
  );
}
