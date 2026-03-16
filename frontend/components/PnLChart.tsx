"use client";

import { useEffect, useRef } from "react";
import { createChart, IChartApi, ISeriesApi, AreaSeries } from "lightweight-charts";
import { useStore } from "@/lib/store";
import { getPortfolioHistory } from "@/lib/api";

export function PnLChart() {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);
  const portfolioHistory = useStore((s) => s.portfolioHistory);
  const setPortfolioHistory = useStore((s) => s.setPortfolioHistory);

  useEffect(() => {
    getPortfolioHistory()
      .then(setPortfolioHistory)
      .catch(() => {});

    const interval = setInterval(() => {
      getPortfolioHistory()
        .then(setPortfolioHistory)
        .catch(() => {});
    }, 30000);

    return () => clearInterval(interval);
  }, [setPortfolioHistory]);

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
        secondsVisible: false,
      },
    });

    const series = chart.addSeries(AreaSeries, {
      lineColor: "#ecad0a",
      topColor: "rgba(236, 173, 10, 0.3)",
      bottomColor: "rgba(236, 173, 10, 0.0)",
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
    if (!seriesRef.current) return;

    const data = portfolioHistory.map((s) => ({
      time: Math.floor(new Date(s.recorded_at).getTime() / 1000) as import("lightweight-charts").UTCTimestamp,
      value: s.total_value,
    }));

    seriesRef.current.setData(data);
    chartRef.current?.timeScale().fitContent();
  }, [portfolioHistory]);

  return (
    <div className="h-full flex flex-col">
      <div className="px-3 py-2 border-b border-border text-xs text-text-secondary">
        Portfolio Value
      </div>
      <div ref={containerRef} className="flex-1" />
    </div>
  );
}
