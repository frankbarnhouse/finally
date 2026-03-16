import { create } from "zustand";
import {
  PriceUpdate,
  Position,
  WatchlistItem,
  ChatMessage,
  ConnectionStatus,
  PortfolioSnapshot,
} from "./types";

interface AppState {
  // Connection
  connectionStatus: ConnectionStatus;
  setConnectionStatus: (status: ConnectionStatus) => void;

  // Prices - latest price per ticker
  prices: Record<string, PriceUpdate>;
  updatePrice: (update: PriceUpdate) => void;

  // Price history for sparklines (accumulated since page load)
  priceHistory: Record<string, { price: number; timestamp: number }[]>;

  // Watchlist
  watchlist: WatchlistItem[];
  setWatchlist: (items: WatchlistItem[]) => void;
  addWatchlistItem: (ticker: string) => void;
  removeWatchlistItem: (ticker: string) => void;

  // Portfolio
  positions: Position[];
  cashBalance: number;
  totalValue: number;
  setPortfolio: (positions: Position[], cash: number, total: number) => void;

  // Portfolio history
  portfolioHistory: PortfolioSnapshot[];
  setPortfolioHistory: (snapshots: PortfolioSnapshot[]) => void;

  // Selected ticker for main chart
  selectedTicker: string | null;
  setSelectedTicker: (ticker: string | null) => void;

  // Chat
  chatMessages: ChatMessage[];
  addChatMessage: (msg: ChatMessage) => void;
  setChatMessages: (msgs: ChatMessage[]) => void;
  chatLoading: boolean;
  setChatLoading: (loading: boolean) => void;

  // Chat panel visibility
  chatOpen: boolean;
  setChatOpen: (open: boolean) => void;
}

export const useStore = create<AppState>((set) => ({
  connectionStatus: "disconnected",
  setConnectionStatus: (status) => set({ connectionStatus: status }),

  prices: {},
  priceHistory: {},
  updatePrice: (update) =>
    set((state) => ({
      prices: { ...state.prices, [update.ticker]: update },
      priceHistory: {
        ...state.priceHistory,
        [update.ticker]: [
          ...(state.priceHistory[update.ticker] || []),
          { price: update.price, timestamp: update.timestamp },
        ].slice(-120), // Keep last 120 points for sparklines
      },
    })),

  watchlist: [],
  setWatchlist: (items) => set({ watchlist: items }),
  addWatchlistItem: (ticker) =>
    set((state) => {
      if (state.watchlist.some((w) => w.ticker === ticker)) return state;
      return { watchlist: [...state.watchlist, { ticker }] };
    }),
  removeWatchlistItem: (ticker) =>
    set((state) => ({
      watchlist: state.watchlist.filter((w) => w.ticker !== ticker),
    })),

  positions: [],
  cashBalance: 10000,
  totalValue: 10000,
  setPortfolio: (positions, cash, total) =>
    set({ positions, cashBalance: cash, totalValue: total }),

  portfolioHistory: [],
  setPortfolioHistory: (snapshots) => set({ portfolioHistory: snapshots }),

  selectedTicker: null,
  setSelectedTicker: (ticker) => set({ selectedTicker: ticker }),

  chatMessages: [],
  addChatMessage: (msg) =>
    set((state) => ({ chatMessages: [...state.chatMessages, msg] })),
  setChatMessages: (msgs) => set({ chatMessages: msgs }),
  chatLoading: false,
  setChatLoading: (loading) => set({ chatLoading: loading }),

  chatOpen: false,
  setChatOpen: (open) => set({ chatOpen: open }),
}));
