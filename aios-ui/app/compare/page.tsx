import Link from "next/link";

import { PageShell } from "@/components/layout/PageShell";
import { getCaller } from "@/server/caller";

export default async function ComparePage(): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const experiments = await caller.experiments.list();

  return (
    <PageShell title="Diff & Compare" subtitle="Side-by-side comparisons for workflow and prompt changes.">
      <section className="panel-card">
        <div className="table-head">
          <span>Experiment</span>
          <span>Surface</span>
          <span>Winner</span>
          <span>Open</span>
        </div>
        {experiments.map((experiment) => (
          <div key={experiment.id} className="table-row">
            <span>{experiment.name}</span>
            <span>{experiment.surface}</span>
            <span>{experiment.winner ?? "-"}</span>
            <span>
              <Link href={`/compare/${experiment.id}/baseline`}>view</Link>
            </span>
          </div>
        ))}
      </section>
    </PageShell>
  );
}
