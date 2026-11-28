# LedgerSG — Remediation Report (P28 Sprint: The SQL-Level Push-Down for the Service-Driven Lists + The Honest Ratchet + The Dev-Tier Dependency Closure)

**Date:** 2026-11-28 (session 53)
**Base commit:** `ad8b3b47` (main — post-P27 + the session-53 narration log)
**Plan:** `docs/REMEDIATION_PLAN_2026-11-28_P28.md` (validated against the codebase before execution — every anchor hand-verified; the baseline reproduced ALL documented gates exactly this session, including the live e2e 43/43 on the first run)
**Method:** TDD (RED → GREEN → full gate) for every behavioural change; eslint parity on touched files; `skills/` excluded from all checks/tests/compilation; no schema changes (v1.2.2 carries forward); no frontend component changes (the web-tree deltas are the coverage-ratchet config + the dev-tier dependency bump).

---

## 1. Verification Ledger (executed evidence)

| Gate | Result | Confidence |
|---|---|---|
| Baseline reproduction (pre-change) | backend **1021P/0F/5S** (30.15s) · vitest **698/698 (85 files)** (108.22s) · tsc 0 · whole-tree eslint **0E/0W** (from `apps/web`) · live `test:e2e:full` **43/43 (2.2m)** · `rls_smoke` **13/13 as `ledgersg_app`** · `mobile-nav-audit.js` **17/17** · the dedicated Tailwind v4 `translate` probe (`scripts/translate-probe-session53.js`, this session): closed `-100%`/hidden → **7 mid-flight samples** (`-96.72% → -1.66%`) → open `0px`/`role="dialog"` → Escape closes; `transitionProperty: "transform, translate, visibility"` · `npm audit` **0 critical** (17 dev-tier: 2 low / 8 moderate / 7 high — all verified dev-only: `undici` via jsdom, `vite` via vitest/`@vitejs/plugin-react`, none in `dependencies`) | Verified |
| The environment | rootless PG 17 on :5432 live (both databases loaded; `ledgersg_dev` 36 tables across the per-app schemas), Redis on :6379, the dev stack (:8000, :8001, :3000) — **no repair required this session** (`ledgersg_app` authenticates at the documented default; the backend suites reproduced exactly) | Verified |
| RED: the push-down spec on base code | NEW `tests/integration/test_pagination_pushdown_p28.py` (4 gates, one per surface): **all 4 failed for exactly the right reason** — the assertion output shows the row-fetch SELECT on each surface's table WITHOUT a LIMIT (e.g. `SELECT "invoicing"."contact"."id", ... ` unbounded) and no COUNT query; the envelope counter-pins were structurally unreachable behind the first failing assert | Verified |
| GREEN: the fixes | the four services return lazy querysets (`contact_service.list_contacts`, `document_service.list_documents`, `payment_service.list`, `reconciliation_service.list_transactions` — the `list(...)` materialisations dropped, the `select_related`/`order_by` chains carried, the return annotations updated to `QuerySet[T]`); the four views count via `.count()` (`invoicing/views.py` ×2, `banking/views.py` ×2 — `len(x)` → `x.count()`; the queryset slice renders SQL LIMIT/OFFSET at the serializer iteration) — **4/4 GREEN** | Verified |
| The full backend suite | **1025 passed / 0 failed / 5 skipped (28.92s)** — the 1021 existing pins (the P24/P25/P26 envelope contracts, the service-level `len()`/indexing tests, the RLS gates) hold unchanged; +4 the new query-level gates | Verified |
| The coverage ratchet | `vitest.config.ts` whole-suite thresholds raised **71/60/68/71 → 73/62/70/73** (lines/functions/branches/statements — the measured floor 73.39/70.72/62.38/73.95); `npm run test:coverage` **exit 0** at the raised floor (the measured values re-printed identical) | Verified |
| The dependency closure | `npm audit fix` applied the dry-run set exactly (in-range semver bumps only: `@typescript-eslint/*` 8.56.1→8.74.0, `vite` 7.3.1→7.3.8, `undici` 7.22.0→7.30.2 via jsdom, `minimatch`→11.0.9, `brace-expansion`, `js-yaml`, `flatted`, `picomatch`, `browserslist`, `semver`, `ignore`, the `@babel/*` toolchain); **`npm audit` now 0 across dev+prod** (`--omit=dev` was already 0 before) | Verified |
| The full web matrix on the bumped tree | vitest **698/698 (85 files)** · coverage exit 0 at the RAISED ratchet · tsc 0 · whole-tree eslint **0E/0W** · live `test:e2e:full` **43/43 (2.3m)** (both backends restarted on the remediated code first) · `build:server` green · `prod-csp-smoke.js` **5/5** (nonce + hydration + zero violations) | Verified |
| The live gates | `rls_smoke` **13/13 as `ledgersg_app`** (against the restarted :8001 RLS instance) · `mobile-nav-audit.js` **17/17** (the twenty-fifth settlement) · the `translate` probe re-PASS (7 mid-flight samples) | Verified |
| The API contracts re-verified live (the byte-identical proof) | contacts mid-set `?limit=1` → count 2 (the TOTAL) + 1 row + next carrying offset=1; the beyond-end page → count 2 + 0 rows + previous present; payments + bank-transactions → `{count, next, previous, results}` with the total counts; the invoices page 2 `?limit=20&offset=20` → count 23 + the last 3 rows + next null; `?offset=` without `?limit=` → **400**; `?limit=abc` → **400**; the unpaginated path → the byte-identical `{results, count}` | Verified |
| Screenshots | 8 captures (`176-183_*_session53.png`), md5-unique, DOM-truth-asserted per surface (the four pushed-down list surfaces incl. the quotes page [fodder stocked through the public API, the P26 convention — the demo substrate had 0 quotes after the e2e runs] + the invoices page 2 held past the old race window + the mobile drawer closed/open) + non-blank pixel-verified (variance 368.8–960.5, threshold 30; `scripts/verify-screenshots-session53.py`) | Verified |
| The `.env.example`s | the config-readers sweep re-run: the 16 backend settings vars all documented (the `config()` reads in `config/settings/*` all present in `apps/backend/.env.example`); the web tree reads exactly `NEXT_PUBLIC_API_URL` (+ the build-script `NEXT_OUTPUT_MODE`) — **truthful, no changes required** (no new env vars this sprint) | Verified |

## 2. What changed (4 services + 2 views + 1 spec file + 1 config + the lockfile, no schema, no frontend components)

1. **`apps/invoicing/services/contact_service.py`** — `list_contacts` returns the lazy queryset (the `list(...)` dropped; the return annotation `List[Contact]` → `QuerySet[Contact]`; the docstring records the lazy contract).
2. **`apps/invoicing/services/document_service.py`** — `list_documents` the same (the `select_related("contact")` chain carried).
3. **`apps/banking/services/payment_service.py`** — `list` the same (the `select_related("contact", "bank_account")` chain carried).
4. **`apps/banking/services/reconciliation_service.py`** — `list_transactions` the same (the `select_related("bank_account")` chain carried).
5. **`apps/invoicing/views.py`** + **`apps/banking/views.py`** — the four list views: `len(x)` → `x.count()` (SQL COUNT(*)); the existing `x[offset : offset + limit]` slice now renders SQL LIMIT/OFFSET (a queryset slice); the unpaginated path unchanged.
6. **Tests:** NEW `tests/integration/test_pagination_pushdown_p28.py` (4 gates, the `CaptureQueriesContext` pattern: the LIMIT-bounded SELECT at the requested page size + the COUNT(*) query + the envelope counter-pin, per surface).
7. **`apps/web/vitest.config.ts`** — the whole-suite coverage ratchet raised to the measured floor (the honest-ratchet fix).
8. **`apps/web/package-lock.json`** — the dev-tier dependency closure (`npm audit fix`; `package.json` itself unchanged — every bump is a transitive in-range resolution).
9. **Scripts:** `scripts/translate-probe-session53.js` (the dedicated Tailwind v4 probe, this session), `scripts/capture-screenshots-session53.js` (the 8-shot capture), `scripts/verify-screenshots-session53.py` (the pixel verification).

## 3. The push-down verdict (the headline)

**A list page now costs one page, not one table.** The P24 sprint shipped the `?limit=&offset=` envelope and (on the ledger and the Peppol log) the SQL-level paging with it — but the four service-driven surfaces (contacts, documents [invoices AND quotes], payments, bank transactions) materialised the entire filtered set in Python and sliced the list in the view: every 20-row page of an organisation with N documents fetched all N rows, instantiated N models, and joined the related rows for all of them. The response was correct at every size — which is exactly why no envelope-level test could see the cost (the bytes are identical whether the fetch is 20 rows or 20,000). This sprint closes the class at the source: the services return lazy querysets, the views count via SQL `COUNT(*)` and page via SQL `LIMIT/OFFSET`, and the query-level gates (`CaptureQueriesContext`) pin it — a paginated request MUST issue a LIMIT-bounded SELECT at the requested page size and a COUNT query. The RED runs prove the gates bite: on the base code, all four failed showing the unbounded SELECT.

## 4. Audit of recent changes (Mode C, static + executed)

- The P27 slice re-audited this session (hand-verified in source): the timer-callback value-change compare, the render-time org resets on all five surfaces, the filters-prop identity resets with the stable `NO_FILTERS` default — **0 new findings**. The same-class sweep (every `setOffset(0)` + every debounce timer in the web tree) found no remaining surface (the ledger has no search; the contact-picker's debounce sets only the query value).
- The named focus — the mobile-nav verdict (twenty-fourth/twenty-fifth settlements): **working as expected; no remaining Tailwind v4 bug** (the dedicated probe: 7 mid-flight `translate` samples, the transition list carries the standalone property, the closed/open/Escape contract holds).
- The honest-ratchet finding (CFG-M2): the config-vs-measured gap was 2+ points across all four whole-suite metrics — raised and re-gated this sprint. The per-glob tier floors remain at their P20 values (all passing; raising them needs the per-glob measured numbers from the JSON report — registered as follow-up).
- `npm audit`: **0 across dev+prod** (was 17 dev-tier; the production set was already clean and stays clean).

## 5. Remaining / deferred (explicit, registered in the plan's §4)

The per-glob coverage-tier raise (new, follow-up of CFG-M2); the `/accounts/search/` limit-contract migration (verified this session: no frontend consumer — the invoice form uses the plain `/accounts/` list); the capped-default flip; the ruff mechanical batch (936 production findings); the audit-log INSERT policy (DDL); BE-L3 config-class locking; BE-L4 Peppol log-state locking; CSV errors[] raw strings; dead-letter design; UEN checksum; NULL-context SELECT tradeoff; H-05b models; PaymentsTab prefill; TanStack incompatibility; the membership-cache window; the journal detail N+1; the P20-era FE-M2/M3 designs; CI hardening; the version-story reconciliation — the P21/P23/P24/P25/P26/P27 deferred registers carry forward unchanged.

## 6. Confidence labels

- **Verified:** every row in §1 (executed and observed in this session, on this tree — including the RED→GREEN transitions, the raised-ratchet coverage exit 0, the 0-finding audit, the full matrix on the bumped tree, and the byte-identical live API contracts).
- **Reasoned:** the no-regression claim for untouched surfaces (the full matrix green; `git status` shows only the intended files).
- **Assumed:** none material.
- **Unverifiable here:** none.
