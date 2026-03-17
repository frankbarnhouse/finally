"use client";

import { useEffect, useRef } from "react";
import { usePriceStore } from "@/stores/priceStore";
import { useLightweightChart } from "@/hooks/useLightweightChart";
import type { ISeriesApi, Time } from "lightweight-charts";

interface MainChartProps {
  ticker: string | null;
}

function ChartView({ ticker }: { ticker: string }) {
  const history = usePriceStore((s) => s.priceHistory[ticker] || []);
  const priceData = usePriceStore((s) => s.prices[ticker]);
  const containerRef = useRef<HTMLDivElement>(null);
  const { chartRef } = useLightweightChart(containerRef);
  const areaSeriesRef = useRef<ISeriesApi<"Area"> | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;
    if (!areaSeriesRef.current) {
      areaSeriesRef.current = chartRef.current.addAreaSeries({
        topColor: "rgba(32, 157, 215, 0.4)",
        bottomColor: "rgba(32, 157, 215, 0.0)",
        lineColor: "#209dd7",
        lineWidth: 2,
      });
    }
    if (history.length > 0) {
      areaSeriesRef.current.setData(
        history.map((p) => ({ time: p.time as Time, value: p.value })),
      );
      chartRef.current.timeScale().fitContent();
    }
  }, [chartRef, history, history.length]);

  const changeColor =
    priceData?.direction === "up"
      ? "text-profit"
      : priceData?.direction === "down"
        ? "text-loss"
        : "text-terminal-muted";

  const changePrefix =
    priceData?.change !== undefined && priceData.change > 0 ? "+" : "";

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-baseline gap-3 px-3 py-2">
        <span className="text-accent-yellow font-mono text-lg font-semibold">
          {ticker}
        </span>
        {priceData && (
          <>
            <span className="text-terminal-text font-mono text-lg">
              {priceData.price.toFixed(2)}
            </span>
            <span className={`font-mono text-sm ${changeColor}`}>
              {changePrefix}
              {priceData.change.toFixed(2)} ({changePrefix}
              {priceData.change_percent.toFixed(2)}%)
            </span>
          </>
        )}
      </div>
      <div
        ref={containerRef}
        data-testid="main-chart-container"
        className="flex-1 min-h-0"
      />
    </div>
  );
}

export function MainChart({ ticker }: MainChartProps) {
  if (!ticker) {
    return (
      <div className="bg-terminal-surface border border-terminal-border rounded flex items-center justify-center h-full">
        <span className="text-terminal-muted text-sm">
          Select a ticker from the watchlist
        </span>
      </div>
    );
  }

  return (
    <div className="bg-terminal-surface border border-terminal-border rounded h-full overflow-hidden">
      <ChartView ticker={ticker} />
    </div>
  );
}
