import { PageShell } from "@/components/layout/PageShell";
import { StartWorkSurface } from "@/components/v2/V2OperatorShell";
import { getCaller } from "@/server/caller";

export default async function StartWorkPage(): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const [overview, projects] = await Promise.all([
    caller.controlPlane.overview(),
    caller.projects.list({ limit: 100 }),
  ]);

  return (
    <PageShell title="Start work" subtitle="Turn intent into an inspectable route. The durable start action is gated until the governed mutation slice ships.">
      <StartWorkSurface overview={overview} projects={projects} />
    </PageShell>
  );
}
