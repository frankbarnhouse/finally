"use client";

import { useStore } from "@/lib/store";
import { formatCurrency, formatPercent } from "@/lib/format";

export function Heatmap() {
  const positions = useStore((s) => s.positions);
  const prices = useStore((s) => s.prices);

  if (positions.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-text-secondary text-xs">
        No positions yet
      </div>
    );
  }

  const enriched = positions.map((pos) => {
    const currentPrice = prices[pos.ticker]?.price ?? pos.current_price ?? pos.avg_cost;
    const value = currentPrice * pos.quantity;
    const pnl = (currentPrice - pos.avg_cost) * pos.quantity;
    const pnlPct = ((currentPrice - pos.avg_cost) / pos.avg_cost) * 100;
    return { ...pos, currentPrice, value, pnl, pnlPct };
  });

  const totalValue = enriched.reduce((sum, p) => sum + p.value, 0);

  return (
    <div className="h-full flex flex-wrap gap-1 p-2 content-start">
      {enriched.map((pos) => {
        const weight = totalValue > 0 ? pos.value / totalValue : 0;
        const bgColor =
          pos.pnl > 0
            ? `rgba(46, 160, 67, ${Math.min(0.6, Math.abs(pos.pnlPct) / 10)})`
            : pos.pnl < 0
            ? `rgba(218, 54, 51, ${Math.min(0.6, Math.abs(pos.pnlPct) / 10)})`
            : "rgba(48, 54, 61, 0.5)";

        return (
          <div
            key={pos.ticker}
            className="flex flex-col items-center justify-center rounded text-xs border border-border/50"
            style={{
              backgroundColor: bgColor,
              flexBasis: `${Math.max(weight * 100, 15)}%`,
              flexGrow: weight > 0.1 ? 1 : 0,
              minHeight: "60px",
            }}
          >
            <span className="font-bold text-accent-yellow">{pos.ticker}</span>
            <span className="text-text-primary">{formatCurrency(pos.value)}</span>
            <span
              className={
                pos.pnl > 0 ? "text-green" : pos.pnl < 0 ? "text-red" : "text-text-secondary"
              }
            >
              {formatPercent(pos.pnlPct)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
