"use client";

import { useState } from "react";

import type { GitHubSkillCandidate } from "@/server/routers/workflows";
import { trpc } from "@/lib/trpc";

type Props = {
  candidates: GitHubSkillCandidate[];
};

export function GitHubSkillCandidates({ candidates: initial }: Props): React.JSX.Element {
  const [items, setItems] = useState<GitHubSkillCandidate[]>(initial);
  const [expanded, setExpanded] = useState<string | null>(null);

  const promoteMutation = trpc.workflows.promoteSkill.useMutation({
    onSuccess: (_, vars) => {
      setItems((prev) => prev.filter((c) => c.id !== vars.id));
    },
  });

  const dismissMutation = trpc.workflows.dismissSkill.useMutation({
    onSuccess: (_, vars) => {
      setItems((prev) => prev.filter((c) => c.id !== vars.id));
    },
  });

  const busy = promoteMutation.isPending || dismissMutation.isPending;

  if (items.length === 0) return <></>;

  return (
    <section className="panel-card">
      <div className="panel-row">
        <div>
          <h3 className="section-title">GitHub Skill Candidates</h3>
          <p className="panel-subtitle">
            Skills discovered on GitHub that may fit this workflow. Promote to add to skills.json, dismiss to hide.
          </p>
        </div>
        <span className="mono" style={{ fontSize: 12, color: "var(--text-muted)" }}>
          {items.length} pending
        </span>
      </div>

      <div className="stack" style={{ marginTop: 12 }}>
        {items.map((candidate) => {
          const isExpanded = expanded === candidate.id;
          const invariants = (candidate.detail.invariants as string[] | undefined) ?? [];
          const failureConds = (candidate.detail.failure_conditions as string[] | undefined) ?? [];
          const execMode = (candidate.detail.execution_mode as string | undefined) ?? "heuristic";
          const isBusy = busy && (promoteMutation.variables?.id === candidate.id || dismissMutation.variables?.id === candidate.id);

          return (
            <article key={candidate.id} className="entity-card">
              <div className="panel-row">
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="panel-row" style={{ justifyContent: "flex-start", gap: 8 }}>
                    <p className="panel-title">{candidate.name}</p>
                    <span className="mono" style={{ fontSize: 10, color: "var(--text-muted)" }}>{execMode}</span>
                  </div>
                  <p className="panel-subtitle">{candidate.summary}</p>
                  {candidate.tags.length > 0 && (
                    <div className="chip-row" style={{ marginTop: 6 }}>
                      {candidate.tags.map((tag) => (
                        <span key={tag} className="wf-skill-chip">{tag}</span>
                      ))}
                    </div>
                  )}
                  <p className="entity-meta">
                    <a href={candidate.githubUrl} target="_blank" rel="noreferrer">
                      {candidate.repo}
                    </a>
                    {candidate.path ? ` · ${candidate.path}` : ""}
                  </p>
                </div>

                <div className="badge-row">
                  <button
                    type="button"
                    className="button-secondary"
                    style={{ fontSize: 11 }}
                    onClick={() => setExpanded(isExpanded ? null : candidate.id)}
                  >
                    {isExpanded ? "less" : "more"}
                  </button>
                  <button
                    type="button"
                    className="button-secondary"
                    disabled={isBusy}
                    onClick={() => dismissMutation.mutate({ id: candidate.id })}
                  >
                    Dismiss
                  </button>
                  <button
                    type="button"
                    className="button-primary"
                    disabled={isBusy}
                    onClick={() => promoteMutation.mutate({ id: candidate.id })}
                  >
                    {isBusy && promoteMutation.variables?.id === candidate.id ? "Promoting…" : "Promote"}
                  </button>
                </div>
              </div>

              {isExpanded && (
                <div className="stack" style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--border)" }}>
                  {invariants.length > 0 && (
                    <div>
                      <p className="panel-title" style={{ fontSize: 11, marginBottom: 4 }}>Invariants</p>
                      <ul className="detail-list">
                        {invariants.map((inv, i) => <li key={i}>{inv}</li>)}
                      </ul>
                    </div>
                  )}
                  {failureConds.length > 0 && (
                    <div>
                      <p className="panel-title" style={{ fontSize: 11, marginBottom: 4 }}>Failure conditions</p>
                      <ul className="detail-list">
                        {failureConds.map((fc, i) => <li key={i}>{fc}</li>)}
                      </ul>
                    </div>
                  )}
                  <p className="entity-meta">skill_key: <span className="mono">{candidate.skillKey}</span></p>
                </div>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
