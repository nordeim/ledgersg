# LedgerSG — Remediation Plan (P5 Sprint: Truth Restoration — Repo Hygiene, Real InvoiceNow, Accounting Integrity & Real Dashboard Data)

**Date:** 2026-11-21 (session 11)
**Base commit:** `cfc74571` (main)
**Source:** `docs/ledgersg-audit-report.md` (the independent audit of `7e4061f0`, uploaded `93b4fbd8`) — every Critical/High finding re-verified against the live codebase this session (see §0) — plus the deferred-debt register of `docs/REMEDIATION_PLAN_2026-11-21_P4.md` §9 (H-08 InvoiceNow wiring is partially absorbed here) and the session-11 user directives (vitest + playwright suite extension through the existing configs; root `.env.example` verification; screenshots; worklog; push).
**Execution mode:** Mode B/D — TDD (RED → GREEN → REFACTOR), surgical fixes
**Plan validated against:** live codebase + rootless PostgreSQL 17 on :5432 (schema v1.1.0 in `ledgersg_dev` + `test_ledgersg_dev`) + Redis 8.0.2 on :6379; all four baselines reproduced exactly before planning — backend `pytest` **534 passed / 0 failed / 5 skipped**, invariants **20 passed**, security **47 passed / 3 skipped**, frontend `vitest` **354/354 (29 files)**, `tsc --noEmit` **0 errors**, playwright default **9 passed + 7 gated skips**; `manage.py check` 0 errors (1 known W001).

**Post-writing validation (plan checked against code before execution):**
- Every §0 finding re-verified in source this session (commands and line evidence below) — the audit report's claims hold at `cfc74571` (the two commits after `7e4061f0` are docs-only).
- The seeded CoA contract for the account-selection fix (Task 6) verified in `database_schema.sql` §`core.seed_default_chart_of_accounts`: **1200 Accounts Receivable** (sub_type 103), **2100 Accounts Payable** (202), **1600 GST Input Tax** (asset, seeded only when GST-registered), **2600 GST Output Tax** (liability, seeded only when GST-registered). The current `_get_gst_output_account` matches `code__startswith="220"` → posts output tax to **2200 Accrued Expenses**; `_get_gst_input_account` broad-matches any ASSET (`.first()` can return 1010 Cash on Hand).
- `JournalService.reverse_entry(org_id, original_entry_id, reversal_date, reason, user_id)` exists and is the pattern `DocumentService.void_document` uses — the payment-void fix (Task 5) mirrors it; `Payment.journal_entry` FK already exists (`apps/core/models/payment.py:67`).
- `TransmissionService` is fully implemented (`transmit_invoice`, `_execute_transmission`, `_update_log_with_result`, `retry_transmission`, adapter selection); `StorecoveAdapter.check_status(message_id)` exists. **Newly discovered wiring bug (verified this session):** `transmit_peppol_invoice_task` calls `service.transmit_invoice(transmission_log_id, org_id)` — but `transmit_invoice(invoice_id, …)` expects the **invoice** id and creates a NEW log; the task passes the **log** id → `InvoiceDocument.DoesNotExist` → the auto-transmit path can never succeed, and the pre-created log from `_queue_peppol_transmission` stays PENDING forever. Task 3 fixes the seam, not just the two stub endpoints.
- `dashboard_service` already ships `query_gst_threshold_status`, `generate_compliance_alerts`, `_get_invoice_counts` (overdue/pending/peppol_pending) — the `DashboardAlertsView` stub (Task 8) never calls them.
- `useInvoices(orgId, filters)` (`apps/web/src/hooks/use-invoices.ts`) is complete and contract-correct (`{results, count}`) but has **zero page consumers** — the invoices list page renders `mockInvoices` (verified `page.tsx:13-41,130`).
- `apps/backend/.env` + `apps/web/.env.local` are **tracked again** — re-added by P4 commit `f225547f` (verified `git show --stat`), despite the P1 untracking and the `.gitignore` rules; 211 `*.pyc`, 54 `apps/web/dist/` files and 8 `*.bak`/`*.bak2` files are tracked (verified `git ls-files` counts).
- `config/settings/testing.py:24-28` hardcodes the DB password/host; base settings already read `DB_*` from env (`base.py:129-133`) — the testing override can honor the same env vars. CI (`ci.yml:23,41`) embeds the shared password; a per-run generated value removes the committed credential with zero secrets-management overhead.

---

## 0. Audit Summary (what this plan is built on)

Focus per instructions: **the recent code changes** (P4 sprint commits `d1323646..7e4061f0`, re-read in full this session — the P4 report's claims hold: cookie flow, evidence gate, settings-driven rates all verified in source and by the reproduced green gates) **plus the independent audit report** (`docs/ledgersg-audit-report.md`), whose findings were re-verified one by one this session:

| Audit ID | Severity | Claim | Re-verified this session |
|---|---|---|---|
| C-1 | Critical | `.env`/`.env.local` tracked in git (re-added by `f225547f`) | `git ls-files` + `git show --stat f225547f` |
| C-2 | Critical | `send_invoicenow`/`get_invoicenow_status` stubs; `check_transmission_status_task` hardcodes PENDING; cleanup deletes DELIVERED/REJECTED logs at 90d | `document_service.py:807-846`, `tasks.py:193-232` |
| C-3 | Critical | CI plaintext password; `testing.py` hardcodes DB creds | `ci.yml:23,41`, `testing.py:24-28` |
| C-4 | Critical | `org_seed_service.py` does not parse (`IndentationError` line 285) | `ast.parse` reproduced |
| C-5 | Critical | Frontend mock data on invoices list/detail, ledger, settings, reports | `page.tsx:13` mocks verified; scope of this sprint = invoices list (part 1) |
| H-1 | High | `allocate()` never writes `document.amount_paid` → AR overstated | `rg amount_paid apps/banking/services/payment_service.py` → zero hits |
| H-2 | High | `PaymentService.void` creates no reversal journal entry | `void()` body read (lines 274-330): sets `is_voided`, no reversal |
| H-3 | High | `invalidate_dashboard_cache` defined, never called in production paths | grep: only its own tests |
| H-4 | High | AR/AP/GST account selection broad OR + `.first()` (output tax → 2200 Accrued Expenses) | `_get_*_account` bodies read (lines 606-700) |
| H-5 | High | `add_line` stores 4dp `line_amount` while GST base is 2dp `amount` | lines 278-315 read; `line_amount = gross - discount` unquantized |
| H-6 | High | `create_entry` uses `lines.index(line_data)+1` (wrong for duplicates, O(n²)) | line 253 |
| H-7/H-8 | High | ruff ~1,251 findings / eslint 42E+30W (pre-existing debt) | reproduced (`--statistics` / `npx eslint src`) |
| H-9 | High | 211 `.pyc` + 54 `dist/` + 8 `.bak` tracked; `.gitignore` incomplete | `git ls-files` counts verified |
| H-10 | High | `DashboardAlertsView` returns placeholder zeros | `views.py:40-68` TODO read |
| M-5 | Medium | `toggle_gst_registration` seeds GST accounts never (dead `if not org.gst_reg_number` after assignment) | body read — always False |
| M-6 | Medium | `update_organisation` `setattr` on any model attr | body read |
| M-7 | Medium | `_create_document_sequences` dead code with wrong doc types | zero callers verified |
| New (this session) | High | `transmit_peppol_invoice_task` passes log id where invoice id is expected → auto-transmit can never succeed | task + service signatures read (see above) |

Counts for this sprint's register: **4 Critical, 7 High, 3 Medium + 1 new High** (scope of execution below; the rest stays in the deferred register §9).

---

## 1. Task 1 (C-1, C-3, H-9, M-9, M-12, L-4/L-5/L-6): repo hygiene — untrack secrets & artifacts, per-run CI credential

**Fix (mechanical, no behavior change):**
1. `git rm --cached apps/backend/.env apps/web/.env.local` (working-tree files stay — they are the live dev config; `.gitignore` already lists them, so they become properly ignored).
2. `git rm --cached -r` the 211 tracked `__pycache__/*.pyc`, the 54 `apps/web/dist/` files, and the 8 `*.bak`/`*.bak2` files (`GEMINI.bak`, `apps/backend/*.bak*`, `apps/web/src/**/*.bak`, `docker/Dockerfile.bak`).
3. `.gitignore` gains: `__pycache__/`, `*.pyc`, `dist/`, `*.bak`, `*.bak2`.
4. `.github/workflows/ci.yml`: `POSTGRES_PASSWORD: ci-${{ github.run_id }}-${{ github.run_attempt }}` (per-run generated; the service container and the test job share `env.POSTGRES_PASSWORD`; nothing committed, no secrets setup needed). Also fix the pip `cache-dependency-path` to `apps/backend/pyproject.toml` (the canonical manifest since P1/A-6 — it currently points at the stale `requirements*.txt`).
5. `config/settings/testing.py`: DB block reads `config("DB_NAME"/"DB_USER"/"DB_PASSWORD"/"DB_HOST"/"DB_PORT", …)` with the current dev values as defaults (honors CI's per-run password; identical local behavior — the documented local invocation exports the same vars).

**Verification (not TDD — mechanical):** `git ls-files | rg '\.pyc$|^apps/web/dist/|\.bak'` → empty; `git ls-files | rg '\.env'` → only the three `.env.example` files; local `.env` still on disk and untracked-ignored; `manage.py check` still 0 errors; full backend suite still green (testing.py change proven by the run).

## 2. Task 2 (C-4): remove the broken `org_seed_service.py`

The module cannot be imported (`IndentationError`), has zero live callers (verified: only the schema's `core.seed_default_chart_of_accounts` function seeds the CoA, called via `organisation_service._seed_chart_of_accounts` raw SQL), and duplicates that SQL function in drifted Python. **Decision: delete the module** (dead + broken + misleading beats repaired-but-still-dead; the audit's alternative). If a future Python-side seeder is needed it should be written against the SQL function, not beside it.

**Verification:** `rg org_seed_service` → zero hits outside git history; `ruff check .` invalid-syntax count 2 → 0; suite green.

## 3. Task 3 (C-2 + new wiring bug + deferred H-08 partially): real InvoiceNow send/status + retention-safe cleanup

**Fix:**
1. **Service seam:** new `TransmissionService.execute_transmission_for_log(log_id)` — loads the log, fetches invoice/org/settings from it, runs `_execute_transmission` + `_update_log_with_result` **on the existing log** (no duplicate log). `transmit_peppol_invoice_task` calls it (fixes the log-id/invoice-id mismatch). `transmit_invoice()` stays for direct/synchronous API use.
2. **`send_invoicenow`** (`document_service.py`): keep the APPROVED + Peppol-ID validation; add org-configuration validation (`OrganisationPeppolSettings.is_configured` else `ValidationError` with a configure-first message); create the `PeppolTransmissionLog` (status PENDING, provider from settings, attempt 1); queue `transmit_peppol_invoice_task`; return the REAL log id + task id (response shape unchanged: `document_id/status/message_id?/transmission_log_id/queued_at/message` — `message_id` now `None` until the AP answers, `status="QUEUED"`).
3. **`get_invoicenow_status`**: query `PeppolTransmissionLog` for the document (latest first); return the latest log's real status + a logs array (id, status, timestamps, error); `"NOT_CONFIGURED"` when the org has no Peppol settings (truthful now, not a blanket NOT_APPLICABLE).
4. **`check_transmission_status_task`**: find the log by `peppol_message_id`; call `adapter.check_status(message_id)`; update the log from the result; return the real dict. Unfindable message → `None` (documented contract).
5. **`cleanup_old_transmission_logs_task`**: retention-safe — delete only stale **non-final** logs (`status__in=["PENDING", "TRANSMITTING", "FAILED"]` older than the horizon); **never** DELIVERED/REJECTED (IRAS 5-year retention, `database_schema.sql:1434,1473`); docstring updated to say so.

**TDD (RED first).** New `tests/peppol/test_transmission_wiring.py` (+ extend where the existing suites live):
- `execute_transmission_for_log` updates the EXISTING log (no second row) — RED today (method missing);
- `transmit_peppol_invoice_task` with a pre-created log reaches the (mocked) adapter instead of raising `ValueError: Invoice … not found` — RED today (the wiring bug);
- `send_invoicenow` on an APPROVED doc with configured settings creates a real log row + queues the task (eager Celery in tests) and returns its id — RED today (returns uuid4());
- `send_invoicenow` without org Peppol settings → ValidationError;
- `get_invoicenow_status` returns the real log rows for a document with history — RED today (always NOT_APPLICABLE);
- cleanup preserves a DELIVERED log older than the cutoff and removes a stale PENDING one — RED today (deletes the DELIVERED row).

## 4. Task 4 (H-1): `allocate()` writes `document.amount_paid`

**Fix.** In the allocation loop, after creating each `PaymentAllocation`: recompute `document.amount_paid = Σ PaymentAllocation.allocated_amount` for that document (query the allocations table, not incremental math — allocation rows are the truth), persist alongside the status transition. The dashboard's outstanding-AR filter (`amount_paid__lt=F("total_incl")`) becomes truthful. `amount_due` (GENERATED from `total_amount − amount_paid`) becomes truthful with it.

**TDD (RED first).** Extend `apps/banking/tests/test_allocation_service.py`:
- allocate S$X of a S$Y invoice → `document.amount_paid == X`, status PARTIALLY_PAID, `amount_due == Y − X` — RED today (amount_paid stays 0);
- full allocation → amount_paid == total_incl, status PAID.

## 5. Task 5 (H-2): payment `void` reverses the journal entry and releases allocations

**Fix.** In `void()`, inside the existing atomic block: (1) if `payment.journal_entry` and not already reversed → `JournalService.reverse_entry(org_id, entry.id, reversal_date=timezone.now().date(), reason=f"Payment voided: {reason}", user_id)`; (2) delete the payment's `PaymentAllocation` rows **after** recomputing each affected document's `amount_paid` (allocations released → amount_paid back to Σ remaining) and reset status to APPROVED when fully released (only from PARTIALLY_PAID/PAID); (3) keep the audit event (extend `new_data` with reversal entry id).

**TDD (RED first).** Extend `apps/banking/tests/test_payment_service.py`:
- void a RECEIVED payment with a journal entry → a REVERSAL entry exists, the original `is_reversed=True`, `reversed_by` set, reversal lines mirror debits/credits — RED today;
- void a payment allocated to an invoice → the document's `amount_paid` returns to 0 and status returns to APPROVED — RED today;
- voiding an already-voided payment still raises.

## 6. Task 6 (H-4): exact control-account resolution, fail-closed

**Fix.** Rewrite the four resolvers in `journal_service.py` as **code-exact → semantically-typed → named** lookups, each raising `ValidationError` (fail-closed, never a broad `.first()`):
- AR: `code="1200"` → `account_sub_type="ACCOUNTS_RECEIVABLE"` → `name="Accounts Receivable"` (non-header);
- AP: `code="2100"` → `account_sub_type="ACCOUNTS_PAYABLE"` → `name="Accounts Payable"`;
- GST input: `code="1600"` → `name="GST Input Tax"`; missing → ValidationError "no GST input control account — is the organisation GST-registered?";
- GST output: `code="2600"` → `name="GST Output Tax"`; same fail-closed posture.
Sub-type codes verified against `coa.account_sub_type` seeds (103 ACCOUNTS_RECEIVABLE, 202 is AP's row — verified: 202 = ACCOUNTS_PAYABLE under CURRENT_LIABILITY 201… final spelling taken from the schema at implementation time).

**TDD (RED first).** New `tests/invariants/test_control_account_resolution.py` with an org seeded via the SQL function (GST-registered) plus a decoy inventory account:
- posting a sales invoice journal debits **1200** (not 1300 Inventory, not 1010 Cash) — RED today (`.first()` can return the decoy);
- output tax credits **2600 GST Output Tax** (not 2200 Accrued Expenses) — RED today;
- a non-GST org (no 1600/2600 seeded) posting a GST-bearing line → ValidationError, no journal — RED today (silent mis-post);
- AR/AP resolution still succeeds on the standard seed.

## 7. Task 7 (H-5, H-6, + auth display fix): money quantization consistency & line numbering

**Fix.**
1. `add_line`: `line_amount = amount` (the 2dp-quantized GST base — the GST calculation base and the stored subtotal become the same number); `total_amount = (line_amount + gst_amount).quantize(Decimal("0.01"))`. Subtotal/GST/total reconcile to the cent; storage stays NUMERIC(19,4).
2. `create_entry`: `for line_number, line_data in enumerate(lines, start=1)` — duplicate line dicts get distinct numbers, O(n).
3. `auth_service.generate_tokens`: `datetime.now()` → `timezone.now()` for `access_expires` (audit §6.1; display value only, but naive datetimes leak into API responses).

**TDD (RED first).** Extend the invoicing + journal test modules:
- a line whose discount rounds (e.g. qty 3 × 33.335, 10% discount) → `line_amount` is 2dp and equals the GST base; `total_amount == line_amount + gst_amount` exactly — RED today (4dp line_amount);
- a journal entry with two IDENTICAL line dicts → line_numbers 1 and 2 (not 1 and 1) — RED today.

## 8. Task 8 (H-3, H-10): dashboard cache invalidation + real alerts

**Fix.**
1. `invalidate_dashboard_cache(org_id)` called (local imports, no cycles) at the end of: `DocumentService.approve_document` / `void_document`, `PaymentService.create_received` / `create_made` / `allocate` / `void`, `GSTReturnService.file_return`.
2. `DashboardAlertsView`: real implementation — `generate_compliance_alerts(org_id)` for `alerts`; `query_gst_threshold_status` for the threshold warning (threshold crossed vs the S$1M limit); `_get_invoice_counts` for overdue; unreconciled bank transactions count (banking model `is_reconciled=False`, non-voided); unpaid bills = outstanding PURCHASE_INVOICE count. Response shape unchanged (same keys, now truthful).

**TDD (RED first).** New `apps/reporting/tests/test_dashboard_alerts.py` + cache-invalidation assertions:
- a fixture org with one overdue APPROVED invoice → the view returns `overdue_invoices_count == 1` and a HIGH-severity alert — RED today (zeros);
- approving an invoice invalidates the cached dashboard (second `get_dashboard_data` recomputes — assert via cache-key miss or changed value) — RED today (no invalidation anywhere);
- GST threshold warning reflects `query_gst_threshold_status`.

## 9. Task 9 (M-5, M-6, M-7): organisation service truth

**Fix.**
1. `toggle_gst_registration`: capture `was_registered = org.gst_registered` BEFORE mutating; seed GST control accounts when `registered and not was_registered` (the `if not org.gst_reg_number` dead branch is removed). Un-registering keeps accounts (historical journals reference them) — documented decision.
2. `update_organisation`: explicit `UPDATABLE_ORG_FIELDS` allowlist (name, entity_type, address_*, postal_code, phone, email, gst_registered? — final list from the serializer's writable fields at implementation time); unknown keys are ignored with a logged warning (not setattr'd).
3. Delete `_create_document_sequences` (dead, wrong doc types).

**TDD (RED first).** Extend `tests/integration/test_organisation_settings.py`:
- toggle GST registration on a fresh org → 1600/2600 control accounts exist — RED today (never seeded);
- `update_organisation(org, id=…, created_at=…)` does not touch protected fields — RED today (setattr any).

## 10. Task 10 (C-5 part 1 + E-5 suite directive): real invoices list page

**Fix.** `apps/web/src/app/(dashboard)/invoices/page.tsx` becomes a server shell + client component (`invoices-client.tsx`) that uses `useInvoices(orgId)`: real rows (document_number, contact name, issue/due dates, total_incl, status badge from the real enum), loading skeleton, error banner, empty state with a "New Invoice" CTA, rows link to `/invoices/[id]`. Mock data deleted. The page is rendered inside the existing org context (the dashboard layout already supplies orgId via the org provider — verified pattern: banking/dashboard pages).

**TDD (RED first).** New `src/app/(dashboard)/invoices/__tests__/invoices-page.test.tsx` (vitest, lands through the existing `vitest.config.ts` include): renders rows from mocked `useInvoices`; empty state; error state. Plus a backend-gated e2e assertion in `apps/web/e2e/invoices.spec.ts` (extends the existing spec through `playwright.config.ts`'s chromium project): the list page renders real rows for the demo org — no financial writes.

## 11. Task 11: docs truth pass, `.env.example`, screenshots, session log, report, worklog, commit & push

1. **Root `.env.example`** re-verified against both app templates after the testing.py change (vars unchanged; the file is already truthful — confirm, adjust only if Task 1 adds a var; none planned).
2. **Docs truth pass:** README (P5 milestone block, test counts, hygiene notes), PAD v3.3.0 (metrics + InvoiceNow now real), CLAUDE.md v2.10.0 (status + component table), AGENTS.md session-11 lessons (the re-added-.env lesson: `git add -A` re-tracks ignored-but-modified files — untracked ≠ safe; the log-id/invoice-id seam lesson), ledgersg_SKILL.md v1.5.0 (debugging rows: amount_paid/void reversal/control accounts/retention cleanup; anti-pattern: untracked files get re-committed by `add -A`), DEPLOYMENT.md (CI per-run password note; InvoiceNow configure-first flow).
3. **Screenshots:** 5 new `docs/screenshots/24..28_*_session11.png` (login, dashboard, invoices list — now real data, new-invoice form, InvoiceNow status or reports) via the real user path, md5-unique, non-blank.
4. `docs/session_11.md`, `docs/REMEDIATION_2026-11-21_P5_REPORT.md` (verification ledger), `worklog.md` session-11 record.
5. Conventional commits on `main` per §12; push via `docs/ssh_git_wrapper_v3.py` with `--remote git@github.com:nordeim/ledgersg.git` per `docs/how-to-git-push-using-ssh-wrapper_SKILL.md`; key 0600 outside the repo, shredded after push.

---

## 12. Verification Gate (definition of done for the sprint)

Environment: PG :5432 (schema v1.1.0 both DBs), Redis :6379, `DB_*` env per §7 of the P4 report.

| # | Check | Expected |
|---|---|---|
| 1 | `pytest --reuse-db --no-migrations -q` | **0 failed**, 534 + ~20 new passed, 5 skipped |
| 2 | `pytest tests/invariants -q` / `pytest tests/security -q` | 20 + new control-account tests passed / 47+ passed, 3 skipped |
| 3 | `manage.py check` (testing settings) | 0 errors (1 known W001) |
| 4 | `ruff check` on touched backend files | no new findings; repo invalid-syntax = 0 |
| 5 | `cd apps/web && npm run typecheck` | 0 errors |
| 6 | `npm test` | 354 + new page tests passed, 0 failed |
| 7 | `npm run test:e2e` (no backend env) | green — gated specs skip with reasons |
| 8 | `npm run test:e2e:full` (backend + Redis) | green incl. the new list-page assertion |
| 9 | Hygiene greps | `git ls-files` shows no `.pyc`/`dist/`/`.bak`/app `.env` files; CI has no static password |
| 10 | Live InvoiceNow flow (curl/eager) | send on unconfigured org → 400 configure-first; configured org → real log row + task id |
| 11 | Accounting truth (spot) | allocate → amount_paid/amount_due correct; void → reversal entry exists; GST output lands on 2600 |
| 12 | Docs truth sweep | counts/status claims match the executed evidence; no stale "stub/placeholder" claims for fixed items |
| 13 | Screenshots | 5 new non-empty unique PNGs (hash-verified) |
| 14 | `git status` clean; commit set matches §13 | all changes committed on main |

Claims labelled **Verified** / **Reasoned** / **Assumed** in the report.

---

## 13. Commit Plan (conventional commits, single branch `main`)

1. `chore(repo): untrack secrets, bytecode, dist and .bak artifacts; per-run CI DB password (C-1/C-3/H-9)`
2. `refactor(core): remove broken dead org_seed_service module (C-4)`
3. `fix(peppol): real InvoiceNow send/status + log-id wiring fix + retention-safe cleanup (C-2)`
4. `fix(banking): allocate writes document.amount_paid; void reverses journal + releases allocations (H-1/H-2)`
5. `fix(journal): exact control-account resolution, fail-closed; line enumerate; 2dp line totals (H-4/H-5/H-6)`
6. `fix(reporting): dashboard cache invalidation + real alerts view (H-3/H-10)`
7. `fix(core): toggle_gst seeds control accounts; update_organisation allowlist; drop dead sequences (M-5/M-6/M-7)`
8. `feat(web): real invoices list page via useInvoices + page tests + e2e assertion (C-5 part 1)`
9. `docs: P5 truth pass — README/PAD/CLAUDE/AGENTS/ledgersg_SKILL/DEPLOYMENT + .env.example verification`
10. `docs(worklog): session 11 worklog, session log, P5 report + screenshots`

---

## 14. Deferred Debt Register (explicit, not silent)

Carried forward from the P4 register (`docs/REMEDIATION_PLAN_2026-11-21_P4.md` §9) unless touched here:

| Item | Status |
|---|---|
| H-02 base-currency reporting / retained earnings / BS assertion | Deferred (design work) |
| C-5 remainder: invoice detail page, ledger table, settings page, reports/quotes pages | **Deferred to P6** (this sprint ships the list page + the hook pattern) |
| M-1 audit-event coverage beyond banking (invoicing/gst/journal writers) | Deferred |
| M-10 CSRF hardening for cookie-auth endpoints (`X-Requested-With` / double-submit) | Deferred |
| M-11 static-export security headers; CSP enforcement (report-only today) | Deferred |
| M-14 Storecove `authenticate()` 404-as-valid semantics | Deferred (health-check semantics; real validation happens on send) |
| H-07 backend ruff debt (~1,251 findings) | Pre-existing; touched files stay lint-clean |
| H-08/B-6 frontend eslint debt (42E/30W incl. dist/ scope) | Pre-existing; the dist/ *tracking* is fixed this sprint, the lint-scope `globalIgnores` fix rides with it if trivially safe |
| F5 return rate-basis (computation date vs document date) | Deferred — period-cut semantics (ties into H-02) |
| A-10 stale root `requirements.txt` | Deferred (repo-owner coordination) |
| GST payment tracking (`pay_return`) | Intentionally raises until schema extension |
| Invoice form: existing-contact picker | Deferred |
| Reg-11 tax-invoice labelling, Schematron fail-closed (H-09/H-10 old register) | Deferred |

---

## 15. Open decisions resolved by this plan (recorded for the next reader)

- **Delete vs repair `org_seed_service.py`** (audit C-4 offered both): delete — it is unimportable, uncalled, and duplicates the SQL seed function that is the actual live path; repairing would resurrect dead code.
- **Cleanup task semantics** (audit: "archive, not delete, or enforce 5-year retention"): retention-safe deletion of stale non-final logs only (PENDING/TRANSMITTING/FAILED beyond the horizon); DELIVERED/REJECTED are the IRAS retention records and are never deleted by the task. Archival export is deferred (needs a storage target decision).
- **CI password**: per-run generated value, not GitHub secrets — zero committed credentials, zero owner setup, same ephemeral-DB security posture.
- **`send_invoicenow` trigger mode**: queue the Celery task (async, retry-backed — same as the auto path) rather than synchronous `transmit_invoice()`; an HTTP request must not block on an external AP. The response returns the real log id for status polling.
- **Payment-void allocation release**: voiding releases allocations and recomputes document `amount_paid`/status (a voided payment cannot remain allocated — it no longer represents money). Full unallocate() endpoint stays out of scope.
- **Non-GST org posting GST-bearing lines**: fail-closed ValidationError (no silent fallback account) — the compliance-calculations-never-guess principle (P2 lesson #17).
- **Suite directive** ("add vitest and playwright test suite by modifying the respective config files"): satisfied exactly as P4 resolved it — new tests land through the existing `vitest.config.ts` include patterns and the `playwright.config.ts` chromium project; configs are touched only where a comment/behavior genuinely changes (none planned beyond the e2e spec extension).
