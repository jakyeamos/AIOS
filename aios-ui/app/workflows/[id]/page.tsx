import { notFound } from "next/navigation";

import { WorkflowSandbox } from "@/components/workflows/WorkflowSandbox";
import { PageShell } from "@/components/layout/PageShell";
import { getCaller } from "@/server/caller";

export default async function WorkflowDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<React.JSX.Element> {
  const { id } = await params;
  const caller = await getCaller();
  const [proposal, skillKeys] = await Promise.all([
    caller.workflows.detail({ id }),
    caller.workflows.skillKeys(),
  ]);

  if (!proposal) {
    notFound();
  }

  return (
    <PageShell
      title={proposal.title}
      subtitle={proposal.summary}
    >
      <WorkflowSandbox proposal={proposal} skillKeys={skillKeys} />
    </PageShell>
  );
}
