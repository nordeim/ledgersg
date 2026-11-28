# LedgerSG — Remediation Plan (P31 Sprint: The B904 Raise-From Closure + The Tests-Tree Mechanical Extension + The Closed-Class Ratchet Unification)

**Date:** 2026-11-28 (session 59)
**Base commit:** `933af819` (main — post-P30 + the session-58/59 logs)
**Method for execution:** TDD (RED → GREEN → full gate) for the behavioural contract (the chaining pins); the reviewed lint batches verified by per-phase diffs + the full test matrix; `skills/` excluded from all checks/tests/compilation; **no schema changes** (v1.2.2 carries forward); **no frontend component changes** (the web tree is untouched).
**Skills consulted:** `skills/skills-catalog.md` → `tdd` (the red→green loop), `code-review`/`code-review-checklist` (Mode C discipline), `debugging-and-error-recovery` (root-cause isolation on any RED surprise), `rootless-postgresql` (the PG environment — live from the prior sessions, re-probed this session), `agent-browser` (the live mobile-nav + translate probes — executed this session, §1), `nextjs16-tailwind4`/`tailwind-patterns` (consulted for the mobile-nav focus — the surface re-settled clean, §1).

---

## 1. Audit inputs (this session's evidence)

- **Repo + docs truth pass:** `git pull` to `933af819` clean on `main` (the only delta from the P30 push: `docs/session_59.md`); full reads of `AGENTS.md`, `CLAUDE.md` v2.31.0, `README.md`, `Project_Architecture_Document.md` v3.20.0, `ledgersg_SKILL.md` v2.17.0, `worklog.md`, `docs/session_58.md`, `docs/session_59.md`, the P30 plan + report.
- **The environment (live, re-probed):** rootless **PG 17** on :5432 (both `ledgersg_dev` + `test_ledgersg_dev` present, schema verified), **Redis** on :6379, the backend venv (`apps/backend/.venv` — Django 6.0.10, ruff 0.15.2), `node_modules`, `next dev` on :3000 (survived the sandbox recycle). The backends were re-daemonised this session through `scripts/daemonize.py` (:8000 dev, :8001 RLS-as-`ledgersg_app`) and survived the shell-call boundary. **No environment repair was required.**
- **The baseline reproduction (pre-change, this session — all gates exact):** backend `pytest --reuse-db --no-migrations -q` **1030P/0F/5S** (30.01s) · vitest **698/698 (85 files)** (107.96s) · `npx tsc --noEmit` **0 errors** · whole-tree `npx eslint . --max-warnings 5` from `apps/web` **0E/0W** · live `test:e2e:full` **43/43 (2.3m, deterministic, first run)** · `rls_smoke.py` **13/13 as `ledgersg_app`** · `mobile-nav-audit.js` **17/17** (the thirtieth settlement) · the dedicated Tailwind v4 `translate` probe (`scripts/translate-probe-session53.js`): **PASS** (7 mid-flight samples, `transitionProperty "transform, translate, visibility"`) · `npm audit` **0 across dev+prod** · `build:server` green + `prod-csp-smoke.js` **5/5** · `make lint-mechanical` exit 0 · the production ruff count **277** (the P30 remainder, exact).
- **The named focus — the mobile-nav verdict (thirtieth settlement):** **WORKING as expected; NO remaining TailwindCSS v4 bug on this surface.**
- **The audit (Mode C) of the P30 slice** (commits `791c6499`..`2c988499`, hand-verified in source this session): both locked fetches chain `.select_for_update().select_related("bank_account")` with the P30 contract comments (`reconciliation_service.py:356-362,437-440`), the per-file-ignores block sits in `pyproject.toml` with the pass-through rationale, `make lint-mechanical` + the CI step are in place, the query-count spec exists — **0 new findings in the P30 slice**. (One log-level false alarm investigated and cleared: a `SyntaxWarning` for `contact_service.py:284` appeared in the appended `/tmp/be8000.log` from a PRE-P30 boot; the current source carries `\\d` and compiles clean under `-W error::SyntaxWarning`.)
- **The companion sweep (the exception-handling surfaces — the natural class around B904):** the 4 S110 try-except-pass sites re-verified as the registered fail-closed designs (the two XSD loads `xml_validation_service.py:61,71`, the rollback best-effort `common/exceptions.py:212`, the token-context user resolution `tenant_context.py:214`); the one BLE001 broad catch (`document_service.py:84`) is noqa'd with the logging contract. The existing raise-from exemplars establish the convention: **`from exc` for cause-preserving translations** (`gst/return_service.py:94`, `peppol/transmission_service.py:80-90`, `payment_service.py:322`, `common/query_params.py:21-56`, `auth_service.py:137-179`), **`from None` only for deliberate noise** (`journal/views.py:362`, `auth_service.py:161`).
- **The lint truth (measured this session):** production tree `apps/ common/ config/` — **277 findings**, of which **B904 ×66** (the register's own "suggested next sprint": 21 files; `document_service.py` ×12, `payment.py`/`payment_service.py`/`transmission_service.py` ×5 each, `allocation.py`/`bank_transaction.py`/`reconciliation_service.py`/`journal_service.py`/`bank_account_service.py`/`organisations.py` ×3-4 each, the rest ×1-2). Tests tree `tests/` — **379 findings**, of which **221 in the P30-closed mechanical classes** (W293×99, F401×66, I001×56); the rest stay registered (E501×74, F811×27, F841×9, S106×8, SIM117×8, C408×7, B007×6, E741×4, F821×2 [verified: the `conftest.py:301,320` string-annotation nits — the import lives inside the function body], S108×2, …).
- **The standing test-suite task (user instruction: "add vitest and playwright test suite by modifying the respective config files"):** verified IN PLACE and current — `apps/web/vitest.config.ts` (jsdom, the setup file, the whole-suite + seven per-glob coverage tiers) and `apps/web/playwright.config.ts` (chromium default, the live-suite serialisation contract, the E2E_API_URL gating), driving **698 vitest specs (85 files) + 43 e2e specs (11 files)**. This sprint ADDS to them (the chaining pins, §3 T1).

**Combined findings (this session's audit): 0 Critical / 1 High / 2 Medium / 1 Low.**

## 2. Findings (verified, with evidence anchors)

### High

**BE-P31-H1 — the registered B904 raise-from batch: 66 production `raise`-inside-`except` sites with no explicit chaining — the P30 report's own "suggested next sprint".**
Today every one of these relies on Python's IMPLICIT `__context__` chaining: the raised domain error (`ResourceNotFound`, `serializers.ValidationError`, `ValidationError`, `ValueError`, Celery's `self.retry`) renders with "During handling of the above exception, another exception occurred" — the ambiguous accidental-chain wording — and any future refactor that moves the `raise` out of the `except` block silently drops the context entirely. Three concrete harms:
1. **The ambiguous traceback class:** "During handling…" reads as an accident, not a translation; `from exc` renders "The above exception was the direct cause…" — the distinction a production investigator needs.
2. **The silent-loss hazard:** implicit `__context__` is an implementation detail of WHERE the raise sits; explicit `__cause__` is a contract.
3. **The register's standing count:** 66 findings bury any NEW B904 the next change introduces.

**The classification (every site reviewed this session, two classes):**
- **Class A — `from exc` (62 sites):** every lookup-miss translation (`except Model.DoesNotExist: raise ResourceNotFound/ValidationError("… not found …")` — ~45 sites), every race translation (`IntegrityError` → the typed-400 bodies: `organisation_service.py:66,347`, `core/views/organisations.py:199,353`, `document_service.py:441` — the constraint name in the cause is diagnostic gold), the Django-password propagation (`core/serializers/auth.py:28,75` — matches the `auth_service.py:137-179 from e` exemplars), the ISO-date parse (`gst/views.py:76` — the original error carries the offending input), the money/box parses whose messages embed only the value (`allocation.py:104,145`, `bank_transaction.py:112`, `gst/views.py:410` — matching the `payment_service.py:322 from exc` exemplar), and the Celery retries (`invoicing/tasks.py:59`, `peppol/tasks.py:104,189` — `raise self.retry(exc=exc) from exc`).
- **Class B — `from None` (4 sites):** ONLY where the raised message already embeds the original error's own string (`{e}`) — `common/decimal_utils.py:51,93,109` ("Cannot convert {value!r} to money: {e}") and `reconciliation_service.py:163` ("Could not decode file: {e}") — there the suppressed context is pure duplication (matching the `journal/views.py:362` / `auth_service.py:161` deliberate-noise exemplars).

**Fix:** the per-class `from exc`/`from None` edit at all 66 sites. Verified safe: `__cause__`/`__suppress_context__` never touch the DRF/custom-exception HTTP rendering (`ResourceNotFound` renders from its own `default_message`/`default_code` — `common/exceptions.py:90-95`; the DRF `ValidationError` renders from its own data), so every response byte is pinned unchanged by the existing contract suites.

### Medium

**BE-P31-M2 — the tests-tree mechanical extension: 221 findings in the exact classes P30 closed on the production tree, still open on `tests/`.**
The P30 closure made `ruff check --fix` safe and the mechanical classes 0 — on `apps/ common/ config/`. The tests tree carries the same classes (W293×99, F401×66, I001×56): the same signal burial and the same blind-fix trap (an F401 autofix beside fixture-registrating imports). The F401 review: tests-tree unused imports need the per-file check for imports whose IMPORT is the side effect (fixture registration, `django_apps` conflation) — the same review P30 did for the `__init__.py` re-export class.

**Fix:** the same three reviewed phases (W291/W293 → I001 → F401 reviewed), then the class count → 0 on `tests/`. The F811×27 (redefined fixtures — `payment_fixture` ×24) and the rest STAY REGISTERED (fixture side-effect care; the register's own rationale).

**CFG-P31-M3 — the closed-class ratchet unification: `make lint-mechanical` covers only the production tree and only the P30 classes.**
After H1 + M2 close, pin the unified contract: `ruff check --select W291,W293,I001,F401,F403,F405,B904 apps/ common/ config/ tests/` must exit 0 — the whole tree's closed classes (the P30 four + B904 + the tests extension) behind ONE gate, in the Makefile AND the CI `backend-tests` step. B904 joins the "closed classes" set (its fix is manual — the from-exc/from-None choice is semantic — but the RATCHET only requires the count to stay 0).

### Low

**DOC-P31-L1 — the docs truths roll forward with the sprint** (the standing DOC-L pattern): README badge/counts + the P31 milestone, CLAUDE 2.31.0 → 2.32.0, AGENTS header + the P31 lessons, SKILL 2.17.0 → 2.18.0, PAD 3.20.0 → 3.21.0, DEPLOYMENT header re-verification, the API guide (no API contract changes — the response bytes pinned byte-identical; the re-verification noted), ci.yml header counts, `.env.example`s re-verified (no new env vars expected).

## 3. The execution plan (phases, TDD)

### Phase 1 — RED: the exception-chaining regression specs

NEW `apps/backend/tests/integration/test_exception_chaining_p31.py` — three gates pinning the contract on one representative seam per class:

| Task | Test (RED first) |
|---|---|
| T1 | **The cause-preserved service seam (Class A):** call `DocumentService.get_document(org_id, uuid4())` under `pytest.raises(ResourceNotFound)`; assert `exc_info.value.__cause__` is an `InvoiceDocument.DoesNotExist` instance — RED now (no explicit chain; `__cause__` is None). Plus the same shape on `ReconciliationService.get_transaction` (the P30 surface). |
| T2 | **The cause-preserved serializer seam (Class A):** drive `AllocationSerializer.validate_allocations` (or the equivalent money-parse path) with a non-numeric `allocated_amount`; assert the raised `serializers.ValidationError.__cause__` is the original `ValueError` — RED now. |
| T3 | **The deliberate-suppression seam (Class B):** call `common.decimal_utils.money("garbage")` under `pytest.raises(ValueError)`; assert `__cause__` is None AND `__suppress_context__` is True (the message embeds the original error string; the chain is pure duplication) — RED now (`__suppress_context__` False). |

### Phase 2 — GREEN: the fixes

| Task | Fix | Verification |
|---|---|---|
| T4 | The 62 Class-A sites gain `from exc` (or `from e`/`from err` matching each site's `as` binding); the 4 Class-B sites gain `from None`. No other edit rides along. | T1/T2/T3 GREEN; `ruff check --select B904 apps/ common/ config/` → **0**; the per-file `git diff` review (raise-line-only changes) |
| T5 | The tests-tree mechanical extension (M2): W291/W293 → I001 → F401-reviewed (the import-is-the-side-effect check per file), the same three phases P30 ran. | `ruff check --select W291,W293,I001,F401 tests/` → **0**; per-phase diffs; the F401 keep-set documented |
| T6 | The full backend suite — every existing pin holds (the HTTP contracts byte-identical: the chaining never touches the rendered bodies). | `pytest` **1030P/0F/5S** (unchanged count — the pins add assertions inside the same spec file? No: NEW file → **1033P/0F/5S** expected, +3 the new gates) |
| T7 | The unified ratchet: `make lint-mechanical` selects `W291,W293,I001,F401,F403,F405,B904` over `apps/ common/ config/ tests/` (+ the help text); the CI `backend-tests` step likewise. | `make lint-mechanical` exit 0 locally; the ci.yml YAML valid |

### Phase 3 — the full gate matrix + the screenshots

1. The complete gate set on the remediated tree (both backends restarted on the remediated code — the `--noreload` lesson): backend `pytest` **1033P/0F/5S** · vitest **698/698 (85 files)** (web tree untouched) · `test:coverage` green at the standing ratchets · `tsc` 0 · whole-tree `eslint` 0E/0W · live `test:e2e:full` **43/43** · `rls_smoke` **13/13** · `mobile-nav-audit.js` **17/17** (the thirty-first settlement) · the `translate` probe re-PASS · `npm audit` **0** (dev+prod) · `build:server` green + `prod-csp-smoke.js` 5/5 · **the live API contract re-verification** (a representative not-found 404 body + a typed-400 validation body — byte-stable against the pre-change capture).
2. Screenshots: 8 DOM-verified captures (`docs/screenshots/200-207_*_session59.png`, md5-unique + non-blank pixel-verified, the session-55 capture conventions) — the exception-contract surfaces featured (a not-found detail route + a typed-400 form error), plus the standing set (invoices, ledger, dashboard, banking, the mobile drawer closed/open).
3. The `.env.example` truth verification (the config-readers sweep re-run; no new env vars expected).

### Phase 4 — the docs truth pass

| Doc | Update |
|---|---|
| README.md | the badge/test arithmetic (backend 1033), the status-table rows, the P31 milestone section |
| CLAUDE.md | version 2.31.0 → 2.32.0, the status block, the P31 milestone block |
| AGENTS.md | the header gate row, the P31 lessons (the chaining contract; the tests-tree F401 review class) |
| ledgersg_SKILL.md | the quick-ref numbers, version 2.17.0 → 2.18.0 |
| Project_Architecture_Document.md | the lint/test count rows, version 3.20.0 → 3.21.0 |
| docs/DEPLOYMENT.md | the header re-verification line (session 59 / P31); re-validate the fresh-host walkthrough against the current tree |
| API_CLI_Usage_Guide.md | re-verify the documented contracts against the live stack (the response bytes pinned byte-identical — no version bump; the re-verification noted) |
| .github/workflows/ci.yml | the header comment counts + the UNIFIED mechanical-lint step |
| `.env.example` ×3 | re-verified truthful (no changes expected) |

## 4. Deferred register (updated, carried forward)

**Fixed this sprint (removed from the register):** the B904 raise-from batch (BE-P31-H1 — 66 → 0, the chaining contract documented + pinned); the tests-tree mechanical batch (BE-P31-M2 — 221 → 0 in the P30 classes); the ratchet split (CFG-P31-M3 — one gate covers the whole tree's closed classes).

**Still deferred (with rationale, unchanged unless noted):**
- **The ruff semantic batch — now 211 production findings** (was 277, B904's 66 closed): UP045/UP006/UP007/UP035×109 (typing modernization — safe-marked but semantics-adjacent; leans on a mypy gate that itself has 1491 errors), E501×39 + `ruff format` (80 files would reformat — the `make format` axis), F841×16, E402×12 (the deliberate end-of-file circular-avoidance imports), SIM105×7, B009×6, S110×4 (the verified fail-closed XSD loads), A001/E741/N806×6, B017/B905/F402/N802×4.
- **The tests/-tree residual — now 158 findings** (was 379, the 221 mechanical closed): E501×74, F811×27 (the `payment_fixture` redefinitions — fixture side-effect care), F841×9, S106×8, SIM117×8, C408×7, B007×6, E741×4, F821×2 (the conftest string-annotation nits — verified inert), S108×2, …
- **The `/accounts/search/` limit-contract migration** — unchanged (verified again: capped + typed; no frontend consumer).
- **The capped-default flip** — unchanged.
- **The audit-log INSERT policy** (DDL — `WITH CHECK (TRUE)` for the SECURITY DEFINER trigger; tightening needs the every-emission-path analysis) — unchanged.
- **BE-L3 config-class locking; BE-L4 Peppol log-state locking; CSV errors[] raw strings; dead-letter design; UEN checksum; NULL-context SELECT tradeoff; H-05b models; PaymentsTab prefill; TanStack incompatibility; the membership-cache window; the P20-era FE-M2/M3 designs; CI hardening (the mypy gate — 1491 errors); the version-story reconciliation** — the P21–P30 deferred registers carry forward unchanged.

## 5. Acceptance criteria

- The chaining pins (executed): the three RED specs GREEN — `__cause__` set on the Class-A seams, `__suppress_context__` True on the Class-B seam.
- `ruff check --select B904 apps/ common/ config/` → **0**; `ruff check --select W291,W293,I001,F401 tests/` → **0**; the whole-tree production count **277 → 211**; the tests count **379 → 158**.
- The backend suite green (**1033P/0F/5S** expected — +3 the new gates); no frontend change; the web gates green at the standing ratchets.
- `make lint-mechanical` exit 0 on the UNIFIED command (production + tests + B904); the ci.yml step updated; the YAML valid.
- The live contract re-verification: the not-found/validation response bodies byte-identical.
- `skills/` untouched by code checks; `git status` shows only the intended files.
- Plan + report saved under `docs/` in the `REMEDIATION_*_P31*` convention; the session log `docs/session_60.md`; the worklog updated.

## 6. Open decisions (resolved with judgment)

- **`from exc` as the default, not `from None`:** the conservative choice that never loses information; it matches the codebase's dominant exemplar set (`return_service`, `transmission_service`, `payment_service:322`, `query_params`, `auth_service`). `from None` is reserved for the 4 sites whose raised message already embeds the original error's string — pure duplication, matching the `journal/views.py:362` deliberate-noise exemplar.
- **The value-embed parses chain `from exc`:** `allocation.py:104,145`, `bank_transaction.py:112`, `gst/views.py:410` embed the offending VALUE but not the original error's string; `payment_service.py:322` (the existing exemplar for exactly this shape) chains `from exc` — consistency wins over the one divergent `journal/views.py:362` site (a pre-existing defensible choice, left untouched).
- **The Celery `self.retry` sites chain `from exc`:** `raise self.retry(exc=exc, countdown=…) from exc` — the retry already carries the exc for the backend; the chain makes the raise-site contract explicit and satisfies B904 with zero behaviour change.
- **The tests-tree F811s stay out:** the 27 redefinitions (`payment_fixture` ×24) need fixture side-effect analysis (a redefine may be deliberate test-layer scoping); the register's own rationale holds — the mechanical classes only.
- **E501 stays out (both trees):** the `make format` axis with its own review burden (80 production files; 74 tests lines) — registered with honest counts.
- **No new e2e spec:** the chaining is invisible to the browser (the response bytes are the contract, pinned by the existing suites + the live re-verification); the `__cause__` truth needs the unit-level capture specs.
- **The unified gate keeps the `lint-mechanical` name:** continuity beats renaming; the help text documents the expanded class set (the P30 four + B904) and tree (production + tests).
