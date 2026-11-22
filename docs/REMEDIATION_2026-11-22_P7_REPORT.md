# LedgerSG — Remediation Report (P7 Sprint: API Truth & Permission Hardening)

**Date:** 2026-11-22 (session 14)
**Base commit:** `9077381b` (main)
**Plan:** `docs/REMEDIATION_PLAN_2026-11-22_P7.md`
**Source audit:** post-P6 audit re-verified in source with line numbers before planning
(two deep review passes — frontend P6 surfaces, backend views layer — plus the
repo-skill scanners per `skills/skills-catalog.md`); every Critical/High finding
re-confirmed against the working tree before execution.
**Method:** TDD (RED → GREEN → full gate). Every production-code fix has a
regression test that failed for the documented reason before the fix and passes
after: **36 new backend tests + 15 new vitest tests + 1 new e2e spec, all RED
first.**

---

## 1. Verification Ledger (executed evidence)

Environment: rootless PostgreSQL 17 on :5432 (schema v1.1.0 in `ledgersg_dev` +
`test_ledgersg_dev`), Redis 8 on :6379, Python 3.12 venv, Node with
`@playwright/test` 1.58.2 + chromium 1208, Django dev server (development
settings) on :8000 + Next dev on :3000 during the e2e/screenshots phase.

| # | Check | Command | Result |
|---|---|---|---|
| 1 | Baseline (pre-remediation, session start) | `pytest --reuse-db --no-migrations -q` | **588 passed, 0 failed, 5 skipped** at base `9077381b` — the documented P6 state reproduced exactly before any change |
| 2 | Baseline (frontend) | `npm test` / `npm run typecheck` / `npm run test:e2e` | 383/383, 0 errors, 9 passed + 11 gated skips — documented state reproduced |
| 3 | RED captures (all tasks) | per-task RED runs in the session log | status-view 4 (403-bypass live: the limited member voided via /status/; ungated PAID; garbage literals; ungated APPROVED), org-create 2 (500 TypeError), fiscal 3 (404s), payment fail-closed 3, error envelope 3, void dialog 4, send recipients 3, payables 1, settings PATCH 5, query params 6, a11y 1 — all failed for the documented reasons pre-fix |
| 4 | Full backend suite (post-remediation) | `pytest --reuse-db --no-migrations -q` | **0 failed, 624 passed, 5 skipped** (588 + 36 new: 5 status-view + 2 org-create + 3 fiscal + 4 payment/send + 4 settings-PATCH/perms + 7 query-params + 1 payables + 2 exception-handler gates + 8 send/others) |
| 5 | Invariant / security gates | `pytest tests/invariants -q` / `pytest tests/security -q` | **27 passed** (unchanged) / **53 passed, 3 skipped** (51 + 2 new posture gates: exception-handler resolution + status-code mapping through DRF dispatch) |
| 6 | Ruff (touched backend files) | before/after diff per file set | 119 → **117** findings on the touched legacy files (the E722 bare-except eliminated by the tolerance fix); all new files clean |
| 7 | Frontend unit suite | `npm test` | **398 passed (398)** — 383 + 5 error-envelope + 4 void-dialog + 2 no-org + 3 PDF/InvoiceNow + 1 a11y |
| 8 | Frontend typecheck | `npm run typecheck` | **0 errors** (the 2 `afterEach` import misses were caught by the gate and fixed — the P2/B-5 lesson held) |
| 9 | Frontend eslint (touched files) | `npx eslint <touched files>` | new files 0E/0W; shell.tsx carries its 1 pre-existing error + 1 warning (parity); 1 new unused-import finding fixed on sight |
| 10 | e2e (default, backend-less) | `npm run test:e2e` | **9 passed + 12 gated skips with reasons** (11 previous + the new void-dialog spec) |
| 11 | e2e (full, live backend + Redis + bootstrapped dev DB) | `E2E_API_URL=… npm run test:e2e:full` | **21/21 passed** — first run 18/21: the 3 failures were a spec-level strict-mode collision (two "New Invoice" links after the shell dead-button fix — spec scoped to the main region); re-run 21/21 |
| 12 | Live API smoke (dev DB) | bootstrap: register/login → org → account 4100 (exact-code resolution — the seeded chart has no account_type values) → SR (effective_on resolution) → contact → 3 invoices with the real line contract | 3 DRAFT documents; the bootstrap itself re-validated two documented contracts (P2 rate-history resolution, the account_type seed gap) |
| 13 | Authorization spot checks | new integration tests | VOID via `/status/` without `can_void_invoices` → **403** (was 200 — the bypass is closed); PAID via `/status/` → 400; settings PATCH without `can_manage_org` → 403; dashboard metrics without `can_view_reports` → 403 |
| 14 | API truth spot checks | new integration tests | org create with `address` → **201** (was 500); `fiscal-periods/` → **200** (was 404); payment on a GL-less bank account at the service seam → clean 400; send-invoice with a string `to` → 200 + list to the task; garbage query params → 400 with the param name at all 6 audited sites |
| 15 | UI truth spot checks | e2e + vitest | Void dialog enforces a reason (button disabled empty, validation message, typed reason reaches the mutation, Cancel fires nothing); error toasts carry the backend message (envelope parser); no-org users see "No organisation selected" on ledger/settings/detail (never fake failures); PDF + Send-via-InvoiceNow buttons live on the detail page with a status badge |
| 16 | Screenshots | `docs/screenshots/35..40_*_session14.png` | 6 unique PNGs (md5-distinct, 1440x900, dark-theme pixel profile 0.96-0.99, sizes 21–77KB) — login, dashboard, invoices list, **invoice detail with the P7 void dialog open**, ledger, settings — captured through the real UI login path with content-based waits |
| 17 | Docs truth sweep | greps across README/PAD/CLAUDE/AGENTS/ledgersg_SKILL/DEPLOYMENT | counts match the executed evidence (1,043 = 624 + 398 + 21); DEPLOYMENT.md rewritten as a fresh-host step-by-step guide (§1–§15, verified commands); P7 lessons 20–25 appended to the skill |
| 18 | `.env.example` verification | per-var cross-check | backend template covers every `config()` read (unchanged); web: `BACKEND_URL` moved to the reserved section (its only reader — the legacy `src/lib/server/api-client.ts` — was deleted as dead code, P7/F-13); root index updated in the same commit |

Confidence labels: all rows **Verified** (executed in this environment). The
production rate-limit posture is **Verified** at the settings level; live
production traffic behavior is **Reasoned** (same decorator mechanics as the
P4/P5 knobs exercised live in the e2e runs).

---

## 2. What Was Fixed

### The Void button works (F-1 + F-8)
The detail page sent `reason: ""` and the backend requires a non-empty reason —
every void from the UI 400'd, hidden behind the F-7 error-message gap. The page
now opens a REQUIRED-reason dialog (Shadcn/Radix Dialog + Textarea — library
discipline; both primitives added as canonical ui/ components), the confirm
button is disabled without a reason, and the typed reason reaches the mutation.
Voiding now also invalidates the ledger cache (the reversal entry), which
approve already did.

### Status-transition authorization (F-2) — the security fix
`InvoiceDocumentStatusView` gated on `elif new_status == "VOIDED"` — the enum
value is `VOID`, so the branch NEVER fired: any org member could void any
document via `POST …/documents/{id}/status/`, bypassing `CanVoidInvoices`. The
status is now a ChoiceField over the model vocabulary, every transition is
permission-gated (`VOID → can_void`, `APPROVED/SENT/OVERDUE → can_approve`),
PAID/PARTIALLY_PAID are refused outright (owned by the allocation service),
and VOID/APPROVED delegate to the canonical service methods (reason
persistence, journal posting/reversal).

### The custom exception handler is actually active (F-19 — discovered during the F-2 RED phase)
`REST_FRAMEWORK` used `"DEFAULT_EXCEPTION_HANDLER"` — DRF's key is
`"EXCEPTION_HANDLER"` (not namespaced under DEFAULT_*). The custom handler
NEVER ran, so every `LedgerSGException` that `wrap_response` re-raises
surfaced as an unhandled 500 instead of its mapped status code (this is why
the pre-P7 permission raise produced 500s). Fixed + two posture gates
(resolved-handler module, status-code mapping through DRF dispatch).

### Fiscal endpoints routed (F-4)
The three org-scoped fiscal routes lived only in the shadowed
`apps/core/urls.py` module (Python resolves `apps.core.urls` to the PACKAGE) —
the frontend's calls 404'd. Routes moved into the active package; the shadowed
module deleted; the close views gain `CanManageOrg` + timezone-aware stamps.

### Org create no longer crashes on its advertised field (F-3)
`OrganisationCreateSerializer` declared `address` — the model has no such
field — so POSTing it (the field the API itself advertised) was a TypeError
500. The phantom field is gone; the payload key is a clean no-op (mirroring
the P6/F-10 PATCH semantics).

### Payments fail closed at the GL seam (F-5)
The audited crash path (payment JE dereferencing `gl_account.id`) is guarded
by the DB (NOT NULL) and the serializer (required) — but the SERVICE seam
still accepted `gl_account=None` and surfaced the database's raw
IntegrityError as a 500. The service now raises a clean ValidationError, and
the payment JE builder carries the same guard as defense-in-depth (source-
level gate test).

### Send-invoice recipients (F-6)
The frontend sent `to` as a string; the truthiness check passed it through and
the Celery task crashed building `EmailMultiAlternatives(to=<string>)` —
silent permanent failure while the UI toasted success. Both sides fixed: a
`RecipientListField` normalizes a bare string to a one-element list and
email-validates every entry (400 on garbage); the hook type is `to: string[]`.

### Real error messages (F-7)
The api-client now reads the backend error envelope (`{error:{message}}`) and
DRF field errors (`{field:[msg]}` → `"field: msg"`), carrying `details`
through `ApiError.errors`. Business-rule messages ("Void reason is
required.") finally reach the user.

### Outstanding payables include PARTIALLY_PAID bills (F-9)
The payables status filter (`APPROVED/OVERDUE`) made partially-paid purchase
bills vanish entirely — receivables correctly included the state since P5.
Both sides now agree; the amount_paid__lt filter handles the arithmetic.

### Settings PATCHes typed + manager-gated (F-10)
Both settings PATCH endpoints went from raw `request.data` setattr (invalid
values → IntegrityError/TypeError 500s) to typed serializers (entity_type from
the model vocabulary, fy_start_month 1–12, IntegerField retry_attempts) and
`can_manage_org` via `get_permissions()` (GET stays member-readable). The
peppol test that encoded the insecure contract is updated to the secured one.

### Malformed query params are 400s (F-11)
Shared parse helpers (`common/query_params.py`: date/UUID/int → domain
ValidationError naming the param) replace the bare calls at the audited
sites: banking payments + bank-transactions date filters, the tolerance probe
(its bare `except:` silently defaulted garbage), journal entry dates + UUID
params + ledger account_id + trial-balance/account-balance dates, coa
trial-balance fiscal_year_id + search limit, gst returns year + deadlines
days, invoicing contact_id.

### Frontend truthfulness + dead code (F-12, F-13, F-14, F-17, F-18)
No-org users get a real "No organisation selected" state on ledger/settings/
detail (disabled queries made them fake failures/empty states); the GST
columns on the new-invoice form reflect the org's real registration; the
shell's dead New Invoice button is a real link (with the nav id fix for
`aria-controls`) and the "Demo User" fallbacks are gone; `handleSend` no
longer leaks an unhandled rejection. The mock-era edit route (would have
created a duplicate contact + invoice if reached by URL), `useUpdateInvoice`
and the legacy `lib/server/api-client.ts` are deleted truthfully, while
`useInvoicePDF` + `useSendInvoiceNow`/`useInvoiceNowStatus` — dead hooks
beside real backends — are wired as actions on the detail page.

### Permission classes + a11y (F-15, F-16)
Dashboard metrics/alerts require `can_view_reports`; the three org-scoped GST
views carry `IsOrgMember` (defense-in-depth). Ledger table headers expose
`scope="col"` + `aria-sort`.

## 3. Deferred Debt Register (explicit — nothing silently dropped)

Carried forward from P6 §11: H-02 base-currency reporting; M-1 audit-event
coverage beyond banking; M-10 CSRF hardening for cookie-auth endpoints; M-11
static-export security headers/CSP enforcement; M-14 Storecove authenticate
semantics; H-07 backend ruff debt (touched files stay clean); frontend eslint
debt (touched files stay parity); F5 GST return rate-basis; A-10 stale root
`requirements.txt`; GST payment tracking (`pay_return`); invoice-form
existing-contact picker; Reg-11 tax-invoice labelling/Schematron;
`status_history` returns `[]` pending the audit module; **reports/quotes real
pages** (static cards today — the FinancialReport/trial-balance endpoints
exist; the P8 candidate); `account_type` seed-column population.

New this sprint (registered, not dropped):
- **B6 list-envelope standardization** (`data` vs `results`; `my_organisations`
  bare array) — needs a synchronized frontend contract change across auth
  paths; cosmetic consistency deferred to avoid contract churn.
- **Invoice edit flow** — the mock-era route was removed truthfully; a real
  edit page needs the backend update contract widened beyond
  due_date/reference/notes.
- **Ledger pagination** — `LedgerView` is unpaginated end-to-end; fine at demo
  scale, degrades for real ledgers.
- **Settings form reset UX** (unsaved org edits wiped on refetch),
  **org-state propagation to the auth provider** (sidebar name stale until
  reload), **fiscal close "all periods closed" precondition** (B9),
  **COA serializer silently-dropped fields** (`gst_tax_code_id`/
  `bank_account_id`), **`checkSession` transport-error vs 401 distinction**,
  **dashboard service duplication** (core vs reporting implementations — the
  frontend only calls the reporting one), **invoice-form textarea label
  associations + line-grid ARIA** (F-14-class).

## 4. How to Verify (reproduction commands)

```bash
# Prerequisites: PG on :5432 (schema v1.1.0 in both DBs), Redis on :6379,
# backend venv + web node_modules, playwright chromium installed.

cd apps/backend
pytest --reuse-db --no-migrations -q                     # 624 passed, 0 failed, 5 skipped
pytest tests/integration/test_document_status_view_p7.py -q   # the F-2 authorization suite
pytest tests/security -q                                 # 53 passed, 3 skipped

cd ../web
npm run typecheck && npm test                            # 0 errors; 398 passed
npm run test:e2e                                         # 9 passed + 12 gated skips

# Full e2e against a live stack (development settings budget the run):
#   backend: python manage.py runserver 127.0.0.1:8000  (dev DB bootstrapped)
#   web:     npm run dev
E2E_API_URL=http://127.0.0.1:8000 E2E_DEMO_EMAIL=… E2E_DEMO_PASSWORD=… \
  npm run test:e2e:full                                  # 21/21

# Authorization bypass check (the F-2 evidence):
#   a member whose role lacks can_void_invoices POSTs {"status":"VOID","reason":"x"}
#   to /api/v1/{org}/invoicing/documents/{id}/status/  → 403 (pre-P7: 200)
```

## 5. Commits

Conventional commits on `main`, **pushed incrementally after every task**
via `docs/ssh_git_wrapper_v3.py` (paramiko shim; remote ref verified on
every push; deploy key shredded after the final push). Two `git add -A`
sweeps moved neighbouring changes into earlier commits than their subject
lines suggest — both traced here for accuracy:

1. `fix(invoicing): status-transition endpoint validates status + enforces per-status permissions (P7/F-2, F-19)` — also carries the exception-handler root-cause fix, the two posture gates, and the validated P7 plan document (first commit of the sprint)
2. `fix(core): organisation create drops the phantom address field (P7/F-3)` — the shadowed `apps/core/urls.py` deletion (−86 lines) was swept into this commit's staged index ahead of the F-4 routes; the routes themselves landed in commit 3
3. `fix(core): fiscal-period/close endpoints routed; shadowed urls module retired (P7/F-4)`
4. `fix(banking): bank-account GL-account truth fails closed at every seam (P7/F-5)`
5. `feat(web): working void/send flows, real error messages, truthful states, PDF+InvoiceNow actions (P7/F-1, F-6, F-7, F-8, F-12, F-13, F-14, F-17, F-18)` — the F-6 backend half (RecipientListField + send-view validation + its TDD suite), the **F-9 payables fix** (`dashboard_service.py` + its TDD test) and the `.env.example` updates rode this batch commit (there is no standalone F-9 commit)
6. `fix(peppol,core): settings PATCHes typed and manager-gated (P7/F-10)`
7. `fix(api): malformed query params return 400 across the audited endpoints (P7/F-11)`
8. `fix(reporting,gst): missing permission classes (P7/F-15)`
9. `fix(web): ledger table a11y + gated void-dialog e2e spec (P7/F-16, F-1)`
10. `test(web,e2e): scope the New Invoice link to the main region (strict-mode collision with the shell link, P7/F-17 follow-up)` — the live-phase spec fix found by the e2e:full run (18/21 → 21/21)
11. `docs: P7 truth pass — README/PAD/CLAUDE/AGENTS/ledgersg_SKILL + DEPLOYMENT fresh-host guide`
12. `docs(worklog): session 14 worklog, session log, P7 report + screenshots`
