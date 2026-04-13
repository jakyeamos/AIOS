import Link from "next/link";

import { PageShell } from "@/components/layout/PageShell";
import { StatusBadge } from "@/components/primitives/StatusBadge";
import { getCaller } from "@/server/caller";

export default async function ProjectsPage(): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const projects = await caller.projects.list({ limit: 100 });

  return (
    <PageShell title="Projects" subtitle="Per-project activity, health, and open issues.">
      <section className="panel-card">
        <div className="table-head">
          <span>Name</span>
          <span>Sessions</span>
          <span>Open Bugs</span>
          <span>Status</span>
        </div>
        {projects.map((project) => (
          <div key={project.id} className="table-row">
            <span>
              <Link href={`/projects/${project.id}`}>{project.name}</Link>
            </span>
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
