import { execFileSync } from "node:child_process";

import { resolveAiosRoot } from "@/server/aios/filesystem";

export type CtsContext = {
  index_status?: string;
  architecture_summary?: string;
  estimated_blast_radius?: number;
  confidence_note?: string;
  directly_relevant_nodes?: string[];
};

export const getCtsContext = (repoPath: string | null, task: string): CtsContext | null => {
  if (!repoPath) {
    return null;
  }

  try {
    const output = execFileSync(
      "python3",
      [
        "-c",
        [
          "import json, sys",
          "from services.cts import get_minimal_context",
          "payload = get_minimal_context(repo_path=sys.argv[1], task=sys.argv[2], changed_files=[], max_tokens=240)",
          "print(json.dumps(payload))",
        ].join("; "),
        repoPath,
        task,
      ],
      {
        cwd: resolveAiosRoot(),
        encoding: "utf8",
      },
    );

    return JSON.parse(output) as CtsContext;
  } catch {
    return null;
  }
};
