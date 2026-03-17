import { create } from "zustand";
import type { PriceUpdate } from "@/types";

const MAX_HISTORY = 500;

interface PriceState {
  prices: Record<string, PriceUpdate>;
  priceHistory: Record<string, { time: number; value: number }[]>;
  connectionStatus: "connected" | "connecting" | "disconnected";
  updatePrices: (data: Record<string, PriceUpdate>) => void;
  setConnectionStatus: (status: PriceState["connectionStatus"]) => void;
}

export const usePriceStore = create<PriceState>((set) => ({
  prices: {},
  priceHistory: {},
  connectionStatus: "connecting",

  updatePrices: (data) =>
    set((state) => {
      const newPrices = { ...state.prices, ...data };
      const newHistory = { ...state.priceHistory };
      for (const [ticker, update] of Object.entries(data)) {
        const existing = newHistory[ticker] || [];
        const entry = { time: update.timestamp, value: update.price };
        const updated = [...existing, entry];
        newHistory[ticker] =
          updated.length > MAX_HISTORY
            ? updated.slice(updated.length - MAX_HISTORY)
            : updated;
      }
      return { prices: newPrices, priceHistory: newHistory };
    }),

  setConnectionStatus: (status) => set({ connectionStatus: status }),
}));
