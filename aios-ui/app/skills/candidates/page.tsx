import Link from "next/link";

import { PageShell } from "@/components/layout/PageShell";
import { formatDateTime } from "@/lib/format";
import { getCaller } from "@/server/caller";

export const dynamic = "force-dynamic";

export default async function SkillCandidatesPage(): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const items = await caller.divergent.promotionItems();

  return (
    <PageShell
      title="Skill Candidates"
      subtitle="Prompt, skill, judge, and workflow promotion gates with evidence requirements."
    >
      <section className="panel-card">
        <div className="table-head" style={{ gridTemplateColumns: "1fr 0.7fr 0.8fr 1.6fr 0.8fr" }}>
          <span>Item</span>
          <span>Kind</span>
          <span>Status</span>
          <span>Reason</span>
          <span>Updated</span>
        </div>
        {items.length === 0 ? (
          <p className="panel-subtitle">No promotion lifecycle items are stored yet.</p>
        ) : (
          items.map((item) => (
            <div key={item.id} className="table-row" style={{ gridTemplateColumns: "1fr 0.7fr 0.8fr 1.6fr 0.8fr" }}>
              <span>
                {item.sourceRunId ? (
                  <Link href={`/runs/divergent/${item.sourceRunId}`}>{item.itemKey}</Link>
                ) : (
                  item.itemKey
                )}
              </span>
              <span>{item.itemKind}</span>
              <span>{item.status}</span>
              <span>{item.statusReason}</span>
              <span>{formatDateTime(item.updatedAt)}</span>
            </div>
          ))
        )}
      </section>
    </PageShell>
  );
}
