"use client";

import { usePriceStore } from "@/stores/priceStore";

const STATUS_COLORS = {
  connected: "#27ae60",
  connecting: "#ecad0a",
  disconnected: "#e74c3c",
} as const;

export function ConnectionDot() {
  const status = usePriceStore((s) => s.connectionStatus);

  return (
    <span
      title={status}
      className="inline-block w-2.5 h-2.5 rounded-full"
      style={{ backgroundColor: STATUS_COLORS[status] }}
    />
  );
}
