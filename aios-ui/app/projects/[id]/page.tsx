import { notFound } from "next/navigation";

import { PageShell } from "@/components/layout/PageShell";
import { TaskiProjectSurface } from "@/components/projects/TaskiProjectSurface";
import { getCaller } from "@/server/caller";

export default async function ProjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<React.JSX.Element> {
  const { id } = await params;
  const caller = await getCaller();
  const [result, taskiSummary] = await Promise.all([
    caller.knowledge.projectDossier({ projectId: id }),
    caller.projects.taskiSummary({ projectId: id }),
  ]);

  if (!result || !taskiSummary) {
    notFound();
  }

  return (
    <PageShell title={result.title} subtitle="Taski-led operating summary connected to durable project knowledge and orchestration state.">
      <TaskiProjectSurface summary={taskiSummary} dossier={result} />
    </PageShell>
  );
}
