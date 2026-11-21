# LedgerSG — Remediation Report (P5 Sprint: Truth Restoration)

**Date:** 2026-11-21 (session 11)
**Base commit:** `cfc74571` (main)
**Plan:** `docs/REMEDIATION_PLAN_2026-11-21_P5.md`
**Source audit:** `docs/ledgersg-audit-report.md` (every Critical/High finding re-verified in source before planning — see plan §0)
**Method:** TDD (RED → GREEN → REFACTOR). Every production-code fix below has a regression test that failed for the documented reason before the fix and passes after: 33 new backend tests + 4 new vitest tests + 1 new e2e spec, all RED first.

---

## 1. Verification Ledger (executed evidence)

Environment: rootless PostgreSQL 17 on :5432 (schema v1.1.0 in `ledgersg_dev` + `test_ledgersg_dev`), Redis 8.0.2 on :6379, Python 3.12 venv, Node with `@playwright/test` + chromium, Django dev server (development settings) on :8000 during the e2e/screenshots phases.

| # | Check | Command | Result |
|---|---|---|---|
| 1 | Baseline (pre-remediation, session start) | `pytest --reuse-db --no-migrations -q` | **534 passed, 0 failed, 5 skipped** at base `cfc74571` — the documented P4 state reproduced exactly before any change |
| 2 | Baseline (frontend) | `npx vitest run` / `npm run typecheck` / `npm run test:e2e` | 354/354, 0 errors, 9 passed + 7 gated skips — documented state reproduced |
| 3 | RED captures (all tasks) | per-task RED runs in the session log | 33 backend + 4 vitest tests failed for the documented reasons pre-fix (stubs, missing writes, wrong accounts, 4dp amounts, duplicate line numbers, no invalidation, no seeding, missing component) |
| 4 | Full backend suite (post-remediation) | `pytest --reuse-db --no-migrations -q` | **0 failed, 567 passed, 5 skipped** (534 + 12 peppol + 5 payment + 7 control-account/money + 4 dashboard + 5 org-service) |
| 5 | Invariant / security gates | `pytest tests/invariants -q` / `pytest tests/security -q` | **27 passed** (20 + 7 new) / **47 passed, 3 skipped** (no regressions) |
| 6 | Django system check | `DJANGO_SETTINGS_MODULE=config.settings.testing python manage.py check` | 0 errors, 1 known pre-existing warning (`django_ratelimit.W001`) |
| 7 | Ruff (touched backend files) | before/after per file (stdin-diff method) | **zero new findings** on every touched file; new test files lint-clean; repo `invalid-syntax` findings 2 → 0 (org_seed_service removed) |
| 8 | Frontend unit suite | `npm test` | **358 passed (358)** — 354 + 4 page tests (30 files) |
| 9 | Frontend typecheck | `npm run typecheck` | **0 errors** |
| 10 | Frontend eslint (touched files) | `npx eslint <touched files>` | **0 errors, 0 warnings** on the new/rewritten files |
| 11 | e2e (default, backend-less) | `npm run test:e2e` | **9 passed + 8 gated skips with reasons** (7 previous + the new list-page spec) |
| 12 | e2e (full, backend + Redis) | `E2E_API_URL=… npm run test:e2e:full` | **17/17 passed** — incl. the new "renders real backend rows or a truthful empty state" and all three P4 session-persistence specs |
| 13 | Hygiene greps | `git ls-files \| rg '\.pyc$\|^apps/web/dist/\|\.bak'` / `rg '\.env'` | **0 artifacts tracked**; only the three `.env.example` files remain; `rg ledgersg_secret_to_change .github/` → 0 hits |
| 14 | Local dev files intact | `ls apps/backend/.env apps/web/.env.local` + `git check-ignore` | both present on disk, properly ignored (dev servers keep working) |
| 15 | Live API smoke (dev DB) | register → create org → set default org → 3× create document with lines | org created with the full 102-account seeded chart (incl. 1600/2600 — the GST control accounts); documents INV-00003/04/05 created DRAFT with correct SR 9% totals (2725.00 / 13625.00 / 8502.00) |
| 16 | Live InvoiceNow posture | (e2e + contract tests) | send on an unconfigured org → ValidationError configure-first (contract test); configured org → real `PeppolTransmissionLog` + queued task (eager Celery in tests) |
| 17 | Accounting truth (spot, test-verified) | payment-truth + control-account suites | allocate → `amount_paid`/status/`amount_due` correct; void → reversal entry linked (`is_reversed`, mirrored lines), allocations released, status restored; GST output lands on **2600**, AR on **1200**; non-GST org + GST line → ValidationError, zero journal lines |
| 18 | Screenshots | `docs/screenshots/24..28_*_session11.png` | 5 unique PNGs (md5-distinct, 1440x900, non-blank — dark-theme pixel profile matches the known-good session-7/9 baseline; table region content stdev 17.1) incl. **26_invoices_real_data** — the list page rendering the three API-created invoices |
| 19 | Docs truth sweep | greps across README/PAD/CLAUDE/AGENTS/ledgersg_SKILL/DEPLOYMENT | counts match the executed evidence (932 = 567 + 358 + 17); no stale "stub/TODO" claims for the fixed items; no `NUMERIC(10,4)` regressions |
| 20 | Root `.env.example` | read + per-var cross-check vs both app templates | still truthful after the testing.py change (no new vars introduced); CI note added to DEPLOYMENT.md |

Confidence labels: all rows **Verified** (executed in this environment). The IRAS 5-year-retention posture of the cleanup task is **Reasoned** (documented consequence of never deleting DELIVERED/REJECTED; the archival-export alternative remains deferred — needs a storage-target decision). CI behavior is **Reasoned** (the workflow's per-run password + DB_* env are verified by construction and the local equivalent runs; GitHub Actions itself was not executed from this sandbox).

---

## 2. What Was Fixed

### Repo hygiene (C-1, C-3, H-9, M-9, M-12, L-4/5/6)
`git rm --cached`: `apps/backend/.env` + `apps/web/.env.local` (re-committed by P4's `git add -A` — gitignore does not protect modified tracked files), 211 `__pycache__/*.pyc`, 54 `apps/web/dist/` files, 10 `*.bak*` files; working-tree copies kept. `.gitignore` gained `__pycache__/`, `*.pyc`, `dist/`, `*.bak*`. CI's `POSTGRES_PASSWORD` is now generated per run (`ci-${{ github.run_id }}-${{ github.run_attempt }}` — zero committed credentials, zero secrets setup); the test step exports `DB_*`; the pip cache points at `pyproject.toml`. `config/settings/testing.py` reads `DB_*` from env (decouple) with the documented dev defaults instead of hardcoding the shared password.

### Dead code (C-4, M-7)
`apps/core/services/org_seed_service.py` deleted — unimportable (`IndentationError`), zero callers, duplicated the SQL seed function that is the live path. Dead `_create_document_sequences` (wrong doc-type vocabulary) removed from `organisation_service.py`.

### Real InvoiceNow (C-2 + the newly-found seam bug)
New `TransmissionService.execute_transmission_for_log(log_id)` drives the EXISTING log row through XML generation → validation → AP adapter; `transmit_peppol_invoice_task` calls it (the old call passed the log id to `transmit_invoice(invoice_id)` — the auto-transmit path could never succeed). `send_invoicenow` creates a real `PeppolTransmissionLog`, queues the task, returns the real log id (+ task id), and rejects unconfigured orgs with a configure-first message. `get_invoicenow_status` reports the real log rows (latest status + history; truthful `NOT_CONFIGURED` / `NOT_TRANSMITTED`). `check_transmission_status_task` is wired to the AP adapter's `check_status` and updates the matching log. `cleanup_old_transmission_logs_task` is retention-safe: it only removes stale non-final logs (PENDING/TRANSMITTING/FAILED beyond the horizon) and NEVER deletes DELIVERED/REJECTED — the IRAS 5-year delivery evidence.

### Accounting integrity (H-1, H-2)
`PaymentService.allocate()` persists `document.amount_paid` (sum of the document's allocation rows) alongside the status transition — the dashboard's outstanding-AR/AP filters and the `amount_due` generated column were permanently overstated because `amount_paid` never left 0. `PaymentService.void()` posts a reversing journal entry (`create_reversal`, with the open-period date fallback mirroring `void_document`), releases the payment's allocations, recomputes each affected document's `amount_paid`/status, and records the reversal id in the audit event.

### Control accounts, fail-closed (H-4)
New `_resolve_control_account`: exact code → exact name → sub-type, header accounts never eligible, `ValidationError` when unknown. AR=**1200**, AP=**2100**, GST input=**1600**, GST output=**2600** (the seeded chart's real control codes; 1600/2600 are GST-registration-conditional and the resolver's error tells the operator to seed them). The old broad-OR `.first()` resolvers posted output tax to **2200 Accrued Expenses**, could land AR on a header account, and silently posted GST for non-GST orgs. The conftest `test_accounts` fixture carried the same wrong map (2200 named "GST Output Tax") and now mirrors the real seed.

### Money & lines (H-5, H-6, + auth display)
`add_line` stores `line_amount = amount` (the 2dp GST base) and `total_amount = (line + gst).quantize(0.01)` — subtotal/GST/total reconcile to the cent (the old 4dp line_amount next to a 2dp GST base did not). `create_entry` numbers lines with `enumerate` (duplicate line dicts previously got the same number and crashed the unique constraint). `auth_service` `access_expires` is timezone-aware.

### Dashboard truth (H-3, H-10)
`invalidate_dashboard_cache` is now called by the mutations that change dashboard state: document approve/void, payment create (received/made)/allocate/void, GST return filing (local imports; exception-guarded so a cache hiccup can never fail the mutation). `DashboardAlertsView` computes real values — compliance alerts and overdue counts via the existing `DashboardService` queries, unreconciled bank transactions, unpaid bills, GST threshold warning — replacing the placeholder zeros.

### Organisation service (M-5, M-6)
`toggle_gst_registration` captures the previous state and seeds the GST control accounts (1600/2600/2610) on a NEW registration via a targeted idempotent helper (the old `if not org.gst_reg_number` guard ran after the assignment — always False; the full chart seed is not re-runnable because sequences collide). `update_organisation` is allow-listed at the service boundary (`UPDATABLE_ORG_FIELDS`); unknown/protected keys are ignored with a warning.

### Frontend: real invoices list (C-5 part 1)
`invoices/page.tsx` mock data deleted; the new `InvoicesClient` renders `useInvoices` data (backend `{results, count}`, `InvoiceDocumentListSerializer` shape) with truthful loading / error-with-retry / empty states, live search, real status badges for the full document enum, and rows linking to `/invoices/[id]`. `useInvoices` retyped to the real row shape (`InvoiceListItem`) and accepts a nullable orgId.

---

## 3. Deferred Debt Register (explicit — nothing silently dropped)

Carried forward from the P4 register (`docs/REMEDIATION_PLAN_2026-11-21_P4.md` §9) unless touched here:

| Item | Status |
|---|---|
| C-5 remainder: invoice DETAIL page, ledger table, settings page, reports/quotes pages | **Deferred to P6** — the hook+client+states pattern is proven on the list page |
| M-1 audit-event coverage beyond banking (invoicing/gst/journal writers) | Deferred |
| M-10 CSRF hardening for cookie-auth endpoints (`X-Requested-With` / double-submit) | Deferred |
| M-11 static-export security headers; CSP enforcement (report-only today) | Deferred |
| M-14 Storecove `authenticate()` 404-as-valid semantics | Deferred (health-check semantics; real validation happens on send) |
| Transmission-log archival export (beyond never-delete) | Deferred — needs a storage-target decision |
| H-07 backend ruff debt (~1,245 findings after this sprint) | Pre-existing; touched files stay lint-clean |
| H-08/B-6 frontend eslint debt (42E/30W) | Pre-existing; the dist/ *tracking* fixed this sprint, the lint-scope `globalIgnores` ride-along was not (register) |
| H-02 base-currency reporting / retained earnings / BS assertion | Deferred (design work) |
| F5 return rate-basis (computation date vs document date) | Deferred — period-cut semantics (ties into H-02) |
| A-10 stale root `requirements.txt` | Deferred (repo-owner coordination) |
| GST payment tracking (`pay_return`) | Intentionally raises until schema extension |
| Invoice form: existing-contact picker | Deferred |
| Reg-11 tax-invoice labelling, Schematron fail-closed (old register H-09/H-10) | Deferred |

---

## 4. How to Verify (reproduction commands)

```bash
# Prerequisites: PG on :5432 (schema v1.1.0), Redis on :6379, backend venv + web node_modules
cd apps/backend
export DB_NAME=test_ledgersg_dev DB_USER=ledgersg DB_PASSWORD=ledgersg_secret_to_change \
       DB_HOST=127.0.0.1 DB_PORT=5432
pytest tests/peppol/test_transmission_wiring.py -q      # 12 passed (C-2)
pytest apps/banking/tests/test_payment_truth.py -q      # 5 passed (H-1/H-2)
pytest tests/invariants/test_control_account_resolution.py -q  # 7 passed (H-4/H-5/H-6)
pytest apps/reporting/tests/test_dashboard_truth.py -q  # 4 passed (H-3/H-10)
pytest tests/integration/test_organisation_service_truth.py -q # 5 passed (M-5/M-6)
pytest --reuse-db --no-migrations -q                    # 567 passed, 0 failed, 5 skipped

cd ../web
npx vitest run "src/app/(dashboard)/invoices/__tests__/invoices-page.test.tsx"  # 4 passed
npm run typecheck && npm test                            # 0 errors; 358/358

# Hygiene
git ls-files | rg '\.env|\.pyc$|^apps/web/dist/|\.bak'   # only the 3 .env.example files
rg ledgersg_secret_to_change .github/                    # no hits

# Full e2e (backend on :8000 + Redis; demo user password is 12+ chars)
E2E_API_URL=http://127.0.0.1:8000 E2E_DEMO_PASSWORD=<demo password> \
  npm run test:e2e:full                                  # 17/17
```
