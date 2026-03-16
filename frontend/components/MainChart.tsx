"use client";

import { useEffect, useRef } from "react";
import { createChart, IChartApi, ISeriesApi, LineSeries } from "lightweight-charts";
import { useStore } from "@/lib/store";

export function MainChart() {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const selectedTicker = useStore((s) => s.selectedTicker);
  const priceHistory = useStore((s) => s.priceHistory);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: "#161b22" },
        textColor: "#8b949e",
      },
      grid: {
        vertLines: { color: "#30363d" },
        horzLines: { color: "#30363d" },
      },
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
      timeScale: {
        timeVisible: true,
        secondsVisible: true,
      },
    });

    const series = chart.addSeries(LineSeries, {
      color: "#209dd7",
      lineWidth: 2,
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const observer = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      chart.applyOptions({ width, height });
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!seriesRef.current || !selectedTicker) return;

    const history = priceHistory[selectedTicker] || [];
    const data = history.map((p) => ({
      time: Math.floor(new Date(p.timestamp).getTime() / 1000) as import("lightweight-charts").UTCTimestamp,
      value: p.price,
    }));

    seriesRef.current.setData(data);
    chartRef.current?.timeScale().fitContent();
  }, [selectedTicker, priceHistory]);

  return (
    <div className="h-full flex flex-col">
      <div className="px-3 py-2 border-b border-border text-xs flex items-center gap-2">
        <span className="text-text-secondary">Chart:</span>
        <span className="text-accent-yellow font-bold">
          {selectedTicker || "Select a ticker"}
        </span>
      </div>
      <div ref={containerRef} className="flex-1" />
    </div>
  );
}
