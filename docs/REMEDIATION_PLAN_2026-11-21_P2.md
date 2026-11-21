# LedgerSG — Remediation Plan (P2 Sprint: Test Gates & Rate-Effectiveness Truth)

**Date:** 2026-11-21 (session 5)
**Base commit:** `4acece81` (main)
**Source:** this session's audit (below) + deferred-debt register of `docs/REMEDIATION_PLAN_2026-11-21_P1.md` §4
**Execution mode:** Mode B/D — TDD (RED → GREEN → REFACTOR), surgical fixes
**Plan validated against:** live codebase + PostgreSQL 17 (rootless, schema v1.0.2) + Redis 8; baselines reproduced exactly — backend `pytest` **499 passed / 0 failed / 5 skipped**, frontend `vitest` **321/321 (24 files)**; every finding below independently reproduced before planning.

**Post-writing validation (plan checked against code before execution):**
- `ResourceNotFound → 404` mapping confirmed in `common/views.py:51` (wrap_response) — Task 4's fail-closed path needs no new plumbing.
- `TaxCodeCreateSerializer` declares `f5_supply_box`/`f5_purchase_box`/`f5_tax_box` (no `box_mapping`) — Task 3 also passes the f5_* fields through to `create_tax_code` (they are validated by the serializer, accepted by the service, and currently silently dropped).
- `DocumentService._add_lines` (used by `create_document`) delegates to `add_line` — the Task 4 effectiveness check covers both the single-line endpoint and document creation in one place.
- Fixture compatibility: `tests/conftest.py` `test_tax_codes` sets `effective_from=2024-01-01`, no `effective_to`; every line-creating test uses `issue_date` ≥ `2024-01-15` or `date.today()` → the new `add_line` validation breaks no existing test (checked `test_invoice_workflow.py`, `test_api_endpoints.py`, integration suites — no other `add_line`/`lines=[` document callers).
- No existing vitest test covers the login page (Task 2's change breaks nothing); `CardTitle` renders `<h3>` (`src/components/ui/card.tsx:31-44`).
- No existing test exercises the `tax_code`/`tax_code_id` path of `gst/calculate/` (all use `rate`) — Task 4's serializer/view changes are additive.

---

## 0. Audit Summary (what this plan is built on)

Focus per instructions: **recent code changes** (the P1 sprint commits `7e3a835f..be3fefee`) plus the repo-included skill-driven sweep (`skills/code-review-and-audit` standard mode + manual verification of every scanner finding, `code-quality-standards` severity discipline, `diagnosing-bugs` root-cause loop, `e2e-testing-lessons`/`browser-testing-with-devtools` for the test-suite work).

Severity taxonomy: Critical / High / Medium / Low / Info. Counts: **0 Critical, 3 High, 3 Medium, 2 Low.**

### P1-sprint change review (recent changes — verified good)

- `fix(coa)` trial balance rewrite: aggregates `journal.line` ⋈ `journal.entry`, honours `fiscal_year_id` — reviewed, correct; invariant tests cover it.
- `fix(invoicing)` document summary + status transitions: `DOCUMENT_TYPES`, `PARTIALLY_PAID` set, `total_incl`, Decimal-safe empty sums — reviewed, correct; regression tests exist.
- `build(pyproject)` + env hygiene + schema header: verified (clean-venv install path reproduced in session 3; `.env` files untracked).
- Scanner "criticals" (21) — same set as session 3; the two production-code hits re-verified as docstring false positives (`dashboard.py:31` auth docstring, `ap_storecove_adapter.py:39` example credentials).

### Findings register

| ID | Severity | Location | Finding | Evidence |
|---|---|---|---|---|
| B-1 | High (test-infra) | `apps/web/playwright.config.ts:55-81` | Config declares 5 browser projects (chromium, firefox, webkit, Mobile Chrome, Mobile Safari) but only chromium is installed in this environment → `npm run test:e2e` fails wholesale: 24 of 30 tests error `Executable doesn't exist` before any page loads. Single `html` reporter gives no terminal summary | Executed: `npx playwright test --reporter=list` → only the 6 chromium tests even launch |
| B-2 | Medium (a11y) | `apps/web/src/app/(auth)/login/page.tsx:66-80` | Login page (what `/` actually renders, via `/` → `/dashboard` → auth-guard redirect) fails the repo's own axe e2e test: no `<main>` landmark, no `<h1>` (the brand title renders inside `CardTitle` = `<h3>`). Contradicts the "WCAG AAA" claim in CLAUDE.md | Executed: axe scan → `landmark-one-main` + `page-has-heading-one` (both moderate); 1 of 6 chromium e2e RED |
| B-3 (= deferred H-04) | High (compliance) | `apps/gst/services/tax_code_service.py:141-150,102-130`; `apps/gst/views.py:200-213`; `apps/invoicing/services/document_service.py:265-287` | GST rate-history resolution is broken end-to-end: (a) `get_tax_code_by_code()` does unordered `.first()` over history rows — **verified returning rate 0.0700 for SR today** (should be 0.0900; rows: 0.07→2022-12-31, 0.08→2023-12-31, 0.09→2024-01-01); (b) `list_tax_codes()` returns all 3 SR rows unordered (UI dropdown would show 3 "SR" entries); (c) `GSTCalculateView` silently falls back to `Decimal("0.09")` when the code is unknown (fail-open on a compliance calculation) and its `tax_code_id` field actually expects a code (comment admits it); (d) `add_line()` never validates that the passed tax code is effective on the document's date → stale-rate lines can be snapshotted | Executed: Django shell — service returns 0.0700/2007-row for SR; SQL query on live DB shows the 3 history rows |
| B-4 | Medium (env/docs) | `apps/web/.env.example` | 7 of 9 documented variables are read **nowhere** in the code (`NEXT_PUBLIC_ENABLE_BCRS/PEPPOL/REACT_QUERY_DEVTOOLS`, `NEXT_PUBLIC_IRAS_API_URL`, `NEXT_PUBLIC_LOG_LEVEL`, `NEXT_PUBLIC_PEPPOL_API_URL`, `NEXT_PUBLIC_TOKEN_REFRESH_INTERVAL`); header falsely claims "Every variable below is actually read by the codebase"; `BACKEND_URL` (read by `src/lib/server/api-client.ts:14`) is missing | Executed: per-var `rg` over `src/` + `next.config.ts` → zero hits for the 7; 1 hit for BACKEND_URL |
| B-5 | Medium (gates) | `apps/web` (no `typecheck` script; test files) | `tsc --noEmit` is RED with **25 pre-existing errors in test files** (Jest-style `global.jest.Mock` typings where vitest is the runner, un-imported `beforeEach`, fixture objects missing required schema fields). Runtime passes because vitest injects globals — the type gate silently drifted | Executed: `npx tsc --noEmit` → 25 errors across `src/app/(dashboard)/banking/__tests__/*`, `src/hooks/__tests__/use-banking.test.tsx`, `src/lib/__tests__/gst-engine.test.ts`, `src/shared/schemas/__tests__/bank-account.test.ts` |
| B-6 | Low (lint debt) | `apps/web` repo-wide | eslint reports 87 errors / 3,755 warnings (pre-existing, mostly warnings) | Executed: `npm run lint` tail |
| B-7 | High (broken feature) | `apps/gst/views.py:80-87` (`TaxCodeListCreateView.post`) | Creating a custom tax code via `POST /{org}/gst/tax-codes/` **always 500s**: the view passes `box_mapping=...` into `create_tax_code(**kwargs)` → `TaxCode.objects.create(box_mapping=...)` → `TypeError: TaxCode() got unexpected keyword arguments: 'box_mapping'` (the model has `f5_supply_box`/`f5_purchase_box`/`f5_tax_box`, and the serializer has no `box_mapping` field, so the value is always None but still passed through) | Executed: direct service call reproduces the TypeError |

### Verified-good (no action needed)

- Backend suite fully green (499P/0F/5S) and frontend vitest 321/321 — both reproduced this session before any change.
- P1 production fixes (A-2/A-3/A-4) reviewed in source and covered by their regression tests; no follow-on defects found in the rewritten queries.
- `chromium` + `chromium_headless_shell` v1208 now installed to match `@playwright/test` 1.58.2 (previous sessions worked around a 1200/1208 mismatch by pinning the executable path) — the standard `npx playwright test` launch path works again.
- Backend `.env.example` verified against `config("…")` reads — every listed variable is real.

### Skill guidance applied

Per `skills/skills-catalog.md`: `code-review-and-audit` (audit_runner standard mode + manual verification), `code-quality-standards` (severity discipline, gate-keeping), `diagnosing-bugs` (root-cause before fix — each B-3 sub-defect reproduced), `tdd`/`test-driven-development` (RED→GREEN per task), `e2e-testing-lessons` + `browser-testing-with-devtools` (playwright project/browser availability, headless-shell lesson), `writing-plans` + `planning-and-task-breakdown` (this document), `verification-and-review-protocol` (evidence ledger in the report), `lint-and-validate` (gate ordering: lint → typecheck → test).

---

## 1. Execution Scope Decision

Goal of this sprint: **(1) both frontend test suites (`vitest` unit + `playwright` e2e) configured to run green end-to-end from the documented commands; (2) GST rate-effectiveness resolved by date everywhere a rate is picked (fail-closed); (3) custom tax-code creation working; (4) the web typecheck gate green; (5) env template truthful.** The remaining P0/P1 deferred register (H-02/H-03/H-08…H-13, M-*, L-*, I-*) stays deferred — re-registered in §4.

Guiding rule (Decision Priority Hierarchy): correctness & safety > security > reliability > maintainability. A silent 9% fallback on a compliance calculation and a stale-rate snapshot are correctness defects — fixed fail-closed. Every production-code fix ships with a regression test written first.

Open decisions resolved by best judgment (per instructions):

1. **Playwright default projects = chromium only.** The environment (and any minimal CI runner) has chromium; firefox/webkit/mobile become opt-in via `PLAYWRIGHT_PROJECTS=all` so `npm run test:e2e` is green by default instead of red by default. Mobile coverage is preserved in the responsive tests via `setViewportSize` (already in `navigation.spec.ts`), so no coverage is lost by default.
2. **`get_tax_code_by_code` gains an optional `as_of: date | None`** (default `None` → resolve for *today*) rather than changing existing callers' signatures — additive, backward compatible. Resolution rule: org-specific row preferred over system row; within that, rows with `effective_from <= as_of` and (`effective_to` null or `>= as_of`), latest `effective_from` wins.
3. **`add_line` fails closed** with a `ValidationError` naming the code and the document date when the passed tax code is not effective on `document.issue_date` — rather than silently re-resolving (silent re-resolution would change the user's explicit code choice; a loud error is auditable).
4. **`GSTCalculateView` unknown code → 404** (`ResourceNotFound`, the service layer's existing exception → mapped by the existing exception handling) instead of the silent `Decimal("0.09")` fallback; a wrong-rate fallback on a compliance endpoint is the worse evil. The `tax_code_id`-actually-a-code confusion is resolved additively: accept `tax_code` (string) as the canonical field, keep `tax_code_id` as a deprecated alias reading into the same path (no consumer breakage), and accept optional `document_date` for rate resolution.
5. **Typecheck gate**: fix the 25 errors properly (imports + fixtures), not by excluding test files from tsconfig — hiding test types would weaken the gate. A `typecheck` npm script is added and wired into `test:all`.
6. **Web `.env.example`** lists exactly what the code reads (plus commented optional-next-steps for the flags that are not yet wired, clearly marked as not-yet-read) — a template must not lie.

---

## 2. Task Breakdown (ordered, vertical slices)

### Task 1 (B-1): Playwright config — green-by-default e2e suite

**Problem.** 5 declared projects, 1 installed browser → `npm run test:e2e` errors on 24/30 tests before any assertion; single `html` reporter gives no terminal summary.

**Fix** (`apps/web/playwright.config.ts`):
1. `projects`: default `[chromium]`; when `process.env.PLAYWRIGHT_PROJECTS === "all"`, the full set (firefox, webkit, Mobile Chrome, Mobile Safari) is included. Comment documents the opt-in and the `npx playwright install` prerequisite.
2. `reporter`: `[["list"], ["html", { open: "never" }]]` — terminal summary always; HTML report written without trying to open a browser.
3. Add `outputDir: "./test-results"` (explicit) and `snapshotDir` untouched (no snapshots in repo).
4. `webServer` unchanged (`npm run dev`, `reuseExistingServer: !CI`, 120 s) — verified working this session.

**TDD / verification.** RED (already captured): `npm run test:e2e` → 24 errors. GREEN: `npm run test:e2e` runs the chromium suite to completion (the axe failure is Task 2's RED, expected to remain); `PLAYWRIGHT_PROJECTS=all npx playwright test --list` lists all 5 projects without launching them.

**Done when:** `npm run test:e2e` completes with only genuine test failures (not browser-launch errors), and the project list is env-gated.

**Files:** `apps/web/playwright.config.ts`. **Dependencies:** none.

---

### Task 2 (B-2): Login-page landmarks (a11y)

**Problem.** Login page renders inside a bare `<div>`; the only heading is an `<h3>` (CardTitle). axe: `landmark-one-main`, `page-has-heading-one` — the repo's own e2e a11y test is RED.

**Fix** (`apps/web/src/app/(auth)/login/page.tsx`):
1. Outer `<div className="min-h-screen …">` → `<main className="min-h-screen …">`.
2. Replace the `CardTitle` brand block with an explicit `<h1 className="font-display text-2xl text-text-primary">LEDGER<span className="text-accent-primary">SG</span></h1>` (same visual classes — `CardTitle` is only an `<h3>` wrapper, verified in `src/components/ui/card.tsx:31-44`). Single h1, no skipped levels, brand stays the visual heading.

**TDD.**
- RED (vitest, new `src/app/(auth)/login/__tests__/login-a11y.test.tsx`): render `<LoginPage />`; assert `screen.getByRole("main")` exists and `screen.getAllByRole("heading", { level: 1 })` has exactly one entry whose text matches /LEDGERSG/.
- GREEN: implement; vitest green; then the e2e axe test (`npx playwright test -g accessibility`) goes green — that e2e test is the second, independent RED→GREEN pair.

**Done when:** new vitest test passes; `npx playwright test --project=chromium` → 6/6.

**Files:** `apps/web/src/app/(auth)/login/page.tsx`, `src/app/(auth)/login/__tests__/login-a11y.test.tsx` (new). **Dependencies:** none.

---

### Task 3 (B-7): Custom tax-code creation un-broken

**Problem.** `TaxCodeListCreateView.post` passes `box_mapping=…` into `create_tax_code(**kwargs)` → `TaxCode.objects.create(box_mapping=None)` → `TypeError` → 500 on every custom-code create.

**Fix** (`apps/gst/views.py`): drop the `box_mapping=data.get("box_mapping") or None` argument entirely (the serializer never had the field; the model never will — box mapping lives in `f5_*` columns). Pass the serializer's validated `f5_supply_box`/`f5_purchase_box`/`f5_tax_box` through to `create_tax_code` instead (currently silently dropped despite being declared fields). Nothing else consumes `box_mapping`.

**TDD.** RED (new `tests/integration/test_tax_code_create.py`): authenticated `POST /api/v1/{org}/gst/tax-codes/` with a valid payload (`code= "SVC7"`, name, rate 0.07, `is_gst_charged=true`) → currently 500; assert `status_code == 201` and the response echoes code/rate. GREEN: remove the kwarg; test passes; re-run the full gst test subset.

**Done when:** POST returns 201; `rg -n "box_mapping" apps/gst/views.py` → no hits.

**Files:** `apps/gst/views.py`, `tests/integration/test_tax_code_create.py` (new). **Dependencies:** none.

---

### Task 4 (B-3 / H-04): Rate-effectiveness by date, fail-closed

**Problem.** Four cooperating defects (register row B-3): unordered `.first()` over rate history (verified 0.07 for SR today), unordered history in the list endpoint, silent 9% fallback + code/id confusion in the calculate view, no effectiveness check in `add_line`.

**Fix.**

1. `TaxCodeService.get_tax_code_by_code(org_id, code, as_of=None)` (`apps/gst/services/tax_code_service.py`):
   - `as_of = as_of or date.today()`;
   - candidate rows: `code` match, `org_id=org_id` **or** `org_id IS NULL`, `is_active=True`, `deleted_at IS NULL`;
   - effectiveness window: `(effective_from IS NULL OR effective_from <= as_of) AND (effective_to IS NULL OR effective_to >= as_of)`;
   - ordering: org-specific rows first (`org_id` nulls last), then `effective_from DESC` (nulls last);
   - `.first()` on that ordering → the row in force on `as_of`. Returns `None` when nothing is in force (callers decide).
2. `TaxCodeService.list_tax_codes(...)`: add optional `effective_on: date | None = None`; when set, apply the same effectiveness window; always append `.order_by("code", "-effective_from")` (newest rate first within a code — deterministic dropdowns).
3. `TaxCodeListCreateView.get` (`apps/gst/views.py`): accept optional `effective_on` query param (ISO date) and pass through. Additive — no existing consumer sends it.
4. `GSTCalculateView.post`: read tax code from `data.get("tax_code") or data.get("tax_code_id")` (both are treated as the code string — documented in the serializer help text); optional `document_date` (ISO date) → `as_of`; unknown code → raise `ResourceNotFound` (no more silent 9%); known code → resolved rate from the effective row.
5. `GSTCalculationRequestSerializer`: add optional `tax_code` (CharField) and `document_date` (DateField) fields; keep `tax_code_id` for backward compatibility.
6. `DocumentService.add_line` (`apps/invoicing/services/document_service.py`): after fetching the tax code, validate effectiveness on `document.issue_date` (the model field mapping to the `document_date` column, verified in `apps/core/models/invoice_document.py:50`): if `not effective_on(tax_code, document.issue_date)` → `ValidationError(f"Tax code {tax_code.code} is not effective on the document date {document.issue_date}")`. Helper `TaxCodeService.is_effective(tax_code, on_date)` shared by both call sites.

**TDD.** New `tests/integration/test_tax_code_effectiveness.py` (RED first, all failing for the audited reasons):
- service: org with SR history rows (0.07→2022-12-31, 0.08→2023, 0.09→2024-01-01) → `get_tax_code_by_code(org, "SR", as_of=date(2023,6,1)).rate == 0.08`; `as_of=date(2024,1,1)` → 0.09; `as_of=date(2020,1,1)` → None; no `as_of` (today) → 0.09;
- service: org-specific SR row (0.05, effective) shadows the system 0.09 row;
- endpoint: `GET …/gst/tax-codes/?effective_on=2023-06-01` returns exactly one SR row (0.08);
- endpoint: `POST …/gst/calculate/` `{"amount": "100.00", "tax_code": "SR", "document_date": "2023-06-01"}` → `rate == "0.0800"`, `gst_amount == "8.00"`;
- endpoint: unknown code `{"amount": "100.00", "tax_code": "NOPE"}` → 404 (not 200-with-9%);
- service: `add_line` with a tax code expired on the document date → `ValidationError`; with the effective row → line created with the snapshotted rate.

**Done when:** all new tests green; `pytest tests/integration/test_tax_code_effectiveness.py tests/integration/test_gst_calculation.py tests/test_api_endpoints.py -q` green (no regressions in the existing calculate/tax-code tests, which use the `rate` path or today-effective fixtures).

**Files:** `apps/gst/services/tax_code_service.py`, `apps/gst/views.py`, `apps/gst/serializers.py`, `apps/invoicing/services/document_service.py`, `tests/integration/test_tax_code_effectiveness.py` (new). **Dependencies:** Task 3 (same view file; keep diffs sequenced).

---

### Task 5 (B-4): Truthful web `.env.example`

**Fix** (`apps/web/.env.example`): rewrite to contain exactly the variables the code reads — `NEXT_PUBLIC_API_URL` (`next.config.ts:23`, `src/middleware.ts:33`, `src/lib/api-client.ts:15`), `NEXT_OUTPUT_MODE` (`next.config.ts`), `BACKEND_URL` (`src/lib/server/api-client.ts:14`, new to the file) — with the copy-to-`.env.local` instruction; the seven not-yet-wired flags move to a clearly-labelled "reserved for future features — NOT read by the code yet" section so the aspirational names aren't lost, but the header no longer claims they are live.

**Verification.** `rg` each kept variable → ≥1 code hit; each "reserved" one → 0 hits (documented as such).

**Files:** `apps/web/.env.example`. **Dependencies:** none.

---

### Task 6 (B-5): Typecheck gate green

**Fix.**
1. `apps/web/package.json`: add `"typecheck": "tsc --noEmit"`; extend `test:all` to `"vitest run && tsc --noEmit && playwright test"`.
2. Repair the 25 errors in the affected test files:
   - `jest.Mock` / `global.jest` typings → `import type { Mock } from "vitest"` (or `vi.fn()` typing via `MockedFunction`);
   - un-imported `beforeEach`/`describe`/`it` where missing → import from `"vitest"`;
   - fixture objects missing required schema fields (`currency`, `exchange_rate`, `is_default`, `opening_balance`, …) → add the missing fields with realistic values (the runtime tests already pass, so the fixtures' extra strictness is type-level only).
3. Re-run `npx tsc --noEmit` → 0 errors.

**TDD.** The RED is the executed `tsc --noEmit` (25 errors). GREEN = 0 errors, plus `npm test` still 321+ green (runtime unchanged).

**Done when:** `npm run typecheck` exits 0; vitest suite still green.

**Files:** `apps/web/package.json`, the 6-8 affected test files under `src/**/__tests__/`. **Dependencies:** none (parallel-safe).

---

### Task 7: Full verification gate + documentation alignment

**Gate (all must pass — see §3).** Then docs:

1. `README.md` — Quick Start / Testing sections: add `npm run typecheck`, document `npm run test:e2e` (chromium default, `PLAYWRIGHT_PROJECTS=all` opt-in, `npx playwright install` prerequisite), update expected counts.
2. `CLAUDE.md` — status table (backend/frontend test counts incl. new tests; suite status "P2 remediated"), milestone row for this sprint.
3. `AGENTS.md` — session-5 lessons (rate-effectiveness semantics; fail-closed over fallback; browser-availability gating in playwright config; type-gate drift lesson: runtime-green ≠ type-green).
4. `docs/REMEDIATION_2026-11-21_P2_REPORT.md` (new) — verification ledger.
5. `ledgersg_SKILL.md` — refresh per `skills/distill-codebase-skill` + `skills/to-distill-project-into-skill` (project_state, new debugging rows, updated counts/commands).
6. `apps/web/README.md` — if it documents test commands, align (checked before editing).

---

### Task 8: Screenshots, session log, worklog, commit & push

1. Screenshots of the remediated app (backend + frontend dev servers, headless chromium via the installed v1208) into `docs/screenshots/` — new captures this session (login incl. the a11y-fixed page, dashboard, at least one data page), names following the existing `NN_page.png` convention with a session suffix to avoid clobbering session 3's set.
2. `docs/session_5.md` — this session's log, following the session_3/4 convention.
3. `worklog.md` (repo root) — append session 5 record.
4. Conventional commits on `main` per §5; push via `docs/ssh_git_wrapper_v3.py` per `docs/how-to-git-push-using-ssh-wrapper_SKILL.md`.

---

## 3. Verification Gate (definition of done for the sprint)

Environment: PG :5432 (schema v1.0.2, `test_ledgersg_dev`), Redis :6379, `DB_*` env per P1 report §4.

| # | Check | Expected |
|---|---|---|
| 1 | `pytest --reuse-db --no-migrations -q` | **0 failed**, 499 + ~12 new passed, 5 skipped |
| 2 | `pytest tests/invariants -q` / `pytest tests/security -q` | 15 passed / 32 passed, 3 skipped |
| 3 | `DJANGO_SETTINGS_MODULE=config.settings.testing python manage.py check` | 0 errors (1 known W001) |
| 4 | `ruff check` on touched backend files | clean (pre-existing debt untouched) |
| 5 | `cd apps/web && npm run typecheck` | 0 errors |
| 6 | `cd apps/web && npm test` | 321 + new tests passed, 0 failed |
| 7 | `cd apps/web && npm run test:e2e` | chromium suite green incl. axe scan |
| 8 | `PLAYWRIGHT_PROJECTS=all npx playwright test --list` | all 5 projects listed (no launch) |
| 9 | `npm run lint` on touched web files | no new findings introduced |
| 10 | `rg -n "box_mapping" apps/gst/views.py` | empty |
| 11 | `.env.example` var audit | every live var has ≥1 code hit; reserved vars documented as not-yet-read |
| 12 | Screenshots in `docs/screenshots/` | new non-empty unique PNGs |

Claims labelled **Verified** / **Reasoned** / **Assumed** in the report.

---

## 4. Deferred Debt Register (explicit, not silent)

Carried forward unchanged from `docs/REMEDIATION_PLAN_2026-11-21_P1.md` §4 unless touched here:

| Item | Status |
|---|---|
| H-02 base-currency reporting / retained earnings / BS assertion | Deferred (design work) |
| H-03 widen 80 `NUMERIC(10,4)` columns to `NUMERIC(19,4)` | Deferred (schema-wide versioned patch) — **note:** `add_line`'s quantize-to-0.01 behaviour retained this sprint; widening is a prerequisite for high-precision unit prices |
| H-08 wire `send-invoicenow` to real `TransmissionService` | Deferred (adapter contract) |
| H-09 (rest) Reg-11 tax-invoice labelling | Deferred |
| H-10 Schematron fail-closed validation | Deferred |
| H-11 fiscal close controls | Deferred |
| H-13 reproducible container build | Deferred |
| M-02…M-16, L-01…L-10, I-01…I-08 | Deferred per audit roadmap |
| GST payment tracking (`pay_return`) | Intentionally raises until schema extension |
| Backend repo-wide ruff debt (~1,311 findings) | Pre-existing; touched files stay lint-clean |
| **B-6 frontend eslint debt (87 errors / 3,755 warnings)** | Pre-existing; registered this session; files touched by this sprint stay clean; a dedicated `eslint --fix` + rule-tightening pass is a separate sprint (risk of large diff) |
| A-10 stale root `requirements.txt` | Deferred (repo-owner coordination decision) |
| `test_api_endpoints.py` local fixture duplication | Deferred cleanup |
| F5 return computation date-basis (returns currently resolve at computation date, lines at document date after Task 4) | Deferred — needs a period-cut semantics decision (ties into H-02) |

---

## 5. Commit Plan (conventional commits, single branch `main`)

1. `build(web): green-by-default playwright config — chromium default, opt-in matrix, list+html reporters (B-1)`
2. `fix(web): login page main landmark + h1; a11y unit test (B-2)`
3. `fix(gst): drop phantom box_mapping kwarg breaking custom tax-code create (B-7)`
4. `fix(gst): resolve tax-code rate by effective date, fail-closed calculate + add_line (B-3/H-04)`
5. `chore(env): truthful web .env.example — live vars only, reserved flags marked (B-4)`
6. `build(web): typecheck script + repair 25 test-file type errors (B-5)`
7. `docs: P2 remediation report; align README/CLAUDE/AGENTS; refresh ledgersg_SKILL.md`
8. `docs(worklog): session 5 worklog, session log and screenshots`
