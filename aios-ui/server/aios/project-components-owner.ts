import { execFileSync } from "node:child_process";
import os from "node:os";
import path from "node:path";

import type { AiosProjectComponentKey } from "@/lib/control-plane";
import { resolveAiosRoot } from "@/server/aios/filesystem";

export type ProjectComponentUpdateInput = {
  projectId: string;
  componentKey: AiosProjectComponentKey;
  enabled: boolean;
};

type PythonComponentSetting = {
  project_id: string;
  component_key: AiosProjectComponentKey;
  enabled: boolean;
  updated_at: string;
};

type PythonEnvelope = {
  data?: PythonComponentSetting;
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

export const setAiosProjectComponentEnabledViaPythonOwner = (
  input: ProjectComponentUpdateInput,
): PythonComponentSetting => {
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
        "project-component-update",
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
      throw new Error(envelope.error?.message ?? "Python owner returned no component payload.");
    }
    return envelope.data;
  } catch (error) {
    if (error instanceof Error && error.message.startsWith("Python owner returned")) {
      throw error;
    }
    throw new Error("Python project-component owner rejected the mutation.", { cause: error });
  }
};
