# Phase 4: Trading Terminal Frontend - Research

**Researched:** 2026-03-16
**Domain:** Next.js static export, real-time SSE streaming UI, financial charting, portfolio visualization
**Confidence:** HIGH

## Summary

This phase builds the entire browser-facing trading terminal as a Next.js static export served by the existing FastAPI backend. The backend APIs (phases 1-3) are complete and provide: SSE price streaming at `/api/stream/prices`, portfolio CRUD, watchlist CRUD, and LLM chat. The frontend consumes these via native `fetch` and `EventSource` -- no special HTTP libraries needed.

The stack is Next.js 15 + React 18 + Tailwind CSS v4 + Lightweight Charts 4.x + Zustand 5.x. The treemap (portfolio heatmap) should use `d3-hierarchy` for layout computation with React SVG rendering -- no heavy charting library needed for this single visualization. All components are client components (`"use client"`) since the app is a static export with no server-side rendering at runtime.

**Primary recommendation:** Scaffold with `create-next-app@15`, manually upgrade to Tailwind v4, build incrementally starting with layout shell and SSE connection, then add panels one by one. Use Zustand as the central price/portfolio state hub that all components subscribe to with selectors.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UI-01 | Dark trading terminal layout with Bloomberg-inspired aesthetic (backgrounds ~#0d1117) | Tailwind v4 custom theme with CSS variables; dark backgrounds, muted borders, accent colors |
| UI-02 | Watchlist panel with live-updating prices from SSE stream | Native EventSource + Zustand price store; SSE data shape documented below |
| UI-03 | Price flash animations (green uptick, red downtick) fading over ~500ms | CSS transition on background-color; toggle class on direction change, remove after timeout |
| UI-04 | Sparkline mini-charts accumulated from SSE since page load | Lightweight Charts v4 LineSeries in small containers; accumulate price history in Zustand |
| UI-05 | Main chart area showing selected ticker price history (click ticker to select) | Lightweight Charts v4 AreaSeries; Zustand selected ticker state; accumulated SSE data |
| UI-06 | Portfolio heatmap (treemap) sized by position weight, colored by P&L | d3-hierarchy treemap layout + React SVG rendering; color interpolation green/red |
| UI-07 | P&L line chart showing portfolio value over time from snapshots | Lightweight Charts v4 LineSeries; data from GET /api/portfolio/history |
| UI-08 | Positions table: ticker, quantity, avg cost, current price, unrealized P&L, % change | Tailwind-styled table; live current_price from Zustand price store |
| UI-09 | Trade bar with ticker input, quantity input, buy button, sell button | Form component; POST /api/portfolio/trade; update portfolio state on success |
| UI-10 | AI chat panel with message input, scrolling history, loading indicator | POST /api/chat; render message + actions; auto-scroll; loading state |
| UI-11 | Inline trade and watchlist action confirmations in chat messages | Parse `actions` field from chat response; render trade/watchlist badges inline |
| UI-12 | Header with live portfolio total value, cash balance, connection status dot | Zustand portfolio store; SSE connection state tracking via EventSource events |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 15.5.x | React framework, static export | Latest stable v15. `output: 'export'` produces static files served by FastAPI. Do NOT use v16. |
| React | 18.3.1 | UI framework | Default pairing with Next.js 15. Do NOT upgrade to React 19. |
| TypeScript | 5.x | Type safety | Included by create-next-app. |
| Tailwind CSS | 4.2.1 | Utility-first styling | CSS-first config (no tailwind.config.js). Manual setup after scaffolding. |
| Lightweight Charts | 4.2.3 | Financial charts (sparklines, main chart, P&L) | TradingView's canvas-based lib. 45KB. Use v4.2.3 (latest v4), NOT v5. |
| Zustand | 5.0.12 | Client state management | 1KB, hook-based, selector-driven re-renders. Ideal for streaming price data. |
| d3-hierarchy | 3.1.2 | Treemap layout computation | Computes rectangle positions for portfolio heatmap. React renders the SVG. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @tailwindcss/postcss | latest | PostCSS plugin for Tailwind v4 | Required for Tailwind v4 build pipeline |
| postcss | latest | CSS transformation | Required by @tailwindcss/postcss |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| d3-hierarchy | recharts Treemap | Recharts adds 200KB+ for one component. d3-hierarchy is 30KB and we render SVG ourselves. |
| d3-hierarchy | react-treemap | Abandoned/unmaintained packages. d3-hierarchy is the gold standard. |
| Lightweight Charts v4 | v5 | v5 is only months old (5.1.0). v4.2.3 is battle-tested. Stick with v4. |
| Native fetch | axios/tanstack-query | Unnecessary dependencies. Our API calls are simple same-origin fetches. |

**Installation:**

```bash
# Scaffold (from project root)
npx create-next-app@15 frontend --typescript --eslint --app --src-dir --no-import-alias

# In frontend/, replace Tailwind v3 with v4
cd frontend
npm uninstall tailwindcss postcss autoprefixer
npm install tailwindcss@^4.2.0 @tailwindcss/postcss postcss

# Core dependencies
npm install lightweight-charts@^4.2.0 zustand@^5.0.0 d3-hierarchy@^3.1.0

# Type definitions
npm install -D @types/d3-hierarchy
```

## Architecture Patterns

### Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx          # Root layout (dark theme, font)
│   │   ├── page.tsx            # Main terminal page
│   │   └── globals.css         # Tailwind import + custom CSS vars
│   ├── components/
│   │   ├── Header.tsx          # Portfolio value, cash, connection dot
│   │   ├── Watchlist.tsx       # Ticker grid with prices + sparklines
│   │   ├── MainChart.tsx       # Large chart for selected ticker
│   │   ├── PortfolioHeatmap.tsx # Treemap visualization
│   │   ├── PnLChart.tsx        # Portfolio value over time
│   │   ├── PositionsTable.tsx  # Positions with live P&L
│   │   ├── TradeBar.tsx        # Buy/sell form
│   │   ├── ChatPanel.tsx       # AI chat sidebar
│   │   └── ConnectionDot.tsx   # Green/yellow/red indicator
│   ├── stores/
│   │   ├── priceStore.ts       # SSE prices + price history
│   │   ├── portfolioStore.ts   # Positions, cash, portfolio value
│   │   └── chatStore.ts        # Chat messages, loading state
│   ├── hooks/
│   │   ├── useSSE.ts           # EventSource connection manager
│   │   └── useLightweightChart.ts # Chart lifecycle hook
│   ├── lib/
│   │   └── api.ts              # fetch wrappers for /api/* endpoints
│   └── types/
│       └── index.ts            # Shared TypeScript interfaces
├── next.config.ts              # output: 'export'
├── postcss.config.mjs          # @tailwindcss/postcss plugin
└── package.json
```

### Pattern 1: Zustand Price Store with SSE

**What:** Central store receives SSE price updates. Components subscribe via selectors for surgical re-renders.
**When to use:** All components that display live prices.

```typescript
// stores/priceStore.ts
import { create } from 'zustand';

interface PriceUpdate {
  ticker: string;
  price: number;
  previous_price: number;
  timestamp: number;
  change: number;
  change_percent: number;
  direction: 'up' | 'down' | 'flat';
}

interface PriceState {
  prices: Record<string, PriceUpdate>;
  priceHistory: Record<string, { time: number; value: number }[]>;
  connectionStatus: 'connected' | 'connecting' | 'disconnected';
  updatePrices: (data: Record<string, PriceUpdate>) => void;
  setConnectionStatus: (status: PriceState['connectionStatus']) => void;
}

export const usePriceStore = create<PriceState>((set) => ({
  prices: {},
  priceHistory: {},
  connectionStatus: 'connecting',
  updatePrices: (data) =>
    set((state) => {
      const newHistory = { ...state.priceHistory };
      for (const [ticker, update] of Object.entries(data)) {
        const existing = newHistory[ticker] || [];
        newHistory[ticker] = [...existing, { time: update.timestamp, value: update.price }];
      }
      return { prices: data, priceHistory: newHistory };
    }),
  setConnectionStatus: (status) => set({ connectionStatus: status }),
}));
```

### Pattern 2: EventSource SSE Hook

**What:** Custom hook manages EventSource lifecycle, reconnection, and feeds Zustand.
**When to use:** Once, at the app level.

```typescript
// hooks/useSSE.ts
import { useEffect } from 'react';
import { usePriceStore } from '@/stores/priceStore';

export function useSSE() {
  const updatePrices = usePriceStore((s) => s.updatePrices);
  const setStatus = usePriceStore((s) => s.setConnectionStatus);

  useEffect(() => {
    const es = new EventSource('/api/stream/prices');

    es.onopen = () => setStatus('connected');
    es.onmessage = (event) => {
      const data = JSON.parse(event.data);
      updatePrices(data);
    };
    es.onerror = () => setStatus('disconnected');

    return () => es.close();
  }, [updatePrices, setStatus]);
}
```

### Pattern 3: Lightweight Charts with React Refs

**What:** Create chart instance in useEffect, update data via refs, clean up on unmount.
**When to use:** MainChart, PnLChart, sparklines.

```typescript
// hooks/useLightweightChart.ts
import { useEffect, useRef } from 'react';
import { createChart, IChartApi, ISeriesApi, LineSeries } from 'lightweight-charts';

export function useLightweightChart(containerRef: React.RefObject<HTMLDivElement | null>) {
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Line'> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: '#0d1117' },
        textColor: '#8b949e',
      },
      grid: {
        vertLines: { color: '#21262d' },
        horzLines: { color: '#21262d' },
      },
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
    });

    const series = chart.addSeries(LineSeries, {
      color: '#209dd7',
      lineWidth: 2,
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const handleResize = () => {
      if (containerRef.current) {
        chart.resize(containerRef.current.clientWidth, containerRef.current.clientHeight);
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [containerRef]);

  return { chartRef, seriesRef };
}
```

### Pattern 4: Treemap with d3-hierarchy + React SVG

**What:** d3 computes layout, React renders SVG rectangles with colors.
**When to use:** Portfolio heatmap (UI-06).

```typescript
// Inside PortfolioHeatmap.tsx
import { hierarchy, treemap, treemapSquarify } from 'd3-hierarchy';

function computeTreemap(positions: Position[], width: number, height: number) {
  const root = hierarchy({ children: positions })
    .sum((d: any) => d.quantity * d.current_price) // size by market value
    .sort((a, b) => (b.value || 0) - (a.value || 0));

  treemap<any>()
    .size([width, height])
    .padding(2)
    .tile(treemapSquarify)(root);

  return root.leaves();
}

// Render: map leaves to <rect> with x0, y0, width=(x1-x0), height=(y1-y0)
// Color: interpolate from red (#e74c3c) to green (#27ae60) based on unrealized_pnl
```

### Pattern 5: Price Flash Animation (CSS)

**What:** Brief background color flash on price change, fading over 500ms.
**When to use:** Watchlist price cells (UI-03).

```css
/* globals.css */
.price-flash-up {
  background-color: rgba(39, 174, 96, 0.3);
  transition: background-color 0.5s ease-out;
}
.price-flash-down {
  background-color: rgba(231, 76, 60, 0.3);
  transition: background-color 0.5s ease-out;
}
.price-flash-none {
  background-color: transparent;
  transition: background-color 0.5s ease-out;
}
```

```typescript
// In watchlist row component
const [flash, setFlash] = useState<'up' | 'down' | 'none'>('none');
useEffect(() => {
  if (priceUpdate?.direction === 'up') setFlash('up');
  else if (priceUpdate?.direction === 'down') setFlash('down');
  const timeout = setTimeout(() => setFlash('none'), 500);
  return () => clearTimeout(timeout);
}, [priceUpdate?.price]);
```

### Anti-Patterns to Avoid

- **React Context for prices:** Context triggers full subtree re-renders on every price tick (~2/second). Use Zustand with selectors instead.
- **SVG charting for streaming data:** SVG re-renders the entire DOM tree. Lightweight Charts uses canvas for O(1) rendering.
- **useEffect for data fetching without cleanup:** Always close EventSource and abort fetch in cleanup functions.
- **Server components for live data:** Everything showing live prices must be a client component (`"use client"`). With `output: 'export'`, all interactive components are client-side anyway.
- **Importing all of d3:** Only import `d3-hierarchy`. Do NOT `npm install d3` (pulls in 500KB+).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Financial charts | Custom canvas drawing | Lightweight Charts v4 | Crosshair, time axis formatting, streaming updates all built-in |
| Treemap layout | Rectangle packing algorithm | d3-hierarchy `treemap()` | Squarify algorithm is non-trivial; d3 is the standard |
| State management for streaming | Custom pub/sub or Context | Zustand | Selector-based re-renders prevent performance death spiral |
| SSE connection | Custom reconnection logic | Native EventSource | Built-in retry with configurable interval (backend sends `retry: 1000`) |
| Price formatting | Manual toFixed everywhere | Shared formatter util | Consistency across watchlist, positions, header |

## Common Pitfalls

### Pitfall 1: Re-renders on Every Price Tick
**What goes wrong:** Using React Context or passing prices as props causes the entire component tree to re-render every 500ms.
**Why it happens:** Context re-renders all consumers on any change. Props cascade through the tree.
**How to avoid:** Use Zustand with selectors. Each component subscribes to only the data it needs: `usePriceStore(s => s.prices['AAPL'])`.
**Warning signs:** Laggy UI, high CPU usage, React DevTools showing unnecessary renders.

### Pitfall 2: Lightweight Charts Memory Leak
**What goes wrong:** Chart instances not cleaned up on component unmount accumulate and leak memory.
**Why it happens:** `createChart()` creates canvas elements and animation frames. Must call `chart.remove()` to clean up.
**How to avoid:** Always return `chart.remove()` from the useEffect cleanup function. Store chart ref and check it exists before operating.
**Warning signs:** Growing memory usage, "detached HTMLDivElement" in heap snapshots.

### Pitfall 3: Static Export Breaks with Server Features
**What goes wrong:** Using `getServerSideProps`, API routes, or server actions causes build failures with `output: 'export'`.
**Why it happens:** Static export generates HTML at build time. No Node.js server at runtime.
**How to avoid:** All data fetching happens client-side via `useEffect` + `fetch`. No Next.js API routes. The backend is FastAPI.
**Warning signs:** Build errors mentioning "Dynamic server usage".

### Pitfall 4: Sparkline History Grows Unbounded
**What goes wrong:** Accumulating every price tick in memory eventually causes performance degradation.
**Why it happens:** SSE pushes ~2 updates/second per ticker. 10 tickers = 20 updates/second. After 1 hour = 72,000 data points.
**How to avoid:** Cap price history arrays at a reasonable limit (e.g., 500 points per ticker). Slice oldest entries when limit is exceeded.
**Warning signs:** Increasing memory usage over time, sparkline rendering slowing down.

### Pitfall 5: EventSource Reconnection Floods
**What goes wrong:** EventSource reconnects immediately on error, creating a tight reconnection loop.
**Why it happens:** Default browser retry is aggressive. If the server is down, reconnect attempts pile up.
**How to avoid:** The backend already sends `retry: 1000` directive. Track connection status and show it to the user (connection dot). EventSource handles this automatically.
**Warning signs:** Console filled with connection errors, high network activity.

### Pitfall 6: Tailwind v4 Config Confusion
**What goes wrong:** Creating `tailwind.config.js` or `tailwind.config.ts` (v3 pattern) when using Tailwind v4.
**Why it happens:** Most tutorials still show v3 config. `create-next-app@15 --tailwind` may scaffold v3.
**How to avoid:** Delete any `tailwind.config.*` files. Use CSS-first config in `globals.css` with `@import "tailwindcss"` and `@theme` directive for custom values.
**Warning signs:** Config file exists but changes don't take effect, or duplicate config.

### Pitfall 7: Lightweight Charts Time Format
**What goes wrong:** Chart shows incorrect times or errors on data update.
**Why it happens:** Lightweight Charts expects time as seconds (Unix timestamp in seconds), not milliseconds. Also, time values must be strictly increasing.
**How to avoid:** Convert timestamps to seconds (`Math.floor(timestamp)`). Ensure each new data point has a time strictly greater than the previous one. Use `series.update()` for the latest point, not `setData()` on every tick.
**Warning signs:** "Value is not a number" errors, chart not rendering, time axis showing wrong dates.

## Code Examples

### SSE Data Shape (from Backend)

The SSE endpoint at `GET /api/stream/prices` sends events in this format:

```
data: {"AAPL": {"ticker": "AAPL", "price": 190.50, "previous_price": 190.25, "timestamp": 1710600000.0, "change": 0.25, "change_percent": 0.1314, "direction": "up"}, "GOOGL": {...}, ...}
```

Each event contains ALL tracked tickers as a single JSON object keyed by ticker symbol.

### API Response Shapes

**GET /api/watchlist:**
```json
[
  {"ticker": "AAPL", "price": 190.50},
  {"ticker": "GOOGL", "price": 175.20}
]
```

**GET /api/portfolio:**
```json
{
  "positions": [
    {"ticker": "AAPL", "quantity": 10, "avg_cost": 185.00, "current_price": 190.50, "unrealized_pnl": 55.00}
  ],
  "cash_balance": 8150.00,
  "total_value": 10055.00
}
```

**POST /api/portfolio/trade** (request: `{ticker, quantity, side}`):
```json
{
  "trade": {"ticker": "AAPL", "side": "buy", "quantity": 10, "price": 190.50, "executed_at": "..."},
  "cash_balance": 8095.00,
  "position": {"ticker": "AAPL", "quantity": 10, "avg_cost": 190.50}
}
```
Error: `{"error": "Insufficient cash: need $1905.00 but only $500.00 available"}`
When sell closes position: `"position": null`

**GET /api/portfolio/history:**
```json
[
  {"total_value": 10000.00, "recorded_at": "2026-03-16T12:00:00+00:00"},
  {"total_value": 10055.00, "recorded_at": "2026-03-16T12:00:30+00:00"}
]
```

**POST /api/chat** (request: `{message}`):
```json
{
  "message": "I'll buy 10 shares of AAPL for you.",
  "actions": {
    "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10, "price": 190.50, "executed_at": "..."}],
    "watchlist_changes": [{"ticker": "PYPL", "action": "add"}]
  }
}
```

### Next.js Config for Static Export

```typescript
// next.config.ts
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'export',
  // Images must use unoptimized since no Node.js server at runtime
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
```

### Tailwind v4 Custom Theme (CSS-first)

```css
/* globals.css */
@import "tailwindcss";

@theme {
  --color-terminal-bg: #0d1117;
  --color-terminal-surface: #161b22;
  --color-terminal-border: #21262d;
  --color-terminal-text: #c9d1d9;
  --color-terminal-muted: #8b949e;
  --color-accent-yellow: #ecad0a;
  --color-accent-blue: #209dd7;
  --color-accent-purple: #753991;
  --color-profit: #27ae60;
  --color-loss: #e74c3c;
}
```

Usage: `bg-terminal-bg`, `text-accent-yellow`, `border-terminal-border`, etc.

### TypeScript Interfaces

```typescript
// types/index.ts
export interface PriceUpdate {
  ticker: string;
  price: number;
  previous_price: number;
  timestamp: number;
  change: number;
  change_percent: number;
  direction: 'up' | 'down' | 'flat';
}

export interface Position {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  unrealized_pnl: number;
}

export interface Portfolio {
  positions: Position[];
  cash_balance: number;
  total_value: number;
}

export interface TradeResult {
  trade: {
    ticker: string;
    side: 'buy' | 'sell';
    quantity: number;
    price: number;
    executed_at: string;
  };
  cash_balance: number;
  position: { ticker: string; quantity: number; avg_cost: number } | null;
}

export interface ChatResponse {
  message: string;
  actions: {
    trades: Array<{
      ticker: string;
      side: string;
      quantity: number;
      price: number;
      executed_at: string;
    }>;
    watchlist_changes: Array<{
      ticker: string;
      action: 'add' | 'remove';
    }>;
  };
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| tailwind.config.js | CSS-first @theme in globals.css | Tailwind v4 (2025) | No config file needed; simpler, faster builds |
| create-next-app sets up Tailwind v3 | Must manually upgrade to v4 | Current (2026) | Extra setup step after scaffolding |
| chart.addLineSeries() | chart.addSeries(LineSeries) | Lightweight Charts v4 | Series type passed as argument, not method name |
| Zustand create with no types | create<State>() generic | Zustand v5 | TypeScript-first API |

## Open Questions

1. **Lightweight Charts v4.2.3 sparkline sizing**
   - What we know: createChart requires explicit width/height or container dimensions
   - What's unclear: Whether very small containers (e.g., 80x30px for sparkline) render cleanly
   - Recommendation: Test early. If sparklines look bad at small sizes, fall back to simple SVG polyline (minimal code).

2. **Tailwind v4 with create-next-app@15**
   - What we know: create-next-app@15 may scaffold Tailwind v3. Need to manually swap to v4.
   - What's unclear: Whether the scaffolded postcss config conflicts with v4
   - Recommendation: After scaffolding, remove all Tailwind v3 artifacts (tailwind.config.*, autoprefixer) and set up v4 from scratch per official docs.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest + React Testing Library |
| Config file | `frontend/vitest.config.ts` (to be created) |
| Quick run command | `cd frontend && npm test -- --run` |
| Full suite command | `cd frontend && npm test -- --run --coverage` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-01 | Dark terminal layout renders | smoke | `cd frontend && npx vitest run src/__tests__/layout.test.tsx` | Wave 0 |
| UI-02 | Watchlist displays prices from mock data | unit | `cd frontend && npx vitest run src/__tests__/Watchlist.test.tsx` | Wave 0 |
| UI-03 | Price flash class applied on direction change | unit | `cd frontend && npx vitest run src/__tests__/PriceFlash.test.tsx` | Wave 0 |
| UI-04 | Sparkline component renders without error | smoke | `cd frontend && npx vitest run src/__tests__/Sparkline.test.tsx` | Wave 0 |
| UI-05 | Main chart container renders | smoke | `cd frontend && npx vitest run src/__tests__/MainChart.test.tsx` | Wave 0 |
| UI-06 | Treemap computes correct rectangle positions | unit | `cd frontend && npx vitest run src/__tests__/Treemap.test.tsx` | Wave 0 |
| UI-07 | P&L chart renders with mock history data | smoke | `cd frontend && npx vitest run src/__tests__/PnLChart.test.tsx` | Wave 0 |
| UI-08 | Positions table displays position data correctly | unit | `cd frontend && npx vitest run src/__tests__/PositionsTable.test.tsx` | Wave 0 |
| UI-09 | Trade bar submits buy/sell requests | unit | `cd frontend && npx vitest run src/__tests__/TradeBar.test.tsx` | Wave 0 |
| UI-10 | Chat panel renders messages and shows loading | unit | `cd frontend && npx vitest run src/__tests__/ChatPanel.test.tsx` | Wave 0 |
| UI-11 | Chat actions rendered inline in messages | unit | `cd frontend && npx vitest run src/__tests__/ChatActions.test.tsx` | Wave 0 |
| UI-12 | Header shows portfolio value and connection dot | unit | `cd frontend && npx vitest run src/__tests__/Header.test.tsx` | Wave 0 |

### Sampling Rate

- **Per task commit:** `cd frontend && npx vitest run --reporter=verbose`
- **Per wave merge:** `cd frontend && npx vitest run --coverage`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `frontend/vitest.config.ts` -- Vitest configuration with jsdom environment
- [ ] `frontend/src/__tests__/` directory -- All test files listed above
- [ ] Vitest + testing-library install: `npm install -D vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event`
- [ ] `frontend/src/test-utils.tsx` -- Shared test render wrapper with store providers

## Sources

### Primary (HIGH confidence)
- Backend source code: `backend/app/market/models.py`, `stream.py`, `cache.py` -- exact SSE data shapes
- Backend source code: `backend/app/services/portfolio.py`, `watchlist.py`, `chat.py` -- exact API response shapes
- [Next.js static exports guide](https://nextjs.org/docs/app/guides/static-exports) -- output: 'export' configuration
- [Tailwind CSS v4 Next.js installation](https://tailwindcss.com/docs/installation/framework-guides/nextjs) -- official setup steps
- [Lightweight Charts React tutorial](https://tradingview.github.io/lightweight-charts/tutorials/react/simple) -- official React integration
- [d3-hierarchy treemap](https://d3js.org/d3-hierarchy/treemap) -- official API docs
- npm registry: verified all package versions via `npm view`

### Secondary (MEDIUM confidence)
- [React Graph Gallery treemap](https://www.react-graph-gallery.com/treemap) -- d3-hierarchy + React SVG pattern
- WebSearch: create-next-app@15 may default to Tailwind v3, needs manual v4 upgrade

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries verified via npm registry, versions confirmed current
- Architecture: HIGH -- patterns verified against official docs and backend source code
- API contracts: HIGH -- read directly from backend service layer source code
- Pitfalls: HIGH -- based on well-known React performance patterns and library documentation

**Research date:** 2026-03-16
**Valid until:** 2026-04-16 (stable ecosystem, no fast-moving dependencies)
