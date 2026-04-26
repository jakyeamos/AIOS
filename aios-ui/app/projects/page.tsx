import Link from "next/link";

import { PageShell } from "@/components/layout/PageShell";
import { StatusBadge } from "@/components/primitives/StatusBadge";
import { getCaller } from "@/server/caller";

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
        <div className="table-head">
          <span>Name</span>
          <span>Health</span>
          <span>Critical</span>
          <span>Pipeline</span>
          <span>Unknown</span>
          <span>Sessions</span>
          <span>Open Bugs</span>
          <span>Status</span>
        </div>
        {projects.map((project) => (
          <div key={project.id} className="table-row">
            <span>
              <Link href={`/projects/${project.id}`}>{project.name}</Link>
            </span>
            <span>{project.healthScore === null ? "n/a" : `${project.healthScore.toFixed(2)} (${project.healthTrend?.toFixed(2) ?? "0.00"})`}</span>
            <span>{project.criticalDeltaCount}</span>
            <span>
              <StatusBadge
                status={pipelineTone(project.pipelineStatus)}
                label={`${project.pipelineConfiguredRequired}/${project.pipelineRequired} ${project.pipelineStatus}`}
              />
            </span>
            <span>{project.unknownCoverage === null ? "n/a" : `${(project.unknownCoverage * 100).toFixed(1)}%`}</span>
            <span>{project.sessionCount}</span>
            <span>{project.openBugs}</span>
            <span>
              <StatusBadge status={project.status === "active" ? "healthy" : "unknown"} label={project.status} />
            </span>
          </div>
        ))}
      </section>
    </PageShell>
  );
}
