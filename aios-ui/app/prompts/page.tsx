import { PageShell } from "@/components/layout/PageShell";
import type { PromptTemplate } from "@/lib/types";
import { getCaller } from "@/server/caller";

type SearchParams = Record<string, string | string[] | undefined>;

const getSingleValue = (value: string | string[] | undefined): string | undefined => {
  if (Array.isArray(value)) {
    return value[0];
  }

  return value;
};

const sortTemplates = (rows: PromptTemplate[]): PromptTemplate[] =>
  [...rows].sort((left, right) => left.name.localeCompare(right.name));

export default async function PromptsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const templates = await caller.prompts.templates();

  const query = await searchParams;

  const templateSearch = (getSingleValue(query.templateQ) ?? "").trim().toLowerCase();

  const filteredTemplates = sortTemplates(
    templates.filter((template) => {
      if (templateSearch.length === 0) {
        return true;
      }

      return (
        template.name.toLowerCase().includes(templateSearch) ||
        template.id.toLowerCase().includes(templateSearch) ||
        template.classification.toLowerCase().includes(templateSearch) ||
        template.purpose.toLowerCase().includes(templateSearch) ||
        template.tags.some((tag) => tag.toLowerCase().includes(templateSearch))
      );
    }),
  );

  return (
    <PageShell
      title="Prompt Library"
      subtitle="Reusable, versioned prompt templates for recurring AIOS workflows."
    >
      <section className="panel-card" id="prompt-library">
        <div className="panel-row">
          <div>
            <h3 className="section-title">Prompt Library</h3>
            <p className="panel-subtitle">Versioned templates loaded from <code>/Users/jakyeamos/AIOS/prompts</code>.</p>
          </div>
          <span className="mono">{filteredTemplates.length} templates</span>
        </div>
        <form className="toolbar" method="get">
          <label>
            Search
            <input name="templateQ" defaultValue={templateSearch} placeholder="name, tag, classification" />
          </label>
          <button type="submit">Apply</button>
        </form>
        <div className="grid grid-2">
          {filteredTemplates.map((template) => (
            <article key={template.id} className="entity-card">
              <div className="panel-row">
                <div>
                  <h4 className="panel-title">{template.name}</h4>
                  <p className="panel-subtitle">{template.purpose}</p>
                </div>
                <span className="status-badge status-healthy">
                  <span className="status-dot" />
                  {template.classification}
                </span>
              </div>
              <div className="badge-row">
                {template.tags.map((tag) => (
                  <span key={tag} className="provenance-badge">
                    {tag}
                  </span>
                ))}
              </div>
              <p className="entity-meta">
                v{template.version} · updated {template.lastUpdated} · <code>{template.file}</code>
              </p>
              <p className="entity-meta">
                Required: {template.requiredInputs.join("; ") || "none recorded"}
              </p>
            </article>
          ))}
        </div>
      </section>
    </PageShell>
  );
}
