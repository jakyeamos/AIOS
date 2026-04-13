import { formatDateTime } from "@/lib/format";
import type { ToolEvent } from "@/lib/types";

type TimelineEventProps = {
  event: ToolEvent;
};

const payloadPreview = (payload: Record<string, unknown>): string => {
  const entries = Object.entries(payload).slice(0, 2);
  if (entries.length === 0) {
    return "no payload";
  }

  return entries
    .map(([key, value]) => `${key}: ${typeof value === "string" ? value : JSON.stringify(value)}`)
    .join(" · ");
};

export function TimelineEvent({ event }: TimelineEventProps): React.JSX.Element {
  return (
    <div className="timeline-event">
      <div className="timeline-meta">
        <span className="timeline-type">{event.eventType}</span>
        <span className="timeline-time">{formatDateTime(event.eventTime)}</span>
      </div>
      <p className="timeline-payload">{payloadPreview(event.payloadJson)}</p>
    </div>
  );
}
