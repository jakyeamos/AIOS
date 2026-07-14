import { expect, test } from "@playwright/test";
import type { APIResponse } from "@playwright/test";

type JsonRecord = Record<string, unknown>;

const asRecord = (value: unknown): JsonRecord | null =>
  value && typeof value === "object" && !Array.isArray(value) ? (value as JsonRecord) : null;

const routeInput = (json: unknown): string => encodeURIComponent(JSON.stringify({ 0: { json } }));

const readTRPCJson = async (response: APIResponse): Promise<JsonRecord> => {
  const body = await response.json();
  const batch = Array.isArray(body) ? body[0] : body;
  const result = asRecord(asRecord(batch)?.result);
  const data = asRecord(result?.data);
  const json = asRecord(data?.json);
  if (!json) {
    throw new Error("Expected a typed tRPC JSON response.");
  }
  return json;
};

test("M3 read-only operator shell keeps the task loop inspectable", async ({ page, request }, testInfo) => {
  const overviewResponse = await request.get(`/api/trpc/controlPlane.overview?batch=1&input=${routeInput(null)}`);
  expect(overviewResponse.status()).toBe(200);
  const overview = await readTRPCJson(overviewResponse);
  const runs = Array.isArray(overview.runs) ? overview.runs : [];
  const runId = asRecord(runs[0])?.id;
  expect(typeof runId).toBe("string");

  const mutationRequests: string[] = [];
  const consoleErrors: string[] = [];
  const badResponses: string[] = [];
  const origin = new URL(page.url()).origin;
  page.on("request", (requestEvent) => {
    if (requestEvent.url().startsWith(origin) && ["POST", "PUT", "PATCH", "DELETE"].includes(requestEvent.method())) {
      mutationRequests.push(`${requestEvent.method()} ${requestEvent.url()}`);
    }
  });
  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text());
    }
  });
  page.on("response", (response) => {
    if (response.url().startsWith(origin) && response.status() >= 400) {
      badResponses.push(`${response.status()} ${response.url()}`);
    }
  });

  const routes = [
    { name: "today", path: "/", heading: "Today" },
    { name: "start", path: "/start", heading: "Start work" },
    { name: "current-run", path: `/runs/${String(runId)}`, heading: "Current run" },
  ];

  for (const viewport of [
    { name: "mobile", width: 375, height: 812 },
    { name: "tablet", width: 768, height: 1024 },
    { name: "desktop", width: 1440, height: 900 },
  ]) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });

    for (const route of routes) {
      await page.goto(route.path, { waitUntil: "networkidle" });
      await expect(page.getByRole("heading", { name: route.heading, exact: false }).first()).toBeVisible();
      const metrics = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
        main: document.querySelectorAll("main").length,
        primaryNav: document.querySelectorAll("nav[aria-label='Primary']").length,
        currentPageLinks: document.querySelectorAll("a[aria-current='page']").length,
      }));
      expect(metrics.scrollWidth).toBe(metrics.clientWidth);
      expect(metrics.main).toBe(1);
      expect(metrics.primaryNav).toBe(1);
      expect(metrics.currentPageLinks).toBeGreaterThan(0);
      await page.screenshot({ path: testInfo.outputPath(`m3-${route.name}-${viewport.name}.png`), fullPage: true });
    }
  }

  await page.goto("/start", { waitUntil: "networkidle" });
  await expect(page.getByText("read-only projection")).toBeVisible();
  await expect(page.getByText("start gated")).toBeVisible();
  await expect(page.getByRole("heading", { name: "State contract" })).toBeVisible();
  await expect(page.getByText("Blocked / ambiguous")).toBeVisible();
  await expect(page.getByText("Stale", { exact: true })).toBeVisible();
  await expect(page.getByText("Empty", { exact: true })).toBeVisible();

  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  const focusedTag = await page.evaluate(() => document.activeElement?.tagName ?? "");
  expect(focusedTag).not.toBe("BODY");
  expect(await page.evaluate(() => document.activeElement?.matches(":focus-visible") ?? false)).toBe(true);

  expect(mutationRequests).toEqual([]);
  expect(consoleErrors).toEqual([]);
  expect(badResponses).toEqual([]);
});
