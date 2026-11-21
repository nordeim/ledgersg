# LedgerSG — Remediation Plan (P3 Sprint: Monetary Capacity, Truthful Invoice Form & Suite Depth)

**Date:** 2026-11-21 (session 7)
**Base commit:** `5b237743` (main)
**Source:** this session's audit (below) + deferred-debt register of `docs/REMEDIATION_PLAN_2026-11-21_P2.md` §4 + the user's session-7 directives (extend the vitest + playwright suites; step-by-step deployment guide)
**Execution mode:** Mode B/D — TDD (RED → GREEN → REFACTOR), surgical fixes
**Plan validated against:** live codebase + PostgreSQL 17 (rootless, schema v1.0.2) + Redis 8; baselines reproduced exactly — backend `pytest` **514 passed / 0 failed / 5 skipped**, frontend `vitest` **324/324 (25 files)**, `tsc --noEmit` **0 errors**, playwright **6/6 (chromium)**; every finding below independently reproduced before planning.

**Post-writing validation (plan checked against code before execution):**
- The `amount_due` generated-column blocker is real and the workaround is verified: `ALTER TABLE invoicing.document ALTER COLUMN total_amount TYPE …` fails with `cannot alter type of a column used by a generated column`; the drop → alter → re-add-generated sequence was executed inside a transaction and rolled back cleanly on the live dev DB (precision 19 confirmed mid-transaction).
- Backend create contract confirmed: `POST /{org}/invoicing/documents/` takes `document_type`, `contact_id` (UUID), `issue_date`, `due_date?`, `reference?`, `notes?`, `lines[]` where each line needs `account_id`, `description`, `quantity`, `unit_price`, `tax_code_id`, `is_bcrs_deposit` (`apps/invoicing/serializers.py:164`, `document_service._add_lines:470`, `add_line:216`).
- `useCreateContact` exists (`src/hooks/use-contacts.ts:92`) with a payload shape compatible with the form's customer fields — the submit adapter needs no new backend surface.
- The authed-e2e mechanism is the repo's own documented hybrid pattern: `page.request.post` shares the browser context's cookie jar, so an API login seeds the HttpOnly refresh cookie and the AuthProvider's silent refresh authenticates the UI session.
- `Account.account_type` is a plain varchar (`"REVENUE"`, `"ASSET_CURRENT"`, …) — `GET /api/v1/{org}/accounts/?account_type=REVENUE` filters correctly server-side (`coa/services.py:74`), so the new `useAccounts` hook needs no client-side filtering.
- The conformance gate (`tests/invariants/test_schema_conformance.py`) checks `data_type` only — precision widening will not trip it, and the planned precision assertion extends it without breaking existing models (all non-widened columns keep their declared shapes).

---

## 0. Audit Summary (what this plan is built on)

Focus per instructions: **recent code changes** (the P2 sprint commits `23bc1487..33548dce` plus the two docs-only commits after) plus the repo-included skill-driven sweep (`skills/code-review-and-audit` standard mode scoped to `apps/` + manual verification of every scanner finding, `code-quality-standards` severity discipline, `diagnosing-bugs` root-cause loop, `e2e-testing-lessons` for the suite work).

Severity taxonomy: Critical / High / Medium / Low / Info. Counts: **1 Critical, 2 High, 1 Medium, 2 Low.**

### P2-sprint change review (recent changes — verified good)

- Rate-effectiveness rewrite (`tax_code_service.py`, `gst/views.py`, `document_service.add_line`) reviewed in source diff **and live**: `POST /gst/calculate/ {amount:100, tax_code:SR, document_date:2023-06-01}` → `rate 0.0800`; `GET /gst/tax-codes/?effective_on=2023-06-01` → exactly one SR row (0.0800). The fail-closed 404 path, `UUID(org_id)` fix and hoisted Decimal imports are all in the shipped code.
- Playwright config (chromium default + `PLAYWRIGHT_PROJECTS=all` opt-in), login a11y (`<main>` + h1 + 7.2:1 contrast), truthful web `.env.example`, typecheck gate — all re-verified green this session (see baselines above).
- The two commits after the sprint (`d6aa85a1`, `5b237743`) are docs-only (`docs/session_6.md`, `docs/sample_DEPLOYMENT.md`) — no code surface.
- Audit-runner scanner "criticals" (24 scoped to `apps/`): every one re-verified as false positive — `api-client.ts:59` is a dynamic template literal (`Bearer ${accessToken}`), `dashboard.py:31` and `ap_storecove_adapter.py:39` are docstrings, the rest are test fixtures with dummy tokens.

### Findings register

| ID | Severity | Location | Finding | Evidence |
|---|---|---|---|---|
| C-1 (= deferred H-03) | **Critical (compliance)** | `database_schema.sql` — 80 `NUMERIC(10,4)` columns across `journal.line` (debit/credit/tax_amount/base_*), `invoicing.document*` (totals, unit_price), `gst.return` (all 15 boxes), `banking.payment*`, `gst.threshold_snapshot`, `core.contact.credit_limit` | Every monetary value is capped at **S$999,999.9999** (6 integer digits). The Singapore GST registration threshold is S$1M turnover, so **every GST-registered org's F5 Box 13 (total revenue) can overflow**, as can any ≥S$1M invoice line, document total, or journal debit. The pure-calculation endpoint computes 2M fine (no persistence); the persist path raises `numeric field overflow` → 500 | Executed: `SELECT 1000000.00::NUMERIC(10,4)` → `ERROR: numeric field overflow … must round to an absolute value less than 10^6`; column census via `pg_attribute` confirms the 80-column blast radius |
| D-1 | High (broken feature) | `apps/web/src/components/invoice/invoice-form.tsx:98-118` | The New Invoice form's `onSubmit` is a **TODO stub**: `console.log` + `setTimeout` + `crypto.randomUUID()` mock — the UI never calls the API. `useCreateInvoice` (`src/hooks/use-invoices.ts:65`) is fully wired but dead code (zero importers). The backend create endpoint works (covered by backend tests) — only the form is fake | Executed: `rg useCreateInvoice src/` → definition only; form body read in full |
| D-2 | High (security + broken) | `apps/web/src/hooks/use-invoices.ts:298` | `useInvoicePDF` sends `Authorization: Bearer ${localStorage.getItem("accessToken")}` — (a) violates the repo's own zero-JWT-exposure mandate (AGENTS.md prohibited action: "NO client-side JWT storage (localStorage)"); (b) is broken anyway: the access token lives in the api-client's module memory, localStorage is never written, so every PDF download sends `Bearer null` → 401 | Executed: `rg localStorage.getItem("accessToken")` → exactly this one site; `setAccessToken` writes only the module variable |
| D-3 (= P2 deferred wiring) | Medium (correctness of preview) | `apps/web/src/components/invoice/invoice-line-row.tsx:143-167`; `apps/web/src/lib/gst-engine.ts:29-37` | The tax-code dropdown is the hardcoded `TAX_CODES` list and the client-side preview uses the hardcoded `GST_RATES` map (SR/TX/BL/RS frozen at 9%). The P2 `?effective_on=` API is ignored: a backdated document previews at today's rate, and org-custom rates are invisible to the form | Executed: component + engine read in full; P2 API verified live (2023 → 0.0800) while the engine would show 9% |
| D-4 | Low (env) | `apps/backend/.env.example` | `ALLOWED_HOSTS` is read by `config/settings/base.py:28` (via `config(...)`) but absent from the template — the file's completeness claim ("Every variable below is actually read") is true but the inverse ("every read variable is listed") is not | Executed: `rg 'config\("' config/settings/*.py` → 15 vars; template lists 14 |
| D-5 | Low (test-suite depth) | `apps/web/e2e/` (1 spec), vitest coverage | The playwright suite covers public navigation only (6 tests): zero coverage of the invoice form (which would have caught D-1 immediately), zero authenticated-flow tests. Vitest has no tests for the invoice-form submit path or any tax-code/account fetching | Executed: `ls e2e/` → `navigation.spec.ts` only |

### Verified-good (no action needed)

- All four documented baselines reproduced exactly before any change (514P/0F/5S backend; 324/324 vitest; 0 typecheck errors; 6/6 e2e).
- P2 production fixes live-verified end-to-end (see above); no follow-on defects found in the rewritten query paths.
- Rootless PG 17 (:5432, both DBs at schema v1.0.2, 30 domain tables) and Redis 8 (:6379) healthy; demo org `Lakshmi's Kitchen Pte Ltd` / `demo@ledgersg.sg` present in the dev DB.
- Both `.env.example` files otherwise truthful (web verified in P2; backend re-verified this session apart from D-4).

### Skill guidance applied

Per `skills/skills-catalog.md`: `code-review-and-audit` (audit_runner standard mode scoped to `apps/` + manual verification of all 24 scanner criticals), `code-quality-standards` (severity discipline, decision-priority ordering), `diagnosing-bugs` (each finding reproduced before planning — C-1 via live SQL, D-2 via usage census), `tdd`/`test-driven-development` (RED→GREEN per task), `e2e-testing-lessons` (green-by-default gating for backend-dependent specs, hybrid API-auth pattern), `writing-plans` + `planning-and-task-breakdown` (this document), `verification-and-review-protocol` (evidence ledger in the report), `lint-and-validate` (gate ordering), `distill-codebase-skill` + `to-distill-project-into-skill` (skill refresh in Task 7).

---

## 1. Execution Scope Decision

Goal of this sprint: **(1) monetary columns widened to `NUMERIC(19,4)` end-to-end (schema v1.1.0, models, serializers, conformance gate extended to precision) so a GST-registered org's real numbers fit; (2) the New Invoice form actually creates documents (contact → document, real payload adapter, per-line revenue account, server-effective tax codes); (3) the PDF download authorized through the api-client instead of localStorage; (4) both frontend test suites extended with real coverage (auth + invoice-form e2e specs, new hook/adapter vitest tests); (5) `ALLOWED_HOSTS` in the backend env template; (6) a complete fresh-host deployment guide.** The remaining P0/P1/P2 deferred register (H-02, H-08…H-13, M-*, L-*, I-*, B-6 eslint debt, F5 rate-basis semantics) stays deferred — re-registered in §4.

Guiding rule (Decision Priority Hierarchy): correctness & safety > security > reliability > maintainability. C-1 is a data-loss-class correctness defect (a ≥S$1M invoice 500s mid-transaction); D-2 is a security-posture violation that is also broken. Every production-code fix ships with a regression test written first.

Open decisions resolved by best judgment (per instructions):

1. **Widen to `NUMERIC(19,4)`, not `(18,4)` or `(20,4)`.** 19 total digits ⇒ max ~S$10^15 — the conventional financial-system width (matches `BIGINT`-cents headroom and Django's common `max_digits=19`), leaves 15 integer digits, and keeps the schema file's "NUMERIC(x,4) mirrors Python Decimal" invariant. `discount_pct NUMERIC(5,2)` and `exchange_rate NUMERIC(12,6)` are untouched (different semantics, different widths).
2. **Schema stays one file, version bumped to 1.1.0.** The 80 column definitions are edited in place (fresh loads get the wide types directly), and a dated in-place migration block is appended (§17) for existing deployments — including the verified drop → alter → re-add sequence for the `invoicing.document.amount_due` generated column. Both local DBs are migrated with that exact block (not by re-loading), proving the migration path works.
3. **Conformance gate extended to precision.** `DecimalField`s with declared `max_digits`/`decimal_places` now must match the live `numeric_precision`/`numeric_scale` — the class of drift C-1 represents becomes a gate failure, not a runtime 500.
4. **Invoice form: complete the flow, minimally.** A per-line revenue-account `<Select>` (populated from a new `useAccounts` hook; the backend's `add_line` contract requires `account_id`), server-driven tax codes via a new `useTaxCodes(orgId, effectiveOn)` hook (falling back to the static list when the API is unreachable — the backend-less default e2e run must stay green), and a pure `buildInvoiceSubmission()` adapter mapping form state → contact payload + document payload. The form's `invoice_number` field stays as a display/reference value; the backend's `document_sequence` remains the authority (the create serializer has no number field — documented in the adapter).
5. **Authed e2e is opt-in, green by default.** New specs that need the backend read `E2E_API_URL` and `test.skip(!E2E_API_URL, …)` when unset — same philosophy as `PLAYWRIGHT_PROJECTS=all`. A `test:e2e:full` npm script sets `E2E_API_URL=http://127.0.0.1:8000`. Login uses the repo's documented hybrid pattern (API login via `page.request` seeds the HttpOnly refresh cookie in the shared context jar; the AuthProvider's silent refresh authenticates the UI).
6. **No e2e invoice submission.** The invoice-form e2e fills the form and asserts server-driven tax codes and computed totals but does not click Create — playwright tests must not write financial rows into the developer's dev DB. Submission correctness is covered by vitest (adapter + form tests with mocked mutations).

---

## 2. Task Breakdown (ordered, vertical slices)

### Task 1 (C-1 / H-03): Widen all monetary columns to NUMERIC(19,4) — schema v1.1.0

**Problem.** 80 `NUMERIC(10,4)` columns cap every monetary value at S$999,999.9999; GST-registered orgs (threshold: S$1M turnover) overflow F5 boxes and ≥S$1M documents/lines/journal amounts raise `numeric field overflow`.

**Fix.**
1. `apps/backend/database_schema.sql`: replace all 80 `NUMERIC(10,4)` → `NUMERIC(19,4)` (header comment precision note updated; version header 1.0.2 → 1.1.0). Append **§16 MONETARY CAPACITY WIDENING (v1.1.0 — H-03 remediation)** (the last existing section is §15b): the in-place migration (`ALTER TABLE … ALTER COLUMN … TYPE NUMERIC(19,4)` for each widened column, with the `invoicing.document.amount_due` drop → alter `total_amount`/`amount_paid` → re-add generated sequence) + the verification query (assert zero `numeric(10,4)` columns remain in the 7 domain schemas).
2. Apply the §16 migration block to `ledgersg_dev` and `test_ledgersg_dev` (idempotent guard: skip if no `numeric(10,4)` columns remain).
3. Models: all `DecimalField(max_digits=10, decimal_places=4)` → `max_digits=19` (30 sites across `core/models/*`, verified by `rg`). Serializers for widened columns (banking `allocation/bank_transaction/payment`, invoicing) swept the same way.
4. `tests/invariants/test_schema_conformance.py`: for every `DecimalField` with declared `max_digits`/`decimal_places`, assert live `numeric_precision == max_digits` and `numeric_scale == decimal_places`.
5. `DocumentService.add_line`: accept and APPLY `discount_pct` (0–100) — `discount_amount = (quantity × unit_price × pct/100)` quantized to 0.0001, net `amount`/`line_amount` after discount — persisting both to the existing `document_line` columns. Validated during planning: `discount_pct`/`discount_amount` are real NOT NULL columns (`database_schema.sql:1100-1107`) with model fields (`invoice_line.py:38-44`); today `add_line` ignores the discount entirely while the client preview applies it (contract drift — resolved here server-side, the authoritative calculator).

**TDD.** New `tests/invariants/test_numeric_capacity.py` (RED first):
- create a document with a line `unit_price = "1500000.00"` (qty 1) → currently `ProgrammingError: numeric field overflow`; after: line created, `line_amount == 1500000.00`;
- approve it and assert the posted `journal.line.debit` ≥ 1,000,000 carries the amount (journal path widened too);
- introspection: `SELECT count(*) FROM information_schema.columns WHERE numeric_precision=10 AND numeric_scale=4 AND table_schema IN (7 domain schemas)` == 0, and the 15 `gst.return` box columns all report precision 19.

**Done when:** new tests green; full backend suite ≥ 514 passed (existing fixtures use sub-cap values — no behavioural change); conformance gate green with the precision assertions; `manage.py check` clean; both DBs report zero `numeric(10,4)` columns.

**Files:** `apps/backend/database_schema.sql`, `apps/core/models/*.py` (DecimalField sites), `apps/banking/serializers/*.py`, `apps/invoicing/serializers.py`, `tests/invariants/test_schema_conformance.py`, `tests/invariants/test_numeric_capacity.py` (new). **Dependencies:** none.

---

### Task 2 (D-3): Server-effective tax codes in the invoice form

**Problem.** Hardcoded `TAX_CODES` dropdown + hardcoded 9% `GST_RATES` preview ignore the P2 `?effective_on` API.

**Fix.**
1. New `src/hooks/use-tax-codes.ts`: `useTaxCodes(orgId, effectiveOn?)` → `GET /api/v1/{org}/gst/tax-codes/?effective_on={date}` ( TanStack Query; `enabled: !!orgId`); returns the resolved list `{id, code, name, rate}`; on error/loading returns nothing — callers fall back to the static list.
2. `invoice-line-row.tsx`: accept a `taxCodes` prop (resolved server list or static fallback); options render `code` with the effective rate (e.g. `SR · 9%`); the selected code's server rate is passed to the GST preview.
3. `gst-engine.ts`: `calculateLineGST` gains an optional `rateOverride?: string` parameter (defaults to the static `GST_RATES` lookup — backward compatible for all existing callers/tests); `calculateFromLines` accepts optional per-code rate overrides the same way.
4. `invoice-form.tsx`: watch `issue_date`; pass `effectiveOn=issue_date` to the hook and the resolved list + rate map down to the rows (re-fetch when the date changes).

**TDD.** RED (new `src/hooks/__tests__/use-tax-codes.test.tsx` + extended line-row/form tests):
- hook: fetch called with `?effective_on=2023-06-01`; error path → data undefined (callers fall back);
- line row: renders server option `SR · 8%` when given a resolved list with rate 0.08 and the preview computes 8% (not 9%);
- engine: `calculateLineGST("1","100","0","SR",false,"0.08")` → `gst_amount "8.0000"`.

**Done when:** new tests green; existing 324 vitest unaffected (rateOverride optional); typecheck clean.

**Files:** `src/hooks/use-tax-codes.ts` (new), `src/components/invoice/invoice-line-row.tsx`, `src/components/invoice/invoice-form.tsx`, `src/lib/gst-engine.ts`, tests (new + extended). **Dependencies:** none.

---

### Task 3 (D-1): Wire the New Invoice form to the real API

**Problem.** `onSubmit` is a stub; `useCreateInvoice` is dead code; the backend needs a per-line `account_id` and a `contact_id` the form never collects.

**Fix.**
1. New `src/hooks/use-accounts.ts`: `useAccounts(orgId)` → `GET /api/v1/{org}/accounts/` (list; caller filters revenue-side accounts by `account_type`), following the established hook pattern.
2. `invoice-form.tsx` / `invoice-line-row.tsx`: per-line **Account** `<Select>` populated from the org's revenue accounts (required; no default beyond the first account — the backend contract demands it). Layout: widen the line grid to fit one more select (adjust col-spans).
3. New `src/lib/invoice-submit.ts` — pure adapter, no React:
   - `buildContactPayload(customer)` → `{contact_type: "CUSTOMER", name, email, uen, address_line_1, is_customer: true}`;
   - `buildDocumentPayload(data, contactId)` → `{document_type: "SALES_INVOICE", contact_id, issue_date, due_date, reference, notes, lines: lines.map(({description, quantity, unit_price, discount_pct, tax_code_id, account_id, is_bcrs_deposit}) => …)}` — computed preview fields (`line_subtotal`, `gst_amount`, `line_total`, `id`) and the form-local `invoice_number` are intentionally dropped (backend `document_sequence` owns numbering; documented in the adapter docstring).
4. `invoice-form.tsx` `onSubmit`: call `useCreateContact` (only when the customer has no server id — new customers always take this path today) then `useCreateInvoice` with the adapter payloads; surface `ApiError.message` in the existing error banner; `onSuccess?.(created.id)`; remove the mock `setTimeout`/`randomUUID`.
5. `onSaveDraft`: same payload with `status` left DRAFT server-side (the create endpoint always creates DRAFT) — the button keeps working as "create draft" (it already delegates to the same path; no separate backend call exists).

**TDD.** RED (new `src/lib/__tests__/invoice-submit.test.ts` + `src/components/invoice/__tests__/invoice-form-submit.test.tsx`):
- adapter: full payload mapping (contact fields; line fields incl. `account_id` + `tax_code_id`; dropped preview fields; `SALES_INVOICE` type);
- form: submit with mocked `useCreateContact`/`useCreateInvoice` asserts both called with adapter-shaped payloads and `onSuccess` receives the created document id; error path: rejected mutation → error banner text visible; no `console.log` submission stub remains.

**Done when:** new tests green; manual smoke via the running dev servers (create a real invoice in the dev DB through the UI — also feeds Task 8's screenshots).

**Files:** `src/hooks/use-accounts.ts` (new), `src/lib/invoice-submit.ts` (new), `src/components/invoice/invoice-form.tsx`, `src/components/invoice/invoice-line-row.tsx`, tests (new). **Dependencies:** Task 2 (tax-code ids flow from the same resolved list).

---

### Task 4 (D-2): Authorize the PDF download through the api-client

**Problem.** `useInvoicePDF` reads `localStorage.getItem("accessToken")` — prohibited client-side JWT storage, and broken (the token lives in the api-client's module memory) ⇒ `Bearer null` ⇒ 401 on every download.

**Fix.**
1. `src/lib/api-client.ts`: extract the fetch + 401-refresh-retry loop of `request()` into an internal `fetchWithAuth(endpoint, options): Promise<Response>`; `request()` becomes `handleResponse(fetchWithAuth(...))`; add `api.blob(endpoint)` = `fetchWithAuth` → non-OK → `ApiError` → `response.blob()`. One auth path for everything (root cause, not a second token reader).
2. `useInvoicePDF`: use `api.blob(endpoints.invoices(orgId).pdf(id))`; delete the localStorage line. Blob + download-anchor behaviour unchanged.

**TDD.** RED (extend `src/lib/__tests__/api-client-auth.test.ts` + new hook test):
- `api.blob`: attaches `Bearer <in-memory token>`; on 401 → refresh → retry succeeds; non-OK non-401 → `ApiError` with status;
- `useInvoicePDF` source contains no `localStorage` (grep-style assertion on the module or behavioural: token comes from `setAccessToken`, not storage).

**Done when:** tests green; `rg "localStorage.getItem\(.accessToken.\)" src/` → empty.

**Files:** `src/lib/api-client.ts`, `src/hooks/use-invoices.ts`, tests. **Dependencies:** none (parallel-safe with Tasks 2-3).

---

### Task 5 (D-5 + session directive): Extend the vitest + playwright suites

**Problem/directive.** The repo's suites are configured and green (P2) but shallow: 1 e2e spec (public navigation only), no invoice-form or authenticated coverage; vitest has no submit-path tests. The session directive asks for the suites to be added/extended via the respective config files.

**Fix.**
1. New `e2e/auth.spec.ts` (always runs): login page client-side validation — empty submit shows field errors; structural assertions on the form. Gated block (`E2E_API_URL`): API login with a bad password → the form surfaces the backend error.
2. New `e2e/invoices.spec.ts` (**gated on `E2E_API_URL`**, `test.skip` otherwise with a clear reason): hybrid login (`page.request.post` → shared cookie jar → AuthProvider silent refresh) → `/invoices/new` renders → per-line Account select populated from the API → tax-code select shows the server-effective codes with rates (SR · 9% today) → fill a line → computed line total + tax breakdown update → **no submission** (no financial writes from e2e).
3. `package.json`: add `"test:e2e:full": "E2E_API_URL=http://127.0.0.1:8000 playwright test"` (documented as requiring the backend + Redis running); `test:all` unchanged (stays backend-less green).
4. Config files: `playwright.config.ts` header comment documents the `E2E_API_URL` gating (mirrors the `PLAYWRIGHT_PROJECTS` doc); `vitest.config.ts` unchanged in behaviour — its include pattern already picks up the new `__tests__` files (verified), and the coverage exclusions still apply.
5. Vitest additions ship with Tasks 2-4 (hook/engine/adapter/form/PDF tests — ~15 new tests).

**TDD / verification.** RED: the new specs fail against the pre-Task-2/3 form (no account select, static tax codes) — run once at the plan-validated state to capture; GREEN after Tasks 2-3 land. `npm run test:e2e` (no env) must stay green (gated specs skip with reasons); `npm run test:e2e:full` runs everything against the live backend.

**Done when:** `npm run test:e2e` green (6 + always-run additions); `E2E_API_URL=… npm run test:e2e` green incl. the invoice-form spec; vitest count grows; typecheck clean.

**Files:** `e2e/auth.spec.ts` (new), `e2e/invoices.spec.ts` (new), `apps/web/package.json`, `apps/web/playwright.config.ts` (comment). **Dependencies:** Tasks 2-3 (form surface).

---

### Task 6 (D-4): Backend `.env.example` completeness

**Fix.** Add `ALLOWED_HOSTS=localhost,127.0.0.1` (with a production note) to `apps/backend/.env.example`; header updated to "every variable read by the settings is listed". Verification: `rg 'config\("' config/settings/*.py` var set == template var set (15/15).

**Files:** `apps/backend/.env.example`. **Dependencies:** none.

---

### Task 7: Documentation alignment + deployment guide + skill refresh

1. **`docs/DEPLOYMENT.md` (new — session directive):** step-by-step fresh-host deployment starting from `git clone https://github.com/nordeim/ledgersg.git`, using `docs/sample_DEPLOYMENT.md` as the layout template (supported shape → prerequisites → install & configure → database installation (rootless PG primary, matching `docs/setup_pg_z.sh` + `skills/rootless-postgresql/SKILL.md`) → schema load (v1.1.0, incl. §17 in-place migration for existing DBs) → Redis → backend (venv, `pip install -e ".[dev]"`, `.env`, `manage.py check`, runserver/gunicorn) → frontend (npm, `.env.local`, dev/build:server/start) → Celery worker → verification checklist (health check, test suites) → production notes (SECRET_KEY gate, CORS, rate limiting, RLS role) → common issues (the repo's real troubleshooting rows) → updating an existing deployment. Every command verified against this codebase before writing.
2. `README.md`: P3 state (suite counts, schema v1.1.0, NUMERIC(19,4)); link `docs/DEPLOYMENT.md` in the Deployment section; testing section gains `test:e2e:full`.
3. `CLAUDE.md` → v2.8.0 status; P3 milestone block.
4. `AGENTS.md`: session-7 lessons (capacity ceilings as schema-level contracts; generated-column migration order; e2e green-by-default gating for backend-dependent specs; dead-code hooks signal unfinished wiring).
5. `ledgersg_SKILL.md` → v1.3.0 per `skills/distill-codebase-skill` + `skills/to-distill-project-into-skill`: project_state, schema v1.1.0, new anti-patterns (capacity ceiling; localStorage token; stubbed submit), new debugging rows, quick-ref additions (`use-tax-codes`, `invoice-submit`, §17 migration).
6. `docs/REMEDIATION_2026-11-21_P3_REPORT.md` (new) — verification ledger.
7. `docs/session_7.md` — session log (session_5 convention).

**Dependencies:** Tasks 1-6 complete.

---

### Task 8: Screenshots, worklog, commit & push

1. Dev servers (backend :8000 development settings, frontend `next dev`) + chromium; capture ≥ 5 new screenshots into `docs/screenshots/` following the `NN_page_sessionN.png` convention (login, dashboard, invoices list, **new-invoice form with the account + effective tax-code selects**, reports) — the invoice-form capture doubles as visual evidence for Tasks 2-3.
2. `worklog.md` (repo root): session 7 record (audit findings, remediation table, gate evidence, deferred register).
3. Conventional commits on `main` per §5; push via `docs/ssh_git_wrapper_v3.py` per `docs/how-to-git-push-using-ssh-wrapper_SKILL.md` (key deployed 0600 outside the repo, shredded after).

---

## 3. Verification Gate (definition of done for the sprint)

Environment: PG :5432 (schema **v1.1.0** in both DBs), Redis :6379, `DB_*` env per P2 report §4.

| # | Check | Expected |
|---|---|---|
| 1 | `pytest --reuse-db --no-migrations -q` | **0 failed**, 514 + ~5 new passed, 5 skipped |
| 2 | `pytest tests/invariants -q` / `pytest tests/security -q` | 16+ passed (conformance + capacity) / 32 passed, 3 skipped |
| 3 | `DJANGO_SETTINGS_MODULE=config.settings.testing python manage.py check` | 0 errors (1 known W001) |
| 4 | `information_schema` census | 0 `numeric(10,4)` columns in the 7 domain schemas; 15 gst.return boxes at precision 19 |
| 5 | `ruff check` on touched backend files | no new findings (pre-existing debt untouched) |
| 6 | `cd apps/web && npm run typecheck` | 0 errors |
| 7 | `npm test` | 324 + ~15 new passed, 0 failed |
| 8 | `npm run test:e2e` (no backend env) | green — gated specs skip with reasons |
| 9 | `npm run test:e2e:full` (backend + Redis up) | green incl. authed invoice-form spec |
| 10 | `rg "localStorage.getItem\(.accessToken.\)" src/` | empty |
| 11 | `rg useCreateInvoice src/` | ≥ 1 importer (the form) |
| 12 | `.env.example` audits | backend: settings var set == template var set; web: unchanged-still-true |
| 13 | Screenshots in `docs/screenshots/` | new non-empty unique PNGs (hash-verified) |
| 14 | `docs/DEPLOYMENT.md` | present; every command block cross-checked against the repo |

Claims labelled **Verified** / **Reasoned** / **Assumed** in the report.

---

## 4. Deferred Debt Register (explicit, not silent)

Carried forward unchanged from `docs/REMEDIATION_PLAN_2026-11-21_P2.md` §4 unless touched here:

| Item | Status |
|---|---|
| H-02 base-currency reporting / retained earnings / BS assertion | Deferred (design work) |
| H-08 wire `send-invoicenow` to real `TransmissionService` | Deferred (adapter contract) |
| H-09 (rest) Reg-11 tax-invoice labelling | Deferred |
| H-10 Schematron fail-closed validation | Deferred |
| H-11 fiscal close controls | Deferred |
| H-13 reproducible container build | Deferred |
| M-02…M-16, L-01…L-10, I-01…I-08 | Deferred per audit roadmap |
| GST payment tracking (`pay_return`) | Intentionally raises until schema extension |
| Backend repo-wide ruff debt (~1,311 findings) | Pre-existing; touched files stay lint-clean |
| B-6 frontend eslint debt (87 errors / 3,755 warnings) | Pre-existing; dedicated sprint (large-diff risk) |
| F5 return rate-basis (computation date vs document date) | Deferred — period-cut semantics decision (ties into H-02) |
| A-10 stale root `requirements.txt` | Deferred (repo-owner coordination) |
| `test_api_endpoints.py` local fixture duplication | Deferred cleanup |
| **Invoice form: contact picker over existing contacts** (Task 3 creates a contact per submission when the customer is typed new) | Registered here — backend supports contact reuse; a searchable existing-contact picker is feature work |
| **`discount_pct` / `add_line` discount semantics** | RESOLVED during plan validation — `discount_pct`/`discount_amount` are real columns; Task 1 makes `add_line` apply the discount server-side (the client preview was already correct) |
| **Dev DB has zero `coa.account` rows** (accounts are org-scoped, created by fixtures in tests, never seeded for the demo org) | The e2e invoice spec and the Task 3 manual smoke create a revenue account via the public API during setup (`POST /api/v1/{org}/accounts/`, `account_type=REVENUE`) — exercising the real code path, no direct SQL |

---

## 5. Commit Plan (conventional commits, single branch `main`)

1. `fix(db): widen 80 monetary columns to NUMERIC(19,4) — schema v1.1.0, in-place migration §17 (C-1/H-03)`
2. `feat(web): server-effective tax codes in invoice form — useTaxCodes + rateOverride (D-3)`
3. `feat(web): wire New Invoice form to real API — accounts select, contact+document adapter (D-1)`
4. `fix(web): authorize PDF download via api-client blob — no localStorage token (D-2)`
5. `test(web): auth + invoice-form e2e specs (E2E_API_URL-gated), test:e2e:full (D-5)`
6. `chore(env): backend .env.example completeness — ALLOWED_HOSTS (D-4)`
7. `docs: deployment guide; align README/CLAUDE/AGENTS; refresh ledgersg_SKILL.md (P3)`
8. `docs(worklog): session 7 worklog, session log and screenshots`
