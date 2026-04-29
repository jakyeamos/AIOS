import { spawnSync } from "node:child_process";

const baseline = 71;
const eslint = spawnSync("./node_modules/.bin/eslint", [".", "--format", "json"], {
  cwd: new URL("..", import.meta.url),
  encoding: "utf8",
});

if (eslint.error) {
  console.error(eslint.error.message);
  process.exit(1);
}

let results;
try {
  results = JSON.parse(eslint.stdout || "[]");
} catch {
  console.error(eslint.stdout);
  console.error(eslint.stderr);
  process.exit(1);
}

const warningCount = results.reduce((total, item) => total + Number(item.warningCount || 0), 0);
const errorCount = results.reduce((total, item) => total + Number(item.errorCount || 0), 0);

if (errorCount > 0) {
  console.error(`ESLint reported ${errorCount} error(s).`);
  process.exit(1);
}

if (warningCount > baseline) {
  console.error(`ESLint warning baseline exceeded: ${warningCount} > ${baseline}.`);
  process.exit(1);
}

console.log(`ESLint warning baseline ok: ${warningCount}/${baseline}.`);
