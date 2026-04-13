import type { Session } from "@/lib/types";

import { SessionCard } from "@/components/panels/SessionCard";

type ActiveRunsProps = {
  sessions: Session[];
};

export function ActiveRuns({ sessions }: ActiveRunsProps): React.JSX.Element {
  return (
    <section>
      <h3 className="section-title">Active Runs</h3>
      <div className="stack">
        {sessions.map((session) => (
          <SessionCard key={session.id} session={session} />
        ))}
      </div>
    </section>
  );
}
