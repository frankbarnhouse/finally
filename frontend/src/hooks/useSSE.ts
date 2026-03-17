"use client";

import { useEffect } from "react";
import { usePriceStore } from "@/stores/priceStore";

export function useSSE() {
  const updatePrices = usePriceStore((s) => s.updatePrices);
  const setStatus = usePriceStore((s) => s.setConnectionStatus);

  useEffect(() => {
    const es = new EventSource("/api/stream/prices");

    es.onopen = () => setStatus("connected");
    es.onmessage = (event) => {
      const data = JSON.parse(event.data);
      updatePrices(data);
    };
    es.onerror = () => setStatus("disconnected");

    return () => es.close();
  }, [updatePrices, setStatus]);
}
