import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath, pathToFileURL } from "node:url";

const FORCE_DYNAMIC_PATTERN = /export\s+const\s+dynamic\s*=\s*["']force-dynamic["']/;

const walkPages = async (directory) => {
  const entries = await readdir(directory, { withFileTypes: true });
  const pages = [];

  for (const entry of entries) {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      pages.push(...(await walkPages(target)));
    } else if (entry.name === "page.tsx") {
      pages.push(target);
    }
  }

  return pages;
};

export const findRuntimePageViolations = async (appDirectory) => {
  const violations = [];

  for (const pagePath of await walkPages(appDirectory)) {
    const source = await readFile(pagePath, "utf8");
    if (source.includes('from "@/server/caller"') && !FORCE_DYNAMIC_PATTERN.test(source)) {
      violations.push(pagePath);
    }
  }

  return violations.sort();
};

const isDirectExecution =
  process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;

if (isDirectExecution) {
  const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
  const appDirectory = path.resolve(scriptDirectory, "..", "app");
  const violations = await findRuntimePageViolations(appDirectory);

  if (violations.length > 0) {
    console.error("Database-backed pages must export dynamic = force-dynamic:");
    for (const violation of violations) {
      console.error(`- ${path.relative(path.resolve(scriptDirectory, ".."), violation)}`);
    }
    process.exitCode = 1;
  } else {
    console.log("Runtime page contract passed.");
  }
}
