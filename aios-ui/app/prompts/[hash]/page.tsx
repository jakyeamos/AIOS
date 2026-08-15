import { PageShell } from "@/components/layout/PageShell";
import { PromptCard } from "@/components/panels/PromptCard";
import { getCaller } from "@/server/caller";

export const dynamic = "force-dynamic";

export default async function PromptDetailPage({
  params,
}: {
  params: Promise<{ hash: string }>;
}): Promise<React.JSX.Element> {
  const { hash } = await params;
  const caller = await getCaller();
  const prompts = await caller.prompts.byHash({ hash, limit: 100 });

  return (
    <PageShell title={`Prompt ${hash}`} subtitle="Historical usage and outcomes for this prompt hash.">
      <div className="stack">
        {prompts.map((prompt) => (
          <PromptCard key={prompt.id} prompt={prompt} />
        ))}
      </div>
    </PageShell>
  );
}
