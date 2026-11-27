# LedgerSG — Remediation Plan (P26 Sprint: The Frontend Pagination Wiring + The Peppol Transmission-Log Contract)

**Date:** 2026-11-28 (session 50)
**Base commit:** `334c2f0e` (main — post-P25 + the session-49 narration log; **all 9 documented gates reproduce exactly this session** — see §1)
**Method for execution:** TDD (RED → GREEN → full gate) for every behavioural change; eslint parity on touched files; conventional commits on `main`; `skills/` excluded from all checks/tests/compilation; **no schema changes** (v1.2.2 carries forward); no backend model changes.
**Skills consulted:** `skills/skills-catalog.md` (343 skills) → `tdd` (the red→green loop), `nextjs16-tailwind4` (the data-surface + queryKey patterns), `tailwind-patterns` (the control styling), `agent-browser` (the live mobile-nav probe — executed this session, §1), `code-review`/`debugging-and-error-recovery` (Mode B/C discipline), `rootless-postgresql` (the PG environment — live from the prior session, re-probed).

---

## 1. Audit inputs (this session's evidence)

- **Repo + docs truth pass:** `git pull` to `334c2f0e` clean on `main`; full reads of `AGENTS.md`, `CLAUDE.md` v2.26.0, `README.md`, `Project_Architecture_Document.md`, `ledgersg_SKILL.md` v2.12.0, `worklog.md`, `docs/session_48.md`, `docs/session_49.md`, the P25 plan + report, and `docs/Tailwind-V4-Validation-Report.md` (Trap 5(b) — the standalone `translate` property).
- **The environment (live from the prior session, re-probed this session):** rootless **PG 17** on :5432 (both databases loaded — `ledgersg_dev` 30 domain tables + the django/public set, `test_ledgersg_dev` 45 tables), **Redis** on :6379, the backend venv, `node_modules`, the daemonized dev stack (:8000 dev, :8001 the RLS instance as `ledgersg_app`, :3000 `next dev`) — all responsive (`/auth/me/` 401 unauthenticated as expected; the web 307 as expected).
- **The full 9-gate baseline reproduction (all executed this session, pre-change):** backend `pytest --reuse-db --no-migrations -q` **1009P/0F/5S** (28.08s) · vitest **664/664 (78 files)** · `npx tsc --noEmit` **0 errors** · whole-tree `npx eslint .` **0E/0W** · live `test:e2e:full` **42/42** (2.2m) · `rls_smoke.py` **13/13 as `ledgersg_app`** · `mobile-nav-audit.js` **17/17** · `prod-csp-smoke.js` **5/5** (after a green `build:server`) · `npm audit` **0 critical** (17 dev-tier: 2 low / 8 moderate / 7 high; `--omit=dev` → 0) — **9 of 9 exact, the first fully-reproducing baseline since the P24 spec landed** (the P25 substrate fix holds).
- **The named focus — the mobile-nav verdict (twentieth settlement):** **WORKING as expected; NO remaining Tailwind v4 bug on this surface.** The dedicated live probe (Playwright, 375px viewport): closed drawer `translate: -100%` + `visibility: hidden`; computed `transitionProperty: "transform, translate, visibility"`; a **120ms mid-flight sample at `translate: -40.9622%`** (the slide interpolates); the open drawer `translate: 0px` + `visibility: visible` + `role="dialog"`; Escape closes it back to `-100%`. Plus the 17/17 audit probe and the 6 e2e mobile-nav specs in the live 42/42.
- **The audit (Mode C) of the P25 slice** (`0def60b5..94af7dc5`, hand-verified in source): `query_params.py`'s `max_value` mirror clean; `pagination.py`'s int8 cap + offset-requires-limit + the docstring contract clean; `table-pagination.tsx`'s beyond-end math + Label-in-Name labels clean; `ledger-client.tsx`'s count-based empty state + render-time org reset clean; the bootstrap's `TAX_CODE_ID` + the count-driven fodder loop verified idempotent in the live DB (49 lines / 13 APPROVED — post-e2e accumulation, as designed). **0 new Critical/High findings in the P25 slice.**
- **The P25 deferred register drives this sprint's scope:** "the frontend pagination wiring for invoices / contacts / payments / transactions" (the next UX slice — the backend contract + the shared TablePagination ready since P24; the ledger the only consumer) and "the Peppol transmission-log pagination (+ its `id` tiebreaker)" (newly registered I1).
- **Test-infra review:** `vitest.config.ts` (the whole-suite ratchet 71/60/68/71 + the per-glob floors + the documented `src/stores/**` exclusion) and `playwright.config.ts` (chromium default, the serial live-suite contract, `retain-on-failure` trace+video, the `Asia/Singapore`/`en-SG` pins) both structurally correct — the P23/P24/P25 conclusion re-affirmed: the task's "add vitest and playwright test suite by modifying the respective config files" is satisfied by **adding suites under the existing configs** (this sprint: 1 new backend spec file + 2 new frontend hook spec files + 1 new e2e spec + 5 extended frontend spec files).
- **The e2e sensitivity sweep (this sprint's changes' blast radius, verified):** the demo org's volumes sit under one 20-row page on every target surface (invoices ~16 documents, contacts 5, payments 2, bank transactions 2 — queried in the live DB), so the existing e2e specs (testid-based `.first()` locators, structural assertions) stay green with the wiring in place; the new pagination spec stocks its own fodder (the P25 self-sufficiency lesson applied at design time — no substrate dependence).

**Combined findings (this session's audit): 0 Critical / 0 High / 4 Medium / 2 Low** — every finding hand-verified in source (anchors below).

## 2. Findings (verified, with evidence anchors)

### Medium

**FE-P26-M1 — the invoices surface loads the unbounded set and searches client-side (the P24 ledger problem, again).**
`apps/web/src/app/(dashboard)/invoices/invoices-client.tsx:61-78` — `useInvoices(orgId, { type: "SALES_INVOICE" })` sends no `limit`; the `filtered` useMemo searches **only the fetched rows**. At real volume the page renders thousands of rows in one response and the search box silently misses everything beyond the fetch. The transport is ready: the hook already types `search` (`use-invoices.ts:126`) and the backend `InvoiceDocumentListCreateView` filters `?search=` server-side (`apps/invoicing/views.py:195,218`). Fix: page state at size 20 (the ledger convention), the search migrated server-side (debounced, the contacts-page pattern), and the shared `TablePagination` (P24/FE-M2 + the P25 a11y/truth hardening) driving the offset; the "filtered.length of count" line is replaced by the control's truthful "Showing x–y of z" summary.

**FE-P26-M2 — the contacts hook discards the envelope (the count is unavailable) and the page is unpaginated.**
`apps/web/src/hooks/use-contacts.ts:76-82` — `queryFn` returns `response.results`, throwing away `count`/`next`/`previous`; `contacts-client.tsx:67` renders every contact in one unbounded fetch. Fix: the hook returns the full envelope + gains a `page` param with the page identity in the queryKey (the P24/FE-L1 cache-paging trap); the client renders `TablePagination`; the one other consumer — `contact-picker.tsx:86-98` — adapts to `data?.results ?? []` (its search-driven fetch keeps the unpaginated shape: bounded by the search filter, no page needed).

**FE-P26-M3 — the payments + transactions surfaces: unpaginated, the dead Load-more an open confession since P10/L-2.**
`apps/web/src/app/(dashboard)/banking/components/payment-list.tsx:96-102` — the comment reads "the 'Load more' button was doubly dead … pagination remains registered debt"; `transaction-list.tsx:32` the same shape. Both surfaces' backend views (`PaymentListView`, `BankTransactionListView`) carry the full P24/P25 contract (limit/offset, typed 400s, the `id` tiebreakers). Fix: `page` params on `usePayments`/`useBankTransactions` (queryKey identity) + `TablePagination` in both components; the filters pass through unchanged.

**BE-P26-M4 — the Peppol transmission log: the last unbounded backend list (the P25/I1 register).**
`apps/backend/apps/peppol/views.py:32-62` — no limit/offset; `order_by("-transmitted_at")` with **no `id` tiebreaker** (the cross-page skip/dup hazard the P24 tiebreaker rule closed on every other surface); the three status counters (`pending`/`failed`/`completed`) each a separate `.count()` query per request. No frontend consumer exists (verified: `use-peppol.ts` carries only the settings hooks), so the additive contract lands clean. Fix: the standard `parse_limit_offset` + `page_envelope` (extended additively with an `extra` payload for the counters — every existing caller unaffected) + the `-transmitted_at, -id` ordering + the counters computed in one conditional-aggregation query; `limit` absent → the response stays byte-identical `{results, count, pending, failed, completed}`.

### Low

**FE-P26-L1 — the quotes surface rides the same unpaginated hook.**
`quotes-client.tsx:23` — `useInvoices(orgId, { type: "SALES_QUOTE" })`, no page; the page renders the unbounded set. The `useInvoices` page param fixes the transport; the page itself needs the `TablePagination` wiring to complete the documents-surface story in one sprint.

**DOC-P26-L2 — the docs truths roll forward with the sprint** (the standing DOC-L pattern): README badge/counts + the P26 milestone, CLAUDE 2.26.0 → 2.27.0, AGENTS header + the P26 lessons, SKILL 2.12.0 → 2.13.0, PAD rows, DEPLOYMENT header/§7/§9, the API guide 3.4.0 → **3.5.0** (the transmission-log pagination addendum), ci.yml counts, `.env.example`s re-verified (no new env vars this sprint).

## 3. The execution plan (phases, TDD)

### Phase 1 — RED: the contract tests (backend + hooks + pages + the live e2e)

| Task | Test (RED first) |
|---|---|
| T1 | New `apps/backend/tests/integration/test_peppol_pagination_p26.py` (the M4 matrix, the P25 file's structure): 5 fixture `PeppolTransmissionLog` rows (mixed statuses, two sharing `transmitted_at`); (a) limit-slice + total-count (`?limit=2` → 2 rows, `count` = 5, `next` present); (b) the next/previous boundaries (`?limit=2&offset=4` → `previous` present, `next` null); (c) the unpaginated envelope byte-identical — `{results, count, pending, failed, completed}` with the counters preserved (RED now: the params are silently ignored); (d) the counters under a `?status=` filter stay within the filtered set (the current semantics, pinned); (e) garbage `limit` 400; huge offset 400; offset-without-limit 400 (the P25 rules ride along — RED now: ignored, 200); (f) the forced-tie pagination (two same-`transmitted_at` rows, `limit=1`, no skip/dup — the `id` tiebreaker); (g) the paginated envelope carries the counters (`next`/`previous` AND `pending`/`failed`/`completed`). |
| T2 | Frontend hooks (the `use-ledger.test.tsx` transport-mock pattern — real TanStack hook under a real QueryClient, only the api-client mocked): NEW `src/hooks/__tests__/use-invoices.test.tsx` — the page param rides the query string (`?type=SALES_INVOICE&limit=20&offset=20`) AND the queryKey (two pages = two cache entries — the cache-paging pin); NEW `src/hooks/__tests__/use-contacts.test.tsx` — the return shape is the envelope (`{results, count}` — RED now: the bare array) + the page param + the queryKey identity; EXTEND `src/hooks/__tests__/use-banking.test.tsx` — `usePayments`/`useBankTransactions` page params (URL + queryKey). |
| T3 | Frontend pages/components (extend the existing spec files): `invoices-page.test.tsx` — the `TablePagination` renders (the nav landmark + "Showing 1–2 of 2"); the search input drives the hook's `search` filter (the debounced server search — fake timers); the beyond-end branch (the P25 pattern: count > 0, empty page keeps the controls). `contacts-client.test.tsx` — the envelope shape + `TablePagination`. `payment-list.test.tsx` + `transaction-list.test.tsx` — `TablePagination` replaces the bare count line. `quotes-page.test.tsx` — `TablePagination`. `contact-picker.test.tsx` — the `data?.results` adaptation (RED only where the shape change bites). |
| T4 | e2e (the live proof, P26/FE-P1): a new spec in `e2e/invoices.spec.ts` — a **self-stocking fodder helper** (count-driven: while the demo org's SALES_INVOICE count ≤ 20, POST small DRAFT fodder documents via the API — DRAFTs post no journal lines, so zero F5/dashboard impact; idempotent across runs), then: the pagination summary "Showing 1–20 of N rows", Previous disabled / Next enabled, Next advances (the page-2 summary + the first row changes), Previous returns. The self-sufficiency is the P25 lesson applied at design time — no substrate dependence to document. |

### Phase 2 — GREEN: the fixes

| Task | Fix | Verification |
|---|---|---|
| T5 | Backend: `common/pagination.py` — `page_envelope` gains the optional `extra: dict` (additive; merged after the standard keys; every existing caller unchanged); `apps/peppol/views.py` — `parse_limit_offset`, the `-transmitted_at, -id` ordering, the SQL-level queryset slice, the one conditional-aggregation counters query, the envelope with the counters in both modes. | T1 (a)-(g) GREEN · the full backend suite re-run |
| T6 | `use-invoices.ts` — the `page` param (query string + queryKey); `invoices-client.tsx` — the page state, the debounced server-side `search`, `TablePagination`, the truthful summary. | T2/T3 GREEN · `tsc` 0 · eslint parity |
| T7 | `use-contacts.ts` — the envelope return + the `page` param; `contacts-client.tsx` — `TablePagination`; `contact-picker.tsx` — the `results` adaptation. | T2/T3 GREEN · the picker suite green |
| T8 | `use-banking.ts` — the `page` params on `usePayments`/`useBankTransactions`; `payment-list.tsx` + `transaction-list.tsx` — `TablePagination` (the dead Load-more comment retired). | T2/T3 GREEN |
| T9 | `quotes-client.tsx` — the page state + `TablePagination`. | T3 GREEN |
| T10 | The live re-probe on the remediated stack: the invoices page paged live (the fodder spec's surface), the transmission-log envelope probed on :8000 (paginated + unpaginated + the counters). | the probe outputs recorded in the report |

### Phase 3 — the full gate matrix + the fresh-DB proof

1. The complete gate set on the remediated tree: backend `pytest` 1009+N/0F/5S · vitest 664+M/(78+ files) · coverage green at the ratchet · `tsc` 0 · whole-tree `eslint` 0E/0W · live `test:e2e:full` **43/43** (42 + the new P26 spec) · `rls_smoke` 13/13 · `mobile-nav-audit.js` 17/17 (the twenty-first settlement) · `prod-csp-smoke.js` 5/5 · `npm audit` 0 critical.
2. **The fresh-DB proof:** drop + recreate `ledgersg_dev` from `database_schema.sql` → restart both `--noreload` backends (the P24 restart rule) → flush Redis → ONE §9 bootstrap run → `npm run test:e2e:full` → **green with 0 skipped on the FIRST run** — proving the new spec's self-sufficiency (it stocks its own fodder; no accumulated-DB dependence — the P25 class of bug designed out, not patched out).
3. Screenshots: 8 DOM-verified captures (`docs/screenshots/160-167_*_session50.png`, md5-unique + non-blank pixel-verified, the session-45/48 capture conventions) — the invoices page 1 / page 2 pair (the headline), the contacts + payments + transactions pages (the newly-paginated surfaces), the mobile drawer closed/open, the desktop band; the capture script `scripts/capture-screenshots-session50.js` (the session-48 pattern).

### Phase 4 — the docs truth pass

| Doc | Update |
|---|---|
| README.md | the badge/test arithmetic (backend 1009+N, vitest 664+M, e2e 43), the status-table rows, the P26 milestone section (the frontend pagination wiring + the Peppol contract) |
| CLAUDE.md | version 2.26.0 → 2.27.0, the status block, the P26 milestone block |
| AGENTS.md | the header gate row, the P26 lessons (the "the page identity lives in the queryKey — every paginated hook, not just the ledger" + the "a self-sufficient spec beats a substrate claim" patterns) |
| ledgersg_SKILL.md | the quick-ref numbers, version 2.12.0 → 2.13.0 |
| Project_Architecture_Document.md | the lint/test count rows |
| docs/DEPLOYMENT.md | the header re-verification line (session 50 / P26), §7/§9/§11 counts |
| API_CLI_Usage_Guide.md | the version row 3.4.0 → **3.5.0** + the P26 addendum: the transmission-log surface joins the pagination contract (limit/offset + the typed 400s + the `id` tiebreaker + the counters in both modes), the frontend pages note |
| .github/workflows/ci.yml | the header comment counts |
| `.env.example` ×3 | re-verified truthful (no changes expected — no new env vars this sprint; the verification noted in the report) |

## 4. Deferred register (updated, carried forward)

**Fixed this sprint (removed from the register):** the frontend pagination wiring for invoices / contacts / payments / transactions / quotes (the P24-era deferral); the Peppol transmission-log pagination + its `id` tiebreaker (the P25/I1 register); the P10/L-2 dead Load-more debt (retired with the real controls).

**Still deferred (with rationale, unchanged from the P25 register unless noted):**
- **The SQL-level push-down for the five service-driven lists** — unchanged (the Python slice is correct; the push-down is a perf increment).
- **The `/accounts/search/` limit-contract migration** — unchanged (documented in the API guide).
- **The capped-default flip** — unchanged (after every consumer passes explicit limits; this sprint moves four more consumers onto explicit limits).
- **The 17 dev-tier npm-audit findings** (7 high) — the dedicated dependency sprint (unchanged).
- **The ruff mechanical batch** (936 production findings); **the audit-log INSERT policy** (DDL); **BE-L3 config-class locking**; **BE-L4 Peppol log-state locking**; **CSV errors[] raw strings**; **dead-letter design; UEN checksum; NULL-context SELECT tradeoff; H-05b models; PaymentsTab prefill; TanStack incompatibility; the membership-cache window; the journal detail N+1; the P20-era FE-M2/M3 designs; CI hardening; the version-story reconciliation** — the P21/P23/P24/P25 deferred registers carry forward unchanged.

## 5. Acceptance criteria

- The backend pins (all executed): the transmission-log limit-slice + total-count; the next/previous boundaries; the unpaginated envelope **byte-identical with the counters**; the counters within a status filter; the garbage/huge/offset-without-limit 400s; the forced-tie no-skip/no-dup; the paginated envelope carrying the counters.
- The frontend pins (all executed): every paginated hook carries the page identity in the queryKey (the cache-paging trap pinned per hook); `useContacts` returns the envelope; the five pages render `TablePagination` with the truthful summary; the invoices search goes server-side; the picker adapts.
- The live proof: the P26 e2e spec green (self-stocked fodder, idempotent re-run); the full gate matrix green (Phase 3.1); **the fresh-DB first-run green** (Phase 3.2).
- No schema change; no backend model change; `skills/` untouched by code checks; `git status` shows only the intended files.
- Plan + report saved under `docs/` in the `REMEDIATION_*_P26*` convention; the session log `docs/session_50.md`; the worklog updated.

## 6. Open decisions (resolved with judgment)

- **The sprint scope — the frontend wiring + the Peppol surface (not the SQL push-down):** the wiring is the user-facing gap (every list page unbounded) and the register's named next slice; the Peppol surface completes the backend list-contract story in the same stroke. The SQL push-down stays deferred (a perf increment with no behavioural gap).
- **The page size — 20 on every surface:** the ledger's convention (P24), one consistent control; the surfaces' volumes sit under one page in the demo substrate (verified), so the e2e contract stays stable.
- **The invoices search migrates server-side (not page-local):** a page-local search over 20 of N rows is a silent lie (misses everything beyond the page); the backend `?search=` + the hook's existing filter make the migration a wiring change, not a contract change. Debounced at 300ms, the contacts-page convention.
- **`useContacts` returns the envelope (a breaking hook change, consumers enumerated):** exactly two consumers exist (verified by sweep — `contacts-client.tsx`, `contact-picker.tsx`); both updated in this sprint; the picker keeps the unpaginated shape (search-bounded). The alternative (a second envelope-returning hook) would fork the cache key and double-fetch.
- **The Peppol counters computed once (conditional aggregation):** three `.count()` queries per request is the current shape; one `aggregate(Count(..., filter=...))` returns the same numbers. The counter semantics (within the filtered set) are pinned by test before the change.
- **`page_envelope`'s `extra` param (not a Peppol-local envelope builder):** the module is the single source of the envelope contract; a Peppol-local builder would fork the URL/next/previous logic the P24/P25 tests pin. The `extra` merge is additive — every existing caller byte-identical.
- **The e2e fodder is DRAFT (not APPROVED):** DRAFTs post no journal lines (zero F5/dashboard impact — the P25 sensitivity sweep's invariant), are visible on the invoices page (no status filter), and self-stock the spec's precondition idempotently (count-driven, the bootstrap's step-4c pattern).
- **The quotes page joins the sprint:** the same hook + the same component; the marginal cost is one page wiring + one spec extension; leaving it unwired would strand the documents endpoint half-paginated.
