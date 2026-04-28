import Link from "next/link";

import { KnowledgeIndex } from "@/components/knowledge/KnowledgePageView";
import { PageShell } from "@/components/layout/PageShell";
import type { KnowledgePageSummary } from "@/lib/control-plane";
import { getCaller } from "@/server/caller";

type SearchParams = Record<string, string | string[] | undefined>;

const filterPages = (pages: KnowledgePageSummary[], q: string): KnowledgePageSummary[] => {
  const lower = q.toLowerCase();
  return pages.filter(
    (page) =>
      page.title.toLowerCase().includes(lower) ||
      page.summary.toLowerCase().includes(lower),
  );
};

export default async function KnowledgePage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const grouped = await caller.knowledge.grouped();
  const query = await searchParams;
  const q = (Array.isArray(query.q) ? query.q[0] : query.q ?? "").trim();

  const project = q ? filterPages(grouped.project, q) : grouped.project;
  const decision = q ? filterPages(grouped.decision, q) : grouped.decision;
  const concept = q ? filterPages(grouped.concept, q) : grouped.concept;
  const system = q ? filterPages(grouped.system, q) : grouped.system;
  const workflow = q ? filterPages(grouped.workflow, q) : grouped.workflow;
  const agent = q ? filterPages(grouped.agent, q) : grouped.agent;

  const totalResults = q ? project.length + decision.length + concept.length + system.length + workflow.length + agent.length : null;

  return (
    <PageShell
      title="Knowledge Index"
      subtitle="Wikipedia-like pages for projects, decisions, workflows, agents, and system contracts."
    >
      <form className="toolbar" method="get">
        <label>
          Search
          <input name="q" defaultValue={q} placeholder="Search pages by title or summary…" autoComplete="off" />
        </label>
        <button type="submit">Search</button>
        {q ? <Link href="/knowledge" className="button-secondary">Clear</Link> : null}
      </form>
      {totalResults !== null ? (
        <p className="panel-subtitle">{totalResults} result{totalResults !== 1 ? "s" : ""} for &ldquo;{q}&rdquo;</p>
      ) : null}
      <div className="grid grid-2">
        <KnowledgeIndex title="Projects" pages={project} />
        <KnowledgeIndex title="Decisions" pages={decision} />
      </div>
      <div className="grid grid-2">
        <KnowledgeIndex title="Concepts" pages={concept} />
        <KnowledgeIndex title="Systems" pages={system} />
      </div>
      <div className="grid grid-2">
        <KnowledgeIndex title="Workflows" pages={workflow} />
        <KnowledgeIndex title="Agents" pages={agent} />
      </div>
    </PageShell>
  );
}
