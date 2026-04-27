"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import type {
  AiosProjectComponentKey,
  AiosProjectComponentSetting,
  KnowledgePageDetail,
  TaskiProjectSummary,
} from "@/lib/control-plane";
import { KnowledgePageView } from "@/components/knowledge/KnowledgePageView";
import { StatusBadge } from "@/components/primitives/StatusBadge";
import { trpc } from "@/lib/trpc";

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

const pipelineStatusTone = (status: string): "healthy" | "warning" | "error" | "unknown" => {
  if (status === "healthy" || status === "pass") {
    return "healthy";
  }
  if (status === "error" || status === "fail" || status === "missing" || status === "blocked") {
    return "error";
  }
  if (status === "warning" || status === "running" || status === "stale") {
    return "warning";
  }
  return "unknown";
};

const pipelineTierLabel: Record<string, string> = {
  tier_1_core: "Tier 1 Core",
  production_app: "Production App",
  domain_specific: "Domain Specific",
};

export function TaskiProjectSurface({
  summary,
  dossier,
}: {
  summary: TaskiProjectSummary;
  dossier: KnowledgePageDetail;
}): React.JSX.Element {
  const router = useRouter();
  const [tab, setTab] = useState<"taski" | "dossier">("taski");
  const [componentSettings, setComponentSettings] = useState<AiosProjectComponentSetting[]>(summary.aiosComponents);
  const [selectedComponentKey, setSelectedComponentKey] = useState<AiosProjectComponentKey>(
    summary.aiosComponents[0]?.key ?? "taski_summary",
  );
  const utils = trpc.useUtils();
  const componentUpdater = trpc.projects.setAiosComponentEnabled.useMutation({
    onSuccess: async (settings) => {
      setComponentSettings(settings);
      await utils.projects.taskiSummary.invalidate({ projectId: summary.projectId });
      router.refresh();
    },
  });
  const backfillUpdater = trpc.projects.updateBackfillTask.useMutation({
    onSuccess: async () => {
      await utils.projects.taskiSummary.invalidate({ projectId: summary.projectId });
    },
  });
  const selectedComponent = componentSettings.find((component) => component.key === selectedComponentKey) ?? componentSettings[0];
  const componentEnabled = (key: AiosProjectComponentKey): boolean =>
    componentSettings.find((component) => component.key === key)?.enabled ?? true;
  const taskiSummaryEnabled = componentEnabled("taski_summary");
  const dossierEnabled = componentEnabled("knowledge_dossier");
  const standardsHealthEnabled = componentEnabled("standards_health");
  const qualityPipelineEnabled = componentEnabled("quality_pipeline");
  const learningWritebacksEnabled = componentEnabled("learning_writebacks");
  const activeRunsEnabled = componentEnabled("active_runs");

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
          <button
            type="button"
            className={tab === "taski" ? "button-primary" : "button-secondary"}
            disabled={!taskiSummaryEnabled}
            onClick={() => setTab("taski")}
          >
            Taski Summary
          </button>
          <button
            type="button"
            className={tab === "dossier" ? "button-primary" : "button-secondary"}
            disabled={!dossierEnabled}
            onClick={() => setTab("dossier")}
          >
            Knowledge Dossier
          </button>
        </div>
      </section>

      <section className="panel-card">
        <div className="panel-row project-scope-row">
          <div>
            <h3 className="section-title">AIOS Project Scope</h3>
            <p className="panel-subtitle">
              Disable noisy AIOS surfaces for this project without changing other project dossiers.
            </p>
          </div>
          <div className="project-scope-control">
            <label className="field">
              Part
              <select
                value={selectedComponentKey}
                onChange={(event) => setSelectedComponentKey(event.target.value as AiosProjectComponentKey)}
              >
                {componentSettings.map((component) => (
                  <option key={component.key} value={component.key}>
                    {component.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Mode
              <select
                value={selectedComponent?.enabled ? "enabled" : "disabled"}
                disabled={!selectedComponent || componentUpdater.isPending}
                onChange={(event) => {
                  if (!selectedComponent) {
                    return;
                  }
                  const nextEnabled = event.target.value === "enabled";
                  setComponentSettings((currentSettings) =>
                    currentSettings.map((component) =>
                      component.key === selectedComponent.key ? { ...component, enabled: nextEnabled } : component,
                    ),
                  );
                  componentUpdater.mutate({
                    projectId: summary.projectId,
                    componentKey: selectedComponent.key,
                    enabled: nextEnabled,
                  });
                }}
              >
                <option value="enabled">enabled</option>
                <option value="disabled">off for this project</option>
              </select>
            </label>
          </div>
        </div>
        {selectedComponent ? <p className="entity-meta">{selectedComponent.summary}</p> : null}
        <div className="badge-row" style={{ marginTop: "0.75rem" }}>
          {componentSettings.map((component) => (
            <StatusBadge
              key={component.key}
              status={component.enabled ? "healthy" : "warning"}
              label={`${component.label}: ${component.enabled ? "on" : "off"}`}
            />
          ))}
        </div>
      </section>

      {tab === "taski" && taskiSummaryEnabled ? (
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

          {learningWritebacksEnabled ? (
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
          ) : null}

          {standardsHealthEnabled ? (
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
                        <div className="panel-row" style={{ marginTop: "0.5rem" }}>
                          <button
                            type="button"
                            className="button-secondary"
                            disabled={backfillUpdater.isPending}
                            onClick={() =>
                              backfillUpdater.mutate({
                                taskId: task.id,
                                owner: task.owner ?? "operator",
                                status: "in_progress",
                                blocked: false,
                                priorityBucket: task.priorityBucket,
                              })
                            }
                          >
                            Start
                          </button>
                          <button
                            type="button"
                            className="button-secondary"
                            disabled={backfillUpdater.isPending}
                            onClick={() =>
                              backfillUpdater.mutate({
                                taskId: task.id,
                                status: "blocked",
                                blocked: true,
                                blockedReason: task.dependencyChain.join(", ") || "Blocked pending upstream dependency.",
                                priorityBucket: "blocked",
                              })
                            }
                          >
                            Block
                          </button>
                          <button
                            type="button"
                            className="button-secondary"
                            disabled={backfillUpdater.isPending}
                            onClick={() =>
                              backfillUpdater.mutate({
                                taskId: task.id,
                                status: "done",
                                blocked: false,
                                reviewAt: new Date().toISOString(),
                              })
                            }
                          >
                            Resolve
                          </button>
                        </div>
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
          ) : null}

          {qualityPipelineEnabled ? (
          <section className="panel-card">
            <h3 className="section-title">Quality Pipeline</h3>
            <div className="stack">
              <article className="entity-card">
                <div className="panel-row">
                  <p className="panel-title">
                    Standard {summary.qualityPipeline.standardVersion}
                    {summary.qualityPipeline.fullPipeline ? " · full pipeline" : " · partial pipeline"}
                  </p>
                  <StatusBadge
                    status={pipelineStatusTone(summary.qualityPipeline.overallStatus)}
                    label={summary.qualityPipeline.overallStatus}
                  />
                </div>
                <ul className="detail-list">
                  <li>
                    Required gates configured: {summary.qualityPipeline.coverage.configuredRequired} /{" "}
                    {summary.qualityPipeline.coverage.required}
                  </li>
                  <li>
                    Required gates passing: {summary.qualityPipeline.coverage.passingRequired} / {summary.qualityPipeline.coverage.required}
                  </li>
                  {summary.qualityPipeline.blockedReason ? <li>Blocked: {summary.qualityPipeline.blockedReason}</li> : null}
                </ul>
              </article>

              <article className="entity-card">
                <p className="panel-title">Tier Coverage</p>
                <ul className="detail-list">
                  {Object.entries(summary.qualityPipeline.coverageByTier).map(([tier, coverage]) => (
                    <li key={tier}>
                      {pipelineTierLabel[tier] ?? tier}: configured {coverage.configuredRequired} / {coverage.required}; passing{" "}
                      {coverage.passingRequired} / {coverage.required}
                    </li>
                  ))}
                </ul>
              </article>

              <article className="entity-card">
                <p className="panel-title">Gate Matrix</p>
                <ul className="detail-list">
                  {summary.qualityPipeline.gates.map((gate) => (
                    <li key={gate.key}>
                      <span style={{ marginRight: "0.5rem" }}>
                        <StatusBadge status={pipelineStatusTone(gate.status)} label={gate.status} />
                      </span>
                      {pipelineTierLabel[gate.tier] ?? gate.tier} · {gate.label}
                      {gate.required ? " · required" : ""}
                      {gate.command ? ` · ${gate.command}` : " · no command configured"}
                      {gate.completedAt ? ` · ${gate.completedAt}` : ""}
                      {gate.blockedReason ? ` · ${gate.blockedReason}` : ""}
                    </li>
                  ))}
                </ul>
              </article>
            </div>
          </section>
          ) : null}

          {activeRunsEnabled ? (
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
          ) : null}
        </div>
      ) : tab === "dossier" && dossierEnabled ? (
        <KnowledgePageView page={dossier} />
      ) : (
        <section className="panel-card">
          <h3 className="section-title">Project Surface Disabled</h3>
          <p className="panel-subtitle">This AIOS part is off for {summary.projectTitle}. Re-enable it from the project scope selector.</p>
        </section>
      )}
    </div>
  );
}
