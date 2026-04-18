import { notFound } from "next/navigation";

import { KnowledgePageView } from "@/components/knowledge/KnowledgePageView";
import { PageShell } from "@/components/layout/PageShell";
import { getCaller } from "@/server/caller";

export default async function KnowledgeDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<React.JSX.Element> {
  const { slug } = await params;
  const caller = await getCaller();
  const page = await caller.knowledge.detail({ slug });

  if (!page) {
    notFound();
  }

  return (
    <PageShell title={page.title} subtitle={page.summary}>
      <KnowledgePageView page={page} />
    </PageShell>
  );
}
