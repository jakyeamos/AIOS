import { execFileSync } from "node:child_process";
import os from "node:os";
import path from "node:path";

import { resolveAiosRoot } from "@/server/aios/filesystem";

export type PatternApprovalDecision = "approve" | "reject";

export type PatternApprovalUpdateInput = {
  id: string;
  decision: PatternApprovalDecision;
};

export type PatternApprovalResult = {
  ok: boolean;
  id: string;
  changedRows: number;
};

type PythonPatternApprovalResult = {
  ok: boolean;
  id: string;
  changed_rows: number;
};

type PythonEnvelope = {
  data?: PythonPatternApprovalResult;
  error?: { message?: string };
};

const resolveDbPath = (): string => {
  const configuredPath = process.env.AIOS_DB?.trim();
  if (!configuredPath) {
    return path.join(os.homedir(), "AIOS", "data", "aios.db");
  }
  if (configuredPath === "~") {
    return os.homedir();
  }
  if (configuredPath.startsWith("~/")) {
    return path.join(os.homedir(), configuredPath.slice(2));
  }
  return path.resolve(configuredPath);
};

export const updatePatternApprovalViaPythonOwner = (
  input: PatternApprovalUpdateInput,
): PatternApprovalResult => {
  const root = resolveAiosRoot();
  const script = path.join(root, "bin", "aios.py");
  try {
    const output = execFileSync(
      "python3",
      [
        script,
        "--json",
        "--db",
        resolveDbPath(),
        "pattern-approval-update",
        "--payload-json",
        JSON.stringify(input),
      ],
      {
        cwd: root,
        encoding: "utf8",
        maxBuffer: 256 * 1024,
      },
    );
    const envelope = JSON.parse(output) as PythonEnvelope;
    if (!envelope.data) {
      throw new Error(envelope.error?.message ?? "Python owner returned no pattern approval payload.");
    }
    return {
      ok: envelope.data.ok,
      id: envelope.data.id,
      changedRows: envelope.data.changed_rows,
    };
  } catch (error) {
    if (error instanceof Error && error.message.startsWith("Python owner returned")) {
      throw error;
    }
    throw new Error("Python pattern approval owner rejected the mutation.", { cause: error });
  }
};
