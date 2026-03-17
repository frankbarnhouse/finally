"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useLightweightChart } from "@/hooks/useLightweightChart";
import { fetchPortfolioHistory } from "@/lib/api";

export function PnLChart() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { seriesRef } = useLightweightChart(containerRef);
  const [hasData, setHasData] = useState<boolean | null>(null);

  const loadData = useCallback(async () => {
    const history = await fetchPortfolioHistory();
    if (history.length === 0) {
      setHasData(false);
      return;
    }

    const sorted = [...history].sort(
      (a, b) => new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime(),
    );

    // Deduplicate: ensure strictly increasing timestamps
    const data: { time: number; value: number }[] = [];
    let lastTime = -1;
    for (const s of sorted) {
      const time = Math.floor(new Date(s.recorded_at).getTime() / 1000);
      if (time > lastTime) {
        data.push({ time, value: s.total_value });
        lastTime = time;
      }
    }

    seriesRef.current?.setData(data as Parameters<typeof seriesRef.current.setData>[0]);
    setHasData(true);
  }, [seriesRef]);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30_000);
    return () => clearInterval(interval);
  }, [loadData]);

  if (hasData === false) {
    return (
      <div className="rounded border border-terminal-border bg-terminal-surface p-4">
        <h3 className="mb-2 text-xs font-semibold tracking-wider text-terminal-muted">P&L</h3>
        <p className="text-sm text-terminal-muted">No history yet</p>
      </div>
    );
  }

  return (
    <div className="rounded border border-terminal-border bg-terminal-surface p-4">
      <h3 className="mb-2 text-xs font-semibold tracking-wider text-terminal-muted">P&L</h3>
      <div ref={containerRef} data-testid="pnl-chart-container" className="h-48 w-full" />
    </div>
  );
}
