import type { ProvenanceLevel } from "@/lib/status-provenance";

type ProvenanceBadgeProps = {
  level: ProvenanceLevel;
  source: string;
  reason: string;
};

export function ProvenanceBadge({ level, source, reason }: ProvenanceBadgeProps): React.JSX.Element {
  return (
    <span
      className={`provenance-badge provenance-${level}`}
      title={`${source}: ${reason}`}
      aria-label={`status provenance ${level}`}
    >
      {level}
    </span>
  );
}
