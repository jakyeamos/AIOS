import Link from "next/link";

import { formatDateTime, formatDuration } from "@/lib/format";
import type { Session } from "@/lib/types";
import { StatusBadge } from "@/components/primitives/StatusBadge";

type SessionCardProps = {
  session: Session;
};

export function SessionCard({ session }: SessionCardProps): React.JSX.Element {
  return (
    <article className="panel-card">
      <div className="panel-row">
        <div>
          <p className="panel-title">
            <Link href={`/runs/${session.id}`}>{session.id}</Link>
          </p>
          <p className="panel-subtitle">
            {session.projectName} · {session.tool}
          </p>
        </div>
        <StatusBadge status={session.status} />
      </div>
      <p className="mono">{session.objective ?? "No objective captured."}</p>
      <div className="panel-metrics">
        <span>{formatDateTime(session.startedAt)}</span>
        <span>{formatDuration(session.durationMs)}</span>
        <span>{session.promptCount} prompts</span>
        <span>{session.toolEventCount} events</span>
      </div>
    </article>
  );
}
