import { render, screen, fireEvent } from "@/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { Watchlist } from "@/components/Watchlist";

// Mock watchlist store
const mockFetchWatchlist = vi.fn();
const mockAddTicker = vi.fn();
const mockRemoveTicker = vi.fn();

vi.mock("@/stores/watchlistStore", () => ({
  useWatchlistStore: vi.fn((selector) => {
    const state = {
      tickers: [
        { ticker: "AAPL", price: 190.5 },
        { ticker: "GOOGL", price: 175.25 },
      ],
      loading: false,
      fetchWatchlist: mockFetchWatchlist,
      addTicker: mockAddTicker,
      removeTicker: mockRemoveTicker,
    };
    return selector ? selector(state) : state;
  }),
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
        GOOGL: {
          ticker: "GOOGL",
          price: 174.0,
          previous_price: 175.25,
          timestamp: 1000,
          change: -1.25,
          change_percent: -0.71,
          direction: "down" as const,
        },
      },
      priceHistory: {
        AAPL: [
          { time: 900, value: 190.0 },
          { time: 1000, value: 191.0 },
        ],
        GOOGL: [
          { time: 900, value: 176.0 },
          { time: 1000, value: 174.0 },
        ],
      },
    };
    return selector ? selector(state) : state;
  }),
}));

// Mock lightweight charts (canvas-based, won't work in jsdom)
vi.mock("lightweight-charts", () => ({
  createChart: vi.fn(),
}));

describe("Watchlist", () => {
  const onSelectTicker = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders watchlist rows for each ticker from watchlistStore", () => {
    render(
      <Watchlist onSelectTicker={onSelectTicker} selectedTicker={null} />,
    );
    expect(screen.getByText("AAPL")).toBeInTheDocument();
    expect(screen.getByText("GOOGL")).toBeInTheDocument();
  });

  it("applies price-flash CSS class based on direction", () => {
    render(
      <Watchlist onSelectTicker={onSelectTicker} selectedTicker={null} />,
    );
    // AAPL has direction 'up', GOOGL has direction 'down'
    const aaplPrice = screen.getByText("191.00");
    const googlPrice = screen.getByText("174.00");

    expect(aaplPrice.closest("[class*='price-flash']")).toBeTruthy();
    expect(googlPrice.closest("[class*='price-flash']")).toBeTruthy();
  });

  it("calls onSelectTicker when a row is clicked", () => {
    render(
      <Watchlist onSelectTicker={onSelectTicker} selectedTicker={null} />,
    );
    fireEvent.click(screen.getByText("AAPL"));
    expect(onSelectTicker).toHaveBeenCalledWith("AAPL");
  });
});
