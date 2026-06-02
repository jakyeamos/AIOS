import Link from "next/link";

import type { PhaseStatusReport } from "@/lib/control-plane";

type PhaseStatusBannerProps = {
  phaseStatus: PhaseStatusReport[];
};

const phaseNumber = (phase: string): string => phase.replace("phase_", "");

export function PhaseStatusBanner({ phaseStatus }: PhaseStatusBannerProps): React.JSX.Element | null {
  const incomplete = phaseStatus.filter((phase) => phase.status !== "complete");
  if (incomplete.length === 0) {
    return null;
  }
  const visible = incomplete.slice(0, 3);
  const remainingCount = Math.max(incomplete.length - visible.length, 0);

  return (
    <section className="alert-item alert-info">
      <div className="panel-row">
        <div>
          <h3 className="section-title">Operator Surfaces Filling In</h3>
          <p>
            Some operator surfaces are still being populated.{" "}
            {visible.map((phase) => `Phase ${phaseNumber(phase.phase)} is ${phase.status}`).join("; ")}
            {remainingCount > 0 ? `; and ${remainingCount} more phase(s)` : ""}. Metrics will fill in as those phases ship.
          </p>
        </div>
        <Link href="/control" className="button-secondary">
          Learn more
        </Link>
      </div>
    </section>
  );
}
