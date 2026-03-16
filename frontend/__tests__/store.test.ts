import { describe, it, expect, beforeEach } from "vitest";
import { useStore } from "@/lib/store";

describe("store", () => {
  beforeEach(() => {
    useStore.setState({
      prices: {},
      priceHistory: {},
      watchlist: [],
      positions: [],
      cashBalance: 10000,
      totalValue: 10000,
      connectionStatus: "disconnected",
      selectedTicker: null,
      chatMessages: [],
      chatLoading: false,
      chatOpen: false,
      portfolioHistory: [],
    });
  });

  it("updates price and adds to history", () => {
    useStore.getState().updatePrice({
      ticker: "AAPL",
      price: 190.5,
      previous_price: 190.0,
      timestamp: "2026-01-01T00:00:00Z",
      direction: "up",
    });

    const state = useStore.getState();
    expect(state.prices["AAPL"].price).toBe(190.5);
    expect(state.priceHistory["AAPL"]).toHaveLength(1);
    expect(state.priceHistory["AAPL"][0].price).toBe(190.5);
  });

  it("limits price history to 120 entries", () => {
    for (let i = 0; i < 130; i++) {
      useStore.getState().updatePrice({
        ticker: "AAPL",
        price: 190 + i * 0.1,
        previous_price: 190 + (i - 1) * 0.1,
        timestamp: `2026-01-01T00:0${i}:00Z`,
        direction: "up",
      });
    }
    expect(useStore.getState().priceHistory["AAPL"]).toHaveLength(120);
  });

  it("sets portfolio data", () => {
    useStore
      .getState()
      .setPortfolio(
        [{ ticker: "AAPL", quantity: 10, avg_cost: 190 }],
        8100,
        10000
      );

    const state = useStore.getState();
    expect(state.positions).toHaveLength(1);
    expect(state.cashBalance).toBe(8100);
    expect(state.totalValue).toBe(10000);
  });

  it("manages watchlist items", () => {
    useStore.getState().addWatchlistItem("AAPL");
    expect(useStore.getState().watchlist).toHaveLength(1);

    // No duplicates
    useStore.getState().addWatchlistItem("AAPL");
    expect(useStore.getState().watchlist).toHaveLength(1);

    useStore.getState().removeWatchlistItem("AAPL");
    expect(useStore.getState().watchlist).toHaveLength(0);
  });

  it("manages connection status", () => {
    useStore.getState().setConnectionStatus("connected");
    expect(useStore.getState().connectionStatus).toBe("connected");
  });

  it("manages selected ticker", () => {
    useStore.getState().setSelectedTicker("AAPL");
    expect(useStore.getState().selectedTicker).toBe("AAPL");
  });
});
