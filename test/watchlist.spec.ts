import { test, expect } from "@playwright/test";

test.describe("Watchlist management", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    // Wait for watchlist to load
    await expect(page.getByText("AAPL", { exact: true }).first()).toBeVisible({ timeout: 15_000 });
  });

  test("add a ticker to the watchlist", async ({ page }) => {
    const tickerInput = page.getByPlaceholder("Add ticker...");
    await tickerInput.fill("PYPL");
    await tickerInput.press("Enter");

    // Verify PYPL appears in the watchlist
    await expect(page.getByText("PYPL", { exact: true }).first()).toBeVisible({ timeout: 10_000 });
  });

  test("remove a ticker from the watchlist", async ({ page }) => {
    // Find the NFLX row and click its remove button (the "x" button)
    const nflxRow = page.locator("tr").filter({ hasText: "NFLX" });
    await nflxRow.locator("button", { hasText: "x" }).click();

    // Verify NFLX is gone from the watchlist
    await expect(
      page.locator("tr").filter({ hasText: "NFLX" })
    ).not.toBeVisible({ timeout: 5_000 });
  });
});
