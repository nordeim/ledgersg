# LedgerSG — Remediation Report (P9 Sprint: Onboarding & Banking Truth)

**Date:** 2026-11-22 (session 18)
**Base commit:** `b6bdfb40` (main)
**Plan:** `docs/REMEDIATION_PLAN_2026-11-22_P9.md`
**Source audit:** post-P8 audit re-verified in source with line numbers before
planning (three deep review passes — a P8-diff regression audit, a
deferred-register validation, a fresh-surfaces gap audit — plus the repo-skill
scanner pass per `skills/skills-catalog.md`); every Critical/High finding
re-confirmed against the working tree before execution, then re-verified by
the live e2e phase (three iterations, each surfacing defects the unit gates
structurally could not see).
**Method:** TDD (RED → GREEN → full gate). Every production-code fix has a
regression test that failed for the documented reason before the fix and passes
after: **21 new backend tests + 36 new vitest tests + 3 new e2e specs, all RED
first.**

---

## 1. Verification Ledger (executed evidence)

Environment: rootless PostgreSQL 17 on :5432 (schema v1.1.0), Redis 8 on :6379,
Python 3.12 venv, Node with `@playwright/test` 1.58.2 + chromium, Django dev
server (development settings) on :8000 + Next dev on :3000 during the live
phase. Session-start incident (recovered, zero work lost): the dev DB had been
wiped to a 2-table stub since P8 — schema reloaded from `database_schema.sql`
(32 tables / 47 NUMERIC(19,4) verified) before the baseline run. A second
drop-and-reload preceded the canonical live phase so the e2e chain and the
screenshots ran against a freshly bootstrapped org.

| # | Check | Command | Result |
|---|---|---|---|
| 1 | Baseline (pre-remediation, session start) | `pytest --reuse-db --no-migrations -q` | **647 passed, 0 failed, 5 skipped** at base `b6bdfb40` — the documented P8 state reproduced exactly before any change |
| 2 | Baseline (frontend) | `npm test` / `npm run typecheck` / `npm run test:e2e` | 418/418, 0 errors, 9 passed + 14 gated skips — documented state reproduced |
| 3 | RED captures (all tasks) | per-task RED runs | InvoiceNow gate 2 (quote 500-to-400 path, member 403), query-params 4 (NameError 500 + garbage dates 500), convert envelope 1 (flat-read `/invoices/undefined`), seeded account_type 3 + is_bank 1 (empty dropdowns on fresh orgs), list amounts 1, multipart 2 (`postForm` not a function / FormData through the JSON helper), suggest-matches 1 (bare-array type vs `{results,count}` envelope), org page 5 (route did not exist), dialog 3, picker 4 + make-form 2, allocations 5, prefill 1, void rows 2, unreconcile 2, aged as-at 1 (post-as-at document included), dashboard 4 (invented figures present), status_history 3, XSD fail-closed 1 (None schema validated silently), checkSession 1 (network fault redirected), null-PayNow 1 (the dialog's real payload 400'd) — all failed for the documented reasons pre-fix |
| 4 | Full backend suite (post-remediation) | `pytest --reuse-db --no-migrations -q` | **0 failed, 668 passed, 5 skipped** (647 + 21 new) |
| 5 | Invariant / security gates | `pytest tests/invariants -q` / `pytest tests/security -q` | **27 passed** / **53 passed, 3 skipped** (unchanged — no posture regressions) |
| 6 | Ruff (touched backend files) | before/after per file set | parity on every touched legacy file; all new files clean |
| 7 | Frontend unit suite | `npm test` | **454 passed (454)** — 418 + 36 new |
| 8 | Frontend typecheck | `npm run typecheck` | **0 errors** |
| 9 | Frontend eslint (touched files) | `npx eslint <touched>` | new files 0E/0W; parity on pre-existing findings |
| 10 | e2e (default, backend-less) | `npm run test:e2e` | **9 passed + 17 gated skips with reasons** (14 previous + the new banking workflow spec) |
| 11 | e2e (full, live backend + Redis + bootstrapped dev DB) | `E2E_API_URL=… npm run test:e2e:full` | **26/26 passed** (serial workers; the banking chain: dialog → Record Payment deep link + picker + allocation → multipart import → rendered 100% match → reconcile → invoice Paid). Three iterations were required; each failure was root-caused to a real defect (see §2's live-gate items), never suppressed |
| 12 | Live workflow spot checks (DB) | psql after the live run | the payment row (RCP-00001, 2,616.0000) with its allocation; the imported transaction (CSV, E2E-REF-001) reconciled; the settled invoice PAID; the bank account created through the dialog |
| 13 | Authorization spot checks | new integration tests | InvoiceNow without `can_create_invoices` → **403** (was 200 — the view was `IsOrgMember`-only); an APPROVED quote → 400 naming the type (was a live transmission path) |
| 14 | Contract spot checks | new integration tests | `?tolerance=abc` → 400 (was a NameError 500); `?date_from=x` → 400 (was a filter 500); convert response nests `invoice` (pinned); fresh-org `?account_type=REVENUE` non-empty; `?is_bank=true` returns the seeded 1100 series; aged `as_at` excludes later-issued docs; bank-account POST with `paynow_type: null` → 201 (was 400) |
| 15 | Workflow spot checks (live UI) | the banking e2e spec | the contact picker selects "Marina Consulting Group Pte Ltd" by name (never a UUID); the allocation row prefills from the deep link and settles INV-00003 to Paid; the imported transaction renders a 100% match row and reconciles |
| 16 | UI truth spot checks | vitest + VLM-verified screenshots | the dashboard renders only real figures (no Box 1/2 bars, no static trends); the org-creation page renders the form the dead CTA targeted; the receive form shows the customer chip + allocation rows; the transactions tab shows the Reconciled badge + 100% reconciliation rate |
| 17 | Screenshots | `docs/screenshots/47..52_*_session18.png` | 6 unique PNGs (md5-distinct, 52–78KB, 1440×900) — organisation creation, bank account dialog, receive payment with contact picker + allocations, reconciled transactions (**VLM-verified: the "Payment received - Marina Consulting" row, +S$ 2,616.00, Reconciled badge, Reconciliation Rate 100%**), truthful dashboard, invoices list — captured through the real UI login path with content-based waits |
| 18 | Docs truth sweep | greps across README/PAD/CLAUDE/AGENTS/ledgersg_SKILL/DEPLOYMENT | counts match the executed evidence (1,148 = 668 + 454 + 26); DEPLOYMENT.md re-verified + P9 spot checks in the §11 checklist; lessons 31–35 appended to the skill; P9 patterns in AGENTS.md |
| 19 | `.env.example` verification | per-var cross-check | both templates cover every `config()` read; P9 adds no env vars (all behavior is code + Django settings); the retired root `requirements.txt` is replaced by a pointer to the single manifest |

Confidence labels: all rows **Verified** (executed in this environment). The
live phase's three iterations are recorded as findings-and-fixes in §2, not as
retries of flake.

---

## 2. What Was Fixed

### Organisation creation — the onboarding dead end (O-1, Critical)
Registration creates a user with **no organisation**, and the dashboard's only
CTA linked to `/settings/organisations/new` — **a route that did not exist** —
while `POST /api/v1/organisations/` (which seeds the chart, fiscal year, roles,
and tax codes) had zero frontend consumers. A self-serve user hit a 404 and
could not use the product. The page ships at the route the CTA already targets:
name/legal name/UEN/entity type/GST toggle (the backend's GST-number validation
mirrored client-side); success refreshes the org list, selects the new org,
and lands on the dashboard.

### The payment workflow is real end to end (B-1, B-2, B-3, B-3b, B-5)
The P5/P6 payment engine was real but unreachable: **no bank transaction could
enter the app** (the import posted `FormData` through the JSON helper —
`JSON.stringify(FormData)` sent `"{}"` with a JSON content-type, so
`request.FILES` was always empty); **reconciliation was impossible** (the
suggest-matches hook typed a bare array while the backend returns
`{results, count}` with `contact`/`score` fields — the envelope has no
`.length`, so the form always rendered "No matching payments found"); **a
payment could not select a customer** (the Customer field was a raw text input
bound to `contact_id`, UUID-validated, with no contacts page anywhere); **no
allocation UI existed** (the backend accepted inline allocations since P5 —
nothing ever sent them, so invoices could never reach PAID through the app);
and the Make Payment button set state that nothing read. Now: `api.postForm`
sends true multipart; the hook unwraps the envelope and maps the fields; a
shared ContactPicker searches server-side (`?search=&is_customer=` — the
backend's real filter keys, fixing the silently-ignored `contact_type` key);
both payment forms list the chosen contact's open documents with clamped
allocation inputs; the invoice detail's Record Payment (status-gated) deep
links into Banking prefilled — including the tab default the first
implementation missed.

### Bank accounts + corrections (B-4, B-6)
The Add Account buttons were dead (no onClick; no form anywhere). The dialog
ships (zod-validated through the previously-unconsumed
`bankAccountInputSchema`, bank-type GL picker). Payment rows gain Void (the
reason the backend requires; the reversal + allocation release happen
server-side); reconciled transaction rows gain Unreconcile.

### Seeded accounts are filterable (C-4 + the two live-gate follow-ups)
The org seed populated only the `account_type_id` FK — the `account_type`
VARCHAR the API filter reads was NULL on every seeded account, so the invoice
form's posting-account dropdown was empty on every fresh org. The seed now
backfills the varchar; the filter matches either column (defense-in-depth for
pre-backfill orgs). The live e2e then surfaced two deeper layers: a type
filter must lift the list service's top-level-only default (the seeded bank
accounts are **children** of the 1000 header), and the dialog's plain-list +
client-side `is_bank` filter needed a real `is_bank` query param end-to-end.

### The wire contract the mocked tests could not see (live gate, B-4)
The dialog's unit suite passed while the real POST 400'd: the payload sent
`paynow_type: null` and the ModelSerializer rejected null — though the DB
column is nullable and the CHECK allows NULL or UEN/MOBILE/NRIC ("" violates
it). Both create and update serializers accept null now ("" normalizes to
NULL), and the dialog's unit test pins the exact payload.

### InvoiceNow transmits invoices only (C-3)
`send_invoicenow` checked `status == "APPROVED"` but never the document type —
and the P8 Convert flow mass-produces APPROVED quotes while the transmission
path maps anything non-credit-note to **UBL Invoice**. Any org member (the
view was `IsOrgMember`-only, looser than every sibling mutation) could deliver
a quotation as a tax invoice into a recipient's AP pipeline. Non-SALES_INVOICE
types are refused with a 400 naming the type; the view gains
`CanCreateInvoices` (parity with the convert view).

### The invoices list shows invoices (C-2)
The page called `useInvoices` with no type filter while the backend filters
only when given — quotes and bills rendered in "Manage your sales invoices",
and a quote row opened labelled INVOICE with a fabricated Amount Due. The page
sends `type=SALES_INVOICE`; any other type that ever leaks through is labelled
on the row.

### The quote-conversion envelope, pinned and read (C-1)
The endpoint nests the created invoice under `invoice`; the hook read the
response flat — every conversion toasted "Invoice undefined created" and
routed to `/invoices/undefined` (nothing caught it: vitest mocked the hook,
the backend tests never hit the endpoint envelope). The shape is pinned by an
HTTP-level test; the hook unwraps `.invoice`; the dead singular invalidation
key is gone.

### Truth batch (C-5, C-6, D-1..D-4, K-1..K-4)
`get_status_history` returned `[]` behind a TODO — it now synthesizes
`[{status, at}]` from the model's timestamps (SENT/PAID have none; documented,
absent rather than invented). The quotes list's CONVERTED badge gates on the
persisted `related_document_id` (an approved-but-unconverted quote is
APPROVED, not CONVERTED). The aged report honours its as-at date (documents
issued after it are excluded). The dashboard's invented GST F5 bars (Box 1
"150,000", Box 2 "25,000", default 15,000/2,550 output/input) and static
trend claims ("+8.2%", "-2.4%", "+12.5%", "On track for target") are removed —
not backfilled with guesses (computed deltas are registered debt); the dead
`href="#"` CTAs route to /reports. `transition_status`'s inline VOID branch
delegates to `void_document` (one engine, one contract); the stale `message`
type field and the pre-P8 `void_document` docstring are corrected.

### Hardening + posture (B-7, S-1, S-2, S-3, S-4)
The suggest-matches `?tolerance=` branch raised a bare `ValidationError` where
only `AppValidationError` is imported — a NameError 500 (the P7 fix itself was
broken; no test covered the path). The documents-list `date_from/date_to` were
the sweep's last raw-date siblings (garbage → filter 500). Both are 400s; the
suggest-matches path id parses through the shared helper and NaN/Infinity
tolerances are rejected. `checkSession` treated transport faults like auth
expiry (clearAuth + redirect) — only 401/403 clear the session now. The
Peppol XSD path failed OPEN when the schema could not load (validating
everything) — it fails closed with a validation-unavailable error. The root
`requirements.txt` — a sandbox pip-freeze contradicting the backend pins
(Django 6.0.3 vs 6.0.2, django-celery-beat 2.8.1 vs 2.9.0) — is replaced by a
pointer to the single manifest.

## 3. Deferred Debt Register (explicit — nothing silently dropped)

Carried forward from P8 §18/§20 unless noted: H-02 base-currency reporting;
M-1 audit-event coverage beyond banking (the audit log still has no READ
surface); M-10 CSRF hardening (SameSite=Lax mitigates; the Origin-check is
the S-sized follow-up); M-11 static-export security headers/CSP; H-07 backend
ruff debt (touched files stay clean; the parity rule failed once pre-P9 —
B-7); frontend eslint debt (parity); F5 GST return rate-basis; GST payment
tracking (`pay_return` needs a gst schema extension); Reg-11 full PINT
Schematron (the XSD fail-closed half shipped; the Schematron wiring follows);
ledger pagination; invoice edit flow (`update_line`); B6 list-envelope
standardization; aged credit/debit-note netting; quote lifecycle vocabulary
(DB enum); trial-balance zero-activity accounts + fiscal-year mode; reports
export; TAX-group coarse type; Storecove authenticate semantics; the
transmission `errors`-vs-`schema_errors` key.

New this sprint (registered, not dropped):
- **Contacts management pages** (list/create/edit/deactivate) — the picker
  ships; full pages are the follow-up.
- **Chart of accounts page** — backend ready, zero UI.
- **Bank account edit/deactivate UI** — create ships; edit/deactivate remain
  API-only.
- **Payment detail surface** — row actions ship (void/unreconcile); a full
  detail view with allocation management stays thin-until-needed.
- **GST review/pay/amend UI + deadlines** — compute/file ship; the rest are
  S-sized follow-ups (pay needs the schema decision).
- **Bills (PURCHASE_INVOICE) creation UI, fiscal-year/period management UI,
  Peppol transmission-log UI, manual journal-entry UI, set-default-org
  persistence** — all backend-real, frontend-absent.
- **Dashboard computed trends** — the lies are removed; real deltas need a
  period-comparison endpoint (design with H-02).
- **Dead "Load more" buttons** in the payment/transaction lists (no
  pagination on the backend lists) — latent, registered.
- **The `is_bank`/`account_type` filter lift is server-validated** — a
  CoA management UI should revisit whether the top-level default itself is
  the right contract for the unfiltered list.

## 4. How to Verify (reproduction commands)

```bash
# Prerequisites: PG on :5432 (schema v1.1.0), Redis on :6379, backend venv +
# web node_modules, playwright chromium. ALWAYS --reuse-db --no-migrations
# (a bare run drops the .env-named DB — the documented invocation is the
# contract).

cd apps/backend
pytest --reuse-db --no-migrations -q                     # 668 passed, 0 failed, 5 skipped
pytest tests/integration/test_bank_account_p9.py -q      # the null-PayNow contract
pytest tests/integration/test_invoicenow_gate_p9.py -q   # the invoice-only gate

cd ../web
npm run typecheck && npm test                            # 0 errors; 454 passed
npm run test:e2e                                         # 9 passed + 17 gated skips

# Full e2e against a live stack (serial workers — the workflow mutates
# shared state): backend: python manage.py runserver 127.0.0.1:8000 (dev DB
# bootstrapped), web: npm run dev
E2E_API_URL=http://127.0.0.1:8000 E2E_DEMO_EMAIL=… E2E_DEMO_PASSWORD=… \
  npm run test:e2e:full                                  # 26/26

# Authorization check (the C-3 evidence): an org member whose role lacks
# can_create_invoices POSTs an APPROVED QUOTE to
# /api/v1/{org}/invoicing/documents/{id}/send-invoicenow/ → 400 naming the
# type (pre-P9: a live transmission path).

# Workflow check (the B-3b evidence): open an outstanding invoice's detail,
# click Record Payment — the receive form opens in Banking prefilled with
# the contact and the allocation; submit and the invoice shows Paid.
```

## 5. Commits

Conventional commits on `main`, **pushed incrementally after every task** via
`docs/ssh_git_wrapper_v3.py` (paramiko shim; remote ref verified on every
push; deploy key shredded after the final push):

1. `fix(invoicing): InvoiceNow transmits invoices only; view permission aligned (P9/C-3)` — carries the validated P9 plan document
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
14. `fix(web): dashboard truth — real GST figure, no invented trends, live links (P9/D-2, D-3, D-4)`
15. `fix(invoicing,web): status_history synthesised; CONVERTED badge truthful; state-machine housekeeping (P9/C-5, C-6, K-1..K-4)`
16. `fix(web,peppol): session survives transport faults; XSD validation fails closed (P9/S-2, S-3)`
17. `fix(banking,coa,web): the live e2e run surfaced two deep bugs + the banking workflow spec (P9 live gate)` — the deep-link tab default + the account_type children lift + the serialized/aligned specs
18. `fix(banking,web,e2e): the live workflow gate — three contract fixes surfaced by e2e:full, then 26/26 green` — null-PayNow, `is_bank` end-to-end, the serial-mode/idempotent workflow spec; carries the 6 verified screenshots
19. `docs: P9 truth pass — README/PAD/CLAUDE/AGENTS/ledgersg_SKILL + DEPLOYMENT verification + .env.example`
20. `docs(worklog): session 18 worklog, session log, P9 report + screenshots`
