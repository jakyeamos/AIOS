"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { trpc } from "@/lib/trpc";
import type { Pattern } from "@/lib/types";

type PatternTableProps = {
  patterns: Pattern[];
};

const stateFromCount = (sessionCount: number): Pattern["state"] => {
  if (sessionCount >= 8) {
    return "hypothesis";
  }

  if (sessionCount >= 4) {
    return "observation";
  }

  return "notice";
};

export function PatternTable({ patterns }: PatternTableProps): React.JSX.Element {
  const router = useRouter();
  const [overrides, setOverrides] = useState<Record<string, Partial<Pattern>>>({});
  const rows = patterns.map((pattern) => ({ ...pattern, ...overrides[pattern.id] }));

  const approveMutation = trpc.patterns.approve.useMutation({
    onSuccess: (_result, variables) => {
      setOverrides((currentOverrides) => ({
        ...currentOverrides,
        [variables.id]: {
          humanApproved: true,
          state: "rule",
        },
      }));
      router.refresh();
    },
  });

  const rejectMutation = trpc.patterns.reject.useMutation({
    onSuccess: (_result, variables) => {
      const pattern = rows.find((row) => row.id === variables.id);
      setOverrides((currentOverrides) => ({
        ...currentOverrides,
        [variables.id]: {
          humanApproved: false,
          state: stateFromCount(pattern?.sessionCount ?? 0),
        },
      }));
      router.refresh();
    },
  });

  const busyId = approveMutation.variables?.id ?? rejectMutation.variables?.id ?? null;
  const isBusy = approveMutation.isPending || rejectMutation.isPending;

  return (
    <section className="panel-card">
      <div className="table-head table-patterns">
        <span>Pattern</span>
        <span>State</span>
        <span>Sessions</span>
        <span>Last Seen</span>
        <span>Actions</span>
      </div>
      {rows.map((pattern) => (
        <div key={pattern.id} className="table-row table-patterns">
          <span title={pattern.id}>
            {pattern.label
              ? pattern.label.slice(0, 80) + (pattern.label.length > 80 ? "…" : "")
              : <span className="mono">{pattern.id.slice(0, 8)}&hellip;</span>}
          </span>
          <span>{pattern.state}</span>
          <span>{pattern.sessionCount}</span>
          <span>{new Date(pattern.lastSeen).toLocaleDateString("en-US")}</span>
          <span className="row-actions">
            <button
              type="button"
              disabled={isBusy && busyId === pattern.id}
              onClick={() => {
                approveMutation.mutate({ id: pattern.id });
              }}
            >
              Approve
            </button>
            <button
              type="button"
              disabled={isBusy && busyId === pattern.id}
              onClick={() => {
                rejectMutation.mutate({ id: pattern.id });
              }}
            >
              Reject
            </button>
          </span>
        </div>
      ))}
    </section>
  );
}
