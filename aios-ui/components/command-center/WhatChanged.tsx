import type { AnomalyAlert } from "@/lib/types";

import { AnomalyAlert as AnomalyAlertCard } from "@/components/panels/AnomalyAlert";

type WhatChangedProps = {
  anomalies: AnomalyAlert[];
};

export function WhatChanged({ anomalies }: WhatChangedProps): React.JSX.Element {
  return (
    <section>
      <h3 className="section-title">What Changed</h3>
      <div className="stack">
        {anomalies.map((anomaly) => (
          <AnomalyAlertCard key={anomaly.id} anomaly={anomaly} />
        ))}
      </div>
    </section>
  );
}
