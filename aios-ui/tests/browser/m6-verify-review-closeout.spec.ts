import { expect, test } from "@playwright/test";
import type { APIResponse, Page } from "@playwright/test";

type JsonRecord = Record<string, unknown>;

const RUNS = [
  { id: "m6-run-verify", activeStage: "Verify" },
  { id: "m6-run-review", activeStage: "Review" },
  { id: "m6-run-closeout", activeStage: "Closeout" },
] as const;

const asRecord = (value: unknown): JsonRecord | null =>
  value && typeof value === "object" && !Array.isArray(value) ? (value as JsonRecord) : null;

const routeInput = (json: unknown): string => encodeURIComponent(JSON.stringify({ 0: { json } }));

const readTRPCJson = async (response: APIResponse): Promise<JsonRecord> => {
  const body: unknown = await response.json();
  const batch = Array.isArray(body) ? body[0] : body;
  const result = asRecord(asRecord(batch)?.result);
  const data = asRecord(result?.data);
  const json = asRecord(data?.json);
  if (!json) {
    throw new Error("Expected a typed tRPC JSON response.");
  }
  return json;
};

const focusSummary = async (page: Page): Promise<{ tag: string; focusVisible: boolean }> =>
  page.evaluate(() => ({
    tag: document.activeElement?.tagName ?? "",
    focusVisible: document.activeElement?.matches(":focus-visible") ?? false,
  }));

const attachBrowserFailures = (page: Page): {
  consoleErrors: string[];
  requestFailures: string[];
  badResponses: string[];
  mutationRequests: string[];
} => {
  const consoleErrors: string[] = [];
  const requestFailures: string[] = [];
  const badResponses: string[] = [];
  const mutationRequests: string[] = [];
  const origin = new URL(`http://127.0.0.1:${process.env.AIOS_UI_TEST_PORT ?? "3210"}`).origin;

  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text());
    }
  });
  page.on("request", (request) => {
    if (new URL(request.url()).origin === origin && ["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) {
      mutationRequests.push(`${request.method()} ${request.url()}`);
    }
  });
  page.on("requestfailed", (request) => {
    if (new URL(request.url()).origin === origin) {
      requestFailures.push(`${request.method()} ${request.url()}: ${request.failure()?.errorText ?? "failed"}`);
    }
  });
  page.on("response", (response) => {
    if (new URL(response.url()).origin === origin && response.status() >= 400) {
      badResponses.push(`${response.status()} ${response.url()}`);
    }
  });

  return { consoleErrors, requestFailures, badResponses, mutationRequests };
};

const assertJourney = async (
  page: Page,
  runId: string,
  activeStage: string,
  testInfo: { outputPath: (name: string) => string },
): Promise<void> => {
  const detailResponse = await page.request.get(
    `/api/trpc/controlPlane.runDetail?batch=1&input=${routeInput({ runId })}`,
  );
  expect(detailResponse.status()).toBe(200);
  const detail = await readTRPCJson(detailResponse);
  const run = asRecord(detail.run);
  expect(run?.id).toBe(runId);
  const events = Array.isArray(detail.events) ? detail.events : [];
  expect(events.length).toBe(1);
  const inspection = asRecord(detail.inspection);
  const selectedSections = Array.isArray(inspection?.selectedSections) ? inspection.selectedSections : [];
  expect(selectedSections.length).toBe(3);
  expect(selectedSections.every((section) => {
    const record = asRecord(section);
    return typeof record?.title === "string" && typeof record.itemCount === "number";
  })).toBe(true);

  await page.goto(`/runs/${runId}`, { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: "Current run", exact: false }).first()).toBeVisible();
  const rail = page.getByRole("list", { name: "Run stages" });
  for (const label of ["Verify", "Review", "Closeout"]) {
    await expect(rail.getByText(label, { exact: true })).toBeVisible();
  }
  await expect(rail.locator("[data-stage='active']").getByText(activeStage, { exact: true })).toBeVisible();
  await expect(page.locator("dt").filter({ hasText: "Stage" }).locator("..").locator("dd")).toHaveText(activeStage);
  await expect(page.locator("[aria-label^='status provenance']").first()).toBeVisible();

  const metrics = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    main: document.querySelectorAll("main").length,
    primaryNav: document.querySelectorAll("nav[aria-label='Primary']").length,
  }));
  expect(metrics.scrollWidth).toBe(metrics.clientWidth);
  expect(metrics.main).toBe(1);
  expect(metrics.primaryNav).toBe(1);
  await page.screenshot({ path: testInfo.outputPath(`m6-${runId}.png`), fullPage: true });
};

test("M6 Verify → Review → Closeout browser contract", async ({ page }, testInfo) => {
  const failures = attachBrowserFailures(page);

  for (const viewport of [
    { name: "mobile", width: 375, height: 812 },
    { name: "tablet", width: 768, height: 1024 },
    { name: "desktop", width: 1440, height: 900 },
  ]) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    for (const run of RUNS) {
      await assertJourney(page, run.id, run.activeStage, {
        outputPath: (name) => testInfo.outputPath(`${viewport.name}-${name}`),
      });
    }
  }

  await page.goto(`/runs/${RUNS[2].id}`, { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: "Lifecycle events", exact: true })).toBeVisible();
  await expect(page.getByText("closeout", { exact: true })).toBeVisible();
  await expect(page.getByText(/Touched files:\s*1/)).toBeVisible();
  await expect(page.getByText(/unpredicted\s*0/)).toBeVisible();

  for (let index = 0; index < 12; index += 1) {
    await page.keyboard.press("Tab");
  }
  const focus = await focusSummary(page);
  expect(focus.tag).not.toBe("BODY");
  expect(focus.focusVisible).toBe(true);

  await page.goto("/control", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: "Approval Queue", exact: true })).toBeVisible();
  const reviewResponse = page.waitForResponse(
    (response) => new URL(response.url()).pathname === "/api/trpc/controlPlane.reviewWriteback" && response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Approve", exact: true }).click();
  expect((await reviewResponse).status()).toBe(412);

  const unexpectedBadResponses = failures.badResponses.filter((response) => {
    const [, responseUrl] = response.split(" ", 2);
    return !(response.startsWith("412 ") && responseUrl && new URL(responseUrl).pathname === "/api/trpc/controlPlane.reviewWriteback");
  });
  const unexpectedRequestFailures = failures.requestFailures.filter((failure) => {
    const [, failureUrl] = failure.split(" ", 2);
    return !(failure.startsWith("GET ") && failure.endsWith("net::ERR_ABORTED") && failureUrl && new URL(failureUrl).pathname.startsWith("/__nextjs_font/"));
  });
  expect(unexpectedBadResponses).toEqual([]);
  expect(unexpectedRequestFailures).toEqual([]);
  expect(failures.consoleErrors).toEqual([]);
  expect(failures.mutationRequests).toHaveLength(1);
  expect(new URL(failures.mutationRequests[0].split(" ", 2)[1]).pathname).toBe("/api/trpc/controlPlane.reviewWriteback");
});
