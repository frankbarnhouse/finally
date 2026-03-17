"use client";

import { useMemo, useRef, useState, useEffect } from "react";
import { hierarchy, treemap, treemapSquarify, type HierarchyRectangularNode } from "d3-hierarchy";
import { usePortfolioStore } from "@/stores/portfolioStore";
import { usePriceStore } from "@/stores/priceStore";
import type { Position } from "@/types";

function pnlColor(pnlPercent: number): string {
  const clamped = Math.max(-10, Math.min(10, pnlPercent));
  const intensity = Math.abs(clamped) / 10;
  if (clamped > 0) return `rgba(39, 174, 96, ${0.3 + intensity * 0.7})`;
  if (clamped < 0) return `rgba(231, 76, 60, ${0.3 + intensity * 0.7})`;
  return "rgba(139, 148, 158, 0.5)";
}

interface LeafNode {
  ticker: string;
  marketValue: number;
  pnlPercent: number;
  pnl: number;
}

export function PortfolioHeatmap() {
  const positions = usePortfolioStore((s) => s.positions);
  const livePrices = usePriceStore((s) => s.prices);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ width: 300, height: 200 });

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        if (width > 0 && height > 0) setDims({ width, height });
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  const leaves = useMemo(() => {
    if (!positions || positions.length === 0) return [];

    const nodes: LeafNode[] = positions.map((p: Position) => {
      const currentPrice = livePrices[p.ticker]?.price ?? p.current_price;
      const marketValue = p.quantity * currentPrice;
      const costBasis = p.quantity * p.avg_cost;
      const pnl = marketValue - costBasis;
      const pnlPercent = costBasis > 0 ? (pnl / costBasis) * 100 : 0;
      return { ticker: p.ticker, marketValue: Math.max(marketValue, 1), pnlPercent, pnl };
    });

    const root = hierarchy<LeafNode | { children: LeafNode[] }>({ children: nodes })
      .sum((d) => ("marketValue" in d ? (d as LeafNode).marketValue : 0))
      .sort((a, b) => (b.value ?? 0) - (a.value ?? 0));

    treemap<LeafNode | { children: LeafNode[] }>()
      .size([dims.width, dims.height])
      .padding(2)
      .tile(treemapSquarify)(root);

    return root.leaves() as HierarchyRectangularNode<LeafNode | { children: LeafNode[] }>[];
  }, [positions, livePrices, dims]);

  if (!positions || positions.length === 0) {
    return (
      <div className="rounded border border-terminal-border bg-terminal-surface p-4">
        <h3 className="mb-2 text-xs font-semibold tracking-wider text-terminal-muted">PORTFOLIO</h3>
        <p className="text-sm text-terminal-muted">No positions yet</p>
      </div>
    );
  }

  return (
    <div className="rounded border border-terminal-border bg-terminal-surface p-4">
      <h3 className="mb-2 text-xs font-semibold tracking-wider text-terminal-muted">PORTFOLIO</h3>
      <div ref={containerRef} className="h-48 w-full">
        <svg width={dims.width} height={dims.height}>
          {leaves.map((leaf) => {
            const d = leaf.data as LeafNode;
            const x = leaf.x0 ?? 0;
            const y = leaf.y0 ?? 0;
            const w = (leaf.x1 ?? 0) - x;
            const h = (leaf.y1 ?? 0) - y;
            const showLabel = w > 40 && h > 25;
            const showPnl = w > 50 && h > 40;

            return (
              <g key={d.ticker}>
                <rect
                  x={x}
                  y={y}
                  width={w}
                  height={h}
                  fill={pnlColor(d.pnlPercent)}
                  rx={2}
                />
                {showLabel && (
                  <text
                    x={x + w / 2}
                    y={y + h / 2 - (showPnl ? 6 : 0)}
                    textAnchor="middle"
                    dominantBaseline="central"
                    fill="#c9d1d9"
                    fontSize={12}
                    fontWeight={600}
                  >
                    {d.ticker}
                  </text>
                )}
                {showPnl && (
                  <text
                    x={x + w / 2}
                    y={y + h / 2 + 10}
                    textAnchor="middle"
                    dominantBaseline="central"
                    fill="#8b949e"
                    fontSize={10}
                  >
                    {d.pnl >= 0 ? "+" : ""}${d.pnl.toFixed(0)}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
