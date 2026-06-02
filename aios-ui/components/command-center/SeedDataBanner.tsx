"use client";

import { trpc } from "@/lib/trpc";

type SeedDataBannerProps = {
  seedDataCount: number;
};

export function SeedDataBanner({ seedDataCount }: SeedDataBannerProps): React.JSX.Element | null {
  const utils = trpc.useUtils();

  if (seedDataCount === 0) {
    return null;
  }

  return (
    <section className="alert-item alert-warning">
      <div className="panel-row">
        <div>
          <h3 className="section-title">Demo Data Shown</h3>
          <p>
            Demo data shown for {seedDataCount} catalog row(s). Registry parsing succeeded for workflows only; fallback catalog rows remain labeled for review.
          </p>
        </div>
        <button type="button" className="button-secondary" onClick={() => void utils.controlPlane.overview.invalidate()}>
          Refresh
        </button>
      </div>
    </section>
  );
}
