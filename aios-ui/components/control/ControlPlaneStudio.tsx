"use client";

import { useState } from "react";

import { ProvenanceBadge } from "@/components/primitives/ProvenanceBadge";
import { StatusBadge } from "@/components/primitives/StatusBadge";
import type {
  AgentProfile,
  BriefingPacket,
  ConsistencyFinding,
  ControlPlaneRunDetail,
  ImprovementWriteback,
  InvocationBackend,
  OrchestrationRun,
  PacketExpansionKind,
  WorkflowTemplate,
} from "@/lib/control-plane";
import { assessRunStatus, assessWritebackStatus } from "@/lib/status-provenance";
import { trpc } from "@/lib/trpc";

type ProjectOption = {
  id: string;
  name: string;
};

type ControlPlaneStudioProps = {
  projects: ProjectOption[];
  workflowTemplates: WorkflowTemplate[];
  agentProfiles: AgentProfile[];
  invocationBackends: InvocationBackend[];
  recentRuns: OrchestrationRun[];
  recentPackets: BriefingPacket[];
  pendingWritebacks: ImprovementWriteback[];
  recentFindings: ConsistencyFinding[];
};

const findingTone = (severity: ConsistencyFinding["severity"]): "healthy" | "warning" | "error" | "unknown" => {
  if (severity === "error") {
    return "error";
  }
  if (severity === "warning") {
    return "warning";
  }
  return "unknown";
};

export function ControlPlaneStudio({
  projects,
  workflowTemplates,
  agentProfiles,
  invocationBackends,
  recentRuns,
  recentPackets,
  pendingWritebacks,
  recentFindings,
}: ControlPlaneStudioProps): React.JSX.Element {
  const utils = trpc.useUtils();
  const [projectId, setProjectId] = useState<string>(projects[0]?.id ?? "");
  const [objective, setObjective] = useState(
    "Turn AIOS into an explicit knowledge and orchestration control plane.",
  );
  const [policyMode, setPolicyMode] = useState<BriefingPacket["policyMode"]>("compact-ranked");
  const [tokenBudget, setTokenBudget] = useState<string>("900");
  const [expansionKind, setExpansionKind] = useState<PacketExpansionKind>("topic");
  const [expansionTarget, setExpansionTarget] = useState("");
  const [selectedRunId, setSelectedRunId] = useState<string>(recentRuns[0]?.id ?? "");
  const [reviewNotes, setReviewNotes] = useState<Record<string, string>>({});

  const planner = trpc.controlPlane.plan.useMutation({
    onSuccess: async (result) => {
      setSelectedRunId(result.run.id);
      await utils.controlPlane.overview.invalidate();
    },
  });
  const expander = trpc.controlPlane.expand.useMutation();
  const invoker = trpc.controlPlane.invoke.useMutation({
    onSuccess: async (result) => {
      setSelectedRunId(result.runDetail.run.id);
      await Promise.all([utils.controlPlane.overview.invalidate(), utils.controlPlane.runDetail.invalidate()]);
    },
  });
  const canceller = trpc.controlPlane.cancel.useMutation({
    onSuccess: async (result) => {
      setSelectedRunId(result.runDetail.run.id);
      await Promise.all([utils.controlPlane.overview.invalidate(), utils.controlPlane.runDetail.invalidate()]);
    },
  });
  const reviewer = trpc.controlPlane.reviewWriteback.useMutation({
    onSuccess: async () => {
      await Promise.all([utils.controlPlane.overview.invalidate(), utils.controlPlane.runDetail.invalidate()]);
    },
  });

  const runDetailQuery = trpc.controlPlane.runDetail.useQuery(
    { runId: selectedRunId },
    { enabled: selectedRunId.length > 0 },
  );

  const selectedRunDetail: ControlPlaneRunDetail | null = runDetailQuery.data ?? null;
  const selectedRunStatus = selectedRunDetail ? assessRunStatus(selectedRunDetail.run) : null;

  return (
    <div className="page-content">
      <section className="panel-card">
        <div className="panel-row">
          <div>
            <h3 className="section-title">Task Router</h3>
            <p className="panel-subtitle">
              Create a durable run, packet, and backend selection before invocation. Runtime status only moves when real events land.
            </p>
          </div>
        </div>
        <div className="stack">
          <label className="field">
            Project
            <select value={projectId} onChange={(event) => setProjectId(event.target.value)}>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Objective
            <textarea
              rows={5}
              value={objective}
              onChange={(event) => setObjective(event.target.value)}
              placeholder="Describe the task AIOS should route and track."
            />
          </label>
          <div className="grid grid-2">
            <label className="field">
              Context Policy
              <select value={policyMode} onChange={(event) => setPolicyMode(event.target.value as BriefingPacket["policyMode"])}>
                <option value="compact-ranked">compact-ranked</option>
                <option value="explore">explore</option>
              </select>
            </label>
            <label className="field">
              Token Budget
              <input value={tokenBudget} onChange={(event) => setTokenBudget(event.target.value)} />
            </label>
          </div>
          <button
            type="button"
            className="button-primary"
            disabled={planner.isPending || objective.trim().length < 8}
            onClick={() =>
              planner.mutate({
                objective: objective.trim(),
                projectId: projectId || undefined,
                policyMode,
                tokenBudget: Number(tokenBudget) || 900,
              })
            }
          >
            {planner.isPending ? "Planning run..." : "Plan run"}
          </button>
        </div>
      </section>

      <div className="grid grid-2">
        <section className="panel-card">
          <h3 className="section-title">Workflow Registry</h3>
          <div className="stack">
            {workflowTemplates.map((workflow) => (
              <article key={workflow.key} className="entity-card">
                <p className="panel-title">{workflow.name}</p>
                <p className="panel-subtitle">{workflow.summary}</p>
                <p className="mono">{workflow.triggers.join(" · ")}</p>
                <p className="entity-meta">default backend: {workflow.defaultBackendKey}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="panel-card">
          <h3 className="section-title">Agent + Backend Registry</h3>
          <div className="stack">
            {agentProfiles.map((agent) => (
              <article key={agent.key} className="entity-card">
                <p className="panel-title">{agent.name}</p>
                <p className="panel-subtitle">{agent.summary}</p>
                <p className="mono">{agent.bestFor.join(" · ")}</p>
                <p className="entity-meta">default backend: {agent.defaultBackendKey}</p>
              </article>
            ))}
            {invocationBackends.map((backend) => (
              <article key={backend.key} className="entity-card">
                <div className="panel-row">
                  <p className="panel-title">{backend.label}</p>
                  <StatusBadge status={backend.transport === "managed_session" ? "healthy" : "warning"} label={backend.transport} />
                </div>
                <p className="panel-subtitle">{backend.summary}</p>
                <p className="mono">{backend.commandPreview.join(" ")}</p>
              </article>
            ))}
          </div>
        </section>
      </div>

      {planner.data ? (
        <div className="grid grid-2">
          <section className="panel-card">
            <h3 className="section-title">Routing Decision</h3>
            <div className="stack">
              <article className="entity-card">
                <p className="panel-title">{planner.data.run.workflowKey}</p>
                <p className="panel-subtitle">{planner.data.run.rationale}</p>
                <p className="entity-meta">backend: {planner.data.run.backendKey ?? "unassigned"}</p>
              </article>
              <article className="entity-card">
                <p className="panel-title">Assumptions</p>
                <ul className="detail-list">
                  {planner.data.run.assumptions.map((assumption) => (
                    <li key={assumption}>{assumption}</li>
                  ))}
                </ul>
              </article>
              <article className="entity-card">
                <p className="panel-title">Context Trace</p>
                <ul className="detail-list">
                  {planner.data.run.contextTrace.map((trace) => (
                    <li key={`${trace.source}-${trace.reason}`}>
                      {trace.source}: {trace.reason}
                    </li>
                  ))}
                </ul>
              </article>
              <article className="entity-card">
                <p className="panel-title">Omitted Context</p>
                <ul className="detail-list">
                  {planner.data.packet.omittedContext.length > 0 ? (
                    planner.data.packet.omittedContext.map((item) => (
                      <li key={`${item.sourceKind}-${item.label}`}>
                        {item.label}: {item.reason}
                      </li>
                    ))
                  ) : (
                    <li>No lower-ranked context was omitted within the current packet budget.</li>
                  )}
                </ul>
              </article>
            </div>
          </section>

          <section className="panel-card">
            <h3 className="section-title">Briefing Packet</h3>
            <div className="stack">
              <article className="entity-card">
                <p className="panel-title">Packet Policy</p>
                <p className="panel-subtitle">
                  {planner.data.packet.policyMode} · budget {planner.data.packet.tokenBudget}
                </p>
              </article>
              {planner.data.packet.sections.map((section) => (
                <article key={section.title} className="packet-section">
                  <p className="panel-title">{section.title}</p>
                  {section.body ? <p className="panel-subtitle">{section.body}</p> : null}
                  <ul className="detail-list">
                    {section.items.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </article>
              ))}
              <article className="entity-card">
                <p className="panel-title">Selection Trace</p>
                <ul className="detail-list">
                  {planner.data.packet.selectionTrace.map((trace) => (
                    <li key={`${trace.section}-${trace.label}`}>
                      {trace.section}: {trace.label} ({trace.sourceKind}, score {trace.score}) - {trace.reason}
                    </li>
                  ))}
                </ul>
              </article>
              <article className="entity-card">
                <p className="panel-title">Targeted Expansion</p>
                <div className="stack">
                  <label className="field">
                    Expansion kind
                    <select value={expansionKind} onChange={(event) => setExpansionKind(event.target.value as PacketExpansionKind)}>
                      <option value="topic">topic</option>
                      <option value="failure_pattern">failure_pattern</option>
                      <option value="code_area">code_area</option>
                      <option value="policy">policy</option>
                      <option value="recent_run">recent_run</option>
                    </select>
                  </label>
                  <label className="field">
                    Target
                    <input
                      value={expansionTarget}
                      onChange={(event) => setExpansionTarget(event.target.value)}
                      placeholder="e.g. packet policy or prior failure mode"
                    />
                  </label>
                  <button
                    type="button"
                    className="button-secondary"
                    disabled={expander.isPending || expansionTarget.trim().length < 2}
                    onClick={() =>
                      expander.mutate({
                        packetId: planner.data.packet.id,
                        runId: planner.data.run.id,
                        projectId: planner.data.packet.projectId ?? undefined,
                        requestKind: expansionKind,
                        requestTarget: expansionTarget.trim(),
                        tokenBudget: 180,
                      })
                    }
                  >
                    {expander.isPending ? "Loading expansion..." : "Request targeted expansion"}
                  </button>
                  {expander.data ? (
                    <ul className="detail-list">
                      {expander.data.returnedContext.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              </article>
            </div>
          </section>
        </div>
      ) : null}

      <div className="grid grid-2">
        <section className="panel-card">
          <h3 className="section-title">Approval Queue</h3>
          <div className="stack">
            {pendingWritebacks.length > 0 ? (
              pendingWritebacks.map((writeback) => {
                const writebackStatus = assessWritebackStatus(writeback);
                return (
                  <article key={writeback.id} className="entity-card">
                    <div className="panel-row">
                      <p className="panel-title">{writeback.title}</p>
                      <div className="badge-row">
                        <StatusBadge status={writebackStatus.tone} label={writeback.status} />
                        <ProvenanceBadge
                          level={writebackStatus.provenance}
                          source={writebackStatus.source}
                          reason={writebackStatus.reason}
                        />
                      </div>
                    </div>
                    <p className="panel-subtitle">{writeback.summary}</p>
                    <p className="entity-meta">
                      impact: {writeback.impactScope} · layer: {writeback.layerType}/{writeback.layerKey}
                    </p>
                    {writeback.approvalReason ? <p className="entity-meta">why review is required: {writeback.approvalReason}</p> : null}
                    <p className="entity-meta">source: {writebackStatus.source}</p>
                    <ul className="detail-list">
                      {writeback.evidence.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                    <label className="field">
                      Decision note
                      <textarea
                        rows={2}
                        value={reviewNotes[writeback.id] ?? ""}
                        onChange={(event) => setReviewNotes((current) => ({ ...current, [writeback.id]: event.target.value }))}
                      />
                    </label>
                    <div className="panel-row">
                      <button
                        type="button"
                        className="button-primary"
                        disabled={reviewer.isPending}
                        onClick={() =>
                          reviewer.mutate({
                            writebackId: writeback.id,
                            decision: "applied",
                            note: reviewNotes[writeback.id] ?? undefined,
                          })
                        }
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        className="button-secondary"
                        disabled={reviewer.isPending}
                        onClick={() =>
                          reviewer.mutate({
                            writebackId: writeback.id,
                            decision: "rejected",
                            note: reviewNotes[writeback.id] ?? undefined,
                          })
                        }
                      >
                        Reject
                      </button>
                    </div>
                  </article>
                );
              })
            ) : (
              <article className="entity-card">
                <p className="panel-subtitle">No gated proposals are currently waiting for review.</p>
              </article>
            )}
          </div>
        </section>

        <section className="panel-card">
          <h3 className="section-title">Structured Findings</h3>
          <div className="stack">
            {recentFindings.length > 0 ? (
              recentFindings.map((finding) => (
                <article key={finding.id} className="entity-card">
                  <div className="panel-row">
                    <p className="panel-title">{finding.ruleKey}</p>
                    <StatusBadge status={findingTone(finding.severity)} label={finding.findingKind} />
                  </div>
                  <p className="panel-subtitle">{finding.summary}</p>
                  <p className="entity-meta">topic: {finding.topicSlug ?? "project-wide"}</p>
                </article>
              ))
            ) : (
              <article className="entity-card">
                <p className="panel-subtitle">No structured drift or contradiction findings have been recorded yet.</p>
              </article>
            )}
          </div>
        </section>
      </div>

      <div className="grid grid-2">
        <section className="panel-card">
          <h3 className="section-title">Run History</h3>
          <div className="stack">
            {recentRuns.map((run) => {
              const runStatus = assessRunStatus(run);
              return (
                <article key={run.id} className="entity-card">
                  <div className="panel-row">
                    <p className="panel-title">{run.objective}</p>
                    <div className="badge-row">
                      <StatusBadge status={runStatus.tone} label={run.status} />
                      <ProvenanceBadge level={runStatus.provenance} source={runStatus.source} reason={runStatus.reason} />
                    </div>
                  </div>
                  <p className="panel-subtitle">
                    {run.projectName} · {run.workflowKey} · {run.agentKey}
                  </p>
                  <p className="entity-meta">
                    backend: {run.backendKey ?? "unassigned"} · invocation: {run.activeInvocationId ?? "none"}
                  </p>
                  <p className="entity-meta">source: {runStatus.source}</p>
                  {run.resultSummary ? <p className="entity-meta">{run.resultSummary}</p> : null}
                  <div className="panel-row">
                    <button type="button" className="button-secondary" onClick={() => setSelectedRunId(run.id)}>
                      Inspect
                    </button>
                    {run.status === "ready" ? (
                      <button
                        type="button"
                        className="button-primary"
                        disabled={invoker.isPending}
                        onClick={() => invoker.mutate({ runId: run.id })}
                      >
                        Invoke
                      </button>
                    ) : null}
                    {run.status === "in_progress" ? (
                      <button
                        type="button"
                        className="button-secondary"
                        disabled={canceller.isPending}
                        onClick={() => canceller.mutate({ runId: run.id })}
                      >
                        Cancel
                      </button>
                    ) : null}
                  </div>
                </article>
              );
            })}
          </div>
        </section>

        <section className="panel-card">
          <h3 className="section-title">Packet Ledger</h3>
          <div className="stack">
            {recentPackets.map((packet) => (
              <article key={packet.id} className="entity-card">
                <p className="panel-title">{packet.objective}</p>
                <p className="panel-subtitle">
                  {packet.workflowKey} · {packet.agentKey}
                </p>
                <p className="entity-meta">
                  {packet.policyMode} · budget {packet.tokenBudget} · {packet.sections.length} sections
                </p>
              </article>
            ))}
          </div>
        </section>
      </div>

      {selectedRunDetail ? (
        <section className="panel-card">
          <div className="panel-row">
            <div>
              <h3 className="section-title">Run Detail</h3>
              <p className="panel-subtitle">{selectedRunDetail.run.objective}</p>
            </div>
            <div className="badge-row">
              <StatusBadge status={selectedRunStatus?.tone ?? "unknown"} label={selectedRunDetail.run.status} />
              <ProvenanceBadge
                level={selectedRunStatus?.provenance ?? "missing"}
                source={selectedRunStatus?.source ?? "orchestration_runs"}
                reason={selectedRunStatus?.reason ?? "Run detail missing source metadata."}
              />
            </div>
          </div>
          <div className="detail-grid" style={{ marginTop: "1rem" }}>
            <article className="entity-card">
              <p className="panel-title">Lifecycle Events</p>
              <ul className="detail-list">
                {selectedRunDetail.events.map((event) => (
                  <li key={event.id}>
                    {event.createdAt}: {event.eventType}
                    {event.toStatus ? ` → ${event.toStatus}` : ""} — {event.summary}
                  </li>
                ))}
              </ul>
            </article>
            <article className="entity-card">
              <p className="panel-title">Invocations</p>
              <ul className="detail-list">
                {selectedRunDetail.invocations.map((invocation) => (
                  <li key={invocation.id}>
                    {invocation.backendLabel}: {invocation.status}
                    {invocation.sessionId ? ` · session ${invocation.sessionId}` : ""}
                    {invocation.pid ? ` · pid ${invocation.pid}` : ""}
                  </li>
                ))}
              </ul>
            </article>
            <article className="entity-card">
              <p className="panel-title">Writebacks</p>
              <ul className="detail-list">
                {selectedRunDetail.writebacks.length > 0 ? (
                  selectedRunDetail.writebacks.map((writeback) => (
                    <li key={writeback.id}>
                      {writeback.title}: {writeback.status} ({writeback.impactScope})
                    </li>
                  ))
                ) : (
                  <li>No writebacks attached to this run.</li>
                )}
              </ul>
            </article>
            <article className="entity-card">
              <p className="panel-title">Evaluator Findings</p>
              <ul className="detail-list">
                {selectedRunDetail.evaluations.length > 0 ? (
                  selectedRunDetail.evaluations.flatMap((evaluation) =>
                    evaluation.findings.map((finding) => (
                      <li key={finding.id}>
                        {finding.findingKind}: {finding.summary}
                      </li>
                    )),
                  )
                ) : (
                  <li>No structured findings recorded for this run.</li>
                )}
              </ul>
            </article>
          </div>
        </section>
      ) : null}
    </div>
  );
}
