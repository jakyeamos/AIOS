import { notFound } from "next/navigation";

import { PageShell } from "@/components/layout/PageShell";
import { SessionCard } from "@/components/panels/SessionCard";
import { getCaller } from "@/server/caller";

export default async function ProjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<React.JSX.Element> {
  const { id } = await params;
  const caller = await getCaller();
  const result = await caller.projects.detail({ id });

  if (!result.project) {
    notFound();
  }

  return (
    <PageShell title={result.project.name} subtitle={result.project.repoPath}>
      <section>
        <h3 className="section-title">Recent Sessions</h3>
        <div className="stack">
          {result.sessions.map((session) => (
            <SessionCard key={session.id} session={session} />
          ))}
        </div>
      </section>
    </PageShell>
  );
}
