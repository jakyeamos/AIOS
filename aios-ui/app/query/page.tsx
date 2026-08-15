import { PageShell } from "@/components/layout/PageShell";
import { GroundedQueryStudio } from "@/components/query/GroundedQueryStudio";
import { getCaller } from "@/server/caller";

export const dynamic = "force-dynamic";

export default async function QueryPage(): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const projects = await caller.projects.list({ limit: 100 });

  return (
    <PageShell
      title="Grounded Query"
      subtitle="Retrieve from AIOS knowledge and workflow state with explicit facts, inference, recommendations, and citations."
    >
      <GroundedQueryStudio projects={projects.map((project) => ({ id: project.id, name: project.name }))} />
    </PageShell>
  );
}
