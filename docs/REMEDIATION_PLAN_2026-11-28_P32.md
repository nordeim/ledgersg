# LedgerSG — Remediation Plan (P32 Sprint: The Dead-Code & Shadow-Fragility Closure + The Tests-Tree Residual + The Extended Closed-Class Ratchet)

**Date:** 2026-11-28 (session 62)
**Base commit:** `ebd4aa0b` (main — post-P31 + the session-60/61 logs)
**Method for execution:** TDD (RED → GREEN → full gate) for the one behavioural contract (the fixture-placement seam — the M2 conftest resolution); the reviewed lint batches verified by per-phase diffs + the full test matrix; `skills/` excluded from all checks/tests/compilation; **no schema changes** (v1.2.2 carries forward); **no frontend component changes** (the web tree is untouched).
**Skills consulted:** `skills/skills-catalog.md` → `tdd` (the red→green loop), `code-review`/`code-review-checklist` (Mode C discipline), `debugging-and-error-recovery` (root-cause isolation on any RED surprise), `rootless-postgresql` (the PG environment — recovered this session after the sandbox recycle damaged the data directory, §1), `agent-browser` (the live mobile-nav + translate probes — executed this session, §1), `nextjs16-tailwind4`/`tailwind-patterns` (consulted for the mobile-nav focus — the surface re-settled clean, §1).

---

## 1. Audit inputs (this session's evidence)

- **Repo + docs truth pass:** fresh `git clone` (the workspace had been reset); full reads of `AGENTS.md`, `CLAUDE.md` v2.32.0, `README.md`, `Project_Architecture_Document.md` v3.21.0, `ledgersg_SKILL.md` v2.18.0, `worklog.md`, `docs/session_60.md`, `docs/session_61.md`, the P31 plan + report.
- **The environment (recovered this session after the sandbox recycle):** the rootless **PG 17** data directory had lost its empty structural subdirectories (`pg_notify`, `pg_stat`, `pg_logical/snapshots`, …) to the recycle — recovered by recreating them (the databases, all 8 schemas and the three roles survived intact; `ledgersg_dev` + `test_ledgersg_dev` verified). **Redis 8** re-provisioned rootless on :6379. The backend venv rebuilt (`pip install -e ".[dev]"` — Django 6.0.10, ruff 0.15.2, pytest 9.0.2). The web `node_modules` rebuilt with `npm ci` after the interrupted first install corrupted two native binaries (rollup + lightningcss SIGBUS — the `npm install-scripts` approval for esbuild/unrs-resolver applied; `npm audit` 0). Playwright chromium re-provisioned for 1.58.2. `next dev` on :3000 + the backends (:8000 dev, :8001 RLS-as-`ledgersg_app`) re-daemonised through `scripts/daemonize.py`.
- **The baseline reproduction (pre-change, this session — all gates exact):** backend `pytest --reuse-db --no-migrations -q` **1034P/0F/5S** (28.81s) · vitest **698/698 (85 files)** · `npx tsc --noEmit` **0 errors** · whole-tree `npx eslint . --max-warnings 5` from `apps/web` **0E/0W** · live `test:e2e:full` **43/43 (2.6m, deterministic, first run)** · `rls_smoke.py` **13/13 as `ledgersg_app`** · `mobile-nav-audit.js` **17/17** (the thirty-second settlement) · the dedicated Tailwind v4 `translate` probe (`scripts/translate-probe-session53.js`): **PASS** (7 mid-flight samples, `transitionProperty "transform, translate, visibility"`) · `npm audit` **0 across dev+prod** · `build:server` green + `prod-csp-smoke.js` **5/5** · `make lint-mechanical` exit 0 · the production ruff count **211** exact · the tests-tree count **157** exact. **All documented gates reproduced exactly — the P31 state holds.**
- **The named focus — the mobile-nav verdict (thirty-second settlement):** **WORKING as expected; NO remaining TailwindCSS v4 bug on this surface.**
- **The audit (Mode C) of the P31 slice** (commits `92e4285b`..`2370f7c4`, hand-verified in source this session): `ruff check --select B904 apps common config tests` → **"All checks passed!"** (the 66-site closure holds); the unified ratchet green; `tests/integration/test_exception_chaining_p31.py` present (4 gates, all in the 1034); the Makefile `lint-mechanical` target + the CI step carry the unified class set — **0 new findings in the P31 slice**.
- **The standing test-suite task (user instruction: "add vitest and playwright test suite by modifying the respective config files"):** verified IN PLACE and current — `apps/web/vitest.config.ts` (jsdom, the setup file, the whole-suite + per-glob coverage tiers) and `apps/web/playwright.config.ts` (chromium default, the live-suite serialisation contract, the E2E_API_URL gating), driving **698 vitest specs (85 files) + 43 e2e specs (12 files)** — all green this session.
- **The lint truth (measured this session):** production tree `apps/ common/ config/` — **211 findings** (UP045×45, E501×39, UP006×35, F841×16, E402×13, UP007×13, UP035×12, SIM105×10, B009×6, S110×4, S105×3, A001×2, E741×2, N806×2, B017/B905/F402/N802/N818/S608/SIM108/SIM110/UP015 ×1 each). Tests tree `tests/` — **157 findings** (E501×73, F811×26, F841×9, S106×8, SIM117×8, C408×7, B007×6, E741×4, F821×2, S108×2, SIM300×2, A001/B905/N806/S105/S110/SIM103/SIM105/SIM118/UP017 ×1 each). The in-tree test dirs (`apps/*/tests/`) carry the S105×3 + B009×6 + B017×1 + N802×1 + F841×13 counted in the production number.
- **The fresh findings (this session's one-seam-deeper sweeps):**
  - **F402 (the one live fragility):** `apps/invoicing/views.py:504` — the loop variable `status` in `DocumentSummaryView.get()` shadows the module-level `from rest_framework import status`. Harmless today (no `status.` use after the loop in that method) but a live trap: any future `status.HTTP_200_OK` added to that method crashes at runtime with AttributeError. Verified: the method builds its `Response` without the status module.
  - **The 3 production F841s (dead bindings at service seams — each reviewed):** `payment_service.py:404` (`reversal` — assigned in both branches, never read; `create_reversal` is the side effect), `document_service.py:529` (`old_status` — a refactor leftover; the transition audit reads status elsewhere), `document_service.py:938` (`fiscal_period` — the guard-query get; the membership check is the point, the binding is dead).
  - **F811 ×26 (the tests-tree fixture class — the architectural finding):** every one is the SAME pattern — `payment_fixture` is DEFINED in `tests/integration/test_payment_allocation_contract_p14.py`, then IMPORTED by 7 sibling test files purely so pytest can resolve the fixture (the import-is-the-side-effect class), and each consuming test's PARAMETER named `payment_fixture` then shadows the import → F811 fires 24 times + `_receive` ×2. The clean fix is the conftest placement: pytest auto-discovers `tests/integration/conftest.py` fixtures with NO import, closing the class architecturally (not with 26 noqas).
  - **F821 ×2 (tests/conftest.py:298,317):** string annotations `-> "Contact"` where `Contact` is imported inside the function body — inert at runtime (never evaluated) but genuinely unresolvable at module scope. The correct fix is the `TYPE_CHECKING` import.
  - **S608 ×1 (gst/calculation_service.py:257):** FALSE POSITIVE — the raw-SQL f-string embeds only a `%s` placeholder list built from a module-level constant tuple; every value flows through params. Closes with the documented noqa, not a rewrite.
  - **S105×3 + S106×8 + S108×2 (test trees):** literal passwords in test fixtures (by design — they are not secrets) and the fixed `/tmp/ledgersg-p11-gate` path (the test's own expected-value pair, not an insecure write). Close via the tests per-file-ignores with the documented rationale.
  - **B017 ×1 (apps/peppol/tests/test_tasks.py:97):** `pytest.raises(Exception)` over a mocked network failure — the blind assert any exception passes, including programming errors. Tighten to the exception class the retry actually raises.
  - **S110 ×4 (production):** re-verified as the registered fail-closed designs (the two XSD loads, the rollback best-effort, the token-context user resolution) — STAY REGISTERED (semantic decisions, not mechanical closures).

**Combined findings (this session's audit): 0 Critical / 1 High / 2 Medium / 1 Low.**

## 2. Findings (verified, with evidence anchors)

### High

**BE-P32-H1 — the production dead-code, shadow-fragility + suppressible-exception closure: 62 findings across the small classes the P30/P31 sprints deliberately left for their own reviewed pass.**
Three concrete harms:
1. **The dead bindings sit at money-flow seams** (`void`, `transition_status`, `approve_document`) — a reader must ask whether the dead `old_status`/`reversal`/`fiscal_period` binding hides a missing behaviour (the review this session proves each genuinely dead, but every future reader re-pays that review).
2. **The F402 shadow is a live trap** — one added `status.HTTP_xxx` in `DocumentSummaryView.get()` is a runtime crash the type checker does not catch (the shadowed name is a valid str).
3. **The register's standing count (211) buries any NEW finding** in these classes — the same signal-burial harm every prior closure sprint cites.

**The classification (every site reviewed this session):**
- **Dead bindings (F841 ×16):** the 3 service seams above + 13 in `apps/*/tests/` (each an unused local in a test helper — reviewed by name, none hides a missed assertion).
- **The shadow-fragility (F402 ×1):** the loop-variable rename `status` → `status_value`.
- **The ambiguous/builtin-shadowing names (E741 ×2, A001 ×2, N806 ×2, N802 ×1):** `l` → `line` (journal_service ×2), `credits` → `credit_total` (journal_service ×2 — `credits` shadows a Python builtin), `ALLOCATABLE_STATUSES`/`POSTING_TYPES` → lowercase locals (payment.py, calculation_service.py), the test helper `D` → a descriptive name.
- **The suppressible-exception rewrites (SIM105 ×10):** `config/urls.py` ×7 (the ImportError-guarded includes — the documented P30 pattern; `with suppress(ImportError):` is byte-identical semantics), `reconciliation_service.py` ×2 (the CSV best-effort parses), `journal_service.py` ×1 (the deliberate pass-through pre-lock check, comment preserved).
- **The small hardening (B905 ×1, SIM108 ×1, SIM110 ×1, UP015 ×1, B009 ×6, B017 ×1):** `zip(strict=…)` where the lengths are contractually equal (coa/services), the ternary/any() rewrites (decimal_utils, tenant_context), the redundant open mode (test_runner), the constant-attr `getattr` calls (peppol tests ×6), the blind-exception assert tightened to the retry's own class.
- **The documented false positive (S608 ×1):** the parameterized raw SQL — noqa + the rationale comment.
- **The deliberate end-of-file imports (E402 ×13):** the Django circular-avoidance pattern (each site already carries its rationale comment) — noqa closes the class honestly (the alternative — moving the imports — reintroduces the circulars).

**Fix:** the per-class edits above. Verified safe: every rewrite is semantics-preserving (the full 1034-test suite is the arbiter; the HTTP contracts byte-identical — no view changes beyond a local variable name).

### Medium

**BE-P32-M2 — the tests-tree non-format residual: 84 findings (the F811 architectural class + the mechanical small classes), leaving only E501×73 + S110×1 registered.**
The headline is the **F811 ×26 closure via the conftest placement**: move `payment_fixture` (and its `_receive` companion) from `test_payment_allocation_contract_p14.py` into `tests/integration/conftest.py`, drop the cross-module imports from the 7 consuming files. The fixture's dependency set (`test_organisation`, `test_user`, `test_accounts`, `test_tax_codes`, `test_fiscal_period` — all from `tests/conftest.py`) is conftest-compatible unchanged. The mechanical remainder: F841×9, SIM117×8, C408×7, B007×6, E741×4, F821×2 (the TYPE_CHECKING fix), SIM300×2, S105×1/S106×8/S108×2 (the tests per-file-ignores — the literal passwords and the fixed /tmp literal are test-design, not secrets), A001/B905/N806/SIM103/SIM105/SIM118/UP017 ×1 each.

**Fix:** the conftest move + the per-class mechanical edits + the per-file-ignores block (`"**/tests/**" = ["S105", "S106", "S108"]` with the documented rationale).

**CFG-P32-M3 — the extended closed-class ratchet: `make lint-mechanical` still gates only the P30+P31 class set.**
After H1 + M2 close, pin the extended contract: the closed set becomes `W291,W293,I001,F401,F403,F405,B904` **+** `F841,F811,F402,E741,A001,N806,N802,B007,B009,B017,B905,C408,SIM103,SIM105,SIM108,SIM110,SIM117,SIM118,SIM300,UP015,UP017,S608,E402,S105,S106` over `apps/ common/ config/ tests/` (the noqa'd + per-file-ignored classes stay 0 by construction — the ratchet catches any NEW finding, including a hardcoded password introduced in production code). The Makefile target + the CI step update together, tab-safe.

### Low

**DOC-P32-L1 — the docs truths roll forward with the sprint** (the standing DOC-L pattern): README badge/counts + the P32 milestone, CLAUDE 2.32.0 → 2.33.0, AGENTS header + the P32 lessons, SKILL 2.18.0 → 2.19.0, PAD 3.21.0 → 3.22.0, DEPLOYMENT header re-verification, the API guide (no API contract changes — the re-verification noted), ci.yml header counts, `.env.example`s re-verified (no new env vars expected).

## 3. The execution plan (phases, TDD)

### Phase 1 — RED: the fixture-placement contract

NEW `apps/backend/tests/integration/test_conftest_fixture_resolution_p32.py` — ONE gate pinning the architectural contract:

| Task | Test (RED first) |
|---|---|
| T1 | **The no-import fixture resolution:** a test class whose methods take `payment_fixture` (and `_receive` where applicable) as parameters, with NO cross-module import in the file — asserting the fixture builds the approved-109.00-invoice substrate (org + bank + contact + invoice with `amount_paid` tracking). RED now: pytest reports `fixture 'payment_fixture' not found` (the fixture lives in a sibling test module, reachable only via the import). GREEN after the conftest move. |

### Phase 2 — GREEN: the fixes

| Task | Fix | Verification |
|---|---|---|
| T2 | **The conftest move (M2 headline):** `payment_fixture` + `_receive` (+ their model imports) move verbatim to `tests/integration/conftest.py`; the 7 consuming files drop their cross-module imports (the `# noqa: F401` import blocks); `test_payment_allocation_contract_p14.py` drops its own definitions (conftest resolves). | T1 GREEN; `ruff check --select F811 tests/` → **0**; the full suite green (every existing consumer proves the resolution) |
| T3 | **The H1 dead-binding closure:** the 3 service seams (drop the dead bindings, keep the side-effect calls + the guard-query, comments preserved) + the 13 in-tree test locals. | `ruff check --select F841 apps common config` → **0**; per-file diffs reviewed (binding-removal only); the full suite green |
| T4 | **The H1 shadow/name/suppress batch:** F402 rename, E741×2, A001×2, N806×2, N802×1, SIM105×10, B905, SIM108, SIM110, UP015, B009×6, B017, S608-noqa, E402×13-noqa. | `ruff check --select F402,E741,A001,N806,N802,SIM105,B905,SIM108,SIM110,UP015,B009,B017,S608,E402 apps common config` → **0**; the Django boot + system check clean |
| T5 | **The M2 mechanical remainder:** F841×9, SIM117×8, C408×7, B007×6, E741×4, F821×2 (TYPE_CHECKING), SIM300×2, A001/B905/N806/SIM103/SIM105/SIM118/UP017, + the per-file-ignores block for S105/S106/S108. | `ruff check tests/` count **157 → 74** (E501×73 + S110×1 only); the full suite green |
| T6 | **The extended ratchet (M3):** the Makefile `lint-mechanical` target + the CI step gain the extended class set (tab-safe edit, the recipe line byte-verified to carry its TAB). | `make lint-mechanical` exit 0; the ci.yml YAML valid |
| T7 | **The full backend suite** — every existing pin holds. | `pytest --reuse-db --no-migrations -q` **1035P/0F/5S** expected (+1 the T1 gate) |

### Phase 3 — the full gate matrix + the screenshots

1. The complete gate set on the remediated tree (both backends restarted on the remediated code — the `--noreload` lesson): backend `pytest` **1035P/0F/5S** · vitest **698/698 (85 files)** (web tree untouched) · `tsc` 0 · whole-tree `eslint` 0E/0W · live `test:e2e:full` **43/43** · `rls_smoke` **13/13** · `mobile-nav-audit.js` **17/17** (the thirty-third settlement) · the `translate` probe re-PASS · `npm audit` **0** (dev+prod) · `build:server` green + `prod-csp-smoke.js` **5/5** · **the live API contract re-verification** (a representative not-found 404 body + a typed-400 validation body — byte-stable against the pre-change capture; the F402/F841 surfaces: the document-summary endpoint re-verified live).
2. Screenshots: 8 DOM-verified captures (`docs/screenshots/208-215_*_session62.png`, md5-unique + non-blank pixel-verified, the session-55 capture conventions) — the P32 headline surfaces featured (the document summary/report view — the F402 seam — + the void-path surface), plus the standing set (invoices, ledger, banking, dashboard, the mobile drawer closed/open).
3. The `.env.example` truth verification (the config-readers sweep re-run; no new env vars expected).

### Phase 4 — the docs truth pass

| Doc | Update |
|---|---|
| README.md | the badge/test arithmetic (backend 1035), the status-table rows, the P32 milestone section |
| CLAUDE.md | version 2.32.0 → 2.33.0, the status block, the P32 milestone block |
| AGENTS.md | the header gate row, the P32 lessons (the conftest-placement lesson; the dead-binding review class) |
| ledgersg_SKILL.md | the quick-ref numbers, version 2.18.0 → 2.19.0 |
| Project_Architecture_Document.md | the lint/test count rows, version 3.21.0 → 3.22.0 |
| docs/DEPLOYMENT.md | the header re-verification line (session 62 / P32); re-validate the fresh-host walkthrough against the current tree |
| API_CLI_Usage_Guide.md | re-verify the documented contracts against the live stack (the response bytes pinned byte-identical — no version bump; the re-verification noted) |
| .github/workflows/ci.yml | the header comment counts + the EXTENDED mechanical-lint step |
| `.env.example` ×3 | re-verified truthful (no changes expected) |

## 4. Deferred register (updated, carried forward)

**Fixed this sprint (removed from the register):** the production dead-code/shadow/suppress batch (BE-P32-H1 — 62 findings → 0); the tests-tree non-format residual (BE-P32-M2 — 84 findings → 0, the F811 class closed architecturally via the conftest placement); the extended closed-class ratchet (CFG-P32-M3).

**Still deferred (with rationale, unchanged unless noted):**
- **The ruff semantic batch — now 149 production findings** (was 211, the 62 small-class findings closed): UP045/UP006/UP007/UP035×105 (typing modernization; safe-marked but semantics-adjacent; leans on a mypy gate that itself has 1491 errors — the mypy-gate conversation stays the registered precondition), E501×39 + `ruff format` (160 files would reformat — the `make format` axis), S110×4 (the verified fail-closed XSD loads), N818×1 (the LedgerSGException rename — touches every importer; its own reviewed pass).
- **The tests/-tree residual — now 74 findings** (was 157): E501×73 (the format axis), S110×1 (the fail-closed design).
- **The `/accounts/search/` limit-contract migration** — unchanged (verified again: capped + typed; no frontend consumer).
- **The capped-default flip** — unchanged.
- **The audit-log INSERT policy** (DDL — `WITH CHECK (TRUE)` for the SECURITY DEFINER trigger; tightening needs the every-emission-path analysis) — unchanged.
- **BE-L3 config-class locking; BE-L4 Peppol log-state locking; CSV errors[] raw strings; dead-letter design; UEN checksum; NULL-context SELECT tradeoff; H-05b models; PaymentsTab prefill; TanStack incompatibility; the membership-cache window; the P20-era FE-M2/M3 designs; CI hardening (the mypy gate — 1491 errors); the version-story reconciliation** — the P21–P31 deferred registers carry forward unchanged.

## 5. Acceptance criteria

- The fixture-placement gate (executed): the T1 RED spec GREEN — `payment_fixture` resolves with NO cross-module import.
- `ruff check --select F841,F811,F402,E741,A001,N806,N802,B007,B009,B017,B905,C408,SIM103,SIM105,SIM108,SIM110,SIM117,SIM118,SIM300,UP015,UP017,S608,E402 apps common config tests` → **0** (the per-file-ignores scoped to the test trees).
- The production count **211 → 149**; the tests count **157 → 74** (the arithmetic exact, no new findings).
- The backend suite green (**1035P/0F/5S** expected — +1 the new gate); no frontend change; the web gates green at the standing ratchets.
- `make lint-mechanical` exit 0 on the EXTENDED command; the ci.yml step updated; the YAML valid.
- The live contract re-verification: the not-found/validation response bodies byte-identical; the document-summary endpoint live-verified.
- `skills/` untouched by code checks; `git status` shows only the intended files.
- Plan + report saved under `docs/` in the `REMEDIATION_*_P32*` convention; the session log `docs/session_62.md`; the worklog updated.

## 6. Open decisions (resolved with judgment)

- **The conftest placement over 26 noqas:** the F811 class closes architecturally (the fixture moves to `tests/integration/conftest.py`) rather than suppression — the import-is-the-side-effect pattern was always a workaround for the missing conftest; pytest's own resolution model is the contract. The 7 consuming files get SIMPLER (import blocks deleted). The `_receive` helper moves with it (it is the fixture's companion API; the 2 `_receive` F811s close with the same move).
- **The S105/S106/S108 closure via per-file-ignores, not noqas:** the literal passwords in test fixtures and the fixed `/tmp` expected-value are test DESIGN, not incidents — the per-file-ignores block is the single documented place for that contract (the same pattern as the settings star-imports). The ratchet still selects the classes: a hardcoded password introduced in PRODUCTION code fails the gate.
- **The E402 closure via noqa, not import moves:** the 13 end-of-file imports are the Django circular-avoidance pattern, each already commented; moving them reintroduces the circulars. The noqa + existing rationale comments close the class honestly.
- **The S608 false positive closes with the noqa + rationale:** the f-string embeds only `%s` placeholders from a module constant; every value flows through params. A rewrite (e.g. building the SQL by concatenation-free means) would be noise.
- **The S110 ×4 stay registered:** the fail-closed designs are semantic decisions (the XSD loads, the rollback best-effort, the token-context resolution) — converting to `contextlib.suppress` changes nothing semantically but S110 keeps firing on `suppress(Exception)` shapes; the honest state is the register.
- **The N818 rename stays out:** `LedgerSGException` is the exported base exception name; the Error-suffix rename touches every importer for a naming-convention win — its own reviewed pass if ever taken.
- **The UP batch stays out (again):** the mypy-gate conversation (1491 errors) remains the registered precondition; this sprint closes the classes that need NO such conversation.
- **E501 + the format axis stays out (again):** 160 files would reformat — its own sprint with its own review burden; the register keeps the honest counts.
- **No new e2e spec:** the closures are invisible to the browser (the response bytes are the contract, pinned by the existing suites + the live re-verification); the fixture-placement truth needs the pytest-level capture spec.
