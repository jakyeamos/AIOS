import Link from "next/link";

import { ProvenanceBadge } from "@/components/primitives/ProvenanceBadge";
import { StatCard } from "@/components/primitives/StatCard";
import { StatusBadge } from "@/components/primitives/StatusBadge";
import { formatDateTime } from "@/lib/format";
import { assessRunStatus } from "@/lib/status-provenance";
import type { NextAction, OrchestrationRun } from "@/lib/control-plane";
import { getCaller } from "@/server/caller";

type Caller = Awaited<ReturnType<typeof getCaller>>;
export type V2Overview = Awaited<ReturnType<Caller["controlPlane"]["overview"]>>;
export type V2RunDetail = Awaited<ReturnType<Caller["controlPlane"]["runDetail"]>>;
export type V2Projects = Awaited<ReturnType<Caller["projects"]["list"]>>;

const stageLabels = ["Intent", "Route", "Execute", "Verify", "Review", "Closeout"] as const;

const stageIndexForRun = (run: OrchestrationRun): number => {
  if (run.status === "planned") {
    return 1;
  }
  if (run.status === "ready") {
    return 2;
  }
  if (run.status === "completed") {
    return 5;
  }
  return 3;
};

const stageLabelForRun = (run: OrchestrationRun): string => {
  if (run.status === "completed") {
    return "Closeout";
  }
  if (run.status === "failed") {
    return "Verify recovery";
  }
  if (run.status === "canceled" || run.status === "superseded") {
    return "Review";
  }
  if (run.status === "in_progress") {
    return "Verify";
  }
  return run.status === "ready" ? "Execute" : "Route";
};

const runSortValue = (run: OrchestrationRun): number => {
  const timestamp = Date.parse(run.updatedAt ?? run.createdAt);
  return Number.isFinite(timestamp) ? timestamp : 0;
};

export const selectCurrentRun = (runs: readonly OrchestrationRun[]): OrchestrationRun | null => {
  const active = runs
    .filter((run) => ["planned", "ready", "in_progress"].includes(run.status))
    .sort((left, right) => runSortValue(right) - runSortValue(left));

  return active[0] ?? [...runs].sort((left, right) => runSortValue(right) - runSortValue(left))[0] ?? null;
};

const nextActionForRun = (actions: readonly NextAction[], run: OrchestrationRun | null): NextAction | null => {
  if (run?.projectId) {
    const projectAction = actions.find((action) => action.projectId === run.projectId);
    if (projectAction) {
      return projectAction;
    }
  }

  return actions[0] ?? null;
};

const statusTone = (run: OrchestrationRun): "healthy" | "warning" | "error" | "unknown" => assessRunStatus(run).tone;

const statTone = (run: OrchestrationRun): "healthy" | "warning" | "error" => {
  const tone = statusTone(run);
  return tone === "healthy" || tone === "error" ? tone : "warning";
};

function ReadOnlyNotice({ children }: { children: React.ReactNode }): React.JSX.Element {
  return (
    <aside className="v2-read-only-notice" aria-label="Read-only boundary">
      <StatusBadge status="unknown" label="read-only projection" />
      <p>{children}</p>
    </aside>
  );
}

function StateCard({
  title,
  detail,
  action,
  tone = "unknown",
}: {
  title: string;
  detail: string;
  action?: React.ReactNode;
  tone?: "healthy" | "warning" | "error" | "unknown";
}): React.JSX.Element {
  return (
    <article className={`v2-state-card v2-state-${tone}`}>
      <div className="panel-row">
        <h3 className="panel-title">{title}</h3>
        <StatusBadge status={tone} label={tone} />
      </div>
      <p className="panel-subtitle">{detail}</p>
      {action ? <div className="v2-state-action">{action}</div> : null}
    </article>
  );
}

function ContextualLinks(): React.JSX.Element {
  return (
    <nav className="v2-context-nav" aria-label="Contextual surfaces">
      <p className="section-title">Contextual surfaces</p>
      <div className="chip-row">
        <Link className="button-secondary" href="/projects">Projects</Link>
        <Link className="button-secondary" href="/search">Search evidence</Link>
        <Link className="button-secondary" href="/knowledge">Knowledge</Link>
        <Link className="button-secondary" href="/context">Context receipts</Link>
        <Link className="button-secondary" href="/control">Diagnostics</Link>
      </div>
    </nav>
  );
}

function StageRail({ run }: { run: OrchestrationRun }): React.JSX.Element {
  const activeIndex = stageIndexForRun(run);

  return (
    <ol className="v2-stage-rail" aria-label="Run stages">
      {stageLabels.map((label, index) => {
        const state = index < activeIndex ? "complete" : index === activeIndex ? "active" : "pending";
        return (
          <li key={label} className={`v2-stage-${state}`} data-stage={state}>
            <span className="v2-stage-index" aria-hidden="true">{index + 1}</span>
            <span>{label}</span>
          </li>
        );
      })}
    </ol>
  );
}

function RunFacts({ run }: { run: OrchestrationRun }): React.JSX.Element {
  const status = assessRunStatus(run);

  return (
    <dl className="v2-fact-grid">
      <div><dt>Project</dt><dd>{run.projectName}</dd></div>
      <div><dt>Stage</dt><dd>{stageLabelForRun(run)}</dd></div>
      <div><dt>Workflow</dt><dd className="mono">{run.workflowKey}</dd></div>
      <div><dt>Agent</dt><dd className="mono">{run.agentKey}</dd></div>
      <div><dt>Authority</dt><dd>{run.backendKey ?? "unassigned"}</dd></div>
      <div><dt>Freshness</dt><dd>{status.stalenessMinutes === null ? "missing" : `${status.stalenessMinutes}m old`}</dd></div>
      <div><dt>Source</dt><dd>{status.source}</dd></div>
      <div><dt>Updated</dt><dd>{formatDateTime(run.updatedAt)}</dd></div>
    </dl>
  );
}

export function TodaySurface({ overview }: { overview: V2Overview }): React.JSX.Element {
  const currentRun = selectCurrentRun(overview.runs);
  const nextAction = nextActionForRun(overview.nextActions ?? [], currentRun);
  const status = currentRun ? assessRunStatus(currentRun) : null;
  const blockers = (overview.nextActions ?? []).filter((action) => action.priorityBucket === "blocked").length;

  return (
    <>
      <ReadOnlyNotice>Today reads the canonical control-plane projections. Starting work and changing durable state remain gated for the next milestone.</ReadOnlyNotice>

      <div className="grid grid-4">
        <StatCard label="Current project" value={currentRun?.projectName ?? "none"} status={currentRun ? statTone(currentRun) : "warning"} />
        <StatCard label="Current stage" value={currentRun ? stageLabelForRun(currentRun) : "Start work"} status={currentRun ? statTone(currentRun) : "warning"} />
        <StatCard label="Pending approvals" value={overview.pendingWritebacks.length} status={overview.pendingWritebacks.length > 0 ? "warning" : "healthy"} />
        <StatCard label="Blocked actions" value={blockers} status={blockers > 0 ? "warning" : "healthy"} />
      </div>

      <section className="panel-card v2-current-work" aria-labelledby="today-current-work">
        <div className="panel-row">
          <div>
            <h2 id="today-current-work" className="section-title">Current work</h2>
            <p className="panel-subtitle">The latest source-backed run, ordered by active status and update time.</p>
          </div>
          {currentRun ? <ProvenanceBadge level={status?.provenance ?? "missing"} source={status?.source ?? "orchestration_runs"} reason={status?.reason ?? "Run metadata is unavailable."} /> : null}
        </div>
        {currentRun ? (
          <div className="v2-current-work-body">
            <div>
              <p className="v2-display-title">{currentRun.objective}</p>
              <p className="panel-subtitle">{currentRun.rationale}</p>
              <div className="badge-row v2-inline-status">
                <StatusBadge status={statusTone(currentRun)} label={currentRun.status} />
                <span className="entity-meta">run {currentRun.id}</span>
              </div>
            </div>
            <div className="v2-action-row">
              <Link className="button-primary" href={`/runs/${currentRun.id}`}>Open current run</Link>
              <Link className="button-secondary" href="/start">Start work</Link>
            </div>
          </div>
        ) : (
          <StateCard title="No current run" detail="No source-backed run is available yet. Review the read-only start surface to see the route and evidence contract." tone="warning" action={<Link className="button-primary" href="/start">Open Start work</Link>} />
        )}
      </section>

      <div className="grid grid-2">
        <section className="panel-card" aria-labelledby="today-next-action">
          <h2 id="today-next-action" className="section-title">Next responsible action</h2>
          {nextAction ? (
            <article className="entity-card">
              <div className="panel-row"><p className="panel-title">{nextAction.title}</p><StatusBadge status={nextAction.priorityBucket === "blocked" ? "warning" : "unknown"} label={nextAction.priorityBucket} /></div>
              <p className="panel-subtitle">{nextAction.rationale}</p>
              <p className="entity-meta">source: {nextAction.evidenceIds[0] ?? "next_action_projection"} · confidence {nextAction.confidence.toFixed(2)}</p>
              <Link className="button-secondary" href={nextAction.drillDownPath}>Open evidence</Link>
            </article>
          ) : (
            <StateCard title="No ranked action" detail="The projection has no next action yet. Continue from Start work or inspect the contextual surfaces." action={<Link className="button-secondary" href="/start">Review route options</Link>} />
          )}
        </section>

        <section className="panel-card" aria-labelledby="today-daily-flow">
          <h2 id="today-daily-flow" className="section-title">Daily flow replay</h2>
          {overview.dailyFlowSummary ? (
            <ol className="v2-flow-list">
              {overview.dailyFlowSummary.steps.slice(0, 6).map((step, index) => (
                <li key={`${step.kind}-${index}`}>
                  <span className="v2-flow-index">{index + 1}</span>
                  <span><strong>{step.kind.replaceAll("_", " ")}</strong><br /><span className="panel-subtitle">{step.summary}</span></span>
                  <ProvenanceBadge level={step.provenance === "contradictory" ? "missing" : step.provenance} source={step.kind} reason={`Freshness: ${step.freshness}`} />
                </li>
              ))}
            </ol>
          ) : (
            <StateCard title="Daily flow missing" detail="No replay is attached to the current projection yet. The absence is shown explicitly rather than inferred as success." tone="warning" />
          )}
        </section>
      </div>

      <ContextualLinks />
    </>
  );
}

export function StartWorkSurface({ overview, projects }: { overview: V2Overview; projects: V2Projects }): React.JSX.Element {
  const currentRun = selectCurrentRun(overview.runs);
  const selectedProject = currentRun?.projectName ?? projects[0]?.name ?? "No project resolved";
  const selectedWorkflow = overview.workflowTemplates[0];

  return (
    <>
      <ReadOnlyNotice>This is the M3 route preview. It exposes objective, project, route, evidence, and approval classes without creating a run, packet, session, or writeback.</ReadOnlyNotice>

      <section className="panel-card" aria-labelledby="start-intent">
        <div className="panel-row"><div><h2 id="start-intent" className="section-title">Intent and scope</h2><p className="panel-subtitle">The governed start action is intentionally disabled until M4 owns mutation routing.</p></div><StatusBadge status="warning" label="start gated" /></div>
        <dl className="v2-fact-grid v2-start-facts">
          <div><dt>Objective</dt><dd>Describe the work you want AIOS to route and verify.</dd></div>
          <div><dt>Project resolution</dt><dd>{selectedProject} <span className="signal-note">source: current run/project projection</span></dd></div>
          <div><dt>Selected route</dt><dd>{selectedWorkflow?.name ?? "No workflow catalog entry"} <span className="signal-note">{selectedWorkflow?.key ?? "missing"}</span></dd></div>
          <div><dt>Expected evidence</dt><dd>{selectedWorkflow?.validation.join(", ") ?? "Route evidence is missing."}</dd></div>
          <div><dt>Approval class</dt><dd>Human review required before durable writeback or external invocation.</dd></div>
          <div><dt>Authority</dt><dd>Python-owned mutation boundary; UI remains read-only in M3.</dd></div>
        </dl>
        <div className="v2-action-row"><Link className="button-secondary" href="/">Return to Today</Link>{currentRun ? <Link className="button-primary" href={`/runs/${currentRun.id}`}>Open current run</Link> : null}</div>
      </section>

      <section className="panel-card" aria-labelledby="start-routes">
        <h2 id="start-routes" className="section-title">Available route families</h2>
        <div className="grid grid-2">
          {overview.workflowTemplates.slice(0, 6).map((workflow) => (
            <article className="entity-card" key={workflow.key}>
              <div className="panel-row"><p className="panel-title">{workflow.name}</p><span className="provenance-badge">catalog</span></div>
              <p className="panel-subtitle">{workflow.summary}</p>
              <p className="entity-meta">triggers: {workflow.triggers.slice(0, 3).join(" · ") || "not specified"}</p>
              <p className="entity-meta">validation: {workflow.validation.join(" · ") || "not specified"}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="panel-card" aria-labelledby="start-states">
        <h2 id="start-states" className="section-title">State contract</h2>
        <div className="grid grid-2">
          <StateCard title="Healthy / resolved" detail="A project and route are source-backed, so M4 can enable an explicit start action." tone="healthy" />
          <StateCard title="Blocked / ambiguous" detail="Missing project, route, or authority evidence must be resolved before any start action is enabled." tone="warning" />
          <StateCard title="Stale" detail="A stale projection remains visible with freshness metadata and a path back to source evidence." tone="warning" />
          <StateCard title="Empty" detail="No run is not treated as success; the operator is directed back to the route preview." />
        </div>
      </section>
    </>
  );
}

export function CurrentRunSurface({ detail, nextAction }: { detail: V2RunDetail; nextAction: NextAction | null }): React.JSX.Element {
  if (!detail) {
    return <StateCard title="Current run unavailable" detail="The selected run is not present in the canonical control-plane projection. Return to Today and choose another source-backed run." tone="error" action={<Link className="button-secondary" href="/">Return to Today</Link>} />;
  }

  const { run, events, invocations, evaluations, inspection } = detail;
  const status = assessRunStatus(run);

  return (
    <>
      <ReadOnlyNotice>Current run is an inspectable projection of the canonical run, event, invocation, packet, and evaluation records. Resume, invoke, cancel, and approval actions remain outside this M3 read path.</ReadOnlyNotice>
      <section className="panel-card" aria-labelledby="current-run-title">
        <div className="panel-row v2-run-heading"><div><p className="topbar-eyebrow">Current run</p><h2 id="current-run-title" className="v2-display-title">{run.objective}</h2><p className="panel-subtitle">{run.projectName} · {run.id}</p></div><div className="badge-row"><StatusBadge status={status.tone} label={run.status} /><ProvenanceBadge level={status.provenance} source={status.source} reason={status.reason} /></div></div>
        <StageRail run={run} />
        <RunFacts run={run} />
      </section>

      <div className="grid grid-2">
        <section className="panel-card" aria-labelledby="current-run-evidence">
          <h2 id="current-run-evidence" className="section-title">Evidence and authority</h2>
          <ul className="v2-evidence-list">
            <li><strong>Packet:</strong> {inspection.packetId ?? "missing"}</li>
            <li><strong>Selected sections:</strong> {inspection.selectedSections.length}</li>
            <li><strong>Omitted context:</strong> {inspection.omittedContextCount}</li>
            <li><strong>Touched files:</strong> {inspection.touchedFiles.length} · unpredicted {inspection.unpredictedTouchedFiles.length}</li>
            <li><strong>Evaluations:</strong> {evaluations.length} · unresolved findings {inspection.unresolvedFindings.length}</li>
            <li><strong>Risk carryover:</strong> {inspection.riskCarryover.length > 0 ? inspection.riskCarryover.join(" · ") : "none recorded"}</li>
          </ul>
          {nextAction ? <article className="entity-card v2-next-action-card"><p className="panel-title">Next responsible action</p><p className="panel-subtitle">{nextAction.title}</p><p className="entity-meta">{nextAction.rationale}</p><Link className="button-secondary" href={nextAction.drillDownPath}>Open source evidence</Link></article> : null}
        </section>

        <section className="panel-card" aria-labelledby="current-run-events">
          <h2 id="current-run-events" className="section-title">Lifecycle events</h2>
          {events.length > 0 ? <ol className="v2-event-list">{events.map((event) => <li key={event.id}><div className="panel-row"><strong>{event.eventType}</strong><span className="entity-meta">{formatDateTime(event.createdAt)}</span></div><p className="panel-subtitle">{event.summary}</p><p className="entity-meta">{event.fromStatus ?? "—"} → {event.toStatus ?? "—"}</p></li>)}</ol> : <StateCard title="No lifecycle events" detail="The run projection has no event evidence yet." tone="warning" />}
        </section>
      </div>

      <section className="panel-card" aria-labelledby="current-run-invocations">
        <h2 id="current-run-invocations" className="section-title">Invocation and review boundary</h2>
        {invocations.length > 0 ? <div className="grid grid-2">{invocations.map((invocation) => <article className="entity-card" key={invocation.id}><div className="panel-row"><p className="panel-title">{invocation.backendLabel}</p><StatusBadge status={invocation.status === "failed" ? "error" : invocation.status === "completed" ? "healthy" : "warning"} label={invocation.status} /></div><p className="entity-meta">session: {invocation.sessionId ?? "not linked"} · actor scope: {typeof invocation.metadata.actor === "string" ? invocation.metadata.actor : "managed runtime"}</p><p className="entity-meta">created: {formatDateTime(invocation.createdAt)}</p></article>)}</div> : <StateCard title="No invocation attached" detail="This run is still a packet or planning projection; no external actor is claimed." />}
      </section>

      <div className="v2-action-row"><Link className="button-secondary" href="/">Return to Today</Link><Link className="button-secondary" href="/start">Review Start work</Link></div>
    </>
  );
}
