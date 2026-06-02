import { notFound } from "next/navigation";

import { PageShell } from "@/components/layout/PageShell";
import { NextActionPanel } from "@/components/next-action/NextActionPanel";
import { TaskiProjectSurface } from "@/components/projects/TaskiProjectSurface";
import { getCaller } from "@/server/caller";

export default async function ProjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<React.JSX.Element> {
  const { id } = await params;
  const caller = await getCaller();
  const [result, taskiSummary, actions] = await Promise.all([
    caller.knowledge.projectDossier({ projectId: id }),
    caller.projects.taskiSummary({ projectId: id }),
    caller.nextAction.getForProject({ projectId: id, limit: 12 }),
  ]);

  if (!result || !taskiSummary) {
    notFound();
  }

  return (
    <PageShell title={result.title} subtitle="Taski-led operating summary connected to durable project knowledge and orchestration state.">
      <NextActionPanel actions={actions} projectId={id} />
      <TaskiProjectSurface summary={taskiSummary} dossier={result} />
    </PageShell>
  );
}
