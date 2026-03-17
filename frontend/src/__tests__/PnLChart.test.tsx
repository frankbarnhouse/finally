import { render, screen } from "@/test-utils";
import { PnLChart } from "@/components/PnLChart";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "@/lib/api";

vi.mock("@/lib/api");
vi.mock("@/hooks/useLightweightChart", () => ({
  useLightweightChart: () => ({
    chartRef: { current: null },
    seriesRef: { current: { setData: vi.fn() } },
  }),
}));

const mockFetchPortfolioHistory = vi.mocked(api.fetchPortfolioHistory);

describe("PnLChart", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders 'No history yet' when data is empty", async () => {
    mockFetchPortfolioHistory.mockResolvedValue([]);
    render(<PnLChart />);
    expect(await screen.findByText("No history yet")).toBeInTheDocument();
  });

  it("renders chart container when history data is available", async () => {
    mockFetchPortfolioHistory.mockResolvedValue([
      { total_value: 10000, recorded_at: "2026-03-17T10:00:00Z" },
      { total_value: 10200, recorded_at: "2026-03-17T10:30:00Z" },
    ]);
    const { container } = render(<PnLChart />);
    // Wait for the data to load
    await screen.findByTestId("pnl-chart-container");
    const chartDiv = container.querySelector("[data-testid='pnl-chart-container']");
    expect(chartDiv).toBeInTheDocument();
  });
});
