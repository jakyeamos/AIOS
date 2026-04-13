import Link from "next/link";

import type { Prompt } from "@/lib/types";
import { StatusBadge } from "@/components/primitives/StatusBadge";

type PromptCardProps = {
  prompt: Prompt;
};

export function PromptCard({ prompt }: PromptCardProps): React.JSX.Element {
  return (
    <article className="panel-card">
      <div className="panel-row">
        <p className="panel-title">{prompt.classification}</p>
        {prompt.reusableCandidate ? <StatusBadge status="healthy" label="candidate" /> : null}
      </div>
      <p>{prompt.promptText?.slice(0, 200) ?? "No prompt text captured."}</p>
      <div className="panel-metrics">
        <span>session: {prompt.sessionId}</span>
        <span>score: {prompt.outcomeScore ?? "-"}</span>
        {prompt.promptHash ? <Link href={`/prompts/${prompt.promptHash}`}>details</Link> : null}
      </div>
    </article>
  );
}
