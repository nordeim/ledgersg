# LedgerSG — Remediation Report (P31 Sprint: The B904 Raise-From Closure + The Tests-Tree Mechanical Extension + The Unified Closed-Class Ratchet)

**Date:** 2026-11-28 (session 59)
**Base commit:** `933af819` (main — post-P30 + the session-58/59 logs)
**Plan:** `docs/REMEDIATION_PLAN_2026-11-28_P31.md` (validated against the codebase before execution — every anchor hand-verified; the baseline reproduced ALL documented gates exactly this session, including the live e2e 43/43 on the first run)
**Method:** TDD (RED → GREEN → full gate) for the chaining contract; the reviewed lint batches verified by per-phase diffs + the full test matrix + the live contract re-verification; `skills/` excluded from all checks/tests/compilation; no schema changes (v1.2.2 carries forward); no frontend component changes (the web tree is untouched).

---

## 1. Verification Ledger (executed evidence)

| Gate | Result | Confidence |
|---|---|---|
| Baseline reproduction (pre-change) | backend **1030P/0F/5S** (30.01s) · vitest **698/698 (85 files)** (107.96s) · tsc 0 · whole-tree eslint **0E/0W** · live `test:e2e:full` **43/43 (2.3m, deterministic, first run)** · `rls_smoke.py` **13/13 as `ledgersg_app`** · `mobile-nav-audit.js` **17/17** (the thirtieth settlement) · the `translate` probe **PASS** (7 mid-flight samples) · `npm audit` **0 across dev+prod** · `build:server` green + `prod-csp-smoke.js` **5/5** · `make lint-mechanical` exit 0 · the production ruff count **277** exact | Verified |
| The environment | rootless PG 17 on :5432 (both DBs present, schema verified), Redis on :6379, the venv, node_modules, `next dev` on :3000 — **no repair required this session** (the backends re-daemonised via `scripts/daemonize.py`, surviving the shell-call boundary) | Verified |
| The named focus — the mobile-nav verdict | **WORKING as expected; NO remaining TailwindCSS v4 bug on this surface** (the thirtieth pre-change settlement + the thirty-first post-change settlement; the `translate` probe re-PASS both times) | Verified |
| RED: the chaining spec on base code | NEW `tests/integration/test_exception_chaining_p31.py` (4 gates): **all four failed for exactly the right reason** — `__cause__` None on the two service seams (`DocumentService.get_document`, `ReconciliationService.get_transaction`), `__cause__` None on the serializer seam (`BulkAllocationSerializer.validate_allocations`), `__suppress_context__` False on the deliberate-suppression seam (`decimal_utils.money`) | Verified |
| GREEN: the H1 fix | The 66 B904 sites chained: **62 `from exc`** + **4 `from None`** (the classified review, §2) — applied by a string-aware statement-end scanner (`scripts/p31_apply_b904.py`, outside the repo); 6 lines the suffix pushed past E501 were hand-wrapped (the raise-line-only diffs reviewed); **4/4 GREEN** | Verified |
| The B904 class closure | `ruff check --select B904 apps/ common/ config/` → **"All checks passed!"**; the whole-tree production count **277 → 211** (the arithmetic exact: no new findings — the 6 E501 overflows fixed by wrapping); `compileall` clean | Verified |
| The tests-tree mechanical closure | W293 **99 → 0** (safe-fixed; `git diff -w` proves pure whitespace) · I001 **56 → 0** (+4 re-sorts after the F401 edits — the P30 lesson applied) · F401 **66 → 0** (every site reviewed by name: models/stdlib/test-helpers only, **no import-is-the-side-effect class**; the full suite is the arbiter) — tests tree **379 → 157** (one F811 rode along with the import cleanup — honest note: the redefined-import the F401 removal retired) | Verified |
| The full backend suite | **1034 passed / 0 failed / 5 skipped (29.94s)** — the 1030 existing pins hold unchanged; +4 the new chaining gates | Verified |
| The full web matrix | vitest **698/698 (85 files)** · tsc 0 · whole-tree eslint **0E/0W** · `npm audit` **0 across dev+prod** (web tree untouched) | Verified |
| The live gates (both backends restarted on the remediated code first) | live `test:e2e:full` **43/43 (2.3m)** · `rls_smoke` **13/13 as `ledgersg_app`** (against the restarted :8001 RLS instance) · `mobile-nav-audit.js` **17/17** (the thirty-first settlement) · the `translate` probe re-PASS · `build:server` green + `prod-csp-smoke.js` **5/5** | Verified |
| The live API contract re-verification | the not-found document detail → **404 with the exact documented body** `{"error":{"code":"not_found","message":"Document <uuid> not found"}}`; the allocation typed-400s → `{"payment_id":["Payment not found in this organisation."]}` (the nonexistent-payment path) and `{"allocations":["Invalid allocated_amount: garbage"]}` (the money-parse path — the exact seam the T2 gate pins) — **byte-stable under the chaining closure** | Verified |
| The unified ratchet | `make lint-mechanical` exit 0 on the unified command (`W291,W293,I001,F401,F403,F405,B904` over `apps common config tests`, run with the venv on PATH; the recipe line byte-verified to carry its TAB — the P30 Makefile lesson); the same command as the CI `backend-tests` step; the ci.yml YAML valid; the ci.yml header counts updated (1034) | Verified |
| Screenshots | 8 captures (`200-207_*_session59.png`), md5-unique, DOM-truth-asserted per surface (the banking payments tab — the P31 headline surface, the allocation typed-400 seam — + the invoice detail, the invoices list, the ledger, the banking transactions tab, the dashboard, the mobile drawer closed/open) + non-blank pixel-verified (variance 566.7–935.2, threshold 30; `scripts/verify-screenshots-session59.py`) | Verified |
| The `.env.example`s | the config-readers sweep re-run: all 17 backend settings vars documented (incl. `DJANGO_SETTINGS_MODULE` as process-env); the web tree reads exactly `NEXT_PUBLIC_API_URL` + `NEXT_OUTPUT_MODE` — **truthful, no changes required** (no new env vars this sprint) | Verified |

## 2. What changed (66 chaining edits across 21 production files + the tests-tree mechanical batch across ~40 test files + 2 config files + 1 spec file, no schema, no frontend components)

1. **The B904 closure (21 production files):** 62 sites gain `from exc` (or the file's existing binding name — every lookup-miss translation, the 5 IntegrityError race translations, the 2 password propagations, the ISO-date + value-parse translations, the 3 Celery `self.retry` sites; the unbound `except X:` clauses gain `as exc`); 4 sites gain `from None` (`common/decimal_utils.py` ×3, `reconciliation_service.py`'s CSV decode — the messages already embed the original error's string). Six lines the suffix pushed past E501 were hand-wrapped (raise-line-only diffs).
2. **Tests:** NEW `tests/integration/test_exception_chaining_p31.py` (4 gates: the Class-A service seam ×2, the Class-A serializer seam, the Class-B suppression seam).
3. **The tests-tree mechanical batch:** W293 ×99 + I001 ×60 (incl. the re-sorts) + F401 ×66 (reviewed) across ~40 test files.
4. **Config:** the `Makefile` `lint-mechanical` target selects `W291,W293,I001,F401,F403,F405,B904` over `apps common config tests` (tab-safe scripted edit; byte-verified) + the help line; **`.github/workflows/ci.yml`** — the unified gate step + the header counts (1034).
5. **Docs:** README (badge 1775, the status rows, the P31 milestone, the suite table), CLAUDE 2.32.0, AGENTS (the header truth block + 2 new P31 lessons), SKILL 2.18.0, PAD 3.21.0, DEPLOYMENT (the header re-verification), the API guide (the P31 re-verification note — no API changes), ci.yml.
6. **Scripts:** `scripts/capture-screenshots-session59.js` (the 8-shot capture), `scripts/verify-screenshots-session59.py` (the pixel verification).

## 3. The closure verdict (the headline)

**The registered 66-site B904 batch — the P30 report's own suggested next sprint — is closed, and the exception-chaining contract is now explicit, classified, and gated.** Every raise-inside-except on the production tree renders as "The above exception was the direct cause of the following exception" (62 `from exc` sites) or deliberately suppresses a redundant context (4 `from None` sites whose raised message already embeds the original error's string). The chain is a contract, not an accident of where the raise sits: a future refactor that moves a raise out of its except block keeps the `__cause__` it now declares, where the implicit `__context__` would have silently dropped. The response bytes never changed — pinned three ways: the 1030 existing contract tests, the e2e 43/43, and the live not-found/typed-400 re-verification. And the whole-tree closed-class set (the P30 four + B904 + the tests-tree extension) now sits behind ONE gate — `make lint-mechanical` + the CI step — so none of it can silently regress.

## 4. Audit of recent changes (Mode C, static + executed)

- The P30 slice re-audited this session (hand-verified in source): both locked fetches chain `select_for_update().select_related("bank_account")` with the contract comments, the per-file-ignores block, the `lint-mechanical` target + CI step, the query-count spec — **0 new findings**. One log-level false alarm investigated and cleared (a `SyntaxWarning` for `contact_service.py:284` in the appended `/tmp/be8000.log` came from a PRE-P30 boot; the current source compiles clean under `-W error::SyntaxWarning`).
- The companion sweep (the exception-handling surfaces): the 4 S110 try-except-pass sites re-verified as the registered fail-closed designs; the one BLE001 broad catch is noqa'd with the logging contract; the existing raise-from exemplars established the convention this sprint codified.
- The named focus — the mobile-nav verdict (thirtieth/thirty-first settlements): **working as expected; no remaining Tailwind v4 bug**.
- The standing test-suite task (vitest + playwright configs): verified IN PLACE and current — this sprint adds the backend chaining specs to the same suites.
- `npm audit`: **0 across dev+prod** (re-verified). The tests tree residual: **157 findings** (E501×73, F811×26, F841×9, S106×8, SIM117×8, C408×7, B007×6, E741×4, F821×2 [the verified-inert string-annotation nits], S108×2, …) — registered follow-up.

## 5. Remaining / deferred (explicit, registered in the plan's §4)

The ruff semantic batch — now **211 production findings** (B904's 66 closed): UP045/UP006/UP007/UP035×109 (typing modernization; leans on a mypy gate that itself carries 1491 errors), E501×39 + `ruff format` (80 files would reformat — the `make format` axis), F841×16, E402×12 (the deliberate end-of-file circular-avoidance imports), SIM105×7, B009×6, S110×4 (the verified fail-closed XSD loads), A001/E741/N806×6, B017/B905/F402/N802×4. The tests/-tree residual — **157 findings** (E501×74→73, F811×27→26, F841×9, S106×8, SIM117×8, C408×7, B007×6, E741×4, F821×2, S108×2, …). The `/accounts/search/` limit-contract migration (verified again: capped + typed; no frontend consumer); the capped-default flip; the audit-log INSERT policy (DDL); BE-L3/BE-L4 locking; the CSV errors[] strings; dead-letter design; UEN checksum; the NULL-context SELECT tradeoff; H-05b models; PaymentsTab prefill; the TanStack incompatibility; the membership-cache window; the P20-era FE-M2/M3 designs; CI hardening (the mypy gate); the version-story reconciliation — the P21–P30 deferred registers carry forward unchanged.

## 6. Confidence labels

- **Verified:** every row in §1 (executed and observed in this session, on this tree — including the RED→GREEN transition, the per-class closure counts, the full matrix on the remediated code, and the live contract re-verification).
- **Reasoned:** the no-regression claim for untouched surfaces (the full matrix green; `git status` shows only the intended files).
- **Assumed:** none material.
- **Unverifiable here:** none.
