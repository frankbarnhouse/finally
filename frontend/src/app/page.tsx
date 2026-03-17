"use client";

import { useState } from "react";
import { useSSE } from "@/hooks/useSSE";
import { Header } from "@/components/Header";
import { Watchlist } from "@/components/Watchlist";
import { MainChart } from "@/components/MainChart";
import { TradeBar } from "@/components/TradeBar";
import { PortfolioHeatmap } from "@/components/PortfolioHeatmap";
import { PnLChart } from "@/components/PnLChart";
import { PositionsTable } from "@/components/PositionsTable";
import { ChatPanel } from "@/components/ChatPanel";

export default function Home() {
  useSSE();
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);

  return (
    <div className="h-screen grid grid-rows-[auto_1fr] bg-terminal-bg">
      <Header />
      <div className="grid lg:grid-cols-[1fr_350px] grid-cols-1 gap-1 p-1 overflow-hidden">
        {/* Left column */}
        <div className="flex flex-col gap-1 overflow-y-auto">
          <div className="grid grid-cols-[280px_1fr] gap-1 min-h-[260px]">
            <Watchlist
              onSelectTicker={setSelectedTicker}
              selectedTicker={selectedTicker}
            />
            <MainChart ticker={selectedTicker} />
          </div>
          <TradeBar />
          <div className="grid grid-cols-2 gap-1">
            <PortfolioHeatmap />
            <PnLChart />
          </div>
          <PositionsTable />
        </div>
        {/* Right column — Chat Panel */}
        <ChatPanel />
      </div>
    </div>
  );
}
