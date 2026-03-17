import { render, screen } from "@/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MainChart } from "@/components/MainChart";

// Mock lightweight charts hook
vi.mock("@/hooks/useLightweightChart", () => ({
  useLightweightChart: vi.fn(() => ({
    chartRef: { current: null },
    seriesRef: { current: null },
  })),
}));

// Mock price store
vi.mock("@/stores/priceStore", () => ({
  usePriceStore: vi.fn((selector) => {
    const state = {
      prices: {
        AAPL: {
          ticker: "AAPL",
          price: 191.0,
          previous_price: 190.5,
          timestamp: 1000,
          change: 0.5,
          change_percent: 0.26,
          direction: "up" as const,
        },
      },
      priceHistory: {
        AAPL: [
          { time: 900, value: 190.0 },
          { time: 1000, value: 191.0 },
        ],
      },
    };
    return selector ? selector(state) : state;
  }),
}));

describe("MainChart", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders placeholder message when no ticker selected", () => {
    render(<MainChart ticker={null} />);
    expect(
      screen.getByText("Select a ticker from the watchlist"),
    ).toBeInTheDocument();
  });

  it("renders chart container when ticker is provided", () => {
    render(<MainChart ticker="AAPL" />);
    expect(screen.getByText("AAPL")).toBeInTheDocument();
    expect(screen.getByText("191.00")).toBeInTheDocument();
    // Chart container should exist
    expect(screen.getByTestId("main-chart-container")).toBeInTheDocument();
  });
});
