# Execution log — LLM Search

Plan: ../plans/2026-10-26-llm-search.md
Spec approved; native execution selected.
Baseline: 19 tests passed; Django check passed. Existing staticfiles warning.
Managed worktree: /home/ryynn/.codex/worktrees/c155/UrbanHarvestCommunity (detached HEAD).
Source branch at creation: feat/llm_searching; source HEAD 2ac85cc.

## Decisions and interfaces
- Task 1 -> Task 2: SearchFilters/ProductCard and repository read interface.
- Task 2 -> Task 3: JSON-serializable result status/filters/products/explanation/degraded.
- Task 3 -> Task 4/5: durable owner-bound job, UUID lease fencing, terminal results.
- Ruling: register llm_searching in Task 1 for test discovery, rather than Task 3 — Django test model import needs the app — no behavior outside LLM changes.
- Ruling: use native managed worktree detached HEAD, rather than manual named branch — platform owns isolation — native branch creation needed before push.

## TDD evidence

### Task 1
RED: missing filters/marketplace implementation, test loader reported expected ModuleNotFoundError (5ea27fa).
GREEN: 7 contract/validation tests; full suite 26/26 passed.
REFACTOR: formatted focused modules/tests; full suite 26/26 passed.
Queries captured: SELECT only, product/category projection, LIMIT 20, no auth/seller columns.

### Task 2
RED: missing OpenRouter/service implementation (9b86b59).
GREEN: 9 tests passed; full suite 35/35 passed.
REFACTOR: formatting; full suite 35/35 passed.
OpenRouter tested at HTTP boundary with complete response envelopes, not a live paid call.
Ruling: explanation uses validated reason codes and server-rendered facts, rather than arbitrary model prose — prevents unsupported product claims — less expressive explanations.
Ruling: extraction includes unsupported_conditions explicitly — represents the approved clarification behavior — semantic completeness still depends on model interpretation and requires live evaluation later.

### Task 3
RED: SearchJob absent (a2c45c8).
GREEN: 5 lifecycle tests passed; full suite 40/40 passed; no missing migrations.
REFACTOR: formatting; full suite 40/40 passed.
Lease minimum 180 seconds covers two bounded provider calls; finalization is fenced by token and expiry.
Quota locks the owner only during admission; marketplace adapter remains account-table-free.
PostgreSQL race behavior has not been verified against a live PostgreSQL server.
