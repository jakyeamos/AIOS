import { ActiveRuns } from "@/components/command-center/ActiveRuns";
import { HealthGrid } from "@/components/command-center/HealthGrid";
import { RecentActivity } from "@/components/command-center/RecentActivity";
import { WhatChanged } from "@/components/command-center/WhatChanged";
import { PageShell } from "@/components/layout/PageShell";
import { seededAnomalies } from "@/lib/seed";
import { getCaller } from "@/server/caller";

export default async function CommandCenterPage(): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const [sessions, events, costs] = await Promise.all([
    caller.sessions.list({ limit: 8 }),
    caller.sessions.recentEvents({ limit: 12 }),
    caller.costs.summary({ period: "week" }),
  ]);

  const activeSessions = sessions.filter((session) => session.status === "open").slice(0, 4);

  return (
    <PageShell
      title="Command Center"
      subtitle="Health at a glance with active runs, anomalies, and efficiency signals."
    >
      <HealthGrid sessions={sessions} costs={costs} />
      <div className="grid grid-2">
        <ActiveRuns sessions={activeSessions.length > 0 ? activeSessions : sessions.slice(0, 4)} />
        <RecentActivity events={events} />
      </div>
      <WhatChanged anomalies={seededAnomalies} />
    </PageShell>
  );
}
