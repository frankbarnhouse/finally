export interface PriceUpdate {
  ticker: string;
  price: number;
  previous_price: number;
  timestamp: number;
  change: number;
  change_percent: number;
  direction: "up" | "down" | "flat";
}

export interface Position {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  unrealized_pnl: number;
}

export interface Portfolio {
  positions: Position[];
  cash_balance: number;
  total_value: number;
}

export interface TradeRequest {
  ticker: string;
  quantity: number;
  side: "buy" | "sell";
}

export interface TradeResult {
  trade: {
    ticker: string;
    side: "buy" | "sell";
    quantity: number;
    price: number;
    executed_at: string;
  };
  cash_balance: number;
  position: { ticker: string; quantity: number; avg_cost: number } | null;
}

export interface ChatResponse {
  message: string;
  actions: {
    trades: Array<{
      ticker: string;
      side: string;
      quantity: number;
      price: number;
      executed_at: string;
    }>;
    watchlist_changes: Array<{
      ticker: string;
      action: "add" | "remove";
    }>;
  };
}

export interface WatchlistItem {
  ticker: string;
  price: number | null;
}
