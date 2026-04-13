import { formatDateTime } from "@/lib/format";
import type { AnomalyAlert as AnomalyAlertType } from "@/lib/types";

import { StatusBadge } from "@/components/primitives/StatusBadge";

type AnomalyAlertProps = {
  anomaly: AnomalyAlertType;
};

export function AnomalyAlert({ anomaly }: AnomalyAlertProps): React.JSX.Element {
  return (
    <article className="panel-card">
      <div className="panel-row">
        <p className="panel-title">{anomaly.type}</p>
        <StatusBadge status={anomaly.severity} />
      </div>
      <p>{anomaly.message}</p>
      <p className="panel-subtitle">{formatDateTime(anomaly.detectedAt)}</p>
    </article>
  );
}
