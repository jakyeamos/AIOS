import seededRuns from "@/demo/runs";

const getCaller = () => null;

export default function RunsPageFixture() {
  const realRuns = getCaller();
  const runs = realRuns ?? seededRuns;

  return (
    <main>
      <h1>Open Sessions</h1>
      <p>{runs.length} sessions in this preview fixture.</p>
    </main>
  );
}
