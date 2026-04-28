"use client";

import { useState } from "react";

import type { GitHubSkillCandidate } from "@/server/routers/workflows";
import { trpc } from "@/lib/trpc";

type Props = {
  candidates: GitHubSkillCandidate[];
};

type GroupedCandidates = Record<string, GitHubSkillCandidate[]>;

const groupByStage = (candidates: GitHubSkillCandidate[]): GroupedCandidates => {
  const groups: GroupedCandidates = {};
  for (const c of candidates) {
    const key = (c.detail.stage_key as string | undefined) ?? c.workflowKey;
    if (!groups[key]) groups[key] = [];
    groups[key].push(c);
  }
  return groups;
};

export function GitHubSkillCandidates({ candidates: initial }: Props): React.JSX.Element {
  const [items, setItems] = useState<GitHubSkillCandidate[]>(initial);

  const promoteMutation = trpc.workflows.promoteSkill.useMutation({
    onSuccess: (_, vars) => setItems((prev) => prev.filter((c) => c.id !== vars.id)),
  });

  const dismissMutation = trpc.workflows.dismissSkill.useMutation({
    onSuccess: (_, vars) => setItems((prev) => prev.filter((c) => c.id !== vars.id)),
  });

  if (items.length === 0) return <></>;

  const groups = groupByStage(items);

  return (
    <section className="panel-card">
      <div className="panel-row">
        <div>
          <h3 className="section-title">Improvement Suggestions from GitHub</h3>
          <p className="panel-subtitle">
            Repos and tools found for each stage based on its purpose and experiment signals.
            Promote a suggestion to wire it as a skill; dismiss to hide it.
          </p>
        </div>
        <span className="mono" style={{ fontSize: 12, color: "var(--text-muted)" }}>
          {items.length} suggestion{items.length !== 1 ? "s" : ""}
        </span>
      </div>

      <div className="stack" style={{ marginTop: 16 }}>
        {Object.entries(groups).map(([stageKey, stageCandidates]) => {
          const strategyLabel = (stageCandidates[0].detail.strategy_label as string | undefined) ?? stageKey;
          const weaknessSignal = stageCandidates[0].detail.weakness_signal as string | undefined;

          return (
            <div key={stageKey}>
              <div style={{ marginBottom: 8 }}>
                <p className="panel-title">{stageKey}</p>
                <p className="panel-subtitle">{strategyLabel}</p>
                {weaknessSignal && (
                  <p className="entity-meta" style={{ color: "var(--warning)" }}>
                    ⚠ Experiment signal: {weaknessSignal}
                  </p>
                )}
              </div>

              <div className="stack">
                {stageCandidates.map((candidate) => {
                  const stars = candidate.detail.stars as number | undefined;
                  const relevance = candidate.detail.relevance as string | undefined;
                  const topics = (candidate.detail.topics as string[] | undefined) ?? candidate.tags;
                  const isBusy =
                    (promoteMutation.isPending && promoteMutation.variables?.id === candidate.id) ||
                    (dismissMutation.isPending && dismissMutation.variables?.id === candidate.id);

                  return (
                    <article key={candidate.id} className="entity-card">
                      <div className="panel-row">
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div className="panel-row" style={{ justifyContent: "flex-start", gap: 10 }}>
                            <a
                              href={candidate.githubUrl}
                              target="_blank"
                              rel="noreferrer"
                              className="panel-title"
                              style={{ fontSize: 13 }}
                            >
                              {candidate.repo}
                            </a>
                            {stars !== undefined && (
                              <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                                ★ {stars.toLocaleString()}
                              </span>
                            )}
                          </div>

                          <p className="panel-subtitle">{candidate.summary}</p>

                          {relevance && (
                            <p className="entity-meta" style={{ marginTop: 4, color: "var(--info)" }}>
                              {relevance}
                            </p>
                          )}

                          {topics.length > 0 && (
                            <div className="chip-row" style={{ marginTop: 6 }}>
                              {topics.slice(0, 6).map((tag) => (
                                <span key={tag} className="wf-skill-chip">{tag}</span>
                              ))}
                            </div>
                          )}
                        </div>

                        <div className="badge-row" style={{ alignSelf: "flex-start", flexShrink: 0 }}>
                          <button
                            type="button"
                            className="button-secondary"
                            disabled={isBusy}
                            onClick={() => dismissMutation.mutate({ id: candidate.id })}
                            style={{ fontSize: 11 }}
                          >
                            Dismiss
                          </button>
                          <button
                            type="button"
                            className="button-primary"
                            disabled={isBusy}
                            onClick={() => promoteMutation.mutate({ id: candidate.id })}
                            style={{ fontSize: 11 }}
                          >
                            {isBusy && promoteMutation.variables?.id === candidate.id
                              ? "Adding…"
                              : "Add as skill"}
                          </button>
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
