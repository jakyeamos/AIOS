/* eslint-disable anti-slop/require-empty-state-action */
import Link from "next/link";

import type { EntityKind, OperatorSearchHit } from "@/lib/control-plane";
import { formatDateTime } from "@/lib/format";

type SearchResultsProps = {
  hits: OperatorSearchHit[];
  query: string;
  selectedKinds?: EntityKind[];
  projectId?: string | null;
};

const kindLabel = (kind: EntityKind): string => kind.replaceAll("_", " ");

const buildKindHref = (query: string, kind: EntityKind, projectId: string | null | undefined): string => {
  const params = new URLSearchParams();
  if (query.length > 0) {
    params.set("query", query);
  }
  params.append("kinds", kind);
  if (projectId) {
    params.set("project", projectId);
  }
  return `/search?${params.toString()}`;
};

export function SearchResults({
  hits,
  query,
  selectedKinds = [],
  projectId,
}: SearchResultsProps): React.JSX.Element {
  const counts = hits.reduce((map, hit) => map.set(hit.kind, (map.get(hit.kind) ?? 0) + 1), new Map<EntityKind, number>());
  const kinds = Array.from(counts.keys()).sort();
  const title = query.length > 0 ? `Results for "${query}"` : "Recent activity";

  return (
    <div className="search-layout">
      <aside className="panel-card">
        <h3 className="section-title">Facets</h3>
        <div className="chip-row">
          {kinds.length > 0 ? (
            kinds.map((kind) => (
              <Link
                key={kind}
                href={buildKindHref(query, kind, projectId)}
                className={selectedKinds.includes(kind) ? "button-primary" : "button-secondary"}
              >
                {kindLabel(kind)} ({counts.get(kind)})
              </Link>
            ))
          ) : (
            <Link href="/search" className="button-secondary">
              Reset search
            </Link>
          )}
        </div>
      </aside>
      <section className="panel-card">
        <div className="panel-row">
          <div>
            <h3 className="section-title">{title}</h3>
            <p className="panel-subtitle">Every result includes a drill-in link to the source evidence.</p>
          </div>
        </div>
        <div className="stack">
          {hits.length > 0 ? (
            hits.map((hit) => (
              <article key={`${hit.kind}-${hit.id}`} className="entity-card">
                <div className="panel-row">
                  <div>
                    <p className="panel-title">{hit.title}</p>
                    <p className="panel-subtitle">{hit.summary || "No summary was projected for this row."}</p>
                  </div>
                  <Link href={hit.drillDownPath} className="button-secondary">
                    Drill in
                  </Link>
                </div>
                <p className="entity-meta">
                  {kindLabel(hit.kind)} · {hit.sourceTable} · score {hit.score.toFixed(2)} · updated{" "}
                  {formatDateTime(hit.lastUpdatedAt)}
                </p>
              </article>
            ))
          ) : (
            <article className="entity-card">
              <p className="panel-subtitle">No rows match these filters. Clear the facets or try a broader query.</p>
              <Link href="/search" className="button-secondary">
                Clear filters
              </Link>
            </article>
          )}
        </div>
      </section>
    </div>
  );
}
