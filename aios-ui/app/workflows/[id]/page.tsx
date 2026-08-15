import { notFound } from "next/navigation";

import { GitHubSkillCandidates } from "@/components/workflows/GitHubSkillCandidates";
import { WorkflowSandbox } from "@/components/workflows/WorkflowSandbox";
import { PageShell } from "@/components/layout/PageShell";
import { getCaller } from "@/server/caller";

export const dynamic = "force-dynamic";

export default async function WorkflowDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<React.JSX.Element> {
  const { id } = await params;
  const caller = await getCaller();
  const [proposal, skillKeys, candidates] = await Promise.all([
    caller.workflows.detail({ id }),
    caller.workflows.skillKeys(),
    caller.workflows.skillCandidates({ workflowKey: id }),
  ]);

  if (!proposal) {
    notFound();
  }

  return (
    <PageShell title={proposal.title} subtitle={proposal.summary}>
      <WorkflowSandbox proposal={proposal} skillKeys={skillKeys} />
      {candidates.length > 0 && (
        <GitHubSkillCandidates candidates={candidates} />
      )}
    </PageShell>
  );
}
