"use client";

import Link from "next/link";
import { useState } from "react";

import { StatusBadge } from "@/components/primitives/StatusBadge";
import type { NextAction, PriorityBucket } from "@/lib/control-plane";
import { trpc } from "@/lib/trpc";

type NextActionPanelProps = {
  actions: NextAction[];
  projectId: string | null;
};

const bucketOrder: PriorityBucket[] = [
  "foundational",
  "high_leverage",
  "quick_wins",
  "blocked",
  "waived_deferred",
];

const bucketLabel: Record<PriorityBucket, string> = {
  foundational: "Foundational",
  high_leverage: "High leverage",
  quick_wins: "Quick wins",
  blocked: "Blocked",
  waived_deferred: "Waived/deferred",
};

const bucketTone = (bucket: PriorityBucket): "healthy" | "warning" | "error" | "unknown" => {
  if (bucket === "foundational" || bucket === "blocked") {
    return "warning";
  }
  if (bucket === "high_leverage") {
    return "healthy";
  }
  return "unknown";
};

export function NextActionPanel({ actions, projectId }: NextActionPanelProps): React.JSX.Element {
  const utils = trpc.useUtils();
  const [lastLaunch, setLastLaunch] = useState<string | null>(null);
  const launcher = trpc.projects.launchRemediation.useMutation({
    onSuccess: async (result) => {
      setLastLaunch(result.plan.run.id);
      await Promise.all([
        utils.controlPlane.overview.invalidate(),
        projectId ? utils.nextAction.getForProject.invalidate({ projectId }) : utils.nextAction.topAcrossProjects.invalidate(),
        projectId ? utils.projects.taskiSummary.invalidate({ projectId }) : Promise.resolve(),
      ]);
    },
  });

  return (
    <section className="panel-card">
      <div className="panel-row">
        <div>
          <h3 className="section-title">Next Actions</h3>
          <p className="panel-subtitle">Ranked work from standards deltas, approvals, blockers, learning gaps, and promotions.</p>
        </div>
        {lastLaunch ? <StatusBadge status="healthy" label={`launched ${lastLaunch}`} /> : null}
      </div>
      <div className="stack">
        {actions.length > 0 ? (
          bucketOrder.map((bucket) => {
            const bucketActions = actions.filter((action) => action.priorityBucket === bucket);
            if (bucketActions.length === 0) {
              return null;
            }
            return (
              <article key={bucket} className="entity-card">
                <div className="panel-row">
                  <p className="panel-title">{bucketLabel[bucket]}</p>
                  <StatusBadge status={bucketTone(bucket)} label={`${bucketActions.length} action(s)`} />
                </div>
                <div className="stack" style={{ marginTop: "0.75rem" }}>
                  {bucketActions.map((action) => {
                    const deltaId = action.evidenceIds[0] ?? "";
                    const canLaunch =
                      action.kind === "launch_remediation_workflow" &&
                      action.recommendedWorkflowKey !== null &&
                      action.projectId !== null &&
                      deltaId.length > 0;
                    return (
                      <div key={`${action.kind}-${action.title}-${deltaId}`} className="timeline-event">
                        <div className="panel-row">
                          <div>
                            <p className="panel-title">{action.title}</p>
                            <p className="panel-subtitle">{action.rationale}</p>
                          </div>
                          <Link href={action.drillDownPath} className="button-secondary">
                            Drill in
                          </Link>
                        </div>
                        <p className="entity-meta">
                          {action.kind} · confidence {action.confidence.toFixed(2)}
                          {action.recommendedWorkflowKey ? ` · workflow ${action.recommendedWorkflowKey}` : ""}
                        </p>
                        {canLaunch ? (
                          <button
                            type="button"
                            className="button-primary"
                            disabled={launcher.isPending}
                            onClick={() =>
                              launcher.mutate({
                                projectId: action.projectId as string,
                                deltaId,
                                objective: action.title,
                              })
                            }
                          >
                            {launcher.isPending ? "Launching..." : "Launch remediation workflow"}
                          </button>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              </article>
            );
          })
        ) : (
          <article className="entity-card">
            <p className="panel-subtitle">No ranked actions are available. Review project health or run search to find evidence.</p>
            <Link href="/search" className="button-secondary">
              Open search
            </Link>
          </article>
        )}
      </div>
    </section>
  );
}
