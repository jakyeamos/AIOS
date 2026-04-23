"use client";

import { useCallback, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

const RUNS = [
  { id: "run-1", label: "Queued jobs" },
  { id: "run-2", label: "Prompt Reuse Rate" },
];

export function ClientInteractionFixture() {
  const router = useRouter();
  const [filter, setFilter] = useState("");
  const visibleRuns = useMemo(
    () => RUNS.filter((item) => item.label.toLowerCase().includes(filter.toLowerCase())),
    [filter],
  );

  const handleRun = useCallback(() => {
    setFilter("queued");
    router.push("/control");
  }, [router]);

  return (
    <section>
      <h2>Prompt Reuse Rate</h2>
      <button onClick={handleRun}>Run check</button>
      {visibleRuns.length === 0 ? (
        <p>No queued runs. Run check to populate this list.</p>
      ) : (
        <ul>
          {visibleRuns.map((item) => (
            <li key={item.id}>{item.label}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
