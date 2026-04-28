"use client";

import { useState } from "react";

import type { WorkflowProposalDetail, WorkflowStage } from "@/server/routers/workflows";
import { trpc } from "@/lib/trpc";

type Props = {
  proposal: WorkflowProposalDetail;
  skillKeys: string[];
};

const STAGE_KINDS = [
  "parse_request",
  "normalize_prompt",
  "enrich_context",
  "generate",
  "transform",
  "validate",
  "finalize",
];

const emptyStage = (): WorkflowStage => ({
  key: "",
  kind: "generate",
  required_skills: [],
  best_practices: [],
  notes: "",
});

export function WorkflowSandbox({ proposal, skillKeys }: Props): React.JSX.Element {
  const [stages, setStages] = useState<WorkflowStage[]>(proposal.stages);
  const [saved, setSaved] = useState(false);

  const updateMutation = trpc.workflows.updateStages.useMutation({
    onSuccess: () => {
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
  });

  const updateStage = (index: number, patch: Partial<WorkflowStage>): void => {
    setStages((prev) => prev.map((s, i) => (i === index ? { ...s, ...patch } : s)));
    setSaved(false);
  };

  const addStage = (): void => {
    setStages((prev) => [...prev, emptyStage()]);
    setSaved(false);
  };

  const removeStage = (index: number): void => {
    setStages((prev) => prev.filter((_, i) => i !== index));
    setSaved(false);
  };

  const moveStage = (index: number, direction: -1 | 1): void => {
    const next = index + direction;
    if (next < 0 || next >= stages.length) return;
    setStages((prev) => {
      const copy = [...prev];
      [copy[index], copy[next]] = [copy[next], copy[index]];
      return copy;
    });
    setSaved(false);
  };

  const toggleSkill = (stageIndex: number, skill: string): void => {
    setStages((prev) =>
      prev.map((s, i) => {
        if (i !== stageIndex) return s;
        const has = s.required_skills.includes(skill);
        return {
          ...s,
          required_skills: has
            ? s.required_skills.filter((k) => k !== skill)
            : [...s.required_skills, skill],
        };
      }),
    );
    setSaved(false);
  };

  const updateBestPractice = (stageIndex: number, bpIndex: number, value: string): void => {
    setStages((prev) =>
      prev.map((s, i) => {
        if (i !== stageIndex) return s;
        const bps = [...(s.best_practices ?? [])];
        bps[bpIndex] = value;
        return { ...s, best_practices: bps };
      }),
    );
    setSaved(false);
  };

  const addBestPractice = (stageIndex: number): void => {
    setStages((prev) =>
      prev.map((s, i) =>
        i === stageIndex ? { ...s, best_practices: [...(s.best_practices ?? []), ""] } : s,
      ),
    );
    setSaved(false);
  };

  const removeBestPractice = (stageIndex: number, bpIndex: number): void => {
    setStages((prev) =>
      prev.map((s, i) =>
        i === stageIndex
          ? { ...s, best_practices: (s.best_practices ?? []).filter((_, j) => j !== bpIndex) }
          : s,
      ),
    );
    setSaved(false);
  };

  return (
    <div className="page-content">
      <section className="panel-card">
        <div className="panel-row">
          <div>
            <h3 className="section-title">Workflow Sandbox</h3>
            <p className="panel-subtitle">
              Edit stages, reorder steps, attach skills, and add best-practice guidance. Changes are
              saved to the proposal and take effect when the workflow is approved.
            </p>
          </div>
          <div className="badge-row">
            <span className="mono">{proposal.status}</span>
            <button
              type="button"
              className="button-primary"
              disabled={updateMutation.isPending}
              onClick={() =>
                updateMutation.mutate({
                  id: proposal.id,
                  stages: stages.map((s) => ({
                    ...s,
                    best_practices: s.best_practices ?? [],
                    notes: s.notes ?? "",
                  })),
                })
              }
            >
              {updateMutation.isPending ? "Saving…" : saved ? "Saved" : "Save Changes"}
            </button>
          </div>
        </div>
        <div className="entity-meta">
          {proposal.evidence.length > 0 && (
            <span>Evidence: {proposal.evidence.slice(0, 2).join(" · ")}</span>
          )}
        </div>
      </section>

      <div className="stack">
        {stages.map((stage, index) => (
          <article key={index} className="entity-card">
            <div className="panel-row">
              <div className="stack" style={{ flex: 1, gap: "0.5rem" }}>
                <div className="panel-row">
                  <label className="field" style={{ flex: 1 }}>
                    Step key
                    <input
                      value={stage.key}
                      placeholder="e.g. humanize_output"
                      onChange={(e) => updateStage(index, { key: e.target.value })}
                    />
                  </label>
                  <label className="field" style={{ flex: 1 }}>
                    Kind
                    <select
                      value={stage.kind}
                      onChange={(e) => updateStage(index, { kind: e.target.value })}
                    >
                      {STAGE_KINDS.map((kind) => (
                        <option key={kind} value={kind}>
                          {kind}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>

                <div>
                  <p className="panel-title" style={{ marginBottom: "0.25rem" }}>Skills</p>
                  <div className="chip-row">
                    {skillKeys.map((skill) => (
                      <button
                        key={skill}
                        type="button"
                        className={stage.required_skills.includes(skill) ? "button-primary" : "button-secondary"}
                        onClick={() => toggleSkill(index, skill)}
                      >
                        {skill}
                      </button>
                    ))}
                  </div>
                </div>

                {(stage.best_practices ?? []).length > 0 || true ? (
                  <div>
                    <div className="panel-row">
                      <p className="panel-title">Best practices</p>
                      <button
                        type="button"
                        className="button-secondary"
                        onClick={() => addBestPractice(index)}
                      >
                        + Add
                      </button>
                    </div>
                    <div className="stack" style={{ marginTop: "0.25rem" }}>
                      {(stage.best_practices ?? []).map((bp, bpIndex) => (
                        <div key={bpIndex} className="panel-row">
                          <input
                            value={bp}
                            placeholder="e.g. Run humanizer on AI-assisted sections"
                            style={{ flex: 1 }}
                            onChange={(e) => updateBestPractice(index, bpIndex, e.target.value)}
                          />
                          <button
                            type="button"
                            className="button-secondary"
                            onClick={() => removeBestPractice(index, bpIndex)}
                          >
                            ×
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}

                <label className="field">
                  Notes
                  <textarea
                    rows={2}
                    value={stage.notes ?? ""}
                    placeholder="Optional: why this step exists or how to extend it"
                    onChange={(e) => updateStage(index, { notes: e.target.value })}
                  />
                </label>
              </div>

              <div className="stack" style={{ gap: "0.25rem", alignSelf: "flex-start" }}>
                <button
                  type="button"
                  className="button-secondary"
                  disabled={index === 0}
                  onClick={() => moveStage(index, -1)}
                >
                  ↑
                </button>
                <button
                  type="button"
                  className="button-secondary"
                  disabled={index === stages.length - 1}
                  onClick={() => moveStage(index, 1)}
                >
                  ↓
                </button>
                <button
                  type="button"
                  className="button-secondary"
                  onClick={() => removeStage(index)}
                >
                  ✕
                </button>
              </div>
            </div>
          </article>
        ))}
      </div>

      <button type="button" className="button-secondary" onClick={addStage}>
        + Add Step
      </button>
    </div>
  );
}
