import { defineConfig } from "@playwright/test";
import path from "node:path";

const port = Number(process.env.AIOS_UI_TEST_PORT ?? "3210");
const baseURL = `http://127.0.0.1:${port}`;
const repoRoot = path.resolve(process.cwd(), "..");
const databasePath = path.join(repoRoot, "aios-ui", "test-results", "m6-verify-review-closeout.sqlite");

export default defineConfig({
  testDir: "./tests/browser",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  reporter: [["list"], ["json", { outputFile: "test-results/m2-browser.json" }]],
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: {
    command: `node --experimental-strip-types tests/browser/global-setup.ts --m6-seed && pnpm exec next dev --hostname 127.0.0.1 --port ${port}`,
    url: baseURL,
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      ...process.env,
      AIOS_DB: databasePath,
      AIOS_ROOT: repoRoot,
    },
  },
});
