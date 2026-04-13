import type { SessionStatus } from "@/lib/types";

export type BadgeStatus = SessionStatus | "healthy" | "warning" | "error" | "unknown";

type StatusBadgeProps = {
  status: BadgeStatus;
  label?: string;
};

const defaultLabelFromStatus = (status: BadgeStatus): string => {
  if (status === "open") {
    return "open";
  }

  if (status === "closed") {
    return "closed";
  }

  if (status === "abandoned") {
    return "abandoned";
  }

  return status;
};

export function StatusBadge({ status, label }: StatusBadgeProps): React.JSX.Element {
  return (
    <span className={`status-badge status-${status}`}>
      <span className="status-dot" aria-hidden="true" />
      {label ?? defaultLabelFromStatus(status)}
    </span>
  );
}
