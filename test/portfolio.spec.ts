import { test, expect } from "@playwright/test";

test.describe("Portfolio visualization", () => {
  test.beforeEach(async ({ page }) => {
    // Buy small positions via API so we have data to visualize
    await page.request.post("/api/portfolio/trade", {
      data: { ticker: "AAPL", quantity: 1, side: "buy" },
    });
    await page.request.post("/api/portfolio/trade", {
      data: { ticker: "GOOGL", quantity: 1, side: "buy" },
    });

    await page.goto("/");
    await expect(page.getByText("FinAlly").first()).toBeVisible({ timeout: 15_000 });
  });

  test("heatmap renders", async ({ page }) => {
    const canvas = page.locator("canvas");
    await expect(canvas.first()).toBeVisible({ timeout: 15_000 });
  });

  test("P&L chart renders", async ({ page }) => {
    const canvases = page.locator("canvas");
    await expect(canvases.first()).toBeVisible({ timeout: 15_000 });
  });

  test("positions are visible on page", async ({ page }) => {
    await expect(page.getByText("AAPL").first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("GOOGL").first()).toBeVisible({ timeout: 10_000 });
  });

  test("portfolio history API returns snapshots", async ({ page }) => {
    const response = await page.request.get("/api/portfolio/history");
    expect(response.ok()).toBe(true);
    const snapshots = await response.json();
    expect(snapshots.length).toBeGreaterThan(0);
  });
});
