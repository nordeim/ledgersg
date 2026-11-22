# LedgerSG — Remediation Plan (P10 Sprint: Self-Serve Onboarding & Contact Truth — Registration, Real Contact Selection, GST F5 Visibility, Wire-Contract Closure)

- **Date:** 2026-11-22
- **Branch:** `main` only (per repo convention)
- **Inputs:** post-P9 audit of the `2a7b498e` state (HEAD `e37f12f0` = the session-log doc commit). Findings gathered per `skills/skills-catalog.md`: the `vulnerability-scanner` scanner pass (all hits in the documented FP classes — comments, test fixtures, dev-compose defaults, the M-14 Storecove docstring, an f-string error message; zero new production hits) plus three parallel deep-audit agents (P9-diff regression audit, deferred-register validation, fresh-surfaces gap audit) with `code-review-and-audit` / `code-quality-standards` discipline. Every Critical/High/Medium finding below was re-verified against the working tree with line numbers by the lead before this plan was written, including a live build check (`npm run build` fails; `npm run build:server` passes) and a live coverage check (`npm run test:coverage` fails its thresholds).
- **Method:** TDD (RED → GREEN → full gate), lint parity on touched files, conventional commits, `skills/` excluded from all checks/tests/compilation.
- **Baselines reproduced before any change (this session, exact):** backend **668 passed / 0 failed / 5 skipped**, vitest **454/454**, typecheck **0 errors**, e2e default **9 passed + 17 gated skips**, `npm run build:server` green — the documented P9 state, reproduced exactly before any change.

---

## 0. Audit Summary (the register this plan is built on)

P9 closed the onboarding dead end for a user who *has an account*, and made the payment
workflow real. The post-P9 audit has three heads: **(a) the self-serve loop is still
open** (there is no way to create an account — the login page's "Create account" link is
`href="#"` while `POST /api/v1/auth/register/` exists with zero consumers), **(b) contact
truth** (every invoice/quote submission blindly creates a brand-new contact — a repeat
UEN-bearing customer *fails* with DuplicateResource, a UEN-less one silently duplicates
rows that fragment the aged AR/AP and flood the picker), and **(c) half-wired compliance
and correction surfaces** (the GST F5 tab lets a user *File* a statutory return whose
computed boxes the UI never displays; bank-account *update* still carries the exact
null-PayNow bug P9 fixed on create; the transmission error key masks XSD failures) —
plus **(d) broken gates** (the CI trigger is corrupted — `branches: ain, develop]` — so
CI has never run on main; the vitest coverage thresholds have never passed; the
static-export build mode fails).

| ID | Severity | Location | Finding (Verified) |
|---|---|---|---|
| H-1 | **Critical** (data corruption + core-flow failure) | `invoice-form.tsx:154-156,260-279`; `contact_service.py:135-136` | Every invoice/quote submit unconditionally `createContact.mutateAsync(...)` — the form has NO contact picker. Backend dedups only on UEN: invoicing the same UEN-bearing customer twice **fails** (`DuplicateResource` — the second invoice cannot be created); UEN-less repeats (the common case) **silently duplicate the contact row**, fragmenting aged AR/AP (grouped by contact), flooding the P9 ContactPicker with identical entries, and preventing Peppol recipient data from accumulating on one master record. |
| H-2 | **Critical** (product dead end — the P9 sequel) | `login/page.tsx:157-170`; `core/urls/auth.py:10`; `core/views/auth.py:31-61` | "Create account" is a dead `href="#"` link; **no registration page exists anywhere** while `POST /api/v1/auth/register/` (rate-limited, returns `{user, tokens}` + sets the P4 session cookies) has zero frontend consumers. A brand-new self-serve user cannot enter the product at all — P9's organisation-creation page is unreachable without curl. "Forgot password?" is equally dead (no backend endpoint exists). |
| H-3 | **High** (compliance surface half-wired) | `reports-client.tsx:425-490`; `use-reports.ts:166-198`; `gst/urls.py:29-37`; `return_service.py:237,343` | The GST F5 tab lets a user **File a statutory return whose computed boxes the UI never displays** (`useGSTReturn` — the detail hook carrying `boxes` — is dead; only `net_gst` renders). The empty state literally says "Periods are created from the API" while `useCreateGSTReturnPeriods` sits implemented and unconsumed. `review_return`/`amend_return` services exist but Review is **unrouted** and Amend/pay/deadlines have zero UI; the StatusBadge renders statuses (REVIEWED/AMENDED) the UI can never produce. |
| M-1 | **High** (the P9/B-4 fix incomplete on the sibling path) | `banking/serializers/bank_account.py:174-225` | `BankAccountUpdateSerializer` derives `paynow_type` from the model: PATCH `{"paynow_type": null}` → **400** (the exact wire value P9 fixed for create), and PATCH `{"paynow_type": ""}` passes (`allow_blank`) but violates the DB CHECK (`NULL OR UEN/MOBILE/NRIC`) → **IntegrityError 500**. `validate()` normalizes only `paynow_id` ""→None (I-5: clearing `paynow_id` alone leaves a dangling `paynow_type`). |
| M-2 | **High** (latent 500 on a public service seam) | `document_service.py:437-440,755` | `transition_status`'s P9/K-1 VOID delegation: `void_user = AppUser.objects.get(id=user_id) if user_id else None` then `void_document(..., user=void_user)` → `user.id` deref at :755 → **AttributeError 500 when `user_id=None`** (the signature advertises `None`), and `DoesNotExist` → 500 for a deleted user. One direct service caller away; the test suite already passes a user. |
| M-3 | **Medium** (dead integration + daily annoyance) | `auth-provider.tsx:115-120,212-219`; `core/views/auth.py:292` | Org selection **resets to the default on every page refresh** (`checkSession` unconditionally re-resolves the default; `switchOrg` only sets React state) — `POST /auth/set-default-org/` (backend real, routed) has **zero frontend callers**. Multi-org users snap back on any hard navigation. |
| M-4 | **Medium** (diagnosability; blunts the P9/S-3 fix) | `transmission_service.py:238-240` vs `xml_validation_service.py:147,177` | The transmission path reads `validation_result.get("errors", …)` but the validator writes `schema_errors`/`schematron_errors` — every XSD failure surfaces as the literal string "Unknown validation error"; the P9 fail-closed message is unreachable. |
| M-5 | **Medium** (unreachable corrections) | `invoicing/views.py:45-137`; `use-contacts.ts:84-149` | Contacts management is API-only: full backend CRUD (list w/ filters, create, GET/PATCH/DELETE-deactivate) and complete frontend hooks (`useContact`/`useUpdateContact`/`useDeactivateContact` — all dead) with **no page anywhere**. A wrong Peppol ID or email (Peppol ID is required for InvoiceNow sends) can never be corrected in-app. |
| M-6 | **Medium** (dead hooks, uncorrectable data) | `banking/views.py:118-163`; `use-banking.ts:65,114,147`; `bank-account-dialog.tsx:37` | Bank-account **edit/deactivate** absent: the dialog wires only `useCreateBankAccount`; `useBankAccount`/`useUpdateBankAccount`/`useDeactivateBankAccount` are dead. A mis-typed account number cannot be corrected in-app. |
| M-7 | **Medium** (audit blindness) | `banking/serializers/payment.py:29-53`; `banking/views.py:341-353`; `use-banking.ts:218,301` | Payment allocations are invisible after creation: the list serializer carries no `allocations`; `PaymentDetailView` returns them but `usePayment`/`useAllocatePayment` are dead. Users can never see which invoices a payment settled. |
| M-8 | **Medium** (unactionable dead end) | `core/views/fiscal.py` (close-only); `document_service.py:646-650` | Invoice approval raises "No open fiscal period found… Please open the fiscal period or change the invoice date" — but **no endpoint can OPEN a period** (only FiscalYearClose/FiscalPeriodClose exist) and no UI consumes any fiscal endpoint. A back-dated invoice outside the seeded periods is a hard dead end whose error points at an impossible action. |
| M-9 | **Medium** (truth violation) | `settings-client.tsx:295-301`; `core/urls/auth.py:24` | Change-password is backend-real (`POST /auth/change-password/`, expires the session cookies) with zero UI; the Settings User Profile card claims "Profile editing is handled by your account settings" — **no such surface exists anywhere**. |
| M-10 | **Medium** (error points at a nonexistent surface) | `peppol/views.py:65-163`; `document_service.py:917-922` | `peppol/settings/` (GET member-readable / PATCH manager-gated, typed serializer: enabled, participant_id, auto_transmit, access_point_provider, retry_attempts) has zero frontend consumers. "Send via InvoiceNow" 400s with "Configure an access point (Peppol settings)…" pointing users at a settings surface that does not exist. |
| M-11 | **High** (broken gate) | `.github/workflows/ci.yml:14-18` | The CI trigger is corrupted YAML — `branches: ain, develop]` (a mangled `[main`): **CI has never run on a push to main**. The backend (schema-init + pytest), frontend (typecheck + vitest + `build:server`) and security jobs are all dead weight until the trigger is fixed. |
| M-12 | **Medium** (broken documented mode) | `package.json:9-11`; `invoices/[id]/page.tsx`; `quotes/[id]/page.tsx`; `DEPLOYMENT.md §9` | `npm run build` (static export) **fails**: `/quotes/[id]` (and `/invoices/[id]`) lack `generateStaticParams` — the mock-era params were deleted when the pages went client-driven, and static export cannot support API-driven detail routes at all. DEPLOYMENT.md §9 still documents `npm run build && npm run serve` as a working "Static CDN build" mode. (`build:server` passes — verified live.) |
| M-13 | **Medium** (config-level lie) | `vitest.config.ts:26-31` | The coverage thresholds (lines/functions/statements 85%, branches 80%) have **never passed** — measured today: lines 64.57%, functions 53.95%, statements 64.05%, branches 49.9%. A gate that never ran green (coverage is not part of any CI or pre-push gate) and whose configured bar is fiction. |
| L-1 | Low | `invoice-detail-client.tsx:143,176,196,278` | All four back links hardcode `/invoices` — quote users are dumped on the invoice list; the error card says "Failed to load invoice" for quotes. |
| L-2 | Low | `payment-list.tsx:98-102`; `transaction-list.tsx:106-110` | "Load more" buttons are doubly dead: no `onClick` AND never rendered (they render only when `data.next` is truthy; the backend never sends `next`). Unbounded list responses are the registered pagination debt. |
| L-3 | Low | `allocation-section.tsx:45-48` | `useInvoices(orgId, {contact_id: ""})` fires an org-wide invoice fetch on every form mount before a contact is picked (empty string is filtered out of the query). |
| L-4 | Low | `import-transactions-form.tsx:99-106` | The import result renders only "`{errors.length}` errors occurred" — the actionable per-row messages the backend returns are dropped. |
| L-5 | Low | `payment-filters.tsx:62-109` | WCAG label-association gaps: three `<label>`s without `htmlFor`/id pairing (transaction-filters does it correctly). |
| L-6 | Low | `reconciliation_service.py:416-418` vs `use-banking.ts:554-560` | `suggest_matches` rows can carry `contact: None`; the frontend type declares `contact: string` — a null maps into `contact_name` and renders blank. |
| L-7 | Low | `banking-client.tsx:34,271` | `useSearchParams()` in a statically-prerendered client tree without a Suspense boundary — one layout refactor away from a `next build` break (today dodged only because the dashboard layout gates children on `mounted`). |
| L-8 | Info | `transmission_service.py:225-226` vs the C-3 gate | The credit-note XML generation branch is newly unreachable (the P9 invoice-only gate refuses SALES_CREDIT_NOTE too) — intended per the plan's wording; the gate comment overstates the mapping rationale. Registered, no action this sprint. |

Verified-clean (explicit): the P9 seed backfill (idempotent, `IS DISTINCT FROM`); the
unfiltered list top-level default (still hides children by design, `is_bank` lifts it);
the checkSession transport/auth split (only 401/403 clear); postForm (headers, auth,
401-retry, non-JSON fallback); the convert envelope (pinned + unwrapped); the InvoiceNow
gate (400/403/200 all test-pinned); list-serializer additions (`related_document_id`,
`amount_paid`/`amount_due` — all consumers updated); status_history shape; aged as-at
bound; dashboard truth; CONVERTED badge; useContacts filter keys; org-creation page
flow; void/unreconcile row actions; requirements.txt tombstone; e2e gating/serial mode.
No dead `href="#"` in dashboard pages beyond the login pair; nav links all resolve.

---

## 1. Task 1 (H-2): the registration page — the self-serve loop closes

New page `/register` (mirrors the login page's structure/styling;
`RegisterSerializer` fields: full_name, email, password with the backend's
12-char minimum — `AUTH_PASSWORD_VALIDATORS` `min_length: 12` — mirrored
client-side; Django's `validate_password` messages surface via the error
envelope). Submit → `api.post` `endpoints.auth.register` → on 201 store tokens via
the existing api-client session path (the response carries `tokens` + the P4 cookies)
→ `refreshOrganisations()` → no org (the fresh state) → route to
`/settings/organisations/new` (the P9 page — registration remains org-less by backend
design) → the org-creation flow lands the user on the dashboard. The login page's
"Create account" links to `/register`; **"Forgot password?" is removed** (no backend
endpoint exists — truthful removal; password reset is registered debt needing an
email-delivery design decision). RED-first vitest (validation, payload, success path,
org-less redirect); the login-page link test updates.

## 2. Task 2 (H-1): the invoice form picks real contacts — no more duplicate rows

The Customer card's raw name/email/UEN/GST inputs become a **two-mode control**:
- **Select mode** (default): the P9 `ContactPicker` (search by name, `?is_customer=`;
  the component moves from `app/(dashboard)/banking/components/` to
  `src/components/` — a shared seam with two consumers now); picking an
  existing contact sends `contact_id` — no contact is created.
- **New-customer mode** (explicit "New customer" toggle): the current fields render;
  submit creates the contact as today (the explicit user intent the flow was missing).
`invoice-submit.ts` gains a `buildContactPayload`-only-when-new contract; the form
payload carries `contact_id` OR the new-customer fields. The quotes new page (shared
form) inherits the fix. RED-first vitest: picking an existing contact posts the
document with `contact_id` and **does not** call createContact; new-customer mode
still creates; the DuplicateResource failure path surfaces the backend message.

## 3. Task 3 (M-5): contacts management — list, edit, deactivate

New `/contacts` page (nav entry): searchable list (`?search=&is_customer=&is_supplier=`
— the backend's real filter keys), type badges, and row actions: **Edit** (dialog with
the PATCH allowlist fields — name, email, phone, uen, gst_registration_no, peppol_id,
address fields per the update serializer) and **Deactivate** (confirm dialog →
DELETE-deactivate). Consumes `useContacts`/`useUpdateContact`/`useDeactivateContact`
(three dead hooks live). RED-first vitest for list render, edit round-trip, deactivate
gating.

## 4. Task 4 (H-3): the GST F5 tab tells the whole truth

- **Boxes visible before File**: the returns table gains a "View boxes" expand per row
  consuming `useGSTReturn` — the IRAS box table (1/2/3/4/5/6/7/8/13/14 with values,
  the schema's own convention) renders from the computed return; File stays but the
  user can no longer file blind.
- **Periods creatable from the UI**: the empty state's dead text is replaced by a
  "Create return periods" dialog (filing_frequency + period start) consuming
  `useCreateGSTReturnPeriods`.
- **Review routed + wired**: `review_return` gets its route (`POST returns/{id}/review/`,
  manager-gated to match file); the row gains Review (COMPUTED→REVIEWED) and Amend
  (FILED→AMENDED) actions consuming the amend endpoint. Pay stays deferred (the
  backend refuses fail-closed — registered).
- **Deadlines banner**: `GET returns/deadlines/` renders the next upcoming deadline on
  the tab.
RED-first: pytest for the review route (403 member / 200 manager / wrong-status 400);
vitest for boxes render, the periods dialog, the new actions' gating, the deadline row.

## 5. Task 5 (M-1 + the I-5 rider): bank-account update — the null-PayNow parity

`BankAccountUpdateSerializer` gains the create path's overrides: `paynow_type`
ChoiceField(allow_null=True) + `paynow_id` (allow_blank/allow_null) + `""`→None
normalization for BOTH fields (clearing `paynow_id` while a type remains now 400s
cleanly instead of storing a dangling pair). RED (pytest): PATCH null → 200 stored
NULL; PATCH `""` → 200 stored NULL (was IntegrityError 500); dangling pair → 400.

## 6. Task 6 (M-2): the VOID seam fails closed, not with a traceback

`transition_status`'s VOID branch: a missing `user_id` raises a clean
`ValidationError("user_id is required to void a document (the reversing journal entry
needs a poster)")` and an unknown user id raises the same (no DoesNotExist 500 — the
posted_by NOT NULL constraint is the reason; fail-closed beats AttributeError). RED
(pytest): `user_id=None` → ValidationError (was AttributeError); deleted user →
ValidationError (was DoesNotExist).

## 7. Task 7 (M-3): the chosen org survives the refresh

`switchOrg` fires the `set-default-org` POST (fire-and-forget; toast on failure) so
the backend's `is_default` follows the user's last choice — `checkSession`'s
default-resolution then restores the CHOSEN org on every reload (and across devices).
RED: vitest that switchOrg posts the endpoint; pytest already pins the backend
contract; an integration assertion that the default flips.

## 8. Task 8 (M-4 + L-6): transmission errors + the null-contact row

`transmission_service.py` reads `schema_errors` + `schematron_errors` (joined) with
the `errors` key as legacy fallback — the real validation detail reaches operators.
The suggest-matches frontend type accepts `contact: string | null` and renders a
fallback for null contacts. RED: pytest with a schema-load failure asserts the real
message (not "Unknown validation error"); vitest for the null-contact row.

## 9. Task 9 (M-6): bank-account edit + deactivate

The dialog ships an edit mode (prefill from the row, PATCH via `useUpdateBankAccount`,
the Task-5 serializer parity behind it) and the accounts tab rows gain Edit +
Deactivate (confirm; DELETE via `useDeactivateBankAccount`). RED-first vitest: edit
prefills and PATCHes; deactivate confirms and invalidates the list.

## 10. Task 10 (M-7): payment allocations visible

Payment rows gain a detail expansion (inline panel, not a route) consuming
`usePayment` — the allocations (document number + allocated amount) render per
payment. RED-first vitest: the panel renders allocations from the detail payload;
empty state for unallocated payments.

## 11. Task 11 (M-8): fiscal periods can be opened

- Backend: `POST fiscal-periods/{id}/open/` (manager-gated, symmetric to close:
  `is_open=True`, clears `locked_at/locked_by`, refuses an open period with a clean
  400, refuses when the parent year is closed). RED-first pytest (member 403, open →
  200, already-open → 400, closed-year → 400).
- Frontend: a Settings "Fiscal year & periods" card — years with their periods,
  status badges, Open/Close buttons (close exists backend-side; consume the fiscal
  endpoints — currently zero consumers). The approval error becomes actionable.

## 12. Task 12 (M-9): change password + the profile-card truth

A "Change password" card in Settings (current + new + confirm, zod, 8-char minimum;
POST via the existing api-client endpoint string; on success the backend expires the
session → the client clears state and routes to /login with a toast). The "Profile
editing is handled by your account settings" line is replaced with the real change-
password affordance (the lie dies). RED-first vitest: validation, payload, success
redirect, error surface.

## 13. Task 13 (M-10): InvoiceNow settings — the 400 gets its surface

A Settings "InvoiceNow / Peppol" card: GET renders
(enabled, participant_id, is_configured status, access_point_provider, auto_transmit,
retry_attempts); PATCH (manager-gated server-side) saves them through the typed
serializer. The invoice detail's InvoiceNow error now points at a real page. RED-first
vitest: card renders from GET, PATCH payload, non-manager sees read-only state.

## 14. Task 14 (M-11): the CI trigger — the gate actually gates

`on: push/pull_request: branches: [main]` (the corrupted `ain, develop]` fixed);
`cache-dependency-path` points at `apps/web/package-lock.json` (npm cache key). The
jobs themselves are sound (schema-init + pytest with per-run DB password; typecheck +
vitest + build:server). No workflow additions this sprint (e2e stays local by design).

## 15. Task 15 (M-12 + M-13 + L-7): build-mode truth + the coverage ratchet + Suspense

- **Static export retired truthfully**: `build`/`build:static`/`serve` are removed
  from package.json (the mode cannot support API-driven detail routes — `generateStaticParams`
  cannot enumerate live IDs; the scripts fail today, so removing them breaks nobody);
  `build:server`/`start` remain the only production path; DEPLOYMENT.md §9 rewritten
  accordingly; next.config.ts comments aligned. `NEXT_OUTPUT_MODE` stays honoured
  (`build:server` sets standalone explicitly).
- **Coverage ratchet**: vitest.config.ts thresholds move to the measured floor
  (lines/statements 64, functions 53, branches 49) — a real gate that FAILS on
  regression instead of a fictional 85% that never ran; the coverage debt (71k
  uncovered lines to the 85% bar) is registered with the ratchet as the mechanism to
  raise it over time.
- **Suspense hardening**: `BankingClient` (the `useSearchParams` consumer) is wrapped
  in a `<Suspense>` boundary at the page level so a prerender refactor cannot break
  `next build`.
- `npm run build:server` added to the local pre-push gate list in the docs.

## 16. Task 16 (L-1..L-5): the truth/UI batch

- Quote detail back links become variant-aware (`/quotes` in quote mode); the quote
  error card says "Failed to load quote".
- The doubly-dead "Load more" buttons are removed (the "Showing X of Y" line stays —
  truthful; pagination remains registered debt).
- `AllocationSection` gates its query on `contactId` (no org-wide fetch pre-pick).
- The import result renders the per-row errors (row number + message) instead of a
  count.
- Payment filters get `htmlFor`/id label pairing (the transaction-filters pattern).

## 17. Task 17 (live gate): e2e + screenshots + docs

Gated e2e coverage for the new surfaces (registration page renders + registers;
contacts list renders; the invoice form's picker selects an existing contact — the
H-1 regression at the wire level), the existing specs updated for changed pages.
Then screenshots `docs/screenshots/53..58_*_session20.png` (registration page,
contacts page, invoice form contact picker, GST F5 boxes view, settings change-
password/InvoiceNow cards, bank-account edit dialog — real UI login path,
content-based waits), `.env.example` cross-check (P10 adds no env vars — verify), docs
truth pass (README/PAD/CLAUDE/AGENTS/ledgersg_SKILL lessons + DEPLOYMENT rewrite),
`docs/REMEDIATION_2026-11-22_P10_REPORT.md`, `docs/session_21.md` (session-20 log per
the naming convention), `worklog.md` entry.

---

## 18. Verification Gate (definition of done for the sprint)

| # | Gate | Expected |
|---|---|---|
| 1 | `pytest --reuse-db --no-migrations -q` | all green (668 baseline + new, 0 failed) |
| 2 | `npm run typecheck` / `npm test` / eslint (touched) | clean / all green / parity |
| 3 | `npm run test:coverage` | green at the ratchet thresholds (the honest floor) |
| 4 | `npm run build:server` | green (the only build mode) |
| 5 | `npm run test:e2e` (no backend) | green, new specs gated with reasons |
| 6 | `npm run test:e2e:full` (live backend + Redis + bootstrapped dev DB, `--workers=1`) | all green incl. new specs |
| 7 | Permission spot checks | set-default-org honoured; fiscal-period open manager-gated (member 403); GST review manager-gated; peppol PATCH manager-gated (existing tests) |
| 8 | Contract spot checks | register 201 + cookies; invoice with picked contact sends NO createContact; bank PATCH null/"" paynow → 200 stored NULL; dangling pair → 400; transition_status VOID without user → 400; transmission schema-failure message real; review route live |
| 9 | Workflow spot checks | register → org-less → org creation → dashboard; picked contact invoiced twice → ONE contact row, invoice #2 succeeds; F5 boxes render before File; periods creatable; fiscal period openable; payment allocations visible; switchOrg persists across reload |
| 10 | Screenshots | ≥ 6 new non-empty unique PNGs (content-verified) |
| 11 | Docs sweep | no stale claims; DEPLOYMENT.md rewritten (standalone-only, current counts); `.env.example` matches the code |
| 12 | `git status` clean; commit set matches §19 | all on `main` |

## 19. Commit Plan (conventional commits, single branch `main`)

1. `feat(web): registration page — the self-serve loop closes (P10/H-2)`
2. `fix(web,invoicing): invoice form picks real contacts — no duplicate rows (P10/H-1)`
3. `feat(web): contacts management — list, edit, deactivate (P10/M-5)`
4. `feat(web,gst): the F5 tab tells the whole truth — boxes, periods, review/amend, deadlines (P10/H-3)`
5. `fix(banking): update-serializer PayNow parity — null/"" stored, dangling pair refused (P10/M-1)`
6. `fix(invoicing): the VOID seam fails closed — user_id required with a clean 400 (P10/M-2)`
7. `fix(web,api): the chosen org survives the refresh — set-default-org wired (P10/M-3)`
8. `fix(peppol,web): transmission errors read the real keys; null-contact rows render (P10/M-4, L-6)`
9. `feat(web): bank-account edit + deactivate (P10/M-6)`
10. `feat(web): payment allocations visible (P10/M-7)`
11. `feat(core,web): fiscal periods can be opened — endpoint + settings card (P10/M-8)`
12. `feat(web): change password + the profile-card truth (P10/M-9)`
13. `feat(web): InvoiceNow settings card (P10/M-10)`
14. `fix(ci): the trigger actually gates — branches [main] (P10/M-11)`
15. `chore(web): build-mode truth — export retired, coverage ratchet, Suspense (P10/M-12, M-13, L-7)`
16. `fix(web): truth/UI batch — quote back links, dead load-more, allocation gate, import rows, filter labels (P10/L-1..L-5)`
17. `test(web,e2e): P10 specs — register, contacts, picker regression (P10 live gate)`
18. `docs: P10 truth pass — README/PAD/CLAUDE/AGENTS/ledgersg_SKILL + DEPLOYMENT rewrite + .env.example`
19. `docs(worklog): session 20 worklog, session log, P10 report + screenshots`

(Adjacent tasks may fold where they share a RED→GREEN cycle; push incrementally after
each task — the workspace-reset safeguard.)

## 20. Deferred Debt Register (explicit, not silently dropped)

Carried forward unchanged from P9 §3 unless noted: H-02 base-currency reporting; M-1
audit-event coverage beyond banking (no READ surface); M-10 CSRF hardening
(SameSite=Lax mitigates; Origin-check is the S-sized follow-up); M-11 static-export
security headers/CSP (narrowed by Task 15 — standalone mode serves headers via
next.config `headers()`; verify in P11); H-07 backend ruff debt (918, improved from
1155); frontend eslint debt (76, parity; 36 `any`s); F5 GST return rate-basis; GST
payment tracking `pay_return` (needs gst schema extension); Reg-11 full PINT
Schematron; ledger pagination (Task 16 removes the dead buttons; real pagination
needs the B6 envelope decision); invoice edit flow `update_line`; B6 list-envelope
standardization; aged credit/debit-note netting; quote lifecycle vocabulary (DB
enum); trial-balance zero-activity accounts + fiscal-year mode (incl. the two TB
endpoints' internal inconsistency); reports export (CSV/PDF); TAX-group coarse type
(F-03 mechanism: an API-created TAX account vanishes from the BS while flipping the
balanced flag — needs a GROUP_TO_COARSE_TYPE.TAX decision); Storecove authenticate
semantics (M-14); dashboard computed trends (needs the period-comparison endpoint,
design with H-02); CoA management page (backend rich, zero UI — top candidate for
P11); manual journal-entry UI; Peppol transmission-log UI; bills (PURCHASE_INVOICE)
creation UI; payment-detail-full-surface (Task 10 ships the inline panel; a dedicated
route stays deferred); `use-dashboard.ts` dead file (delete-or-wire in P11); coverage
debt to the 85% bar (Task 15 ships the ratchet); L-8 credit-note transmission branch
(intended dead per the C-3 gate; revisit when credit-note transmission is designed).

New this sprint (registered, not dropped):
- **Password reset / forgot-password flow** — needs an email-delivery design decision
  (token table + mail transport); the dead link is removed truthfully in Task 1.
- **Contacts bulk import / merge** — Task 2/3 stop the bleeding (no new duplicates);
  merging EXISTING duplicate contacts needs a merge endpoint (data decision).
- **Registration email verification** — the backend registers without verification;
  an email-verification flow is a design decision (same transport as reset).

## 21. Open decisions resolved by this plan

- **H-2 scope:** ship the register page at `/register` (a new route, not the login
  page doubling as both — the login page links to it); registration remains org-less
  and lands on the P9 org-creation page (the backend's user-created-org design
  stands, as re-affirmed in P9 §21). "Forgot password?" is REMOVED rather than
  faked (no backend endpoint exists; truthful removal per the P9/D-2 precedent).
- **H-1 mechanism:** the UI picks existing contacts; new-contact creation becomes an
  explicit user act (toggle) — the backend contract stays as-is (UEN dedup is
  correct); no name-based backend dedup (false positives across genuinely distinct
  same-name customers outweigh the benefit; the picker search makes the existing row
  discoverable).
- **H-3 scope:** backend-first only where a route is missing (review); the boxes/
  periods/deadlines surfaces consume existing endpoints; Pay stays deferred (the
  fail-closed backend refusal is the correct posture until the schema decision).
- **M-8 semantics:** an explicit open endpoint (symmetric to close) rather than
  auto-opening periods on demand — period open/close is a control act a manager
  performs deliberately; the approval error names the periods, the card makes the
  act possible.
- **M-12 policy:** truthful removal of the export scripts (they fail today — removal
  breaks nobody) over adding fake `generateStaticParams` (which would 404 detail
  pages on a CDN silently). Standalone is the only supported production mode.
- **M-13 policy:** the ratchet at the measured floor (a real gate that fails on
  regression) over either weakening silently or shipping a sprint-sized effort at an
  85% bar that was never real. The debt is registered with the ratchet as the
  raising mechanism.
- **M-2 semantics:** fail-closed 400 over threading a user-less path — `posted_by`
  is NOT NULL by schema; a void without an accountable poster must not post a
  reversing entry, it must refuse.
