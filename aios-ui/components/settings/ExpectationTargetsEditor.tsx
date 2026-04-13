"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { trpc } from "@/lib/trpc";
import type { ExpectationDirection, ExpectationTarget } from "@/lib/types";

type ExpectationTargetsEditorProps = {
  targets: ExpectationTarget[];
};

type DraftTarget = {
  targetValue: string;
  warningDelta: string;
  errorDelta: string;
  direction: ExpectationDirection;
};

const labels: Record<ExpectationTarget["metricKey"], string> = {
  abandon_rate: "Abandon Rate",
  open_run_rate: "Open Run Rate",
  first_pass_success: "First Pass Success",
  follow_up_turns: "Follow-Up Turns",
  prompt_reuse_rate: "Prompt Reuse Rate",
  error_event_rate: "Error Event Rate",
  avg_run_duration_minutes: "Avg Run Duration (min)",
};

export function ExpectationTargetsEditor({ targets }: ExpectationTargetsEditorProps): React.JSX.Element {
  const router = useRouter();

  const [drafts, setDrafts] = useState<Record<string, DraftTarget>>(() => {
    const initial: Record<string, DraftTarget> = {};
    for (const target of targets) {
      initial[target.metricKey] = {
        targetValue: `${target.targetValue}`,
        warningDelta: `${target.warningDelta}`,
        errorDelta: `${target.errorDelta}`,
        direction: target.direction,
      };
    }

    return initial;
  });

  const mutation = trpc.insights.upsertExpectation.useMutation({
    onSuccess: () => {
      router.refresh();
    },
  });

  const sortedTargets = useMemo(
    () => [...targets].sort((left, right) => labels[left.metricKey].localeCompare(labels[right.metricKey])),
    [targets],
  );

  return (
    <section className="panel-card">
      <div className="table-head table-expectations">
        <span>Metric</span>
        <span>Direction</span>
        <span>Target</span>
        <span>Warning Δ</span>
        <span>Error Δ</span>
        <span>Action</span>
      </div>
      {sortedTargets.map((target) => {
        const draft = drafts[target.metricKey];
        const disabled = mutation.isPending && mutation.variables?.metricKey === target.metricKey;

        return (
          <div key={target.id} className="table-row table-expectations">
            <span>{labels[target.metricKey]}</span>
            <span>
              <select
                value={draft.direction}
                onChange={(event) => {
                  setDrafts((currentDrafts) => ({
                    ...currentDrafts,
                    [target.metricKey]: {
                      ...currentDrafts[target.metricKey],
                      direction: event.target.value as ExpectationDirection,
                    },
                  }));
                }}
              >
                <option value="max">max</option>
                <option value="min">min</option>
                <option value="exact">exact</option>
              </select>
            </span>
            <span>
              <input
                value={draft.targetValue}
                onChange={(event) => {
                  setDrafts((currentDrafts) => ({
                    ...currentDrafts,
                    [target.metricKey]: {
                      ...currentDrafts[target.metricKey],
                      targetValue: event.target.value,
                    },
                  }));
                }}
              />
            </span>
            <span>
              <input
                value={draft.warningDelta}
                onChange={(event) => {
                  setDrafts((currentDrafts) => ({
                    ...currentDrafts,
                    [target.metricKey]: {
                      ...currentDrafts[target.metricKey],
                      warningDelta: event.target.value,
                    },
                  }));
                }}
              />
            </span>
            <span>
              <input
                value={draft.errorDelta}
                onChange={(event) => {
                  setDrafts((currentDrafts) => ({
                    ...currentDrafts,
                    [target.metricKey]: {
                      ...currentDrafts[target.metricKey],
                      errorDelta: event.target.value,
                    },
                  }));
                }}
              />
            </span>
            <span>
              <button
                type="button"
                disabled={disabled}
                onClick={() => {
                  const nextTargetValue = Number.parseFloat(draft.targetValue);
                  const nextWarningDelta = Number.parseFloat(draft.warningDelta);
                  const nextErrorDelta = Number.parseFloat(draft.errorDelta);

                  if (
                    Number.isNaN(nextTargetValue) ||
                    Number.isNaN(nextWarningDelta) ||
                    Number.isNaN(nextErrorDelta)
                  ) {
                    return;
                  }

                  mutation.mutate({
                    scopeType: target.scopeType,
                    scopeKey: target.scopeKey,
                    metricKey: target.metricKey,
                    direction: draft.direction,
                    targetValue: nextTargetValue,
                    warningDelta: nextWarningDelta,
                    errorDelta: nextErrorDelta,
                  });
                }}
              >
                Save
              </button>
            </span>
          </div>
        );
      })}
    </section>
  );
}
