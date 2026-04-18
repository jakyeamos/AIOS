import { ControlPlaneStudio } from "@/components/control/ControlPlaneStudio";
import { PageShell } from "@/components/layout/PageShell";
import { getCaller } from "@/server/caller";

export default async function ControlPlanePage(): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const [overview, projects] = await Promise.all([
    caller.controlPlane.overview(),
    caller.projects.list({ limit: 100 }),
  ]);

  return (
    <PageShell
      title="Control Plane"
      subtitle="Explicit routing, workflow templates, agent registry, and packet generation for delegated work."
    >
      <ControlPlaneStudio
        projects={projects.map((project) => ({ id: project.id, name: project.name }))}
        workflowTemplates={overview.workflowTemplates}
        agentProfiles={overview.agentProfiles}
        recentRuns={overview.runs}
        recentPackets={overview.packets}
      />
    </PageShell>
  );
}
