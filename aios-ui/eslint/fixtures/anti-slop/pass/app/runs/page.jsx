import seededRuns from "@/demo/runs";

const getCaller = () => ({ runs: seededRuns });

export default function RunsPageFixture() {
  const caller = getCaller();
  const runs = caller.runs;

  return (
    <main>
      <h1>Open Sessions</h1>
      <p>{runs.length} sessions in this preview fixture.</p>
    </main>
  );
}
