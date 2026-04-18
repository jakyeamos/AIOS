import { KnowledgeIndex } from "@/components/knowledge/KnowledgePageView";
import { PageShell } from "@/components/layout/PageShell";
import { StatCard } from "@/components/primitives/StatCard";
import { getCaller } from "@/server/caller";

export default async function CommandCenterPage(): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const [pages, control, changes, projects] = await Promise.all([
    caller.knowledge.grouped(),
    caller.controlPlane.overview(),
    caller.changes.list({ limit: 6 }),
    caller.projects.list({ limit: 6 }),
  ]);

  return (
    <PageShell
      title="AIOS Overview"
      subtitle="Canonical entry point for knowledge, grounded retrieval, workflow memory, and orchestration."
    >
      <div className="grid grid-4">
        <StatCard label="Knowledge Pages" value={Object.values(pages).flat().length} />
        <StatCard label="Projects" value={projects.length} />
        <StatCard label="Control Runs" value={control.runs.length} />
        <StatCard label="Packets" value={control.packets.length} />
      </div>

      <div className="grid grid-2">
        <KnowledgeIndex title="Projects" pages={pages.project.slice(0, 5)} />
        <KnowledgeIndex title="Decisions" pages={pages.decision.slice(0, 5)} />
      </div>

      <div className="grid grid-2">
        <section className="panel-card">
          <h3 className="section-title">Recent Orchestration Runs</h3>
          <div className="stack">
            {control.runs.slice(0, 6).map((run) => (
              <article key={run.id} className="entity-card">
                <p className="panel-title">{run.objective}</p>
                <p className="panel-subtitle">
                  {run.projectName} · {run.workflowKey} · {run.agentKey}
                </p>
              </article>
            ))}
          </div>
        </section>

        <section className="panel-card">
          <h3 className="section-title">What Changed</h3>
          <div className="stack">
            {changes.map((change) => (
              <article key={change.id} className="entity-card">
                <p className="panel-title">{change.title}</p>
                <p className="panel-subtitle">{change.summary}</p>
              </article>
            ))}
          </div>
        </section>
      </div>
    </PageShell>
  );
}
