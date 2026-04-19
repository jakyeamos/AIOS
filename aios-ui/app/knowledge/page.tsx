import { KnowledgeIndex } from "@/components/knowledge/KnowledgePageView";
import { PageShell } from "@/components/layout/PageShell";
import { getCaller } from "@/server/caller";

export default async function KnowledgePage(): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const grouped = await caller.knowledge.grouped();

  return (
    <PageShell
      title="Knowledge Index"
      subtitle="Wikipedia-like pages for projects, decisions, workflows, agents, and system contracts."
    >
      <div className="grid grid-2">
        <KnowledgeIndex title="Projects" pages={grouped.project} />
        <KnowledgeIndex title="Decisions" pages={grouped.decision} />
      </div>
      <div className="grid grid-2">
        <KnowledgeIndex title="Concepts" pages={grouped.concept} />
        <KnowledgeIndex title="Systems" pages={grouped.system} />
      </div>
      <div className="grid grid-2">
        <KnowledgeIndex title="Workflows" pages={grouped.workflow} />
        <KnowledgeIndex title="Agents" pages={grouped.agent} />
      </div>
    </PageShell>
  );
}
