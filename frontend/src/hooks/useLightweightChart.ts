"use client";

import { useEffect, useRef } from "react";
import { createChart, type IChartApi, type ISeriesApi } from "lightweight-charts";

export function useLightweightChart(
  containerRef: React.RefObject<HTMLDivElement | null>,
) {
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    const chart = createChart(container, {
      layout: {
        background: { color: "#0d1117" },
        textColor: "#8b949e",
      },
      grid: {
        vertLines: { color: "#21262d" },
        horzLines: { color: "#21262d" },
      },
      width: container.clientWidth,
      height: container.clientHeight,
    });

    const series = chart.addLineSeries({
      color: "#209dd7",
      lineWidth: 2,
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        chart.resize(width, height);
      }
    });
    observer.observe(container);

    return () => {
      observer.disconnect();
      chart.remove();
    };
  }, [containerRef]);

  return { chartRef, seriesRef };
}
