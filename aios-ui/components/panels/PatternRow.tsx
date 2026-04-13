import type { Pattern } from "@/lib/types";
import { StatusBadge } from "@/components/primitives/StatusBadge";

type PatternRowProps = {
  pattern: Pattern;
};

export function PatternRow({ pattern }: PatternRowProps): React.JSX.Element {
  return (
    <div className="table-row">
      <span className="mono">{pattern.id}</span>
      <span>
        <StatusBadge status={pattern.humanApproved ? "healthy" : "warning"} label={pattern.state} />
      </span>
      <span>{pattern.sessionCount}</span>
      <span>{new Date(pattern.lastSeen).toLocaleDateString("en-US")}</span>
    </div>
  );
}
