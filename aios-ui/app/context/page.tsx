import { PageShell } from "@/components/layout/PageShell";
import { getContextCompilerOverview } from "@/server/aios/context-compiler";

export const dynamic = "force-dynamic";

const formatScore = (score: number): string => score.toFixed(2);

const formatDate = (value: string | null): string => {
  if (!value) {
    return "missing";
  }

  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
};

export default async function ContextCompilerPage(): Promise<React.JSX.Element> {
  const overview = await getContextCompilerOverview();
  const issueCount =
    overview.conflicts.length +
    overview.staleContext.length +
    overview.missingContext.length +
    overview.writebackCandidates.length;

  return (
    <PageShell
      title="Context Compiler"
      subtitle="File-backed context routing, selected packets, receipts, and writeback warnings."
    >
      <section className="grid grid-4">
        <article className="stat-card">
          <p className="stat-label">Loaded Context</p>
          <p className="stat-value">{overview.loadedFiles.length}</p>
          <p className="stat-delta">{overview.skippedContext.length} skipped</p>
        </article>
        <article className="stat-card">
          <p className="stat-label">Context Files</p>
          <p className="stat-value">{overview.inventory.totalFiles}</p>
          <p className="stat-delta">{overview.inventory.byTier.length} tiers indexed</p>
        </article>
        <article className="stat-card">
          <p className="stat-label">Warnings</p>
          <p className={`stat-value ${issueCount > 0 ? "text-warning" : "text-healthy"}`}>{issueCount}</p>
          <p className="stat-delta">conflicts, stale, missing, writebacks</p>
        </article>
        <article className="stat-card">
          <p className="stat-label">Receipt Updated</p>
          <p className="stat-value context-small-stat">{formatDate(overview.generatedAt)}</p>
          <p className="stat-delta">latest compiled packet</p>
        </article>
      </section>

      <section className="panel-card">
        <div className="panel-row">
          <div>
            <h3 className="section-title">Latest Task Packet</h3>
            <p className="panel-title">{overview.taskSummary}</p>
            <p className="panel-subtitle">
              {overview.exists
                ? "Compiled from the file-backed context tree."
                : "Run pnpm context:compile --task \"...\" to create the first packet, then refresh this page."}
            </p>
          </div>
          <div className="badge-row context-badge-row">
            {overview.domains.map((domain) => (
              <span key={domain} className="provenance-badge provenance-confirmed">
                {domain}
              </span>
            ))}
          </div>
        </div>
        <div className="chip-row context-chip-row">
          {overview.signals.map((signal) => (
            <span key={signal} className="status-badge status-unknown">
              <span className="status-dot" />
              {signal}
            </span>
          ))}
        </div>
      </section>

      <section className="panel-card" aria-label="Projection contract">
        <div className="panel-row">
          <div>
            <h3 className="section-title">Projection contract</h3>
            <p className="panel-subtitle">
              This satellite is a read-only view of the file-backed compiler output; the compiler CLI remains
              the only mutation owner.
            </p>
          </div>
          <span className="provenance-badge provenance-confirmed">read-only projection</span>
        </div>
        <div className="grid grid-2 context-contract-grid">
          <article className="entity-card">
            <p className="panel-title">Authority</p>
            <p className="panel-subtitle">{overview.projection.authority.owner}</p>
            <p className="panel-subtitle">
              Mutation owner: {overview.projection.authority.mutationOwner}
            </p>
          </article>
          <article className="entity-card">
            <p className="panel-title">Freshness</p>
            <p className="panel-subtitle">
              {overview.projection.freshness.state === "recorded"
                ? `Recorded ${formatDate(overview.projection.freshness.generatedAt)}`
                : "No compiled packet recorded"}
            </p>
            <p className="panel-subtitle">Next: {overview.projection.nextAction}</p>
          </article>
        </div>
      </section>

      <section className="panel-card">
        <h3 className="section-title">Loaded Context</h3>
        <div className="table-head table-context-loaded">
          <span>File</span>
          <span>Tier</span>
          <span>Priority</span>
          <span>Score</span>
          <span>Reason</span>
        </div>
        {overview.loadedFiles.map((file) => (
          <div key={`${file.id}-${file.path}`} className="table-row table-context-loaded">
            <span>
              <span className="mono">{file.id}</span>
              <span className="context-path">{file.path}</span>
            </span>
            <span>{file.tier}</span>
            <span>{file.priority}</span>
            <span className="mono">{formatScore(file.final_score)}</span>
            <span>{file.reason}</span>
          </div>
        ))}
      </section>

      <div className="grid grid-2">
        <section className="panel-card">
          <h3 className="section-title">Skipped Context</h3>
          <div className="stack">
            {overview.skippedContext.slice(0, 12).map((item) => (
              <article key={item} className="entity-card">
                <p className="panel-subtitle">{item}</p>
              </article>
            ))}
            {overview.skippedContext.length === 0 ? (
              <p className="panel-subtitle">No skipped context recorded; run the compiler with a concrete task.</p>
            ) : null}
          </div>
        </section>

        <section className="panel-card">
          <h3 className="section-title">Context Inventory</h3>
          <div className="context-tier-grid">
            {overview.inventory.byTier.map((tier) => (
              <article key={tier.tier} className="entity-card">
                <p className="panel-title">{tier.tier}</p>
                <p className="stat-value">{tier.count}</p>
              </article>
            ))}
          </div>
        </section>
      </div>

      <section className="panel-card">
        <h3 className="section-title">Warnings + Writebacks</h3>
        <div className="grid grid-2">
          <article className="entity-card">
            <p className="panel-title">Conflicts</p>
            <ul className="detail-list">
              {overview.conflicts.length > 0 ? (
                overview.conflicts.map((conflict) => (
                  <li key={`${conflict.topic}-${conflict.loser}`}>
                    {conflict.topic}: {conflict.winner} overrides {conflict.loser}. {conflict.resolution}
                  </li>
                ))
              ) : (
                <li>Clear after latest compile; rerun the compiler after changing priority or conflict metadata.</li>
              )}
            </ul>
          </article>
          <article className="entity-card">
            <p className="panel-title">Missing Context</p>
            <ul className="detail-list">
              {overview.missingContext.length > 0 ? (
                overview.missingContext.map((item) => (
                  <li key={`${item.suggested_file}-${item.reason}`}>
                    {item.suggested_file ?? "unspecified"}: {item.reason}
                  </li>
                ))
              ) : (
                <li>Clear after latest compile; add packets when task receipts call out gaps.</li>
              )}
            </ul>
          </article>
          <article className="entity-card">
            <p className="panel-title">Stale Context</p>
            <ul className="detail-list">
              {overview.staleContext.length > 0 ? (
                overview.staleContext.map((item) => (
                  <li key={item.id}>
                    {item.id}: last reviewed {item.lastReviewed}
                  </li>
                ))
              ) : (
                <li>Clear after latest compile; update last_reviewed when authoritative files change.</li>
              )}
            </ul>
          </article>
          <article className="entity-card">
            <p className="panel-title">Writeback Candidates</p>
            <ul className="detail-list">
              {overview.writebackCandidates.length > 0 ? (
                overview.writebackCandidates.map((item) => (
                  <li key={`${item.suggested_file}-${item.reason}`}>
                    {item.suggested_file ?? item.type ?? "candidate"}: {item.reason}
                  </li>
                ))
              ) : (
                <li>Clear after latest compile; rerun compilation after discovering reusable context.</li>
              )}
            </ul>
          </article>
        </div>
      </section>

      <section className="panel-card">
        <h3 className="section-title">Context Receipt</h3>
        <pre className="code-block context-receipt">
          {overview.receiptMarkdown || "No receipt found. Run pnpm context:compile --task \"...\", then refresh this page."}
        </pre>
      </section>
    </PageShell>
  );
}
