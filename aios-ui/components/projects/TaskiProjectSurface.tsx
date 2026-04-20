"use client";

import { useState } from "react";

import type { KnowledgePageDetail, TaskiProjectSummary } from "@/lib/control-plane";
import { KnowledgePageView } from "@/components/knowledge/KnowledgePageView";
import { StatusBadge } from "@/components/primitives/StatusBadge";

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
            </div>
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
