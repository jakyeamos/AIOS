import { expect, test } from "@playwright/test";
import type { APIResponse, Page } from "@playwright/test";

type JsonRecord = Record<string, unknown>;

const asRecord = (value: unknown): JsonRecord | null =>
  value && typeof value === "object" && !Array.isArray(value) ? (value as JsonRecord) : null;

const unwrapTRPC = (value: unknown): JsonRecord => {
  const batch = Array.isArray(value) ? value[0] : value;
  const result = asRecord(asRecord(batch)?.result);
  const data = asRecord(result?.data);
  const json = asRecord(data?.json);
  if (!json) {
    throw new Error("Expected a typed tRPC JSON response.");
  }
  return json;
};

const readJson = async (response: APIResponse): Promise<JsonRecord> => unwrapTRPC(await response.json());

const routeInput = (json: unknown): string => encodeURIComponent(JSON.stringify({ 0: { json } }));

const attachBrowserFailures = (page: Page): { consoleErrors: string[]; requestFailures: string[]; badResponses: string[] } => {
  const consoleErrors: string[] = [];
  const requestFailures: string[] = [];
  const badResponses: string[] = [];
  const origin = new URL(`http://127.0.0.1:${process.env.AIOS_UI_TEST_PORT ?? "3210"}`).origin;

  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text());
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

  return { consoleErrors, requestFailures, badResponses };
};

const focusSummary = async (page: Page): Promise<{ tag: string; label: string; focusVisible: boolean }> =>
  page.evaluate(() => {
    const element = document.activeElement;
    if (!element) {
      return { tag: "", label: "", focusVisible: false };
    }
    return {
      tag: element.tagName,
      label: (element.getAttribute("aria-label") || element.textContent || element.getAttribute("placeholder") || "")
        .trim()
        .slice(0, 120),
      focusVisible: element.matches(":focus-visible"),
    };
  });

test("M2 seeded control-plane browser contract", async ({ page, request }, testInfo) => {
  const failures = attachBrowserFailures(page);
  const overviewResponse = await request.get(`/api/trpc/controlPlane.overview?batch=1&input=${routeInput(null)}`);
  expect(overviewResponse.status()).toBe(200);
  const overview = await readJson(overviewResponse);
  const runs = Array.isArray(overview.runs) ? overview.runs : [];
  expect(Array.isArray(overview.workflowTemplates)).toBe(true);
  expect(runs.length).toBeGreaterThan(0);

  const runId = asRecord(runs[0])?.id;
  expect(typeof runId).toBe("string");
  const runDetailResponse = await request.get(
    `/api/trpc/controlPlane.runDetail?batch=1&input=${routeInput({ runId })}`,
  );
  expect(runDetailResponse.status()).toBe(200);
  const runDetail = await readJson(runDetailResponse);
  expect(asRecord(runDetail.run)).not.toBeNull();
  expect(Array.isArray(runDetail.events)).toBe(true);

  for (const viewport of [
    { name: "mobile", width: 375, height: 812 },
    { name: "tablet", width: 768, height: 1024 },
    { name: "desktop", width: 1440, height: 900 },
  ]) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/control", { waitUntil: "networkidle" });
    const metrics = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      main: document.querySelectorAll("main").length,
      nav: document.querySelectorAll("nav").length,
    }));
    expect(metrics.scrollWidth).toBe(metrics.clientWidth);
    expect(metrics.main).toBe(1);
    expect(metrics.nav).toBe(1);
    await page.screenshot({ path: testInfo.outputPath(`m2-control-${viewport.name}.png`), fullPage: true });
  }

  await page.goto("/control", { waitUntil: "networkidle" });
  const tabbableCount = await page.locator("a,button,input,select,textarea,[tabindex]:not([tabindex='-1'])").count();
  expect(tabbableCount).toBeGreaterThan(0);
  const focusTrail: Array<{ tag: string; label: string; focusVisible: boolean }> = [];
  for (let index = 0; index < 12; index += 1) {
    await page.keyboard.press("Tab");
    focusTrail.push(await focusSummary(page));
  }
  expect(focusTrail.every((entry) => entry.tag !== "BODY")).toBe(true);
  expect(focusTrail.some((entry) => entry.focusVisible)).toBe(true);

  expect(failures.consoleErrors).toEqual([]);
  expect(failures.requestFailures).toEqual([]);
  expect(failures.badResponses).toEqual([]);
});
