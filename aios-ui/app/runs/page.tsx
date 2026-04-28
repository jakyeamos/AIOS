import Link from "next/link";

import { PageShell } from "@/components/layout/PageShell";
import { formatDateTime, formatDuration } from "@/lib/format";
import type { Session } from "@/lib/types";
import { getCaller } from "@/server/caller";

type SearchParams = Record<string, string | string[] | undefined>;

type RunSortKey =
  | "startedAt"
  | "durationMs"
  | "promptCount"
  | "toolEventCount"
  | "artifactCount"
  | "projectName"
  | "status";

type SortDirection = "asc" | "desc";

const getSingleValue = (value: string | string[] | undefined): string | undefined => {
  if (Array.isArray(value)) {
    return value[0];
  }

  return value;
};

const parseSortKey = (value: string | undefined): RunSortKey => {
  if (
    value === "startedAt" ||
    value === "durationMs" ||
    value === "promptCount" ||
    value === "toolEventCount" ||
    value === "artifactCount" ||
    value === "projectName" ||
    value === "status"
  ) {
    return value;
  }

  return "startedAt";
};

const parseSortDirection = (value: string | undefined): SortDirection =>
  value === "asc" ? "asc" : "desc";

const compareStrings = (left: string, right: string): number => left.localeCompare(right);

const compareNumbers = (left: number | null, right: number | null): number => {
  const normalizedLeft = left ?? -1;
  const normalizedRight = right ?? -1;

  return normalizedLeft - normalizedRight;
};

const sortSessions = (sessions: Session[], sortKey: RunSortKey, dir: SortDirection): Session[] => {
  const sorted = [...sessions].sort((left, right) => {
    if (sortKey === "startedAt") {
      return compareStrings(left.startedAt, right.startedAt);
    }

    if (sortKey === "durationMs") {
      return compareNumbers(left.durationMs, right.durationMs);
    }

    if (sortKey === "promptCount") {
      return left.promptCount - right.promptCount;
    }

    if (sortKey === "toolEventCount") {
      return left.toolEventCount - right.toolEventCount;
    }

    if (sortKey === "artifactCount") {
      return left.artifactCount - right.artifactCount;
    }

    if (sortKey === "projectName") {
      return compareStrings(left.projectName, right.projectName);
    }

    return compareStrings(left.status, right.status);
  });

  return dir === "asc" ? sorted : sorted.reverse();
};

export default async function RunsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const sessions = await caller.sessions.list({ limit: 200 });
  const query = await searchParams;

  const sort = parseSortKey(getSingleValue(query.sort));
  const dir = parseSortDirection(getSingleValue(query.dir));
  const statusFilter = getSingleValue(query.status) ?? "all";
  const toolFilter = getSingleValue(query.tool) ?? "all";
  const textFilter = (getSingleValue(query.q) ?? "").trim().toLowerCase();

  const filtered = sessions.filter((session) => {
    if (statusFilter !== "all" && session.status !== statusFilter) {
      return false;
    }

    if (toolFilter !== "all" && session.tool !== toolFilter) {
      return false;
    }

    if (textFilter.length === 0) {
      return true;
    }

    return (
      session.id.toLowerCase().includes(textFilter) ||
      session.projectName.toLowerCase().includes(textFilter) ||
      (session.objective ?? "").toLowerCase().includes(textFilter)
    );
  });

  const sorted = sortSessions(filtered, sort, dir);
  const toggleDirection = (column: RunSortKey): SortDirection =>
    sort === column && dir === "desc" ? "asc" : "desc";

  const buildSortHref = (column: RunSortKey): string => {
    const next = new URLSearchParams();
    next.set("sort", column);
    next.set("dir", toggleDirection(column));
    next.set("status", statusFilter);
    next.set("tool", toolFilter);
    if (textFilter.length > 0) {
      next.set("q", textFilter);
    }

    return `/runs?${next.toString()}`;
  };

  return (
    <PageShell title="Run Inspector" subtitle="Per-session drill down with timeline and tool activity.">
      <form className="toolbar" method="get">
        <label>
          Status
          <select name="status" defaultValue={statusFilter}>
            <option value="all">all</option>
            <option value="open">open</option>
            <option value="closed">closed</option>
            <option value="abandoned">abandoned</option>
          </select>
        </label>
        <label>
          Tool
          <select name="tool" defaultValue={toolFilter}>
            <option value="all">all</option>
            <option value="codex">codex</option>
            <option value="claude-code">claude-code</option>
            <option value="desktop-claude">desktop-claude</option>
          </select>
        </label>
        <label>
          Search
          <input name="q" defaultValue={textFilter} placeholder="session, project, objective" />
        </label>
        <input type="hidden" name="sort" value={sort} />
        <input type="hidden" name="dir" value={dir} />
        <button type="submit">Apply</button>
      </form>

      <section className="panel-card">
        <div className="table-head table-runs">
          <span>
            <Link href={buildSortHref("startedAt")}>Started</Link>
          </span>
          <span>
            <Link href={buildSortHref("projectName")}>Project</Link>
          </span>
          <span>Objective</span>
          <span>
            <Link href={buildSortHref("status")}>Status</Link>
          </span>
          <span>
            <Link href={buildSortHref("durationMs")}>Duration</Link>
          </span>
          <span>
            <Link href={buildSortHref("promptCount")}>Prompts</Link>
          </span>
          <span>
            <Link href={buildSortHref("toolEventCount")}>Events</Link>
          </span>
        </div>
        {sorted.map((session) => (
          <div key={session.id} className="table-row table-runs">
            <span>{formatDateTime(session.startedAt)}</span>
            <span>{session.projectName}</span>
            <span>
              <Link href={`/runs/${session.id}`} title={session.id}>
                {session.objective ?? <span className="text-muted mono">{session.id.slice(0, 8)}&hellip;</span>}
              </Link>
            </span>
            <span>{session.status}</span>
            <span>{formatDuration(session.durationMs)}</span>
            <span>{session.promptCount}</span>
            <span>{session.toolEventCount}</span>
          </div>
        ))}
      </section>
    </PageShell>
  );
}
