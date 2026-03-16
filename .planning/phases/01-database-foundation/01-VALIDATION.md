---
phase: 1
slug: database-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3+ with pytest-asyncio |
| **Config file** | `backend/pyproject.toml` (pytest section exists) |
| **Quick run command** | `cd backend && uv run pytest tests/db/test_init.py -x -q` |
| **Full suite command** | `cd backend && uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~3 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/db/test_init.py -x -q`
- **After every plan wave:** Run `cd backend && uv run pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | DB-01 | unit | `uv run pytest tests/db/test_init.py::test_schema_creation -x` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | DB-02 | unit | `uv run pytest tests/db/test_init.py::test_default_user -x` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | DB-03 | unit | `uv run pytest tests/db/test_init.py::test_default_watchlist -x` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 1 | DB-04 | unit | `uv run pytest tests/db/test_init.py::test_wal_mode -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/db/test_init.py` — stubs for DB-01, DB-02, DB-03, DB-04
- [ ] `backend/tests/conftest.py` — shared fixtures (temp db path, async event loop)

*Existing pytest infrastructure covers framework needs.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
