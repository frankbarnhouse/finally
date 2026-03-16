"use client";

import { useEffect, useRef } from "react";
import { useStore } from "./store";
import { PriceUpdate } from "./types";

export function useSSE() {
  const updatePrice = useStore((s) => s.updatePrice);
  const setConnectionStatus = useStore((s) => s.setConnectionStatus);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const es = new EventSource("/api/stream/prices");
    eventSourceRef.current = es;

    es.onopen = () => {
      setConnectionStatus("connected");
    };

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // SSE sends all prices as a dict: {ticker: PriceUpdate, ...}
        for (const update of Object.values(data)) {
          updatePrice(update as PriceUpdate);
        }
      } catch {
        // Ignore malformed messages
      }
    };

    es.onerror = () => {
      if (es.readyState === EventSource.CONNECTING) {
        setConnectionStatus("reconnecting");
      } else {
        setConnectionStatus("disconnected");
      }
    };

    return () => {
      es.close();
      eventSourceRef.current = null;
    };
  }, [updatePrice, setConnectionStatus]);
}
