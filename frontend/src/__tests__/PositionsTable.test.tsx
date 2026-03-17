import { render, screen } from "@/test-utils";
import { PositionsTable } from "@/components/PositionsTable";
import { usePortfolioStore } from "@/stores/portfolioStore";
import { usePriceStore } from "@/stores/priceStore";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/stores/portfolioStore");
vi.mock("@/stores/priceStore");

const mockUsePortfolioStore = vi.mocked(usePortfolioStore);
const mockUsePriceStore = vi.mocked(usePriceStore);

describe("PositionsTable", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUsePriceStore.mockReturnValue({});
  });

  it("renders 'No positions' message when positions array is empty", () => {
    mockUsePortfolioStore.mockReturnValue([]);
    render(<PositionsTable />);
    expect(screen.getByText(/No positions/)).toBeInTheDocument();
  });

  it("renders table rows with correct columns for each position", () => {
    const positions = [
      { ticker: "AAPL", quantity: 10, avg_cost: 150, current_price: 190, unrealized_pnl: 400 },
      { ticker: "GOOGL", quantity: 5, avg_cost: 160, current_price: 140, unrealized_pnl: -100 },
    ];
    mockUsePortfolioStore.mockReturnValue(positions);
    mockUsePriceStore.mockReturnValue({
      AAPL: { price: 190 },
      GOOGL: { price: 140 },
    });

    render(<PositionsTable />);
    expect(screen.getByText("AAPL")).toBeInTheDocument();
    expect(screen.getByText("GOOGL")).toBeInTheDocument();
    expect(screen.getByText("Ticker")).toBeInTheDocument();
    expect(screen.getByText("Qty")).toBeInTheDocument();
    expect(screen.getByText("Avg Cost")).toBeInTheDocument();
    expect(screen.getByText("Current Price")).toBeInTheDocument();
  });

  it("P&L values have correct color classes", () => {
    const positions = [
      { ticker: "AAPL", quantity: 10, avg_cost: 150, current_price: 190, unrealized_pnl: 400 },
      { ticker: "GOOGL", quantity: 5, avg_cost: 160, current_price: 140, unrealized_pnl: -100 },
    ];
    mockUsePortfolioStore.mockReturnValue(positions);
    mockUsePriceStore.mockReturnValue({
      AAPL: { price: 190 },
      GOOGL: { price: 140 },
    });

    const { container } = render(<PositionsTable />);
    const profitElements = container.querySelectorAll(".text-profit");
    const lossElements = container.querySelectorAll(".text-loss");
    expect(profitElements.length).toBeGreaterThan(0);
    expect(lossElements.length).toBeGreaterThan(0);
  });

  it("calculates and displays P&L percentage", () => {
    const positions = [
      { ticker: "AAPL", quantity: 10, avg_cost: 150, current_price: 190, unrealized_pnl: 400 },
    ];
    mockUsePortfolioStore.mockReturnValue(positions);
    mockUsePriceStore.mockReturnValue({
      AAPL: { price: 190 },
    });

    render(<PositionsTable />);
    // (10*190 - 10*150) / (10*150) * 100 = 26.67%
    expect(screen.getByText("26.67%")).toBeInTheDocument();
  });

  it("displays negative P&L percentage", () => {
    const positions = [
      { ticker: "GOOGL", quantity: 5, avg_cost: 160, current_price: 140, unrealized_pnl: -100 },
    ];
    mockUsePortfolioStore.mockReturnValue(positions);
    mockUsePriceStore.mockReturnValue({
      GOOGL: { price: 140 },
    });

    render(<PositionsTable />);
    // (5*140 - 5*160) / (5*160) * 100 = -12.50%
    expect(screen.getByText("-12.50%")).toBeInTheDocument();
  });

  it("renders current prices from price store", () => {
    const positions = [
      { ticker: "AAPL", quantity: 10, avg_cost: 150, current_price: 190, unrealized_pnl: 400 },
    ];
    mockUsePortfolioStore.mockReturnValue(positions);
    mockUsePriceStore.mockReturnValue({
      AAPL: { price: 195 },
    });

    render(<PositionsTable />);
    // Price store price (195) overrides position current_price (190)
    expect(screen.getByText("$195.00")).toBeInTheDocument();
  });
});
