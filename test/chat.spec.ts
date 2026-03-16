import { test, expect } from "@playwright/test";

test.describe("AI Chat (mocked)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("FinAlly").first()).toBeVisible({ timeout: 15_000 });
  });

  test("send a message and receive a mock response", async ({ page }) => {
    // Open chat panel
    await page.getByRole("button", { name: /AI Chat/i }).click();
    await expect(page.getByText("AI Trading Assistant")).toBeVisible({ timeout: 5_000 });

    // Send a generic message
    const chatInput = page.getByPlaceholder("Ask the AI...");
    await chatInput.fill("Hello, what can you do?");
    await page.getByRole("button", { name: "Send" }).click();

    // Mock returns: "I can help you trade, analyze your portfolio..."
    // The mock response is fast, so "Thinking..." may flash too quickly to catch.
    // Just wait for the actual response text.
    await expect(
      page.getByText("I can help you trade", { exact: false })
    ).toBeVisible({ timeout: 10_000 });
  });

  test("trade action renders inline in chat", async ({ page }) => {
    // Open chat
    await page.getByRole("button", { name: /AI Chat/i }).click();
    await expect(page.getByText("AI Trading Assistant")).toBeVisible({ timeout: 5_000 });

    // Use "add to watchlist" which doesn't require cash
    const chatInput = page.getByPlaceholder("Ask the AI...");
    await chatInput.fill("Add PYPL to the watchlist");
    await page.getByRole("button", { name: "Send" }).click();

    // Mock response: "Adding PYPL to your watchlist." + watchlist action
    await expect(
      page.getByText("Adding PYPL to your watchlist", { exact: false })
    ).toBeVisible({ timeout: 10_000 });

    // Watchlist change action should render as "Watchlist: add PYPL"
    await expect(
      page.getByText("Watchlist: add PYPL")
    ).toBeVisible({ timeout: 5_000 });
  });

  test("chat API returns valid structured response in mock mode", async ({ page }) => {
    const response = await page.request.post("/api/chat", {
      data: { message: "What is my portfolio worth?" },
    });
    expect(response.ok()).toBe(true);
    const body = await response.json();
    expect(body.message).toBeTruthy();
    expect(typeof body.message).toBe("string");
  });
});
