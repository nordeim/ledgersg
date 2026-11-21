# LedgerSG — Remediation Plan (P6 Sprint: C-5 Completion & Payment Posting Integrity — Real Detail/Ledger/Settings Pages, Exact Payment Control Accounts, Org Address Truth)

- **Date:** 2026-11-22
- **Branch:** `main` only (per repo convention)
- **Inputs:** post-P5 audit of the session-11 state (all findings re-verified against the
  working tree with line numbers before this plan was written), P5 deferred-debt register
  (`docs/REMEDIATION_PLAN_2026-11-21_P5.md` §14), and the P5 report baselines.
- **Method:** TDD (RED → GREEN → full gate), lint parity on touched files, conventional
  commits, `skills/` excluded from all checks/tests/compilation.

---

## 0. Audit Summary (what this plan is built on)

P5 shipped repo hygiene, real InvoiceNow, accounting-integrity fixes (H-1/H-2/H-4), and the
real invoices **list** page. The post-P5 audit re-examined the P5 diffs and the remaining
surface, and found the register below. Four production-code "criticals" from the scanner
were manually verified as false positives (docstrings, endpoint paths, comments) — the same
documented FP classes as P5. The 114 raw "critical" hits all fall in the excluded
`skills/` tree, test fixtures, or dev-environment credentials, as documented in P5 §0.

| ID | Severity | Location | Finding (Verified) |
|---|---|---|---|
| F-4 | High | `apps/banking/services/payment_service.py:463` | `allocate()` rejects any document not `APPROVED` — a `PARTIALLY_PAID` document can never receive its second allocation. P5/H-1 deliberately made `PARTIALLY_PAID` a persisted state, but the guard was never widened, so the state is a dead end. |
| F-5 | High | `payment_service.py:620-623, 651-654` | `_create_payment_journal_entry` control-account fallback broad-matches `Q(account_type="ASSET")` / `Q(account_type="LIABILITY")` with unordered `.first()` — the exact defect class P5/H-4 eliminated in `journal_service` (AR could land on any asset, e.g. 1010 Cash on Hand; AP on the 2000 header). Nondeterministic GL posting on a compliance path. |
| F-6 | High | `apps/invoicing/services/contact_service.py:82-165` | `create_contact` never sets `receivable_account`/`payable_account`, so **every** payment JE for an API-created contact goes through the F-5 fallback (bank-account field exists but is only set by the SQL seed path). |
| F-7 | Medium | `payment_service.py:537-585` | `unallocate()` deletes the allocation but does not recompute `document.amount_paid` (P5/H-1 covered `allocate`/`void` only) — the outstanding-AR dashboard filters and the `amount_due` generated column then read a stale `amount_paid`. It also only restores `APPROVED` at exactly zero, leaving a stale `PARTIALLY_PAID`/`PAID` status at 0 < remaining < threshold — actually it resets status only when total == 0; intermediate states are never recomputed. |
| F-10 | High | `apps/core/views/organisations.py:104-115`, `apps/core/services/organisation_service.py:282` | Both organisation-update allowlists forward a phantom `address` key that the `Organisation` model does not have (it is silently dropped by `update_organisation`), while the real model fields `address_line_1/2, city, postal_code, country` are filtered out — **an organisation address can never be updated through the API**. The `OrganisationSerializer` already exposes the real fields. |
| F-11 | Medium | `apps/invoicing/serializers.py:131-163` | `InvoiceDocumentDetailSerializer` omits `amount_paid`/`amount_due` — the detail page cannot show payment state even though the model persists `amount_paid` (P5/H-1) and the DB exposes `amount_due` as a generated column. |
| C-5 | Medium (carry-over) | `apps/web/src/app/(dashboard)/invoices/[id]/`, `ledger/`, `settings/` | The three pages deferred in P5 §14 still render hardcoded mocks: `mockInvoice` (detail), `mockData` (ledger table), `defaultValue="Demo Company Pte Ltd"` etc. (settings). |
| E-1 | Medium (discovered during this sprint's e2e bring-up) | `apps/core/views/auth.py` refresh decorator; `config/settings/development.py` | The full e2e suite's ~37 refresh calls exceed the hardcoded refresh throttle and the DRF anonymous budget (20/min) — the documented `e2e:full` gate cannot run against development settings without flaky 429s. Needs P4-style settings knobs (not env-only), mirroring `testing.py`. |
| D-1 | Low | `apps/web/src/app/(dashboard)/invoices/[id]/page.tsx` | Page component reads `params` synchronously (`{ params }: { params: { id: string } }`). In this Next.js version route `params` is a Promise — the sync read works only by accident of the current build and breaks the RSC data flow during screenshot capture. Fix: `await params`. |

De-escalated (recorded, no action): the SQL seed does not populate `account_type` (8 top-level
types), so the F-5 broad `Q()` today resolves only via its `code=` arm — the defect is latent
fragility plus nondeterminism-on-any-tie, not a live misposting today. The fix (F-5) removes
the class entirely, so no separate ticket is carried.

---

## 1. Task 1 (F-4): allow second allocations on PARTIALLY_PAID

`allocate()` guard widens from `status != "APPROVED"` to `status not in ("APPROVED",
"PARTIALLY_PAID")`. `DRAFT`/`VOID`/`PAID`/`OVERDUE`… remain rejected. RED tests:
second allocation on a `PARTIALLY_PAID` document succeeds and flips status by the
recomputed total; allocation against a `PAID` document still raises.

## 2. Task 2 (F-5, F-6, F-7): payment posting truth

1. **F-5:** `_create_payment_journal_entry` stops broad-matching. When
   `contact.receivable_account` / `payable_account` is unset it resolves the org control
   account exactly via `JournalService._get_ar_account()` / `_get_ap_account()` (P5/H-4
   resolver: exact code → exact name → sub-type code, headers excluded, fail-closed).
   The local `Q(account_type=…)` blocks are deleted.
2. **F-6:** `create_contact` assigns default control accounts at creation
   (`_get_ar_account` for customers, `_get_ap_account` for suppliers, `BOTH` gets both),
   so the normal path never depends on the fallback.
3. **F-7:** `unallocate()` recomputes `document.amount_paid` from the surviving
   allocations and derives the status (`PAID` / `PARTIALLY_PAID` / `APPROVED`) instead of
   only resetting at exactly zero.

RED tests (new file `apps/banking/tests/test_payment_posting_p6.py`, integration-style
fixtures mirroring the P5 payment tests): decoy asset/liability accounts prove the old
broad match picked a wrong account; fail-closed case renames code AND name so the fixed
resolver cannot name-match by luck; `amount_due` (generated column, not a model field)
asserted via raw SQL; unallocate leaves `amount_paid` consistent. The two pre-existing
`test_views.py` fixtures that silently depended on the F-5 fallback (customer without
`receivable_account`, org without 1200 — AR was silently posted to the 1100 bank account)
are corrected to the real contract.

## 3. Task 3 (F-10): organisation update allowlist truth

Both allowlists (`organisations.py` view, `organisation_service.py`) replace `"address"`
with `"address_line_1", "address_line_2", "city", "postal_code", "country"` (fields the
model and `OrganisationSerializer` actually carry). RED tests: PATCH with the real fields
round-trips; PATCH with the phantom `address` key changes nothing.

## 4. Task 4 (F-11 + C-5 detail): invoice detail truth end-to-end

Backend: `InvoiceDocumentDetailSerializer` gains `amount_paid` (model field) and
`amount_due` (`SerializerMethodField` — the DB column is generated, the model does not
declare it). Tests in `tests/integration/` (root-conftest fixtures are app-test-reachable
only there — documented P5 trap).

Frontend: new `InvoiceDetail` type in `hooks/use-invoices.ts` typed to the real detail
serializer; full rewrite of `invoices/[id]/invoice-detail-client.tsx` replacing
`mockInvoice` (status timeline from real `status_history` source data, lines table,
totals incl. amount paid/due, approve/void/send actions via the existing mutation hooks);
`page.tsx` switches to `await params` (D-1) and drops `generateStaticParams` demo IDs.
Vitest page tests + a gated e2e assertion (same pattern as the P5 list-page spec).

## 5. Task 5 (C-5 ledger): real general-ledger page

Backend: `GET /api/v1/organisations/{org_id}/journal/ledger/` returning flat line-level
rows (entry number/date, source type, reference, narration, account code/name, debit,
credit, description) with date filters and pagination — the list serializer's aggregated
shape cannot drive the line-level table. RED integration test for shape + org scoping.

Frontend: `useLedger` hook + props-driven rewrite of `components/ledger/ledger-table.tsx`
(drop `mockData`), page wiring, hook + component tests (auth-provider mock), gated e2e.

## 6. Task 6 (C-5 settings): real organisation settings page

Frontend only — the backend already exposes `GET/PATCH organisations/{id}/` and
`POST/DELETE organisations/{id}/gst/` (GSTRegistrationView). New `useOrganisation` hook
(query + update mutation + GST register/deregister mutations, cache-invalidating), and a
`settings-client.tsx` replacing the hardcoded `defaultValue` cards with controlled inputs
over the real organisation (Company / UEN / address / contact / GST registration card with
register/deregister). Page + hook tests (name vs legal_name distinct fixtures), gated e2e.

## 7. Task 7 (E-1): development rate-limit budgets as settings knobs

P4 pattern (`tests/security/test_settings_gates.py`): the refresh endpoint's hardcoded
throttle and the DRF anonymous/user budgets become settings-derived
(`REST_AUTH["TOKEN_REFRESH_THROTTLE_RATE"]` honoured by the decorator; development raises
both budgets; testing keeps them off). Not env-only — the decorator reads settings at
import, and env-prefix inheritance proved unreliable. RED gate tests first (posture
assertions), then the four-file change.

## 8. Task 8: docs truth pass, `.env.example`, screenshots, session log, report, worklog

- README / `Project_Architecture_Document.md` / `ledgersg_SKILL.md` / AGENTS.md updates:
  P6 milestone module, new endpoints, C-5 remainder closed, AGENTS `NUMERIC(10,4)` stale
  claim corrected to the real precision (`NUMERIC(19,4)` money columns / `NUMERIC(12,6)`
  rates, per `apps/core/models/*.py`).
- `.env.example` re-verified against the codebase (P6 adds no new env vars — the E-1 knobs
  are settings, not env).
- Screenshots of the remediated pages (login, dashboard, invoices list, invoice detail,
  ledger, settings) into `docs/screenshots/` via the real UI login path.
- `docs/REMEDIATION_2026-11-22_P6_REPORT.md`, `docs/session_13.md`, `worklog.md`.

---

## 9. Verification Gate (definition of done for the sprint)

| # | Gate | Expected |
|---|---|---|
| 1 | `pytest --reuse-db --no-migrations` | all green (567 baseline + new tests, 0 failed) |
| 2 | `npm run typecheck` / `npm run lint` (touched files) / `npm test` | clean / parity / all green |
| 3 | `npm run test:e2e` (no backend) | green, new specs gated with reasons |
| 4 | `npm run test:e2e:full` (live backend + Redis + seeded dev DB) | 20/20 green incl. detail/ledger/settings specs |
| 5 | Accounting spot checks | allocation on PARTIALLY_PAID flips status correctly; unallocate recomputes; payment JE AR/AP land on 1200/2100 exactly, fail-closed without them |
| 6 | Org PATCH | real address fields round-trip via API; phantom key is a no-op |
| 7 | Screenshots | 6 new non-empty unique PNGs (content-verified, not loading spinners) |
| 8 | Docs sweep | no stale claims for P6-fixed items; AGENTS precision claim matches models |
| 9 | `git status` clean; commit set matches §10 | all on `main` |

## 10. Commit Plan (conventional commits, single branch `main`)

1. `fix(banking): allocate allows second allocations on PARTIALLY_PAID docs (P6/F-4)`
2. `fix(banking): exact payment control accounts, fail-closed; contact defaults; unallocate recomputes amount_paid (P6/F-5/F-6/F-7)`
3. `fix(core): organisation update allowlist forwards real address fields (P6/F-10)`
4. `feat(invoicing): detail serializer exposes amount_paid/amount_due (P6/F-11)`
5. `feat(web): real invoice detail page via useInvoice + amount tracking (P6/C-5)`
6. `feat(web): real general-ledger page via journal ledger endpoint (P6/C-5)`
7. `feat(web): real organisation settings page + GST registration wiring (P6/C-5)`
8. `feat(core): settings-derived refresh/auth throttle budgets for development (P6/E-1)`
9. `docs: P6 truth pass — README/PAD/ledgersg_SKILL/AGENTS precision + .env.example verification`
10. `docs(worklog): session 12 worklog, session log, P6 report + screenshots`

(1+2 may fold into one commit if they land in the same RED→GREEN cycle; the split is
preferred for reviewability.)

## 11. Deferred Debt Register (explicit, not silent)

Carried forward from P5 §14 unless touched here: H-02 base-currency reporting/retained
earnings; M-1 audit-event coverage beyond banking; M-10 CSRF hardening for cookie-auth
endpoints; M-11 static-export security headers/CSP enforcement; M-14 Storecove
authenticate semantics; H-07 backend ruff debt (touched files stay clean); frontend
eslint debt (touched files stay parity); F5 GST return rate-basis; A-10 stale root
`requirements.txt`; GST payment tracking (`pay_return`); invoice form existing-contact
picker; Reg-11 tax-invoice labelling/Schematron. New: none (the de-escalated
`account_type` seed gap is closed by F-5's fail-closed resolver; populating the column
in the SQL seed remains optional hardening, deferred).

## 12. Open decisions resolved by this plan

- **F-5 fallback shape:** reuse `JournalService._get_ar_account/_get_ap_account`
  (single source of truth for control-account resolution) rather than duplicating a
  resolver in `payment_service` — the fix is at the seam.
- **F-6 assignment policy:** control accounts are assigned at contact creation from the
  org's seeded chart (1200/2100). No per-contact override UI this sprint (the FK fields
  remain editable by admins through the model).
- **F-7 status derivation in unallocate:** mirror `allocate()`'s threshold logic
  (`>= total_incl` → PAID, `> 0` → PARTIALLY_PAID, else APPROVED).
- **Ledger endpoint shape:** a dedicated flat-lines endpoint (`journal/ledger/`) instead
  of fattening `JournalEntryListSerializer` with nested lines — the list serializer is
  consumed elsewhere; additive, non-breaking.
- **E-1 knob placement:** settings (base defaults + development/testing overrides), not
  env — the decorator evaluates at import time and the env-prefix route proved unreliable
  during bring-up; testing.py keeps limits off exactly as today.
- **D-1 params:** `await params` + drop `generateStaticParams` demo IDs (the page is
  client-driven; the static params were mock-era scaffolding).
