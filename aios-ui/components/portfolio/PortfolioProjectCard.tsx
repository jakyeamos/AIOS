import Link from "next/link";

import { StatusBadge } from "@/components/primitives/StatusBadge";
import type { PortfolioProjectProjection } from "@/server/aios/portfolio";

import { PortfolioCopyButton } from "./PortfolioCopyButton";

type PortfolioProjectCardProps = {
  projection: PortfolioProjectProjection;
};

export function PortfolioProjectCard({ projection }: PortfolioProjectCardProps): React.JSX.Element {
  return (
    <article className={`portfolio-project-card portfolio-tone-${projection.statusTone}`}>
      <header className="portfolio-card-header">
        <div>
          <p className="portfolio-eyebrow">Project update</p>
          <h3 className="portfolio-card-title">{projection.projectName}</h3>
        </div>
        <StatusBadge status={projection.statusTone} label={projection.statusLabel} />
      </header>

      <p className="portfolio-narrative">{projection.narrative}</p>

      <div className="portfolio-proof-grid" aria-label={`${projection.projectName} current signals`}>
        {projection.proofPoints.map((point) => (
          <div key={point.label} className="portfolio-proof-point">
            <span className="portfolio-proof-label">{point.label}</span>
            <strong>{point.value}</strong>
          </div>
        ))}
      </div>

      <div className="portfolio-card-body">
        <section>
          <p className="portfolio-section-label">Recent progress</p>
          <ul className="portfolio-progress-list">
            {projection.progress.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>

        <section className="portfolio-next-step">
          <p className="portfolio-section-label">Next step</p>
          <p>{projection.nextStep}</p>
        </section>
      </div>

      <footer className="portfolio-card-footer">
        <span className="portfolio-meta">
          {projection.confidenceLabel} · {projection.updatedLabel}
        </span>
        <div className="portfolio-card-actions">
          <Link className="button-secondary" href={`/projects/${projection.projectId}`}>
            Inspect evidence
          </Link>
          <PortfolioCopyButton text={projection.copyText} />
        </div>
      </footer>

      <details className="portfolio-copy-preview">
        <summary>Preview public copy</summary>
        <pre>{projection.copyText}</pre>
      </details>
    </article>
  );
}
