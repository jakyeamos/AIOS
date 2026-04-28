import type { Pattern } from "@/lib/types";
import { StatusBadge } from "@/components/primitives/StatusBadge";

type PatternRowProps = {
  pattern: Pattern;
};

export function PatternRow({ pattern }: PatternRowProps): React.JSX.Element {
  return (
    <div className="table-row">
      <span title={pattern.id}>
        {pattern.label
          ? pattern.label.slice(0, 80) + (pattern.label.length > 80 ? "…" : "")
          : <span className="mono">{pattern.id.slice(0, 8)}&hellip;</span>}
      </span>
      <span>
        <StatusBadge status={pattern.humanApproved ? "healthy" : "warning"} label={pattern.state} />
      </span>
      <span>{pattern.sessionCount}</span>
      <span>{new Date(pattern.lastSeen).toLocaleDateString("en-US")}</span>
    </div>
  );
}
