"use client";

import { useState } from "react";

import type { GroundedAnswer } from "@/lib/control-plane";
import { trpc } from "@/lib/trpc";

type ProjectOption = {
  id: string;
  name: string;
};

type GroundedQueryStudioProps = {
  projects: ProjectOption[];
};

const exampleQuestions = [
  "What changed in AIOS recently?",
  "What is the state of this project?",
  "Why was this decision made?",
  "What should an agent know before doing this task?",
];

export function GroundedQueryStudio({ projects }: GroundedQueryStudioProps): React.JSX.Element {
  const utils = trpc.useUtils();
  const [projectId, setProjectId] = useState<string>(projects[0]?.id ?? "");
  const [question, setQuestion] = useState(exampleQuestions[0]);
  const query = trpc.query.ask.useMutation();
  const workflowLauncher = trpc.automations.triggerWorkflow.useMutation({
    onSuccess: async () => {
      await utils.controlPlane.overview.invalidate();
    },
  });

  const answer: GroundedAnswer | undefined = query.data;

  return (
    <div className="page-content">
      <section className="panel-card">
        <h3 className="section-title">Grounded Query</h3>
        <p className="panel-subtitle">
          Pick a project, ask a question, and inspect the facts, inference, recommendations, and citations AIOS used.
        </p>
        <div className="stack">
          <label className="field">
            Project
            <select value={projectId} onChange={(event) => setProjectId(event.target.value)}>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Question
            <textarea
              rows={4}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask about changes, state, decisions, or delegation context."
            />
          </label>
          <div className="chip-row">
            {exampleQuestions.map((example) => (
              <button key={example} type="button" className="button-secondary" onClick={() => setQuestion(example)}>
                {example}
              </button>
            ))}
          </div>
          <button
            type="button"
            className="button-primary"
            disabled={query.isPending || question.trim().length < 5}
            onClick={() =>
              query.mutate({
                question: question.trim(),
                projectId: projectId || undefined,
              })
            }
          >
            {query.isPending ? "Querying..." : "Ask AIOS"}
          </button>
        </div>
      </section>

      {answer ? (
        <div className="grid grid-2">
          <section className="panel-card">
            <h3 className="section-title">Answer</h3>
            <article className="entity-card">
              <p className="panel-title">{answer.intent}</p>
              <p className="panel-subtitle">{answer.answer}</p>
              {answer.recommendedWorkflow ? (
                <div className="stack" style={{ marginTop: "0.75rem" }}>
                  <p className="entity-meta">
                    workflow: {answer.recommendedWorkflow.workflowKey} · {answer.recommendedWorkflow.rationale}
                  </p>
                  <button
                    type="button"
                    className="button-primary"
                    disabled={workflowLauncher.isPending}
                    onClick={() =>
                      workflowLauncher.mutate({
                        automationId: "grounded-query",
                        workflowKey: answer.recommendedWorkflow?.workflowKey ?? "implementation-delivery",
                        objective: question.trim(),
                        projectId: projectId || undefined,
                      })
                    }
                  >
                    {workflowLauncher.isPending ? "Launching..." : "Launch workflow"}
                  </button>
                  {workflowLauncher.data ? <p className="entity-meta">run: {workflowLauncher.data.plan.run.id}</p> : null}
                </div>
              ) : null}
            </article>
            <div className="stack">
              <article className="entity-card">
                <p className="panel-title">Facts</p>
                <ul className="detail-list">
                  {answer.facts.map((item, index) => (
                    <li key={index}>{item}</li>
                  ))}
                </ul>
              </article>
              <article className="entity-card">
                <p className="panel-title">Inference</p>
                <ul className="detail-list">
                  {answer.inferences.map((item, index) => (
                    <li key={index}>{item}</li>
                  ))}
                </ul>
              </article>
              <article className="entity-card">
                <p className="panel-title">Recommendation</p>
                <ul className="detail-list">
                  {answer.recommendations.map((item, index) => (
                    <li key={index}>{item}</li>
                  ))}
                </ul>
              </article>
            </div>
          </section>

          <section className="panel-card">
            <h3 className="section-title">Inspectability</h3>
            <article className="entity-card">
              <p className="panel-title">Citations</p>
              <ul className="detail-list">
                {answer.citations.map((citation, index) => (
                  <li key={index}>
                    <a href={citation.href}>{citation.label}</a>: {citation.excerpt}
                  </li>
                ))}
              </ul>
            </article>
            <article className="entity-card">
              <p className="panel-title">Retrieval Trace</p>
              <ul className="detail-list">
                {answer.retrievalTrace.map((trace, index) => (
                  <li key={index}>
                    {trace.source}: {trace.reason}
                  </li>
                ))}
              </ul>
            </article>
            <article className="entity-card">
              <p className="panel-title">Assumptions</p>
              <ul className="detail-list">
                {answer.assumptions.length > 0 ? (
                  answer.assumptions.map((assumption, index) => <li key={index}>{assumption}</li>)
                ) : (
                  <li>No additional assumptions were required. Ask a narrower question if you need stricter scoping.</li>
                )}
              </ul>
            </article>
          </section>
        </div>
      ) : null}
    </div>
  );
}
