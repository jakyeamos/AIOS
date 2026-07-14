import { PageShell } from "@/components/layout/PageShell";
import { TodaySurface } from "@/components/v2/V2OperatorShell";
import { getCaller } from "@/server/caller";

export default async function TodayPage(): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const overview = await caller.controlPlane.overview();

  return (
    <PageShell title="Today" subtitle="Resume the operating loop from source-backed project, run, evidence, and next-action projections.">
      <TodaySurface overview={overview} />
    </PageShell>
  );
}
