# LedgerSG — Remediation Plan (P9 Sprint: Onboarding & Banking Truth — Org Creation, Real Payment Workflow, P8-Diff Regression Closure)

- **Date:** 2026-11-22
- **Branch:** `main` only (per repo convention)
- **Inputs:** post-P8 audit of the `8bb9ebee` state (HEAD `b6bdfb40` = the session-log doc commit). Findings gathered with the repo skills per `skills/skills-catalog.md` (scanner pass + `code-review-and-audit` discipline) plus three deep review passes (P8-diff regression audit, deferred-register validation, fresh-surfaces gap audit — banking/contacts/dashboard/navigation/api-map). Every Critical/High finding below was re-verified against the working tree with line numbers by the lead before this plan was written. Scanner criticals outside `apps/` fall in the documented false-positive classes (docstring examples like `api_key="your-api-key"` — the single production hit this pass, registered M-14).
- **Method:** TDD (RED → GREEN → full gate), lint parity on touched files, conventional commits, `skills/` excluded from all checks/tests/compilation.
- **Baselines reproduced before any change (this session, exact):** backend **647 passed / 0 failed / 5 skipped**, vitest **418/418**, typecheck **0 errors**, e2e default **9 passed + 14 gated skips** — the documented P8 state. (Environment incident at session start, recovered: the dev DB had been wiped to a 2-table stub since P8 — schema reloaded from `database_schema.sql` per the documented recovery; 32 tables / 47 NUMERIC(19,4) verified before the baseline run.)

---

## 0. Audit Summary (the register this plan is built on)

P8 closed the reporting/quotes truth gaps. The post-P8 audit has three heads: **(a) the
P8 sprint's own loose ends** (a broken quote-conversion envelope, an un-gated InvoiceNow
path P8's Convert flow made reachable), **(b) the registered deferred items that GREW
into live bugs** (the account_type seed gap now blanks the invoice form's account
dropdown on every fresh org), and **(c) the never-remediated banking frontend** — built
pre-P1, never touched by a sprint, with three contract breaks its mock-based tests
could not see — plus the **onboarding dead end**: a self-registered user cannot create
an organisation at all.

| ID | Severity | Location | Finding (Verified) |
|---|---|---|---|
| O-1 | **Critical** (product dead end) | `dashboard-client.tsx:91-96`; `core/views/auth.py:31-61`; `core/urls/organisation.py` | Registration creates a user + tokens but **no organisation**; the dashboard empty state's only CTA links to `/settings/organisations/new` — **a route that does not exist** (settings tree: page/loading/client only). `POST /api/v1/organisations/` is real (`OrganisationListCreateView`, `IsAuthenticated`) with **zero frontend consumers** (grep-verified). A new self-serve user hits a 404 and cannot proceed; the product is unusable without curl. |
| B-1 | **High** (core flow always fails) | `use-banking.ts:433-446`; `api-client.ts:265-269` | Statement import builds `FormData` then posts it through the JSON helper — `JSON.stringify(FormData)` → `"{}"` with `Content-Type: application/json`; backend `request.FILES.get("file")` is always empty → guaranteed 400. **No bank transaction can enter the app through the UI.** |
| B-2 | **High** (wired but wrong, both directions) | `banking/views.py:619` + `reconciliation_service.py:410-419` vs `use-banking.ts:545-560` | Suggest-matches returns `{results, count}` with `payment_id/payment_number/amount/contact/score`; the hook types a **bare array** with `contact_name/match_score`. `{results…}.length` is `undefined` → the Reconcile form always renders "No matching payments found" even when matches exist; the field names would render blank/`undefined%` even if the envelope were fixed. **Reconciliation is impossible through the UI** (match selection is the only way to pick a payment). |
| B-3 | **High** (unusable primary workflow) | `receive-payment-form.tsx:133-147`; `payment.ts:67`; `invoice-detail-client.tsx` | The Receive Payment "Customer" field is a **raw text input bound to `contact_id`**, UUID-validated — with no contact picker and no contacts page, a user cannot obtain a UUID. The form never sends `allocations` (backend accepts them inline: `PaymentAllocationInputSerializer {document_id, allocated_amount}`), `useAllocatePayment` has zero consumers, and the invoice detail page has **no Record Payment action** — so invoices can never reach PAID through the UI. |
| B-4 | **High** (dead buttons) | `banking-client.tsx:161-164,177-184` | "Add Bank Account"/"Add Account" buttons have **no onClick**; no form exists. `useCreateBankAccount`/`useUpdateBankAccount`/`useDeactivateBankAccount` are real and unconsumed. A new org cannot add a bank account through the UI — gating the whole payments surface. |
| B-5 | **High** (dead button) | `banking-client.tsx:240,304-311` | "Make Payment" sets `showMakeForm` state that **nothing reads** (grep: one occurrence). `useMakePayment` + `POST /payments/make/` (with allocations) are real and unconsumed — payables can never be recorded, so aged payables can never be populated by UI action. |
| B-6 | Medium (one-way workflows) | `transaction-row.tsx:171-184`; `payment-list.tsx:104-114` | Unreconcile has no UI (`useUnreconcileTransaction` unconsumed); no payment detail/void surface (`useVoidPayment`, `useAllocatePayment` unconsumed; `setSelectedPaymentId` never rendered). Mis-keys and mis-reconciliations are uncorrectable through the UI. |
| B-7 | **High** (live 500, the P7 fix itself broken) | `banking/views.py:33,609` | The file imports `ValidationError as AppValidationError`, but the tolerance branch raises **bare `ValidationError`** → `NameError` at runtime: `GET …/bank-transactions/{id}/suggest-matches/?tolerance=abc` → 500 instead of the P7-intended 400. No test covers the malformed path (ruff F821-class miss; the parity rule failed here). |
| C-1 | **High** (P8 regression, flagship flow) | `use-invoices.ts:407-438` vs `invoicing/views.py:399-425` | The convert endpoint returns `{"message", "invoice": {…}}` (nested); the hook types and reads the response **flat** (`response.id`, `response.document_number`) → every conversion toasts "Invoice undefined created…" and routes to `/invoices/undefined`. Data is fine (the link persists); the UX is broken on both convert surfaces, every time. Nothing catches it: vitest mocks the hook, backend tests never hit the endpoint envelope. |
| C-2 | **High** (truth violation on a financial list) | `invoices-client.tsx:58` | The invoices list calls `useInvoices(orgId)` with **no type filter** (backend filters only when given) — quotes and bills render in "Invoices / Manage your sales invoices", and a quote row opens at `/invoices/{id}` labelled INVOICE with a fabricated "Amount Due" (the shared detail client defaults to `variant="invoice"`). |
| C-3 | **High** (wrong document over the wire) | `document_service.py:876-886`; `invoicing/views.py:616-617` | `send_invoicenow` checks only `status == "APPROVED"` — **no document_type gate** — and the view's permission is `IsOrgMember` only (looser than every sibling mutation). P8's Convert flow mass-produces APPROVED quotes, and the transmission path maps anything non-credit-note to **UBL Invoice** — so any org member can POST an APPROVED quote and a quotation goes out as a tax invoice into the recipient's AP pipeline. The web UI gates quotes out; the API does not. |
| C-4 | **High** (grew-worse deferred debt) | `database_schema.sql:587,2800-2893`; `coa/services.py:74-75`; `use-accounts.ts:48-50` | The seed populates only `account_type_id` (FK) — the `account_type VARCHAR(50)` column the API filter reads is **NULL on every seeded account**. `useRevenueAccounts` sends `?account_type=REVENUE` → on a fresh org the New Invoice / New Quote **posting-account dropdown is empty** (corroborated by the P8 live smoke, which had to create account 4100 before invoicing). API-created accounts work (`create_account` sets both) — the seeded ones don't. |
| C-5 | Medium (lying API field) | `invoicing/serializers.py:163-166` | `get_status_history` returns `[]` behind a TODO — the timestamps to synthesize a real history (created_at→DRAFT, approved_at→APPROVED, voided_at→VOID) exist on the model. |
| C-6 | Medium (badge conflation) | `quotes-client.tsx:139-143` | Any APPROVED quote renders "CONVERTED" — but a quote approved directly via the generic status endpoint (legal: quotes post no JE) shows CONVERTED with no linked invoice and loses its Convert button. The badge should gate on `related_document_id`. |
| D-1 | Medium (historical reports wrong) | `reporting/services/aged_service.py:50-66` | The aged queryset has **no date bound** — a document issued 2025-06 appears in an `as_at=2024-12-31` report (bucketed "current"); status/amount_paid are current-state too. The reports page exposes the As-at picker, so any historical date yields a materially wrong statement. |
| D-2 | Medium (fake compliance data) | `gst-f5-chart.tsx:39-52`; `gst-chart-wrapper.tsx:25` | The dashboard GST F5 chart hardcodes Box 1 (150,000), Box 2 (25,000) and defaults output/input tax (15,000/2,550) — only Box 8 (Net GST) is real. Invented figures on a compliance-facing chart. |
| D-3 | Medium (fake analytics) | `dashboard-client.tsx:210-213,271-275,290-294,355-358` | "+8.2%", "-2.4%", "+12.5%", "On track for target" are static JSX — no data feeds them. Users are told their cash fell and revenue grew regardless of the books. |
| D-4 | Medium (dead links) | `dashboard-client.tsx:172-177,222-228` | Compliance-alert action and "File F5" links point at `href="#"` while a real GST F5 tab exists at `/reports`. |
| S-1 | Medium (500 on bad params — the sweep's last sibling) | `invoicing/views.py:154-155` → `document_service.py:119-124` | `date_from`/`date_to` pass raw strings into `issue_date__gte/lte` filters — garbage raises Django's ValidationError at SQL-compile → 500 (the exact class P7/F-11 and P8/G-2 eliminated elsewhere; the invoicing sibling was missed). |
| S-2 | Medium (forced logout on transient failures) | `auth-provider.tsx:119-133` | `checkSession`'s catch treats network `TypeError` and 500s identically to a 401: `clearAuth()` + redirect. A transient outage on page load bounces a logged-in user (P8 gave `refreshOrganisations` the correct transport-vs-auth split; `checkSession` didn't get it). |
| S-3 | Medium (validation fails open) | `peppol/services/xml_validation_service.py:74-77` | `_validate_xsd` returns `[]` when the schema fails to load — a startup/load failure validates **everything**. The Peppol path's posture inverts to fail-open exactly when it matters. |
| S-4 | Low (actively misleading file) | root `requirements.txt` | A pip-freeze of the sandbox global env (torch, PyQt5, streamlit, editable ssh installs) that **contradicts the backend pins** (`Django==6.0.3` vs backend `6.0.2`; `django-celery-beat==2.8.1` vs `2.9.0`). `pip install -r requirements.txt` silently downgrades a contributor's venv. |
| K-1 | Low (contradictory dead branch) | `document_service.py:430-436` | `transition_status` still carries a VOID branch that bypasses the P8 allocation guard + reason contract (no view reaches it; tests do). Dead code whose semantics now contradict the engine. |
| K-2/K-3/K-4 | Low | `use-invoices.ts:268-274,426`; `document_service.py:671-686` | Stale `message?: string` in the send payload type (field removed in P8); dead `"invoice"` (singular) invalidation key; stale `void_document` docstring (pre-P8 accepted set). |
| K-5 | Low (latent, rides Task 10) | `use-contacts.ts:49-54` vs `invoicing/views.py:57-60` | `useContacts` sends `contact_type` — the backend reads `is_customer/is_supplier/search`. Harmless today (no consumer passes filters); the Task 10 picker becomes the first real consumer, so the keys must be fixed with it. |

Verified-clean (explicit): GST re-gate holds (P8/G-1); aged endpoint permissions + bucket math;
retained-earnings tie-out; route rename has no stale consumers; void state machine uniform on
both endpoints; cc/bcc chain; blob envelope; GROUP_TO_COARSE_TYPE completeness; core-dashboard
deletion leaves zero importers; fiscal-close precondition; settings round-trip; sidebar nav has
zero 404s; **every api-client endpoint string resolves to a real backend route** (the P5-era
mismatches are gone — the breaks this sprint are all response-side, not URL-side).

---

## 1. Task 1 (C-3): InvoiceNow transmits invoices only

Backend-first, worst failure mode. RED (pytest): an APPROVED SALES_QUOTE POSTed to
`/documents/{id}/send-invoicenow/` → 400 naming the document type (the task-queue mock
per the existing peppol test pattern); an org member whose role lacks `can_create_invoices`
→ 403 (permission parity with `QuoteConvertView`). GREEN: `send_invoicenow` refuses
`document_type != SALES_INVOICE`; `InvoiceSendInvoiceNowView` gains `CanCreateInvoices`.

## 2. Task 2 (B-7 + S-1 + S-4): hardening riders

RED: `?tolerance=abc` → 400 (currently 500 NameError); `?date_from=x` on the documents
list → 400 (currently 500). GREEN: raise `AppValidationError` in the tolerance branch;
`parse_date_param` for `date_from`/`date_to` in `InvoiceDocumentListCreateView.get` (the
journal-view pattern); two new CASES rows in `test_query_params_p7.py`. Root
`requirements.txt` replaced with a 3-line pointer to `apps/backend/pyproject.toml`.

## 3. Task 3 (C-1 + K-3): the convert envelope, pinned end to end

RED (backend): endpoint-level test asserting the POST `/quotes/convert/` response body
`{message, invoice:{id, document_number, …}}` — the contract the frontend consumes
(no test currently pins it). GREEN (frontend): `useConvertQuote` unwraps `.invoice`
before returning; the dead `"invoice"` invalidation key removed; vitest for the unwrap
(mock the api layer at the seam, assert `router.push` gets the real id).

## 4. Task 4 (C-2): the invoices list shows invoices

`invoices-client.tsx` calls `useInvoices(orgId, { type: "SALES_INVOICE" })`; a
document-type badge renders on the row (defensive: any type that leaks is labelled,
not silently shown as an invoice). Vitest: the hook receives the filter; the badge
branch renders for non-invoice types.

## 5. Task 5 (C-4): seeded accounts join the filtered lists

RED (pytest): after the org seed, `list_accounts(account_type="REVENUE")` returns the
4000-series rows (currently empty). GREEN: the seed function backfills the
`account_type` varchar from `account_type` codes (one UPDATE after the group inserts);
the list filter matches `account_type` OR `account_type_ref__code` (defense-in-depth for
orgs created before the backfill — no schema change; the varchar already exists).
Schema-file edit + conformance gate re-run.

## 6. Task 6 (B-1): statement import sends real multipart

RED (vitest): the import mutation issues a fetch with a `FormData` body and **no**
JSON content-type. GREEN: `api.postForm` helper (no stringifying, no JSON header) in
api-client; `useImportTransactions` uses it; blob/JSON error paths unchanged.

## 7. Task 7 (B-2): reconciliation matches render

RED (vitest): `useSuggestMatches` returns the row array from a `{results, count}`
envelope and maps `contact`→`contact_name`, `score`→`match_score`; the reconcile form
renders a match row for a realistic backend payload (currently mocked as a bare array —
the test flips to the REAL backend shape). GREEN: hook unwrap + mapping; form unchanged
(its per-row rendering was correct all along).

## 8. Task 8 (O-1): organisation creation — the dead end closed

New page `/settings/organisations/new` (the route the dashboard CTA already targets):
form (name, legal_name, UEN, entity_type select, GST toggle + reg number) →
`api-client` `organisations.create` → `useCreateOrganisation` → success:
`refreshOrganisations()` + select the new org + navigate to the dashboard with a toast.
RED-first vitest (form validation, payload shape, success path). The dashboard CTA now
lands on a real page; registration remains org-less (creating the org is an explicit
user action — matches the backend design where orgs are user-created).

## 9. Task 9 (B-4): bank account management is real

Dialog form wired to the dead buttons: fields per `BankAccountCreateSerializer`
(account_name, bank_name, account_number, currency, gl_account select from
bank-type accounts, paynow_type/paynow_id conditional) → `useCreateBankAccount`.
Vitest: dialog opens from both buttons, payload shape, error surface. Edit/deactivate
remain API-only (registered — the create unblocks the workflow).

## 10. Task 10 (B-3 + B-5 + K-5): payments pick real contacts; Make Payment exists

- `useContacts` filter keys fixed (`is_customer`/`is_supplier`/`search` — the backend
  contract; K-5) with a debounced search combobox component (shared).
- Receive Payment: the raw UUID input becomes the customer combobox.
- Make Payment: the dead button gets its form — the mirror of receive (supplier
  combobox, bank account, method, amount, date, reference) via `useMakePayment`.
- Vitest: combobox searches and selects; both forms' payloads.

## 11. Task 11 (B-3b): allocations — payments settle invoices

- Both payment forms gain an "Open invoices" section for the chosen contact
  (`useInvoices` with `contact_id` + outstanding statuses) with per-invoice allocation
  amounts; the create payload carries `allocations: [{document_id, allocated_amount}]`
  (the backend's inline contract, verified in the serializer).
- Invoice detail gains a "Record Payment" action (status-gated to outstanding states)
  deep-linking to Banking → Receive Payment prefilled (contact, invoice, amount due)
  via query params; the banking page reads them.
- Vitest: allocation rows render for open invoices; payload includes allocations;
  prefill path populates the form.

## 12. Task 12 (B-6): correction paths — void + unreconcile

Payment rows gain a Void action (confirm dialog → `useVoidPayment` — the P5
void-with-reversal engine finally has a consumer); transaction rows gain Unreconcile
(`useUnreconcileTransaction`) for reconciled rows. Vitest for both actions' gating.

## 13. Task 13 (D-1): the aged report honours its as-at date

RED (pytest): a document issued after `as_at` is excluded from the aged report.
GREEN: `.filter(issue_date__lte=as_at)` in the aged queryset (status/amount_paid stay
current-state — documented; the issue-date bound removes the impossible history).

## 14. Task 14 (D-2 + D-3 + D-4): the dashboard tells the truth

- GST F5 chart: drop the invented Box 1/Box 2 bars and the hardcoded output/input
  defaults; render the real boxes available from the metrics payload (Box 8 net GST
  stays; if the dashboard endpoint carries output/input tax they render, else the
  chart shows only what is real).
- Trend rows: remove the static "+8.2%/-2.4%/+12.5%/On track" JSX (truthful removal —
  computed deltas are a registered follow-up needing a period-comparison endpoint).
- Dead links: `href="#"` → `/reports` (GST tab) and the real settings route.
- Vitest updates; screenshot re-capture in the live phase.

## 15. Task 15 (C-5 + C-6 + K-1/K-2/K-4): truth batch

- `get_status_history` synthesizes `[{status, at}]` from the model timestamps
  (created_at→DRAFT, approved_at→APPROVED, voided_at→VOID; SENT/PAID have no dedicated
  timestamps — documented in the serializer docstring). Pytest pins the shape.
- The CONVERTED badge gates on `related_document_id` (exposed by the list serializer);
  an approved-but-unconverted quote shows APPROVED and keeps its Convert button.
- The `transition_status` VOID branch delegates to `void_document` (one engine, one
  contract); stale `message?: string` type and `void_document` docstring fixed.

## 16. Task 16 (S-2 + S-3): session + Peppol posture

- `checkSession`: transport failures (non-ApiError, or ApiError ≥500) keep the session
  and surface a retryable error state; only 401/403 clear + redirect (the
  `refreshOrganisations` pattern from P8). Vitest for both branches.
- `_validate_xsd` fails CLOSED: schema-load failure returns an error entry (never an
  empty list). Pytest with a bad schema path.

## 17. Task 17 (live gate): banking e2e spec + screenshots + docs

Gated `e2e/banking.spec.ts` (E2E_API_URL): import statement → suggest-matches renders a
row → reconcile; receive payment (picked contact + allocation) → the invoice shows
PAID. Runs in `e2e:full` with the bootstrapped dev DB. Then screenshots
`docs/screenshots/47..52_*_session18.png` (org creation, bank account dialog, receive
payment with contact picker + allocations, reconciled transactions, truthful dashboard,
invoices list with type badges — real UI login path, content-based waits),
`.env.example` cross-check, docs truth pass (README/PAD/CLAUDE/AGENTS/ledgersg_SKILL
lessons + DEPLOYMENT.md verification), `docs/REMEDIATION_2026-11-22_P9_REPORT.md`,
`docs/session_19.md` (session-18 log per the naming convention), `worklog.md` entry.

---

## 18. Verification Gate (definition of done for the sprint)

| # | Gate | Expected |
|---|---|---|
| 1 | `pytest --reuse-db --no-migrations -q` | all green (647 baseline + new, 0 failed) |
| 2 | `npm run typecheck` / `npm test` / eslint (touched) | clean / all green / parity |
| 3 | `npm run test:e2e` (no backend) | green, new banking spec gated with reason |
| 4 | `npm run test:e2e:full` (live backend + Redis + bootstrapped dev DB) | all green incl. the banking workflow spec |
| 5 | Permission spot checks | InvoiceNow without `can_create_invoices` → 403; quote → 400 |
| 6 | Contract spot checks | `?tolerance=abc` → 400; `?date_from=x` → 400; convert response carries nested `invoice`; fresh-org REVENUE account list non-empty; aged `as_at` excludes later-issued docs |
| 7 | Workflow spot checks | org created through the UI is selectable; bank account created through the dialog appears in the receive form; a received payment with an allocation drives an invoice to PARTIALLY_PAID/PAID |
| 8 | Screenshots | ≥ 6 new non-empty unique PNGs (content-verified, 2 VLM-checked) |
| 9 | Docs sweep | no stale claims; DEPLOYMENT.md verified; `.env.example` matches the code |
| 10 | `git status` clean; commit set matches §19 | all on `main` |

## 19. Commit Plan (conventional commits, single branch `main`)

1. `fix(invoicing): InvoiceNow transmits invoices only; view permission aligned (P9/C-3)`
2. `fix(banking,invoicing): tolerance + document-date params are 400s; root requirements.txt retired (P9/B-7, S-1, S-4)`
3. `fix(invoicing,web): quote conversion envelope pinned and read; dead key gone (P9/C-1)`
4. `fix(web): invoices list shows invoices — type filter + document-type badge (P9/C-2)`
5. `fix(coa): seeded accounts carry account_type; filter matches either column (P9/C-4)`
6. `fix(web,api): statement import sends real multipart — postForm helper (P9/B-1)`
7. `fix(web): reconciliation matches render — envelope + field mapping (P9/B-2)`
8. `feat(web): organisation creation — the onboarding dead end closed (P9/O-1)`
9. `feat(web): bank account management dialog (P9/B-4)`
10. `feat(web): payment forms pick real contacts; Make Payment exists (P9/B-3, B-5, K-5)`
11. `feat(web): payment allocations + Record Payment from the invoice (P9/B-3b)`
12. `feat(web): payment void + transaction unreconcile actions (P9/B-6)`
13. `fix(reporting): the aged report honours its as-at date (P9/D-1)`
14. `fix(web): dashboard truth — real GST boxes, no invented trends, live links (P9/D-2, D-3, D-4)`
15. `fix(invoicing,web): status_history synthesised; CONVERTED badge truthful; state-machine housekeeping (P9/C-5, C-6, K-1..K-4)`
16. `fix(web,peppol): session survives transport faults; XSD validation fails closed (P9/S-2, S-3)`
17. `test(web,e2e): banking workflow spec — import/match/reconcile + receive/allocate/paid (P9 live gate)`
18. `docs: P9 truth pass — README/PAD/CLAUDE/AGENTS/ledgersg_SKILL + DEPLOYMENT verification + .env.example`
19. `docs(worklog): session 18 worklog, session log, P9 report + screenshots`

(Adjacent tasks may fold where they share a RED→GREEN cycle; push incrementally after
each task — the workspace-reset safeguard.)

## 20. Deferred Debt Register (explicit, not silently dropped)

Carried forward unchanged from P8 §18 unless noted: H-02 base-currency reporting; M-1
audit-event coverage beyond banking (audit-log READ surface joins it — L-4: no HTTP
endpoint exposes `audit.event_log` at all); M-10 CSRF hardening (SameSite=Lax mitigates;
Origin-check is the S-sized follow-up); M-11 static-export security headers/CSP; H-07
backend ruff debt (1155 errors — the parity rule failed once, see B-7; keep the policy);
frontend eslint debt (74 problems, 36 `any`s); F5 GST return rate-basis (fold into the
H-02 design note); GST payment tracking `pay_return` (needs gst schema extension);
Reg-11 Schematron (the XSD fail-closed half ships in Task 16; full PINT Schematron
wiring follows); `status_history` SENT/PAID timestamps (needs the quote-vocabulary
decision); ledger pagination; invoice edit flow `update_line` (the registered L-item —
still absent, verified); checkSession retry-once refinement (Task 16 ships the
transport/auth split); B6 list-envelope standardization (three shapes coexist — churn
until pagination forces it); aged credit/debit-note netting; quote lifecycle vocabulary
(DB enum); trial-balance zero-activity accounts + fiscal-year mode; reports export
(CSV/PDF); TAX-group coarse type (F-7: an API-created TAX account breaks the BS tie-out
silently); Storecove authenticate semantics (M-14); transmission `errors`-vs-
`schema_errors` key (message polish).

New this sprint (registered, not dropped):
- **Contacts management pages** (list/create/edit/deactivate) — Task 10 ships the
  picker (the duplication + UUID problems); full pages are the follow-up.
- **Chart of accounts page** — backend ready (list/create/hierarchy/balance), zero UI.
- **Bank account edit/deactivate UI** — Task 9 ships create (the workflow unblock);
  edit/deactivate remain API-only.
- **Payment detail surface** — Task 12 ships row actions (void/unreconcile); a full
  detail view with allocation management stays thin-until-needed.
- **GST review/pay/amend UI + deadlines** — the F5 tab ships compute/file (P8); the
  remaining lifecycle buttons are S-sized follow-ups (pay needs the schema decision).
- **Bills (PURCHASE_INVOICE) creation UI + fiscal-year/period management UI + Peppol
  transmission-log UI + manual journal-entry UI + set-default-org persistence** — all
  backend-real, frontend-absent (fresh-surfaces audit L-items).
- **Dashboard computed trends** — Task 14 removes the lies; real deltas need a
  period-comparison endpoint (design with H-02).

## 21. Open decisions resolved by this plan

- **O-1 scope:** ship the create-org PAGE at the route the dashboard already targets
  (`/settings/organisations/new`) rather than auto-creating an org at registration —
  org creation is an explicit, name-bearing act; the backend's user-created design
  stands. The dead link is closed by making it live, not by re-pointing it.
- **C-3 semantics:** refuse non-invoice types with a 400 naming the type (fail-closed),
  and align the view permission with `QuoteConvertView` (`CanCreateInvoices`) — the
  send-invoicenow action is an invoice-creating transmission, and member-wide access
  was looser than every sibling mutation view.
- **C-4 mechanism:** backfill the varchar in the seed + dual-column filter match — no
  schema change (the column exists); orgs created before the backfill are covered by
  the filter fallback; the schema file remains the source of truth.
- **B-2 direction:** the frontend adapts to the backend's `{results, count}` envelope
  (the codebase convention — 9 endpoints use it; the backend is not special-cased to
  the one hook).
- **D-2/D-3 policy:** truthful removal over invented data — the fake bars/trends are
  deleted, not backfilled with guesses; computed analytics register as the follow-up.
- **D-1 semantics:** bound by `issue_date__lte=as_at` now (removes the impossible
  history); as-of status/amount_paid semantics are registered debt (needs the same
  allocation-model decision as netting).
- **C-5 scope:** backend-first synthesis from existing timestamps; the UI timeline is a
  follow-up (the field stops lying first).
- **B-3b allocation UX:** inline allocations in the payment forms (the backend's
  existing contract) + a prefilled deep link from the invoice — no new backend
  surface; a dedicated payment-detail allocation editor stays deferred.
