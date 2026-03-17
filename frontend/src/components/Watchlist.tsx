"use client";

import { useEffect, useState } from "react";
import { useWatchlistStore } from "@/stores/watchlistStore";
import { usePriceStore } from "@/stores/priceStore";
import type { PriceUpdate } from "@/types";

interface WatchlistProps {
  onSelectTicker: (ticker: string) => void;
  selectedTicker: string | null;
}

function Sparkline({ ticker }: { ticker: string }) {
  const history = usePriceStore((s) => s.priceHistory[ticker] || []);

  if (history.length < 2) return <div className="w-[100px] h-[30px]" />;

  const values = history.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const width = 100;
  const height = 30;

  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * width;
      const y = height - ((v - min) / range) * height;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg width={width} height={height} className="flex-shrink-0">
      <polyline
        points={points}
        fill="none"
        stroke="#209dd7"
        strokeWidth="1.5"
      />
    </svg>
  );
}

function WatchlistRow({
  ticker,
  isSelected,
  onSelect,
  onRemove,
}: {
  ticker: string;
  isSelected: boolean;
  onSelect: () => void;
  onRemove: () => void;
}) {
  const priceData = usePriceStore((s) => s.prices[ticker]) as
    | PriceUpdate
    | undefined;
  const [flashClass, setFlashClass] = useState("price-flash-none");

  useEffect(() => {
    if (!priceData) return;
    if (priceData.direction === "up") {
      setFlashClass("price-flash-up");
    } else if (priceData.direction === "down") {
      setFlashClass("price-flash-down");
    }
    const timer = setTimeout(() => setFlashClass("price-flash-none"), 500);
    return () => clearTimeout(timer);
  }, [priceData?.price, priceData?.direction]);

  const price = priceData?.price;
  const change = priceData?.change;
  const changePct = priceData?.change_percent;
  const direction = priceData?.direction;

  const changeColor =
    direction === "up"
      ? "text-profit"
      : direction === "down"
        ? "text-loss"
        : "text-terminal-muted";

  const changePrefix =
    change !== undefined && change > 0 ? "+" : "";

  return (
    <div
      className={`grid grid-cols-[60px_1fr_100px_24px] items-center gap-2 px-2 py-1.5 cursor-pointer hover:bg-terminal-bg/50 ${
        isSelected ? "border-l-2 border-accent-blue" : "border-l-2 border-transparent"
      }`}
      onClick={onSelect}
    >
      <span className="text-accent-yellow font-mono text-sm font-semibold">
        {ticker}
      </span>

      <div className="flex items-center gap-2">
        <span className={`font-mono text-sm ${flashClass}`}>
          {price !== undefined ? price.toFixed(2) : "--"}
        </span>
        <span className={`font-mono text-xs ${changeColor}`}>
          {change !== undefined
            ? `${changePrefix}${change.toFixed(2)} (${changePrefix}${changePct?.toFixed(2)}%)`
            : ""}
        </span>
      </div>

      <Sparkline ticker={ticker} />

      <button
        className="text-terminal-muted hover:text-loss text-xs"
        onClick={(e) => {
          e.stopPropagation();
          onRemove();
        }}
      >
        x
      </button>
    </div>
  );
}

export function Watchlist({ onSelectTicker, selectedTicker }: WatchlistProps) {
  const tickers = useWatchlistStore((s) => s.tickers);
  const fetchWatchlist = useWatchlistStore((s) => s.fetchWatchlist);
  const addTicker = useWatchlistStore((s) => s.addTicker);
  const removeTicker = useWatchlistStore((s) => s.removeTicker);
  const [newTicker, setNewTicker] = useState("");

  useEffect(() => {
    fetchWatchlist();
  }, [fetchWatchlist]);

  const handleAdd = () => {
    const t = newTicker.trim().toUpperCase();
    if (!t) return;
    addTicker(t);
    setNewTicker("");
  };

  return (
    <div className="bg-terminal-surface border border-terminal-border rounded flex flex-col h-full overflow-hidden">
      <div className="px-3 py-2 border-b border-terminal-border">
        <span className="text-terminal-muted text-xs font-semibold tracking-wider">
          WATCHLIST
        </span>
      </div>

      <div className="flex-1 overflow-y-auto">
        {tickers.map((item) => (
          <WatchlistRow
            key={item.ticker}
            ticker={item.ticker}
            isSelected={selectedTicker === item.ticker}
            onSelect={() => onSelectTicker(item.ticker)}
            onRemove={() => removeTicker(item.ticker)}
          />
        ))}
      </div>

      <div className="flex gap-1 p-2 border-t border-terminal-border">
        <input
          type="text"
          value={newTicker}
          onChange={(e) => setNewTicker(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAdd()}
          placeholder="Add ticker..."
          className="flex-1 bg-terminal-bg border border-terminal-border rounded px-2 py-1 text-sm text-terminal-text font-mono placeholder:text-terminal-muted"
        />
        <button
          onClick={handleAdd}
          className="bg-accent-purple text-white text-sm px-3 py-1 rounded hover:opacity-80"
        >
          Add
        </button>
      </div>
    </div>
  );
}
