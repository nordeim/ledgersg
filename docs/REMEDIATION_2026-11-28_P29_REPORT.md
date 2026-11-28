# LedgerSG — Remediation Report (P29 Sprint: The Detail-View N+1 Closure + The Per-Glob Coverage Ratchet Raise + The Missing shared Tier)

**Date:** 2026-11-28 (session 55)
**Base commit:** `6f398bf3` (main — post-P28 + the session-54/55 logs)
**Plan:** `docs/REMEDIATION_PLAN_2026-11-28_P29.md` (validated against the codebase before execution — every anchor hand-verified; the baseline reproduced ALL documented gates exactly this session, including the live e2e 43/43 on the first run)
**Method:** TDD (RED → GREEN → full gate) for every behavioural change; eslint parity on touched files; `skills/` excluded from all checks/tests/compilation; no schema changes (v1.2.2 carries forward); no frontend component changes (the one web-tree delta is the coverage-ratchet config); the response bytes pinned byte-identical by design (select_related/prefetch_related change HOW rows travel, not WHAT the serializer emits).

---

## 1. Verification Ledger (executed evidence)

| Gate | Result | Confidence |
|---|---|---|
| Baseline reproduction (pre-change) | backend **1025P/0F/5S** (28.79s) · vitest **698/698 (85 files)** (107.20s) · tsc 0 · whole-tree eslint **0E/0W** (from `apps/web`) · live `test:e2e:full` **43/43 (2.4m, deterministic, first run)** · `rls_smoke` **13/13 as `ledgersg_app`** · `mobile-nav-audit.js` **17/17** (the twenty-sixth settlement) · the dedicated Tailwind v4 `translate` probe (`scripts/translate-probe-session53.js`): **PASS** (7 mid-flight samples, closed `-100%`/hidden → open `0px`/`role="dialog"` → Escape closes) · `npm audit` **0 across dev+prod** | Verified |
| The environment | rootless PG 17 on :5432 live, Redis on :6379, the dev stack (:8000 health 200, :8001 health 200, :3000 `next dev`) — **no repair required this session**; both backends restarted on the remediated code before the live gates (the §12.4 RLS instance run as `ledgersg_app` via the DB_* env overrides) | Verified |
| The named focus — the mobile-nav verdict | **WORKING as expected; NO remaining Tailwind v4 bug on this surface** (the twenty-sixth pre-change settlement + the twenty-seventh post-change settlement; the `translate` probe re-PASS both times) | Verified |
| RED: the query-count spec on base code | NEW `tests/integration/test_detail_query_counts_p29.py` (3 gates, one per surface): **all 3 failed for exactly the right reason** — the document detail walked `coa"."account` 3 times on a 3-line document (the assertion output shows the three separate SELECTs), the journal entry detail the same 3 walks, the payment fetch was single-table with the contact riding its own walk | Verified |
| GREEN: the fixes | `DocumentService.get_document` → `.select_related("contact").prefetch_related(Prefetch("lines", queryset=InvoiceLine.objects.select_related("account", "tax_code")))`; `JournalService.get_entry` → `.prefetch_related(Prefetch("lines", queryset=JournalLine.objects.select_related("account")))`; `PaymentService.get` → `.select_related("contact", "bank_account")` — no `order_by` on any prefetch (the related manager's default order is the serialized-line contract; the bytes cannot change) — **3/3 GREEN** | Verified |
| The full backend suite | **1028 passed / 0 failed / 5 skipped (30.20s)** — the 1025 existing pins (the P24/P25/P26/P28 envelope + query-level contracts, the service tests, the RLS gates) hold unchanged; +3 the new query-count gates | Verified |
| The per-glob ratchet raise | `vitest.config.ts` — lib **71/52/74/73 → 73/54/78/75**, hooks **52/47/36/52 → 55/47/51/55** (branches 36 → 51: the 15-point rubber stamp closed), app **73/64/71/73 → 75/65/73/76**, components **82/74/68/83 → 83/76/69/84**, providers **61/60/58/60 → 63/63/58/62** (statements/functions/branches/lines), + the NEW **`src/shared/**` tier at 73/62/76/73**; `npm run test:coverage` **exit 0** at the raised floors | Verified |
| The full web matrix | vitest **698/698 (85 files)** · coverage exit 0 at the RAISED per-glob ratchets · tsc 0 · whole-tree eslint **0E/0W** · live `test:e2e:full` **43/43 (2.3m)** (both backends restarted on the remediated code first) · `build:server` green · `prod-csp-smoke.js` **5/5** · `npm audit` **0 across dev+prod** | Verified |
| The live gates | `rls_smoke` **13/13 as `ledgersg_app`** (against the restarted :8001 RLS instance) · `mobile-nav-audit.js` **17/17** (the twenty-seventh settlement) · the `translate` probe re-PASS | Verified |
| The API contracts re-verified live (the byte-identical proof) | the document detail payload (lines with `account_code`/`tax_code_code`, the nested contact, the totals — `4100`/`SR`/`Demo Trading Pte Ltd` on the demo substrate); the payment detail payload (`contact_name`, `bank_account_name`, the allocations array); the contacts envelope `?limit=1` → count 2 (the TOTAL) + 1 row + next carrying offset=1 | Verified |
| Screenshots | 8 captures (`184-191_*_session55.png`), md5-unique, DOM-truth-asserted per surface (the invoice detail page — the P29 headline surface — + the pushed-down lists, the ledger, the mobile drawer closed/open) + non-blank pixel-verified (variance 485.3–929.8, threshold 30; `scripts/verify-screenshots-session55.py`) | Verified |
| The `.env.example`s | the config-readers sweep re-run: the 16 backend settings vars all documented; the web tree reads exactly `NEXT_PUBLIC_API_URL` (+ the build-script `NEXT_OUTPUT_MODE`) — **truthful, no changes required** (no new env vars this sprint) | Verified |

## 2. What changed (3 services + 1 spec file + 1 config, no schema, no frontend components)

1. **`apps/backend/apps/invoicing/services/document_service.py`** — `get_document` gains the bounded-fetch contract (the `Prefetch` import + the select_related/prefetch_related chain; the docstring-comment records the pre-P29 cost: a 5-line detail paid 14 queries).
2. **`apps/backend/apps/journal/services/journal_service.py`** — `get_entry` gains the lines-with-account prefetch (the `Prefetch` import).
3. **`apps/backend/apps/banking/services/payment_service.py`** — `PaymentService.get` gains `.select_related("contact", "bank_account")`.
4. **Tests:** NEW `tests/integration/test_detail_query_counts_p29.py` (3 gates, the `CaptureQueriesContext` pattern: the per-line tables fetched by ≤1 joined SELECT, the fixed related rows riding the main query, the payload counter-pins).
5. **`apps/web/vitest.config.ts`** — the five per-glob coverage tiers raised to their measured floors + the NEW `src/shared/**` tier.
6. **Scripts:** `scripts/capture-screenshots-session55.js` (the 8-shot capture), `scripts/verify-screenshots-session55.py` (the pixel verification).

## 3. The detail-N+1 verdict (the headline)

**A detail page now costs one detail, not one detail per line.** The P28 sprint closed the list-surface cost class (a page that fetched the whole table); the detail-surface sibling carried the same disease at the get-seam: three `get_*` service methods returned a plain `.objects.get(...)` while the serializers walked FKs — the invoice/quote detail walked **account + tax_code on every line** (a 5-line detail paid 14 queries where 3 would do, across 8 serialising call sites including the PDF context and the email/send payloads), the journal entry detail walked **account on every line** (the deferred register's "journal detail N+1"), the payment detail walked contact + bank_account on every serialisation. The response was correct at every line count — which is exactly why no existing test could see the cost (the bytes are identical whether the fetch is 3 queries or 14). This sprint closes the class at the source: the fixes land at the SERVICE seam (uniform, one gate per service, every serialising consumer benefits), the prefetches carry no `order_by` (the related manager's default order is the serialized-line contract), and the query-count gates pin it — a detail request MUST issue a bounded, line-count-independent set of SELECTs. The RED runs prove the gates bite: on the base code, all three failed showing the per-line walks.

## 4. Audit of recent changes (Mode C, static + executed)

- The P28 slice re-audited this session (hand-verified in source): the four lazy querysets, the `.count()` views, the raised whole-suite ratchet, the dependency closure — **0 new findings**.
- The same-class sweep (every serializer field with nested `source="fk.field"` access, every service `get`): the three fixed surfaces are the complete set — the banking/core/gst/coa/peppol serializers carry no nested-source walks (the payment allocation serializer's `document` walk was already covered by `get_allocations`' `select_related("document")`); the journal LIST serializer reads only the prefetched lines' debit/credit (no account walk); the GST returns and COA accounts lists are bounded domains without pagination contracts (by design).
- The named focus — the mobile-nav verdict (twenty-sixth/twenty-seventh settlements): **working as expected; no remaining Tailwind v4 bug**.
- CFG-P29-M2: the per-glob tiers sat at their P20-measured values (the hooks branches floor 15 points below the truth) — raised this sprint; the `src/shared/**` tier gap closed with it (the P20 blind-spot class).
- The standing test-suite task (vitest + playwright configs): verified IN PLACE and current — this sprint adds the backend query-count specs to the same suites.
- `npm audit`: **0 across dev+prod** (carried from P28, re-verified this session). Ruff re-measured: ~1307 whole-tree / 928 production findings (the registered deferred mechanical batch; NOT a CI gate).

## 5. Remaining / deferred (explicit, registered in the plan's §4)

The `/accounts/search/` limit-contract migration (verified again: no frontend consumer); the capped-default flip; the ruff mechanical batch (928 production findings; `make lint` convenience only — the F405 star-import usage makes blind `--fix` unsafe, so it stays a dedicated reviewed sprint); the audit-log INSERT policy (DDL); BE-L3 config-class locking; BE-L4 Peppol log-state locking; CSV errors[] raw strings; dead-letter design; UEN checksum; NULL-context SELECT tradeoff; H-05b models; PaymentsTab prefill; TanStack incompatibility; the membership-cache window; the P20-era FE-M2/M3 designs; CI hardening; the version-story reconciliation — the P21/P23/P24/P25/P26/P27/P28 deferred registers carry forward unchanged.

## 6. Confidence labels

- **Verified:** every row in §1 (executed and observed in this session, on this tree — including the RED→GREEN transitions, the raised-ratchet coverage exit 0, the full matrix on the remediated code, and the byte-identical live API contracts).
- **Reasoned:** the no-regression claim for untouched surfaces (the full matrix green; `git status` shows only the intended files).
- **Assumed:** none material.
- **Unverifiable here:** none.
