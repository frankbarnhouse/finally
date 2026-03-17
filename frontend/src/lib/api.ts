import type {
  Portfolio,
  TradeRequest,
  TradeResult,
  WatchlistItem,
  ChatResponse,
} from "@/types";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(body.error || `Request failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchPortfolio(): Promise<Portfolio> {
  return request<Portfolio>("/api/portfolio");
}

export async function executeTrade(req: TradeRequest): Promise<TradeResult> {
  return request<TradeResult>("/api/portfolio/trade", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
}

export async function fetchPortfolioHistory(): Promise<
  { total_value: number; recorded_at: string }[]
> {
  return request("/api/portfolio/history");
}

export async function fetchWatchlist(): Promise<WatchlistItem[]> {
  return request<WatchlistItem[]>("/api/watchlist");
}

export async function addToWatchlist(ticker: string): Promise<void> {
  await request<void>("/api/watchlist", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker }),
  });
}

export async function removeFromWatchlist(ticker: string): Promise<void> {
  await request<void>(`/api/watchlist/${ticker}`, { method: "DELETE" });
}

export async function sendChatMessage(
  message: string,
): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
}
