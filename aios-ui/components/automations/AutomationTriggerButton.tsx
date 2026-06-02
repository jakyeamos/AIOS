"use client";

import { useState } from "react";

import { trpc } from "@/lib/trpc";

type AutomationTriggerButtonProps = {
  automationId: string;
  automationName: string;
  defaultObjective: string;
};

export function AutomationTriggerButton({
  automationId,
  automationName,
  defaultObjective,
}: AutomationTriggerButtonProps): React.JSX.Element {
  const utils = trpc.useUtils();
  const [expanded, setExpanded] = useState(false);
  const [workflowKey, setWorkflowKey] = useState("implementation-delivery");
  const [objective, setObjective] = useState(defaultObjective);
  const [projectId, setProjectId] = useState("");
  const trigger = trpc.automations.triggerWorkflow.useMutation({
    onSuccess: async () => {
      await Promise.all([
        utils.automations.list.invalidate(),
        utils.controlPlane.overview.invalidate(),
      ]);
    },
  });

  return (
    <div className="stack">
      <button type="button" className="button-secondary" onClick={() => setExpanded((current) => !current)}>
        Trigger workflow
      </button>
      {expanded ? (
        <div className="entity-card">
          <label className="field">
            Workflow
            <input value={workflowKey} onChange={(event) => setWorkflowKey(event.target.value)} />
          </label>
          <label className="field">
            Objective
            <textarea rows={3} value={objective} onChange={(event) => setObjective(event.target.value)} />
          </label>
          <label className="field">
            Project id
            <input value={projectId} onChange={(event) => setProjectId(event.target.value)} placeholder="optional" />
          </label>
          <button
            type="button"
            className="button-primary"
            disabled={trigger.isPending || workflowKey.trim().length === 0 || objective.trim().length < 8}
            onClick={() =>
              trigger.mutate({
                automationId,
                workflowKey: workflowKey.trim(),
                objective: objective.trim(),
                projectId: projectId.trim() || undefined,
              })
            }
          >
            {trigger.isPending ? "Triggering..." : `Trigger ${automationName}`}
          </button>
          {trigger.data ? <p className="entity-meta">run: {trigger.data.plan.run.id}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
