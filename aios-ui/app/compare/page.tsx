import Link from "next/link";

import { PageShell } from "@/components/layout/PageShell";
import { getCaller } from "@/server/caller";

export const dynamic = "force-dynamic";

export default async function ComparePage(): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const [experiments, testRepos, workflowSkillExperiments] = await Promise.all([
    caller.experiments.list(),
    caller.experiments.testRepos(),
    caller.experiments.workflowSkillExperiments(),
  ]);

  return (
    <PageShell title="Diff & Compare" subtitle="Side-by-side comparisons for workflow and prompt changes.">
      <section className="panel-card" id="test-repos">
        <div className="panel-row">
          <div>
            <h3 className="section-title">Experiment Test Repos</h3>
            <p className="panel-subtitle">Canonical local repos for strategy, prompt, workflow, and validation experiments.</p>
          </div>
          <span className="mono">{testRepos.filter((repo) => repo.status === "ready").length}/{testRepos.length} ready</span>
        </div>
        <div className="table-head">
          <span>Repo</span>
          <span>Profile</span>
          <span>Purpose</span>
          <span>Status</span>
          <span>Path</span>
        </div>
        {testRepos.map((repo) => (
          <div key={repo.id} className="table-row">
            <span>
              <strong>{repo.name}</strong>
              <br />
              <span className="text-muted">{repo.setup}</span>
            </span>
            <span>{repo.profile}</span>
            <span className="text-muted">{repo.purpose}</span>
            <span>{repo.status}</span>
            <span className="mono">{repo.repoPath}</span>
          </div>
        ))}
      </section>
      <section className="panel-card" id="workflow-skill-experiments">
        <div className="panel-row">
          <div>
            <h3 className="section-title">Workflow Skill Experiments</h3>
            <p className="panel-subtitle">Queued branch experiments for generated workflow skills across the registered test repos.</p>
          </div>
          <span className="mono">{workflowSkillExperiments.length} queued</span>
        </div>
        <div className="table-head">
          <span>Workflow</span>
          <span>Skill</span>
          <span>Repo</span>
          <span>Status</span>
          <span>Branch</span>
        </div>
        {workflowSkillExperiments.map((experiment) => (
          <div key={experiment.id} className="table-row">
            <span>{experiment.workflowKey}</span>
            <span className="mono">{experiment.skillKey}</span>
            <span>{experiment.testRepoId}</span>
            <span>{experiment.outcome ?? experiment.status}</span>
            <span className="mono">{experiment.branchName}</span>
          </div>
        ))}
      </section>
      <section className="panel-card">
        <h3 className="section-title">Experiment Runs</h3>
        <div className="table-head">
          <span>Experiment</span>
          <span>Hypothesis</span>
          <span>Surface</span>
          <span>Winner</span>
          <span>Status</span>
          <span>Open</span>
        </div>
        {experiments.map((experiment) => (
          <div key={experiment.id} className="table-row">
            <span>{experiment.name}</span>
            <span className="text-muted">{experiment.hypothesis}</span>
            <span>{experiment.surface}</span>
            <span>{experiment.winner ?? "—"}</span>
            <span>{experiment.endedAt ? "closed" : "running"}</span>
            <span>
              <Link href={`/compare/${experiment.id}/baseline`}>view</Link>
            </span>
          </div>
        ))}
      </section>
    </PageShell>
  );
}
