"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { trpc } from "@/lib/trpc";

const useDebouncedValue = (value: string, delayMs: number): string => {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const handle = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(handle);
  }, [delayMs, value]);

  return debounced;
};

export function GlobalSearchInput(): React.JSX.Element {
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebouncedValue(query.trim(), 200);
  const enabled = debouncedQuery.length >= 2;
  const search = trpc.operatorSearch.search.useQuery(
    { query: debouncedQuery, limit: 5 },
    { enabled },
  );
  const hits = search.data ?? [];
  const seeAllHref = `/search?query=${encodeURIComponent(query.trim())}`;

  return (
    <div className="global-search">
      <label className="global-search-label" htmlFor="global-search-input">
        Search
      </label>
      <input
        id="global-search-input"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Search runs, packets, writebacks"
        autoComplete="off"
      />
      {enabled ? (
        <div className="global-search-results">
          {search.isLoading ? <p className="panel-subtitle">Loading matches...</p> : null}
          {!search.isLoading && hits.length === 0 ? (
            <p className="panel-subtitle">No matches yet. Open the full search page to broaden filters.</p>
          ) : null}
          {hits.map((hit) => (
            <Link
              key={`${hit.kind}-${hit.id}`}
              href={hit.drillDownPath}
              className="global-search-hit"
              onClick={() => setQuery("")}
            >
              <span className="panel-title">{hit.title}</span>
              <span className="entity-meta">
                {hit.kind} · score {hit.score.toFixed(2)}
              </span>
            </Link>
          ))}
          <Link href={seeAllHref} className="global-search-all" onClick={() => setQuery("")}>
            See all results
          </Link>
        </div>
      ) : null}
    </div>
  );
}
