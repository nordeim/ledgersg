# LedgerSG — Remediation Plan (P27 Sprint: The Pagination State-Machine Truth — The Debounce Race + The Reset-Consistency Completion)

**Date:** 2026-11-28 (session 52)
**Base commit:** `3aad8b63` (main — post-P26 + the session-51 narration log)
**Method for execution:** TDD (RED → GREEN → full gate) for every behavioural change; eslint parity on touched files; conventional commits on `main`; `skills/` excluded from all checks/tests/compilation; **no schema changes** (v1.2.2 carries forward); no backend changes at all (the defect class is entirely frontend state-machine wiring).
**Skills consulted:** `skills/skills-catalog.md` (343 skills) → `tdd` (the red→green loop), `nextjs16-tailwind4` (the data-surface + queryKey patterns), `tailwind-patterns` (the control styling), `agent-browser` (the live mobile-nav probe — executed this session, §1), `code-review`/`debugging-and-error-recovery` (Mode B/C discipline — the trace-driven root-cause isolation below), `rootless-postgresql` (the PG environment — live from the prior session, re-probed).

---

## 1. Audit inputs (this session's evidence)

- **Repo + docs truth pass:** `git pull` to `3aad8b63` clean on `main`; full reads of `AGENTS.md`, `CLAUDE.md` v2.27.0, `README.md`, `Project_Architecture_Document.md` v3.16.0, `ledgersg_SKILL.md` v2.13.0, `worklog.md`, `docs/session_50.md`, `docs/session_51.md`, the P26 plan + report, and `docs/Tailwind-V4-Validation-Report.md`.
- **The environment (live from the prior session, re-probed this session):** rootless **PG 17** on :5432 (both databases loaded — `ledgersg_dev` 30 domain tables + the django/public set, `test_ledgersg_dev`), **Redis** on :6379, the backend venv, `node_modules`, the dev stack (:8000 dev, :3000 `next dev`). One environment repair was required: the live cluster's `ledgersg_app` password had drifted from the documented default (`CHANGE_ME_IN_PRODUCTION`, schema §15) — the two RLS-perspective pytest gates failed with `password authentication failed`; after `ALTER ROLE` back to the documented default the suite reproduced **exactly**. The :8001 RLS instance was restarted under the corrected role password (the DEPLOYMENT §12.3 command, on a detached daemon) and the smoke re-ran green.
- **The baseline reproduction (pre-change, this session):** backend `pytest --reuse-db --no-migrations -q` **1021P/0F/5S** (28.81s; exact) · vitest **686/686 (80 files)** (99.38s; exact) · `npx tsc --noEmit` **0 errors** (exact) · whole-tree `npx eslint .` **0E/0W** (exact) · `rls_smoke.py` **13/13 as `ledgersg_app`** (exact) · `mobile-nav-audit.js` **17/17** (exact) · the dedicated Tailwind v4 `translate` probe: closed `-100%`/hidden → **8 mid-flight samples** (`-96.72% → -82.4856% → -54.2766% → -30.4783% → -16.2883% …`) → open `0px`/`role="dialog"` → Escape closes; computed `transitionProperty: "transform, translate, visibility"` · `npm audit` **0 critical** on the production set (17 dev-tier: 2 low / 8 moderate / 7 high; `--omit=dev` → 0) — **but the live `test:e2e:full` returned 42/43, not the documented 43/43** (reproduced three times; the failing spec: `invoices.spec.ts:446` — the P26 pagination walk). The P26 slice audit follows in §2.
- **The named focus — the mobile-nav verdict (twenty-second settlement):** **WORKING as expected; NO remaining Tailwind v4 bug on this surface.** The dedicated live probe (375px) plus the 17/17 audit — the drawer slides (8 intermediate `translate` values), the transition list carries the standalone `translate` property, the closed/open/Escape contract holds.
- **The audit (Mode C) of the P26 slice** (`95d7764b..3aad8b63`, hand-verified in source): `common/pagination.py`'s additive `extra` merge clean; `apps/peppol/views.py`'s parse/slice/aggregate/envelope sequence clean (counters computed once, byte-identical unpaginated, the `-transmitted_at, -id` tiebreaker); `use-invoices.ts`/`use-contacts.ts`/`use-banking.ts` page params + queryKey identity clean; `contact-picker.tsx`'s `data?.results` adaptation clean; `table-pagination` consumption on all five surfaces clean. **The defect is NOT in the transport or the envelope — it is in the page-state machines** (§2, H1).

**Combined findings (this session's audit): 0 Critical / 1 High / 2 Medium / 1 Low** — the High proven by executed trace evidence, not inspection alone.

## 2. Findings (verified, with evidence anchors)

### High

**FE-P27-H1 — the debounce mount-run resets the page: a Next click inside the window is silently reverted (the P26 e2e contract is broken by it).**
`apps/web/src/app/(dashboard)/invoices/invoices-client.tsx:80-86` and `contacts-client.tsx:62-68`:

```ts
React.useEffect(() => {
  const timer = setTimeout(() => {
    setDebouncedSearch(search.trim());
    setOffset(0); // a new search restarts the paging   ← the defect
  }, 300);
  return () => clearTimeout(timer);
}, [search]);
```

The timer body runs on the **mount-run** of the effect — `search` has not changed, but `setOffset(0)` fires anyway ~300ms after mount (and the effect re-runs under React StrictMode in dev, doubling the window to ~600ms). Any Next/Previous click landing inside that window is **silently reverted to page 1**: the offset state snaps back, the queryKey returns to the page-1 entry, and TanStack serves it **from cache — no refetch, no feedback, the click is simply lost**.

**Executed evidence (the full-run e2e failure, `invoices.spec.ts:446`, reproduced 3×):** the Playwright trace shows the `next.click()` dispatched at `22:23:57.701`; the network layer shows the page-2 request `?type=SALES_INVOICE&limit=20&offset=20` fired at `22:23:57.706` and answered **200 OK** in 93ms; the failure snapshot then shows the page at **"Showing 1–20 of 25 rows"** with Previous disabled and **no third network request** — the cache-served revert, exactly this defect's signature. The isolated re-run passes (the click lands outside the window by timing luck) — a textbook race that the serial full run loses deterministically and isolation wins. The P26 plan's own lesson ("the offset reset batches INTO the debounce tick — one render") fixed the double-fetch but introduced the mount-run reset: the reset was bundled with the timer instead of the value change.

**Fix (the codebase's own P25/FE-L3 convention — `ledger-client.tsx:33-38`):** the timer carries ONE state set (the value); the page restart moves to a **render-time value-change check** (`if (debouncedSearch !== lastDebounced)`) — the React-endorsed prev-state pattern, idempotent under StrictMode, never fires on mount. A real search change still resets the page (pinned by test before the change).

### Medium

**FE-P27-M2 — the banking lists never restart the paging when the filters change.**
`payment-list.tsx:32` and `transaction-list.tsx:38` hold `const [offset, setOffset] = useState(0)` with no reset keyed to the `filters` prop. The parent (`banking-client.tsx:419-431, 558-564`) holds the filters in `useState` — the prop identity changes exactly when the user changes a filter. A reader on page 2 (offset 20) who narrows the payment-type/reconciliation/date filter stays at offset 20 of the new filtered set — the P25 beyond-end math keeps the controls truthful ("Showing 0–0 of N"), but the invoices/contacts convention ("a new filter restarts the paging" — `contacts-client.tsx:122`) is not applied. Fix: the same render-time compare on the `filters` prop identity (+ the orgId prop — see M3).

**FE-P27-M3 — the five P26 surfaces never reset the offset on organisation switch (the ledger does).**
`ledger-client.tsx:33-38` resets the offset during render when `orgId` changes (P25/FE-L3, pinned by `ledger-org-switch.test.tsx` — the real-hook transport-URL spec). The five surfaces the P26 sprint paginated (`invoices-client`, `contacts-client`, `quotes-client`, `payment-list`, `transaction-list`) carry **no such reset**: switching org while on page 2 dispatches the new org's fetch at offset 20 — the stale-offset fetch + a garbage cache entry per switch (the exact defects the P25 sprint closed on the ledger). Fix: the same render-time compare on the org identity (from `useAuth()` for the page clients; the `orgId` prop for the banking lists).

### Low

**DOC-P27-L1 — the docs truths roll forward with the sprint** (the standing DOC-L pattern): README badge/counts + the P27 milestone, CLAUDE 2.27.0 → 2.28.0, AGENTS header + the P27 lessons, SKILL 2.13.0 → 2.14.0, PAD 3.16.0 → 3.17.0, DEPLOYMENT header/§7/§9, the API guide re-verified against the live stack (no API contract changes this sprint — the version row stays 3.5.0 unless re-verification finds drift), ci.yml counts, `.env.example`s re-verified (no new env vars expected).

## 3. The execution plan (phases, TDD)

### Phase 1 — RED: the regression specs (real-hook transport-mock, the `ledger-org-switch.test.tsx` pattern)

The lesson from P25 applies verbatim: **a module mock cannot observe a cache-served revert or a stale-offset dispatch** — only the REAL TanStack hook under a REAL QueryClient fetches what a committed render asks for. Every new spec below mocks only `@/lib/api-client` and asserts on the transport URLs + the rendered page-math summaries.

| Task | Test (RED first) |
|---|---|
| T1 | NEW `src/app/(dashboard)/invoices/__tests__/invoices-pagination-state.test.tsx`: (a) **the race** — render, await "Showing 1–20 of 51 rows", `fireEvent.click(Next)` (inside the mount-run window), await "Showing 21–40 of 51 rows", then wait 700ms past the mount window and assert the summary is STILL "Showing 21–40 of 51 rows" and the transport saw no revert (RED now: the summary flips to "Showing 1–20" — the cache-served revert); (b) **a real search change still resets** — type into the search box, advance past the debounce, assert the transport URL carries `search=` AND `offset=0` (the pin that the fix may not over-correct); (c) **the org switch resets** — walk to page 2, switch `currentOrg`, assert the new org is never fetched at `offset=20` (RED now: the P25 ledger pin applied to this surface). |
| T2 | NEW `src/app/(dashboard)/contacts/__tests__/contacts-pagination-state.test.tsx`: the same three contracts (the race; the search reset; the org switch) + (d) **the type-filter click still resets** (the existing behaviour at `contacts-client.tsx:122`, pinned). |
| T3 | NEW `src/app/(dashboard)/quotes/__tests__/quotes-pagination-state.test.tsx`: the org-switch reset contract (the surface has no search/filter — only M3 applies). |
| T4 | NEW `src/app/(dashboard)/banking/__tests__/payment-list-state.test.tsx`: (a) **the filter-change reset** — walk to page 2 under filters A, rerender with filters B (a new object identity), assert the transport URL for the new filters carries `offset=0` and never `offset=20` (RED now); (b) **the orgId-prop switch reset** — the same walk, rerender with a different `orgId`, the same assertion. |
| T5 | NEW `src/app/(dashboard)/banking/__tests__/transaction-list-state.test.tsx`: the same two contracts for the transactions surface. |

### Phase 2 — GREEN: the fixes

| Task | Fix | Verification |
|---|---|---|
| T6 | `invoices-client.tsx` — the debounce timer body drops `setOffset(0)` (the value set only); the render-time `lastDebounced` compare resets the page on the debounced VALUE CHANGE; the render-time `lastOrgId` compare (the ledger pattern) resets on org switch. | T1 (a)(b)(c) GREEN · the full existing invoices suite green (the P26 pins hold) |
| T7 | `contacts-client.tsx` — the same two render-time resets (the filter-click reset at line 122 stays — a user action, correct as-is). | T2 GREEN · the contacts suite green |
| T8 | `quotes-client.tsx` — the render-time `lastOrgId` reset. | T3 GREEN |
| T9 | `payment-list.tsx` + `transaction-list.tsx` — the render-time `lastFilters` (prop identity) + `lastOrgId` resets. | T4/T5 GREEN · the banking suites green |
| T10 | The live re-probe on the remediated dev stack: the invoices page paged live (Next → page 2 → wait past the window → still page 2 — the race gone in a real browser), the org-switch probe on the invoices surface. | the probe outputs recorded in the report |

### Phase 3 — the full gate matrix + the fresh-DB proof

1. The complete gate set on the remediated tree: backend `pytest` **1021P/0F/5S** (unchanged — no backend code touched) · vitest **686+15/(85 files)** · coverage green at the ratchet · `tsc` 0 · whole-tree `eslint` 0E/0W · live `test:e2e:full` **43/43 — deterministically this time** (the race window is structurally closed, not timing-narrowed) · `rls_smoke` 13/13 · `mobile-nav-audit.js` 17/17 (the twenty-third settlement) · `prod-csp-smoke.js` 5/5 (after a green `build:server`) · `npm audit` 0 critical.
2. **The fresh-DB proof** (the P26 acceptance convention): drop + recreate `ledgersg_dev` from `database_schema.sql` → restart both `--noreload` backends (8001 with `DB_USER=ledgersg_app`) → flush Redis → ONE §9 bootstrap run → `npm run test:e2e:full` → **43/43, 0 skipped, on the FIRST run** — proving the spec set's self-sufficiency holds on the P27 tree.
3. Screenshots: 8 DOM-verified captures (`docs/screenshots/168-175_*_session52.png`, md5-unique + non-blank pixel-verified, the session-45/48/50 capture conventions) — the invoices page 1 / **page 2 held** pair (the headline: the page-2 state persists past the old race window), the contacts page, the payments + transactions pages, the mobile drawer closed/open, the desktop band; the capture script `scripts/capture-screenshots-session52.js` (the session-50 pattern).
4. The `.env.example` truth verification (the config-readers sweep re-run; no new env vars expected — the finding noted in the report).

### Phase 4 — the docs truth pass

| Doc | Update |
|---|---|
| README.md | the badge/test arithmetic (vitest 686+15, e2e 43 — the race fix noted), the status-table rows, the P27 milestone section |
| CLAUDE.md | version 2.27.0 → 2.28.0, the status block, the P27 milestone block |
| AGENTS.md | the header gate row, the P27 lessons (the "a page reset belongs to the VALUE CHANGE, never the timer" + "a race proven by trace is a bug even when isolation passes" patterns) |
| ledgersg_SKILL.md | the quick-ref numbers, version 2.13.0 → 2.14.0 |
| Project_Architecture_Document.md | the lint/test count rows, version 3.16.0 → 3.17.0 |
| docs/DEPLOYMENT.md | the header re-verification line (session 52 / P27), §7/§9/§11 counts; re-validate the full fresh-host walkthrough against the current tree |
| API_CLI_Usage_Guide.md | re-verify the documented contracts against the live stack (no API changes this sprint; the version row stays 3.5.0 unless drift is found) |
| .github/workflows/ci.yml | the header comment counts |
| `.env.example` ×3 | re-verified truthful (no changes expected) |

## 4. Deferred register (updated, carried forward)

**Fixed this sprint (removed from the register):** the P26 pagination state-machine gaps on the five surfaces (the mount-run race + the filter/org reset consistency).

**Still deferred (with rationale, unchanged from the P26 register unless noted):**
- **The SQL-level push-down for the five service-driven lists** — unchanged (the Python slice is correct; the push-down is a perf increment).
- **The `/accounts/search/` limit-contract migration** — unchanged (documented in the API guide).
- **The capped-default flip** — unchanged.
- **The 17 dev-tier npm-audit findings** (7 high) — the dedicated dependency sprint (unchanged).
- **The ruff mechanical batch** (936 production findings); **the audit-log INSERT policy** (DDL); **BE-L3 config-class locking**; **BE-L4 Peppol log-state locking**; **CSV errors[] raw strings**; **dead-letter design; UEN checksum; NULL-context SELECT tradeoff; H-05b models; PaymentsTab prefill; TanStack incompatibility; the membership-cache window; the journal detail N+1; the P20-era FE-M2/M3 designs; CI hardening; the version-story reconciliation** — the P21/P23/P24/P25/P26 deferred registers carry forward unchanged.

## 5. Acceptance criteria

- The regression pins (all executed): the mount-window race cannot revert a page (the summary holds past the window; no cache-served revert); a real search change still resets the page; the type-filter click still resets (contacts); the org switch never dispatches the new org at a stale offset (all five surfaces); the banking filter change never dispatches the new filter set at a stale offset.
- The live proof: the full gate matrix green (Phase 3.1) with **e2e 43/43** — the P26 spec green in the serial full run, the exact failure mode of this session's baseline closed; **the fresh-DB first-run green** (Phase 3.2).
- No schema change; **no backend change at all**; `skills/` untouched by code checks; `git status` shows only the intended files.
- Plan + report saved under `docs/` in the `REMEDIATION_*_P27*` convention; the session log `docs/session_52.md`; the worklog updated.

## 6. Open decisions (resolved with judgment)

- **The sprint scope — the state-machine truth, not the SQL push-down:** the race is a *proven* broken contract (the documented 43/43 does not reproduce — 42/43, three times); the push-down is a perf increment with no behavioural gap. Correctness first; the register order stands.
- **The fix pattern — the render-time value-change check (not a `first-run` ref):** a skip-first-run ref still leaves a StrictMode window (the double-run defeats it); comparing the committed VALUE is idempotent under any effect-order and matches the codebase's own P25/FE-L3 convention (the ledger's `lastOrgId`) — one pattern, three reset causes (search value, org identity, filter identity).
- **The org-switch reset joins the sprint (M3):** the same one-line pattern per surface; the P25 sprint set the convention on the ledger and the P26 surfaces simply predate the application; leaving it would keep the garbage-cache-entry behaviour the ledger's own spec calls a defect.
- **No new e2e spec:** the P26/FE-P1 spec already walks the exact failing path (it is the regression test — it caught the bug); the vitest real-hook specs pin the state-machine contracts the e2e cannot isolate (the cache-served revert is invisible to URL counting). The e2e count stays 43.
- **The banking filter reset keys on the filters PROP IDENTITY (not deep equality):** the parent holds the filters in `useState` — the identity changes exactly when the user changes a filter and is stable across unrelated re-renders; deep equality would be speculative generality (no caller mutates in place).
- **The environment repairs (the `ledgersg_app` password drift, the 8001 restart) are session-log findings, not code findings:** the DEPLOYMENT §12.3 command is correct as documented; the drift was cluster state, corrected by the documented `ALTER ROLE`.
