import { PageShell } from "@/components/layout/PageShell";

export default async function CompareDetailPage({
  params,
}: {
  params: Promise<{ a: string; b: string }>;
}): Promise<React.JSX.Element> {
  const { a, b } = await params;

  return (
    <PageShell title={`Compare ${a} vs ${b}`} subtitle="Scaffolded side-by-side diff surface.">
      <section className="grid grid-2">
        <article className="panel-card">
          <h3 className="section-title">Variant A</h3>
          <p>Attach baseline metrics, traces, and prompt snapshots.</p>
        </article>
        <article className="panel-card">
          <h3 className="section-title">Variant B</h3>
          <p>Attach challenger metrics, traces, and prompt snapshots.</p>
        </article>
      </section>
    </PageShell>
  );
}
