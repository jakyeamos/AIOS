import type { ToolEvent } from "@/lib/types";

import { TimelineEvent } from "@/components/primitives/TimelineEvent";

type RecentActivityProps = {
  events: ToolEvent[];
};

export function RecentActivity({ events }: RecentActivityProps): React.JSX.Element {
  return (
    <section>
      <h3 className="section-title">Recent Activity</h3>
      <div className="stack">
        {events.map((event) => (
          <TimelineEvent key={event.id} event={event} />
        ))}
      </div>
    </section>
  );
}
