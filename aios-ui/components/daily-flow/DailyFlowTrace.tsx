import Link from "next/link";

import { ProvenanceBadge } from "@/components/primitives/ProvenanceBadge";
import type { DailyFlowTrace } from "@/lib/control-plane";

type DailyFlowTraceProps = {
  trace: DailyFlowTrace;
};

const stepLabel = (kind: string): string => kind.replaceAll("_", " ");

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
        {trace.steps.map((step, index) => (
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
            <Link href={step.drillDownPath} className="button-secondary">
              Drill in
            </Link>
          </article>
        ))}
      </div>
    </section>
  );
}
