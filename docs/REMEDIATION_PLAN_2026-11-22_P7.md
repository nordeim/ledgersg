# LedgerSG — Remediation Plan (P7 Sprint: API Truth & Permission Hardening — Status-Transition Authorization, Routed Fiscal Endpoints, Fail-Closed Payments, Real Error Messages, Working Void/Send Actions)

- **Date:** 2026-11-22
- **Branch:** `main` only (per repo convention)
- **Inputs:** post-P6 audit of the `9077381b` state. Findings gathered with the repo skills per
  `skills/skills-catalog.md` (`code-review-and-audit` standard mode via `audit_runner.py`,
  `code-quality-standards`, `vulnerability-scanner`, `diagnosing-bugs`, `e2e-testing-lessons`,
  `writing-plans`) plus two deep manual review passes (frontend P6 surfaces, backend views
  layer). Every Critical/High finding below was re-verified against the working tree with line
  numbers before this plan was written. Scanner "criticals" outside `apps/` fall in the
  documented false-positive classes (`skills/` tree, test fixtures, dev credentials, hardcoded
  schema-name DDL, docstrings) — same classes as P5 §0/P6 §0.
- **Method:** TDD (RED → GREEN → full gate), lint parity on touched files, conventional
  commits, `skills/` excluded from all checks/tests/compilation.
- **Baselines reproduced before any change (this session, exact):** backend **588 passed /
  0 failed / 5 skipped**, vitest **383/383**, typecheck **0 errors**, e2e default
  **9 passed + 11 gated skips**.

---

## 0. Audit Summary (the register this plan is built on)

P6 closed C-5 and the payment-posting integrity gaps. The post-P6 audit found the register
below — the dominant theme is **API-surface truth**: an authorization bypass on the status
endpoint, a crash-on-advertised-field in org create, fiscal endpoints that are unrouted
(frontend calls 404), a 500 on a core money path, and two UI actions that are silently
broken (void always 400s; send-email never delivers) hidden behind an error-message parser
that cannot read the backend's error envelope.

| ID | Severity | Location | Finding (Verified) |
|---|---|---|---|
| F-1 | **Critical** (feature 100% broken) | `apps/web/src/app/(dashboard)/invoices/[id]/invoice-detail-client.tsx:212` | The Void button calls `voidInvoice.mutate("")` — the backend `InvoiceVoidView` requires a non-empty `reason` (`apps/invoicing/views.py:493-495`), so **every void from the UI 400s**. There is no reason input at all, and no void test exists. |
| F-2 | **High** (security: authorization bypass) | `apps/backend/apps/invoicing/views.py:279-286` | `InvoiceDocumentStatusView` gates on `elif new_status == "VOIDED"` — the enum value is `VOID`, so the branch NEVER fires: any org member can void any document via `POST …/documents/{id}/status/` **bypassing `CanVoidInvoices`** (which correctly guards the dedicated `/void/` endpoint). The bare `CharField` also accepts arbitrary strings, and transitions to `PAID`/`PARTIALLY_PAID`/`SENT`/`OVERDUE` have NO permission gate (an invoice can be marked PAID with no payment record). |
| F-3 | **High** (500 on advertised field) | `apps/backend/apps/core/serializers/organisation.py:51` + `organisation_service.py:39-61` | `OrganisationCreateSerializer` declares `address`; `create_organisation(**validated_data)` forwards it into `Organisation.objects.create(**kwargs)` — the model has no `address` field → `TypeError` → **500 on POST /api/v1/organisations/ with `address`** (the field the API itself advertises). The PATCH twin was fixed in P6/F-10; the create path was not. |
| F-4 | **High** (unrouted endpoints, frontend 404s) | `apps/backend/apps/core/urls.py` (shadowed) vs `apps/core/urls/` (active package) | The active URL package does not register `fiscal-periods/`, `fiscal-years/{id}/close/`, `fiscal-periods/{id}/close/` — they exist only in the shadowed `apps/core/urls.py` module → dead code. The frontend calls all three (`src/lib/api-client.ts:337-339`) → guaranteed 404. (The same shadowing class as the P2 NEW-3 fix for `set-default-org`.) |
| F-5 | **High** (500 on core money path) | `apps/backend/apps/banking/services/payment_service.py:621,635,664` | `_create_payment_journal_entry` dereferences `payment.bank_account.gl_account.id` unconditionally, but `create_bank_account` explicitly allows `gl_account=None` (`bank_account_service.py:61-62`) and `create_received`/`create_made` never validate it → **AttributeError → 500** when a payment is recorded against such an account. Not fail-closed (violates the P5/H-4 pattern). |
| F-6 | **High** (silent email failure) | `invoice-detail-client.tsx:155` + `use-invoices.ts:287` + backend `tasks.py:20-46` | Send-invoice passes `to: invoice.contact.email` (a **string**); the backend truthiness check passes it through unwrapped and the Celery task builds `EmailMultiAlternatives(to=<string>)` → `TypeError` inside the task (caught, logged, retried forever) while the API already returned success and the UI toasts "Invoice sent". Permanent silent failure. |
| F-7 | **High** (error truth) | `apps/web/src/lib/api-client.ts:141-148` | `handleResponse` reads `errorData.message \|\| errorData.detail` — the backend envelope is `{"error": {"code", "message", "details"}}` and DRF field errors are `{"field": ["msg"]}`. Neither key exists → **every business-rule failure surfaces as "Request failed: Bad Request"**, hiding messages like "Void reason is required." (this is what masked F-1). |
| F-8 | **Medium** (stale cache) | `apps/web/src/hooks/use-invoices.ts:262-271` | `useVoidInvoice.onSuccess` does not invalidate `[orgId, "ledger"]` although voiding creates the reversal journal entry (the toast even says so); `useApproveInvoice` does invalidate it. Ledger page serves stale rows for the staleTime window. |
| F-9 | **Medium** (accounting truth) | `apps/backend/apps/reporting/services/dashboard_service.py:262` | `query_outstanding_payables` filters `status__in=["APPROVED", "OVERDUE"]` — **`PARTIALLY_PAID` purchase bills vanish from outstanding payables** (receivables at line 246 correctly includes it). Since P6/F-4 second allocations exist, this state is reachable and materially understates payables. |
| F-10 | **Medium** (unvalidated writes + missing permission) | `apps/backend/apps/peppol/views.py:128-149`, `apps/core/views/organisations.py:300-341` | `PeppolSettingsView.patch` and `OrganisationSettingsView.patch` setattr raw `request.data` onto models with no serializer/type/choices validation (`"retry_attempts": "abc"` → 500; invalid `entity_type` → DB CHECK IntegrityError → 500), and both carry only `IsOrgMember` while the sibling `OrganisationDetailView.patch` correctly requires `can_manage_org` — any member can flip `invoicenow_enabled`/AP provider/base currency. |
| F-11 | **Medium** (500s on bad query params) | `banking/views.py:201,205,453,457,594-598`; `journal/views.py:53-57,179,214,363`; `coa/views.py:262,298`; `gst/views.py:300,472`; `invoicing/views.py:163` | Malformed `date_from`/`date_to`/UUID/int query params raise `ValueError`/`InvalidOperation` → 500 instead of 400 (`banking/views.py:594` additionally uses a bare `except:` that silently defaults an invalid `tolerance`). |
| F-12 | **Medium** (untruthful states) | `ledger-client.tsx:44-46`, `settings-client.tsx:58`, `invoice-detail-client.tsx:102` | With `currentOrg == null` (authenticated, no organisation), disabled queries report `isLoading=false` → the three P6 pages render **"Failed to load…" / fake empty states** for a legitimately org-less user (the P5 invoices client guards this correctly with `authLoading`). |
| F-13 | **Medium** (mock-era leftovers / dead code) | `apps/web/src/app/(dashboard)/invoices/[id]/edit/`, `use-invoices.ts:187,313,359,381`, `lib/server/api-client.ts` | The Edit route is an orphaned mock-era stub: no links point at it, `generateStaticParams` ships demo IDs, `params` read synchronously (the P6/D-1 class), and its form would **create a duplicate contact + new DRAFT invoice** if reached by URL. `useUpdateInvoice`, `useSendInvoiceNow`, `useInvoiceNowStatus`, `useInvoicePDF` have zero importers; `lib/server/api-client.ts` is a stale legacy server client (reads cookies the current design never sets, calls the duplicate `/dashboard/` endpoint). |
| F-14 | **Medium** (hardcoded GST flag) | `invoices/new/page.tsx:31`, `edit/edit-invoice-client.tsx:36` | `isGSTRegistered={true}` hardcoded — a non-GST org gets GST columns/tax breakdown as if registered (`currentOrg.gst_registered` is available and the detail page already uses it). |
| F-15 | **Low** (permission consistency) | `apps/reporting/views.py:29-30,49-50`, `apps/gst/views.py:207-208,264-265` | `DashboardMetricsView`/`DashboardAlertsView` lack `CanViewReports` (the core twin requires it — any member sees financial metrics); `GSTCalculateView`/`GSTCalculateDocumentView` lack `IsOrgMember` (tenant middleware still blocks non-members — defense-in-depth gap only). |
| F-16 | **Low** (a11y) | `components/ledger/ledger-table.tsx:46-67`, `components/layout/shell.tsx:122,240` | Sortable `<th>`s lack `aria-sort`/`scope="col"`; mobile nav `aria-controls="main-navigation"` has no matching `id` on the `<nav>`. |
| F-17 | **Low** (placeholders) | `components/layout/shell.tsx:205-208,259-266` | "Demo User"/"user@example.com" fallbacks render for null users; header "New Invoice" button has no handler (dead button). |
| F-18 | **Low** (unhandled rejection) | `invoice-detail-client.tsx:150-161` | `handleSend` awaits `mutateAsync` with no `catch` → unhandled promise rejection on failure. |

De-escalated (recorded, no action): scanner criticals in `skills/`, fixtures, dev credentials
and the `CREATE SCHEMA IF NOT EXISTS {schema}` f-strings (hardcoded name list, no user
input — verified); duplicate dashboard surfaces (`apps/core` vs `apps/reporting`
DashboardService — the frontend only calls the reporting one; consolidation is registered
debt M-15, not a behavior bug); revenue/threshold status sets excluding `SENT`/`OVERDUE`
(Sent precedes approval in the transition map; ties into the F5 rate-basis deferred item).

---

## 1. Task 1 (F-2): status-transition endpoint — real validation + authorization

`StatusTransitionSerializer.status` becomes a `ChoiceField` over
`InvoiceDocument.STATUS_CHOICES`. `InvoiceDocumentStatusView.post` gets a per-target-status
permission map: `APPROVED → can_approve_invoices`, `VOID → can_void_invoices` (literal
fixed from `"VOIDED"`), and the **payment-derived statuses (`PARTIALLY_PAID`, `PAID`) are
rejected outright** on this generic endpoint — they are owned by the allocation service
(`allocate()`/`unallocate()` derive them). `SENT`/`OVERDUE` transitions likewise require
`can_approve_invoices` (they are operational lifecycle transitions gated by the same role
in `transition_status`'s contract).
RED tests (`tests/integration/test_document_status_view_p7.py`): member WITHOUT
`can_void_invoices` POSTing `{"status": "VOID"}` → 403 (bypass closed); member WITH the
permission → 200 + reversal journal entry exists; `{"status": "PAID"}` → 400 with a clear
message; `{"status": "VOIDED"}`/`{"status": "GARBAGE"}` → 400 (ChoiceField).

## 2. Task 2 (F-3): organisation create — drop the phantom `address` field

`OrganisationCreateSerializer.address` is deleted (the model has `address_line_1/2`, city,
postal_code, country — already on the serializer via PATCH's allowlist semantics; DRF
ignores undeclared payload keys, so clients sending `address` get a clean 201 no-op exactly
like the PATCH path). RED test: `POST /api/v1/organisations/` with `address` in the payload
→ 201 (currently 500 `TypeError`).

## 3. Task 3 (F-4): fiscal endpoints routed — shadowed module retired

The three org-scoped fiscal routes (`fiscal-periods/`, `fiscal-years/<year_id>/close/`,
`fiscal-periods/<period_id>/close/`) move from the shadowed `apps/core/urls.py` into the
active `apps/core/urls/` package (registered in `org_scoped_urlpatterns`); the shadowed
module is deleted after a zero-reference check. While routing them, the two close views get
the audited hardening: `CanManageOrg` permission and `timezone.now()` instead of naive
`datetime.now()` (`fiscal.py:80,119`); the "all periods closed" validation stays registered
debt (it is a behavior change beyond routing). RED tests: `GET /api/v1/{org}/fiscal-periods/`
→ 200 (currently 404); `fiscal-years/{id}/close/` reachable (403/200 by permission, no
longer 404); member without `can_manage_org` → 403 on close.

## 4. Task 4 (F-5): payments fail closed on a bank account without a GL account

`create_received`/`create_made` validate `bank_account.gl_account` before any write and
raise `ValidationError("Bank account '<name>' has no GL account configured…")` → 400. RED
tests (`apps/banking/tests/…`): payment against a `gl_account=None` bank account → 400 with
the message (currently 500 AttributeError); happy path unchanged.

## 5. Task 5 (F-7): api-client reads the real error envelope

`handleResponse` extracts, in order: `errorData?.error?.message` (the wrap_response
envelope), `errorData?.message`, `errorData?.detail`, then the first DRF field error
(`{"field": ["msg"]}` → `"field: msg"`), then the statusText fallback. `ApiError.errors`
carries `errorData?.error?.details ?? errorData`. RED vitest (`src/lib/__tests__/`):
envelope shape → "Void reason is required."; DRF field shape → "reason: This field is
required."; plain fallback unchanged; non-JSON body → fallback.

## 6. Task 6 (F-1 + F-8): the Void button works — reason dialog + ledger invalidation

`invoice-detail-client.tsx` gains a void-reason dialog (existing Shadcn Dialog + a required
Textarea; submit disabled while pending or empty; server error rendered via the F-7 parser).
`useVoidInvoice.onSuccess` additionally invalidates `[orgId, "ledger"]`. RED vitest
(`invoices/[id]/__tests__/`): clicking Void opens the dialog; submitting an empty reason
shows the validation message and does NOT call the API; submitting a reason calls
`mutate(reason)`; the hook test asserts the ledger invalidation. Gated e2e assertion added
to the invoices spec (dialog opens, empty submit blocked).

## 7. Task 7 (F-6): send-invoice recipients — array contract on both sides

Frontend: `to: [invoice.contact.email]`, hook type `to: string[]`. Backend
(`InvoiceSendView`): a small serializer (`EmailField list`) normalizes a single string to a
one-element list and rejects non-email strings → 400 (fail-closed instead of the silent
task crash). RED: backend test posting `to: "user@x.com"` → 200 and the task receives
`["user@x.com"]` (mocked `.delay`); posting `to: "not-an-email"` → 400; vitest asserting
the page/hook sends an array.

## 8. Task 8 (F-9): outstanding payables includes PARTIALLY_PAID

`query_outstanding_payables` status set becomes `["APPROVED", "PARTIALLY_PAID", "OVERDUE"]`
(mirroring receivables; the `amount_paid__lt` filter already handles the arithmetic). RED
test (reporting service tests): a PARTIALLY_PAID purchase bill with amount_paid < total
counts in outstanding payables (currently invisible).

## 9. Task 9 (F-12 + F-14 + F-17): frontend truthfulness batch

- Ledger/detail/settings clients: guard `!currentOrg` (from `useAuth`) with a dedicated
  "Select an organisation" state rendered before the query states (mirrors the P5 invoices
  client's `authLoading` guard).
- `invoices/new/page.tsx` + the edit stub's GST flag: `isGSTRegistered={!!currentOrg?.gst_registered}`.
- Shell: "Demo User"/"user@example.com" fallbacks → neutral fallbacks (empty string /
  "Member"); header "New Invoice" dead button → `<Link href="/invoices/new">`.
RED vitest per surface (render with `currentOrg=null` → the no-org state, never "Failed to
load"; GST flag off for non-GST org; shell renders the link).

## 10. Task 10 (F-10): settings PATCHes validated + permission-gated

`PeppolSettingsView.patch` and `OrganisationSettingsView.patch` move to typed serializers
(IntegerField/BooleanField/ChoiceField for `entity_type` from the model vocabulary,
`fy_start_month` 1-12, 3-char `base_currency`) and both add `CanManageOrg`. RED tests:
`retry_attempts: "abc"` → 400 (not 500); invalid `entity_type` → 400 (not IntegrityError
500); member without `can_manage_org` → 403; valid PATCH round-trips.

## 11. Task 11 (F-11): malformed query params → 400, not 500

A tiny shared helper (`parse_date_param`/`parse_uuid_param`/`parse_int_param` →
`ValidationError`) applied at the audited sites: banking `date_from/date_to` (both list
views) + the bare-`except:` tolerance probe, journal UUID/date params + `account_id`, coa
`fiscal_year_id`/`limit`, gst `year`/`days`, invoicing `contact_id`. RED tests: each
endpoint with garbage params → 400 with a message (currently 500); valid params unchanged.

## 12. Task 12 (F-13 + F-18): dead-code truth pass (frontend)

- Delete the orphaned `invoices/[id]/edit/` route + `edit-invoice-client.tsx` (mock-era
  stub that would create duplicates; the real edit flow — due_date/reference/notes, line
  editing — is registered debt).
- Delete `useUpdateInvoice` (orphaned with the route). **Wire** `useInvoicePDF` into the
  detail page (a real "Download PDF" button — the backend endpoint and the P3/D-2 auth
  path already exist; converts dead code into a shipped feature). **Wire**
  `useSendInvoiceNow` into the detail page for APPROVED+ invoices (the P5/C-2 real
  transmission path) with the `useInvoiceNowStatus` status shown on the detail card.
- Delete `lib/server/api-client.ts` (stale legacy client; zero importers) → move
  `BACKEND_URL` to the reserved section of `apps/web/.env.example` + root index (it becomes
  unread; the file's own header claims it reads `src/lib/server/api-client.ts`).
- `handleSend` unhandled rejection: `try/catch` (onError already toasts) or `.mutate()`.
RED/GREEN vitest: PDF button calls `api.blob` with the right URL; InvoiceNow send button
visible on APPROVED, hidden on DRAFT; no test references the deleted modules remain.

## 13. Task 13 (F-15 + F-16): permission classes + a11y batch

`DashboardMetricsView`/`DashboardAlertsView` += `CanViewReports`;
`GSTCalculateView`/`GSTCalculateDocumentView` += `IsOrgMember`. Ledger table `<th>`s get
`scope="col"` + `aria-sort`; shell `<nav>` gets `id="main-navigation"`. RED tests: metrics
endpoint without `can_view_reports` → 403; ledger-table a11y assertions in the existing
component test.

## 14. Task 14: test-suite extension (vitest + playwright) and config verification

This sprint's additions ride the existing configs — the new vitest files live under
`src/**/__tests__/` (matched by the existing `include`) and the new e2e specs under `e2e/`
(chromium project, `E2E_API_URL`-gated where backend-dependent, per the B-1/D-5 patterns).
The configs themselves are audited and left unchanged unless a new file requires otherwise
(none expected — documented with evidence in the report). New suites:
`test_document_status_view_p7.py` (auth), banking fail-closed tests, reporting payables
tests, settings-serializer tests, query-param-400 tests (backend, est. +28);
api-client envelope tests, void-dialog tests, no-org-state tests, PDF/InvoiceNow wiring
tests, a11y assertions (frontend, est. +24); gated e2e: void-reason flow, error-message
display (est. +2 specs).

## 15. Task 15: docs truth pass, `.env.example`, screenshots, session log, report, worklog

- README / PAD / `ledgersg_SKILL.md` / AGENTS.md / CLAUDE.md: P7 milestone module, new
  counts, the fiscal routes now live, P7 lessons appended to the skill (numbering
  continues from 19).
- `docs/DEPLOYMENT.md` rewritten as a **fresh-host step-by-step guide** from
  `git clone https://github.com/nordeim/ledgersg.git` (prereqs → clone → PG §rootless →
  schema → Redis → backend venv + check → frontend install → Celery → run + verify
  checklist), counts refreshed (588+new backend, 383+new vitest, 20+new e2e), the P7
  endpoint changes noted.
- `.env.example` files re-verified var-by-var against the code (backend `config()` calls,
  web `process.env` reads); the only expected change is `BACKEND_URL` → reserved (Task 12).
- Screenshots of the remediated pages (login, dashboard, invoices list, invoice detail
  **with the void dialog open**, ledger, settings) into `docs/screenshots/` (continuing
  numbering, `_session14` tags) via the real UI login path with content-based waits.
- `docs/REMEDIATION_2026-11-22_P7_REPORT.md`, `docs/session_15.md` (session-14 log per the
  naming convention), `worklog.md` entry.

---

## 16. Verification Gate (definition of done for the sprint)

| # | Gate | Expected |
|---|---|---|
| 1 | `pytest --reuse-db --no-migrations -q` | all green (588 baseline + new, 0 failed) |
| 2 | `npm run typecheck` / `npm run lint` (touched files) / `npm test` | clean / parity / all green |
| 3 | `npm run test:e2e` (no backend) | green, new specs gated with reasons |
| 4 | `npm run test:e2e:full` (live backend + Redis + seeded dev DB) | all green incl. void-dialog + error-message specs |
| 5 | Authorization spot checks | VOID via `/status/` without `can_void_invoices` → 403; settings PATCH without `can_manage_org` → 403; dashboard metrics without `can_view_reports` → 403 |
| 6 | API truth spot checks | org create with `address` → 201; `fiscal-periods/` → 200; payment on GL-less bank account → 400 with message; send-invoice with string `to` → 200 + list to the task; garbage query params → 400 |
| 7 | UI truth spot checks | Void dialog enforces a reason and the mutation succeeds end-to-end; error toasts show the backend message; no-org users see "Select an organisation" (never "Failed to load"); PDF + InvoiceNow buttons live on the detail page |
| 8 | Screenshots | ≥ 6 new non-empty unique PNGs (content-verified, not loading spinners) |
| 9 | Docs sweep | no stale claims for P7-fixed items; DEPLOYMENT.md step-by-step from clone; `.env.example` matches the code |
| 10 | `git status` clean; commit set matches §17 | all on `main` |

## 17. Commit Plan (conventional commits, single branch `main`)

1. `fix(invoicing): status-transition endpoint validates status + enforces per-status permissions (P7/F-2)`
2. `fix(core): organisation create drops the phantom address field (P7/F-3)`
3. `fix(core): fiscal-period/close endpoints routed; shadowed urls module retired; close views hardened (P7/F-4)`
4. `fix(banking): payments fail closed on bank accounts without a GL account (P7/F-5)`
5. `feat(web): api-client surfaces the backend error envelope (P7/F-7)`
6. `feat(web): working void flow — reason dialog + ledger cache invalidation (P7/F-1, F-8)`
7. `fix(invoicing): send-invoice recipient list contract on both sides (P7/F-6)`
8. `fix(reporting): outstanding payables includes PARTIALLY_PAID bills (P7/F-9)`
9. `feat(web): truthful no-org states + org-derived GST flag + shell links (P7/F-12, F-14, F-17)`
10. `fix(peppol,core): settings PATCHes typed + CanManageOrg-gated (P7/F-10)`
11. `fix(api): malformed query params return 400 across audited endpoints (P7/F-11)`
12. `refactor(web): remove mock-era edit route + dead server client; wire PDF + InvoiceNow actions (P7/F-13, F-18)`
13. `fix(reporting,gst): missing permission classes; ledger table a11y (P7/F-15, F-16)`
14. `docs: P7 truth pass — README/PAD/CLAUDE/AGENTS/ledgersg_SKILL + DEPLOYMENT fresh-host guide + .env.example`
15. `docs(worklog): session 14 worklog, session log, P7 report + screenshots`

(Adjacent tasks may fold where they share a RED→GREEN cycle; the split is preferred for
reviewability. Push incrementally after each task — the workspace-reset safeguard.)

## 18. Deferred Debt Register (explicit, not silent)

Carried forward from P6 §11 unchanged: H-02 base-currency reporting; M-1 audit-event
coverage beyond banking; M-10 CSRF hardening for cookie-auth endpoints; M-11 static-export
security headers/CSP enforcement; M-14 Storecove authenticate semantics; H-07 backend ruff
debt (touched files stay clean); frontend eslint debt (touched files stay parity); F5 GST
return rate-basis; A-10 stale root `requirements.txt`; GST payment tracking (`pay_return`);
invoice-form existing-contact picker; Reg-11 tax-invoice labelling/Schematron;
`status_history` returns `[]` pending the audit module; reports/quotes real pages (static
cards today — the FinancialReport/trial-balance endpoints exist; a real reports page is the
P8 candidate); `account_type` seed-column population.

New this sprint (registered, not silently dropped):
- **B6 list-envelope standardization** (`data` vs `results`; `my_organisations` bare array)
  — needs a synchronized frontend contract change across auth paths; cosmetic consistency,
  deferred to avoid contract churn inside this sprint.
- **Invoice edit flow** (due_date/reference/notes + line editing) — the mock-era route was
  removed truthfully; a real edit page needs the backend update contract widened.
- **Ledger pagination** (F-11-adjacent, frontend agent finding): `LedgerView` is unpaginated
  end-to-end; fine at demo scale, degrades for real ledgers.
- **Settings form reset UX** (unsaved org edits wiped on refetch), **org-state propagation
  to the auth provider**, **`fiscal.py` close-view period-closed precondition** (B9),
  **COA serializer silently-dropped fields** (`gst_tax_code_id`/`bank_account_id`),
  **`checkSession` transport-error vs 401 distinction**, **dashboard service duplication**
  (core vs reporting implementations).
- **Ledger `aria-sort`** shipped in Task 13; the invoice-form textarea label associations
  and `role="table"` ARIA fixes (F-14-class) remain.

## 19. Open decisions resolved by this plan

- **F-2 permission map:** payment-derived statuses (`PARTIALLY_PAID`, `PAID`) are outright
  rejected on the generic status endpoint (the allocation service owns them); `SENT`/
  `OVERDUE`/`APPROVED` map to `can_approve_invoices`, `VOID` to `can_void_invoices`. The
  dedicated `/approve/` and `/void/` endpoints keep their existing permissions and remain
  the canonical paths — the status endpoint is the generic escape hatch that must not be
  weaker than them.
- **F-3 shape:** drop `address` from the create serializer (consistent with the PATCH
  no-op semantics fixed in P6/F-10) rather than mapping it to `address_line_1` — an
  API-advertised phantom field must disappear, not gain a secret alias.
- **F-4 scope:** route + harden permissions/timezone now; the "all periods closed"
  validation is a behavior change beyond routing and stays registered.
- **F-13 edit route:** remove (truthful) + register the real edit flow as debt — do not
  half-ship an edit page under sprint pressure; wire the two dead hooks that have real,
  working backends (PDF, InvoiceNow) instead.
- **BACKEND_URL:** moves to the reserved section (its only reader is deleted); the root
  index and web template are updated in the same commit so the template never advertises a
  live variable that nothing reads.
- **Test configs:** the existing `vitest.config.ts`/`playwright.config.ts` already match
  every new file location; configs are audited and unchanged (evidence in the report) —
  the "add test suites" directive is satisfied by the new vitest/e2e files the configs
  pick up, not by no-op config edits.
