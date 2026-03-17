"use client";

import { useEffect } from "react";
import { usePortfolioStore } from "@/stores/portfolioStore";
import { usePriceStore } from "@/stores/priceStore";
import { ConnectionDot } from "./ConnectionDot";

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(value);
}

export function Header() {
  const totalValue = usePortfolioStore((s) => s.totalValue);
  const cashBalance = usePortfolioStore((s) => s.cashBalance);
  const fetchPortfolio = usePortfolioStore((s) => s.fetchPortfolio);
  // Subscribe to price changes to trigger re-render for portfolio context
  const _prices = usePriceStore((s) => s.prices);
  void _prices;

  useEffect(() => {
    fetchPortfolio();
  }, [fetchPortfolio]);

  return (
    <header className="flex items-center justify-between px-4 py-2 bg-terminal-surface border-b border-terminal-border">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-bold text-accent-yellow tracking-wide">
          FinAlly
        </h1>
      </div>
      <div className="flex items-center gap-6 text-sm">
        <div>
          <span className="text-terminal-muted mr-1">Portfolio:</span>
          <span className="font-semibold">{formatCurrency(totalValue)}</span>
        </div>
        <div>
          <span className="text-terminal-muted mr-1">Cash:</span>
          <span className="font-semibold">{formatCurrency(cashBalance)}</span>
        </div>
        <ConnectionDot />
      </div>
    </header>
  );
}
