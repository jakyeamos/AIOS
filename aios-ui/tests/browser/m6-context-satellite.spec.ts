import { expect, test } from "@playwright/test";

test("M6 context compiler satellite stays source-backed and read-only", async ({ page }, testInfo) => {
  const mutationRequests: string[] = [];
  const consoleErrors: string[] = [];
  const badResponses: string[] = [];
  const origin = new URL(`http://127.0.0.1:${process.env.AIOS_UI_TEST_PORT ?? "3210"}`).origin;

  page.on("request", (request) => {
    if (new URL(request.url()).origin === origin && ["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) {
      mutationRequests.push(`${request.method()} ${request.url()}`);
    }
  });
  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text());
    }
  });
  page.on("response", (response) => {
    if (new URL(response.url()).origin === origin && response.status() >= 400) {
      badResponses.push(`${response.status()} ${response.url()}`);
    }
  });

  for (const viewport of [
    { name: "mobile", width: 375, height: 812 },
    { name: "tablet", width: 768, height: 1024 },
    { name: "desktop", width: 1440, height: 900 },
  ]) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/context", { waitUntil: "networkidle" });
    await expect(page.getByRole("heading", { name: "Context Compiler", exact: true })).toBeVisible();
    await expect(page.getByText("read-only projection", { exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Projection contract", exact: true })).toBeVisible();

    const metrics = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      main: document.querySelectorAll("main").length,
      primaryNav: document.querySelectorAll("nav[aria-label='Primary']").length,
    }));
    expect(metrics.scrollWidth).toBe(metrics.clientWidth);
    expect(metrics.main).toBe(1);
    expect(metrics.primaryNav).toBe(1);
    await page.screenshot({ path: testInfo.outputPath(`m6-context-${viewport.name}.png`), fullPage: true });
  }

  await page.keyboard.press("Tab");
  expect(await page.evaluate(() => document.activeElement?.matches(":focus-visible") ?? false)).toBe(true);
  expect(mutationRequests).toEqual([]);
  expect(consoleErrors).toEqual([]);
  expect(badResponses).toEqual([]);
});
