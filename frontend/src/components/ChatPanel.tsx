"use client";

import { useState, useRef, useEffect } from "react";
import { useChatStore } from "@/stores/chatStore";
import { usePortfolioStore } from "@/stores/portfolioStore";
import { useWatchlistStore } from "@/stores/watchlistStore";

export function ChatPanel() {
  const messages = useChatStore((s) => s.messages);
  const loading = useChatStore((s) => s.loading);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const fetchPortfolio = usePortfolioStore((s) => s.fetchPortfolio);
  const fetchWatchlist = useWatchlistStore((s) => s.fetchWatchlist);

  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const prevMessageCount = useRef(messages.length);

  useEffect(() => {
    if (messages.length > prevMessageCount.current) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });

      const last = messages[messages.length - 1];
      if (last.role === "assistant" && last.actions) {
        if (last.actions.trades?.length > 0) {
          fetchPortfolio();
        }
        if (last.actions.watchlist_changes?.length > 0) {
          fetchWatchlist();
        }
      }
    }
    prevMessageCount.current = messages.length;
  }, [messages, fetchPortfolio, fetchWatchlist]);

  async function handleSend() {
    const trimmed = input.trim();
    if (!trimmed || loading) return;
    setInput("");
    await sendMessage(trimmed);
  }

  return (
    <div className="flex h-full flex-col rounded border border-terminal-border bg-terminal-surface">
      <div className="border-b border-terminal-border px-3 py-2">
        <h3 className="text-xs font-semibold tracking-wider text-terminal-muted">AI ASSISTANT</h3>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.length === 0 && !loading && (
          <p className="text-sm text-terminal-muted">
            Ask me about your portfolio, or tell me to make a trade!
          </p>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded px-3 py-2 text-sm ${
                msg.role === "user"
                  ? "bg-accent-purple/20 text-terminal-text"
                  : "bg-terminal-bg text-terminal-text"
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
              {msg.role === "assistant" && msg.actions && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {msg.actions.trades?.map((t, j) => (
                    <span
                      key={`trade-${j}`}
                      className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${
                        t.side === "buy" ? "bg-profit/20 text-profit" : "bg-loss/20 text-loss"
                      }`}
                    >
                      {t.side === "buy" ? "Bought" : "Sold"} {t.quantity} {t.ticker} @ ${t.price.toFixed(2)}
                    </span>
                  ))}
                  {msg.actions.watchlist_changes?.map((w, j) => (
                    <span
                      key={`wl-${j}`}
                      className="inline-block rounded bg-accent-blue/20 px-2 py-0.5 text-xs font-medium text-accent-blue"
                    >
                      {w.action === "add" ? "Added" : "Removed"} {w.ticker} {w.action === "add" ? "to" : "from"} watchlist
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="rounded bg-terminal-bg px-3 py-2 text-sm text-terminal-muted">
              <span className="animate-pulse">Thinking...</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div className="border-t border-terminal-border p-2">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask about your portfolio..."
            className="flex-1 rounded bg-terminal-bg px-3 py-1.5 text-sm text-terminal-text placeholder-terminal-muted border border-terminal-border focus:outline-none focus:border-accent-blue"
          />
          <button
            onClick={handleSend}
            disabled={loading}
            className="rounded bg-accent-purple px-3 py-1.5 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
