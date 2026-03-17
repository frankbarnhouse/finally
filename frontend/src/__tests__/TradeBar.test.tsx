import { render, screen, fireEvent, waitFor } from "@/test-utils";
import { TradeBar } from "@/components/TradeBar";
import { usePortfolioStore } from "@/stores/portfolioStore";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/stores/portfolioStore");

const mockUsePortfolioStore = vi.mocked(usePortfolioStore);

describe("TradeBar", () => {
  const mockExecuteTrade = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockExecuteTrade.mockResolvedValue(undefined);
    mockUsePortfolioStore.mockReturnValue(mockExecuteTrade);
  });

  it("renders ticker input, quantity input, Buy and Sell buttons", () => {
    render(<TradeBar />);
    expect(screen.getByPlaceholderText("Ticker")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Qty")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /buy/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sell/i })).toBeInTheDocument();
  });

  it("Buy button calls executeTrade with correct side", async () => {
    render(<TradeBar />);
    fireEvent.change(screen.getByPlaceholderText("Ticker"), { target: { value: "AAPL" } });
    fireEvent.change(screen.getByPlaceholderText("Qty"), { target: { value: "10" } });
    fireEvent.click(screen.getByRole("button", { name: /buy/i }));

    await waitFor(() => {
      expect(mockExecuteTrade).toHaveBeenCalledWith({
        ticker: "AAPL",
        quantity: 10,
        side: "buy",
      });
    });
  });
});
