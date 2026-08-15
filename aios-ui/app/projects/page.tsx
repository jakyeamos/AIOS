import Link from "next/link";

import { PageShell } from "@/components/layout/PageShell";
import { StatusBadge } from "@/components/primitives/StatusBadge";
import { sourceLabel } from "@/lib/trusted-signals";
import { getCaller } from "@/server/caller";

export const dynamic = "force-dynamic";

const pipelineTone = (status: string): "healthy" | "warning" | "error" | "unknown" => {
  if (status === "healthy") {
    return "healthy";
  }
  if (status === "error" || status === "blocked") {
    return "error";
  }
  if (status === "warning") {
    return "warning";
  }
  return "unknown";
};

export default async function ProjectsPage(): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const projects = await caller.projects.list({ limit: 100 });

  return (
    <PageShell
      title="Projects"
      subtitle="Project dossiers are the durable memory surface for current state, rules, decisions, and recent changes."
    >
      <section className="panel-card">
        <div className="table-head table-projects">
          <span>Name</span>
          <span title="Composite health score on a 0-100 scale, with trend shown as a separate signal">Health</span>
          <span title="Number of high-severity changes flagged since last review">Critical Δ</span>
          <span title="CI/CD pipeline: configured checks / required checks">Pipeline</span>
          <span title="Fraction of surface area with unknown coverage">Unknown %</span>
          <span>Sessions</span>
          <span>Open Bugs</span>
          <span>Status</span>
        </div>
        {projects.map((project) => (
          <div key={project.id} className="table-row table-projects">
            <span>
              <Link href={`/projects/${project.id}`}>{project.name}</Link>
            </span>
            <span title={`${project.healthScoreSignal.explanation} Source: ${sourceLabel(project.healthScoreSignal)}`}>
              {project.healthScore === null ? "missing" : project.healthScore.toFixed(1)}
              <br />
              <span className="signal-note">
                trend {project.healthTrend === null ? "missing" : project.healthTrend.toFixed(1)}
              </span>
            </span>
            <span title={`${project.criticalDeltaSignal.explanation} Source: ${sourceLabel(project.criticalDeltaSignal)}`}>
              {project.criticalDeltaCount}
            </span>
            <span>
              <StatusBadge
                status={pipelineTone(project.pipelineStatus)}
                label={project.pipelineLabel}
              />
              <br />
              <span className={project.pipelineSignal.provenance === "contradictory" ? "signal-note text-error" : "signal-note"}>
                {project.pipelineSignal.provenance}
              </span>
            </span>
            <span title={`${project.unknownCoverageSignal.explanation} Source: ${sourceLabel(project.unknownCoverageSignal)}`}>
              {project.unknownCoverage === null ? "missing" : `${(project.unknownCoverage * 100).toFixed(1)}%`}
            </span>
            <span>{project.sessionCount}</span>
            <span>{project.openBugs}</span>
            <span>
              <StatusBadge status={project.status === "active" ? "healthy" : "unknown"} label={project.status} />
              <br />
              <span className="signal-note">{project.statusSignal.provenance}</span>
            </span>
          </div>
        ))}
      </section>
    </PageShell>
  );
}
