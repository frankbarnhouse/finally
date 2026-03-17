import { create } from "zustand";
import type { Position, TradeRequest } from "@/types";
import { fetchPortfolio, executeTrade } from "@/lib/api";

interface PortfolioState {
  positions: Position[];
  cashBalance: number;
  totalValue: number;
  loading: boolean;
  fetchPortfolio: () => Promise<void>;
  executeTrade: (req: TradeRequest) => Promise<void>;
}

export const usePortfolioStore = create<PortfolioState>((set) => ({
  positions: [],
  cashBalance: 0,
  totalValue: 0,
  loading: false,

  fetchPortfolio: async () => {
    set({ loading: true });
    const data = await fetchPortfolio();
    set({
      positions: data.positions,
      cashBalance: data.cash_balance,
      totalValue: data.total_value,
      loading: false,
    });
  },

  executeTrade: async (req) => {
    await executeTrade(req);
    const data = await fetchPortfolio();
    set({
      positions: data.positions,
      cashBalance: data.cash_balance,
      totalValue: data.total_value,
    });
  },
}));
