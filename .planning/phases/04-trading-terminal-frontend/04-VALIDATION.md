---
phase: 4
slug: trading-terminal-frontend
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest + React Testing Library |
| **Config file** | `frontend/vitest.config.ts` (created during scaffolding) |
| **Quick run command** | `cd frontend && npm run test -- --run` |
| **Full suite command** | `cd frontend && npm run test -- --run` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick test command
- **After every plan wave:** Run full suite + visual check in browser
- **Before `/gsd:verify-work`:** Full suite must be green + manual visual inspection
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 1 | UI-01 | build | `cd frontend && npm run build` | ❌ W0 | ⬜ pending |
| 4-02-01 | 02 | 2 | UI-02,03 | visual | Browser check — prices streaming, flash animations | N/A | ⬜ pending |
| 4-02-02 | 02 | 2 | UI-04,05 | visual | Browser check — sparklines, main chart | N/A | ⬜ pending |
| 4-03-01 | 03 | 3 | UI-06,07,08 | visual | Browser check — heatmap, P&L chart, positions | N/A | ⬜ pending |
| 4-04-01 | 04 | 4 | UI-09,10,11,12 | visual | Browser check — trade bar, chat, header | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/` scaffolded with Next.js + TypeScript + Tailwind
- [ ] Build succeeds with `npm run build`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dark terminal aesthetic | UI-01 | Visual design quality | Open browser, verify dark theme, data-dense layout |
| Price flash animations | UI-03 | CSS animation timing | Watch prices update, verify green/red flash with fade |
| Sparkline progressive fill | UI-04 | Time-based accumulation | Wait 30s, verify sparklines filling in |
| Chart interactivity | UI-05 | Click interaction | Click tickers, verify chart updates |
| Heatmap visualization | UI-06 | Color/sizing accuracy | Make trades, verify treemap updates |
| Connection status | UI-12 | Browser EventSource state | Check dot color matches SSE connection |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
