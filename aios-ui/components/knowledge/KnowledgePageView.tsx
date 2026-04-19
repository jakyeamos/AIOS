import Link from "next/link";

import type { KnowledgePageDetail, KnowledgePageSummary } from "@/lib/control-plane";
import { StatusBadge } from "@/components/primitives/StatusBadge";

export function KnowledgeIndex({
  title,
  pages,
}: {
  title: string;
  pages: KnowledgePageSummary[];
}): React.JSX.Element {
  return (
    <section className="panel-card">
      <h3 className="section-title">{title}</h3>
      <div className="stack">
        {pages.map((page) => (
          <article key={page.slug} className="entity-card">
            <div className="panel-row">
              <div>
                <p className="panel-title">
                  <Link href={`/knowledge/${page.slug}`}>{page.title}</Link>
                </p>
                <p className="panel-subtitle">{page.summary}</p>
              </div>
              <StatusBadge status={page.status} />
            </div>
            <p className="entity-meta">
              {page.kind} · {page.freshness}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}

export function KnowledgePageView({ page }: { page: KnowledgePageDetail }): React.JSX.Element {
  return (
    <div className="page-content">
      <section className="panel-card">
        <div className="panel-row">
          <div>
            <p className="topbar-eyebrow">{page.kind}</p>
            <h3 className="section-title">{page.title}</h3>
            <p className="panel-subtitle">{page.summary}</p>
          </div>
          <StatusBadge status={page.status} />
        </div>
        <p className="entity-meta">
          {page.freshness} · confidence {(page.confidence * 100).toFixed(0)}%
        </p>
      </section>

      <div className="detail-grid">
        <section className="panel-card">
          <h3 className="section-title">Sections</h3>
          <div className="stack">
            {page.sections.map((section) => (
              <article key={section.title} className="entity-card">
                <p className="panel-title">{section.title}</p>
                {section.body ? <p className="panel-subtitle">{section.body}</p> : null}
                <ul className="detail-list">
                  {section.items.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </section>

        <section className="panel-card">
          <h3 className="section-title">Related</h3>
          <div className="stack">
            <article className="entity-card">
              <p className="panel-title">Relationships</p>
              <ul className="detail-list">
                {page.relationships.map((relationship) => (
                  <li key={`${relationship.relation}-${relationship.href}`}>
                    {relationship.relation}: <Link href={relationship.href}>{relationship.label}</Link>
                  </li>
                ))}
              </ul>
            </article>
            <article className="entity-card">
              <p className="panel-title">Backlinks</p>
              <ul className="detail-list">
                {page.backlinks.length > 0 ? (
                  page.backlinks.map((backlink) => (
                    <li key={`${backlink.relation}-${backlink.href}`}>
                      {backlink.relation}: <Link href={backlink.href}>{backlink.label}</Link>
                    </li>
                  ))
                ) : (
                  <li>No backlinks have been resolved for this page yet.</li>
                )}
              </ul>
            </article>
            <article className="entity-card">
              <p className="panel-title">References</p>
              <ul className="detail-list">
                {page.references.map((reference) => (
                  <li key={`${reference.label}-${reference.detail}`}>
                    <Link href={reference.href}>{reference.label}</Link>: {reference.detail}
                  </li>
                ))}
              </ul>
            </article>
            <article className="entity-card">
              <p className="panel-title">Recent Changes</p>
              <ul className="detail-list">
                {page.recentChanges.map((change) => (
                  <li key={change.id}>
                    {change.href ? <Link href={change.href}>{change.title}</Link> : change.title}: {change.summary}
                  </li>
                ))}
              </ul>
            </article>
          </div>
        </section>
      </div>
    </div>
  );
}
