"use client";

import { useState } from "react";
import { useSSE } from "@/hooks/useSSE";
import { Header } from "@/components/Header";
import { Watchlist } from "@/components/Watchlist";
import { MainChart } from "@/components/MainChart";

function Placeholder({ label }: { label: string }) {
  return (
    <div className="bg-terminal-surface border border-terminal-border rounded p-3 flex items-center justify-center">
      <span className="text-terminal-muted text-sm">{label}</span>
    </div>
  );
}

export default function Home() {
  useSSE();
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);

  return (
    <div className="h-screen grid grid-rows-[auto_1fr] bg-terminal-bg">
      <Header />
      <div className="grid grid-cols-[1fr_360px] gap-2 p-2 overflow-hidden">
        {/* Left column */}
        <div className="grid grid-rows-[240px_1fr_200px] gap-2 overflow-hidden">
          <Watchlist
            onSelectTicker={setSelectedTicker}
            selectedTicker={selectedTicker}
          />
          <MainChart ticker={selectedTicker} />
          <div className="grid grid-cols-2 gap-2">
            <Placeholder label="Portfolio Heatmap" />
            <Placeholder label="P&L Chart" />
          </div>
        </div>
        {/* Right column */}
        <div className="grid grid-rows-[1fr_auto] gap-2 overflow-hidden">
          <Placeholder label="Chat Panel" />
          <Placeholder label="Positions / Trade Bar" />
        </div>
      </div>
    </div>
  );
}
