import { render, screen } from "@/test-utils";
import { PortfolioHeatmap } from "@/components/PortfolioHeatmap";
import { usePortfolioStore } from "@/stores/portfolioStore";
import { usePriceStore } from "@/stores/priceStore";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/stores/portfolioStore");
vi.mock("@/stores/priceStore");

const mockUsePortfolioStore = vi.mocked(usePortfolioStore);
const mockUsePriceStore = vi.mocked(usePriceStore);

describe("PortfolioHeatmap", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUsePriceStore.mockReturnValue({});
  });

  it("renders 'No positions yet' when positions array is empty", () => {
    mockUsePortfolioStore.mockReturnValue([]);
    render(<PortfolioHeatmap />);
    expect(screen.getByText("No positions yet")).toBeInTheDocument();
  });

  it("renders SVG rect elements when positions exist", () => {
    const positions = [
      { ticker: "AAPL", quantity: 10, avg_cost: 150, current_price: 190, unrealized_pnl: 400 },
      { ticker: "GOOGL", quantity: 5, avg_cost: 160, current_price: 140, unrealized_pnl: -100 },
    ];
    mockUsePortfolioStore.mockReturnValue(positions);
    mockUsePriceStore.mockReturnValue({
      AAPL: { price: 190 },
      GOOGL: { price: 140 },
    });

    const { container } = render(<PortfolioHeatmap />);
    const rects = container.querySelectorAll("rect");
    expect(rects.length).toBeGreaterThanOrEqual(2);
  });

  it("colors green for positive P&L and red for negative P&L", () => {
    const positions = [
      { ticker: "AAPL", quantity: 10, avg_cost: 150, current_price: 190, unrealized_pnl: 400 },
      { ticker: "GOOGL", quantity: 5, avg_cost: 160, current_price: 140, unrealized_pnl: -100 },
    ];
    mockUsePortfolioStore.mockReturnValue(positions);
    mockUsePriceStore.mockReturnValue({
      AAPL: { price: 190 },
      GOOGL: { price: 140 },
    });

    const { container } = render(<PortfolioHeatmap />);
    const rects = container.querySelectorAll("rect");

    const fills = Array.from(rects).map((r) => r.getAttribute("fill"));
    // At least one greenish and one reddish fill
    const hasGreen = fills.some((f) => f && f.includes("39, 174, 96"));
    const hasRed = fills.some((f) => f && f.includes("231, 76, 60"));
    expect(hasGreen).toBe(true);
    expect(hasRed).toBe(true);
  });
});
