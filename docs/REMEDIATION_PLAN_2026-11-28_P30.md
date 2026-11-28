# LedgerSG — Remediation Plan (P30 Sprint: The Ruff Mechanical Closure + The Fourth-Surface Walk Completion + The Mechanical-Class Lint Ratchet)

**Date:** 2026-11-28 (session 57)
**Base commit:** `5a31ff9c` (main — post-P29 + the session-56/57 logs)
**Method for execution:** TDD (RED → GREEN → full gate) for every behavioural change; the mechanical lint batch verified by per-phase diffs + the full test matrix + the live contract re-verification; `skills/` excluded from all checks/tests/compilation; **no schema changes** (v1.2.2 carries forward); **no frontend component changes** (the web tree is untouched).
**Skills consulted:** `skills/skills-catalog.md` → `tdd` (the red→green loop), `code-review`/`code-review-checklist` (Mode C discipline), `debugging-and-error-recovery` (root-cause isolation on any RED surprise), `rootless-postgresql` (the PG environment — live from the prior sessions, re-probed this session), `agent-browser` (the live mobile-nav + translate probes — executed this session, §1), `nextjs16-tailwind4`/`tailwind-patterns` (consulted for the mobile-nav focus — the surface re-settled clean, §1).

---

## 1. Audit inputs (this session's evidence)

- **Repo + docs truth pass:** `git pull` to `5a31ff9c` clean on `main` (the only delta from the P29 push: `docs/session_57.md`); full reads of `AGENTS.md`, `CLAUDE.md` v2.30.0, `README.md`, `Project_Architecture_Document.md` v3.19.0, `ledgersg_SKILL.md` v2.16.0, `worklog.md`, `docs/session_56.md`, `docs/session_57.md`, the P29 plan + report.
- **The environment (live, re-probed):** rootless **PG 17** on :5432, **Redis** on :6379, the backend venv, `node_modules`, the dev stack (:8000 health 200, :8001 health 200, :3000 `next dev`). **No environment repair was required this session.**
- **The baseline reproduction (pre-change, this session — all gates exact):** backend `pytest --reuse-db --no-migrations -q` **1028P/0F/5S** (29.81s) · vitest **698/698 (85 files)** (106.80s) · `npx tsc --noEmit` **0 errors** · whole-tree `npx eslint . --max-warnings 5` from `apps/web` **0E/0W** · live `test:e2e:full` **43/43 (2m20s, deterministic, first run)** · `rls_smoke.py` **13/13 as `ledgersg_app`** · `mobile-nav-audit.js` **17/17** (the twenty-eighth settlement) · the dedicated Tailwind v4 `translate` probe (`scripts/translate-probe-session53.js`): **PASS** (7 mid-flight samples, closed `-100%`/hidden → open `0px`/`role="dialog"` → Escape closes) · `npm audit` **0 across dev+prod**.
- **The named focus — the mobile-nav verdict (twenty-eighth settlement):** **WORKING as expected; NO remaining TailwindCSS v4 bug on this surface.**
- **The audit (Mode C) of the P29 slice** (`8b56f5e1`, `d3daa2f7`, `d878a592` — hand-verified in source this session): the three service gets carry the bounded-fetch contracts (`document_service.py:173-177`, `journal_service.py:151-154`, `payment_service.py:298`), the P29 query-count spec is in place, the raised per-glob ratchets + the shared tier sit in `vitest.config.ts` — **0 new findings in the P29 slice**.
- **The same-class sweep one seam deeper (all verified clean):** every serializer nested-`source=` walk is covered by a carrying queryset (the bank-transaction LIST rides `select_related("bank_account")` — `reconciliation_service.py:59`; the allocation serializer's `document` walk rides `get_allocations`' select_related — `payment_service.py:694`); the report paths are single grouped queries (trial balance `journal_service.py:657-664`, P&L/BS `reporting/views.py:180-270`, aged `aged_service.py:50-62`, F5 boxes `calculation_service.py:257+` — one grouped raw SQL); the write-path per-row ORM calls are deliberate bounded locking designs (`create_entry`'s sorted account pre-lock + per-line gates, `allocate`'s sorted document pre-lock); the dashboard is cached aggregates.
- **The test-suite standing task (user instruction: "add vitest and playwright test suite by modifying the respective config files"):** verified IN PLACE and current — `apps/web/vitest.config.ts` (jsdom, the setup file, the whole-suite + six per-glob coverage tiers) and `apps/web/playwright.config.ts` (chromium default, the live-suite serialisation contract, the E2E_API_URL gating), driving **698 vitest specs (85 files) + 43 e2e specs (11 files)**. This sprint ADDS to them (the new query-count specs, §3 T1).
- **The lint truth (measured this session, production tree `apps/ common/ config/`):** `ruff check` reports **928 findings**; the registered mechanical classes are **650**: W293×372 (blank-line-with-whitespace), W291×6 (trailing-whitespace), I001×122 (unsorted-imports), F401×121 (unused-import, across **51 files** — none an `__init__.py`), F403×3 + F405×26 (the Django split-settings star imports, all 29 inside `config/settings/{base,development,production,testing,service}.py`'s `from .base import *` idiom). The remaining 278 are semantic classes (B904×66, UP045×45, E501×39, UP006×35, F841×16, UP035×16, UP007×13, E402×12, SIM105×7, B009×6, S110×4, A001×2, E741×2, N806×2, B017×1, B905×1, F402×1, N802×1). Spot-verified genuine: `os` imported-but-unused in BOTH `config/settings/base.py` and `service.py` (the env reads are decoupled), `CanManageCoA` unused in `apps/coa/views.py` (a reader could believe a permission check exists that does not), the placeholder `apps/core/urls/{fiscal,settings,user}.py` import `path` for empty `urlpatterns`, and `config/urls.py`'s three try-import lines whose names are never used (the import is an availability probe; `include()` already raises the same `ImportError` inside the same `try`). `mypy --strict`: 1491 errors (the registered convenience tool, NOT a gate — this sprint does not lean on it). `ruff format --check`: 80 files would reformat (the `make format` axis — registered follow-up, NOT this sprint). The `tests/` tree (backend root): 379 findings incl. F811×27 and F821×2 (string-annotation nits in `tests/conftest.py:301,320` — the import lives inside the function body) — registered follow-up, out of this sprint's production scope.

**Combined findings (this session's audit): 0 Critical / 1 High / 2 Medium / 1 Low.**

## 2. Findings (verified, with evidence anchors)

### High

**BE-P30-H1 — the registered ruff mechanical batch: 650 production findings in the four mechanical classes, live since the P20-era measurement and explicitly deferred as "needs a dedicated, reviewed sprint" — this is that sprint.**
Three concrete harms, all verified this session:
1. **The blind-`--fix` trap (the register's own warning):** `ruff check --fix` today would be UNSAFE — the 26 F405 star-import usages mean an autofix could remove names the star import must keep flowing. Every future agent faces this trap.
2. **Signal burial:** `make lint` prints 928 findings; a NEW real finding (a genuinely dead import that masks a missing permission import, an undefined name) is invisible in the noise.
3. **Dead imports mislead:** `CanManageCoA` imported-but-unused in `apps/coa/views.py` reads as a permission contract that does not exist; `os` in the settings suggests env reads that happen elsewhere.

**The fix (four reviewed phases, per class):**
- **W291/W293 (378):** `ruff check apps/ common/ config/ --select W291,W293 --fix` — pure whitespace, zero semantic surface. Verify: the class count → 0.
- **I001 (122):** `ruff check apps/ common/ config/ --select I001 --fix` — import ordering (isort-compatible, `known-first-party` already configured). Verified by the full backend suite + the Django boot.
- **F401 (121, 51 files, none `__init__.py`):** the safe subset via `--fix`, then a per-file review of the remainder: remove the genuinely dead (the spot-verified set above), drop the three redundant `config/urls.py` availability-probe imports (`include()` raises the same `ImportError` inside the same `try` — behaviour-identical), keep any deliberate re-export with `# noqa: F401` + rationale. Verify: the class count → 0, the suite green, the live contracts byte-identical.
- **F403/F405 (29, the three settings modules):** NOT converted to explicit imports — the Django split-settings pass-through contract (`base.py` settings must flow into every derived module; an explicit-import conversion would silently DROP future base additions — the exact drift class this repo's lessons warn about). The fix: `[tool.ruff.lint.per-file-ignores]` `"config/settings/*.py" = ["F403", "F405"]` in `pyproject.toml`, with the rationale documented in a comment at the config. The three real F401s inside the settings files (e.g. `os` in base/service) are still fixed.

### Medium

**BE-P30-M2 — the fourth-surface walk completion: `reconcile()`/`unreconcile()` responses serialise a row whose FK walks its own query.**
`ReconciliationService.reconcile` (`apps/banking/services/reconciliation_service.py:351-353`) and `unreconcile` (`:432-436`) return the row from a `select_for_update()` fetch with **no select_related**, and the views serialise it with `BankTransactionSerializer` (`apps/banking/views.py:582,611`) whose `bank_account_name = serializers.CharField(source="bank_account.account_name")` (`bank_transaction.py:20`) walks the FK — **one extra query per reconcile/unreconcile response**. This is the P29 class on the fourth surface: the bank-transaction surface has no detail GET (only list/import/reconcile/unreconcile/suggest-matches), so the mutation responses ARE the serialising consumers — the exact shape P29 documented and fixed for the payment status-only consumers. The LIST path already carries `select_related("bank_account")` (P17/BE-M7).

**Fix:** chain `.select_related("bank_account")` onto both locked fetches. Verified safe: the FK is non-nullable (`bank_transaction.py:22-27` — INNER JOIN, so `FOR UPDATE` over the join is legal Postgres), the lock-order lesson holds (the joined `bank_account` row is acquired first on both paths — consistent across concurrent reconciles on the same account, and no sibling path locks bank accounts after transactions), and the payload is byte-identical (select_related changes HOW the row travels).

**CFG-P30-M3 — the mechanical-class lint ratchet: `make lint` is a convenience nobody gates.**
After the H1 closure, pin it: a `make lint:mechanical` target (`ruff check --select W291,W293,I001,F401,F403,F405 apps/ common/ config/` — must exit 0) + the same command as a CI step in the `backend-tests` job (ruff==0.15.2 is already a dev dependency — zero extra install). The 278 semantic findings stay ungated (registered) — the ratchet covers exactly what this sprint closed, the honest-ratchet philosophy applied to lint: a gate nobody runs is a rubber stamp.

### Low

**DOC-P30-L1 — the docs truths roll forward with the sprint** (the standing DOC-L pattern): README badge/counts + the P30 milestone, CLAUDE 2.30.0 → 2.31.0, AGENTS header + the P30 lessons, SKILL 2.16.0 → 2.17.0, PAD 3.19.0 → 3.20.0, DEPLOYMENT header re-verification, the API guide (no API contract changes — the response bytes pinned byte-identical; the re-verification noted), ci.yml header counts, `.env.example`s re-verified (no new env vars expected).

## 3. The execution plan (phases, TDD)

### Phase 1 — RED: the query-count regression specs

NEW `apps/backend/tests/integration/test_reconcile_query_counts_p30.py` — two gates (reconcile POST, unreconcile POST), reusing the `detail_fx`-style fixture conventions (the `test_organisation`/`test_user`/`test_accounts`/`test_fiscal_period`/`auth_client` fixtures + a direct `BankTransaction` + a received payment) and `django.test.utils.CaptureQueriesContext`:

| Task | Test (RED first) |
|---|---|
| T1 | Under the capture context, POST `/api/v1/<org>/banking/bank-transactions/<id>/reconcile/` then POST `.../unreconcile/`; assert on each: (a) the bank-transaction fetch query **carries the `banking"."bank_account` JOIN** (read the SQL — the fixed-related-row assertion shape, per the P29 lesson: the walk count does not distinguish a JOIN from a fixed walk; the JOIN presence does) — RED now: the fetch is single-table and the bank_account rides its own walk; (b) the counter-pins: `is_reconciled` flips true then false, `bank_account_name` present in both payloads (the fix must not change the bytes). URL anchors (verified): `/api/v1/<org>/banking/bank-transactions/<id>/reconcile/`, `.../unreconcile/`. |

### Phase 2 — GREEN: the fixes

| Task | Fix | Verification |
|---|---|---|
| T2 | `ReconciliationService.reconcile` locked fetch → `.select_for_update().select_related("bank_account")`; the comment records the P30 contract. | T1 reconcile GREEN · the banking suites green |
| T3 | `ReconciliationService.unreconcile` locked fetch → the same chain. | T1 unreconcile GREEN · the banking suites green |
| T4 | The ruff mechanical closure (H1, four phases: W291/W293 → I001 → F401 reviewed → per-file-ignores + the settings F401s). Per-phase `git diff --stat` review; no `--unsafe-fixes`; no edits outside the mechanical classes. | `ruff check --select W291,W293,I001,F401,F403,F405 apps/ common/ config/` **exit 0**; the whole-tree count **928 → 278**; Django system check + boot green |
| T5 | The full backend suite — every existing pin (the P24-P29 envelope + query-level contracts, the service tests, the RLS gates) holds. | `pytest` **1028+2P/0F/5S** (the new gates add; nothing replaces) |
| T6 | The mechanical-class ratchet: the `make lint:mechanical` target (+ the Makefile help line) + the ci.yml step in `backend-tests`. | `make lint:mechanical` exit 0 locally; the ci.yml YAML valid |

### Phase 3 — the full gate matrix + the screenshots

1. The complete gate set on the remediated tree (both backends restarted on the remediated code first — the `--noreload` lesson): backend `pytest` **1030P/0F/5S** · vitest **698/698 (85 files)** (web tree untouched) · `test:coverage` green at the standing ratchets · `tsc` 0 · whole-tree `eslint` 0E/0W · live `test:e2e:full` **43/43** · `rls_smoke` **13/13** · `mobile-nav-audit.js` **17/17** (the twenty-ninth settlement) · the `translate` probe re-PASS · `npm audit` **0** (dev+prod) · `build:server` green + `prod-csp-smoke.js` 5/5 · **the live API contract re-verification** (the bank-transactions list envelope + a reconcile round-trip — the byte-identical proof).
2. Screenshots: 8 DOM-verified captures (`docs/screenshots/192-199_*_session57.png`, md5-unique + non-blank pixel-verified, the session-55 capture conventions) — the banking surfaces (the P30 headline surface: the transactions list + the reconciliation area), the invoice detail, the ledger, the dashboard, the mobile drawer closed/open.
3. The `.env.example` truth verification (the config-readers sweep re-run; no new env vars expected).

### Phase 4 — the docs truth pass

| Doc | Update |
|---|---|
| README.md | the badge/test arithmetic (backend 1030), the status-table rows, the P30 milestone section |
| CLAUDE.md | version 2.30.0 → 2.31.0, the status block, the P30 milestone block |
| AGENTS.md | the header gate row, the P30 lessons |
| ledgersg_SKILL.md | the quick-ref numbers, version 2.16.0 → 2.17.0 |
| Project_Architecture_Document.md | the lint/test count rows, version 3.19.0 → 3.20.0 |
| docs/DEPLOYMENT.md | the header re-verification line (session 57 / P30); re-validate the fresh-host walkthrough against the current tree |
| API_CLI_Usage_Guide.md | re-verify the documented contracts against the live stack (the response bytes pinned byte-identical — no version bump; the re-verification noted) |
| .github/workflows/ci.yml | the header comment counts + the NEW mechanical-lint step |
| `.env.example` ×3 | re-verified truthful (no changes expected) |

## 4. Deferred register (updated, carried forward)

**Fixed this sprint (removed from the register):** the ruff mechanical batch (BE-P30-H1 — the registered 928-finding production batch, mechanical classes closed 650 → 0, the register's blind-`--fix` trap defused); the fourth-surface reconcile/unreconcile walk (BE-P30-M2 — the P29-class completion); the ungated `make lint` (CFG-P30-M3 — the closed classes now ratcheted in CI).

**Still deferred (with rationale, unchanged unless noted):**
- **The ruff semantic batch — now 278 production findings** (was 928): B904×66 (raise-from chaining — 66 reviewed edits, a sprint of its own), UP045/UP006/UP007/UP035×109 (typing modernization — safe-marked but semantics-adjacent; leans on a mypy gate that itself has 1491 errors), E501×39 + `ruff format` (80 files would reformat — the `make format` axis), F841×16, E402×12 (the deliberate end-of-file circular-avoidance imports), SIM105×7, B009×6, S110×4 (the verified fail-closed XSD loads), A001/E741/N806×6, B017/B905/F402/N802×4.
- **The tests/-tree lint batch (379 findings incl. F811×27, F821×2)** — the conftest string-annotation nits + the redefined-name smells; needs the same reviewed-sprint treatment with fixture side-effect care.
- **The `/accounts/search/` limit-contract migration** — unchanged (verified again this session: the endpoint is capped + typed; the frontend never calls it; a backend-only contract nicety).
- **The capped-default flip** — unchanged.
- **The audit-log INSERT policy** (DDL — verified this session: `rls_insert_event_log` is `WITH CHECK (TRUE)` for the SECURITY DEFINER trigger; tightening needs the every-emission-path analysis) — unchanged.
- **BE-L3 config-class locking; BE-L4 Peppol log-state locking; CSV errors[] raw strings; dead-letter design; UEN checksum; NULL-context SELECT tradeoff; H-05b models; PaymentsTab prefill; TanStack incompatibility; the membership-cache window; the P20-era FE-M2/M3 designs; CI hardening (the mypy gate — 1491 errors); the version-story reconciliation** — the P21–P29 deferred registers carry forward unchanged.

## 5. Acceptance criteria

- The query-count pins (executed): a reconcile/unreconcile request fetches the bank-transaction row WITH the bank_account JOIN — never a separate walk; the response bytes stay identical (the existing contract suites green, the e2e 43/43).
- The mechanical classes at **0** on the production tree (`ruff check --select W291,W293,I001,F401,F403,F405 apps/ common/ config/` exit 0); the whole-tree count **928 → 278**; `make lint:mechanical` exit 0; the ci.yml step in place.
- The backend suite green (**1030P/0F/5S** expected — +2 the new gates); no frontend change; the web gates green at the standing ratchets.
- `skills/` untouched by code checks; `git status` shows only the intended files.
- Plan + report saved under `docs/` in the `REMEDIATION_*_P30*` convention; the session log `docs/session_58.md`; the worklog updated.

## 6. Open decisions (resolved with judgment)

- **The per-file-ignore, not the conversion, for the settings star imports:** the Django split-settings idiom is a pass-through contract — `from .base import *` must keep flowing every future base addition into the derived modules; an explicit-import conversion would silently drop them (the drift class this repo registers as a lesson). The per-file-ignore documents the contract in ONE place with the rationale; the conversion would scatter it across 29 usage sites.
- **The redundant try-imports are DROPPED, not noqa'd:** `include("apps.X.urls")` raises the same `ImportError` inside the same `try` — the probe import adds nothing; removing it is behaviour-identical and honest.
- **`ruff format` stays out:** 80 reformatted files is a different axis (`make format`, never gated) with its own review burden; bundling it would bury the mechanical-closure diff. Registered as the follow-up with the honest count.
- **The tests/ tree stays out:** the registered item is the production batch; the tests tree carries F811/F821 classes that need fixture side-effect care — a different review. Registered with the count (379).
- **No `--unsafe-fixes` anywhere:** the 96 hidden F401 fixes are reviewed by hand instead (the register's exact warning — blind fixing beside star imports is the trap this sprint defuses).
- **The lock-scope note on M2:** chaining `select_related` onto `select_for_update` extends the row lock to the joined `bank_account` row — verified benign (a reference row no sibling path locks after transactions; concurrent reconciles on the same account acquire it FIRST consistently). Documented in the service comment.
- **No new e2e spec:** the walk is invisible to the browser (the response bytes are the contract, already pinned); the query-level truth needs the capture-context specs (the P28/P29 open decision, re-applied).
