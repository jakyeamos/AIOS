import Link from "next/link";

import { ProvenanceBadge } from "@/components/primitives/ProvenanceBadge";
import type { DailyFlowTrace } from "@/lib/control-plane";

type DailyFlowTraceProps = {
  trace: DailyFlowTrace;
};

type RepoCloseoutSummary = {
  repo: string;
  branch: string | null;
  head: string | null;
  dirty: boolean;
  dirtyFiles: string[];
  diffStatLines: string[];
};

const stepLabel = (kind: string): string => kind.replaceAll("_", " ");

const asRecord = (value: unknown): Record<string, unknown> | null =>
  value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;

const stringArray = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];

const repoCloseoutSummary = (metadata: Record<string, unknown>): RepoCloseoutSummary | null => {
  const closeout = asRecord(metadata.repo_closeout);
  if (!closeout || closeout.schema !== "aios-repo-closeout-v0.1") {
    return null;
  }
  const git = asRecord(closeout.git);
  const diffStat = asRecord(closeout.diff_stat);
  const repo = typeof closeout.repo === "string" ? closeout.repo : null;
  if (!repo || !git) {
    return null;
  }
  return {
    repo,
    branch: typeof git.branch === "string" ? git.branch : null,
    head: typeof git.head === "string" ? git.head : null,
    dirty: git.dirty === true,
    dirtyFiles: stringArray(git.dirty_files),
    diffStatLines: stringArray(diffStat?.lines),
  };
};

const provenanceReason = (provenance: string): string => {
  if (provenance === "missing") {
    return "Source evidence is not present yet; this step will fill in as the relevant phase ships or records data.";
  }
  if (provenance === "inferred") {
    return "This step is inferred from live projections.";
  }
  if (provenance === "contradictory") {
    return "Evidence sources disagree and need review.";
  }
  return "This step is confirmed by persisted evidence.";
};

export function DailyFlowTrace({ trace }: DailyFlowTraceProps): React.JSX.Element {
  return (
    <section className="panel-card">
      <div className="panel-row">
        <div>
          <h3 className="section-title">Daily Flow Trace</h3>
          <p className="panel-subtitle">Goal: {trace.objective}</p>
        </div>
        <span className="provenance-badge">{trace.isPreview ? "preview" : "replay"}</span>
      </div>
      <div className="daily-flow-stack">
        {trace.steps.map((step, index) => {
          const closeout = repoCloseoutSummary(step.metadata);
          const diffStat = closeout?.diffStatLines.join(" · ");
          return (
            <article
              key={`${step.kind}-${index}`}
              className={step.provenance === "missing" ? "entity-card daily-flow-missing" : "entity-card"}
            >
              <div className="panel-row">
                <div>
                  <p className="panel-title">
                    {index + 1}. {stepLabel(step.kind)}
                  </p>
                  <p className="panel-subtitle">{step.summary}</p>
                </div>
                <ProvenanceBadge
                  level={step.provenance === "contradictory" ? "missing" : step.provenance}
                  source={step.kind}
                  reason={provenanceReason(step.provenance)}
                />
              </div>
              <p className="entity-meta">
                freshness: {step.freshness}
                {step.provenance === "missing" ? " · Phase data is still being populated." : ""}
              </p>
              {closeout ? (
                <div className="entity-meta">
                  <p>
                    repo: <span className="mono">{closeout.repo}</span>
                  </p>
                  <p>
                    branch {closeout.branch ?? "unknown"} · head{" "}
                    {closeout.head ? closeout.head.slice(0, 12) : "unknown"} ·{" "}
                    {closeout.dirty ? `${closeout.dirtyFiles.length} dirty file(s)` : "clean"}
                  </p>
                  <p>diff: {diffStat && diffStat.length > 0 ? diffStat : "tracked diff clean"}</p>
                </div>
              ) : null}
              <Link href={step.drillDownPath} className="button-secondary">
                Open drilldown
              </Link>
            </article>
          );
        })}
      </div>
    </section>
  );
}
