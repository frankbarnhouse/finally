"use client";

import { usePortfolioStore } from "@/stores/portfolioStore";
import { usePriceStore } from "@/stores/priceStore";
import type { Position } from "@/types";

function formatCurrency(value: number): string {
  return `$${value.toFixed(2)}`;
}

function formatPercent(value: number): string {
  return `${value.toFixed(2)}%`;
}

export function PositionsTable() {
  const positions = usePortfolioStore((s) => s.positions);
  const livePrices = usePriceStore((s) => s.prices);

  if (!positions || positions.length === 0) {
    return (
      <div className="rounded border border-terminal-border bg-terminal-surface p-4">
        <h3 className="mb-2 text-xs font-semibold tracking-wider text-terminal-muted">POSITIONS</h3>
        <p className="text-sm text-terminal-muted">
          No positions — use the trade bar to buy shares
        </p>
      </div>
    );
  }

  return (
    <div className="rounded border border-terminal-border bg-terminal-surface p-4">
      <h3 className="mb-2 text-xs font-semibold tracking-wider text-terminal-muted">POSITIONS</h3>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-terminal-muted text-left">
            <th className="pb-2 font-medium">Ticker</th>
            <th className="pb-2 font-medium text-right">Qty</th>
            <th className="pb-2 font-medium text-right">Avg Cost</th>
            <th className="pb-2 font-medium text-right">Current Price</th>
            <th className="pb-2 font-medium text-right">P&L</th>
            <th className="pb-2 font-medium text-right">% Change</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((p: Position) => {
            const currentPrice = livePrices[p.ticker]?.price ?? p.current_price;
            const costBasis = p.quantity * p.avg_cost;
            const unrealizedPnl = p.quantity * currentPrice - costBasis;
            const pctChange = costBasis > 0 ? (unrealizedPnl / costBasis) * 100 : 0;
            const colorClass = unrealizedPnl > 0 ? "text-profit" : unrealizedPnl < 0 ? "text-loss" : "";

            return (
              <tr key={p.ticker} className="border-t border-terminal-border hover:bg-terminal-bg">
                <td className="py-1.5 font-medium text-terminal-text">{p.ticker}</td>
                <td className="py-1.5 text-right text-terminal-text">{p.quantity}</td>
                <td className="py-1.5 text-right text-terminal-text">{formatCurrency(p.avg_cost)}</td>
                <td className="py-1.5 text-right text-terminal-text">{formatCurrency(currentPrice)}</td>
                <td className={`py-1.5 text-right ${colorClass}`}>{formatCurrency(unrealizedPnl)}</td>
                <td className={`py-1.5 text-right ${colorClass}`}>{formatPercent(pctChange)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
