import { notFound } from "next/navigation";

import { DailyFlowTrace } from "@/components/daily-flow/DailyFlowTrace";
import { PageShell } from "@/components/layout/PageShell";
import { SessionCard } from "@/components/panels/SessionCard";
import { StatusBadge } from "@/components/primitives/StatusBadge";
import { TimelineEvent } from "@/components/primitives/TimelineEvent";
import { formatDateTime } from "@/lib/format";
import { getCaller } from "@/server/caller";

type SearchParams = Record<string, string | string[] | undefined>;

const getSingleValue = (value: string | string[] | undefined): string | undefined => {
  if (Array.isArray(value)) {
    return value[0];
  }

  return value;
};

export default async function RunDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<SearchParams>;
}): Promise<React.JSX.Element> {
  const { id } = await params;
  const query = await searchParams;
  const caller = await getCaller();
  const [result, trace] = await Promise.all([
    caller.sessions.detail({ id }),
    caller.dailyFlow.replay({ runId: id }),
  ]);

  if (!result.session) {
    notFound();
  }

  const eventTypeFilter = getSingleValue(query.eventType) ?? "all";
  const sourceToolFilter = getSingleValue(query.sourceTool) ?? "all";
  const eventSearch = (getSingleValue(query.q) ?? "").trim().toLowerCase();

  const filteredEvents = result.events.filter((event) => {
    if (eventTypeFilter !== "all" && event.eventType !== eventTypeFilter) {
      return false;
    }

    if (sourceToolFilter !== "all" && event.sourceTool !== sourceToolFilter) {
      return false;
    }

    if (eventSearch.length === 0) {
      return true;
    }

    return JSON.stringify(event.payloadJson).toLowerCase().includes(eventSearch);
  });

  const eventTypes = Array.from(new Set(result.events.map((event) => event.eventType))).sort();
  const sourceTools = Array.from(new Set(result.events.map((event) => event.sourceTool))).sort();

  return (
    <PageShell title={`Run ${result.session.id}`} subtitle="Trace and root-cause surface for this session.">
      <DailyFlowTrace trace={trace} />
      <SessionCard session={result.session} />

      <div className="grid grid-2">
        <section className="panel-card">
          <h3 className="section-title">Root Cause Signals</h3>
          {result.rootCauseSignals.length === 0 ? (
            <p className="panel-subtitle">No warning/error signals inferred from trace data.</p>
          ) : (
            <div className="stack">
              {result.rootCauseSignals.map((signal) => (
                <article key={`${signal.signal}-${signal.detail}`} className="timeline-event">
                  <div className="panel-row">
                    <p className="panel-title">{signal.signal}</p>
                    <StatusBadge status={signal.severity} />
                  </div>
                  <p className="panel-subtitle">{signal.detail}</p>
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="panel-card">
          <h3 className="section-title">Breakdown</h3>
          <div className="table-head table-breakdown">
            <span>Category</span>
            <span>Value</span>
            <span>Count</span>
          </div>
          {result.eventTypeBreakdown.map((row) => (
            <div key={`eventType-${row.eventType}`} className="table-row table-breakdown">
              <span>eventType</span>
              <span className="mono">{row.eventType}</span>
              <span>{row.count}</span>
            </div>
          ))}
          {result.sourceToolBreakdown.map((row) => (
            <div key={`source-${row.sourceTool}`} className="table-row table-breakdown">
              <span>sourceTool</span>
              <span className="mono">{row.sourceTool}</span>
              <span>{row.count}</span>
            </div>
          ))}
          {result.promptBreakdown.map((row) => (
            <div key={`promptClass-${row.classification}`} className="table-row table-breakdown">
              <span>promptClass</span>
              <span className="mono">{row.classification}</span>
              <span>{row.count}</span>
            </div>
          ))}
        </section>
      </div>

      <div className="grid grid-2">
        <section className="panel-card">
          <h3 className="section-title">Artifacts</h3>
          <div className="table-head table-artifacts">
            <span>Type</span>
            <span>Path</span>
            <span>Created</span>
          </div>
          {result.artifacts.length === 0 ? (
            <p className="panel-subtitle">No artifacts linked to this session.</p>
          ) : (
            result.artifacts.map((artifact) => (
              <div key={artifact.id} className="table-row table-artifacts">
                <span>{artifact.artifactType}</span>
                <span className="mono">{artifact.path ?? "-"}</span>
                <span>{formatDateTime(artifact.createdAt)}</span>
              </div>
            ))
          )}
        </section>

        <section className="panel-card">
          <h3 className="section-title">Linked Bugs</h3>
          <div className="table-head table-bugs">
            <span>Symptom</span>
            <span>Root Cause</span>
            <span>Status</span>
          </div>
          {result.bugRows.length === 0 ? (
            <p className="panel-subtitle">No bug records reference this run.</p>
          ) : (
            result.bugRows.map((bug) => (
              <div key={bug.id} className="table-row table-bugs">
                <span>{bug.symptom}</span>
                <span>{bug.rootCause ?? "-"}</span>
                <span>{bug.status}</span>
              </div>
            ))
          )}
        </section>
      </div>

      <section>
        <h3 className="section-title">Trace</h3>
        <form className="toolbar" method="get">
          <label>
            Event Type
            <select name="eventType" defaultValue={eventTypeFilter}>
              <option value="all">all</option>
              {eventTypes.map((eventType) => (
                <option key={eventType} value={eventType}>
                  {eventType}
                </option>
              ))}
            </select>
          </label>
          <label>
            Source Tool
            <select name="sourceTool" defaultValue={sourceToolFilter}>
              <option value="all">all</option>
              {sourceTools.map((sourceTool) => (
                <option key={sourceTool} value={sourceTool}>
                  {sourceTool}
                </option>
              ))}
            </select>
          </label>
          <label>
            Search Payload
            <input name="q" defaultValue={eventSearch} placeholder="error, command, file" />
          </label>
          <button type="submit">Apply</button>
        </form>
        <div className="stack">
          {filteredEvents.map((event) => (
            <TimelineEvent key={event.id} event={event} />
          ))}
        </div>
      </section>
    </PageShell>
  );
}
