import { create } from "zustand";
import type { WatchlistItem } from "@/types";
import {
  fetchWatchlist,
  addToWatchlist,
  removeFromWatchlist,
} from "@/lib/api";

interface WatchlistState {
  tickers: WatchlistItem[];
  loading: boolean;
  fetchWatchlist: () => Promise<void>;
  addTicker: (ticker: string) => Promise<void>;
  removeTicker: (ticker: string) => Promise<void>;
}

export const useWatchlistStore = create<WatchlistState>((set) => ({
  tickers: [],
  loading: false,

  fetchWatchlist: async () => {
    set({ loading: true });
    const data = await fetchWatchlist();
    set({ tickers: data, loading: false });
  },

  addTicker: async (ticker) => {
    await addToWatchlist(ticker);
    const data = await fetchWatchlist();
    set({ tickers: data });
  },

  removeTicker: async (ticker) => {
    await removeFromWatchlist(ticker);
    const data = await fetchWatchlist();
    set({ tickers: data });
  },
}));
