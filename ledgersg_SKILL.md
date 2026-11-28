---
name: ledgersg
description: "Engineering skill for the LedgerSG codebase — a SQL-First, double-entry accounting platform for Singapore SMBs (Django 6 + DRF + Next.js 16 + PostgreSQL 16 RLS). Captures the architecture, the hard lessons of the 2026-11-21 P0+P1+P2+P3+P4 remediations, testing prerequisites and gates, and the debugging guide a future agent needs before touching financial code."
version: 2.17.0
last_updated: 2026-11-28
project_state: "P30 remediated; all gates green — 1030 backend tests (0 failed, 5 skipped; +2 the reconcile/unreconcile query-count gates) frontend 698 vitest (85 files, on vitest 4.1.12) + 43 e2e (43/43 live) — P30 headline: the ruff mechanical closure (the registered 928-finding production batch's mechanical classes closed 650 → 0: whitespace ×378, import order ×122, unused imports ×121 across 51 files, the Django split-settings star imports ×29 documented via per-file-ignores — the pass-through contract; ruff check --fix now SAFE, the register's blind-fix trap defused; the 277 semantic findings stay registered; make lint-mechanical + the CI step pin the closed classes at 0) + the fourth-surface walk completion (reconcile/unreconcile responses now JOIN bank_account instead of walking it — the locked fetches chain select_related, byte-identical payloads pinned by 2 new CaptureQueriesContext gates + the live round-trip); carries the P29 state forward — 1028 backend tests (0 failed, 5 skipped; +3 the detail-query-count gates) frontend 698 vitest (85 files, on vitest 4.1.12) + 43 e2e (43/43 live) — P29 headline: the detail-view N+1 closure (the three detail seams — document detail, journal entry detail, payment detail — fetched their row with a plain .objects.get(...) while the serializers walked the related FKs: the invoice/quote detail walked account + tax_code on EVERY line [a 5-line detail paid 14 queries where 3 would do, across 8 serialising call sites incl. the PDF context], the journal entry detail walked account on every line [the registered 'journal detail N+1'], the payment detail walked contact + bank_account; fixed at the service seam: the contact rides the document SELECT, the lines arrive in ONE joined SELECT carrying account + tax_code, the payment joins its related rows — the payloads byte-identical, pinned by 3 new CaptureQueriesContext query-count gates) + the per-glob coverage ratchet raise (the five per-glob tiers raised at their measured floors — the hooks branches floor sat 15 points below the measured 51.16 — plus the NEW src/shared tier 73/62/76/73, closing the P20 blind spot); carries the P28 state forward — 1025 backend tests, frontend 698 vitest + 43 e2e — P28 headline: the SQL-level push-down for the service-driven lists (the four services — contacts, documents [invoices AND quotes], payments, bank transactions — materialised the ENTIRE filtered set in Python on every request and the views Python-sliced + len()-counted, so every 20-row page fetched all N rows; the P24 envelope paged the RESPONSE, not the QUERY; fixed: lazy querysets + SQL COUNT(*) + SQL LIMIT/OFFSET, the envelope byte-identical, pinned by 4 new CaptureQueriesContext gates) + the honest ratchet (the vitest whole-suite floor raised 71/60/68/71 → 73/62/70/73 at the measured value the P21–P27 reports recorded but never wrote into the config) + the dev-tier dependency closure (the 17 npm-audit findings closed with in-range semver bumps; npm audit 0 across dev+prod); carries the P27 state forward — 1021 backend tests, frontend 698 vitest + 43 e2e — P27 headline: the pagination state-machine truth (the P26 search-debounce MOUNT-run reset race — a Next click inside the ~600ms window silently reverted to the cached page 1, no refetch, no feedback; proven by trace; fixed by gating the page restart on the debounced VALUE CHANGE — the last-committed-value ref compared inside the timer callback, never during render; the org-switch offset reset extended to all five P26 surfaces; the banking filter-change offset reset with the stable NO_FILTERS default; all pinned by real-hook transport-URL specs — 12 new gates); carries the P26 state forward — 1021 backend tests, frontend 686 vitest + 43 e2e — the P26 headline: the frontend pagination wiring + the Peppol transmission-log contract — P26 headline: the frontend pagination wiring + the Peppol transmission-log contract (every list surface — invoices/contacts/payments/bank-transactions/quotes — pages server-side at size 20 through the shared TablePagination with the page identity in each hook queryKey; the invoices search migrated server-side; useContacts returns the envelope; the Peppol transmission log joined the ?limit=&offset= contract with the -transmitted_at,-id tiebreaker + one conditional-aggregation counters query, byte-identical unpaginated; the P26/FE-P1 e2e spec stocks its own fodder — fresh DB → one bootstrap → the FIRST e2e:full 43/43, 0 skipped); carries the P25 state forward — the fresh-substrate first-run truth + the pagination contract hardening (the §9 bootstrap tax_code_id fix + the step-4c fodder top-up; the int8 offset cap + the offset-requires-limit typed 400s; the WCAG 2.5.3 pagination labels; the beyond-end controls; the render-time org-switch reset); carries the P24 state forward — the server-side list pagination (the additive ?limit=&offset= contract on the six core list surfaces — the ledger at the SQL level, the entries/documents/contacts/payments/transactions lists at the envelope level; byte-identical {results, count} when limit is absent, next/previous + the total count when present; typed 400s on garbage; the ordering tiebreakers; the shared TablePagination control + the useLedger page identity in the queryKey); carries the P23 state forward — 969 backend tests (0 failed, 5 skipped; re-verified on a fresh clone, session 44), frontend 642 vitest + 41 e2e — P23 headline: the mobile-nav drawer-slide transition truth (Tailwind v4 animates translate-x-* through the standalone `translate` CSS property; the drawer's transition list omitted it, so the 300ms slide never interpolated while every functional probe stayed green — fixed to transition-[transform,translate,visibility] and pinned by its own compiled-CSS gates: the shell-drawer-transition vitest spec + the P23/FE-M1 e2e computed-style spec) + the vitest critical-advisory closure (^4.0.18 → ^4.1.12 — both criticals closed, 0 critical remaining, the 17 residual findings all dev-tier, the production set clean); carries the P21 state forward — 969 backend tests, the list-envelope unification ({results, count} on every list surface, the pagination prerequisite; the vacuous RLS-isolation assert fixed with it) + the InvoiceNow invoicenow_sent_at evidence stamp (the restore-to-SENT branch was dead code) + the on-commit cache truth + the bank-account default-flag locks + the ValidateBalance typed-400 body + the banking a11y batch (the Reference name, the keyboard-reachable CSV import, the loader live regions, the payment-card keyboard contract, the reconcile aria-pressed) + the timezone-safe date helpers; carries the P20 state forward — 950 backend tests (0 failed, 5 skipped; invariants 34, security 83P/3S), frontend 627 vitest + 40 e2e (40/40 live, green on the FIRST run of a fresh DB), typecheck 0, whole-tree eslint 0 errors (0 warnings), the coverage ratchet RAISED to 71/60/68/71 with the app+providers tiers measured, the production-CSP smoke 5/5 (nonce + hydration + zero violations), the runtime-role smoke 13/13 as ledgersg_app, the mobile-nav probe 17/17 (the navigation works; no Tailwind v4 bug — re-settled on the P18 tree; the tailwindcss-animate family that silently compiled to nothing in v4 was fixed with tw-animate-css), schema v1.2.2 (§17 RLS complete + §15c Django framework tables incl. the ENABLE_ADMIN opt-in set), zero known dependency advisories; P20 headline: the void/transition/allocate lock completion (void locks its affected documents sorted; transition_status locks + update_fields; allocate pre-locks sorted) + the CSV import savepoint + magnitude bound (the poison-row 500) + the posting-side balance-cache invalidation + the e2e first-run truth (the banking helper is contact-self-sufficient; the one-command §9 bootstrap script) + the two a11y Highs (the invoice-form Notes/Terms names, the named back links) + the ContactPicker blur dismissal + the timezone-safe date formatter + the raised coverage ratchet + the playwright locale/timezone/trace pins; P19 headline: the remove_line truth-gap fix (the P18 commit claimed the lock; the method was also broken end-to-end — a FieldError on every call) + the unallocate lock re-order (the AB-BA deadlock) + the archive-gate cache bypass + the create_entry sorted account locks + the return-periods savepoint + the status-task FULL tenant-context wrap + the journal-list prefetch + the five uuid route islands + the serializer-tolerance alignment + display_money finite gate; the four banking modals are Radix Dialogs, the transaction row is keyboard-operable (WCAG 2.1.1), the ContactPicker is a WAI-ARIA 1.0 combobox and the in-app unsaved-work route guard ships (the two oldest P16-era deferrals closed), the enforced CSP reports to the tested endpoint, the CSV import is size-capped, eslint at 0E/0W; P18 headline: the statutory-record locks (generate_f5/review_return under the row lock), the concurrency completion (unallocate/unreconcile/convert/credit-cap/add_line locks + the header/archived posting gate), the Celery coverage completion (the three remaining Peppol task bodies under the RLS tenant context, the on-commit dispatch covered, terminal classification for deleted-org tasks), the email status gate (APPROVED invoices only), the contrast debt closed (bg-success/bg-alert/text-muted at WCAG AA with pairing gates), the genuinely-shared uenSchema; P17 headline: the concurrency guards (double-reversal typed 400 / double-void / double-reconcile typed 400, all under row locks — BE-H1/H2/M5), the Celery tenant context (on-commit dispatch + the worker-side RLS context via common/tenant_context.py — BE-H3), the 400-contract sweep (typed GST box parsing, bulk-allocation UUID field errors, UEN normalize-then-validate on org PATCH, tax-rate range, 6-dp exchange_rate), /admin/ gated off outside DEBUG + the Django 6 STORAGES manifest migration, select_related on the three list services, no negative-membership cache poisoning, the --color-success token + the unsaved-changes beforeunload guard + the org-selector Radix menu contract + the shared uenSchema + redirect-carry + the dead CSP origins dropped; P16: the nonce-based CSP via src/proxy.ts + src/lib/csp.ts with force-dynamic (FE-C1), the service-path middleware restored from base + settings-gated (BE-H1), the allocate endpoint accepts instalments (BE-H2), the dashboard invalidation key fixed (FE-H1), org-creation selects the new org via selectOrgById (FE-H2), all three ACRA UEN forms accepted (FE-H3), the payment-row lock + atomic create+allocate + NaN/Infinity box rejection + the line-total bound + system-tax-code read-only + UEN normalization (the M-batch), the open-redirect guard + scroll-lock release + dialog semantics + the e2e serial contract (the FE batch); P15: the tree repaired after the corrupted 2bcb43f0, P14 complete (FILED immutability, GST lock, linked CNs, allocation cap, honest validators, line-item 400s, NRIC masking, Viewer read-only, XXE hardening, tax-code dedupe, single-flight refresh); P12: the mobile nav verified working (the v4 setup is clean), the open menu is a modal overlay (now with role=dialog — P16); P11: credit notes post REVERSED GL entries and NET in the F5 computation"
---

# LedgerSG — Engineering Skill

> Distilled from the codebase, the 2026-11-21 audit + P0 remediation sprint
> (`LedgerSG_Code_Review_Audit_Report_2026-11-21.md`, `docs/REMEDIATION_2026-11-21_REPORT.md`),
> the session-3 P1 sprint (`docs/REMEDIATION_PLAN_2026-11-21_P1.md`,
> `docs/REMEDIATION_2026-11-21_P1_REPORT.md`), the session-5 P2 sprint
> (`docs/REMEDIATION_PLAN_2026-11-21_P2.md`, `docs/REMEDIATION_2026-11-21_P2_REPORT.md`),
> and the session-7 P3 sprint (`docs/REMEDIATION_PLAN_2026-11-21_P3.md`,
> `docs/REMEDIATION_2026-11-21_P3_REPORT.md`), and the session-9 P4 sprint
> (`docs/REMEDIATION_PLAN_2026-11-21_P4.md`,
> `docs/REMEDIATION_2026-11-21_P4_REPORT.md`).
> Every claim below is verifiable against a file path or a runnable command.

---

## 1. Project Identity & Philosophy

LedgerSG is a **double-entry accounting platform for Singapore SMBs** with IRAS GST
compliance (F5 returns, InvoiceNow/Peppol PINT-SG, BCRS). Three non-negotiables:

1. **SQL-First**: `apps/backend/database_schema.sql` is the source of truth. All models
   are `managed = False`. NEVER run `makemigrations`. Schema changes = hand-written DDL
   patch + version bump + model alignment + conformance gate green.
2. **Money is `NUMERIC(19,4)`** (schema v1.1.0, the §16 in-place widening; v1.2.0 was the §17 RLS completion) — no floats, ever. All Python money math goes through
   `common.decimal_utils.money()`.
3. **Corrections are reversals**: journal entries are immutable; a void is a reversing
   entry, never an update.

## 2. Tech Stack (locked versions)

| Layer | Tech | Version |
|---|---|---|
| Backend | Django / DRF / simplejwt | 6.0.10 / 3.18.3 / 5.5.1 (+ token_blacklist app, schema §15b) |
| DB | PostgreSQL (rootless dev via `docs/setup_pg_z.sh`) | 16+ (dev: 17) |
| Cache/queue | Redis + Celery | 6.4 / 5.6 |
| Frontend | Next.js App Router / React / Tailwind / Shadcn | 16.4.6 / 19.2 / 4.0 |
| Tests | pytest-django (`--reuse-db --no-migrations`) / Vitest + RTL | 9.x / 4.x |
| Lint | ruff (`target-version py312`, line-length 100) | 0.15.x |

## 3. Environment Bootstrap (exact, verified)

```bash
# 1. Rootless PostgreSQL on :5432 (superuser postgres/postgres)
bash docs/setup_pg_z.sh
PGBIN=/home/z/my-project/pg/root/usr/lib/postgresql/17/bin
"$PGBIN/psql" -h /home/z/my-project/pg/data -U postgres -d postgres -c \
  "CREATE ROLE ledgersg WITH LOGIN PASSWORD 'ledgersg_secret_to_change' SUPERUSER;"
# (SUPERUSER is required to load the schema: it CREATEs ROLEs in DO blocks.
#  The application role in production is ledgersg_app — see §6 RLS.)

# 2. Databases + schema (BOTH dev and test)
for db in ledgersg_dev test_ledgersg_dev; do
  "$PGBIN/psql" -h ... -U postgres -d postgres -c "CREATE DATABASE $db OWNER ledgersg;"
done
export PGPASSWORD=ledgersg_secret_to_change
psql -h 127.0.0.1 -U ledgersg -d ledgersg_dev     -f apps/backend/database_schema.sql
psql -h 127.0.0.1 -U ledgersg -d test_ledgersg_dev -f apps/backend/database_schema.sql

# 3. Redis on :6379 (REQUIRED — see Anti-Pattern #1)
# 4. Backend deps
cd apps/backend && python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## 4. Test Workflow (the only correct invocation)

```bash
cd apps/backend
export DB_NAME=test_ledgersg_dev DB_USER=ledgersg DB_PASSWORD=ledgersg_secret_to_change \
       DB_HOST=127.0.0.1 DB_PORT=5432
pytest --reuse-db --no-migrations -q
# Current state (2026-11-28, post-P30): 0 failed, 1030 passed, 5 skipped — SUITE GREEN (+2 the reconcile/unreconcile query-count gates); the ruff mechanical classes at 0 on the production tree (make lint-mechanical / the CI step)
pytest tests/invariants -q   # 34 gates: atomic rollback (+ the P13 handler-layer
                             # rollback + reversal-atomicity + sub-mil tolerance
                             # gates), void net-zero, F5 tie-out, schema
                             # conformance (incl. numeric precision), journal
                             # balances, CoA trial balance, monetary capacity,
                             # immutability contract, naive-today gate
pytest tests/security -q     # 83 passed + 3 skipped: RLS transaction isolation,
                             # token lifecycle, settings gates (incl. the
                             # P6/E-1 throttle-posture gates + the P13
                             # copy-on-write gates), refresh-cookie +
                             # session_hint contracts
```

Frontend gates (`apps/web`): `npm test` (698 vitest, 85 files — on vitest 4.1.12, the P23
advisory closure), `npm run typecheck` (tsc, 0
errors), `npm run test:e2e` (playwright; 11 tests green without a backend —
31 backend-gated specs skip with reasons), `npm run test:e2e:full` (all 43 —
needs the Django backend on :8000 + Redis AND the E2E_DEMO_* trio exported
(see docs/DEPLOYMENT.md §9); `npx playwright install chromium` first;
development settings raise the refresh/DRF throttle budgets so the suite is
not 429'd mid-run — production posture unchanged, P6/E-1).
`PLAYWRIGHT_PROJECTS=all` opts into the 5-browser matrix.

Gates before any PR: `manage.py check` (0 errors), invariants green, security green,
full suite no worse than the documented baseline, `ruff check` clean on touched files.

## 5. Backend Architecture Map

```
Request → SecurityMiddleware → CORS → CSP → WhiteNoise → Session → Common → CSRF
        → AuthenticationMiddleware
        → TenantContextMiddleware   ← org extraction, membership check, RLS transaction
        → AuditContextMiddleware    ← app.client_ip/user_agent/request_path
        → view (thin, @wrap_response)
              → services/ (ALL business logic; transaction.atomic() here)
                    → unmanaged models → 7 PG schemas (RLS enforced)
```

**URL layout**: org-scoped APIs are `/api/v1/{org_id}/<module>/…`, mounted from
`config/urls.py` `org_scoped_urlpatterns`. Auth is `/api/v1/auth/*`. IMPORTANT: the ACTIVE
core URL config is the `apps/core/urls/` PACKAGE (`__init__.py` + `auth.py` + …), NOT the
shadowed `apps/core/urls.py` module — new routes go in the package files.

**Key files**: `common/views.py` (wrap_response), `common/middleware/tenant_context.py`
(RLS), `apps/journal/services/journal_service.py` (GL), `apps/gst/services/*` (F5),
`apps/invoicing/services/document_service.py` (lifecycle), `apps/core/services/auth_service.py` (JWT).

## 6. Database Invariants (enforced by CHECKs — never fight them)

| Constraint | Rule |
|---|---|
| `journal` balance trigger | Σ debits == Σ credits per entry (deferred to commit) |
| `chk_reversal_consistency` | `is_reversed` and `reversed_by_id` flip TOGETHER |
| `chk_void_reason` | `voided_at` set ⇒ `void_reason` non-empty |
| `chk_box4_total` | `box4 = box1+box2+box3` (unless DRAFT) |
| `chk_box8_net` | `box8 = box6_output_tax − box7_input_tax_claimable` |
| `return_status_check` | status ∈ {DRAFT, COMPUTED, REVIEWED, FILED, AMENDED} |
| doc_status enum | DRAFT, APPROVED, SENT, PARTIALLY_PAID, PAID, OVERDUE, VOID |
| RLS | `USING (org_id = core.current_org_id())`, FORCE; `ledgersg_app` is bound by it |
| token_blacklist §15b | outstandingtoken/blacklistedtoken (public schema, no RLS) |

## 7. GST F5 Box Convention (IRAS; drive from tax_code columns)

Box 1/2/3 supplies (net) ← `f5_supply_box`; Box 4 = 1+2+3; Box 5 taxable purchases ←
`f5_purchase_box`; Box 6 output tax ← `f5_tax_box=6`; Box 7 input tax ← `f5_tax_box=7`
AND `is_claimable`; Box 8 = 6−7; Box 13 revenue; Box 14 ← `is_reverse_charge`.
Sales vs purchase split on `document_type::text LIKE 'PURCHASE%'`. Statuses counted:
APPROVED, SENT, PARTIALLY_PAID, PAID, OVERDUE. Excluded: DRAFT, VOID, BCRS lines.

## 8. Anti-Patterns & Common Bugs (each one shipped a real defect)

1. **Redis-less test runs** → every org-scoped request 500s `tenant_context_error`
   (membership cache). Redis on :6379 is a hard prerequisite.
2. **`SET LOCAL` outside a transaction** → discarded before the view runs; RLS inert.
   Middleware must open `transaction.atomic()` and call `get_response()` inside it
   (`tests/security/test_rls_transaction_isolation.py` proves it under autocommit).
3. **Catching `Exception` in views/decorators** → returns a 500 Response inside
   ATOMIC_REQUESTS → Django COMMITS partial state. Re-raise instead.
4. **Phantom model attributes** — Python happily `obj.foo = x` on any attr; `save()`
   silently discards. Every field write must match a `db_column` (conformance gate).
5. **Wrong enum literals** (`PAID_PARTIAL`, `AMENDING`, `PAID`, `INVOICE`) →
   `invalid input value for enum` / CHECK violation at flush time.
6. **Posting journal entries outside the atomic block** → approved doc with no GL entry.
7. **`pytest.mark.django_db` masks RLS bugs** — the wrapping transaction makes bare
   `SET LOCAL` look fine. Use `TransactionTestCase` for transaction-scoping proofs.
8. **Second definition of a method silently wins** — duplicate `_reverse_journal_entry`
   made the live one a `pass` placeholder. Never define a method twice in a class.
9. **`hasattr` mass assignment** on request-supplied dicts — allow-list field names
   explicitly (F5 boxes: `OVERRIDABLE_BOX_FIELDS`).
10. **Assuming a DB view/table exists** (`coa.account_balance`) — verify against
    `information_schema`; the schema is the only truth.
11. **Missing `user_id` on journal creates** — `posted_by` is NOT NULL.
12. **`date.today()` in posting paths** — the fiscal period for today may be closed;
    fall back to the original entry's date.
13. **`UserOrganisation` without `accepted_at`** — the tenant middleware filters on
    `accepted_at__isnull=False`; a pending invitation 403s every org-scoped request.
    Every fixture that creates a membership must set it (the root `tests/conftest.py`
    does; a shadowed local fixture in `tests/test_api_endpoints.py` did not and cost
    25 red tests). Prefer consuming root conftest fixtures over redefining them.
14. **Red suites hide real bugs** — the 26 "known fixture debt" failures masked three
    production defects (document-summary phantom attrs + invalid enum, CoA trial
    balance on a phantom view, missing `org_id` kwarg). Never normalise a red suite.
15. **Invalid enum literals travel in groups** — `PAID_PARTIAL` (vs `PARTIALLY_PAID`)
    appeared in three places; `pte_ltd` (vs `PRIVATE_LIMITED`) in another. When you
    find one wrong literal, sweep the codebase for it and for its siblings.
16. **Unordered `.first()` over history rows** — `gst.tax_code` stores rate HISTORY
    (SR: 0.07/0.08/0.09 by `effective_from`); `.first()` returned the 2007 row today.
    Always resolve by effective date: `get_tax_code_by_code(org, code, as_of=…)`
    (org rows shadow system rows; latest `effective_from` wins; NULL `effective_to`
    = open-ended). `add_line` fails closed on codes not in force on the document's
    `issue_date`.
17. **Silent fallbacks on money paths** — the GST calculate endpoint used to answer
    9% when a code was unknown. On compliance calculations, 404 the unknown, never
    guess a plausible rate.
18. **Untested branches rot invisibly** — `POST /gst/tax-codes/` 500'd on EVERY call
    (phantom `box_mapping` kwarg → `TypeError`) while the suite was green, because
    only the `rate` branch of calculate and no create was tested. The same branch
    also hid `UUID(org_id)` re-wrap and `UnboundLocalError: Decimal` (function-local
    import in the sibling branch) crashes. Test both branches of every conditional
    API path.
19. **Runtime-green ≠ type-green** — vitest injects globals at runtime, so 321 passing
    tests coexisted with 25 `tsc` errors (jest-style `jest.Mock`, un-imported
    `beforeEach`, incomplete fixtures). `npm run typecheck` is a gate; when testing
    zod defaults use the `z.input` type, and build full payloads for mutations
    typed with `z.infer`.
20. **Playwright configs must match installed browsers** — declaring 5 projects when
    only chromium is installed makes `test:e2e` fail on 24/30 tests before any
    assertion. Chromium-only default + `PLAYWRIGHT_PROJECTS=all` opt-in; axe scans
    must await the auth-redirect chain (`toHaveURL(/login/)`) before `.analyze()`.
21. **Money width is a business-model contract** — `NUMERIC(10,4)` capped at
    S$999,999.9999, below the S$1M GST registration threshold (P3/C-1). All
    money is `NUMERIC(19,4)` since schema v1.1.0; the conformance gate asserts
    DecimalField precision against `information_schema` (it caught
    `JournalLine.exchange_rate` over-declaring 19,6 vs the real 12,6 on its
    first run — schema is truth; align the model DOWN).
22. **Generated columns block their inputs' ALTERs** — `amount_due` is
    `GENERATED ALWAYS AS (total_amount - amount_paid) STORED`; widening its
    inputs requires drop generated → alter → re-add with the identical
    expression (schema §16 ships this as an idempotent in-place migration —
    count-then-skip guard; never re-load the schema over live data).
23. **Dead hooks signal unfinished wiring** — `useCreateInvoice` existed with
    zero importers while the form's onSubmit was a `console.log` stub (P3/D-1).
    When adding a hook, grep for its intended caller; when a form needs an
    API, write a PURE payload adapter (`src/lib/invoice-submit.ts`) that maps
    form state to the backend contract and drops client-computed preview
    fields — the server recalculates authoritatively and owns numbering
    (`document_sequence`), so the local `invoice_number` is display-only.
24. **One auth path for every transport** — anything needing the token goes
    through the api-client (`fetchWithAuth` + `api.blob()`); a second reader
    (the old `localStorage.getItem("accessToken")` in `useInvoicePDF`)
    violated the zero-JWT-exposure mandate AND read a location that is never
    written (token lives in module memory) → `Bearer null` → 401 (P3/D-2).
25. **Sessions are memory-only; e2e must walk the real path** — the backend
    returns tokens in the login body and sets no cookie, so a `page.goto`
    after login drops the session. Authed specs: UI login → dashboard →
    sidebar `<Link>` → target, all client-side. Native validation is enforced
    in headless chromium (an 8-char `minLength` silently blocks short
    passwords — no event fires); the login rate limit (10/min per IP)
    accumulates across dev iterations (flush Redis when a full run fails only
    on login). Backend-dependent specs read `E2E_API_URL` and skip when unset
    — the default suite stays green on a fresh clone (P3/D-5).
26. **Untracked ≠ safe — `git add -A` re-tracks modified tracked files** —
    P1 untracked the env files, P4's `git add -A` re-committed them
    (gitignore only applies to untracked files). Gate every bulk add with
    `git ls-files | rg '\.env|\.pyc|dist/|\.bak'`; also `git stash pop`
    unstages staged `rm --cached` deletions — re-stage before committing.
27. **Opaque id seams swap silently** — passing a log id where an invoice
    id is expected type-checks fine and fails only at runtime; name
    parameters for the row they mean and test the seam's observable
    effect (the row's final state), not the mock's call shape.
28. **Every cache needs its invalidation call sites in the same commit** —
    `invalidate_dashboard_cache` shipped with zero production callers and
    served stale KPIs for a sprint; grep for callers before declaring a
    cache feature done.
29. **Fixtures carry the wrong domain map too** — the test chart named
    2200 "GST Output Tax" while the real seed puts output tax at 2600;
    when a domain constant is wrong in code, sweep fixtures and seeds
    for the same lie.

## 9. Debugging Guide

| Symptom | Cause | Fix |
|---|---|---|
| 500 `tenant_context_error` on every org URL | Redis down or middleware exception | Start Redis :6379; read the middleware log line |
| `FieldError: Cannot resolve keyword 'journal_entry'` | Wrong FK name (it's `entry`) | `entry__org_id`, `entry__entry_date`; no `is_posted` |
| `relation "invoicing.invoice" does not exist` | Querying a table that isn't in the schema | Use `invoicing.document` / `document_line` |
| `numeric field overflow` | DB still on ≤ v1.0.2 (NUMERIC(10,4) money) | Apply schema §16 in-place widening (idempotent); both DBs — fixed everywhere as of v1.1.0 |
| `No open fiscal period found for date …` | Posting dated outside open periods | Date the document inside an open period (fixtures: Jan 2024) |
| `No document sequence configured for org … type X` | Org fixture lacks the sequence | conftest now seeds all types; extend if you add one |
| Test 404s on a route you "added" | Added to shadowed `apps/core/urls.py` | Add to the `apps/core/urls/` package module instead |
| 403 on EVERY org-scoped URL in a test | Fixture created `UserOrganisation` without `accepted_at` | Set `accepted_at=timezone.now()` in the fixture (root conftest already does) |
| 500 on `/{org}/documents/summary/` | Phantom attrs: `DOCUMENT_TYPE_CHOICES`, `total`; invalid `PAID_PARTIAL` literal | Use `DOCUMENT_TYPES`, `total_incl`, enum-correct outstanding set |
| 500 on `/{org}/accounts/trial-balance/` | `get_trial_balance` joined phantom `coa.account_balance` | Aggregates `journal.line` JOIN `journal.entry` (fixed; keep it that way) |
| 500 TypeError `unexpected keyword argument 'org_id'` | View signature missing the kwarg its org-scoped route passes | Add `org_id: str` to the view signature |
| `ModuleNotFoundError: django_celery_beat` / `django_ratelimit` after fresh install | Settings import apps not declared in `pyproject.toml` | Both declared since P1 (beat 2.9.0 — 2.8.1 pins Django<6); pyproject is canonical, NOT root `requirements.txt` |
| `UndefinedColumn "updated_at"` on ExchangeRate | BaseModel injects it; table lacks it | Don't inherit BaseModel for tables without timestamps |
| Void 500s on `chk_void_reason` | Reason not persisted | `void_document()` does now; keep it that way |
| GST computed at the WRONG rate (7% not 9%) | Unordered `.first()` over rate-history rows | `get_tax_code_by_code(org, code, as_of=document_date)`; `gst/calculate/` takes `tax_code` + `document_date` |
| 500 `TypeError … unexpected keyword arguments: 'box_mapping'` on POST /gst/tax-codes/ | View forwarded a field that exists on neither serializer nor model | Fixed in P2; when adding serializer fields, forward the REAL model fields (f5_*) |
| 404 `Tax code 'X' is not in force on the requested date` | Fail-closed resolution (P2 contract) | Pass `document_date` matching the row's effective window, or use an explicit `rate` |
| `UnboundLocalError: Decimal` in a view branch | `from decimal import Decimal` imported inside the SIBLING branch | Imports are module-level in `apps/gst/views.py`; never function-local-import into one branch of a conditional |
| Playwright `Executable doesn't exist` | Declared browser projects not installed | `npx playwright install chromium`, or stay on the chromium default; `PLAYWRIGHT_PROJECTS=all` needs the full install |
| e2e axe scan flaky on `/` | Scan raced the `/` → `/dashboard` → `/login` redirect chain | `await expect(page).toHaveURL(/\/login/)` before `.analyze()` (fixed in `e2e/navigation.spec.ts`) |
| `numeric field overflow … less than 10^6` | DB still on ≤ v1.0.2 (NUMERIC(10,4) money) | Apply schema §16 in-place widening (idempotent); both DBs |
| Login button does nothing (no error, no request) | Native `minLength={8}` on the password input blocks the submit in chromium | Use an 8+ char password |
| e2e authed test lands back on /login | Pre-P4: memory-only session (no refresh cookie, `&& accessToken` gate) | Fixed in P4 — reload/goto now survives via the HttpOnly refresh cookie; if it recurs, check `session_hint` evidence and the backend cookie path |
| e2e full run fails only on login (429) | ~11 logins/run vs the login rate limit | Dev settings now budget 60/min IP (`LOGIN_RATELIMIT_IP`); production keeps 10/min — flush Redis (`redis-cli -n 0 FLUSHDB`) on dev if a window is already spent |
| Dashboard shows stale KPIs after a mutation | 5-min cache with no invalidation (pre-P5) | Mutations invalidate (approve/void/payment/file); keep the invalidator wired into every new dashboard-visible mutation |
| Outstanding AR overstated / amount_due wrong | `allocate()` didn't write `document.amount_paid` (pre-P5) | Fixed — allocations are the truth; `amount_due` is GENERATED off amount_paid |
| Payment void leaves the ledger out of balance | `void()` didn't reverse the journal (pre-P5) | Fixed — `create_reversal` + allocations released + status restored |
| GST posted to 2200 Accrued Expenses / AR on a header | Broad `.first()` control-account match (pre-P5) | Exact resolution 1200/2100/1600/2600, fail-closed; seed GST accounts via toggle if missing |
| InvoiceNow send returns a log id that doesn't exist | Stub `uuid4()` response (pre-P5) | Real `PeppolTransmissionLog` + queued task; poll `invoicenow-status` for the real row |
| Auto-transmit never delivers; log stuck PENDING | Task passed LOG id to `transmit_invoice(invoice_id)` (pre-P5) | `execute_transmission_for_log(log_id)` updates the existing row |
| `transmitted_at` ignores the value passed on create | `auto_now_add` discards it | Use `queryset.update()` for historical timestamps in tests |
| jsdom: `target.hasPointerCapture is not a function` | Radix Select needs pointer-capture APIs jsdom lacks | Setup polyfills in `src/__tests__/setup.ts`; drive selection via `{ArrowDown}{Enter}` |
| `cannot alter type of a column used by a generated column` | `amount_due` is GENERATED off total_amount/amount_paid | Drop generated → alter inputs → re-add identical expression (schema §16) |
| Session lost on every page reload (pre-P4) | Three-link chain: no cookie backend, discarded refresh token, `&& accessToken` refresh gate | P4 cookie flow: login sets HttpOnly refresh cookie + `session_hint`; cold-401 refresh retries (`apps/core/views/_refresh_cookie.py`) |
| Login form shows "Session expired" instead of the credential error | api-client refreshed on an anonymous 401 and hard-redirected | Evidence gate: refresh only with an in-memory token OR the `session_hint` cookie; anonymous 401s propagate to the caller |
| Refresh endpoint 429s during a UI test run | Pointless refreshes on anonymous 401s (pre-refinement) | Same evidence gate; the backend also expires both cookies on a failed cookie-refresh so dead evidence can't linger |

## 10. Pre-Ship Checklist

```bash
pytest tests/invariants -q && pytest tests/security -q      # must be green
pytest --reuse-db --no-migrations -q | tail -1               # ≥ documented baseline
DJANGO_SETTINGS_MODULE=config.settings.testing python manage.py check
ruff check <files you touched>
# schema touched? → bump database_schema.sql version, update BOTH DBs, keep the
# conformance gate green, align models, document in the changelog section
```

Plus: no floats for money; enums from the vocabulary (never literals); every service
write inside `transaction.atomic()`; new tests RED before the fix.

## 11. Lessons Learnt (2026-11-21 sprints; P6 lessons 15-19 below)

1. A green test suite can mask RLS failure when the test harness itself provides the
   transaction production lacks — test the *mechanism* under production semantics.
2. Hand-maintained model mirrors drift silently; an introspection gate turns drift into
   a test failure (it caught ExchangeRate and OrganisationSetting immediately).
3. "Documented as complete" ≠ complete — the void-reversal, RLS, F5 and InvoiceNow
   claims all diverged from code. Validate claims against executable evidence.
4. TDD on fixes is cheap: each Critical fix here is one fixture + assertions that
   failed pre-fix and pass post-fix.
5. Schema CHECK constraints are a gift: encode the box identities and reversal rules
   in DDL, then the application cannot silently violate them.
6. Fixture debt is not neutral: 25 of 26 "known" failures were one missing
   `accepted_at`, and the red noise hid three live endpoint bugs. Fix red suites
   before adding features on top of them.
7. A clean-venv install is a packaging test: settings-imported packages MUST be
   declared in the canonical manifest, and version pins must respect the framework
   major (beat 2.8.1 vs Django 6).
8. Rate data is temporal: "the SR rate" does not exist — only "the SR rate in
   force on date X". Every rate lookup needs a date, and every rate snapshot
   (document line) must validate its row against the document's own date (P2/H-04).
9. Endpoints rot in their untested branches: a green suite with zero coverage on
   the `tax_code` branch of calculate and on create-tax-code hid three distinct
   crashes in one view file (P2/B-7).
10. Test toolchains drift: vitest runs Jest-typed test files fine at runtime while
    `tsc` is red — keep a typecheck gate or the drift compounds (P2/B-5: 25 errors
    accumulated silently).
11. Capacity is a contract: a monetary column that cannot hold the business
    model's real numbers (S$1M GST threshold) is a Critical defect even when
    every current row fits. Encode the ceiling in a gate
    (`test_numeric_capacity.py`), not in tribal knowledge (P3/C-1).
12. Fully-implemented dead code (useCreateInvoice with zero importers) is the
    signature of an unfinished wiring step — grep for callers before writing
    a parallel implementation (P3/D-1).
13. A comment describing nonexistent behavior ("refresh token: HttpOnly cookie"
    with no cookie code behind it) is a defect detector — and a cross-layer
    symptom can be a three-link chain where fixing any single link changes
    nothing (P4/E-1). Write the reload-e2e acceptance test, not just unit
    tests, for session behavior.
14. "Obvious" auth fixes need an anonymous-state regression test: refreshing
    on every 401 flooded the refresh rate limit and swallowed the login form's
    own error — the e2e run caught what unit tests blessed (P4/E-1
    refinement). The 401 handler is a state machine: evidence (in-memory token
    or `session_hint` cookie) gates the refresh; dead evidence must be expired
    server-side.


15. (P6) A persisted status nobody can re-enter is a dead end: P5/H-1 wrote
   PARTIALLY_PAID but the allocate guard still demanded APPROVED — the second
   payment could never settle the remainder. When you add a state, grep every
   guard that mentions its neighbours.
16. (P6) A "fallback" resolver that broad-matches is a deferred misposting: the
   payment JE's Q(account_type="ASSET").first() could land AR on 1010 Cash on
   Hand the day account_type gets populated. Fix resolvers once at the seam
   (JournalService._resolve_control_account) and route every caller through it.
17. (P6) Allowlists that forward phantom keys fail silently: org PATCH accepted
   `address` (no such model field — dropped on save) while filtering the real
   address_line_1/2/city/postal_code/country. Mirror allowlists to the
   serializer's field set, and test the round-trip, not just the 200.
18. (P6) Settings modules must copy-on-write their REST_FRAMEWORK overrides:
   testing.py's in-place assignment corrupted the shared base dict for every
   other module in the process — the settings-gate posture test caught what
   three sprints of green suites had normalized.
19. (P6) Decorator literals are untestable budgets: the refresh throttle's
   hardcoded 20/minute 429'd the e2e suite mid-run with no knob to turn.
   Anything the e2e suite legitimately exercises must be a settings knob
   (production posture unchanged, development budget raised).

20. (P7) A settings key nobody reads is a dead integration: REST_FRAMEWORK
   used "DEFAULT_EXCEPTION_HANDLER" — DRF's key is "EXCEPTION_HANDLER" —
   so the custom exception handler NEVER ran and every in-view
   LedgerSGException surfaced as an unhandled 500. Symptom that exposed
   it: a permission check raising UnauthorizedOrgAccess produced a 500,
   not a 403. Gate integrations by their RESOLVED value
   (api_settings.EXCEPTION_HANDLER.__module__), not the settings dict.

21. (P7) Permission literals must come from the same vocabulary they gate:
   the status-transition view compared against "VOIDED" while the enum is
   VOID, so the CanVoidInvoices branch was dead code — any member could
   void via the generic endpoint. A ChoiceField over the model's
   STATUS_CHOICES makes the whole class of wrong-literal bypasses
   unrepresentable.

22. (P7) Payment-derived statuses belong to the payment service: allowing
   PAID/PARTIALLY_PAID through a generic status endpoint lets a client
   assert a payment that does not exist. The generic endpoint now refuses
   them; only allocate()/unallocate() derive them (with the amount_paid
   arithmetic that justifies them).

23. (P7) Error envelopes are a contract: the frontend read keys the
   backend never writes ({message}/{detail} at the top level) — every
   business-rule failure surfaced as "Request failed: Bad Request", which
   is exactly what hid an always-broken Void button for two sprints.
   Parse the real shape ({error:{message}} + DRF field errors) and test
   the parser against both.

24. (P7) Dead code hides live defects and duplicates them: the mock-era
   edit route would have created a duplicate contact + invoice if reached
   by URL; useUpdateInvoice/useInvoicePDF/useSendInvoiceNow sat unimported
   beside real, working backends. Sweep for zero-importer hooks every
   sprint: either wire them (PDF + InvoiceNow now ship on the detail
   page) or delete them truthfully (edit route, legacy server client).

25. (P7) An API that advertises a field must survive receiving it: the
   org-create serializer declared a phantom `address` the model lacks —
   POSTing it (the field the API itself advertised) was a TypeError 500.
   Serializer field sets are contracts: mirror the model, and
   regression-test every advertised field round-trips or no-ops.

26. (P8) A permission refactor must match the view's actual verbs: the
   P7/F-10 get_permissions() pattern (gate PATCH, keep GET readable) was
   applied to GSTRegistrationView — whose mutations are POST/DELETE —
   loosening GST register/deregister to any member for a sprint. When
   copying a hardening pattern, list the view's mutating verbs first.

27. (P8) An advertised state machine and its engine must agree:
   STATUS_TRANSITIONS listed DRAFT/PAID/OVERDUE→VOID while void_document
   accepted only APPROVED/SENT/PARTIALLY_PAID — an OVERDUE invoice could
   be voided through NO endpoint, and users saw buttons that always
   400'd. Fix by making the accepted set EXACTLY the advertised one, and
   refuse paid documents with credit-note guidance (the accounting
   remedy), never silently.

28. (P8) Serializer fields are promises: InvoiceSendSerializer validated
   cc/bcc/message but the Celery task received only `to` — the frontend
   was actively sending a `message` nobody delivered. Either wire the
   field through or delete it from the contract; both sides then match.

29. (P8) Config has two sources of truth: DOCUMENT_TYPES hardcoded
   QUO/PINV while core.document_sequence (the schema seed) promises QT-/
   BILL-. The schema file is the source of truth — align Python to it
   (issued numbers are stored and unaffected).

30. (P8) Assignment to a non-existent field is a silent no-op:
   quote.converted_to_id = invoice.id set a TRANSIENT attribute that
   save() discarded — the quote→invoice link never existed in the DB.
   Persist links through the real FK (related_document), and
   regression-test the round-trip through refresh_from_db.

31. (P9) Mocked unit tests cannot see wire contracts: the bank-account
   dialog's vitest suite passed while the real POST 400'd — the payload
   carried paynow_type: null and the ModelSerializer rejected null (the
   DB column is nullable; the CHECK allows NULL or UEN/MOBILE/NRIC, and
   "" violates it). Pin the exact payload in the unit test AND keep a
   live e2e that posts it for real; "null vs omitted vs empty" is a
   contract decision the DB schema already made — read it.

32. (P9) A list service's "default view" can silently hide filtered
   rows: list_accounts defaulted to top-level-only (parent__isnull=True)
   even WITH an account_type query, and the seeded bank accounts are
   CHILDREN of the 1000 header — the dialog's GL picker was empty while
   every unit test passed (the fixtures were top-level). When a filter
   narrows by type/flag, lift the structural default; test with the
   SEEDED shape (children), not just synthetic rows.

33. (P9) fullyParallel races writer specs: the banking workflow's three
   tests are a chain sharing live data (test 2 needs test 1's bank
   account), and cross-file workers raced the writer against the
   reader specs on one shared dev DB. test.describe.configure({ mode:
   "serial" }) for chains; --workers=1 for any run that mutates shared
   state. Strict-mode tip: overlay buttons collide with the page behind
   them — scope locators to div.fixed.inset-0.

34. (P9) Locator semantics bite: get_by_role(name) matches SUBSTRINGS,
   but "Add Account" is NOT a substring of "Add Bank Account" — an
   either-branch locator needs a regex alternation. Playwright payment
   numbers came out RCP- (not REC- as the seed table suggested for
   PAYMENT_RECEIVED) — assert on data you READ from the system, never
   on a prefix you assumed from config.

35. (P9) Orphaned dev servers poison later runs: killing the npm wrapper
   leaves next-server alive holding port 3000, and a stale Django
   runserver serves OLD code while you debug NEW fixes (the e2e
   "still failing" after a serializer fix was the stale process).
   Teardown must pkill the process tree; before debugging a "fix didn't
   work", check the port actually serves the code you changed.

36. (P10) A mount-time session check must know which pages are public:
   checkSession runs on EVERY page and treated the anonymous 401 an
   unauthenticated /register visitor gets from /auth/me as session
   expiry — clearAuth + redirect to /login. The registration form only
   ever worked by winning that race (the e2e click landed
   mid-navigation). Public-route exemptions belong beside the loop guard.

37. (P10) A rate-limit block must not masquerade as an authorization
   failure: django-ratelimit's Ratelimited is a bare PermissionDenied
   subclass — on a DRF view it fell through the fallback as a raw 403
   "You do not have permission…", which the frontend api-client treats
   as auth failure (bounce to /login). Map it in custom_exception_handler
   to the documented 429 contract (code, retry_after, Retry-After). And
   when raising a rate budget for e2e, enumerate EVERY knob — the login
   IP budget (P4) and refresh IP budget (P6) were raised, the per-user
   login budget was missed and blocked the grown suite's tail.

38. (P10) Settings modules must copy-on-write their base structures:
   development.py did INSTALLED_APPS += […] and MIDDLEWARE.insert(…) —
   in-place mutations of the lists `from .base import *` shares. Any
   process importing development.py under other settings (a test
   asserting its knobs) injected debug_toolbar into the live registry
   mid-run — a 79-test middleware cascade that looked like everything
   and was one file.

39. (P10) A constraint guard must cover every writer path: the UEN
   UNIQUE was validated only in the CREATE serializer — the detail PATCH
   is a raw request.data allowlist (no serializer at all) and the settings
   PATCH passes no instance, so a taken UEN was an IntegrityError 500 on
   all three paths. Share one guard (ensure_uen_available) across them;
   enumerate writer paths when a constraint exists.

40. (P10) Verify raw bytes before declaring corruption: the "corrupted CI
   trigger" (branches: ain]) was a tool-DISPLAY artifact — the output
   layer eats the byte sequence [m when rendering text; the file on disk
   was always intact (od -c ground truth at both commits). When a finding
   turns out to be an artifact, correct the record explicitly.

41. (P10) e2e specs must not depend on fixture names from other eras:
   the banking statement spec filtered on "Marina" — a P9-era bootstrap
   customer name that broke when P10's bootstrap named a customer
   differently. Specs against a persistent dev DB generate run-unique
   data (timestamps in descriptions/references); a shell breadcrumb h2
   duplicating each page's h1 belongs demoted to aria-hidden (strict mode
   + one-h1-per-page).

42. (P11) A document-type branch in the posting engine must be verified
   PER TYPE: `post_invoice` served SALES_INVOICE and SALES_CREDIT_NOTE
   identically — a credit note DEBITED the customer's AR (books
   overstated receivables on every credit note since the engine shipped).
   Direction assertions belong in the TDD suite per document type, and
   the F5 computation must net the contra documents (and exclude
   quotes — an APPROVED quote is a quotation, not a supply).

43. (P11) An edit dialog must prefill from the SAME payload its save
   writes: the contacts dialog prefilled from the LIST row serializer —
   uen/peppol_id/gst_reg_number rendered blank, and an unconditional
   eight-field save ERASED the stored values with a success toast
   (Peppol ID loss breaks InvoiceNow). Prefill source = write source;
   undeclared serializer fields are silently dropped by DRF (declare
   gst_reg_number or the save reports success and persists nothing);
   round-trip e2e re-reads after the save.

44. (P11) Panel keys must match the backend contract byte-for-byte: the
   F5 boxes panel read idealized `box1` keys while the serializer sends
   `box1_std_rated_supplies` — every box rendered "—". Write key lists
   FROM a real response (paste from the API), never from memory; gate
   with a live e2e asserting a monetary value renders.

45. (P11) One knob per behavior: INSTALLED_APPS gated debug_toolbar on
   DEBUG_TOOLBAR while config/urls.py gated it on DEBUG — the "off"
   combination DEBUG=true + DEBUG_TOOLBAR=false raised ImportError at
   boot. When two gates guard one behavior, the unreachable quadrant is
   a crash; pick the single authoritative knob.

46. (P11) Production settings must only import what production
   installs: production's CACHES declared `django_redis` (a dev extra —
   never in the production dependency set), so the first cache touch
   crashed the boot. Verify production imports against the production
   install (a settings-gate test that boots the module and round-trips
   the cache catches the whole class).

47. (P11) "No rows" assertions must be scoped to the actor in a shared
   dev DB: the failed-login audit test asserted NO LOGIN rows anywhere —
   the live gate's legitimate demo-user logins broke it. Scope silence
   assertions to the test's own actor, matching the positive test's
   scoping; the pytest suite and the dev server share `ledgersg_dev`.

48. (P11) Every hardcoded rate-limit literal becomes a knob the day
   the suite re-runs: register's `5/hour` decorator literal blocked
   the self-serve e2e spec on the 6th `test:e2e:full` run against the
   same dev server. The P4/P6 pattern (settings knob + dev budget +
   posture gate test) is the house style for every new throttle.

49. (P11) e2e specs that CONSUME their fixture must create their own:
   the banking payment spec depended on "the bootstrap-approved"
   invoice — settled by its own previous run, so re-runs starved. An
   idempotent ensure* helper (unique reference per run, reuse
   APPROVED-or-PAID documents) beats fixture archaeology across
   re-runs.

50. (P11) Compute from the raw value, never the display string: the
   dashboard chart fed `parseFloat("SGD 315.00")` → NaN → 0. When the
   API ships both a raw value and a `*_display` string, anything that
   COMPUTES reads the raw one; only the DOM renders the display one
   (with a single currency prefix — never "S$" + "SGD x.xx" doubling).

51. (P12) `display:flex` on a `md:hidden` toggle inside a flex header is
   CORRECT CSS, not a Tailwind v4 bug: an inline-level flex item
   blockifies its outer display. Before diagnosing a "v4 utility not
   winning", trace the matched rules (document.styleSheets walk) — only
   then claim a cascade defect. In this repo the v4 setup is clean:
   `@import "tailwindcss"` + `@theme`, no legacy config file.

52. (P12) An open mobile menu is a modal overlay — it owes the four
   §9.4 behaviors (Escape close, focus trap, body scroll lock, focus
   return to the trigger). The shipped floor: a keydown listener while
   open, a `useEffect` on `sidebarOpen` locking `body.style.overflow`, a
   prev-state ref returning focus, and a Tab-cycle trap within the
   sidebar's focusables. 7 vitest + 3 gated e2e specs pin the contract.

53. (P12) Lint parity on touched files drifts the FULL register silently
   (47 documented → 79 real). Measure the whole-tree count every sprint,
   clear the mechanical classes (unused imports, dead state, in-render
   component definitions), and re-register the truthful remainder
   (post-P12: 45 — 36 any-debt + mounted-gates + exhaustive-deps +
   compiler-informationals).

54. (P12) Playwright `getByRole` name matching is SUBSTRING by default:
   `getByRole('link', { name: 'Ledger' })` also matched the logo link
   ("L LEDGERSG" contains "LEDGER") → strict-mode violation that reads
   like an app bug. Scope to the landmark + `exact: true` when a nav
   item's name is a substring of another element's accessible name.

55. (P13) A DRF exception handler runs INSIDE the request transaction: its
   500 fallback must call `transaction.set_rollback(True)` or partial
   writes COMMIT behind a "successful" 500 Response (B-1 — the typed-
   exception contract has to be audited at every catch layer, and the
   handler is the last one before the transaction boundary).

56. (P13) Statutory rounding gates need SUB-UNIT fixtures: the GST quantum
   bug (`0.001` instead of `0.01` for rounding=2) passed every existing
   test because the fixtures used round amounts — identical at both
   quanta. Test 100.05/100.06-class bases, and tolerance gates at the
   boundary (0.0005 between the service's 0.001 and the DB trigger's
   0.0001 — both now aligned).

57. (P13) Next.js middleware headers OVERRIDE next.config headers() for
   the same key — two definitions means the middleware's silently wins
   (H-1: the env-aware CSP was defeated in production while every unit
   test passed). ONE source of truth; gate the header table with a
   NODE_ENV-stubbing unit test AND verify the SERVED headers live.

58. (P13) `transform` moves an off-canvas drawer off-screen but NOT out
   of the tab order (H-2): the closed mobile sidebar stayed keyboard-
   focusable (WCAG 2.4.3/2.4.7). `invisible md:visible` +
   `transition-[transform,visibility]` removes it from the tab order and
   the a11y tree while keeping the slide animation. Bonus proof: a role
   locator cannot resolve a visibility:hidden element — the a11y-tree
   exclusion IS the fix working (use a CSS locator for closed-state
   assertions).

59. (P15) An interrupted session's partial commit is a tree-corruption
vector: the model file was overwritten by serializer code (circular
import — `manage.py check` is the cheapest corruption probe) and the real
fixes sat at wrong paths. Repair from the parent commit (`git show
<commit>~1:<path>`), port fix BLOCKS into canonical files (diff first,
never adopt wholesale rewrites), and never build on an unverified tree.

60. (P15) A never-run RED suite is a hypothesis batch, not a spec: five
test-side bugs surfaced at first execution (wrong ValidationError import,
a duplicate fiscal-year fixture, state-machine-skipping approve tests,
line-less posting fixtures, a recursing cursor spy). Diagnose every
failure as implementation-gap OR test-bug — never treat the batch as
uniformly correct.

61. (P15) RLS completion must account for PRE-CONTEXT reads: the
middleware attaches request.org_role before the org context exists, so
an org-scoped-only policy on core.role broke every org-scoped request
(403s across the board). NULL-context SELECT on the membership/role
tables is the documented tradeoff (§17b/§17c); enumerate every
pre-context read before choosing policy predicates.

62. (P15) lxml parser flags are write-only — a config gate cannot read
them back. Ship the policy as a module constant the parser builds from
(X-1). And the IRAS M-form GST number has TWO documented lengths (OECD
ANNNNNNNC 9-char + real-world 10-char, e.g. M90356174N) — accept the
union (`^M\d{7,8}[A-Z]$`); a validator that rejects real numbers is
worse than one accepting both (M-1).

63. (P15) `npm audit fix --omit=dev` PRUNES devDependencies from
node_modules (vitest/playwright vanish) — follow it with a plain
`npm install` and verify the dev bins. And a duplicate serializer class
definition silently wins (F811) — grep for the class name before
defining one; lint parity on touched files is a functional gate.

64. (P16) A static production CSP kills hydration silently: Next ships
NON-nonced inline bootstrap scripts on every page, and the whole test
suite runs against `next dev` (whose CSP allows unsafe-inline) — the
production CSP branch had zero coverage. Ship the nonce via
`src/proxy.ts` + `src/lib/csp.ts` (ONE source; the request-CSP header is
how Next learns the nonce), opt the app into dynamic rendering, and gate
with a standalone-build smoke (`scripts/prod-csp-smoke.js`).

65. (P16) A from-scratch MIDDLEWARE list in a settings module is a drift
bomb: service.py dropped the tenant/audit/CSP/WhiteNoise middleware and
the Docker path would have 403'd every org request. DERIVE from base and
gate every HTTP-serving settings module on the four entries.

66. (P16) Enumerate every ENFORCER of a contract when fixing it: the P14
instalment fix landed in the service and the embedded serializer but the
dedicated allocate endpoint's serializer kept the stale literal — and the
tests called the service, never the wire. Test through the wire
serializer, not just the service.

67. (P16) State updates do not rebind closure variables: an onSuccess
that calls refreshOrganisations() then switchOrg(id) holds the
PRE-refresh list. Mutation callbacks that need post-mutation state need
an API that takes the id (selectOrgById), not a state re-read.

68. (P16) `Decimal("NaN")` parses cleanly and quantize() propagates it —
every decimal seam needs an is_finite() gate (in money() AND at the parse
sites that bypass it). A NaN box override could be FILED.

69. (P16) The frontend must not be stricter than the backend: a frontend
UEN regex accepting 2 of 3 ACRA formats rejected LLP numbers the backend
accepts. Mirror the backend's validator vocabulary in the shared schema;
delete dead duplicate validators.


## 12. Quick Reference Card

| Thing | Where |
|---|---|
| Schema (truth) | `apps/backend/database_schema.sql` (v1.2.2 — §17 RLS complete + §15c framework tables) |
| RLS middleware | `common/middleware/tenant_context.py` |
| wrap_response | `common/views.py` |
| money() | `common/decimal_utils.py` |
| GL service | `apps/journal/services/journal_service.py` |
| F5 pipeline | `apps/gst/services/{calculation_service,return_service}.py` |
| Document lifecycle | `apps/invoicing/services/document_service.py` |
| Auth/JWT | `apps/core/services/auth_service.py`, `apps/core/urls/auth.py` |
| Invariant gates | `tests/invariants/` |
| Security gates | `tests/security/` |
| Fixtures | `tests/conftest.py` (org seeds ALL document sequences; memberships carry `accepted_at`) |
| PG setup | `docs/setup_pg_z.sh` + `skills/rootless-postgresql/SKILL.md` |
| Deferred debt | `docs/REMEDIATION_PLAN_2026-11-21.md` §4 + `_P1.md` §4 + `_P2.md` §4 + `_P3.md` §4 |
| P0 remediation report | `docs/REMEDIATION_2026-11-21_REPORT.md` |
| P1 remediation report | `docs/REMEDIATION_2026-11-21_P1_REPORT.md` |
| P2 remediation report | `docs/REMEDIATION_2026-11-21_P2_REPORT.md` |
| P3 remediation report | `docs/REMEDIATION_2026-11-21_P3_REPORT.md` |
| Audit report | `LedgerSG_Code_Review_Audit_Report_2026-11-21.md` |
| Env templates | root `.env.example` (combined index) → `apps/backend/.env.example` + `apps/web/.env.example`; `.gitignore` lists `.env*` — the local dev `.env` / `.env.local` are UNTRACKED (`git ls-files` shows only the three `.env.example`s; never commit them) |
| Session cookies | login/register/refresh set + rotate; logout/change-password/failed-cookie-refresh expire — `apps/backend/apps/core/views/_refresh_cookie.py`; gate = `tests/security/test_refresh_cookie.py` |
| Rate resolution | `TaxCodeService.get_tax_code_by_code(org, code, as_of)` / `is_effective(tc, date)` — `apps/gst/services/tax_code_service.py` |
| Money capacity | All money `NUMERIC(19,4)` since schema v1.1.0; §16 = in-place widening migration; gate = `tests/invariants/test_numeric_capacity.py` |
| Invoice form adapter | `src/lib/invoice-submit.ts` (form state → contact+document payloads) — `src/hooks/use-tax-codes.ts`, `src/hooks/use-accounts.ts` |
| Authed e2e pattern | UI login → sidebar Links (client-side only); `E2E_API_URL` gating — `apps/web/e2e/invoices.spec.ts`; session persistence (reload survival) — `apps/web/e2e/session.spec.ts` |
| Deployment guide | `docs/DEPLOYMENT.md` (fresh-host, rootless PG + §16 migration + Redis + gates) |
| P4 plan/report | `docs/REMEDIATION_PLAN_2026-11-21_P4.md` / `docs/REMEDIATION_2026-11-21_P4_REPORT.md` |
| P10 plan/report | `docs/REMEDIATION_PLAN_2026-11-22_P10.md` / `docs/REMEDIATION_2026-11-22_P10_REPORT.md` |
| P11 plan/report | `docs/REMEDIATION_PLAN_2026-11-23_P11.md` / `docs/REMEDIATION_2026-11-23_P11_REPORT.md` |
| P16 plan/report | `docs/REMEDIATION_PLAN_2026-11-26_P16.md` / `docs/REMEDIATION_2026-11-26_P16_REPORT.md` |
| P17 plan/report | `docs/REMEDIATION_PLAN_2026-11-27_P17.md` / `docs/REMEDIATION_2026-11-27_P17_REPORT.md` |
| P11 live-gate bootstrap | `apps/web/e2e/p11.spec.ts` ensureDemoActivity (idempotent contact/invoice/CN/F5) — the P16 tree's canonical bootstrap (the historical `scripts/p11_bootstrap.py` no longer ships) |
