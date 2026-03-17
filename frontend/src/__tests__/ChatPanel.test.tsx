import { render, screen } from "@/test-utils";
import { ChatPanel } from "@/components/ChatPanel";
import { useChatStore } from "@/stores/chatStore";
import { usePortfolioStore } from "@/stores/portfolioStore";
import { useWatchlistStore } from "@/stores/watchlistStore";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/stores/chatStore");
vi.mock("@/stores/portfolioStore");
vi.mock("@/stores/watchlistStore");

const mockUseChatStore = vi.mocked(useChatStore);
const mockUsePortfolioStore = vi.mocked(usePortfolioStore);
const mockUseWatchlistStore = vi.mocked(useWatchlistStore);

describe("ChatPanel", () => {
  const mockSendMessage = vi.fn();
  const mockFetchPortfolio = vi.fn();
  const mockFetchWatchlist = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockSendMessage.mockResolvedValue(undefined);
    mockUsePortfolioStore.mockReturnValue(mockFetchPortfolio);
    mockUseWatchlistStore.mockReturnValue(mockFetchWatchlist);
  });

  it("renders welcome message when no messages exist", () => {
    mockUseChatStore.mockImplementation((selector: unknown) => {
      const state = { messages: [], loading: false, sendMessage: mockSendMessage };
      return (selector as (s: typeof state) => unknown)(state);
    });
    render(<ChatPanel />);
    expect(screen.getByText(/ask me about your portfolio/i)).toBeInTheDocument();
  });

  it("renders user and assistant messages with correct alignment", () => {
    const messages = [
      { role: "user" as const, content: "Buy some AAPL" },
      { role: "assistant" as const, content: "I bought 10 shares of AAPL." },
    ];
    mockUseChatStore.mockImplementation((selector: unknown) => {
      const state = { messages, loading: false, sendMessage: mockSendMessage };
      return (selector as (s: typeof state) => unknown)(state);
    });

    render(<ChatPanel />);
    expect(screen.getByText("Buy some AAPL")).toBeInTheDocument();
    expect(screen.getByText("I bought 10 shares of AAPL.")).toBeInTheDocument();
  });

  it("renders inline action badges for trades in assistant messages", () => {
    const messages = [
      {
        role: "assistant" as const,
        content: "Done!",
        actions: {
          trades: [{ ticker: "AAPL", side: "buy", quantity: 10, price: 190.5, executed_at: "2026-03-13T14:30:00Z" }],
          watchlist_changes: [],
        },
      },
    ];
    mockUseChatStore.mockImplementation((selector: unknown) => {
      const state = { messages, loading: false, sendMessage: mockSendMessage };
      return (selector as (s: typeof state) => unknown)(state);
    });

    render(<ChatPanel />);
    expect(screen.getByText(/bought 10 AAPL/i)).toBeInTheDocument();
  });
});
