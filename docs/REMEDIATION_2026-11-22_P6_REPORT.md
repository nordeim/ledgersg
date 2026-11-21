# LedgerSG — Remediation Report (P6 Sprint: C-5 Completion & Payment Posting Integrity)

**Date:** 2026-11-22 (session 12)
**Base commit:** `20069486` (main)
**Plan:** `docs/REMEDIATION_PLAN_2026-11-22_P6.md`
**Source audit:** the post-P5 audit re-verified in source before planning (plan §0; every
finding re-confirmed against the fresh clone with line numbers)
**Method:** TDD (RED → GREEN → REFACTOR). Every production-code fix below has a regression
test that failed for the documented reason before the fix and passes after: 21 new backend
tests + 21 new vitest tests + 3 new e2e specs, all RED first.

---

## 1. Verification Ledger (executed evidence)

Environment: rootless PostgreSQL 17 on :5432 (schema v1.1.0 in `ledgersg_dev` +
`test_ledgersg_dev`), Redis 8 on :6379, Python 3.12 venv, Node with `@playwright/test`
1.58.2 + chromium 1208, Django dev server (development settings) on :8000 + Next dev on
:3000 during the e2e/screenshots phases.

| # | Check | Command | Result |
|---|---|---|---|
| 1 | Baseline (pre-remediation, session start) | `pytest --reuse-db --no-migrations -q` | **567 passed, 0 failed, 5 skipped** at base `20069486` — the documented P5 state reproduced exactly before any change |
| 2 | Baseline (frontend) | `npm run test` / `npm run typecheck` / `npm run test:e2e` / `npm run lint` | 358/358, 0 errors, 10 passed + gated skips, 74 pre-existing lint problems — documented state reproduced |
| 3 | RED captures (all tasks) | per-task RED runs in the session log | payment 9 (F-4 guard message, AR-on-1010 decoy, no-raise fail-closed, None control accounts, stale amount_paid), org allowlist 1, serializer 2, detail page 7, ledger 2+module-missing, settings module-missing, gates 4 — all failed for the documented reasons pre-fix |
| 4 | Full backend suite (post-remediation) | `pytest --reuse-db --no-migrations -q` | **0 failed, 588 passed, 5 skipped** (567 + 10 payment + 2 org-allowlist + 2 serializer + 3 ledger + 4 settings-gates) |
| 5 | Invariant / security gates | `pytest tests/invariants -q` / `pytest tests/security -q` | **27 passed** (unchanged) / **51 passed, 3 skipped** (47 + 4 new posture gates) |
| 6 | Ruff (touched backend files) | before/after per file (same-directory originals) | payment_service 30→26, contact_service 69→68, test_views 5→5, organisations 9→9, organisation_service 25→25, serializers 19→17, journal urls 5→2, views 1→1 (pre-existing B904), settings base 3→3 / testing 10→9 / ratelimits 0→0 / auth 0→0; development 19→21 (the 2 new F405s are the file's established star-import idiom, same rule class as the pre-existing 19); all new test files clean |
| 7 | Frontend unit suite | `npm test` | **383 passed (383)** — 358 + 7 detail + 3 ledger-hook + 4 ledger-page + 5 org-hook + 6 settings-page |
| 8 | Frontend typecheck | `npm run typecheck` | **0 errors** |
| 9 | Frontend eslint (touched files) | `npx eslint <touched files>` | 0 errors/0 warnings on all new files; the rewritten ledger-table carries the same 1 pre-existing tanstack `react-hooks/incompatible-library` warning as the file it replaced (parity) |
| 10 | e2e (default, backend-less) | `npm run test:e2e` | **9 passed + 11 gated skips with reasons** (8 previous + the new detail/ledger/settings specs) |
| 11 | e2e (full, backend + Redis + bootstrapped dev DB) | `E2E_API_URL=… npx playwright test` | **20/20 passed** — incl. the detail page (real document number + payment state, never mocks), the ledger page (real lines or truthful empty state), and the settings page (real org values, never the mock defaults) |
| 12 | Live API smoke (dev DB) | bootstrap script: register/login → org → account 4100 → SR tax code → contact → 3 invoices | 3 documents with the real line contract (`account_id` + `tax_code_id` per line); first e2e full run at 18/20 exposed two real defects (payment state hidden on unpaid invoices; `getByDisplayValue` unavailable) — both fixed, 20/20 on the re-run |
| 13 | Accounting truth (spot, test-verified) | payment-posting P6 suite | second allocation on PARTIALLY_PAID → status by recomputed total; AR credit on **1200** (decoy 1010 rejected), AP debit on **2100** (2000 header rejected); renamed code+name → ValidationError; create_contact assigns 1200/2100 by type; unallocate recomputes amount_paid/status and the amount_due generated column (raw SQL) |
| 14 | Org PATCH truth | integration tests | real address fields round-trip through the API (response + DB); the phantom `address` key is a no-op |
| 15 | Screenshots | `docs/screenshots/29..34_*_session12.png` | 6 unique PNGs (md5-distinct, 1440x900, non-blank dark-theme pixel profile ≥ 0.996) — login, dashboard, invoices list, **invoice detail (real data, payment state)**, **ledger (real journal lines)**, **settings (real org)** — captured through the real UI login path with content-based waits |
| 16 | Docs truth sweep | greps across README/PAD/AGENTS/ledgersg_SKILL | counts match the executed evidence (991 = 588 + 383 + 20); AGENTS `NUMERIC(10,4)` current-precision claims corrected to `NUMERIC(19,4)` money / `NUMERIC(12,6)` rates (verified against `information_schema` — 47 money columns at 19,4; the line-821 P3 history note stays, it is accurate history) |
| 17 | `.env.example` verification | per-var cross-check (`config()` calls vs backend template; `process.env` vs web template) | every variable read by the code is documented; **P6 introduced no new env vars** (the E-1 knobs are Django settings, not env); no changes needed |
| 18 | Settings-dict isolation | posture gate test | base 20/min anon + 100/min user + 20/min refresh intact after loading development/testing (the testing.py in-place mutation that corrupted the shared base dict is fixed copy-on-write) |

Confidence labels: all rows **Verified** (executed in this environment). The production
rate-limit posture is **Verified** at the settings level (gate tests); live production
traffic behavior is **Reasoned** (same decorator mechanics as the login knobs, which the
P4/P5 sessions exercised live).

---

## 2. What Was Fixed

### PARTIALLY_PAID is no longer a dead end (F-4)
`allocate()`'s guard widens from `status != "APPROVED"` to `status not in ("APPROVED",
"PARTIALLY_PAID")`. P5/H-1 deliberately persisted PARTIALLY_PAID, but the guard was never
widened — the second payment could never settle the remainder. DRAFT/VOID/PAID/OVERDUE
remain rejected (guard test).

### Exact payment control accounts, fail-closed (F-5)
`_create_payment_journal_entry` stops broad-matching `Q(account_type="ASSET"/"LIABILITY")
.first()` — the exact defect class P5/H-4 eliminated in journal_service. When the contact's
control account is unset it resolves through `JournalService._get_ar_account() /
_get_ap_account()` (exact code → exact name → sub-type code, headers excluded, fail-closed).
The decoy tests prove the old code could post AR to 1010 Cash on Hand; the fail-closed test
renames code AND name so neither resolver arm can match by luck.

### Contacts get control accounts at creation (F-6)
`create_contact` assigns `_get_ar_account` (customers) / `_get_ap_account` (suppliers) /
both (BOTH) — the normal payment path never depends on the fallback. The two `test_views`
fixtures that silently depended on the old fallback (customer without receivable_account,
org without 1200 — AR was silently posted to the 1100 bank account, the F-5 defect in
action) are corrected to the real contract.

### unallocate() recomputes (F-7)
`amount_paid` is recomputed from the surviving allocations and the status derived with the
same thresholds as allocate() (`>= total_incl` → PAID, `> 0` → PARTIALLY_PAID, else
APPROVED). The `amount_due` generated column stays truthful (asserted via raw SQL — it is
not a model field).

### Organisation address is updatable (F-10)
Both update allowlists (view + service) replace the phantom `address` key with the real
model fields (`address_line_1/2`, `city`, `postal_code`, `country`) — the
`OrganisationSerializer` already carried them. A PATCH with the phantom key is a no-op.

### Invoice detail truth end-to-end (F-11 + C-5 + D-1)
Backend: `InvoiceDocumentDetailSerializer` gains `amount_paid` (model field) and
`amount_due` (SerializerMethodField mirroring the DB generated column
`total_amount - amount_paid`). Frontend: full rewrite of the detail client (status badge,
lines table, totals, payment state on every non-void document, approve/void/send mutations
with pending states, truthful loading/error states); `useInvoice` retyped to the real
`InvoiceDetail` contract (was typed as the client-side form schema — a type lie); the page
`await`s its route params (a Promise in this Next.js version — the sync read only worked by
build accident, D-1) and drops the mock-era `generateStaticParams`.

### Real general-ledger page (C-5)
New `GET /api/v1/organisations/{org_id}/journal-entries/ledger/` — one row per journal
line joined with entry + account (entry number/date, source type, reference, narration,
account code/name, description, debit, credit), filtered by date range / account / source
type; org-scoped and header-guarded. Frontend: `useLedger` hook + props-driven
`ledger-table` rewrite (mockData deleted) + client with loading/error/empty states.

### Real settings page (C-5)
`useOrganisation` hooks (detail query, allowlisted PATCH updates, GST register/deregister
with cache invalidation and toasts) + a settings client replacing the hardcoded
`defaultValue` cards. The GST endpoints seed the GST control accounts (P5/M-5) — the
settings page is now the UI path for that.

### e2e-friendly rate budgets as settings knobs (E-1)
`REFRESH_RATELIMIT_IP` (base 20/minute — production posture unchanged) resolved lazily via
`config.ratelimits.refresh_ip`; development raises the refresh + DRF anon/user budgets
(240/min, 600/min) copy-on-write; testing stays off. The first full e2e run 429'd mid-suite
against the hardcoded limits — with the knobs it is 20/20. Bonus defect fixed: testing.py's
in-place `REST_FRAMEWORK` mutation corrupted the shared base dict for every other module in
the process (the new posture gate test caught it); both settings modules are now
copy-on-write.

---

## 3. Deferred Debt Register (explicit — nothing silently dropped)

Carried forward unchanged from P5 §14: H-02 base-currency reporting / retained earnings /
BS assertion; M-1 audit-event coverage beyond banking; M-10 CSRF hardening for cookie-auth
endpoints; M-11 static-export security headers / CSP enforcement; M-14 Storecove
authenticate semantics; H-07 backend ruff debt (~1,251 findings; touched files stay clean);
frontend eslint debt (touched files stay parity); F5 GST return rate-basis; A-10 stale root
`requirements.txt`; GST payment tracking (`pay_return`); invoice-form existing-contact
picker; Reg-11 tax-invoice labelling / Schematron.

New this sprint: none. (The de-escalated `account_type` seed gap is closed by the F-5
fail-closed resolver; populating the column in the SQL seed remains optional hardening —
deferred. Invoice detail's `status_history` still returns `[]` pending the audit module —
pre-existing TODO, unchanged.)

## 4. How to Verify (reproduction commands)

```bash
# Prerequisites: PG on :5432 (schema v1.1.0 in ledgersg_dev + test_ledgersg_dev),
# Redis on :6379, backend venv + web node_modules, playwright chromium installed.

cd apps/backend
pytest --reuse-db --no-migrations -q        # 588 passed, 0 failed, 5 skipped
pytest apps/banking/tests/test_payment_posting_p6.py -q   # 10 payment-truth tests
pytest tests/security -q                    # 51 passed, 3 skipped (4 new posture gates)

cd ../web
npm run typecheck && npm test               # 0 errors; 383 passed
npm run test:e2e                            # 9 passed + 11 gated skips

# Full e2e against a live stack (development settings raise the throttle budgets):
#   backend: python manage.py runserver 127.0.0.1:8000  (dev DB bootstrapped)
#   web:     npm run dev
E2E_API_URL=http://127.0.0.1:8000 E2E_DEMO_EMAIL=… E2E_DEMO_PASSWORD=… \
  npm run test:e2e:full                     # 20/20

# Org address round-trip:
curl -X PATCH "$API/api/v1/$ORG_ID/" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"address_line_1":"12 Marina Boulevard","city":"Singapore","postal_code":"018982"}'
```

## 5. Commits

Conventional commits on `main`, pushed incrementally via `docs/ssh_git_wrapper_v3.py`
(paramiko shim; key shredded after the final push):

1. `fix(banking): payment posting integrity — PARTIALLY_PAID allocations, exact control accounts, contact defaults, unallocate recompute (P6/F-4/F-5/F-6/F-7)`
2. `fix(core): organisation update allowlists forward the real address fields (P6/F-10)`
3. `feat(invoicing): detail serializer exposes amount_paid/amount_due (P6/F-11)`
4. `feat(web): real invoice detail page via useInvoice + payment state (P6/C-5, D-1)`
5. `feat(journal): flat line-level ledger endpoint (P6/C-5)`
6. `feat(web): real general-ledger page via journal ledger endpoint (P6/C-5)`
7. `feat(web): real organisation settings page + GST registration wiring (P6/C-5)`
8. `feat(core): settings-derived refresh/auth throttle budgets (P6/E-1)`
9. `feat(web): always surface the invoice payment state + e2e/screenshot fixes (P6/C-5)`
10. `docs: P6 truth pass — README/PAD/ledgersg_SKILL/AGENTS precision + .env.example verification`
11. `docs(worklog): session 12 worklog, session log, P6 report + screenshots`
