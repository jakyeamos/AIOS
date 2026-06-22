"use client";

import Link from "next/link";
import { useState } from "react";

import type { EvalSummary } from "@/lib/control-plane";

type EvalSummaryPanelProps = {
  evalData: EvalSummary | null;
};

const formatScore = (value: number | null): string => (value === null ? "n/a" : value.toFixed(2));

const scoreRows = (evalData: EvalSummary): Array<[string, number | null]> => [
  ["Task success", evalData.taskSuccess],
  ["Quality", evalData.qualityAdherence],
  ["Speed", evalData.workflowSpeed],
  ["Cost", evalData.costEfficiency],
  ["Context", evalData.contextEffectiveness],
  ["Autonomy", evalData.autonomy],
  ["User trust", evalData.userTrust],
  ["Portability", evalData.contextPortability],
];

export function EvalSummaryPanel({ evalData }: EvalSummaryPanelProps): React.JSX.Element | null {
  const [expanded, setExpanded] = useState(false);
  if (!evalData) return null;

  return (
    <section className="panel-card">
      <div className="panel-row">
        <div>
          <h3 className="section-title">Eval Summary</h3>
          <p className="panel-subtitle">
            {evalData.runCount} run(s) · context {evalData.contextProfile ?? "mixed"} · score {formatScore(evalData.overallScore)}
          </p>
        </div>
        <button type="button" className="button-secondary" onClick={() => setExpanded((value) => !value)}>
          {expanded ? "Collapse" : "Expand"}
        </button>
      </div>
      {expanded ? (
        <div className="stack" style={{ marginTop: "0.75rem" }}>
          <div className="grid grid-4">
            {scoreRows(evalData).map(([label, value]) => (
              <article key={label} className="entity-card">
                <p className="stat-label">{label}</p>
                <p className="stat-value">{formatScore(value)}</p>
              </article>
            ))}
          </div>
          <div className="grid grid-2">
            <article className="entity-card">
              <p className="panel-title">Second Brain Lift</p>
              <p className="stat-value">{formatScore(evalData.secondBrainLift)}</p>
            </article>
            <article className="entity-card">
              <p className="panel-title">Portability Gap</p>
              <p className="stat-value">{formatScore(evalData.portabilityGap)}</p>
            </article>
          </div>
          {evalData.fullEvalRunPath ? (
            <Link href={evalData.fullEvalRunPath} className="button-secondary">
              Full eval run detail
            </Link>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
