"use client";

import { useState } from "react";

import type { AgentProfile, BriefingPacket, OrchestrationRun, WorkflowTemplate } from "@/lib/control-plane";
import { trpc } from "@/lib/trpc";

type ProjectOption = {
  id: string;
  name: string;
};

type ControlPlaneStudioProps = {
  projects: ProjectOption[];
  workflowTemplates: WorkflowTemplate[];
  agentProfiles: AgentProfile[];
  recentRuns: OrchestrationRun[];
  recentPackets: BriefingPacket[];
};

export function ControlPlaneStudio({
  projects,
  workflowTemplates,
  agentProfiles,
  recentRuns,
  recentPackets,
}: ControlPlaneStudioProps): React.JSX.Element {
  const [projectId, setProjectId] = useState<string>(projects[0]?.id ?? "");
  const [objective, setObjective] = useState(
    "Turn AIOS into an explicit knowledge and orchestration control plane.",
  );
  const planner = trpc.controlPlane.plan.useMutation();

  return (
    <div className="page-content">
      <section className="panel-card">
        <div className="panel-row">
          <div>
            <h3 className="section-title">Task Router</h3>
            <p className="panel-subtitle">
              Generate a briefing packet with explicit workflow selection, agent role, assumptions, and context trace.
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
              placeholder="Describe the task you want AIOS to route."
            />
          </label>
          <button
            type="button"
            className="button-primary"
            disabled={planner.isPending || objective.trim().length < 8}
            onClick={() =>
              planner.mutate({
                objective: objective.trim(),
                projectId: projectId || undefined,
              })
            }
          >
            {planner.isPending ? "Generating packet..." : "Generate packet"}
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
              </article>
            ))}
          </div>
        </section>

        <section className="panel-card">
          <h3 className="section-title">Agent Registry</h3>
          <div className="stack">
            {agentProfiles.map((agent) => (
              <article key={agent.key} className="entity-card">
                <p className="panel-title">{agent.name}</p>
                <p className="panel-subtitle">{agent.summary}</p>
                <p className="mono">{agent.bestFor.join(" · ")}</p>
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
            </div>
          </section>

          <section className="panel-card">
            <h3 className="section-title">Briefing Packet</h3>
            <div className="stack">
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
            </div>
          </section>
        </div>
      ) : null}

      <div className="grid grid-2">
        <section className="panel-card">
          <h3 className="section-title">Run History</h3>
          <div className="stack">
            {recentRuns.map((run) => (
              <article key={run.id} className="entity-card">
                <p className="panel-title">{run.objective}</p>
                <p className="panel-subtitle">
                  {run.projectName} · {run.workflowKey} · {run.agentKey}
                </p>
              </article>
            ))}
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
              </article>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
