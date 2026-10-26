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

### Task 4
RED: missing routes/templates produced 404 and absent status_url (ad0f316).
GREEN: 5 API/template tests passed; full suite 45/45 passed. CSS build and node --check passed.
REFACTOR: formatting; full suite 45/45 passed.
Login tests create the app-specific Session row, exercising SingleSessionMiddleware.
JSON rendering uses textContent and the reusable card template; no model prose is inserted as HTML.

### Task 5
RED: transport/coordinator absent (7ed90f0).
GREEN: 7 broker tests; extended bounded pool/backoff coverage brings task tests to 9; full suite 54/54 passed.
REFACTOR: sorted imports, lint cleanup, tuple Meta indexes, and resource formatting; full suite 54/54 passed.
Pika pinned 1.3.2; confirmed APIs against its tagged primary source.

### Task 6: infrastructure evidence
Full PostgreSQL suite: 54/54 passed against a temporary PostgreSQL 16 cluster under /tmp, isolated from the host server.
Real PostgreSQL races: 2/2 passed (six concurrent admissions -> three accepted; four competing claims -> one token).
These two tests are additional verification of existing behavior, not represented as new RED cycles.

## Transfer to original checkout

User explicitly requested continuing directly in `/home/ryynn/Desktop/UrbanHarvestCommunity`
and preserving commit history. The clean `feat/llm_searching` branch was fast-forwarded
from `2ac85cc` to `ea0052c`: all 17 worktree commits retained their original hashes.
The two generated documentation files in the source checkout were byte-compared with
their committed counterparts and backed up before transfer. No user edits were discarded.
All subsequent fixes and verification ran from the original checkout.

## Whole-branch review and one fix pass

Fresh independent reviewer examined `2ac85cc..ea0052c`: no Critical issues, two Important
issues, one Minor issue. Review was read-only; native implementer applied fixes.

- Fixed schema drift classification: `b53ac44` RED reproduced three uncaught Django
  schema errors; `e14a922` GREEN validates contracted fields and maps schema errors to
  `marketplace_unavailable`. Seven related tests passed; full suite 59 tests, 2 SQLite
  skips, no failures.
- Fixed provider total deadline: `f1fb4f6` RED adds real socket regressions;
  `f8d0f4c` GREEN introduces a spawned, bounded HTTP process. A real HTTP server
  trickling a byte every 50 ms is terminated within a 0.5-second test deadline,
  without waiting for an 8192-byte chunk. Child is reaped. Five related tests passed;
  full SQLite suite 61 tests, 2 PostgreSQL-only skips, no failures.
- Ruling: provider I/O is isolated in a short-lived spawned process — Requests read
  timeout bounds inactivity rather than total wall time — deployment needs child-process
  support and bears process startup overhead; without it stalled streams could exhaust workers.
- Final: minor (deferred): unsupported-condition clarification remains a generic safe
  message rather than condition-specific guidance. It still prevents product searching
  with unsupported constraints; improving the wording is deferred.

## Rulings on review limitations

- Final: Ruling: Gemma interpretation fidelity still needs live prompt evaluation —
  schema tests cannot prove semantic preservation — unsupported conditions could be
  missed by the model despite the clarification instruction.
- Final: Ruling: keep optional filter fields with strict JSON Schema — no incompatibility
  was demonstrated for the selected endpoint — an endpoint rejection remains possible
  until a live OpenRouter request verifies provider support.
- Final: Ruling: final marketplace integration remains an explicit dependency handoff —
  actual marketplace models/routes are absent — fixture success does not prove deployment
  integration with another team's implementation.
- Final: Ruling: broker recovery is independently verified below; paid OpenRouter remains
  uncalled — no production API key was supplied for a live evaluation — provider-side
  behavior and model quality remain unverified.
- Final: Ruling: exactly-once provider calls remain outside the approved guarantee —
  lease fencing protects stored results, not an external paid call — a crash can incur
  a duplicate API charge before a terminal result is committed.

## Live infrastructure smoke

An owned, labeled temporary RabbitMQ 4 container on localhost:56739 and an isolated
PostgreSQL 16 cluster under `/tmp` were used, without modifying existing services.
The real coordinator, real Pika transport, real thread pool and real job database
processed fixture-service jobs (not a live LLM call):

1. Broker healthy: four jobs completed, measured peak concurrency four.
2. The test broker was stopped: three durable jobs completed through serial fallback.
3. The same broker was restarted: healthy pool recovered; all nine jobs completed,
   exactly nine fixture-service calls. This test does not establish exactly-once API
   delivery under every possible crash boundary.

The actual worker management command was also exercised with `--once` and no broker.

## Final verification

- PostgreSQL final complete suite: 61/61 passed, including both real race tests and
  both real-socket provider deadline regressions.
- SQLite final complete suite: 61 discovered, 59 passed and 2 PostgreSQL-only tests
  skipped, no failures.
- Django system check: no issues. Migration dry run: no changes detected.
- Ruff check for changed LLM code: passed (original admin stub excluded).
- Ruff format --check: 35 files already formatted.
- Tailwind CSS build, node --check and git diff --check: passed.
- Existing staticfiles-directory warning is inherited from the baseline; no test failure.
- No paid OpenRouter call or final marketplace end-to-end integration was claimed.

## Preserved commit checkpoints

| Task | RED | GREEN | REFACTOR |
| --- | --- | --- | --- |
| Filters/adapter | 5ea27fa | d23630d | a55167d |
| OpenRouter/grounding | 9b86b59 | bbd2175 | 5ab4efd |
| Durable jobs | a2c45c8 | bbbbb4a | ca0b1da |
| Login/API/UI | ad0f316 | 8d1eaf1 | 7172589 |
| RabbitMQ/recovery | 7ed90f0 | 13a4e34 | ac5bd81 |
| Schema regression | b53ac44 | e14a922 | included in green |
| Provider deadline | f1fb4f6 | f8d0f4c | included in green |

All original worktree commit IDs remain ancestors of the current feature branch.

## Follow-up recovery and search robustness

The requested earlier prompt changes were found in stash object
`bb8297df37760c942ccb737660e39a3a1fa9b5a6` (also present in the older stash
`981927e686caf17bce5151bd9e4b2e210b67da0b`). Recovery copied only the extraction
implementation and its related tests; no stash was popped or deleted. The saved
marketplace-aware test fixture was recovered from
`520611852140371a54d64eb9655a7654ce3f1dc9` to keep post-rebase tests compatible.

Before the fix, all three new live regression cases returned needs_clarification:
cheapest vegetables, a misspelled tomato/location with an explicit budget, and a
misspelled category. Service regressions also failed because model ranking could
reverse explicit price ordering or exclude the cheapest candidate.

The restored instructions now recognize category-only recommendations, convert
cheapest/most-expensive wording into supported sorting, and normalize obvious
typos without inventing a budget or changing explicit numeric constraints. Absent
preferences retain neutral values. Ambiguous and unsupported constraints still
require clarification. The price-sorted database candidates now remain authoritative
for both order and membership through the suggestion stage.

Focused offline verification: 19 tests passed. Six live Gemma cases passed,
covering the original simple search, price/location preservation, unsupported
quantity budgets, cheapest recommendations, and product/category/location typos.
Additional unseen-typo and actual seeded-database pipeline checks are recorded in
the follow-up verification result. No API keys or raw provider responses were logged.

Follow-up verification result:

- Full suite: 185 tests, 176 passed and 9 skipped (7 opt-in live checks and 2
  PostgreSQL-only checks); no failures.
- Live extraction: 7/7 passed, including the unseen typo `sayruan paling murha`.
- Actual seeded-database pipeline: cheapest vegetables began with Kangkung
  Hidroponik at Rp8.000, followed by prices 9.000, 12.000, 25.000 in order.
- Actual typo pipeline: `tomta di dpok maksimal 30 ribu` became keyword `tomat`,
  location `Depok`, max_price 30000 and returned Tomat Cherry Organik.
- The recommendation suggestion stage fell back safely; a separate diagnostic
  confirmed the provider exceeded the existing 35-second deadline. Database
  results and deterministic explanations remained available and correctly sorted.
  The tomato typo pipeline completed without degradation. Provider latency is
  not claimed fixed by these prompt changes; deadlines and safety checks remain.
- Ruff, formatting, Django checks, migration dry run and whitespace checks passed.
- All three original stash objects remain unchanged. The user subsequently
  requested a refactor commit for this follow-up; the active worker needs a restart
  to load the updated prompt.

Temporary RabbitMQ container removed after verifying its ownership label; isolated
PostgreSQL cluster stopped. Existing host services were left running unchanged.
