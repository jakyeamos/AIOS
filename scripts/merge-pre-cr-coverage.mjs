import { spawn } from "node:child_process";
import { mkdtemp, readFile, rename, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

const repoRoot = path.resolve(import.meta.dirname, "..");
const pythonCoveragePath = "/private/tmp/aios-pre-cr-python.lcov";
const combinedCoveragePath = "/private/tmp/aios-pre-cr-combined.lcov";

export function mergeLcovReports(reports) {
  const normalized = reports.map((report) => report.trim()).filter(Boolean);
  if (normalized.length !== reports.length) {
    throw new Error("Every Pre-CR coverage report must contain LCOV records.");
  }
  if (normalized.some((report) => !report.includes("end_of_record"))) {
    throw new Error("A Pre-CR coverage report is missing an LCOV end_of_record marker.");
  }
  return `${normalized.join("\n")}\n`;
}

async function runCommand(command, args) {
  await new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd: repoRoot,
      env: process.env,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stderr = "";
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) {
        resolve();
        return;
      }
      reject(new Error(`Node coverage command failed with exit code ${code}: ${stderr.trim()}`));
    });
  });
}

async function main() {
  const reportsDir = await mkdtemp(path.join(tmpdir(), "aios-pre-cr-node-coverage-"));
  const c8Bin = path.join(repoRoot, "node_modules", "c8", "bin", "c8.js");
  const nodeCoveragePath = path.join(reportsDir, "lcov.info");
  const temporaryOutputPath = `${combinedCoveragePath}.tmp-${process.pid}`;

  try {
    await runCommand(process.execPath, [
      c8Bin,
      "--reporter=lcov",
      `--reports-dir=${reportsDir}`,
      "--include=tools/**/*.mjs",
      process.execPath,
      "--test",
      "tests/context-compiler.test.mjs",
    ]);
    const [pythonCoverage, nodeCoverage] = await Promise.all([
      readFile(pythonCoveragePath, "utf8"),
      readFile(nodeCoveragePath, "utf8"),
    ]);
    await writeFile(temporaryOutputPath, mergeLcovReports([pythonCoverage, nodeCoverage]), "utf8");
    await rename(temporaryOutputPath, combinedCoveragePath);
    process.stdout.write(`Combined Pre-CR coverage: ${combinedCoveragePath}\n`);
  } finally {
    await rm(reportsDir, { recursive: true, force: true });
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
    process.exitCode = 1;
  });
}
