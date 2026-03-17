"use client";

import { useState } from "react";
import { usePortfolioStore } from "@/stores/portfolioStore";

export function TradeBar() {
  const executeTrade = usePortfolioStore((s) => s.executeTrade);
  const [ticker, setTicker] = useState("");
  const [quantity, setQuantity] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  async function handleTrade(side: "buy" | "sell") {
    const trimmed = ticker.trim().toUpperCase();
    const qty = Number(quantity);
    if (!trimmed || qty <= 0 || isNaN(qty)) return;

    setLoading(true);
    setError(null);
    try {
      await executeTrade({ ticker: trimmed, quantity: qty, side });
      setTicker("");
      setQuantity("");
      setSuccess(true);
      setTimeout(() => setSuccess(false), 1000);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Trade failed";
      setError(msg);
      setTimeout(() => setError(null), 3000);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className={`flex items-center gap-2 rounded border bg-terminal-surface p-2 transition-colors ${
        success ? "border-profit" : "border-terminal-border"
      }`}
    >
      <input
        type="text"
        placeholder="Ticker"
        value={ticker}
        onChange={(e) => setTicker(e.target.value.toUpperCase())}
        className="w-24 rounded bg-terminal-bg px-2 py-1 text-sm text-terminal-text placeholder-terminal-muted border border-terminal-border focus:outline-none focus:border-accent-blue"
      />
      <input
        type="number"
        placeholder="Qty"
        min={1}
        value={quantity}
        onChange={(e) => setQuantity(e.target.value)}
        className="w-20 rounded bg-terminal-bg px-2 py-1 text-sm text-terminal-text placeholder-terminal-muted border border-terminal-border focus:outline-none focus:border-accent-blue"
      />
      <button
        onClick={() => handleTrade("buy")}
        disabled={loading}
        className="rounded bg-profit px-3 py-1 text-sm font-semibold text-terminal-bg hover:opacity-90 disabled:opacity-50"
      >
        Buy
      </button>
      <button
        onClick={() => handleTrade("sell")}
        disabled={loading}
        className="rounded bg-loss px-3 py-1 text-sm font-semibold text-terminal-bg hover:opacity-90 disabled:opacity-50"
      >
        Sell
      </button>
      {error && <span className="text-xs text-loss">{error}</span>}
    </div>
  );
}
