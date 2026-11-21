# LedgerSG — Remediation Report (P2 Sprint: Test Gates & Rate-Effectiveness Truth)

**Date:** 2026-11-21 (session 5)
**Base commit:** `4acece81` (main)
**Plan:** `docs/REMEDIATION_PLAN_2026-11-21_P2.md`
**Method:** TDD (RED → GREEN → REFACTOR); every production-code fix has a regression test that failed before the fix and passes after. All 12 rate-effectiveness tests, 3 tax-code-create tests, and 3 login-a11y tests were written RED first.

---

## 1. Verification Ledger (executed evidence)

Environment: rootless PostgreSQL 17 on :5432 (schema v1.0.2 in `ledgersg_dev` + `test_ledgersg_dev`), Redis 8 on :6379, Python 3.12 venv, Node with `@playwright/test` 1.58.2 + chromium/chromium-headless-shell v1208 installed.

| # | Check | Command | Result |
|---|---|---|---|
| 1 | Baseline (pre-remediation, this session) | `pytest --reuse-db --no-migrations -q` | **499 passed, 0 failed, 5 skipped** — documented P1 state reproduced exactly |
| 2 | Baseline (frontend unit) | `npx vitest run` | **321 passed (24 files)** — documented state reproduced |
| 3 | Full backend suite (post-remediation) | same | **0 failed, 514 passed, 5 skipped** (+15: 12 rate-effectiveness, 3 tax-code-create) |
| 4 | Invariant / security gates | `pytest tests/invariants -q` / `pytest tests/security -q` | 15 passed / 32 passed, 3 skipped — no regression |
| 5 | Django system check | `DJANGO_SETTINGS_MODULE=config.settings.testing python manage.py check` | 0 errors, 1 pre-existing warning (`django_ratelimit.W001`) |
| 6 | Ruff (touched backend production files) | `ruff check apps/gst/{views,serializers}.py apps/gst/services/tax_code_service.py apps/invoicing/services/document_service.py` | 19 findings before == 19 after (pre-existing debt only, measured via `git stash` comparison); **new test files clean** |
| 7 | Frontend typecheck | `npm run typecheck` (new script) | **0 errors** (was 25 errors before the sprint) |
| 8 | Frontend unit suite | `npm test` | **324 passed (25 files)** — 321 + 3 new login-a11y tests |
| 9 | Frontend e2e suite | `npm run test:e2e` | **6/6 passed (chromium)** — was 24/30 launch-errors before the config fix; the axe scan was RED, now GREEN |
| 10 | Playwright project gating | `npx playwright test --list` / `PLAYWRIGHT_PROJECTS=all npx playwright test --list` | 6 tests (chromium) / 30 tests (5 projects) — verified |
| 11 | Phantom kwarg sweep | `rg -n "box_mapping" apps/gst/views.py` | no hits |
| 12 | ESLint (files created/rewritten this sprint) | `npx eslint <touched files>` | clean; the 34 errors in `banking/__tests__/` are pre-existing (`banking-client-transactions.test.tsx` — untouched by this sprint) |
| 13 | `.env.example` truthfulness | per-var `rg` against `src/` + `next.config.ts` | every LIVE var has ≥1 code hit; reserved vars documented as not-yet-read |

Confidence labels: every row above is **Verified** (executed in this environment).

---

## 2. What Was Fixed

### B-3 / deferred H-04 — GST rate history resolved by effective date, fail-closed
- `TaxCodeService.get_tax_code_by_code(org_id, code, as_of=None)`: resolves the row in force on `as_of` (default today) — effective-window filter (`effective_from <= as_of <= effective_to`, NULLs = open ends), org-scoped rows shadow system rows (`F("org_id").asc(nulls_last=True)`), latest `effective_from` wins. **Pre-fix evidence: the service returned the 2007 row (rate 0.0700) for SR today.**
- New `TaxCodeService.is_effective(tax_code, on_date)` helper.
- `list_tax_codes(..., effective_on=None)`: optional date filter resolving to the single row a document dated that day would use per code; ordering is now `(code, org-first, effective_from DESC)`.
- `GET /{org}/gst/tax-codes/?effective_on=YYYY-MM-DD` wired (invalid dates → 400).
- `GSTCalculateView`: canonical `tax_code` (string) + optional `document_date`; the legacy `tax_code_id` field (which always held a code, never a UUID — it was a `UUIDField`, so the branch was doubly unreachable) is kept as a deprecated CharField alias; unknown / not-in-force codes → **404** instead of the silent `Decimal("0.09")` fallback. Two latent crashes in the same branch were fixed in passing: `UUID(org_id)` re-wrapping of an already-UUID kwarg, and an `UnboundLocalError` on `Decimal` (function-local import in the else-branch; imports hoisted to module level).
- `DocumentService.add_line`: fails closed with `ValidationError` when the passed tax code is not effective on `document.issue_date`; `_add_lines` (document creation) inherits the check for free.
- Tests: `tests/integration/test_tax_code_effectiveness.py` — 12 tests (service resolution ×5, list endpoint ×2, calculate endpoint ×3, add_line ×2), all RED first for the audited reasons.

### B-7 — Custom tax-code creation un-broken
- `POST /{org}/gst/tax-codes/` always 500'd: the view passed `box_mapping=…` (a field on neither serializer nor model) into `TaxCode.objects.create`. Fixed: kwarg removed; the serializer's declared `f5_supply_box`/`f5_purchase_box`/`f5_tax_box` now persist instead of being silently dropped.
- `create_tax_code` gained `is_input`/`is_output` params defaulting to output-side, satisfying the DB CHECK `chk_io_flag` (`is_input OR is_output OR code='NA'`) that previously made every custom create an IntegrityError even without the phantom kwarg.
- Tests: `tests/integration/test_tax_code_create.py` — 3 tests (201 create, f5 persistence, reserved-code 400), RED first with the exact audited `TypeError`.

### B-1 — Playwright green by default
- `playwright.config.ts`: chromium-only projects by default; `PLAYWRIGHT_PROJECTS=all` opts into firefox/webkit/Mobile Chrome/Mobile Safari; reporters `list` + `html(open: never)`; explicit `outputDir`. Pre-fix: 24/30 tests errored on missing browser executables.
- Installed chromium v1208 + headless shell to match `@playwright/test` 1.58.2 (previous sessions pinned an older executable path as a workaround).

### B-2 — Login page a11y (the repo's own axe test is green)
- `<main>` landmark wrapper; brand heading is now an explicit `<h1>` (was `CardTitle` = `<h3>`); terms text `text-text-muted` (3.3:1) → `text-text-secondary` (7.2:1).
- The e2e axe test now waits for the auth-redirect chain to settle (`toHaveURL(/\/login/)`) before scanning — the old test raced the guard's null shell and flaked on cold servers.
- Tests: `src/app/(auth)/login/__tests__/login-a11y.test.tsx` — 3 vitest tests (main landmark, single h1, no skipped levels), RED first; e2e axe GREEN as the independent pair.

### B-4 — Truthful `apps/web/.env.example`
- LIVE section: `NEXT_PUBLIC_API_URL`, `BACKEND_URL` (was missing — read by `src/lib/server/api-client.ts`), `NEXT_OUTPUT_MODE`. The seven not-yet-wired flags moved to a clearly-marked RESERVED section; the false "every variable below is actually read" header claim removed.

### B-5 — Typecheck gate green
- `npm run typecheck` script added; `test:all` = `vitest run && tsc --noEmit && playwright test`.
- 25 pre-existing errors repaired: `jest.Mock` → vitest `Mock` (6 banking test files), missing `beforeEach` imports, schema-typing corrections (`BankAccountInputParams = z.input<…>` for default-tests; `GSTCalculatableLine` for `calculateFromLines`, whose signature now takes the input-side type), and completed mutation fixtures in `use-banking.test.tsx`.

---

## 3. Deferred Debt Register (explicit — nothing silently dropped)

Carried forward from `docs/REMEDIATION_PLAN_2026-11-21_P1.md` §4 unless touched here:

| Item | Status |
|---|---|
| H-02 base-currency reporting / retained earnings / BS assertion | Deferred (design work) |
| H-03 widen 80 `NUMERIC(10,4)` columns to `NUMERIC(19,4)` | Deferred (schema-wide versioned patch) |
| H-08 wire `send-invoicenow` to real `TransmissionService` | Deferred (adapter contract) |
| H-09 (rest) Reg-11 tax-invoice labelling | Deferred |
| H-10 Schematron fail-closed validation | Deferred |
| H-11 fiscal close controls | Deferred |
| H-13 reproducible container build | Deferred |
| M-02…M-16, L-01…L-10, I-01…I-08 | Deferred per audit roadmap |
| GST payment tracking (`pay_return`) | Intentionally raises until schema extension |
| Backend repo-wide ruff debt (~1,311 findings) | Pre-existing; touched files stay lint-clean |
| **B-6 frontend eslint debt (87 errors / 3,755 warnings)** | Registered this session; pre-existing (`banking-client-transactions.test.tsx` etc.); a dedicated `eslint --fix` + rule-tightening sprint is separate (large-diff risk) |
| **F5 return rate-basis: returns resolve at computation date, lines at document date** | Registered this session; needs a period-cut semantics decision (ties into H-02) |
| A-10 stale root `requirements.txt` | Deferred (repo-owner coordination decision) |
| `test_api_endpoints.py` local fixture duplication | Deferred cleanup |
| Tax-code list UI: no frontend consumer of `effective_on` yet | The API is ready; wiring the invoice form's tax-code dropdown to `?effective_on=<document date>` is frontend feature work |

---

## 4. How to Verify (reproduction commands)

```bash
# Prerequisites: PG on :5432 (schema v1.0.2 loaded), Redis on :6379
cd apps/backend && source .venv/bin/activate
export DB_NAME=test_ledgersg_dev DB_USER=ledgersg DB_PASSWORD=ledgersg_secret_to_change \
       DB_HOST=127.0.0.1 DB_PORT=5432

pytest --reuse-db --no-migrations -q   # 0 failed, 514 passed, 5 skipped
pytest tests/invariants -q             # 15 passed
pytest tests/security -q               # 32 passed, 3 skipped
pytest tests/integration/test_tax_code_effectiveness.py tests/integration/test_tax_code_create.py -q  # 15 passed

cd ../web
npm run typecheck                      # 0 errors
npm test                               # 324 passed (25 files)
npx playwright install chromium        # first run only
npm run test:e2e                       # 6 passed (chromium)
PLAYWRIGHT_PROJECTS=all npx playwright test --list   # 30 tests, 5 projects
```

**Labels:** §1 is Verified (executed). §2 statements are Verified for the described code state at commit time of this report.
