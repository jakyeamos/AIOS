import { PageShell } from "@/components/layout/PageShell";
import { SearchResults } from "@/components/search/SearchResults";
import type { EntityKind } from "@/lib/control-plane";
import { getCaller } from "@/server/caller";

export const dynamic = "force-dynamic";

type SearchParams = Record<string, string | string[] | undefined>;

const entityKinds = new Set<EntityKind>([
  "run",
  "packet",
  "writeback",
  "finding",
  "prompt_template",
  "prompt_use",
  "skill",
  "workflow",
  "knowledge_object",
  "route_decision",
  "delta_item",
  "backfill_task",
  "automation",
  "experiment",
  "divergent_run",
  "learning_pattern",
  "promotion_lifecycle_item",
]);

const toArray = (value: string | string[] | undefined): string[] => {
  if (Array.isArray(value)) {
    return value;
  }
  return value ? [value] : [];
};

const parseKinds = (value: string | string[] | undefined): EntityKind[] | undefined => {
  const kinds = toArray(value).filter((kind): kind is EntityKind => entityKinds.has(kind as EntityKind));
  return kinds.length > 0 ? kinds : undefined;
};

const firstValue = (value: string | string[] | undefined): string | undefined =>
  Array.isArray(value) ? value[0] : value;

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}): Promise<React.JSX.Element> {
  const query = await searchParams;
  const caller = await getCaller();
  const searchText = firstValue(query.query) ?? "";
  const selectedKinds = parseKinds(query.kinds);
  const projectId = firstValue(query.project) ?? null;
  const hits = await caller.operatorSearch.search({
    query: searchText,
    kinds: selectedKinds,
    projectId,
    limit: 100,
  });

  return (
    <PageShell title="Search" subtitle="Mixed-entity operator search with drill-down links to source evidence.">
      <form className="toolbar" method="get">
        <label>
          Query
          <input name="query" defaultValue={searchText} placeholder="run, workflow, writeback, delta" />
        </label>
        <button type="submit">Search</button>
      </form>
      <SearchResults hits={hits} query={searchText} selectedKinds={selectedKinds} projectId={projectId} />
    </PageShell>
  );
}
