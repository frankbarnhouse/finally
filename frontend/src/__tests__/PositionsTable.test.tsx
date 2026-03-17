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
});
