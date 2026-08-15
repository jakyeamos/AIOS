import assert from "node:assert/strict";
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";

import { findRuntimePageViolations } from "./assert-runtime-pages-dynamic.mjs";

test("checked-in caller pages are dynamic", async () => {
  const appDirectory = path.resolve(import.meta.dirname, "..", "app");

  assert.deepEqual(await findRuntimePageViolations(appDirectory), []);
});

test("reports a database-backed page that can be prerendered", async () => {
  const appDirectory = await mkdtemp(path.join(tmpdir(), "aios-runtime-pages-"));
  const pageDirectory = path.join(appDirectory, "projects");

  try {
    await mkdir(pageDirectory);
    const pagePath = path.join(pageDirectory, "page.tsx");
    await writeFile(
      pagePath,
      'import { getCaller } from "@/server/caller";\nexport default async function Page() { return getCaller(); }\n',
      "utf8",
    );

    assert.deepEqual(await findRuntimePageViolations(appDirectory), [pagePath]);
  } finally {
    await rm(appDirectory, { recursive: true, force: true });
  }
});
