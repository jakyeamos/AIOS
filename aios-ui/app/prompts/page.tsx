import Link from "next/link";

import { PageShell } from "@/components/layout/PageShell";
import { PatternTable } from "@/components/panels/PatternTable";
import { PromptCard } from "@/components/panels/PromptCard";
import type { Pattern, Prompt, PromptTemplate } from "@/lib/types";
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

const sortPrompts = (rows: Prompt[]): Prompt[] =>
  [...rows].sort((left, right) => {
    const leftScore = left.outcomeScore ?? -1;
    const rightScore = right.outcomeScore ?? -1;

    return rightScore - leftScore;
  });

const sortTemplates = (rows: PromptTemplate[]): PromptTemplate[] =>
  [...rows].sort((left, right) => left.name.localeCompare(right.name));

export default async function PromptsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const [templates, prompts, patterns] = await Promise.all([
    caller.prompts.templates(),
    caller.prompts.list({ limit: 200 }),
    caller.patterns.list({ limit: 200 }),
  ]);

  const query = await searchParams;

  const promptClassFilter = getSingleValue(query.promptClass) ?? "all";
  const promptSearch = (getSingleValue(query.promptQ) ?? "").trim().toLowerCase();
  const templateSearch = (getSingleValue(query.templateQ) ?? "").trim().toLowerCase();

  const patternStateFilter = getSingleValue(query.patternState) ?? "all";
  const patternApprovalFilter = getSingleValue(query.patternApproval) ?? "all";
  const patternSearch = (getSingleValue(query.patternQ) ?? "").trim().toLowerCase();
  const patternSort = parsePatternSortKey(getSingleValue(query.patternSort));
  const patternDir = parseSortDirection(getSingleValue(query.patternDir));

  const filteredPrompts = sortPrompts(
    prompts.filter((prompt) => {
      if (promptClassFilter !== "all" && prompt.classification !== promptClassFilter) {
        return false;
      }

      if (promptSearch.length === 0) {
        return true;
      }

      return (
        prompt.sessionId.toLowerCase().includes(promptSearch) ||
        (prompt.promptHash ?? "").toLowerCase().includes(promptSearch) ||
        (prompt.promptText ?? "").toLowerCase().includes(promptSearch)
      );
    }),
  );

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
      if (patternStateFilter !== "all" && pattern.state !== patternStateFilter) {
        return false;
      }

      if (patternApprovalFilter === "approved" && !pattern.humanApproved) {
        return false;
      }

      if (patternApprovalFilter === "unapproved" && pattern.humanApproved) {
        return false;
      }

      if (patternSearch.length === 0) {
        return true;
      }

      return pattern.id.toLowerCase().includes(patternSearch);
    }),
    patternSort,
    patternDir,
  );

  return (
    <PageShell
      title="Prompts & Rules"
      subtitle="Reusable prompt templates, observed prompt history, and promotion status."
    >
      <section className="panel-card">
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
          <input type="hidden" name="promptClass" value={promptClassFilter} />
          <input type="hidden" name="promptQ" value={promptSearch} />
          <input type="hidden" name="patternState" value={patternStateFilter} />
          <input type="hidden" name="patternApproval" value={patternApprovalFilter} />
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
      <div className="grid grid-2">
        <section>
          <h3 className="section-title">Recent Prompts</h3>
          <form className="toolbar" method="get">
            <label>
              Classification
              <select name="promptClass" defaultValue={promptClassFilter}>
                <option value="all">all</option>
                <option value="debugging">debugging</option>
                <option value="planning">planning</option>
                <option value="refactor">refactor</option>
                <option value="review">review</option>
                <option value="explain">explain</option>
                <option value="implement">implement</option>
                <option value="other">other</option>
              </select>
            </label>
            <label>
              Search
              <input name="promptQ" defaultValue={promptSearch} placeholder="hash, session, text" />
            </label>
            <input type="hidden" name="patternState" value={patternStateFilter} />
            <input type="hidden" name="patternApproval" value={patternApprovalFilter} />
            <input type="hidden" name="patternQ" value={patternSearch} />
            <input type="hidden" name="patternSort" value={patternSort} />
            <input type="hidden" name="patternDir" value={patternDir} />
            <input type="hidden" name="templateQ" value={templateSearch} />
            <button type="submit">Apply</button>
          </form>
          <div className="stack">
            {filteredPrompts.slice(0, 40).map((prompt) => (
              <PromptCard key={prompt.id} prompt={prompt} />
            ))}
          </div>
        </section>

        <section>
          <h3 className="section-title">Pattern Candidates</h3>
          <form className="toolbar" method="get">
            <label>
              State
              <select name="patternState" defaultValue={patternStateFilter}>
                <option value="all">all</option>
                <option value="notice">notice</option>
                <option value="observation">observation</option>
                <option value="hypothesis">hypothesis</option>
                <option value="rule">rule</option>
              </select>
            </label>
            <label>
              Approval
              <select name="patternApproval" defaultValue={patternApprovalFilter}>
                <option value="all">all</option>
                <option value="approved">approved</option>
                <option value="unapproved">unapproved</option>
              </select>
            </label>
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
              <input name="patternQ" defaultValue={patternSearch} placeholder="pattern id" />
            </label>
            <input type="hidden" name="promptClass" value={promptClassFilter} />
            <input type="hidden" name="promptQ" value={promptSearch} />
            <input type="hidden" name="templateQ" value={templateSearch} />
            <button type="submit">Apply</button>
          </form>

          <PatternTable patterns={filteredPatterns} />

          <p className="panel-subtitle">
            Tip: pattern IDs prefixed with <code>id:</code> represent single prompt instances with no hash.
            Hash-based IDs aggregate repeated prompt usage.
          </p>

          <p className="panel-subtitle">
            Open hash detail views directly from prompt cards, or use <Link href="/prompts">this page</Link> filters
            to isolate reusable candidates.
          </p>
        </section>
      </div>
    </PageShell>
  );
}
