# LedgerSG — Remediation Plan (P24 Sprint: The Server-Side List Pagination — The Ledger Line Materialisation First Target)

**Date:** 2026-11-27 (session 45)
**Base commit:** `05daa36f` (main — post-P23 + the session-45 log; all gates green at 969P/0F/5S backend · vitest 642/642 (76 files) · tsc 0 · eslint 0E/0W · live e2e 41/41 · rls_smoke 13/13 · mobile-nav 17/17 · prod-CSP 5/5 · npm audit 0 critical)
**Method for execution:** TDD (RED → GREEN → full gate) for every behavioural change; lint parity on touched files (eslint frontend); conventional commits on `main`; `skills/` excluded from all checks/tests/compilation; **no schema changes** (v1.2.2 carries forward); no backend model changes.
**Skills consulted:** `skills/skills-catalog.md` (343 skills) → `tdd` (the red→green loop; vertical slices, seams at the public interface — the pagination seam is the HTTP envelope), `nextjs16-tailwind4` (the frontend data-surface patterns), `tailwind-patterns` (the pagination control styling), `agent-browser` (the live mobile-nav probe — executed this session, see §1), `code-review`/`debugging-and-error-recovery` (Mode C discipline), `rootless-postgresql` (the PG environment — already live this session, §1).

---

## 1. Audit inputs (this session's evidence)

- **Repo + docs truth pass:** `git pull` to `05daa36f` clean on `main`; full reads of `AGENTS.md`, `CLAUDE.md` v2.24.0, `README.md`, `Project_Architecture_Document.md`, `ledgersg_SKILL.md` v2.10.0, `worklog.md`, `docs/session_44.md`, `docs/session_45.md`, the P23 plan + report (`docs/REMEDIATION_PLAN_2026-11-27_P23.md` — the applied mobile-nav drawer transition fix), and `docs/Tailwind-V4-Validation-Report.md` (Trap 5(b) — the standalone `translate` property).
- **The environment (carried live this session, verified):** rootless **PG 17** on :5432 (the `docs/setup_pg_z.sh` layout; roles `ledgersg` + `ledgersg_owner` + `ledgersg_app` verified; `ledgersg_dev` 37 tables + `test_ledgersg_dev` 45 tables — schema v1.2.2 loaded), **Redis** on :6379, the backend venv on :8000 + the :8001 RLS instance, `npm install`'d web tree, Playwright chromium, and the demo substrate (`E2E_DEMO` login verified 200; the dev DB holds **51 journal lines / 20 entries / 11 documents / 6 contacts / 9 payments** — real pagination fodder).
- **The full 9-gate baseline reproduced on this tree (all executed, green — the P23 claims re-Verified here):** backend `pytest --reuse-db --no-migrations -q` **969P/0F/5S** (20.78s) · vitest **642/642 (76 files, 96.28s)** · `npx tsc --noEmit` **0 errors** · whole-tree `npx eslint .` **0E/0W** · live `test:e2e:full` **41/41** (2.2m) · `rls_smoke.py` **13/13 as `ledgersg_app`** on the :8001 instance · `mobile-nav-audit.js` **17/17** at 375/800/1280 (the sixteenth settlement) · `prod-csp-smoke.js` **5/5** · `npm audit` **0 critical** (17 dev-tier findings; `npm audit --omit=dev` → **0** — the production set clean).
- **The named focus — the mobile navigation verdict (this session, live agent-browser + the full gate set):** **WORKING as expected; NO remaining Tailwind v4 bug on this surface.** The functional contract is green (17/17 live probe + the 12/12 + 7/7 vitest suites + the 6 e2e specs inside the 41/41 run), AND the animation contract is green (the P23 fix verified live again): the aside's computed `transitionProperty` reads `"transform, translate, visibility"` (desktop + mobile viewports), the closed drawer reads `translate: -100%` + `visibility: hidden`, a 120ms post-click sample caught the slide **mid-flight at `translate: -40.963%`**, the open drawer reads `translate: 0px` + `visibility: visible` + `role="dialog"`, and Escape closes it back to `-100%`. The v4 hygiene sweep stays clean (the `tw-animate-css` import, no legacy config, the v4-correct chevrons, the Trap-4 `space-y` probe re-run inside the 17/17).
- **The audit (Mode C) of the current codebase — the registered deferral picked as the sprint target:** **no list endpoint paginates.** Every list returns the FULL matching set inside `{results, count}` (the P21 envelope was explicitly "the prerequisite for pagination"). The unbounded surfaces: `LedgerView` (line-level — one row per journal line, grows with every posting; the register's named first target), `JournalEntryListCreateView` (entries), `InvoiceDocumentListCreateView` (documents), `ContactListCreateView`, `PaymentListView`, `BankTransactionListView`. The frontend ledger page renders every line (`useLedger` passes no limit; no pagination controls exist anywhere in the web app; `InvoiceListResponse` already declares unused optional `next`/`previous` fields — the type was designed for this sprint).
- **The pagination-correctness prerequisite audit (verified in source):** every candidate surface already has a deterministic total order — `(org_id, entry_number)` is UNIQUE (schema `uq_entry_org_number`) so the ledger's `(-entry__entry_date, -entry__entry_number, line_number)` and the entries list's `(-entry_date, -entry_number)` are total orders; documents order by `(-issue_date, -document_number)`; contacts by `name` and payments by `(-payment_date, -created_at)` carry no unique tiebreaker (a cross-page skip/dup hazard under ties — the fix registers below); transactions carry `id` (total). `parse_int_param` (the typed-400 query-param helper, P7/F-11 + P8/G-2) already exists for the limit/offset parsing.
- **Test-infra review:** `vitest.config.ts` (the 71/60/68/71 whole-suite ratchet + 5 per-glob floors + the documented `src/stores/**` exclusion) and `playwright.config.ts` (chromium default, serial live-suite contract P16/FE-M4, `retain-on-failure` trace+video, `Asia/Singapore`/`en-SG` pins, `expect.timeout 10s`) both structurally correct — the P23 conclusion re-affirmed: the task's "add vitest and playwright test suite by modifying the respective config files" is satisfied by **adding suites under the existing configs** (this sprint: 1 new vitest spec file + 2 extended spec files + 1 new e2e case) rather than churning proven gates.
- **Docs truth audit (re-measured):** the top status blocks are P23-truthful; the second-tier surfaces sit on P23 numbers and roll forward with the P24 counts at the end of this sprint (the registered DOC-L pattern). The `.env.example`s were re-verified truthful in P23; re-verified again this session (the config-readers sweep unchanged — no new env vars this sprint).

**Combined findings (this session's audit): 0 Critical / 0 High / 2 Medium / 3 Low / 3 Informational** — every execution-scoped finding hand-verified in source/live (anchors below).

## 2. Findings (verified, with evidence anchors)

### Medium

**BE-P24-M1 — THE headline (the registered big-ticket deferral): the list layer returns EVERY matching row — no server-side pagination on ANY list endpoint.**
Six core list surfaces materialise the full org history per request: `apps/journal/views.py:369` (LedgerView — line-level, unbounded: every posting adds rows), `apps/journal/views.py:42` (entries), `apps/invoicing/views.py:179` (documents), `apps/invoicing/views.py:73` (contacts), `apps/banking/views.py:178` (payments), `apps/banking/views.py:427` (transactions). The response payload grows without bound — the ledger endpoint returns the org's entire journal-line history in one payload. The P21 envelope unification was registered as exactly this prerequisite. Fix (the additive contract): a shared `common/pagination.py` — `?limit=N&offset=M` query params (typed 400s on garbage per the P7/F-11 convention; limit clamped to [1, 1000]); **when `limit` is absent the response stays byte-identical `{results, count}`** (every existing consumer — e2e, bootstrap, rls_smoke, five frontend hooks — keeps working unchanged); when present the envelope gains `next`/`previous` (absolute URLs carrying limit+offset+filters, DRF-style) and `count` reads as the TOTAL matching rows (which equals `len(results)` only in the unpaginated mode — the semantic is documented in the API guide). LedgerView paginates at the SQL level (`queryset.count()` + `queryset[offset:offset+limit]` — the named first target); the five service-driven lists take the sequence-level helper this sprint (envelope + payload bounded; pushing LIMIT/OFFSET into the service signatures registers as the next increment).

**FE-P24-M2 — the ledger UI has no pagination controls and the hook never passes a limit.**
`apps/web/src/hooks/use-ledger.ts:41` (no limit/offset; the queryKey `[orgId, "ledger", filters]` has no page identity — a cache-paging trap: pages would serve each other's cached data), `apps/web/src/app/(dashboard)/ledger/ledger-client.tsx:19` (renders every line), and no pagination component exists in `src/components/`. Fix: `useLedger` gains `limit`/`offset` params **included in the queryKey**; a shared accessible `TablePagination` (`src/components/ui/table-pagination.tsx` — nav semantics, real Previous/Next buttons, a "Showing x–y of z" summary, disabled states); the ledger client wires page state at page size 50 (the dense data surface; the demo substrate's 51 lines → 2 live pages).

### Low

**FE-P24-L1 — the queryKey page-identity trap.** Adding offset to the fetch without adding it to the queryKey makes TanStack serve page 2 from page 1's cache. Pinned by its own test (two offsets, distinct cache entries).

**DOC-P24-L2 — the second-tier doc surfaces sit on P23 numbers** (the registered roll-forward): README badge/status rows, AGENTS header gate row, CLAUDE.md status/gate rows, `ledgersg_SKILL.md` quick-ref, PAD rows, DEPLOYMENT header/§7/§9/§11 counts, the API guide version row — every count re-measured after the gates; the API guide moves 3.2.1 → **3.3.0** (an API-surface change this time — the pagination contract + CLI examples).

**CFG-P24-L3 — the suite counts grow:** backend 969 → 969+N (the pagination contract file), vitest 642 → 642+M (the new component spec + the extended hook/page specs), e2e 41 → **42** (the P24 ledger pagination spec, backend-gated; the always-green 11 unchanged).

### Informational

**I1 — the ordering tiebreakers.** Contacts (`order_by("name")`) and payments (`order_by(-payment_date, -created_at)`) lack a unique final tiebreaker — a cross-page skip/dup hazard once paginated (Postgres tie order is not stable across executions). Fix rides with M1: append the `id` tiebreaker (contacts: `name, id`; payments: `-payment_date, -created_at, id`) with a no-skip/no-dup test under forced ties. The ledger/entries/documents/orders already carry unique keys.
**I2 — the 17 dev-tier npm-audit findings stay deferred** (2 low / 8 moderate / 7 high — the typescript-eslint 8.x stack, vite, undici chains needing major bumps; `npm audit fix` dry-run measured **49 package changes** — a blind fix could un-green the tree; the dedicated dependency sprint decision re-affirmed; the production set is clean at 0).
**I3 — the mobile-nav surface needs no further work this sprint** — the sixteenth settlement closes the loop the P23 gates already pin (the `shell-drawer-transition` spec + the `P23/FE-M1` e2e + the live mid-flight sampling above).

## 3. The execution plan (phases, TDD)

### Phase 1 — RED: the pagination contract tests (backend + frontend + e2e)

| Task | Test (RED first) |
|---|---|
| T1 | New `apps/backend/tests/integration/test_pagination_p24.py`: (a) the ledger endpoint unpaginated → exactly `{results, count}` (the back-compat pin — no `next`/`previous` keys); (b) `limit=10&offset=0` → 10 results, `count` = the TOTAL (not the page size), `next` URL contains `limit=10&offset=10`, `previous` is null; (c) the last page / offset-beyond-end → empty or partial results + `next` null + a valid `previous`; (d) garbage `limit` ("abc" / 0 / -5 / 1001) and garbage `offset` ("abc" / -1) → the typed 400 envelope; (e) the five other endpoints (entries, documents, contacts, payments, transactions) → the limit slice + total-count + next/previous boundaries; (f) the tiebreaker test — two same-name contacts, `limit=1` → the two pages carry both rows exactly once (no skip, no dup). |
| T2 | Frontend vitest: new `src/components/ui/__tests__/table-pagination.test.tsx` (renders the "Showing 1–50 of 51" summary; Previous disabled on page 1; Next disabled at the end; clicks fire the handlers; the nav landmark + button names are accessible); extended `src/hooks/__tests__/use-ledger.test.tsx` (limit/offset forwarded as query params; the queryKey varies with offset — the stale-cache trap pin); extended `src/app/(dashboard)/ledger/__tests__/ledger-page.test.tsx` (the paginated shape renders the controls + the summary). |
| T3 | New e2e case in `apps/web/e2e/ledger.spec.ts` (`P24/FE-P1`, no existing spec modified): the ledger page shows the pagination summary over the real backend rows; Next loads the second page (the row set changes / the summary advances); Previous returns. Backend-gated like its file sibling. |

### Phase 2 — GREEN: the pagination contract implementation

| Task | Fix | Verification |
|---|---|---|
| T4 | Backend: new `apps/backend/common/pagination.py` (`parse_limit_offset` — typed 400s via the existing `parse_int_param` conventions, limit ∈ [1, 1000]; `build_page_response(request, items, total)` — the `{results, count, next, previous}` envelope with absolute next/previous URLs); `LedgerView` paginates at the SQL level (`count()` + `queryset[offset:offset+limit]`); the five service-driven views integrate the sequence-level helper; the contacts/payments order tiebreakers (`name, id` / `-payment_date, -created_at, id`). | T1 GREEN · the full backend suite re-run · the envelope shape asserted both ways |
| T5 | Frontend: `useLedger` limit/offset params + queryKey identity; new `src/components/ui/table-pagination.tsx`; `ledger-client.tsx` page state at page size 50. | T2 GREEN · `tsc` 0 · eslint 0 on touched files · the coverage gate green at the ratchet (the new component carries thorough tests — the components-tier floor cannot regress) |
| T6 | The live re-probe on the remediated stack (agent-browser): the ledger page paginates in the real DOM (page 2 loads on Next). | the probe output recorded in the report |

### Phase 3 — the full gate matrix + the deliverables

The complete gate set on the remediated tree: backend `pytest` 969+N/0F/5S · vitest 642+M/(77+ files) · coverage green at the ratchet · `tsc` 0 · whole-tree `eslint` 0E/0W · live `test:e2e:full` **42/42** · `rls_smoke` 13/13 · `mobile-nav-audit.js` 17/17 (the seventeenth settlement) · `prod-csp-smoke` 5/5 · `npm audit` 0 critical.

Deliverables: 8 DOM-verified screenshots (`docs/screenshots/144-151_*_session45.png`, md5-unique + non-blank pixel-verified, mirroring the session-44 capture conventions — the ledger page 1 / page 2 (the paginated controls live), the mobile drawer closed/open, the desktop band, the invoices + banking + settings surfaces on the remediated stack); the P24 report (`docs/REMEDIATION_2026-11-27_P24_REPORT.md`); the session log (`docs/session_46.md`); the worklog entry; the docs truth pass (§2 DOC-L2); the `.env.example` re-verification note; the conventional commits + the SSH-wrapper push to main.

### Phase 4 — the docs truth pass

| Doc | Update |
|---|---|
| README.md | the badge/test arithmetic (backend 969+N, vitest 642+M, e2e 42), the status-table rows, the P24 milestone section (the list-pagination contract) |
| CLAUDE.md | version 2.24.0 → 2.25.0, the status block, the P24 milestone block |
| AGENTS.md | the header gate row, the P24 lessons (the "page identity must live in the queryKey" + the "envelope contracts pin both modes" patterns) |
| ledgersg_SKILL.md | the quick-ref numbers, version 2.10.0 → 2.11.0 |
| Project_Architecture_Document.md | the lint/test count rows |
| docs/DEPLOYMENT.md | the header re-verification line (session 45 / P24), §7/§9/§11 counts, the §9 ledger note (the page size), the npm-audit note carried |
| API_CLI_Usage_Guide.md | the version row 3.2.1 → **3.3.0** + the **P24 pagination addendum** (the `?limit=&offset=` contract, the count/next/previous semantics, the 1..1000 clamp + the typed 400s, CLI paging examples) |
| .github/workflows/ci.yml | the header comment counts |
| `.env.example` ×3 | re-verified truthful (no changes expected — no new env vars this sprint; the verification noted in the report) |

## 4. Deferred register (updated, carried forward)

**Fixed this sprint (removed from the register):** the list-pagination contract on the six core surfaces (M1) — the P21-era register's big-ticket item; the ledger UI pagination (M2); the queryKey page-identity trap (L1); the contacts/payments order tiebreakers (I1); the second-tier docs roll-forward (L2).

**Still deferred (with rationale, unchanged from the P23 register unless noted):**
- **The SQL-level push-down for the five service-driven lists** — the services materialise `list(...)`; this sprint bounds the payload at the view layer; pushing LIMIT/OFFSET through the service signatures (and returning totals) is the next increment once the frontend consumers migrate.
- **The frontend pagination wiring for invoices / contacts / payments / transactions** — the backend contract now supports them; the UI pages (filter bars + page state) register as the next UX slice.
- **The capped-default flip** — the unpaginated default stays for back-compat; once every consumer passes explicit limits, the default can flip to a capped page with a migration note.
- **The 17 dev-tier npm-audit findings** (7 high) — the dedicated dependency sprint with lockfile review (the 49-package `audit fix` dry-run measured too risky for this sprint's scope).
- **The ruff mechanical batch** (936 production findings); **the audit-log INSERT policy** (DDL); **BE-L3 config-class locking**; **BE-L4 Peppol log-state locking**; **CSV errors[] raw strings**; **dead-letter design; UEN checksum; NULL-context SELECT tradeoff; H-05b models; PaymentsTab prefill; TanStack incompatibility; the membership-cache window; the journal detail N+1; the P20-era FE-M2/M3 designs; CI hardening; the version-story reconciliation** — the P21/P23 deferred registers carry forward unchanged.

## 5. Acceptance criteria

- The pagination contract pinned both ways (all executed): unpaginated → `{results, count}` byte-identical (the back-compat test); paginated → `{results, count, next, previous}` with `count` = the total, next/previous carrying limit+offset+filters, boundaries correct (first page `previous: null`, last page `next: null`, offset-beyond-end → empty), garbage limit/offset → typed 400s.
- The ledger endpoint paginates at the SQL level (`count()` + the queryset slice — the query log shows LIMIT/OFFSET).
- `useLedger` forwards limit/offset AND the queryKey varies with them (the stale-cache pin); the ledger page renders the shared `TablePagination` (a11y: nav landmark, button names, disabled states) at page size 50.
- The full gate matrix green on the remediated tree: backend 969+N/0F/5S · vitest 642+M · coverage green at the ratchet · tsc 0 · eslint 0E/0W · live e2e:full **42/42** (the P24 spec included) · rls_smoke 13/13 · mobile-nav 17/17 · prod-CSP 5/5 · npm audit 0 critical.
- The tiebreaker test green (two same-name contacts paginate without skip/dup).
- No schema change; `skills/` untouched by code checks; `git status` shows only the intended files (the backend module + 6 views + 1 test file + the service tiebreakers + the frontend component/hook/client + 3 test files + 1 e2e file + package files if any + the docs + the screenshots).
- Plan + report saved under `docs/` in the `REMEDIATION_*_P24*` convention; the session log `docs/session_46.md`; the worklog updated.

## 6. Open decisions (resolved with judgment)

- **The unpaginated default stays (additive back-compat):** flipping the default to a capped page would change every consumer's contract in one shot (the e2e specs, the bootstrap script, rls_smoke, five frontend hooks). The additive path ships the capability + the first consumer (the ledger UI) with zero breakage; the flip registers as the future default-change once all consumers pass explicit limits.
- **`limit`/`offset` (not `page`/`page_size`):** the offset primitive is CLI-friendly (the API guide's audience), matches the `next`/`previous` URL math directly, and needs no page-size round-trip; page arithmetic stays a frontend concern.
- **A typed 400 on out-of-range limit (1..1000) — explicit beats silent clamping:** the repo's garbage-param convention (P7/F-11/P8/G-2); a silent clamp would hide a caller's paging bug.
- **`count` semantics = the total matching rows:** identical to today's unpaginated value; the API guide documents that `len(results) < count` marks a page. No new field needed.
- **`next`/`previous` as absolute URLs (DRF convention):** self-describing for CLI operators; built via `request.build_absolute_uri` with the caller's filters preserved.
- **SQL-level on LedgerView only this sprint:** the services return materialised lists; changing five signatures (+ the totals return shape) doubles the blast radius for no user-visible gain this sprint. The payload is bounded now; the query push-down registers next.
- **Page size 50 on the ledger UI:** a dense financial table; the demo substrate's 51 lines exercise the controls live (2 pages) in the e2e.
- **The npm-audit remainder stays deferred:** the measured 49-package `audit fix` footprint is a dependency sprint, not a rider on this one.
- **The mobile-nav focus needs no code this sprint:** the sixteenth settlement (17/17 + the live mid-flight sampling + the P23 gates) confirms the surface; the sprint budget goes to the register's big-ticket deferral.
