---
phase: 2
slug: portfolio-and-watchlist-apis
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3+ with pytest-asyncio |
| **Config file** | `backend/pyproject.toml` (pytest section exists) |
| **Quick run command** | `cd backend && uv run pytest tests/api/ -x -q` |
| **Full suite command** | `cd backend && uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/api/ -x -q`
- **After every plan wave:** Run `cd backend && uv run pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 1 | PORT-01 | unit | `uv run pytest tests/api/test_portfolio.py -x` | ❌ W0 | ⬜ pending |
| 2-01-02 | 01 | 1 | PORT-02,03,04,05 | unit | `uv run pytest tests/api/test_trade.py -x` | ❌ W0 | ⬜ pending |
| 2-01-03 | 01 | 1 | PORT-06,07 | unit | `uv run pytest tests/api/test_snapshots.py -x` | ❌ W0 | ⬜ pending |
| 2-02-01 | 02 | 1 | WATCH-01,02,03 | unit | `uv run pytest tests/api/test_watchlist.py -x` | ❌ W0 | ⬜ pending |
| 2-03-01 | 03 | 1 | INFRA-04 | unit | `uv run pytest tests/api/test_health.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/api/__init__.py` — test package
- [ ] `backend/tests/api/test_portfolio.py` — stubs for PORT-01
- [ ] `backend/tests/api/test_trade.py` — stubs for PORT-02..05
- [ ] `backend/tests/api/test_watchlist.py` — stubs for WATCH-01..03
- [ ] `backend/tests/api/test_health.py` — stubs for INFRA-04

*Existing pytest infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Watchlist changes reflect in SSE price stream | WATCH-01 | SSE stream verification requires browser/EventSource | Add ticker via POST, verify SSE includes it |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
