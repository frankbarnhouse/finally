import { test, expect } from "@playwright/test";

const BASE = "http://localhost:8000";

test.describe("FinAlly E2E", () => {
  test("health check returns ok", async ({ request }) => {
    const res = await request.get(`${BASE}/api/health`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.status).toBe("ok");
  });

  test("default watchlist has 10 tickers", async ({ request }) => {
    const res = await request.get(`${BASE}/api/watchlist`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toHaveLength(10);
    const tickers = body.map((item: { ticker: string }) => item.ticker);
    expect(tickers).toContain("AAPL");
  });

  test("prices are streaming via SSE", async ({ page }) => {
    const event = await page.evaluate((url) => {
      return new Promise<{ ticker: string; price: number }>((resolve, reject) => {
        const timeout = setTimeout(() => {
          es.close();
          reject(new Error("No SSE event received within 10 seconds"));
        }, 10_000);

        const es = new EventSource(`${url}/api/stream/prices`);
        es.onmessage = (e) => {
          clearTimeout(timeout);
          es.close();
          resolve(JSON.parse(e.data));
        };
        es.onerror = () => {
          clearTimeout(timeout);
          es.close();
          reject(new Error("SSE connection error"));
        };
      });
    }, BASE);

    expect(event).toHaveProperty("ticker");
    expect(event).toHaveProperty("price");
  });

  test("can add and remove ticker from watchlist", async ({ request }) => {
    // Add PYPL
    const addRes = await request.post(`${BASE}/api/watchlist`, {
      data: { ticker: "PYPL" },
    });
    expect(addRes.status()).toBe(200);

    // Verify PYPL is in the watchlist
    const listRes = await request.get(`${BASE}/api/watchlist`);
    const list = await listRes.json();
    const tickers = list.map((item: { ticker: string }) => item.ticker);
    expect(tickers).toContain("PYPL");

    // Remove PYPL
    const delRes = await request.delete(`${BASE}/api/watchlist/PYPL`);
    expect(delRes.status()).toBe(200);

    // Verify PYPL is gone
    const listRes2 = await request.get(`${BASE}/api/watchlist`);
    const list2 = await listRes2.json();
    const tickers2 = list2.map((item: { ticker: string }) => item.ticker);
    expect(tickers2).not.toContain("PYPL");
  });

  test("can buy shares and see position", async ({ request }) => {
    const buyRes = await request.post(`${BASE}/api/portfolio/trade`, {
      data: { ticker: "AAPL", quantity: 5, side: "buy" },
    });
    expect(buyRes.status()).toBe(200);
    const buyBody = await buyRes.json();
    expect(buyBody.trade.ticker).toBe("AAPL");
    expect(buyBody.cash_balance).toBeLessThan(10_000);
    expect(buyBody.position.quantity).toBe(5);

    // Verify position appears in portfolio
    const portRes = await request.get(`${BASE}/api/portfolio`);
    const portfolio = await portRes.json();
    const aaplPos = portfolio.positions.find(
      (p: { ticker: string }) => p.ticker === "AAPL"
    );
    expect(aaplPos).toBeTruthy();
  });

  test("can sell shares", async ({ request }) => {
    // Buy 10 shares first
    await request.post(`${BASE}/api/portfolio/trade`, {
      data: { ticker: "MSFT", quantity: 10, side: "buy" },
    });

    // Sell 5
    const sell1 = await request.post(`${BASE}/api/portfolio/trade`, {
      data: { ticker: "MSFT", quantity: 5, side: "sell" },
    });
    expect(sell1.status()).toBe(200);
    const sell1Body = await sell1.json();
    expect(sell1Body.position.quantity).toBe(5);

    // Sell remaining 5 to close position
    const sell2 = await request.post(`${BASE}/api/portfolio/trade`, {
      data: { ticker: "MSFT", quantity: 5, side: "sell" },
    });
    expect(sell2.status()).toBe(200);
    const sell2Body = await sell2.json();
    expect(sell2Body.position).toBeNull();
  });

  test("chat returns AI response with mock", async ({ request }) => {
    const res = await request.post(`${BASE}/api/chat`, {
      data: { message: "Tell me about my portfolio" },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(typeof body.message).toBe("string");
    expect(body.message.length).toBeGreaterThan(0);
    expect(body).toHaveProperty("actions");
  });

  test("page loads with trading terminal UI", async ({ page }) => {
    await page.goto(BASE);
    // Wait for the page to show key content within 15 seconds
    await expect(
      page.getByText("AAPL").first()
    ).toBeVisible({ timeout: 15_000 });
  });
});
