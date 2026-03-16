---
phase: 3
slug: llm-chat-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3+ with pytest-asyncio |
| **Config file** | `backend/pyproject.toml` (pytest section exists) |
| **Quick run command** | `cd backend && uv run pytest tests/services/test_chat.py tests/api/test_chat.py -x -q` |
| **Full suite command** | `cd backend && uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/services/test_chat.py tests/api/test_chat.py -x -q`
- **After every plan wave:** Run `cd backend && uv run pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 1 | CHAT-01,04 | unit | `uv run pytest tests/services/test_chat.py -x` | ❌ W0 | ⬜ pending |
| 3-01-02 | 01 | 1 | CHAT-02,03,06 | unit | `uv run pytest tests/services/test_chat.py -x` | ❌ W0 | ⬜ pending |
| 3-01-03 | 01 | 1 | CHAT-05 | unit | `uv run pytest tests/services/test_chat.py::test_mock_mode -x` | ❌ W0 | ⬜ pending |
| 3-02-01 | 02 | 2 | CHAT-01 | integration | `uv run pytest tests/api/test_chat.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/services/test_chat.py` — stubs for CHAT-01..06
- [ ] `backend/tests/api/test_chat.py` — stubs for chat API endpoint

*Existing pytest infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| AI response references actual portfolio state | CHAT-01 | Requires real LLM call to verify contextual awareness | Send "what's in my portfolio?" with GOOGLE_API_KEY set |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
