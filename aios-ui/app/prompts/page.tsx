import { PageShell } from "@/components/layout/PageShell";
import { PatternTable } from "@/components/panels/PatternTable";
import type { Pattern, PromptTemplate } from "@/lib/types";
import { getCaller } from "@/server/caller";

type SearchParams = Record<string, string | string[] | undefined>;

type PatternSortKey = "sessions" | "lastSeen" | "state" | "id";
type SortDirection = "asc" | "desc";

const getSingleValue = (value: string | string[] | undefined): string | undefined => {
  if (Array.isArray(value)) {
    return value[0];
  }

  return value;
};

const parseSortDirection = (value: string | undefined): SortDirection =>
  value === "asc" ? "asc" : "desc";

const parsePatternSortKey = (value: string | undefined): PatternSortKey => {
  if (value === "sessions" || value === "lastSeen" || value === "state" || value === "id") {
    return value;
  }

  return "sessions";
};

const sortPatterns = (rows: Pattern[], sortKey: PatternSortKey, dir: SortDirection): Pattern[] => {
  const sorted = [...rows].sort((left, right) => {
    if (sortKey === "sessions") {
      return left.sessionCount - right.sessionCount;
    }

    if (sortKey === "lastSeen") {
      return left.lastSeen.localeCompare(right.lastSeen);
    }

    if (sortKey === "state") {
      return left.state.localeCompare(right.state);
    }

    return left.id.localeCompare(right.id);
  });

  return dir === "asc" ? sorted : sorted.reverse();
};

const sortTemplates = (rows: PromptTemplate[]): PromptTemplate[] =>
  [...rows].sort((left, right) => left.name.localeCompare(right.name));

export default async function PromptsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const [templates, patterns] = await Promise.all([
    caller.prompts.templates(),
    caller.patterns.list({ limit: 100, minSessionCount: 4 }),
  ]);

  const query = await searchParams;

  const templateSearch = (getSingleValue(query.templateQ) ?? "").trim().toLowerCase();

  const patternSearch = (getSingleValue(query.patternQ) ?? "").trim().toLowerCase();
  const patternSort = parsePatternSortKey(getSingleValue(query.patternSort));
  const patternDir = parseSortDirection(getSingleValue(query.patternDir));

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

  const filteredPatterns = sortPatterns(
    patterns.filter((pattern) => {
      if (patternSearch.length === 0) {
        return true;
      }

      return (
        pattern.id.toLowerCase().includes(patternSearch) ||
        (pattern.label ?? "").toLowerCase().includes(patternSearch)
      );
    }),
    patternSort,
    patternDir,
  );

  return (
    <PageShell
      title="Prompts & Rules"
      subtitle="Reusable prompt templates and mature repeated rules."
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
          <input type="hidden" name="patternQ" value={patternSearch} />
          <input type="hidden" name="patternSort" value={patternSort} />
          <input type="hidden" name="patternDir" value={patternDir} />
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
      <section>
        <div className="panel-row">
          <div>
            <h3 className="section-title">Mature Patterns</h3>
            <p className="panel-subtitle">Only approved rules or repeated prompt patterns seen in 4+ sessions.</p>
          </div>
          <span className="mono">{filteredPatterns.length} patterns</span>
        </div>
        <form className="toolbar" method="get">
          <label>
            Sort
            <select name="patternSort" defaultValue={patternSort}>
              <option value="sessions">sessions</option>
              <option value="lastSeen">last seen</option>
              <option value="state">state</option>
              <option value="id">id</option>
            </select>
          </label>
          <label>
            Dir
            <select name="patternDir" defaultValue={patternDir}>
              <option value="desc">desc</option>
              <option value="asc">asc</option>
            </select>
          </label>
          <label>
            Search
            <input name="patternQ" defaultValue={patternSearch} placeholder="pattern text or id" />
          </label>
          <input type="hidden" name="templateQ" value={templateSearch} />
          <button type="submit">Apply</button>
        </form>

        <PatternTable patterns={filteredPatterns} />
      </section>
    </PageShell>
  );
}
