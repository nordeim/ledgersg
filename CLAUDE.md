# LedgerSG — Comprehensive Developer Briefing

> **Single Source of Truth** for coding agents and human developers
> **Version**: 2.30.0
> **Last Updated**: 2026-11-28
> **Status**: P29 Remediated 🟢 (the detail-view N+1 closure — the three detail seams (document detail, journal entry detail, payment detail) fetched their row with a plain `.objects.get(...)` while the serializers walked the related FKs per line / per related object: the invoice/quote detail walked account + tax_code on EVERY line (a 5-line detail paid 14 queries where 3 would do, across 8 serialising call sites incl. the PDF context), the journal entry detail walked account on every line (the registered "journal detail N+1"), the payment detail walked contact + bank_account. Fixed at the service seam (the same seam as the P28 list push-down): `get_document` selects the contact and prefetches the lines with account + tax_code in ONE joined SELECT; `get_entry` prefetches lines-with-account; `PaymentService.get` joins contact + bank_account — the payloads byte-identical, pinned by 3 NEW query-count gates (`tests/integration/test_detail_query_counts_p29.py`: the RED runs proved the 3-walks-on-a-3-line-document truth); the per-glob coverage ratchet raise (the five per-glob tiers raised at their measured floors — the hooks branches floor sat 15 points below the measured 51.16 — plus the NEW `src/shared/**` tier, closing the P20 blind spot); backend 1028P/0F/5S (+3); vitest 698/698 (85 files); e2e 43/43; rls 13/13; mobile-nav 17/17 (twenty-seventh settlement) + the translate probe re-PASS; build:server green + prod-CSP 5/5 — carries the P28 state forward (the SQL-level push-down — the four service-driven list surfaces (contacts, documents [invoices AND quotes], payments, bank transactions) materialised the ENTIRE filtered set in Python on every request (`return list(queryset...)`) and the views Python-sliced + `len()`-counted, so every 20-row page of an organisation with N documents fetched all N rows: the P24 envelope paged the RESPONSE, not the QUERY. Fixed: the services return lazy querysets; the views count via SQL COUNT(*) and page via SQL LIMIT/OFFSET — the envelope byte-identical, pinned by 4 NEW query-level gates (`tests/integration/test_pagination_pushdown_p28.py`: a paginated request issues a LIMIT-bounded SELECT at the requested page size + a COUNT query — the RED runs proved the unbounded fetch); the honest ratchet (the vitest whole-suite floor raised 71/60/68/71 → 73/62/70/73 at the measured value the P21–P27 reports recorded but never wrote into the config); the dev-tier dependency closure (the 17 npm-audit findings — 7 high, all verified dev-only — closed with in-range semver bumps; npm audit now 0 across dev+prod) — backend 1025P/0F/5S (+4); vitest 698/698 (85 files); e2e 43/43; rls 13/13; mobile-nav 17/17 (twenty-fifth settlement) + the translate probe re-PASS; build:server green + prod-CSP 5/5 — carries the P27 state forward (the pagination state-machine truth — the P26 search-debounce effect's MOUNT-run called setOffset(0) unconditionally, so a Next click inside the ~600ms window (doubled under StrictMode) was silently reverted to the cached page 1: no refetch, no feedback, the click lost — the serial full-run e2e lost this race deterministically (42/43 ×3) while isolation passed it; proven by trace (the click dispatched, the offset=20 request answered 200, then the UI back at page 1 with NO third request — the cache-served revert signature). Fixed: the page restart fires ONLY on a debounced VALUE CHANGE (the last-committed-value ref compared inside the timer callback — an event, never during render; a real search change still restarts, pinned); the org-switch offset reset extended to all five P26 surfaces (the P25/FE-L3 render-time pattern — the stale-offset fetch + garbage cache entry per switch closed); the banking filter-change offset reset (the render-time filters-prop identity compare, with a stable module-level NO_FILTERS default) — all pinned by real-hook transport-URL specs (the ledger-org-switch pattern; a module mock cannot observe a cache-served revert). 12 new vitest gates; backend untouched (1021P/0F/5S); vitest 698/698 (85 files); coverage floor RAISED to 73.39/70.72/62.38/73.95; e2e 43/43 deterministic + the fresh-DB first-run proof 43/43, 0 skipped — carries the P26 state forward (the frontend pagination wiring + the Peppol transmission-log contract — every remaining list surface (invoices, contacts, payments, bank-transactions, quotes) now pages server-side at size 20 through the shared `TablePagination` control with the page identity in each hook's queryKey (the cache-paging trap pinned per hook); the invoices search migrated server-side (debounced, the hook's `search` filter — the client-side filter only ever saw the fetched page); `useContacts` returns the full envelope (the count was previously discarded — the ContactPicker adapted); the P10/L-2 'Load more was doubly dead' debt retired with real controls; the Peppol transmission log (the last unbounded backend list) joined the `?limit=&offset=` contract with the `-transmitted_at, -id` tiebreaker and one conditional-aggregation counters query (byte-identical unpaginated); `page_envelope` gained the additive `extra` payload; the new `P26/FE-P1` e2e spec stocks its own fodder through the public API (count-driven DRAFT documents, idempotent, zero journal impact) — **proven: fresh DB → one bootstrap → the FIRST `test:e2e:full` = 43/43, 0 skipped** — carries the P25 state forward: the fresh-substrate first-run truth + the pagination contract hardening — the §9 bootstrap's silent invoice/credit-note breakage fixed (the line serializer has required `tax_code_id` since P14/M-4; the POSTs failed behind `|| true` guards and printed "invoice OK ()" with an empty id) with the SR tax code now on every substrate line and failures LOUD (exit 1), plus **step 4c the pagination fodder top-up** (a count-driven loop stocking ≥ 36 ledger lines and ≥ 4 APPROVED invoices — idempotent), proven end-to-end: drop/recreate the dev DB → one bootstrap run → the FIRST `test:e2e:full` = 42/42 with 0 skipped (the P20-era first-run promise restored); the int8 offset cap (a validly-typed offset > 2^63−1 was an untyped 500 on the ledger — now the typed 400 on every surface; `parse_int_param` gained `max_value`); `offset` without `limit` now the typed 400 (was silently ignored — explicit beats silent; no existing consumer sends the shape); the transactions surface joined the P24 test matrix (the coverage gap the P24 commit overstated); the WCAG 2.5.3 Label-in-Name pagination buttons ("Previous page"/"Next page" contain their visible text); the beyond-end page keeps its controls with the truthful "Showing 0–0 of N" (never a false "No journal entries yet" with no way back); the org-switch offset reset during render (the React prev-state pattern — the guarantee explicit rather than timing-emergent, pinned by a real-hook transport-URL spec) — carries the P24 state forward: the server-side list pagination — the registered big-ticket deferral shipped: the additive `?limit=&offset=` contract on the six core list surfaces (the general ledger at the SQL level — count() + the queryset slice; the entries, documents, contacts, payments and transactions lists at the envelope level), with the response byte-identical `{results, count}` when `limit` is absent (every existing consumer keeps working) and `{results, count, next, previous}` with `count` as the TOTAL matching rows when present; typed 400s on garbage limit/offset, the documented max 1000; the ordering tiebreakers on contacts/payments/transactions (`id` final key — a paginated page boundary must not skip or duplicate a tied row); the shared accessible TablePagination control + the useLedger page identity in the queryKey (the cache-paging trap) + the live paging e2e — carries the P23 state forward: the mobile-nav drawer-slide transition truth (Tailwind v4 animates `translate-x-*` through the standalone `translate` CSS property, and the drawer's `transition-[transform,visibility]` omitted it, so the 300ms slide never interpolated (the drawer snapped while every functional probe stayed green); fixed to `transition-[transform,translate,visibility]` and pinned by its own compiled-CSS gates: the `shell-drawer-transition` vitest spec + the `P23/FE-M1` e2e computed-style spec + the live mid-slide sampling proof + the vitest critical-advisory closure (^4.0.18 → ^4.1.12, the fixed 4.x line — both GHSA criticals closed, 0 critical remaining, the 17 residual findings all dev-tier) — carries the P21 state forward: the list-envelope unification ({results, count}) on every list surface — the pagination prerequisite, now consummated) + the InvoiceNow `invoicenow_sent_at` evidence stamp + the on-commit cache truth (void/manual-entry dashboard invalidation included) + the bank-account default-flag locks + the ValidateBalance typed-400 body + the banking a11y batch (the Reference name, the keyboard-reachable CSV import, the loader live regions, the payment-card keyboard contract, the reconcile aria-pressed) + the timezone-safe date helpers + the visible-label ContactPicker) — carries the P20 state forward: the void/transition/allocate lock completion + the CSV savepoint + magnitude bound + the posting-side cache invalidation + the e2e first-run truth + the raised coverage ratchet (the remove_line truth gap + the modal semantics + the ContactPicker + the route guard (statutory-record locking + the contrast debt + the Celery coverage completion: generate_f5/review_return locked with file_return; unallocate/unreconcile/convert/credit-cap/add_line locked; header/archived account posting refused; the three remaining Peppol task bodies under the RLS tenant context + the on-commit dispatch covered + terminal classification for deleted-org tasks; the email status gate; the bg-success/bg-alert contrast fixes (1.33:1 → 15.27:1) + the text-muted AA fix; tw-animate-css imported (the Radix animate utilities compiled to nothing in v4); the genuinely-shared uenSchema; the nested-Escape fix; the hooks-tier coverage floor; the CI no-backend e2e job; schema v1.2.2 §15c completion; carries the P17 state forward — the double-reversal / double-void / double-reconcile money-mutation races closed under row locks; the Celery tasks now dispatch on-commit and run inside the RLS tenant context in real workers; the 400-contract sweep — typed GST box parsing, bulk-allocation UUID field errors, UEN normalize-then-validate on org PATCH, tax-rate range, 6-dp exchange_rate; `/admin/` gated off outside DEBUG; the Django 6 STORAGES manifest migration; `select_related` on the three list services; the frontend contract batch — the `--color-success` token, the unsaved-changes beforeunload guard, the org-selector Radix menu contract, the shared `uenSchema`, redirect-carry, dead-CSP-origin removal, whole-tree eslint 0 errors; schema v1.2.2 §15c completion) — all gates green (backend 1009P/0F/5S, vitest 664/664, typecheck 0, eslint 0 errors/0 warnings, the coverage ratchet held at 71/60/68/71 with the app+providers tiers measured, build:server green; the live gates re-settled on the P25 tree: e2e 42P green including the fresh-DB first-run proof, rls_smoke 13/13, mobile-nav 17/17, prod-CSP smoke 5/5) — the P19 headline: remove_line locked + actually working (the P18 commit claimed the lock; the method also carried a FieldError), the unallocate lock re-order (the AB-BA deadlock), the archive-gate cache bypass, the create_entry sorted account locks, the return-periods savepoint, the status-task full tenant-context wrap, the journal prefetch, the five uuid route islands, the serializer tolerance alignment; the four banking modals are Radix Dialogs, the transaction row is keyboard-operable, the ContactPicker is a WAI-ARIA 1.0 combobox (the P16-era deferral closed), the in-app unsaved-work route guard ships, the enforced CSP reports to the tested endpoint, the CSV import is capped — P16 production-truth carries forward (the nonce-based production CSP fixed the shipped app that could not hydrate; the service-path middleware restored; the allocation endpoint instalment contract completed; the dashboard invalidation key fixed; org-creation no longer dead-ends; the ACRA other-entities UEN form accepted; P14 completed + the tree repaired after the corrupted 2bcb43f0 commit; the runtime-role gate live: the full onboarding path as ledgersg_app, 13/13 smoke steps; §17 RLS complete; zero known dependency advisories on the production set)

---

## 📋 Table of Contents

1. [Executive Summary](#-executive-summary)
2. [Project Architecture](#-project-architecture)
3. [Backend Deep Dive](#-backend-deep-dive)
4. [Frontend Deep Dive](#-frontend-deep-dive)
5. [Database Architecture](#-database-architecture)
6. [IRAS Compliance & GST](#-iras-compliance--gst)
7. [Security Architecture](#-security-architecture)
8. [Testing Strategy](#-testing-strategy)
9. [Development Guidelines](#-development-guidelines)
10. [Troubleshooting](#-troubleshooting)

---

## 🎯 Executive Summary

**LedgerSG** is a production-grade, double-entry accounting platform purpose-built for Singapore SMBs. It transforms IRAS compliance from a burden into a seamless, automated experience while delivering a distinctive "Illuminated Carbon" neo-brutalist user interface.

### Current Status

| Component | Version | Status | Key Metrics |
|-----------|---------|--------|-------------|
| **Frontend** | v0.3.8 | ✅ Ready | 16 pages, 698 unit + 43 e2e tests (11 always + 32 backend-gated; the live suite 43P/0F green incl. the fresh-DB first-run proof — re-proven P26 with the self-stocked fodder spec), typecheck clean, whole-tree eslint 0 errors, axe-clean login flow, cross-reload session persistence, real invoices list/detail + ledger + settings pages, working void dialog + real error messages + PDF/InvoiceNow actions, real reports + quotes pages, organisation creation + full payment workflow + truthful dashboard (P5–P9), registration + contacts + the contact-picker invoice form + the GST F5 lifecycle + bank edit/deactivate + fiscal open + change password + InvoiceNow settings (P10), the truthful edit-dialog prefill + F5 box labels + dashboard GST/chart/prefix truth + permission-gated row actions + dev-only CSP unsafe (P11), the server-side paginated ledger (P24), the pagination a11y/truth hardening (P25), the frontend pagination wiring on every list surface (P26), the pagination state-machine truth (P27) |
| **Backend** | v0.6.8 | ✅ Suite Fully Green | 90+ endpoints, **1028 tests passing, 0 failed** (5 skipped, documented), HttpOnly refresh-cookie auth, real InvoiceNow + accounting truth (credit notes post reversed entries and net in F5 — P11/C-1), per-status transition permissions + active custom exception handler, real financial reports + aged AR/AP + quote lifecycle + the P9 banking/onboarding contracts (P5–P9), GST F5 review/amend + fiscal-period open + UEN 400s + the 429 rate-limit contract (P10), production settings that boot (builtin cache + LOG_DIR) + typed org-settings PATCH + UUID routing 404s + audit-trail context (P11); the exception-handler rollback + IRAS 2dp GST quantum + typed ImmutabilityError + InvoiceNow 404s + reversal atomicity + timezone-aware dates + copy-on-write settings (P13), the server-side list pagination on every core list surface (P24), the pagination contract hardening — the int8 offset cap + the offset-requires-limit 400s + the transactions test coverage (P25), the Peppol transmission-log pagination contract (P26), the SQL-level push-down for the service-driven lists (P28), the detail-view N+1 closure (P29) |
| **Database** | v1.2.2 | ✅ Complete | 7 schemas + token blacklist, RLS complete on every tenant table (§17, incl. the append-only audit log), 30 domain tables + §15c framework tables (incl. the ENABLE_ADMIN opt-in set), NUMERIC(19,4) money |
| **Accounting** | v1.0.0 | ✅ Verified | 3/3 Workflows (void reversal restored 2026-11-21) |
| **Security** | v1.3.0 | ✅ P0 Hardened + P4 Cookie Auth + P7 API gates | Token rotation+blacklist, SECRET_KEY gate, ratelimit default-on (settings-driven login knobs), HttpOnly refresh cookie + `session_hint` evidence gate, per-status document permissions, manager-gated settings PATCHes |
| **API Contracts** | v1.3.0 | ✅ Standardized | {results, count} lists; auth contract aligned to tests 2026-11-21; error envelope {error:{code,message,details}} active in DRF (P7/F-19); the additive `?limit=&offset=` pagination with next/previous + total-count (P24) |

### Latest Milestone: P29 Sprint — The Detail-View N+1 Closure (The Detail Seams + The Per-Glob Ratchet + The Missing shared Tier) ✅ — 2026-11-28 (session 55)

Source: `docs/REMEDIATION_PLAN_2026-11-28_P29.md` (validated against the codebase before execution; every behavioural change TDD — RED first). No schema changes (v1.2.2 carries forward); no frontend component changes (the web-tree delta is the coverage-ratchet config).

| Fix | Impact |
|-----|--------|
| **BE-H1 (the headline — the detail-view N+1 closure)** | The three detail seams fetched their row with a plain `.objects.get(...)` while the serializers walked the related FKs — the invoice/quote detail walked account + tax_code on EVERY line (a 5-line invoice paid 14 queries where 3 would do, across 8 serialising call sites incl. the PDF context), the journal entry detail walked account on every line (the registered "journal detail N+1"), the payment detail walked contact + bank_account. Fixed at the service seam: `get_document` selects the contact and prefetches the lines with account + tax_code in ONE joined SELECT; `get_entry` prefetches lines-with-account; `PaymentService.get` joins contact + bank_account — the payloads byte-identical (the contract suites green, the e2e 43/43, the detail contracts re-verified live). Pinned by 3 NEW query-count gates: a detail request issues a bounded, line-count-independent set of SELECTs — the RED runs proved the per-line walks |
| **CFG-M2 (the per-glob ratchet + the shared tier)** | The five per-glob coverage tiers still held their P20-measured values (the hooks branches floor sat 15 points below the measured 51.16 — the widest rubber stamp) — all raised at the measured floors (lib 73/54/78/75, hooks 55/47/51/55, app 75/65/73/76, components 83/76/69/84, providers 63/63/58/62), plus the NEW `src/shared/**` tier at 73/62/76/73 (the P20 tier set had missed the shared primitives — the same blind-spot class it closed for app+providers); `test:coverage` green at the raised floors |
| **The gate** | backend **1028P/0F/5S** (+3) · vitest **698/698 (85 files)** · coverage green at the RAISED per-glob ratchets · tsc 0 · eslint **0E/0W** · live e2e **43/43** · rls_smoke 13/13 · mobile-nav 17/17 (twenty-seventh settlement) · the `translate` probe re-PASS · npm audit **0** (dev+prod) · build:server green + prod-CSP 5/5 · 8 DOM-verified screenshots (184-191) |

### Previous Milestone: P28 Sprint — The SQL-Level Push-Down (The Service-Driven Lists + The Honest Ratchet + The Dev-Tier Dependency Closure) ✅ — 2026-11-28 (session 53)

Source: `docs/REMEDIATION_PLAN_2026-11-28_P28.md` (validated against the codebase before execution; every behavioural change TDD — RED first). No schema changes (v1.2.2 carries forward); no frontend component changes (the web-tree deltas are the coverage-ratchet config + the dev-tier dependency bump).

| Fix | Impact |
|-----|--------|
| **BE-H1 (the headline — the SQL-level push-down)** | The four service-driven list surfaces (contacts, documents [invoices AND quotes], payments, bank transactions) materialised the ENTIRE filtered set in Python on every request (`return list(queryset...)`) and the views Python-sliced + `len()`-counted — every 20-row page of an organisation with N documents fetched all N rows (the P24 envelope paged the RESPONSE, not the QUERY). Fixed: the services return lazy querysets; the views count via SQL COUNT(*) and page via SQL LIMIT/OFFSET — the envelope byte-identical (the P24 suite green, the e2e 43/43, the API contracts re-verified live). Pinned by 4 NEW query-level gates: a paginated request issues a LIMIT-bounded SELECT at the requested page size + a COUNT query — the RED runs proved the unbounded fetch |
| **CFG-M2 (the honest ratchet)** | The vitest coverage config still held the P20 whole-suite floor (71/60/68/71) while the measured floor had risen to 73.39/62.38/70.72/73.95 — the P21–P27 reports each recorded "the floor RAISED to <measured>" but never wrote it into the config (a ratchet nobody bumps is a rubber stamp). Raised to 73/62/70/73; `test:coverage` green at the raised floor |
| **DEP-M3 (the dependency closure)** | The 17 dev-tier npm-audit findings (7 high — undici via jsdom, vite via vitest/plugin-react, @typescript-eslint, minimatch, brace-expansion, js-yaml, flatted, picomatch, browserslist, semver, ignore, the @babel toolchain) — all verified dev-only (`--omit=dev` was already 0) — closed with in-range semver bumps only (the dry-run set reviewed before applying); `npm audit` now reports 0 across dev+prod; the full web matrix re-verified on the bumped tree |
| **The gate** | backend **1025P/0F/5S** (+4) · vitest **698/698 (85 files)** · coverage green at the RAISED ratchet · tsc 0 · eslint **0E/0W** · live e2e **43/43** · rls_smoke 13/13 · mobile-nav 17/17 (twenty-fifth settlement) · the `translate` probe re-PASS · npm audit **0** (dev+prod) · build:server green + prod-CSP 5/5 · 8 DOM-verified screenshots (176-183) |

### Previous Milestone: P27 Sprint — The Pagination State-Machine Truth (The Debounce Race + The Reset-Consistency Completion) ✅ — 2026-11-28 (session 52)

Source: `docs/REMEDIATION_PLAN_2026-11-28_P27.md` (validated against the codebase before execution; every behavioural change TDD — RED first). No schema changes (v1.2.2 carries forward); **no backend changes at all** — the defect class is entirely frontend state-machine wiring.

| Fix | Impact |
|-----|--------|
| **FE-H1 (the headline — the debounce mount-run race, proven by trace)** | The P26 search-debounce effect's timer body called `setOffset(0)` unconditionally — including on the effect's MOUNT-run (~300ms after mount, doubled under React StrictMode in dev) — so a Next click landing inside that window was silently reverted to page 1: the offset snapped back, the queryKey returned to the page-1 cache entry, and TanStack served it from cache with no refetch and no feedback. The serial full-run e2e lost this race deterministically (42/43 three times — the documented 43/43 did not reproduce) while the isolated run passed it. Fixed: the page restart fires ONLY on a debounced VALUE CHANGE (the last-committed-value ref compared inside the timer callback — an event, never during render, so the react-hooks/refs contract holds); a real search change still restarts the paging (pinned by its own gate) |
| **FE-M3 (the org-switch reset, extended)** | The five P26-paginated surfaces carried no org-switch reset (the ledger got it in P25/FE-L3) — switching org mid-pagination dispatched the new org at the previous offset (a stale-offset fetch + a garbage cache entry per switch). Fixed with the render-time prev-state pattern on every surface, pinned per surface by real-hook transport-URL specs |
| **FE-M2 (the banking filter-change reset)** | The payments/transactions lists never restarted the paging on a filter change — a reader on page 2 of the narrowed set landed beyond the end. Fixed: the render-time reset on the filters-prop identity change (the parent holds the filters in useState; a stable module-level `NO_FILTERS` default keeps the identity compare safe when the prop is omitted) |
| **The gate** | backend **1021P/0F/5S** (unchanged) · vitest **698/698 (85 files)** (+12) · coverage green at the ratchet (whole-suite floor RAISED to 73.39/70.72/62.38/73.95) · tsc 0 · eslint **0E/0W** · live e2e **43/43 — deterministic** · rls_smoke 13/13 · mobile-nav 17/17 (twenty-third settlement) · prod-CSP 5/5 · **the fresh-DB proof: 43/43, 0 skipped, FIRST run** · 8 DOM-verified screenshots (168-175) |

### Previous Milestone: P26 Sprint — The Frontend Pagination Wiring + The Peppol Transmission-Log Contract ✅ — 2026-11-28 (session 50)

Source: `docs/REMEDIATION_PLAN_2026-11-28_P26.md` (validated against the codebase before execution; every behavioural change TDD — RED first). No schema changes (v1.2.2 carries forward); no backend models touched.

| Fix | Impact |
|-----|--------|
| **FE-M1/M2/M3/L1 (the headline — the frontend pagination wiring)** | The invoices, contacts, payments, bank-transactions and quotes surfaces all loaded the **unbounded** set (every list page fetched its entire history in one response); the invoices search filtered client-side over only the fetched rows; the contacts hook discarded the envelope (`return response.results` — the count unavailable); the payments/transactions lists carried the P10/L-2 'Load more was doubly dead' confession. Fixed: every surface pages server-side at size 20 through the P24 contract with the shared `TablePagination`; the page identity lives in each hook's queryKey (`useInvoices`/`useContacts`/`usePayments`/`useBankTransactions` — the cache-paging trap pinned per hook); the invoices search migrated server-side (debounced 300ms); `useContacts` returns the envelope (the ContactPicker adapted to `data?.results`); the offset reset batches into the debounce tick / the filter click (never a separate effect — the double-render lesson) |
| **BE-M4 (the last unbounded backend list)** | `/peppol/transmission-log/` had no limit/offset, no `id` tiebreaker on `-transmitted_at` (the cross-page skip/dup hazard), and three separate COUNT queries for the status counters. Fixed: the standard `parse_limit_offset` + `page_envelope` (extended additively with `extra` for the counters — every existing caller byte-identical) + the `-transmitted_at, -id` ordering + one conditional-aggregation query; `limit` absent keeps `{results, count, pending, failed, completed}` byte-identical; the P25 typed-400 rules ride along |
| **E2E (the self-sufficiency)** | The new `P26/FE-P1` spec stocks its own fodder through the public API (count-driven: while the invoice count ≤ 20, create small DRAFT fodder — no journal lines, so the F5 boxes and dashboard stay untouched; idempotent). **Proof: fresh DB → one bootstrap → the FIRST e2e:full = 43/43, 0 skipped** — the P25 lesson applied at design time (no substrate dependence to document) |
| **The gate** | backend **1021P/0F/5S** (+12) · vitest **686/686 (80 files)** (+22) · coverage green at the ratchet (the whole-suite floor RAISED to 72.94/70.32/62.38/73.51 by the new suites) · tsc 0 · eslint **0E/0W** · live e2e **43/43** (incl. the fresh-DB first-run proof) · rls_smoke 13/13 · mobile-nav **17/17** (twenty-first settlement) · prod-CSP 5/5 · 8 DOM-verified screenshots (`160-167`, the paginated invoices page 1/page 2 the headline pair) |

### Previous Milestone: P25 Sprint — The Fresh-Substrate First-Run Truth + The Pagination Contract Hardening ✅ — 2026-11-28 (session 48)

Source: `docs/REMEDIATION_PLAN_2026-11-28_P25.md` (validated against the codebase before execution; every behavioural change TDD — RED first). No schema changes (v1.2.2 carries forward); no backend models touched.

| Fix | Impact |
|-----|--------|
| **E2E-M1 (the headline — the fresh-host first-run truth)** | The §9 bootstrap's step 4a/4b silently shipped broken (the line serializer has required `tax_code_id` since P14/M-4 — the POSTs failed behind `|| true` guards, printing "invoice OK ()" with an empty id) and the substrate never carried the volume the P24-era e2e contract needs (a fresh bootstrap posts 6 lines; the pagination spec needs > 20, the void spec a surviving voidable document). Fixed: the SR tax code on every substrate line with LOUD failures (exit 1) + **step 4c the fodder top-up** (count-driven: ≥ 36 ledger lines, ≥ 4 APPROVED invoices, idempotent). **Proof: fresh DB → one bootstrap → the FIRST e2e:full = 42/42, 0 skipped** |
| **BE-M2/L4 (the contract hardening)** | A validly-typed offset above the Postgres bigint bound was an untyped **500** on the ledger (DataError: bigint out of range) — now the typed 400 on every surface (`parse_int_param` gained `max_value`; `MAX_PAGE_OFFSET = 2^63−1`); `offset` without `limit` was silently ignored (the full set returned) — now the typed 400 (no existing consumer sends the shape; the API guide documents the rule) |
| **BE-M3 (the coverage gap)** | The transactions surface joined the P24 pagination test matrix (3 fixture bank transactions; the P24 commit message had claimed "the five service-driven surfaces" while the tests covered four) + the empty-string params and the full absolute `next` URL shape pinned |
| **FE-L1/L2/L3 (the truth/a11y hardening)** | The pagination buttons' accessible names contain their visible text (WCAG 2.5.3 — "Previous page"/"Next page"); a page beyond the end keeps its controls with the truthful "Showing 0–0 of N" (never a false "No journal entries yet"); the org-switch offset reset during render (the React prev-state pattern; empirically the old effect reset never fired a stale fetch on React 19 + TanStack 5.90 — the fix makes the guarantee explicit, pinned by a real-hook transport-URL spec) |
| **The gate** | backend **1009P/0F/5S** (+14) · vitest **664/664 (78 files)** (+4) · coverage green at the ratchet · tsc 0 · eslint **0E/0W** · live e2e **42/42** (incl. the fresh-DB first-run proof) · rls_smoke 13/13 · mobile-nav **17/17** (eighteenth settlement) · prod-CSP 5/5 · 8 DOM-verified screenshots (`152-159`, the fresh-substrate ledger page 1/page 2 the headline pair) |

### Previous Milestone: P24 Sprint — The Server-Side List Pagination (the Ledger Line Materialisation First Target) ✅ — 2026-11-27 (session 45)

Source: `docs/REMEDIATION_PLAN_2026-11-27_P24.md` (validated against the codebase before execution — every surface hand-audited; every change TDD — RED first). No schema changes (v1.2.2 carries forward); no backend models touched.

| Fix | Impact |
|-----|--------|
| **BE-M1 (the registered big-ticket deferral)** | The additive `?limit=N&offset=M` on the six core list surfaces — the general ledger (line-level, the SQL level: `queryset.count()` + the queryset slice), the entries, documents, contacts, payments and transactions lists (the envelope level). With `limit` absent the response stays byte-identical `{results, count}`; with it the envelope gains `next`/`previous` (absolute URLs carrying limit+offset+the caller's filters) and `count` reads as the **TOTAL** matching rows. Garbage limit/offset are typed 400s; the documented max is 1000 |
| **I1 (the ordering tiebreakers)** | Contacts (`name, id`), payments (`-payment_date, -created_at, -id`) and transactions (`-transaction_date, -created_at, -id`) gained the unique final tiebreaker — Postgres tie order is not stable across executions, so a paginated page boundary could skip or duplicate a tied row; pinned by the forced-tie test (two same-name contacts paginate without skip or dup) |
| **FE-M2/L1 (the ledger UI + the cache trap)** | The shared accessible `TablePagination` (nav landmark, polite live region "Showing x–y of z", boundary-disabled Previous/Next) wired into the ledger client at page size 20 + `useLedger` limit/offset forwarding with the **page identity in the queryKey** (the cache-paging trap: pages would otherwise serve each other's cache) + the live paging e2e (`P24/FE-P1` — Next advances to "Showing 21–36 of 36", Previous returns) |
| **The gate** | backend **995P/0F/5S** (+26) · vitest **660/660 (77 files)** (+18) · coverage green at the ratchet · tsc 0 · eslint **0E/0W** · live e2e **42/42** (+1) · rls_smoke 13/13 · mobile-nav **17/17** (sixteenth settlement) · prod-CSP 5/5 · 8 DOM-verified screenshots (`144-151`, the ledger page 1/page 2 the headline pair) |

### Previous Milestone: P23 Sprint — The Mobile-Nav Drawer Slide Truth + The Vitest Advisory Closure ✅ — 2026-11-27 (session 44)

Source: `docs/REMEDIATION_PLAN_2026-11-27_P23.md` (validated against the codebase before execution — the transition token compile-proven; every fix TDD — RED first). No schema changes (v1.2.2 carries forward); no backend code changes (the P21 suite re-verified 969P/0F/5S on a fresh clone).

| Fix | Impact |
|-----|--------|
| **FE-M1 (the named focus)** | The drawer's `transition-[transform,visibility]` omitted v4's standalone `translate` property — the 300ms slide never interpolated (compile proof: `.-translate-x-full → translate: var(…)`; live probe: `transitionProperty: "transform, visibility"` + `transform: none` — the budget was dead config). Fixed to `transition-[transform,translate,visibility]`; the live re-probe samples **16 intermediate translate values** mid-flight; the drawer now slides |
| **L1 (the animation-contract gate)** | The compiled-CSS gates the 13 prior mobile-nav settlements lacked: the `shell-drawer-transition.test.tsx` spec pins the transition token + positioning contract; the `P23/FE-M1` e2e spec asserts the computed `transition-property` in a real browser at 375px |
| **M2 (the advisory closure)** | `vitest` + `@vitest/coverage-v8` ^4.0.18 → **^4.1.12** (the fixed 4.x line, a minor bump inside the caret range) — **both critical advisories closed** (GHSA-82fw-gwwq-j7x9 + GHSA-qxg6-89mg-rqv8); `npm audit` 20 → 17 findings, **0 critical** (the 17 residual are dev-tier; the production set clean) |
| **The gate** | backend **969P/0F/5S** (re-verified) · vitest **642/642 (76 files)** · coverage green at the ratchet · tsc 0 · eslint **0E/0W** · live e2e **41/41** (+1) · rls_smoke 13/13 · mobile-nav **17/17** (fifteenth settlement — with the slide animating) · prod-CSP 5/5 · 8 DOM-verified screenshots (`136-143`, incl. the drawer captured mid-slide) |

### Previous Milestone: P21 Sprint — The List-Envelope Unification, the InvoiceNow Evidence Stamp, the Cache-Commit Truth & the Banking A11y Batch ✅ — 2026-11-27 (session 42)

Source: `docs/REMEDIATION_PLAN_2026-11-27_P21.md` (validated against the codebase before execution; every fix TDD — RED first). No schema changes (v1.2.2 carries forward).

| Fix | Impact |
|-----|--------|
| **BE-M6 (the envelope)** | Every LIST endpoint returns `{results, count}` — the 7 non-conforming sites unified (the orgs list, fiscal years, the bare-array `/auth/organisations/`, the journal trial balance + entry types, the IRAS tax-code info, the GST return-periods POST); reports keep `{data: {...}}` (lists → results, reports → data); the frontend + e2e + bootstrap migrated; the prerequisite for pagination; the VACUOUS RLS isolation assert fixed (read `.get("data", [])` against a `{results}` endpoint — always passed) |
| **BE-M1** | The bank-account default flag row-locked: `set_default` (org-wide sorted lock — two concurrent calls can no longer leave two defaults), `update`/`deactivate` (locked read + `update_fields` scoped saves — no more full-row clobbers of concurrent `opening_balance` edits) |
| **BE-M2 + M3** | The dashboard cache invalidated by `void_document` + manual journal entries (the P5/H-3 completion), and every mutation-path invalidation/deletion moved to `transaction.on_commit` (a delete inside the transaction re-seeds the stale value in the delete→commit window) |
| **BE-M4** | `invoicenow_sent_at` stamped on a DELIVERED Peppol transmission (stamp-once via the isnull filter) — the evidence column the void/unallocate "restore to SENT" branch reads was never written (dead code) |
| **BE-M5** | `ValidateBalanceView` typed 400s on malformed bodies (non-numeric debit/credit, dict/string `lines`) — was AttributeError/InvalidOperation 500s |
| **FE-H1/H2 + M1/M2/M4/M5** | The banking a11y batch: the Make-Payment Reference input's accessible name; the keyboard-reachable CSV import (`sr-only`, not display:none); the import dialog's unique ids (the co-mounted filters' duplicate `bank-account`); the loader live regions on every remaining surface; the payment-card keyboard contract; the reconcile selection's `aria-pressed` |
| **FE-M3 + L-batch** | The timezone class completion: `isoYearOf` (the GST year read lexically — the local-tz read queried the wrong year's returns) + `localTodayISO` (local calendar day, was UTC); the visible-label ContactPicker (`aria-labelledby`); the dead `accent-primary` token; the always-rendered `aria-controls` regions; playwright `video: retain-on-failure` |
| **The gate** | backend **969P/0F/5S** (+19) · vitest **641/641** (+14, 75 files) · tsc 0 · eslint 0 errors/0 warnings · coverage green at the ratchet · live e2e 40/40 · rls_smoke 13/13 · mobile-nav 17/17 (thirteenth settlement) · prod-CSP 5/5 |

### Previous Milestone: P20 Sprint — The void/transition Lock Completion, the CSV Transaction Poisoning, the E2E First-Run Truth & the Test-Config Ratchet ✅ — 2026-11-27 (session 40)

Source: `docs/REMEDIATION_PLAN_2026-11-27_P20.md` (validated against the codebase before execution; every fix TDD — RED first). No schema changes (v1.2.2 carries forward).

| Fix | Impact |
|-----|--------|
| **BE-H1/H3 + M1/M2** | The locking completion: `void()` locks its affected documents (sorted pre-lock — a concurrently-committed allocation no longer vanishes from `amount_paid`); `transition_status()` locks + re-validates post-lock + `update_fields` (no stale status/totals over a concurrent approval); `allocate()` pre-locks its documents in sorted order (the AB-BA class) |
| **BE-H2** | The CSV import savepoint + the `1E15` magnitude bound — one DB-level poison row (a NUMERIC(19,4) overflow) is a typed row error in `errors[]` while the surrounding rows import (previously an abort-everything untyped 500) |
| **BE-M5 + L-batch** | `create_entry()` invalidates the `account_balance` cache for the touched accounts (the 5-minute stale money read); the `Decimal` F821; the allocate positive guard; the unreconcile org filter |
| **FE-H1/H2 + M1/M4/M7 + L2/L3** | The invoice-form Notes/Terms accessible names; the named back links on /invoices/new + /quotes/new; the ContactPicker blur dismissal (the WAI-ARIA pattern, mousedown still wins); the gst-f5-chart valid ARIA row; `formatDateOnly` with `timeZone: "UTC"` (the date off-by-one for timezones behind UTC); the one-h1-per-page shell; the loading live regions |
| **CFG batch (the owner's named task)** | The coverage ratchet expanded (`src/app/**` + `src/providers/**` measured, per-glob floors, the whole-suite floor RAISED to 71/60/68/71, the `__tests__` helper excluded); playwright `retain-on-failure` traces + the en-SG/Asia-Singapore locale/timezone pins; `test:all` runs the coverage |
| **X-H1 + docs batch** | The e2e first-run truth (the banking helper is contact-self-sufficient + the one-command §9 bootstrap script — a fresh DB's first run is green); DEPLOYMENT §3 parametrized to `$PG_BASE`; the stale counts refreshed in DEPLOYMENT/AGENTS/PAD/ci.yml; the four wrong API-guide routes corrected; the backend `.env.example` decouple caveat |
| **The gate** | backend **950P/0F/5S** (+13) · vitest **627/627** (+8) · tsc 0 · eslint 0E/0W · coverage green at the RAISED ratchet · e2e 40P (first-run green) · rls_smoke 13/13 · mobile-nav 17/17 (eleventh settlement) · prod-CSP 5/5 |

### Previous Milestone: P19 Sprint — The remove_line Truth Gap, the Unallocate Deadlock, the Status-Task Context & the Coverage Floors ✅ — 2026-11-27 (session 38; the P18 header previously sat on this block's gate row — corrected P21)

Source: `docs/REMEDIATION_PLAN_2026-11-27_P18.md` (validated against the codebase before execution; every fix TDD — RED first). One additive schema section (§15c completion — v1.2.2).

| Fix | Impact |
|-----|--------|
| **BE-H1** | `generate_f5`/`review_return` locked (`select_for_update` + atomic, the `file_return` pattern) — a concurrent recompute could regress a FILED statutory record to COMPUTED while `filed_at` stayed populated (the P14/C-2 shape, reopened through a race) |
| **BE-M batch** | `unallocate`/`unreconcile` locked (sibling lock order); `convert_quote_to_invoice` locked (double-convert refused); `add_line` line-number race closed + typed 400; the credit-note cumulative cap locked; header/archived account posting refused at `create_entry` (the TB/ledger divergence closed); `archive_account` locked |
| **BE-M1/M7/L3** | The three remaining Peppol task bodies open the RLS tenant context (org passed explicitly); the production-only `on_commit` dispatch branch test-covered; deleted-org/document tasks classify terminal (no 3x60s retry-to-death) |
| **BE-L batch** | suggest-matches `<uuid>` converter (routing 404); the email status gate (APPROVED invoices only); the exchange-rate seam typed; the return-period UNIQUE race typed |
| **FE-H1 + M2/M3** | The contrast debt: the three `bg-success text-white` badges (1.33:1!) → `text-void` (15.27:1), the `bg-alert` trio likewise, `--color-text-muted` at AA — pinned by new pairing/ratio regression gates |
| **FE-M1/M4/L1/L3** | The nested-Escape fix (the org menu consumes the first Escape; the drawer keeps focus visible); the genuinely-shared `uenSchema` (the invoice customer field normalizes — lowercase UENs no longer false-rejected); `tw-animate-css` imported (the Radix animate utilities that silently compiled to nothing in v4 — a real Tailwind v4-class bug); `hasUnsavedChanges` reset on submit success |
| **Schema v1.2.2 (§15c)** | `django_session` + `django_admin_log` — the `ENABLE_ADMIN` opt-in no longer 500s on a schema-only host |
| **CFG batch** | The CI no-backend e2e job (the always-green 11); the hooks-tier coverage floor at the measured value; `@types/uuid` removed (uuid 13 ships its own types) |
| **Docs truth pass** | DEPLOYMENT.md (the §4 fresh-load count 30 — was 40, measured on a polluted test DB; the collectstatic step for the manifest-bound production storage, in the guide + systemd + Dockerfile; the PG_BASE parametrization; the v1.2.2 ladder rung; the §11 login/ canonical URL); README (stack-table versions, the Key-Files proxy row, Redis required, the Docker cross-reference, ENABLE_ADMIN, the P18 milestone); API guide (the org-PATCH URL fixed to the org-scoped root, the P18 addendum); AGENTS/CLAUDE/PAD/SKILL normalized; the Makefile canonical flags; both `.env.example`s gained ENABLE_ADMIN |
| **The gate** | backend 937P/0F/5S (+23) · vitest 619/619 (+18) · tsc 0 · eslint 0 errors/0 warnings · build:server green · CI + the no-backend e2e job |

### Previous Milestone: P17 Sprint — Concurrency Truth, the 400-Contract Sweep & the Celery Tenant Context ✅ — 2026-11-27 (session 34)

Source: `docs/REMEDIATION_PLAN_2026-11-27_P17.md` (validated against the codebase before execution; every fix TDD — RED first). No new DDL — every fix is application-layer; the one schema change is additive §15c (v1.2.1).

| Fix | Impact |
|-----|--------|
| **BE-H1** | Double journal-entry reversals refused (typed 400, `select_for_update` + re-check) — the second request now sees the reversed state post-lock |
| **BE-H2** | Double payment void refused under the row lock; single void unchanged |
| **BE-H3** | Celery tasks dispatched `on_commit` (never inside the request transaction) and the task bodies open the RLS tenant context (`common/tenant_context.py`) — real workers no longer run as unscoped superusers |
| **BE-M batch** | Typed GST box parsing (400s), bulk-allocation UUID field errors, UEN normalize-then-validate on org PATCH (case-dodge duplicates refused), tax-rate range, 6-dp exchange_rate, reconcile double-match 400, uuid route converters, `select_related` (O(1) list queries), negative-membership cache fix |
| **BE-L batch** | `/admin/` 404s outside DEBUG (settings-gate tested); the Django 6 `STORAGES` manifest migration (WhiteNoise compressed-manifest storage active) |
| **FE batch** | The `--color-success` token (14 dead class usages now compile); the unsaved-changes `beforeunload` guard; the org-selector Radix menu contract; the shared `uenSchema`; redirect-carry on refresh failure; four dead CSP origins dropped; the 6 lint errors cleared (0 errors, 5 parity warnings) |
| **The gate** | backend 882P/0F/5S (+22) · vitest 582/582 (+28) · tsc 0 · eslint 0 errors · build:server green · mobile-nav 17/17 · prod-CSP 5/5 · rls_smoke 13/13 · live e2e 40P |

### Previous Milestone: P16 Sprint — Production Truth (CSP Hydration, the Service-Path Middleware & the Deferred-Contract Sweep) ✅ — 2026-11-26 (session 32)

| Fix | Impact |
|-----|--------|
| **FE-C1 (Critical)** | The production CSP was `script-src 'self'` while every page shipped non-nonced inline bootstrap scripts — **the shipped production app could not hydrate**. Now nonce-based per-request via `src/proxy.ts` + `src/lib/csp.ts` (single source of truth; the app opts into dynamic rendering); gated by the new `scripts/prod-csp-smoke.js` (build standalone, boot, assert nonce + hydration + zero violations — the class the dev-mode suite structurally cannot cover) |
| **BE-H1** | `config/settings/service.py` (the Docker/script API entrypoint) rebuilt MIDDLEWARE from scratch and dropped TenantContextMiddleware + AuditContextMiddleware + CSP + WhiteNoise — every org endpoint would 403 for non-superusers with RLS seeing NULL. Now derived from base; a settings gate asserts the stack in every HTTP-serving module |
| **BE-H2** | The dedicated `POST /payments/{id}/allocate/` endpoint still demanded APPROVED-only (the P14 instalment fix missed the wire serializer) — PARTIALLY_PAID invoices 400'd. Now shares `ALLOCATABLE_STATUSES` |
| **FE-H1** | The dashboard query key was inverted (`["dashboard", orgId]`) — all 10 mutation→dashboard invalidations were silent no-ops. Now consumes `useDashboardMetrics` (orgId-first key) |
| **FE-H2** | Org creation dead-ended: `switchOrg` read the PRE-creation org list from a stale closure and silently skipped the selection. The new `selectOrgById` selects without list state |
| **FE-H3** | The frontend UEN regex rejected the ACRA other-entities form (LLPs like T08LL1234A) the backend accepts — now mirrors all three ACRA forms |
| **BE-M batch** | Payment-row `select_for_update` (TOCTOU); NaN/Infinity box-override rejection + `money()` non-finite guard; the line-total NUMERIC(19,4) bound; atomic create+allocate (no orphaned payments behind 400s); `discount_pct` forwarded on line-add; system tax-code rows read-only; file/amend row locks |
| **FE-M/L batch** | Open-redirect guard on `?redirect=`; the mobile drawer releases its scroll lock at the md breakpoint; `role="dialog"` + broadened focus trap; the e2e serial contract encoded in the Playwright config; the single-flight shared-FAILURE path pinned |
| **Docs truth pass** | Every stale count/version/claim in CLAUDE/README/PAD/SKILL/API guide/DEPLOYMENT corrected; the §17 upgrade note added for existing databases; 7 tracked log files + backup//plan/ debris untracked |

### Previous Milestone: P15 Sprint — Tree Repair, P14 Completion & the Runtime-Role Gate ✅ — 2026-11-26 (session 30)

| Fix | Impact |
|-----|--------|
| **Tree repair** | The interrupted session-29 committed its P14 work to wrong paths (the Payment model destroyed by a serializer overwrite — the backend could not boot); every stranded fix relocated to its canonical home, all P14 RED tests green |
| **C-2 + H-3** | FILED/AMENDED F5 returns are immutable (409, not even `force=true`); the GST period lock refuses back-posted approvals/journals/voids inside filed periods |
| **H-1..H-5** | Allocation cap (no negative amount_due), instalment statuses complete, linked+cap-checked credit notes (IRAS credit-note rule), the GST-registration guard |
| **H-6 + M-6a** | Schema v1.2.0 §17: RLS on all six remaining tenant tables (organisation, user_organisation, role, peppol_settings, tax_code, event_log — append-only); `audit.log_change` pins search_path |
| **C-1 + H-7** | Org creation sets the RLS context before seeding; the whole onboarding path verified LIVE as the non-superuser `ledgersg_app` (13/13 smoke steps; cross-org reads blocked; no-context reads fail closed) |
| **H-8 + H-9** | Django 6.0.10 / DRF 3.18.3 / lxml 6.1.3 / WeasyPrint 70 / Next 16.4.6 / zod 4.6.7 (zero known advisories, both production sets); the Docker path generates a strong per-boot key; service.py gates its key like production |
| **M-1/M-4/M-5/M-10/X-1/H-04b/H-05b** | Honest ACRA/IRAS validators (both M-form lengths; UEN-form GST numbers accepted); the line-item schema (400s); Viewer read-only; tax-code dedupe; XXE-hardened parser; NRIC PayNow masking + masked-echo rejection; F5 override evidence trail |
| **F-A + F-B** | The e2e bootstrap self-creates the F5 return; linked-CN + cap-headroom + real-UEN e2e contracts; single-flight token refresh (the rotation race killed sessions mid-suite) |

### Previous Milestone: P11 Sprint — Accounting Truth & Config Honesty ✅ — 2026-11-23 (session 23)

| Fix | Impact |
|-----|--------|
| **C-1** | Credit notes post REVERSED GL entries (previously invoice-direction — AR debited instead of credited) and NET in the F5 computation; quotes no longer count as supplies (H-3) |
| **C-2** | Production settings boot: the builtin Redis cache replaces the never-installed `django_redis`; `LOG_DIR` is an env knob; `DEBUG=true, DEBUG_TOOLBAR=false` no longer crashes dev (one gate — H-5) |
| **H-1 + M-3/M-4** | The contacts edit dialog prefills from the DETAIL endpoint — uen/peppol_id/address/gst_reg_number arrive with their stored values and a save persists them (previously an unconditional save ERASED them with a success toast); the search debounces |
| **H-2/H-4 + M-1/M-7/M-11/L-2** | The F5 boxes panel reads the real box keys (every box previously rendered "—"), the deadlines envelope and REVIEWED filter are truthful, the dashboard GST payable equals the F5 net GST (was hardcoded 0), the revenue chart takes raw values (was NaN on "SGD x.xx"), single currency prefixes |
| **M-2/M-5/M-6** | Bank-account PATCH without id → 404; the org-settings PATCH is typed (choice fields, clean 400s on garbage); garbage path UUIDs 404 at the routing layer (uuid converters) |
| **M-8** | The audit trigger reads the middleware's request context (ip/user-agent/path were NULL on every row); LOGIN/LOGOUT emission (in the CHECK vocabulary, never emitted) |
| **M-9..M-16 + H-6/H-7 + L-batch** | CI runs coverage + dead steps removed; devDependencies split; `.gitignore` covers `uv.lock`; the Docker path boots (pinned installs, gunicorn CMD, compose credentials, no at-boot migrate); CSP unsafe-* dev-only; root debris removed; `timezone.localdate()`; ledger reversals visible; UEN TOCTOU hardening; permission-gated row actions |

### Previous Milestone: P9 Sprint — Onboarding & Banking Truth ✅ — 2026-11-22 (session 18)

| Fix | Impact |
|-----|--------|
| **O-1** | Organisation creation ships at the route the dashboard's dead-end CTA targeted — a self-serve user could previously not use the product at all (registration creates no org; the CTA 404'd) |
| **B-1/B-2** | Statement import sends real multipart (`JSON.stringify(FormData)` sent `"{}"` — the import could never succeed); reconciliation match suggestions render (envelope + field mapping — the form always said "No matching payments found") |
| **B-3/B-3b** | Payment forms pick real contacts (the Customer field was a raw UUID text input) and settle invoices through inline allocations; the invoice detail's Record Payment deep-links into Banking prefilled |
| **B-4..B-6** | The bank-account dialog ships (the Add buttons were dead); payment Void + transaction Unreconcile give the P5/P6 correction engine its first UI |
| **C-1/C-2** | The quote-conversion envelope is pinned and read (the flat read routed to `/invoices/undefined` on every conversion); the invoices list shows invoices (quotes/bills no longer render as invoices) |
| **C-4** | Seeded accounts are filterable: the seed backfills `account_type` (the invoice form's dropdown was empty on fresh orgs) and the bank accounts are reachable via `is_bank` |
| **D-1..D-4** | The aged report honours its as-at date; the dashboard's invented GST boxes/trends are removed; the dead CTAs route to /reports |
| **C-3/B-7/S-1..S-4** | InvoiceNow transmits invoices only (an APPROVED quote could be delivered as a UBL Invoice — type gate + permission parity); tolerance/date NameError-500s are 400s; transport faults keep sessions; XSD fails closed; the stale root requirements.txt retired |

### Previous Milestone: P5 Sprint — Truth Restoration (Repo Hygiene, Real InvoiceNow, Accounting Integrity & Real Dashboard Data) ✅ — 2026-11-21 (session 11)

Built on the independent audit (`docs/ledgersg-audit-report.md`; every Critical/High re-verified in source):

| Fix | Impact |
|-----|--------|
| **C-1/C-3/H-9** | `.env`/`.env.local`/`.pyc`/`dist/`/`.bak` untracked (the P4 `git add -A` had re-committed the env files); CI DB password generated per run; `testing.py` reads `DB_*` from env |
| **C-2 + seam bug** | `send_invoicenow` creates a real transmission log + queues the task; `invoicenow-status` reports real rows; **the task passed a LOG id to `transmit_invoice(invoice_id)` — auto-transmit could never succeed**; cleanup never deletes DELIVERED/REJECTED (IRAS 5-year retention) |
| **H-1** | `allocate()` persists `document.amount_paid` — outstanding AR/AP and `amount_due` were permanently overstated (amount_paid never left 0) |
| **H-2** | payment `void()` posts a reversing journal entry (create_reversal, open-period date fallback) and releases allocations with document status restoration |
| **H-4** | control-account resolution is exact and fail-closed: AR 1200 / AP 2100 / GST input 1600 / GST output 2600 (the old `.first()` broad-match posted output tax to 2200 Accrued Expenses) |
| **H-5/H-6** | `add_line` stores the 2dp GST base as line_amount and a 2dp total; `create_entry` enumerates lines (duplicate dicts crashed the unique constraint) |
| **H-3/H-10** | dashboard cache invalidated by mutations (approve/void, payments, GST filing); alerts view computes real overdue/unreconciled/unpaid counts |
| **M-5/M-6/M-7** | GST registration seeds the control accounts (dead guard fixed); `update_organisation` allow-listed; dead sequence code removed |
| **C-5 (part 1)** | invoices list page renders real `useInvoices` data with truthful states; hook retyped to the real backend row shape |

### Previous Milestone: P4 Sprint — Cross-Reload Session Persistence & Suite Depth ✅ — 2026-11-21 (session 9)

Sessions now survive page reloads/new tabs/browser restarts, and the auth client can no longer be tricked into pointless refreshes:

| Fix | Impact |
|-----|--------|
| **E-1 backend** | `login/register` set the refresh token as an **HttpOnly cookie** (`Path=/api/v1/auth/`, SameSite=Lax, Secure=!DEBUG, 7d), `refresh` accepts body **or** cookie (rotation+blacklist identical, response re-sets the rotated cookie), `logout` blacklists whichever credential is present and expires the cookie, `change-password` expires it too (revoke-all); body flow unchanged for API clients (8 contract tests → 14 with the hint suite) |
| **E-1 frontend** | `fetchWithAuth` refreshes on a **cold 401** (no in-memory access token) and retries — the `&& accessToken` guard that dropped every reload is gone; the login body tokens stay unchanged |
| **E-1 refinement** | Evidence-gated refresh: a non-secret, JS-readable `session_hint` cookie (set alongside the refresh cookie; expired on logout/password-change/failed cookie-refresh) gates the client's refresh attempt — anonymous 401s (bad credentials) propagate to the caller instead of flooding the refresh rate limit and swallowing the login form's error behind a hard redirect (root-caused from the e2e run; 3 vitest + 6 pytest regression tests) |
| **E-5** | Session-persistence e2e spec: reload survival, post-reload client navigation, logout-kills-session (16 e2e total: 9 always + 7 gated); logout affordance added to the shell footer |
| **Rates** | Login limits became settings knobs (`LOGIN_RATELIMIT_IP/USER`; production defaults unchanged 10/min + 30/min; development 60/min for the e2e budget) via `config/ratelimits.py` dotted-path callables |
| **E-2/E-3/E-4** | Docs truth pass (README/PAD/CLAUDE/AGENTS/ledgersg_SKILL), root `.env.example` index, DEPLOYMENT.md cookie-flow + reload-persistence checklist |

### Previous Milestone: P3 Sprint — Monetary Capacity, Truthful Invoice Form & Suite Depth ✅ — 2026-11-21 (session 7)

Money now fits the business model (S$1M GST threshold), the New Invoice form actually creates documents, and both frontend suites gained real depth:

| Fix | Impact |
|-----|--------|
| **C-1/H-03** | All 47 monetary columns widened `NUMERIC(10,4)` → `NUMERIC(19,4)` (schema v1.1.0): the old width capped every value at S$999,999.9999 — **below the GST registration threshold** — so F5 Box 13 and ≥ S$1M lines/journal amounts overflowed (verified live). §16 ships the idempotent in-place migration (incl. the `amount_due` generated-column drop→widen→re-add sequence); the conformance gate now asserts numeric precision; `add_line` applies `discount_pct` server-side |
| **D-1** | New Invoice form submit was a TODO stub (`console.log` + mock UUID) with `useCreateInvoice` dead code — now wired: per-line posting-account select, pure contact+document payload adapter, error banner, server-authoritative recalculation |
| **D-2** | `useInvoicePDF` read the token from `localStorage` (zero-JWT-exposure violation AND `Bearer null` → 401 on every download) — now `api.blob()` shares the single fetch+refresh auth path |
| **D-3** | Tax-code dropdown + preview use the server rows in force on the document's date (`?effective_on=` wiring); backdated documents preview at the right rate; invalid server rates fail closed to 0, never 9% |
| **D-4/D-5** | Backend `.env.example` complete (15/15 settings-read vars incl. `ALLOWED_HOSTS`); e2e suite 6 → 13 tests (auth + invoice-form specs, `E2E_API_URL`-gated, `npm run test:e2e:full`); +25 vitest tests; fresh-host `docs/DEPLOYMENT.md` |

### Previous Milestone: P1 Sprint — Green Suite & Contract Truth ✅ — 2026-11-21 (session 3)

The 26 documented `test_api_endpoints.py` fixture failures were fixed and the suite went fully green (499P/0F/5S); the fixture pass unmasked and fixed three real endpoint bugs:

| Fix | Impact |
|-----|--------|
| **A-1** | Org fixture sets `UserOrganisation.accepted_at` — the tenant middleware requires accepted memberships (25 of the 26 failures were this one omission) |
| **A-2** | `DocumentSummaryView`: real `DOCUMENT_TYPES` vocabulary, enum-correct outstanding set (`PARTIALLY_PAID`, not `PAID_PARTIAL`), `total_incl` (not phantom `total`), Decimal-safe empty sums; same enum sweep in `deactivate_contact` |
| **A-3** | CoA trial balance aggregates `journal.line` — the schema has no `coa.account_balance` view |
| **A-4** | `ValidStatusTransitionsView` accepts the `org_id` kwarg its route passes |
| **A-6** | `pyproject.toml` declares `django-celery-beat==2.9.0` + `django-ratelimit` — clean-venv install + `manage.py check` now works end-to-end |
| **A-7/8/9** | `.env.example` for both apps; `.env` files gitignored + untracked; schema header v1.0.2 |

### Latest Milestone: P0 Remediation Sprint ✅ — 2026-11-21

All four Critical findings from the independent code audit were fixed test-first:

| Fix | Impact |
|-----|--------|
| **C-04** | `wrap_response` re-raises; journal posting inside the approve atomic block — no more partial commits |
| **C-02** | Void creates a real reversal entry; `void_reason` persisted; `PARTIALLY_PAID` voidable |
| **C-03** | RLS `SET LOCAL` executes inside a request-spanning transaction — tenant isolation actually applies under autocommit |
| **C-01/H-14** | GST F5 rebuilt on `invoicing.document*` with IRAS box convention; state machine `DRAFT→COMPUTED→REVIEWED→FILED→AMENDED` persists |
| **H-01** | Trial balance / account balance endpoints work (FK + `is_posted` fixes) |
| **H-05** | Refresh-token rotation + blacklist (schema §15b); logout and password-change revoke |
| **H-06/H-07** | Production SECRET_KEY gate; rate limiting default-on |
| **M-01** | Schema–model conformance gate in CI (`tests/invariants/test_schema_conformance.py`) — caught and fixed drifted `ExchangeRate`/`OrganisationSetting` models |

**Deferred:** H-02/H-03/H-04/H-08/H-10/H-11/H-13, M-02…M-16, L-*, I-* — full register in `docs/REMEDIATION_PLAN_2026-11-21.md` §4.

### Latest Milestone: API Contract Standardization & 500 Error Investigation ✅ COMPLETE (2026-03-15; superseded in part by the 2026-11-21 audit)
**Date**: 2026-03-15
**Status**: API contracts standardized, "500 error" myth debunked.

| Achievement | Impact |
|-----|--------|
| **API Contract Fix** | 9 endpoints standardized to {results, count} format |
| **8 Contract Tests** | New TDD test suite validates API contracts |
| **500 Error Investigation** | Debunked myth - no actual 500 errors exist |
| **Root Cause Found** | Test fixture issues cause 403s, not production bugs |

**Key Finding**: The "500 errors in journal/invoice endpoints" mentioned in documentation do NOT exist. What exists are:
- **403 Forbidden** errors caused by pytest fixture isolation issues  
- The production API works correctly (verified with direct testing)
- Tests using `auth_client` + `test_organisation` separately can fail due to RLS

**Critical Finding**: HttpOnly cookies break automation tool session persistence. **Solution**: Hybrid approach (API for auth/data, UI for verification only).

### Previous Milestone: SMB Workflow Hardening ✅ COMPLETE
**Date**: 2026-03-10
**Status**: 100% Double-Entry Accuracy Verified across Lakshmi's Kitchen (12mo) and ABC Trading.

| Fix / Alignment | Impact |
|-----|--------|
| **Ghost Column Fix** | Removed invalid timestamp/audit fields from Peppol models to match SQL exactly. |
| **Journal Filter Fix** | Eliminated incorrect `is_voided` reference in `JournalService` posting loop. |
| **Accounting Engine** | Ledger now reflects all transactions (Invoices → Approval → Payment). |
| **Reporting Accuracy**| Real-time SQL aggregations for P&L/BS verified with 100% precision. |
| **Test Results** | **789 unit tests** + **3 authoritative workflows** passing. |

---

## 🧪 Testing Strategy

### E2E Workflow Validation (Recommended Approach)

**Session persistence note (P4/E-1 + P13 correction)**: real-browser
automation (Playwright, full browser contexts) DOES carry the HttpOnly
refresh cookie across navigations and reloads — the green session-persistence
e2e specs prove it. The hybrid API approach below remains the right tool
for cookie-less CLI drivers (curl, agent-browser's request mode) and for
efficient bulk data setup.

**Hybrid Approach (cookie-less CLI drivers):**
```
┌─────────────────────────────────────────────────────────────┐
│  AUTHENTICATION (API)                                       │
│  • POST /api/v1/auth/login/                                 │
│  • Store access_token in memory                              │
│  • Skip HttpOnly cookie dependency                          │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐         ┌─────────────────────────┐
│  DATA CREATION (API)    │         │  UI VERIFICATION        │
│  • Journal entries      │         │  • Dashboard views      │
│  • Contacts             │         │  • Screenshots          │
│  • Invoices             │         │  • Visual assertions    │
│  • Payments             │         │                         │
└─────────────────────────┘         └─────────────────────────┘
```

**Why cookie-less drivers need the hybrid approach:**
- Access token stored in JavaScript memory (not accessible to CLI drivers)
- Refresh token in HttpOnly cookie (not attachable by curl-style clients)
- Result: those drivers must re-login via the API and carry the bearer token

**Standardized Validation Workflow:**
1. **API Login**: Get tokens via `POST /api/v1/auth/login/`
2. **API Data Creation**: Create all test data via authenticated API calls
3. **UI Verification**: Use Playwright for screenshots and visual checks only
4. **API Cleanup**: Delete test data via API

**Tools by Use Case:**
- **Quick checks**: agent-browser (single page only)
- **Full E2E**: the Playwright live suite (`npm run test:e2e:full`)
- **Visual regression**: Playwright with hybrid approach
- **CI/CD**: Hybrid approach with headless Playwright

---

## 🎓 Lessons Learned (2026-03-14 Update)

### E2E Testing Lessons

1. **Session Persistence is Hard**: HttpOnly cookies designed for security break automation. JWT access tokens in JavaScript memory are ephemeral. **Solution**: API-first authentication, UI only for verification.

2. **API Contracts Must Be Explicit**: Frontend expected `{results, count}`, backend returned `[]`. This broke entire Banking module. **Solution**: Schema validation, integration tests, shared contracts.

3. **Hybrid Testing is Powerful**: API for data, UI for verification. Best of both worlds. More reliable than pure UI, more visual than pure API.

4. **Tool Selection Matters**: 
   - agent-browser: Quick manual checks only
   - Playwright: Full automation with hybrid approach
   - Pure UI: Fragile, avoid for complex workflows

5. **Documentation ≠ Reality**: Test counts differed from README. Schema counts differed from PAD. Always validate against actual code.

### Previous Lessons (2026-03-10)

1. **Model Inheritance Hygiene**: Inheritance in Django is a "greedy" operation. In a SQL-First project, inheriting from `TenantModel` blindly will inject `created_at` and `updated_at` fields into your SQL queries. If the DB schema doesn't have them, the request will fail with a `ProgrammingError`.
2. **Side-Effect Determinism**: Approval is the explicit gateway to the General Ledger. This ensures that financial integrity is maintained even if operational data (DRAFT invoices) is noisy.
3. **Conflict Resilience**: Recent fixes to align `JournalService` and `Peppol` models with the SQL schema reinforce the stability of previous Meridian (Workflow 3) remediations. No regressions or conflicts were introduced.
