import { PageShell } from "@/components/layout/PageShell";
import { ExpectationTargetsEditor } from "@/components/settings/ExpectationTargetsEditor";
import { getCaller } from "@/server/caller";

export const dynamic = "force-dynamic";

export default async function SettingsPage(): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const targets = await caller.insights.expectations({
    scopeType: "global",
    scopeKey: "global",
  });

  return (
    <PageShell title="Settings" subtitle="Model defaults, budgets, and guardrails.">
      <ExpectationTargetsEditor targets={targets} />
    </PageShell>
  );
}
