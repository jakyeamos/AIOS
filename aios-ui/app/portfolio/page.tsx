import { PageShell } from "@/components/layout/PageShell";
import { StatusBadge } from "@/components/primitives/StatusBadge";
import { PortfolioProjectCard } from "@/components/portfolio/PortfolioProjectCard";
import { buildPortfolioProjection } from "@/server/aios/portfolio";
import { getCaller } from "@/server/caller";

export default async function PortfolioPage(): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const projects = await caller.projects.list({ limit: 100 });
  const projections = await Promise.all(
    projects.map(async (project) => {
      const dossier = await caller.knowledge.projectDossier({ projectId: project.id });

      return buildPortfolioProjection({ project, dossier });
    }),
  );
  const reviewCount = projections.filter((projection) => projection.confidenceLabel === "Review required").length;

  return (
    <PageShell
      title="Portfolio"
      subtitle="A review-ready projection of project progress, quality signals, and the next public milestone."
    >
      <section className="portfolio-hero panel-card">
        <div>
          <p className="portfolio-eyebrow">Public projection</p>
          <h3 className="portfolio-hero-title">Turn project truth into a story people can scan.</h3>
          <p className="portfolio-hero-copy">
            This surface translates operational evidence into readable project updates. It keeps raw paths, prompts,
            transcripts, and internal workflow language out of copy-ready output.
          </p>
        </div>
        <div className="portfolio-review-note">
          <StatusBadge status="warning" label="Review before publishing" />
          <p>Confirm the wording, add a screenshot or demo link, then publish manually.</p>
          <div className="portfolio-hero-stats">
            <div>
              <strong>{projections.length}</strong>
              <span>projects represented</span>
            </div>
            <div>
              <strong>{reviewCount}</strong>
              <span>need evidence review</span>
            </div>
          </div>
        </div>
      </section>

      <section aria-labelledby="portfolio-updates-title">
        <div className="portfolio-section-header">
          <div>
            <p className="portfolio-eyebrow">Project updates</p>
            <h3 id="portfolio-updates-title">A stronger public read on the work</h3>
          </div>
          <p>Each card gives you a narrative, proof points, a next step, and copy you can edit before sharing.</p>
        </div>

        {projections.length > 0 ? (
          <div className="portfolio-grid">
            {projections.map((projection) => (
              <PortfolioProjectCard key={projection.projectId} projection={projection} />
            ))}
          </div>
        ) : (
          <div className="portfolio-empty panel-card">
            <h3>No projects are ready for a portfolio projection yet.</h3>
            <p>Project activity and quality signals will appear here once AIOS has a project record to summarize.</p>
          </div>
        )}
      </section>
    </PageShell>
  );
}
