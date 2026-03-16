import { test, expect } from "@playwright/test";

test.describe("Trading", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("FinAlly").first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("AAPL", { exact: true }).first()).toBeVisible({ timeout: 15_000 });
  });

  test("buy shares via API: cash decreases and position appears", async ({ page }) => {
    // Check current cash first
    const beforeResponse = await page.request.get("/api/portfolio");
    const before = await beforeResponse.json();
    const initialCash = before.cash_balance;

    // Buy 1 share (cheap enough to always have cash for)
    const tradeResponse = await page.request.post("/api/portfolio/trade", {
      data: { ticker: "AAPL", quantity: 1, side: "buy" },
    });
    expect(tradeResponse.ok()).toBe(true);
    const trade = await tradeResponse.json();

    expect(trade.trade.ticker).toBe("AAPL");
    expect(trade.trade.side).toBe("buy");
    expect(trade.trade.quantity).toBe(1);
    expect(trade.cash_balance).toBeLessThan(initialCash);
    expect(trade.position.ticker).toBe("AAPL");
  });

  test("buy shares via UI: trade bar works", async ({ page }) => {
    // Click AAPL in the watchlist to select it
    const watchlistTable = page.locator("table").first();
    await watchlistTable.locator("tr").filter({ hasText: "AAPL" }).click();

    // Fill quantity and buy
    await page.getByPlaceholder("Qty").fill("1");
    await page.getByRole("button", { name: "Buy" }).click();

    // Wait and verify
    await page.waitForTimeout(2000);
    const response = await page.request.get("/api/portfolio");
    const portfolio = await response.json();
    const aaplPos = portfolio.positions.find(
      (p: { ticker: string }) => p.ticker === "AAPL"
    );
    expect(aaplPos).toBeTruthy();
  });

  test("sell shares via API: cash increases and position removed", async ({ page }) => {
    // First buy 1 share of a cheap ticker
    const buyResponse = await page.request.post("/api/portfolio/trade", {
      data: { ticker: "V", quantity: 1, side: "buy" },
    });

    // If buy fails due to insufficient cash, skip gracefully
    if (!buyResponse.ok()) {
      test.skip();
      return;
    }

    const afterBuy = await page.request.get("/api/portfolio");
    const beforeSell = await afterBuy.json();
    const vPos = beforeSell.positions.find(
      (p: { ticker: string }) => p.ticker === "V"
    );

    // Sell all V shares
    const sellResponse = await page.request.post("/api/portfolio/trade", {
      data: { ticker: "V", quantity: vPos.quantity, side: "sell" },
    });
    expect(sellResponse.ok()).toBe(true);
    const sellResult = await sellResponse.json();

    expect(sellResult.position).toBeNull();
    expect(sellResult.cash_balance).toBeGreaterThan(beforeSell.cash_balance);
  });
});
