# LedgerSG — Remediation Plan (P17 Sprint: Concurrency Truth, the 400-Contract Sweep, the Celery Tenant Context & the Docs Truth Debt)

**Date:** 2026-11-27 (session 34)
**Base commit:** `e9b2626d` (main — post-P16, all gates green at 860P/0F/5S backend · 554/554 vitest · tsc 0 · eslint 9 (src) · live e2e 40P/0F/0S · rls_smoke 13/13 · mobile-nav 17/17 · prod-CSP smoke 5/5 · schema v1.2.0)
**Method for execution:** TDD (RED → GREEN → full gate) for every behavioural fix; lint parity on touched files; conventional commits on `main`; `skills/` excluded from all checks/tests/compilation; schema untouched this sprint (no DDL needed — every fix is application-layer).

---

## 1. Audit inputs (this session's evidence)

Three parallel deep audits (Mode C) + lead hand-verification of every
Critical/High finding in source, plus the live baselines reproduced on a
**fresh clone** (the workspace had been reset — repo re-cloned from
`github.com/nordeim/ledgersg`, PostgreSQL 17 + Redis 8 reinstalled from
`docs/setup_pg_z.sh` + `skills/rootless-postgresql/SKILL.md`, both DBs
loaded with schema v1.2.0, `ledgersg_app` password restored to the
documented dev default):

- **Baselines reproduced** (all executed, green):
  backend **860P/0F/5S** · invariants 34P · security 76P/3S ·
  vitest **554/554** (64 files) · tsc 0 · eslint **9** (`src/`) ·
  `manage.py check` 0 errors (the documented W001 only) ·
  **mobile-nav live probe 17/17 PASS at 375/800/1280** (toggle, closed-drawer
  `visibility:hidden`, overlay, X hit-target, transition-aware close, no
  overflow, no console errors, sticky tablet/desktop, the v4 space-y trap
  sweep clean) — **the navigation works; no TailwindCSS v4 bug exists**
  (the P12/P13/P15/P16 verdicts re-settled live on the fresh clone; the v4
  setup is CSS-first-clean: `@import "tailwindcss"` + `@theme`, no legacy
  config, no deprecated utility traps in the compiled CSS).
- **payment.py / serializer regression check (session_29, P14 partial
  completion and save)** — verified via git commit history of the files:
  `2bcb43f0` ("partial p14 changes", 2026-11-25) overwrote
  `apps/core/models/payment.py` (the MODEL) with serializer code (circular
  import; `manage.py check` could not run) and stranded the P14 fixes at
  wrong paths → `d47e4923` (P15) restored the model from `2bcb43f0~1` and
  relocated the stranded modules → `8d185bad` (P16) fixed the residual wire
  serializer gap (the dedicated allocate endpoint still demanded
  APPROVED-only). **Current tree state verified clean:** the `Payment`
  model is intact (`apps/core/models/payment.py:11`, maps
  `banking.payment`), `ALLOCATABLE_STATUSES` is identical across
  `apps/banking/serializers/allocation.py:21`,
  `apps/banking/serializers/payment.py:93` and the service guard, and the
  full suite (860P/0F/5S) covers the instalment contract (endpoint-level
  P16 tests). **No regression remains.**
- **Vitest + Playwright suites verified present and green** (the user-facing
  ask): `vitest.config.ts` (jsdom, coverage ratchet with per-glob lib floor)
  and `playwright.config.ts` (chromium default, 5-browser opt-in matrix,
  serial live-suite contract, webServer) both exist and run —
  `npm test` 554/554, chromium headless shell installed,
  `scripts/mobile-nav-audit.js` 17/17. P17 strengthens them (new unit
  tests for the proxy nonce orchestration, the lint gate added to CI, new
  backend regression tests) rather than re-adding what exists.
- **Backend audit** (P16 diff + payment/serializer/banking/gst/journal
  perimeter + views/authn/RLS/tests/deps): **0 Critical, 3 High, 7 Medium,
  6 Low, 9 Informational** — every High/Medium verified in source by the
  lead (two verified live in the venv: `Decimal(str(None))` etc. raise
  `InvalidOperation`; Django 6 reads `STORAGES` only).
- **Frontend audit** (P16 surfaces + security + a11y + query keys + tests +
  config + compiled-CSS v4 sweep): **0 Critical, 0 High, 4 Medium, 6 Low,
  9 Informational** — every Medium verified in source and compiled build
  artifacts by the lead (the `success` token is absent from the compiled
  CSS; production nonce CSP re-verified end-to-end on a live boot).
- **Cross-cutting truth audit** (docs vs tree, deployment guide, API guide,
  env examples, scripts, CI, git hygiene): **1 High, 11 Medium, 12 Low** —
  the High (invalid GST example in DEPLOYMENT.md §9/§11 bootstrap) was
  found by the lead live (the documented payload 400s against the P15
  honest validator) and independently re-verified.

## 2. The findings (verified, with evidence anchors)

### High

**BE-H1 — `create_reversal` has no already-reversed guard: a sequential
double-reversal corrupts the GL.**
`apps/journal/services/journal_service.py:400-455` — the method fetches the
original with `JournalService.get_entry()` (no `select_for_update`, no
`is_reversed` check). The schema's `chk_reversal_consistency` only requires
the flag+pointer pair to agree, so a second POST to
`/api/v1/{org}/journal-entries/{entry_id}/reverse/` happily creates a second
swap-side entry (every affected account misstated by 2× the original) —
and the trial balance stays balanced, so nothing detects it. The P13/B-11
comment in the file itself names the double-reversal hazard yet the guard
was never added. **Fix:** `select_for_update()` the original inside the
atomic block and refuse with a typed `ValidationError` when `is_reversed`
is already true.

**BE-H2 — `PaymentService.void()` takes no row lock: concurrent
double-void double-reverses the payment's GL entry.**
`apps/banking/services/payment_service.py:272-300` — `void()` reads via
plain `PaymentService.get()` then checks `is_voided`; two concurrent voids
both read `is_voided=False` (READ COMMITTED) and both proceed. P16/BE-M1
locked `allocate()` and P16/BE-L3 locked `file_return`/`amend_return` —
`void()` is the missed sibling (the document path locks correctly,
`document_service.py:876-879`). **Fix:** lock the payment row first
(`select_for_update`), re-check `is_voided` after the lock.

**BE-H3 — Celery tasks run with no RLS tenant context: invoice email and
InvoiceNow transmission silently never execute in production.**
`apps/invoicing/tasks.py:29-31` and `apps/peppol/tasks.py:58-60` query
tenant tables (`InvoiceDocument.objects.get(...)`,
`execute_transmission_for_log`) with no `app.current_org_id` set. Every
tenant SELECT policy is `USING (org_id = core.current_org_id())` and
`core.current_org_id()` returns NULL when unset — a worker process never
sets it → 0 rows → `DoesNotExist` → `self.retry` ×3 → task dies, while the
API already answered `{"sent": true}`. It works in dev/test only because
`CELERY_TASK_ALWAYS_EAGER=True` (development/testing) runs the task
synchronously inside the middleware's transaction where the context IS set;
`production.py:98` disables eager mode. The dispatch sites also fire
`.delay()` **inside** the request transaction
(`document_service.py:1031, 1117, 1254`) — a worker can race the
uncommitted row. The codebase already solved this class for org creation
(P14/C-1: `SELECT set_config('app.current_org_id', %s, true)`).
**Fix:** a shared tenant-context helper wrapping both task bodies +
`transaction.on_commit` dispatch at the three seams.

### Medium (backend)

**BE-M1 — non-numeric GST box override → unhandled `InvalidOperation` →
500.** `apps/gst/views.py:394-406` — `Decimal(str(v))` raises for
`None`/`dict`/`"garbage"` (verified live in the venv); the serializer's
`boxes` is a bare `DictField` so values arrive untyped. P16/BE-M2 covered
NaN/Infinity, not malformed types. Fix: catch `InvalidOperation`/`TypeError`
→ typed `ValidationError` (400).

**BE-M2 — bulk allocation with a non-UUID `document_id` → unhandled
Django `ValidationError` → 500.** `apps/banking/serializers/allocation.py:137-146`
— `allocations` is `ListField(child=DictField())`; the embedded path has a
`UUIDField`, the bulk path does not. Django's `UUIDField.to_python` raises
`django.core.exceptions.ValidationError` (not `DoesNotExist`, not an
`APIException`) → the custom handler 500s. Fix: typed UUID validation per
allocation.

**BE-M3 — UEN normalization applied on create only; both PATCH paths still
store raw, unvalidated UEN.** `apps/core/views/organisations.py:114-117`
(detail PATCH) and `:334-337` (settings PATCH) — the P16/BE-L7
normalize+validate block (`organisation.py:126-129`) runs on create only;
PATCH calls `ensure_uen_available()` on the raw (case-sensitive) value and
stores unnormalized strings. Fix: share a `normalize_uen()` helper across
all three write paths.

**BE-M6 — `TaxCodeUpdateSerializer` lacks the rate range check the create
path has → DB CHECK violation 500.** `apps/gst/serializers.py:94-103` vs
`:87-91`; `chk_rate_range` (`database_schema.sql:667`) rejects `rate` outside
0..1 at the DB, surfacing as an unhandled `CheckViolation` 500 instead of
a 400. Fix: mirror the create-path `validate_rate` on the update serializer.

**BE-M7 — N+1 query patterns on the three main list endpoints.**
`payment_service.py:225-248` + `PaymentSerializer` FK traversal;
`document_service.py:108-128` + `InvoiceDocumentListSerializer.contact_name`;
`reconciliation_service.py:53-70` + `BankTransactionSerializer.bank_account_name`.
No `select_related` anywhere; unpaginated materialization (the registered
BE-L6 deferral) multiplies it. Fix: `select_related("contact",
"bank_account")` / `select_related("contact")` / `select_related("bank_account")`.

**BE-M5 — one payment can be reconciled to multiple bank transactions; no
row locks in `reconcile()`.** `reconciliation_service.py:264-333` — checks
`transaction_obj.is_reconciled` but never the payment side; `suggest_matches`
filters `is_reconciled=False` (line 407) but the write path trusts the
caller. Sequential double-reconcile of payment P to transactions A and B
double-counts the bank reconciliation. Fix: refuse when the payment is
already matched + lock both rows.

**BE-M4 — org-membership cache (5-min TTL) never invalidated.**
`common/middleware/tenant_context.py:231-247` — carried forward on the P15
register (B-9); the removal/invite-acceptance flows that would own the
invalidation keys do not exist yet. **Registered as deferred again** (needs
the membership-management surface to invalidate from); the interim
mitigation — stop caching negative lookups — is a one-line change worth
taking this sprint.

### Medium (frontend)

**FE-M1 — the `success` color token does not exist: 14 class usages across
10 files generate no CSS.** `src/app/globals.css:9-89` defines no
`--color-success` (verified: absent from the compiled production CSS), yet
`text-success`/`bg-success` are used on the PAID badge
(`invoice-detail-client.tsx:51`), reconcile forms, match scores, fiscal and
InvoiceNow settings cards. The PAID badge renders white-on-transparent;
green financial semantics silently vanish. Fix: add `--color-success` to
`@theme` (the "Illuminated Carbon" accent green) — one line, widest blast
radius.

**FE-M2 — `npm run lint` exits 1 (6 errors) and CI has no lint gate.**
3× `react-hooks/set-state-in-effect` errors (the `mounted`-pattern trio:
`gst-chart-wrapper.tsx:14`, `banking-client.tsx:404`, `layout.tsx:18`), 2×
`react-hooks/immutability` errors in `auth-provider-session.test.tsx`, 1×
`prefer-const` in `e2e/p11.spec.ts:234`; `ci.yml` runs tsc/vitest/build but
no lint. Also the "eslint 9" register counts `src/` only — the whole tree
is 11 (2 in `e2e/`). Fix: clear the 6 errors, then add the lint gate to CI
with `--max-warnings` parity so the count cannot drift silently again.

**FE-M3 — the P16 nonce-CSP proxy orchestration has zero automated
coverage.** No test imports `src/proxy.ts`; Playwright's webServer always
boots `next dev` (whose CSP is the dev exemption set) — the exact FE-C1
failure class stays invisible to every suite except the manual
`prod-csp-smoke.js`. Fix: a vitest unit test driving `proxy()` with a
`NextRequest` (request-header CSP + `x-nonce` forwarding + response CSP +
per-request nonce rotation).

**FE-M4 — the unsaved-changes guard is written but never read: dirty
invoice/quote data is lost silently.** `invoice-store.ts:25,34`
(`hasUnsavedChanges`) + writer (`invoice-form.tsx:48,134-136`) exist, but
zero consumers; no `beforeunload` listener anywhere in `src/`. A user
typing a long invoice who navigates or closes the tab loses everything.
Fix: wire a `beforeunload` effect on `hasUnsavedChanges`.

### Low (selected — the ones that carry correctness weight; the rest ride the register)

**BE-L2 — bank-transaction reconcile/unreconcile routes use `<str:>` +
raw `UUID()`: malformed id → 500.** `apps/banking/urls.py:67-80` +
`views.py:549,579` — every sibling route uses `<uuid:…>`; fix the two
routes (or `parse_uuid_param`).

**BE-L3 — `/admin/` mounted unconditionally in production.**
`config/urls.py:165` — the comment says "development only in production"
but no gate exists (debug_toolbar is correctly gated at `:29-34`).

**BE-L4 — `STATICFILES_STORAGE` is a silent no-op on Django 6.**
`base.py:185`, `production.py:142` — Django 6 reads only `STORAGES` (grep
of installed django: zero reads of the legacy setting); WhiteNoise
compressed-manifest storage is never active. Fix: migrate to the
`STORAGES` dict.

**BE-L1 — `exchange_rate` silently truncated to 4 dp before storage and FX
math.** `payment_service.py:102,161` — `money()` quantizes to 0.0001 while
the wire contract and column are 6 dp (`NUMERIC(12,6)`); base amounts
drift deterministically on 6-dp rates. Fix: validate the rate at 6 dp
without `money()`'s quantize; keep the monetary products quantized.

**FE-L1 — CSP carries four dead third-party origins.** `src/lib/csp.ts:53-56`
— fonts are self-hosted via `next/font`; the two API origins map to
`.env.example` "RESERVED — NOT READ" flags. Fix: drop all four (re-add when
the integrations actually ship).

**FE-L2 — dead utilities `bg-background` / `text-foreground`.**
`payment-filters.tsx:96,110`, `transaction-filters.tsx:145,159`,
`ui/alert.tsx:6` — no such tokens in `@theme`; date inputs render
transparent. Fix: sweep to existing tokens (`bg-surface`, etc.).

**FE-L3 — dead code surviving the P16 sweep.**
`use-dashboard.ts:24-44` (`useComplianceAlerts`, zero consumers),
`auth-provider.tsx:331-344` (`useCurrentOrg` — throws during render when
org is null), `invoice-store.ts` unconsumed fields
(`sidebarCollapsed`/`compactMode`/`bcrsEnabled`/`currentTotals`/
`updateTotals`/`resetStore`, and `createInvoiceLine` duplicating
`createEmptyLine`). Fix: delete.

**FE-L4 — org-selector dropdown a11y gaps.** `shell.tsx:254-292` — no
`aria-expanded`/`aria-haspopup` on the trigger, no Escape/outside-click
close, no arrow-key navigation. Fix: the Radix menu contract (the mobile
drawer is the exemplar).

**FE-L5 — refresh-failure hard redirect loses `?redirect=`.**
`api-client.ts:129-134` — `window.location.href = "/login"` drops the
return URL (the two sibling redirect paths carry it). Fix: carry the
current path as `?redirect=` (validated by the existing login guard).

**FE-L6 — inconsistent UEN validation across surfaces.**
`new-organisation-client.tsx:154-164` (none), `shared/schemas/bank-account.ts:60,116`
(`length <= 10` only) vs `shared/schemas/invoice.ts:16` (full 3-form ACRA).
Fix: export a shared `uenSchema` and reuse.

### Docs & hygiene (the cross-cutting truth audit — selected)

**DOC-H1 — DEPLOYMENT.md §9/§11 bootstrap example uses an invalid GST
number.** `docs/DEPLOYMENT.md:307` — `"gst_reg_number":"M90345678"`
missing the check letter; the P15 honest validator
(`validators.py:39` `_GST_M_FORM`) rejects it → the whole documented e2e
bootstrap 400s (verified live by the lead this session). Fix: `M9034567K`.

**DOC-M1 — DEPLOYMENT.md §7 stale expected outputs (834/72 vs the same
file's P16 header 860/76).** Fix: 860P/0F/5S + 76P/3S.

**DOC-M2 — README Configuration documents `DATABASE_URL` (read by nothing)
and omits the real `DB_*` mechanism; lists the three `NEXT_PUBLIC_ENABLE_*`
flags as active when `.env.example` marks them reserved.** Fix: correct the
table to the five `DB_*` vars + reserved note.

**DOC-M3 — LICENSE missing while the repo claims AGPL-3.0.** README badge,
README "See [LICENSE](LICENSE)" (dead link), `pyproject.toml:7`. Fix: add
the standard AGPL-3.0 LICENSE text.

**DOC-M4/M5/M6 — DEPLOYMENT.md §11 cookie-jar bug (`-b /tmp/cj2.txt` never
created; `$ORG_ID` never exported) + §9 credit-note bootstrap omits the
required `related_document_id`.** Fix: single- jar flow + export step +
the field.

**DOC-M7/M8/M9 — AGENTS.md §1 status snapshot 3 majors stale (12 pages/305
tests/233 backend/28 tables/Django 6.0.2/98% security); README carries four
contradictory test counts (1454 badge vs 834/532 vs 1320/750/530); three
docs' tech-stack tables carry P13-era versions.** Fix: one sweep
normalizing to the P16/P17 truth (16 pages · 554 vitest · 860 backend ·
40 e2e · schema v1.2.0 · Next 16.4.6 · Django 6.0.10 · DRF 3.18.3).

**DOC-M10 — ledgersg_SKILL.md falsely claims the local `.env`s are
git-tracked** (`git ls-files` is empty; both are ignored). Fix: invert the
claim. **DOC-M11 — `scripts/mobile-nav-audit.js` + capture script fail from
the repo root** (bare `require("@playwright/test")`; only
`prod-csp-smoke.js` self-resolves). Fix: port the self-resolving require.

**DOC-L batch** — `middleware.ts` refs in 4 docs (it is `src/proxy.ts`);
README dead file refs (`start_apps.sh`, `SECURITY_AUDIT.md`,
`E2E_TEST_EXECUTION_SUMMARY.md`, `src/app/api/`), wrong dashboard endpoint
in the README diagram, wrong issues URL, stale footer; PAD stale paths
(`src/lib/server/`, `/home/project/Ledger-SG/`), stale handbook counts,
schema-table errors, CSP-mode wording; SKILL v1.1.0 + `p11_bootstrap.py`
refs; `.env.example` header comments lag P16; ci.yml `DATABASE_URL`
no-op; one tracked runtime artifact (`apps/backend/database_connection_status.txt`).

**API_CLI_Usage_Guide.md** — verified substantially accurate against the
routes (all endpoint paths, envelopes, the P16 additions, login token
shape, P14 line schema); needs only the P17 addendum (new 400 contracts,
the reversal guard semantics) — no structural rework.

## 3. Execution plan (TDD; ordered by risk, then dependency)

### Phase 0 — environment & baselines (already executed, this session)

Fresh clone, PG 17 + Redis 8 rootless install, both DBs at schema v1.2.0,
`ledgersg_app` at the documented dev password, venv + node_modules
installed, all baselines reproduced green (see §1). No code changes.

### Phase 1 — backend concurrency & contract batch (each: RED test → GREEN fix → suite)

| # | Task | Files | Test (RED first) |
|---|---|---|---|
| 1 | **BE-H1** double-reversal guard + row lock | `journal_service.py`, `journal/views.py` (typed 409-class error) | double-reversal refused; sequential + concurrent-safe assertion; the first reversal still GREEN |
| 2 | **BE-H2** void() row lock + re-check | `payment_service.py` | double-void refused (second call sees `is_voided=True` post-lock); single void unchanged |
| 3 | **BE-H3** Celery tenant context + on-commit dispatch | NEW `common/tenant_context.py` helper (context-manager), `invoicing/tasks.py`, `peppol/tasks.py`, `document_service.py` (3 seams) | unit test: task body executes queries with `app.current_org_id` set (assert via the helper's set_config contract); dispatch deferred past commit |
| 4 | **BE-M1** GST box typed parse | `gst/views.py` | non-numeric box values → 400 (None, dict, "garbage"), NaN still 400, valid still files |
| 5 | **BE-M2** bulk-allocation UUID validation | `banking/serializers/allocation.py` | `"document_id": "abc"` → 400 field error; valid UUIDs unchanged |
| 6 | **BE-M3** UEN normalize+validate on PATCH (shared helper) | `core/serializers/organisation.py`, `core/views/organisations.py` (2 paths) | PATCH with lowercase/whitespace UEN → normalized + validated; invalid form → 400; case-dodge duplicate refused |
| 7 | **BE-M6** tax-rate range on update serializer | `gst/serializers.py` | PATCH rate 9 / -1 → 400; 0.09 GREEN |
| 8 | **BE-M5** reconcile payment-side guard + locks | `reconciliation_service.py` | second reconcile of the same payment → typed 400; first reconcile GREEN |
| 9 | **BE-L2** uuid converters on the two routes | `banking/urls.py` (routes), `banking/views.py` | malformed id → 404 (route no longer matches), not 500 |
| 10 | **BE-L3** gate `/admin/` | `config/urls.py` | admin 404 under non-DEBUG settings (test-settings gate pattern from `test_settings_gates.py`) |
| 11 | **BE-L4** `STORAGES` migration | `base.py`, `production.py` | settings gate: `STORAGES["staticfiles"]["BACKEND"]` is the manifest storage in production; default unchanged in dev |
| 12 | **BE-L1** exchange_rate 6-dp validation (no `money()` quantize on the rate) | `payment_service.py` | 1.234567 rate stored/round-tripped exact; monetary products still 4-dp |
| 13 | **BE-M7** `select_related` on the 3 list services | `payment_service.py`, `document_service.py`, `reconciliation_service.py` | query-count assertions (assertNumQueries-style via captured connection queries) — list of N rows stays O(1) FK queries |
| 14 | **BE-M4 interim** stop caching negative membership lookups | `tenant_context.py` | non-member request → no cache write (assert cache key absent); member hit still cached |

### Phase 2 — frontend contract batch (vitest RED → GREEN; e2e where live)

| # | Task | Files | Test (RED first) |
|---|---|---|---|
| 15 | **FE-M1** `--color-success` token | `globals.css` | compiled-theme assertion (the utility exists in the generated CSS via the @theme contract — a vitest on the CSS source + a rendered-badge test) |
| 16 | **FE-M2** clear the 6 lint errors + CI lint gate | `gst-chart-wrapper.tsx` (useSyncExternalStore or narrow rule), `banking-client.tsx:404`, `layout.tsx:18`, `auth-provider-session.test.tsx` (hoist probe capture), `p11.spec.ts:234` (const), `ci.yml` (lint step) | whole-tree eslint = 0 errors (warnings at documented parity); CI runs lint |
| 17 | **FE-M3** proxy nonce orchestration unit test | NEW `src/__tests__/lib/proxy.test.ts` (or `src/lib/__tests__`) | proxy() sets request CSP + `x-nonce`, response CSP carries the same nonce, two calls rotate the nonce |
| 18 | **FE-M4** wire the unsaved-changes guard | `invoice-form.tsx` (or the form page) | `beforeunload` fires only when `hasUnsavedChanges`; no listener when clean |
| 19 | **FE-L1** drop the 4 dead CSP origins | `csp.ts` + its test | builder output no longer contains them; all existing CSP tests GREEN |
| 20 | **FE-L2** dead-utility sweep | the 3 filter files + `alert.tsx` | visual/DOM class assertions (classes resolve to real utilities) |
| 21 | **FE-L3** dead-code deletion | `use-dashboard.ts`, `auth-provider.tsx`, `invoice-store.ts` | tsc 0 + full suite GREEN (deletion-only) |
| 22 | **FE-L4** org-selector a11y | `shell.tsx` | aria-expanded/hpopup assertions; Escape closes |
| 23 | **FE-L5** redirect carry on refresh-failure | `api-client.ts` | failure path builds `/login?redirect=<path>` (guard-compatible) |
| 24 | **FE-L6** shared `uenSchema` | NEW export in `shared/schemas/`, reused in invoice + bank-account + new-organisation | 3-form ACRA parity tests on all three surfaces |

### Phase 3 — docs truth pass + hygiene (no code behavior)

1. **DEPLOYMENT.md** — the user-named priority: rewrite/validate as the
   complete step-by-step fresh-host guide (from `git clone` to verified
   stack): fix §9 GST example (DOC-H1), §7 counts (DOC-M1), §11 cookie-jar
   + `$ORG_ID` (DOC-M4), §9 `related_document_id` (DOC-M6), and re-verify
   EVERY command against the tree.
2. **README.md** — env table (DOC-M2), test counts (M8), stack versions
   (M9), dead refs/endpoint/issues-URL/footer (L-batch).
3. **AGENTS.md / PAD / CLAUDE.md / ledgersg_SKILL.md** — status snapshots
   and version tables normalized (M7/M9/PAD-L); SKILL `.env` claim (M10).
4. **API_CLI_Usage_Guide.md** — full route re-validation + the P17
   addendum (new 400 contracts, reversal semantics, on-commit dispatch
   note).
5. **LICENSE** (AGPL-3.0), `.env.example` header comments, `ci.yml`
   `DATABASE_URL` removal, untrack `database_connection_status.txt`.
6. **scripts/** — self-resolving requires (DOC-M11).
7. Root `.env.example` — re-verified against every env reader; updated
   where stale (the user-named deliverable; committed).

### Phase 4 — the full verification gate + deliverables

- Full backend suite + invariants + security ≥ the 860 baseline (with the
  new P17 tests).
- `manage.py check` (testing settings) — 0 errors.
- vitest ≥ 554 + new tests; `tsc --noEmit` 0; whole-tree eslint **0
  errors** (warnings at parity); `npm run build:server` green; prod-CSP
  smoke 5/5.
- Live stack: `test:e2e` default green; `test:e2e:full` 40P live;
  `rls_smoke.py` 13/13 as `ledgersg_app`; mobile-nav probe 17/17
  (re-settled on the remediated tree).
- Screenshots: 8+ new (`docs/screenshots/96-*_session34…` naming, DOM-
  verified, md5-unique) of the remediated dev stack.
- `worklog.md` + `docs/session_34.md` + the P17 report
  (`docs/REMEDIATION_2026-11-27_P17_REPORT.md`).
- Conventional commits on `main`, pushed via `docs/ssh_git_wrapper_v3.py`,
  remote ref verified, key shredded.

## 4. Risks & mitigations

- **BE-H3 design risk (worker context):** the helper must mirror the
  middleware's `SET LOCAL` semantics; eager mode must stay bit-identical
  for dev/test (the existing tests run under ALWAYS_EAGER). Mitigation:
  the helper wraps in `transaction.atomic()` exactly like the middleware;
  tests assert both modes' contracts.
- **Lint-error fixes (FE-M2) must not weaken rules** (the §5 hard
  lesson): the `mounted` trio gets a real refactor or a documented
  file-scoped narrow, never a global disable; the immutability test errors
  get a hoisted capture, not a rule-off.
- **`select_related` (BE-M7)** must not change serializer output shapes
  (pure query-plan change); the existing tests + new query-count gates
  hold the contract.
- **Docs sweep is wide but mechanical** — every edit lands in the same
  commit family as the code it describes; the P17 report carries the
  row-by-row ledger.
- **Session continuity:** dev servers are double-fork daemons
  (`scripts/daemonize.py`); PG/Redis survive tool-call boundaries
  (verified this session).

## 5. Deferred (registered, not dropped — carried forward)

The P16 register in full (ContactPicker WAI-ARIA combobox, email-restore
lifecycle-evidence column, backend list pagination BE-L6, the audit-log
INSERT WITH CHECK forgery surface + tax-code row-capture note, the ruff
~1216 mechanical register, UEN checksum pending the official ACRA
algorithm, H-3 DB-trigger layer, H-05b attachment model, B-3/B-4/B-8/B-9/
B-12/B-15..B-19, the P11/P12 L-batch) + this sprint's new: BE-M4's full
invalidation design (needs the membership-management surface),
BE-L5 (CSV size cap / bulk dedup), the CSP report-endpoint log bound,
`display_money`/`round_half_up` finite-gate consistency, journal
serializer tolerance alignment, lines max_length, `get_allocations`
org-filter defense-in-depth.
