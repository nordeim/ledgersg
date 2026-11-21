# LedgerSG — Worklog

## 2026-11-21 — Session 7: P3 Sprint (Monetary Capacity, Truthful Invoice Form & Suite Depth)

**Base:** `5b237743` (main) · **Plan:** `docs/REMEDIATION_PLAN_2026-11-21_P3.md` · **Report:** `docs/REMEDIATION_2026-11-21_P3_REPORT.md`

### Environment (reused, re-verified)

- Rootless PG 17 (`/home/z/my-project/pg`, :5432) + Redis 8 (:6379) re-verified; schema loaded at v1.0.2 and **migrated in-place to v1.1.0** via the new §16 block during Task 1 (47 monetary columns widened; idempotent re-run verified).
- Baselines reproduced before any change: backend **514P/0F/5S**, frontend vitest **324/324**, typecheck **0 errors**, e2e **6/6** — the documented P2 state, exactly. P2 rate-effectiveness live-verified through the API (2023 SR → 0.0800).

### Audit (Mode C) — findings this session

Repo skills: `code-review-and-audit` (standard mode scoped to `apps/` + manual verification of all 24 scanner criticals — all false positives), `code-quality-standards`, `diagnosing-bugs`, `e2e-testing-lessons`, `writing-plans`, `planning-and-task-breakdown`. Real findings (full register in plan §0):

- **C-1 (= deferred H-03, Critical/compliance)**: 47 `NUMERIC(10,4)` columns cap all money at S$999,999.9999 — below the S$1M GST registration threshold; F5 Box 13 and ≥ S$1M lines/journal amounts raise `numeric field overflow` (verified live).
- **D-1 (High)**: New Invoice form submit was a TODO stub (`console.log` + mock UUID); `useCreateInvoice` dead code — the UI could not create documents.
- **D-2 (High, security + broken)**: `useInvoicePDF` read the token from `localStorage` — zero-JWT-exposure violation AND broken (token lives in module memory → `Bearer null` → 401).
- **D-3 (Medium)**: tax dropdown + preview hardcoded at 9%, ignoring the P2 `?effective_on=` API (backdated documents preview wrong).
- **D-4 (Low)**: `ALLOWED_HOSTS` missing from the backend `.env.example`.
- **D-5 (Low/coverage)**: e2e covered public navigation only (6 tests); no invoice-form or authenticated coverage.

### Remediation executed (TDD)

| Task | Change | Evidence |
|---|---|---|
| 1 (C-1/H-03) | Schema v1.1.0: 47 columns → NUMERIC(19,4); §16 idempotent in-place migration (generated-column drop→widen→re-add); 31 model/serializer sites; conformance gate asserts numeric precision (caught pre-existing `exchange_rate` 19,6 vs 12,6 — aligned DOWN); `add_line` applies `discount_pct` server-side | 5 tests RED→GREEN; census 0 × (10,4); suite 514→519 |
| 2 (D-3) | `useTaxCodes(orgId, effectiveOn?)` + `endpoints.gst`; engine `rateOverride` (fail-closed); form watches issue_date; dropdown shows `CODE · rate%` | 8 tests RED→GREEN |
| 3 (D-1) | `lib/invoice-submit.ts` pure adapter (contact+document payloads, readiness validation); `use-accounts` hook; per-line Account select; real submit flow + error banner; `useCreateInvoice` retyped | 14 tests RED→GREEN; `rg useCreateInvoice` 0 → 2 importers |
| 4 (D-2) | `fetchWithAuth` extracted; `api.blob()` on the single auth path; localStorage read deleted | 3 tests RED→GREEN; `rg localStorage…accessToken` empty |
| 5 (D-5) | `e2e/auth.spec.ts` + `e2e/invoices.spec.ts` (real UI login → client-side nav; account/tax-code/preview assertions; NO submission); `test:e2e:full`; Radix pointer-capture mocks in setup.ts | 13 e2e total; default 9+4skip; full 13/13 ×2 |
| 6 (D-4) | `ALLOWED_HOSTS` in backend `.env.example` | 15/15 settings-read vars listed |

### Final gate (all Verified, executed)

- `pytest --reuse-db --no-migrations -q` → **0 failed, 519 passed, 5 skipped** (+5)
- `pytest tests/invariants -q` → **20 passed** · `pytest tests/security -q` → 32 passed, 3 skipped
- `manage.py check` → 0 errors (1 known W001) · ruff: touched files 15 before == 15 after; new files clean
- Web: typecheck 0 errors · vitest **349/349** (+25; 26 files) · eslint on touched files clean · e2e default **9 passed + 4 gated skips**, full **13/13** (twice)
- 5 new screenshots (`docs/screenshots/14..18_*_session7.png`), hash-unique — incl. the new-invoice form with the account dropdown open and a S$1.5M line

### Deferred (registered, not dropped)

P0/P1/P2 register unchanged (H-02/H-08…H-13, M-*, L-*, I-*, B-6 eslint debt, F5 rate-basis, backend ruff debt); NEW this session: **cross-reload session persistence** (backend returns tokens in the body, sets no cookie; the provider discards the refresh token; `tryRefreshToken` posts an empty body the backend 400s — needs a design decision), the **invoice-form existing-contact picker**, and the **e2e login-rate budget** (7 logins/full-run vs 10/min-per-IP). See P3 report §3.

### Commits

Conventional commits on `main` per P3 plan §5; pushed via `docs/ssh_git_wrapper_v3.py` (key shredded after push).

---

## 2026-11-21 — Session 5: P2 Sprint (Test Gates & Rate-Effectiveness Truth)

**Base:** `4acece81` (main) · **Plan:** `docs/REMEDIATION_PLAN_2026-11-21_P2.md` · **Report:** `docs/REMEDIATION_2026-11-21_P2_REPORT.md`

### Environment (reused, re-verified)

- Rootless PG 17 (`/home/z/my-project/pg`, :5432) + Redis 8 (:6379) restarted; schema v1.0.2 confirmed in both DBs (30 domain tables; the seed's system SR rate history 0.07/0.08/0.09 is present in `test_ledgersg_dev` and drove the per-code `effective_on` design).
- Baselines reproduced before any change: backend **499P/0F/5S**, frontend vitest **321/321** — the documented P1 state, exactly.
- Installed chromium v1208 + headless shell to match `@playwright/test` 1.58.2 (session 3's executable-path workaround no longer needed).

### Audit (Mode C) — findings this session

Repo skills: `code-review-and-audit` (audit_runner standard mode + per-finding manual verification), `code-quality-standards`, `diagnosing-bugs`, `e2e-testing-lessons`, `browser-testing-with-devtools`. Scanner "criticals" = the same 21 session-3 false positives. Real findings (full register in plan §0):

- **B-1** (High, infra): playwright config declares 5 browser projects, only chromium installed → `npm run test:e2e` errors 24/30 tests pre-assertion.
- **B-2** (Medium, a11y): login page fails the repo's own axe e2e (no `<main>`, no `<h1>` — CardTitle is an h3; terms text 3.3:1 contrast); the scan also races the auth redirect chain.
- **B-3 = H-04** (High, compliance): rate history resolution broken end-to-end — unordered `.first()` (verified returning SR=0.07 today), unordered list endpoint, calculate endpoint fail-open to silent 9% with a triple-broken code branch, `add_line` no effectiveness check.
- **B-4** (Medium, env): web `.env.example` — 7/9 vars read nowhere; `BACKEND_URL` missing.
- **B-5** (Medium, gates): no typecheck script; `tsc --noEmit` red with 25 pre-existing test-file errors.
- **B-6** (Low, debt): eslint 87E/3755W repo-wide (pre-existing; registered).
- **B-7** (High, broken feature): `POST /gst/tax-codes/` always 500 (phantom `box_mapping` kwarg → TypeError; also fixed `chk_io_flag` compliance via is_input/is_output defaults).

### Remediation executed (TDD)

| Task | Change | Evidence |
|---|---|---|
| 1 (B-1) | playwright.config.ts: chromium default, `PLAYWRIGHT_PROJECTS=all` opt-in, list+html(open never) reporters | `--list`: 6 vs 30 tests; e2e 6/6 |
| 2 (B-2) | Login `<main>` + explicit h1; contrast fix; deterministic axe (await redirect) | 3 vitest RED→GREEN; e2e axe GREEN |
| 3 (B-7) | box_mapping kwarg removed; f5_* forwarded; `create_tax_code` io-flag defaults | 3 tests RED (TypeError) → 201 GREEN |
| 4 (B-3/H-04) | `get_tax_code_by_code(as_of)` + `is_effective()`; `list_tax_codes(effective_on=…)`; calculate: `tax_code`+`document_date`, legacy alias, fail-closed 404; `add_line` fails closed on stale codes | 12 tests RED→GREEN |
| 5 (B-4) | Truthful `.env.example` (live vars + reserved section) | per-var rg audit |
| 6 (B-5) | `typecheck` script; `test:all` chain; 25 errors repaired | tsc 0 errors; vitest still green |

### Final gate (all Verified, executed)

- `pytest --reuse-db --no-migrations -q` → **0 failed, 514 passed, 5 skipped** (+15 new)
- `pytest tests/invariants -q` → 15 passed · `pytest tests/security -q` → 32 passed, 3 skipped
- `manage.py check` → 0 errors (1 known W001) · ruff: touched files 19 before == 19 after (pre-existing only); new files clean
- Web: `npm run typecheck` → 0 errors (was 25) · `npm test` → **324 passed (25 files)** · `npm run test:e2e` → **6/6 (chromium)**
- 5 new screenshots (`docs/screenshots/09..13_*_session5.png`), hash-unique

### Deferred (registered, not dropped)

P0/P1 register unchanged (H-02/03/08/09r/10/11/13, M-*, L-*, I-*, backend ruff debt); NEW this session: **B-6** frontend eslint debt (87E/3755W), **F5 rate-basis semantics** (returns at computation date vs lines at document date — needs a period-cut decision, ties into H-02), and the frontend wiring of `?effective_on=` for the invoice form's tax-code dropdown. See P2 plan §4.

### Commits

Conventional commits on `main` per P2 plan §5; pushed via `docs/ssh_git_wrapper_v3.py` (paramiko shim; key shredded after push).

---

## 2026-11-21 — Session 3: P1 Sprint (Green Suite & Contract Truth)

**Base:** `342d16fb` (main) · **Plan:** `docs/REMEDIATION_PLAN_2026-11-21_P1.md` · **Report:** `docs/REMEDIATION_2026-11-21_P1_REPORT.md`

### Environment (rebuilt from scratch this session)

- Rootless PostgreSQL 17 via `docs/setup_pg_z.sh` + `skills/rootless-postgresql` (`/home/z/my-project/pg`, port 5432); role `ledgersg` (SUPERUSER, required by the schema's DO-block CREATE ROLE), databases `ledgersg_dev` + `test_ledgersg_dev`, schema v1.0.2 loaded in both (30 domain tables + 2 token-blacklist tables).
- Redis 8.0.2 (rootless .deb extraction, `/home/z/my-project/redis`) — hard prerequisite for the suite (middleware membership cache).
- Backend venv via `pip install -e ".[dev]"`; frontend `npm install`.
- Baseline reproduced EXACTLY as documented: 26 failed / 465 passed / 5 skipped; invariants 12P; security 32P/3S; frontend 321/321.

### Audit (Mode C) — findings this session

Used `skills/code-review-and-audit` (audit_runner standard mode + manual verification of every scanner finding), `code-quality-standards`, `diagnosing-bugs`, `writing-plans`, `planning-and-task-breakdown`. The 21 scanner "criticals" were individually verified as test-fixture/docstring false positives. Real findings (full register in the plan §0):

- **A-1** (High): `test_api_endpoints.py` org fixture missing `UserOrganisation.accepted_at` → 25 of the 26 documented failures.
- **A-2** (High): `DocumentSummaryView` — phantom `DOCUMENT_TYPE_CHOICES`, invalid `PAID_PARTIAL` enum literal (×2), phantom `total` attribute, int-vs-Decimal `.quantize()` crash on empty orgs; same literal in `contact_service.deactivate_contact`.
- **A-3** (High): CoA `get_trial_balance` LEFT JOINs the non-existent `coa.account_balance` view → 500.
- **A-4** (Medium): `ValidStatusTransitionsView` missing `org_id` kwarg → 500.
- **A-5** (Medium): `test_create_organisation` payload bugs (`gst_reg_date` missing; `entity_type: pte_ltd` not in the CHECK vocabulary).
- **A-6** (High, packaging): `django-celery-beat` + `django-ratelimit` imported by settings but undeclared in `pyproject.toml`; `requirements.txt`'s beat 2.8.1 pin forces a Django 5.x downgrade.
- **A-7/A-8** (Low): `.env`/`.env.local` tracked, no gitignore rules; `apps/web/.env.example` referenced by README but missing; backend example incomplete.
- **A-9** (Low): schema header still said v1.0.1.
- **A-10** (Info): stale root `requirements.txt` second manifest.

### Remediation executed (TDD)

| Task | Change | Evidence |
|---|---|---|
| 1 (A-1/A-5) | Fixture `accepted_at=timezone.now()`; test payload `gst_reg_date` + `PRIVATE_LIMITED` | 26F → 4F (the 4 = the real bugs) |
| 2 (A-2) | `DOCUMENT_TYPES`, outstanding set `[APPROVED, SENT, PARTIALLY_PAID, OVERDUE]`, `total_incl`, Decimal-safe sums; contact-service sweep | New `tests/integration/test_document_summary.py` 5/5 (RED→GREEN) |
| 3 (A-3) | Trial balance rewritten on `journal.line` ⋈ `journal.entry` with optional `fiscal_year_id` | +3 invariant assertions (RED→GREEN) |
| 4 (A-4) | `get(self, request, org_id: str)` | status-transitions test green |
| 5 (A-6) | `pyproject.toml`: `django-celery-beat==2.9.0`, `django-ratelimit>=4.1,<5` | Clean-venv install + `manage.py check` pass, Django stays 6.0.2 |
| 6 (A-7/A-8) | `apps/web/.env.example` (new), backend example completed, `.gitignore` rules, `git rm --cached` env files | fresh copies are git-ignored |
| 7 (A-9) | Schema header → v1.0.2 | grep |
| 8 | Docs aligned (README, CLAUDE.md v2.6.0, AGENTS.md session-3 lessons, P1 report) | claims match executed evidence |
| 9 | 8 dev-server screenshots in `docs/screenshots/` (login, post-login, dashboard, invoices, ledger, banking, settings, reports) | unique PNGs verified by hash |

### Final gate (all Verified, executed)

- `pytest --reuse-db --no-migrations -q` → **0 failed, 499 passed, 5 skipped** (first fully green run)
- `pytest tests/invariants -q` → 15 passed · `pytest tests/security -q` → 32 passed, 3 skipped
- `manage.py check` → 0 errors (1 known W001) · clean-venv install path works
- `npm test` (web) → 321 passed (24 files)
- Ruff: new files clean; touched legacy files carry only pre-existing debt (210 → 208 on those files)

### Deferred (registered, not dropped)

P0 register (H-02/03/04/08/09r/10/11/13, M-02…M-16, L-*, I-*) unchanged; plus repo-wide ruff debt (1,311 findings) and the stale root `requirements.txt` manifest decision. See plan §4.

### Commits

Conventional commits on `main` per plan §5; pushed via `docs/ssh_git_wrapper_v3.py` (paramiko shim; key shredded after push).
