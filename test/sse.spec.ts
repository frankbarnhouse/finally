import { test, expect } from "@playwright/test";

test.describe("SSE connection", () => {
  test("SSE endpoint is accessible", async ({ page }) => {
    // Navigate to the SSE endpoint and verify it responds
    // We can't use request.get() for SSE since it's a streaming response
    // Instead, verify the frontend connects and receives data
    await page.goto("/");
    await expect(page.getByText("FinAlly").first()).toBeVisible({ timeout: 15_000 });

    // Verify prices appear (proves SSE is working)
    const priceCell = page.locator("td").filter({ hasText: /^\d{1,4}\.\d{2}$/ });
    await expect(priceCell.first()).toBeVisible({ timeout: 15_000 });
  });

  test("connection status shows connected after page load", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("connected")).toBeVisible({ timeout: 10_000 });
  });

  test("health endpoint returns ok", async ({ request }) => {
    const response = await request.get("/api/health");
    expect(response.ok()).toBe(true);
  });
});
