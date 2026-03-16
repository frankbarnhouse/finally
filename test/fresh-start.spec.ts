import { test, expect } from "@playwright/test";

test.describe("Fresh start", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("FinAlly").first()).toBeVisible({ timeout: 15_000 });
  });

  test("displays default watchlist with 10 tickers", async ({ page }) => {
    const defaultTickers = [
      "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
      "NVDA", "META", "JPM", "V", "NFLX",
    ];

    for (const ticker of defaultTickers) {
      await expect(page.getByText(ticker, { exact: true }).first()).toBeVisible({ timeout: 15_000 });
    }
  });

  test("shows starting cash balance in header", async ({ page }) => {
    // Header has "Cash" label followed by a formatted dollar amount
    // Use .first() since both Portfolio and Cash may show the same initial value
    const cashLabel = page.getByText("Cash");
    await expect(cashLabel).toBeVisible({ timeout: 10_000 });

    // Verify there's a dollar amount visible near "Cash"
    const headerCash = page.locator("header").getByText(/\$[\d,]+\.\d{2}/).last();
    await expect(headerCash).toBeVisible({ timeout: 10_000 });
  });

  test("prices update via SSE", async ({ page }) => {
    // Wait for connected status first
    await expect(page.getByText("connected")).toBeVisible({ timeout: 15_000 });

    // Then wait for at least one price to appear (not "--")
    // Prices appear as formatted numbers in td elements
    await page.waitForFunction(
      () => {
        const cells = document.querySelectorAll("td");
        return Array.from(cells).some((td) =>
          /^\d{1,4}\.\d{2}$/.test(td.textContent?.trim() ?? "")
        );
      },
      { timeout: 20_000 }
    );
  });

  test("connection status shows connected", async ({ page }) => {
    await expect(page.getByText("connected")).toBeVisible({ timeout: 15_000 });
  });
});
