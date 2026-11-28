# LedgerSG — Remediation Plan (P28 Sprint: The SQL-Level Push-Down for the Service-Driven Lists + The Honest Ratchet + The Dev-Tier Dependency Closure)

**Date:** 2026-11-28 (session 53)
**Base commit:** `ad8b3b47` (main — post-P27 + the session-53 narration log)
**Method for execution:** TDD (RED → GREEN → full gate) for every behavioural change; eslint parity on touched files; conventional commits on `main`; `skills/` excluded from all checks/tests/compilation; **no schema changes** (v1.2.2 carries forward); no frontend component changes (the one web-tree change is the coverage-ratchet config + the dependency bump — both verified by the full matrix).
**Skills consulted:** `skills/skills-catalog.md` → `tdd` (the red→green loop), `code-review`/`debugging-and-error-recovery` (Mode B/C discipline), `rootless-postgresql` (the PG environment — live from the prior sessions, re-probed this session), `agent-browser` (the live mobile-nav + translate probes — executed this session, §1), `nextjs16-tailwind4`/`tailwind-patterns` (consulted for the mobile-nav focus — the surface re-settled clean, §1).

---

## 1. Audit inputs (this session's evidence)

- **Repo + docs truth pass:** `git pull` to `ad8b3b47` clean on `main`; full reads of `AGENTS.md`, `CLAUDE.md` v2.28.0, `README.md`, `Project_Architecture_Document.md` v3.17.0, `ledgersg_SKILL.md` v2.14.0, `worklog.md`, `docs/session_52.md`, `docs/session_53.md`, the P27 plan + report, and `docs/Tailwind-V4-Validation-Report.md`.
- **The environment (live, re-probed):** rootless **PG 17** on :5432 (`ledgersg_dev` loaded — 36 tables via Django introspection across the per-app schemas core/invoicing/banking/coa/journal/audit/gst; `test_ledgersg_dev` present), **Redis** on :6379, the backend venv, `node_modules`, the dev stack (:8000 dev — health 200, :8001 RLS, :3000 `next dev`). **No environment repair was required this session** — `ledgersg_app` authenticates at the documented default (`CHANGE_ME_IN_PRODUCTION`, schema §15).
- **The baseline reproduction (pre-change, this session — all gates exact):** backend `pytest --reuse-db --no-migrations -q` **1021P/0F/5S** (30.15s) · vitest **698/698 (85 files)** (108.22s) · `npx tsc --noEmit` **0 errors** · whole-tree `npx eslint . --max-warnings 5` from `apps/web` **0E/0W** · live `test:e2e:full` **43/43 (2.2m, deterministic)** · `rls_smoke.py` **13/13 as `ledgersg_app`** · `mobile-nav-audit.js` **17/17** (the twenty-fourth settlement) · the dedicated Tailwind v4 `translate` probe (this session's script, `scripts/translate-probe-session53.js`): closed `-100%`/hidden → **7 mid-flight samples** (`-96.72% → -69.29% → -30.48% → -16.29% → -5.17% → -1.66%`) → open `0px`/`role="dialog"` → Escape closes; computed `transitionProperty: "transform, translate, visibility"` · `npm audit` **0 critical** on the production set (`--omit=dev` → 0; 17 dev-tier: 2 low / 8 moderate / 7 high — all verified dev-only: `undici` via `jsdom`, `vite` via `vitest`/`@vitejs/plugin-react`, the rest via the toolchain).
- **The named focus — the mobile-nav verdict (twenty-fourth settlement):** **WORKING as expected; NO remaining Tailwind v4 bug on this surface.** The dedicated live probe (375px, this session) plus the 17/17 audit — the drawer slides through 7 interpolated `translate` values, the transition list carries the standalone `translate` property, the closed/open/Escape contract holds.
- **The audit (Mode C) of the P27 slice** (`df9e70ad..19a1c2d0`, hand-verified in source this session): the timer-callback value-change compare (`lastDebounced` read/written only inside the timer — an event, never render), the render-time org resets on all five surfaces, the filters-prop identity resets with the stable `NO_FILTERS` default — **0 new findings in the P27 slice**. The same-class sweep (every `setOffset(0)` + every debounce timer in the web tree) found no remaining surface: the ledger has no search; the contact-picker's debounce sets only the query value (no offset).

**Combined findings (this session's audit): 0 Critical / 1 High / 2 Medium / 1 Low.**

## 2. Findings (verified, with evidence anchors)

### High

**BE-P28-H1 — every page of the four service-driven lists fetches the FULL matching table (the registered push-down deferral, now sized precisely).**
`apps/invoicing/services/contact_service.py` (`list_contacts` → `return list(queryset...)`), `apps/invoicing/services/document_service.py:142-145` (`list_documents` → `return list(queryset.select_related("contact").order_by(...))`), `apps/banking/services/payment_service.py:269` (`list` → `return list(queryset.order_by(...))`), `apps/banking/services/reconciliation_service.py:76` (`list_transactions` → `return list(queryset...)`) — all four materialize the entire filtered set into Python. The views (`apps/invoicing/views.py:103-107, 227-231`; `apps/banking/views.py:241-244, 490-496`) then **Python-slice** the list and count via `len()`. Consequence: an organisation with 10,000 documents pays a 10,000-row fetch + 10,000 model instantiations + the select_related joins **on every one of its 20-row pages** — the pagination contract (P24) pages the RESPONSE but not the QUERY. The two P24/P26-era SQL-level surfaces prove the intended pattern: `apps/journal/views.py:473` (`total = queryset.count()`) and `apps/peppol/views.py:69` — both count in SQL and slice the queryset (SQL `LIMIT/OFFSET`). The register has carried this as "the SQL-level push-down for the five service-driven lists" (documents covers the invoices AND quotes UI surfaces — four views, five surfaces).

**Consumer sweep (verified this session):** the four list methods' only production consumers are the four list views; the remaining `DocumentService`/`ContactService` call sites use other methods (`approve_document`, `void_document`, `generate_pdf`); the direct service tests use `len()` + `[0]` indexing — both behave identically on a lazy queryset. **RLS note (verified):** every evaluation point (the serializer iteration, `.count()`, the slice) runs inside the request, under the tenant context — no deferred evaluation can escape it.

**Fix:** the four services return the **queryset** (lazy; the `select_related`/`order_by` chains carry); the four views take `count = qs.count()` (SQL `COUNT(*)`) and slice the queryset (`qs[offset : offset + limit]` — Django renders SQL `LIMIT/OFFSET`). The unpaginated path (`limit is None`) serializes the queryset directly — the response stays byte-identical. The envelope contract ({results, count, next, previous}, the ordering tiebreakers, the filters-in-URLs) is untouched — pinned by the existing `tests/integration/test_pagination_p24.py` suite and now by the new query-level gates (§3 T1).

### Medium

**CFG-P28-M2 — the coverage ratchet never followed the measured floor the P21–P27 reports claimed.** `apps/web/vitest.config.ts:59-65` still holds the P20 whole-suite floor (`lines 71 / functions 60 / branches 68 / statements 71` — set in commit `764f7ae4`), while the measured floor this session is **73.39 / 62.38 / 70.72 / 73.95** (statements/functions/branches/lines) — the P21–P27 reports each recorded "the floor RAISED to `<measured>`" but the config thresholds were never bumped, contradicting the config's own ratchet instruction ("bump these numbers as coverage improves, never lower them"). The gate passes only because it sits 2+ points below the truth. Fix: raise the whole-suite thresholds to the measured floor (73/62/70/73) and re-run `test:coverage` (the per-glob tier floors are left at their P20 values — all passing; raising them needs the per-glob measured numbers and is registered as follow-up).

**DEP-P28-M3 — the 17 dev-tier npm-audit findings (7 high), all verified dev-only.** `npm audit fix --dry-run` (this session) resolves all 17 with **in-range semver bumps only** — `@typescript-eslint/*` 8.56.1→8.74.0, `vite` 7.3.1→7.3.8, `undici` 7.22.0→7.30.2 (via jsdom), `minimatch`→11.0.9, `brace-expansion`, `js-yaml`, `flatted`, `picomatch`, `browserslist`, `semver`, `ignore`, the `@babel/*` toolchain — no production dependency moves (verified: `dependencies` in `apps/web/package.json` contains none of them; `npm audit --omit=dev` is already 0). This is the registered "dedicated dependency sprint", executable as the mechanical half of this sprint. The full web gate matrix (vitest 698, tsc, eslint, e2e 43) re-verifies the tree after the bump.

### Low

**DOC-P28-L1 — the docs truths roll forward with the sprint** (the standing DOC-L pattern): README badge/counts + the P28 milestone, CLAUDE 2.28.0 → 2.29.0, AGENTS header + the P28 lessons, SKILL 2.14.0 → 2.15.0, PAD 3.17.0 → 3.18.0, DEPLOYMENT header/§7/§9, the API guide (no API contract changes this sprint — the response bytes are pinned byte-identical by design; the version row stays 3.5.0 with the re-verification noted), ci.yml counts, `.env.example`s re-verified (no new env vars expected).

## 3. The execution plan (phases, TDD)

### Phase 1 — RED: the query-level regression specs

NEW `apps/backend/tests/integration/test_pagination_pushdown_p28.py` — one test class per surface (contacts, documents, payments, transactions), each reusing the `pagination_fx`/`auth_client` fixtures (the `test_pagination_p24.py` conventions) and `django.test.utils.CaptureQueriesContext`:

| Task | Test (RED first) |
|---|---|
| T1 | Per surface, GET `?limit=2` under the capture context, then assert: (a) **the row-fetch SELECT on the surface's table carries `LIMIT 2`** (the requested page size — RED now: the fetch is unbounded); (b) **a `COUNT(*)` query runs against the surface's table** (RED now: the count comes from `len()` on the cached list); (c) the envelope counter-pin — `count` is the TOTAL, `results` is the 2-row page (passes now; the fix must not change it). Table anchors: `invoicing"."contact`, `invoicing"."document`, `banking"."payment`, `banking"."bank_transaction` (the embedded-schema `db_table` values, verified this session). |

### Phase 2 — GREEN: the fixes

| Task | Fix | Verification |
|---|---|---|
| T2 | `contact_service.list_contacts` + `document_service.list_documents` return the queryset (drop the `list(...)` materialization; the return annotations updated; the docstrings note the lazy contract); `apps/invoicing/views.py` — `count = contacts.count()` / `documents.count()`, the slice applied to the queryset. | T1 contacts + documents GREEN · the P24 envelope suite green · the direct service tests green |
| T3 | `payment_service.list` + `reconciliation_service.list_transactions` return the queryset; `apps/banking/views.py` — `.count()` + the queryset slice. | T1 payments + transactions GREEN · the banking suites green |
| T4 | The full backend suite — every existing pin (the P24/P25/P26 envelope contracts, the service-level `len()`/indexing tests, the RLS gates) holds. | `pytest` 1021+N passed / 0 failed / 5 skipped |
| T5 | The coverage ratchet raise: `apps/web/vitest.config.ts` whole-suite thresholds 71/60/68/71 → **73/62/70/73** (lines/functions/branches/statements — the measured floor). | `npm run test:coverage` exit 0 at the raised floor |
| T6 | `npm audit fix` (the in-range dev-tier bumps, exactly the dry-run set); `package-lock.json` committed. | `npm audit` **0 findings** (dev+prod) · the full web matrix: vitest 698/698 · tsc 0 · eslint 0E/0W · live e2e 43/43 |

### Phase 3 — the full gate matrix + the screenshots

1. The complete gate set on the remediated tree: backend `pytest` **1021P+4/0F/5S** · vitest **698/698 (85 files)** · `test:coverage` green at the RAISED ratchet · `tsc` 0 · whole-tree `eslint` 0E/0W · live `test:e2e:full` **43/43** · `rls_smoke` **13/13** · `mobile-nav-audit.js` **17/17** (the twenty-fifth settlement) · the `translate` probe re-PASS · `npm audit` **0** (dev+prod) · `build:server` green + `prod-csp-smoke.js` 5/5.
2. Screenshots: 8 DOM-verified captures (`docs/screenshots/176-183_*_session53.png`, md5-unique + non-blank pixel-verified, the session-45/48/50/52 capture conventions) — the four paginated list surfaces (the push-down beneficiaries), the mobile drawer closed/open, the desktop band, the dashboard; the capture script `scripts/capture-screenshots-session53.js` (the session-52 pattern).
3. The `.env.example` truth verification (the config-readers sweep re-run; no new env vars expected — the finding noted in the report).

### Phase 4 — the docs truth pass

| Doc | Update |
|---|---|
| README.md | the badge/test arithmetic (backend 1025, e2e 43), the status-table rows, the P28 milestone section |
| CLAUDE.md | version 2.28.0 → 2.29.0, the status block, the P28 milestone block |
| AGENTS.md | the header gate row, the P28 lessons ("a paginated response is not a paginated query — pin the SQL, not just the envelope" + "a ratchet nobody bumps is a rubber stamp") |
| ledgersg_SKILL.md | the quick-ref numbers, version 2.14.0 → 2.15.0 |
| Project_Architecture_Document.md | the lint/test count rows, version 3.17.0 → 3.18.0 |
| docs/DEPLOYMENT.md | the header re-verification line (session 53 / P28), §7/§9/§11 counts; re-validate the fresh-host walkthrough against the current tree |
| API_CLI_Usage_Guide.md | re-verify the documented contracts against the live stack (the response bytes are pinned byte-identical — no version bump; the re-verification noted) |
| .github/workflows/ci.yml | the header comment counts |
| `.env.example` ×3 | re-verified truthful (no changes expected) |

## 4. Deferred register (updated, carried forward)

**Fixed this sprint (removed from the register):** the SQL-level push-down for the service-driven lists (BE-P28-H1); the 17 dev-tier npm-audit findings (DEP-P28-M3); the whole-suite coverage-ratchet drift (CFG-P28-M2).

**Still deferred (with rationale, unchanged unless noted):**
- **The per-glob coverage-tier raise** (NEW, follow-up of CFG-P28-M2): the whole-suite floor is raised this sprint; the lib/hooks/app/components/providers globs still sit at their P20 measured values (all passing) — raising them needs the per-glob measured numbers from the JSON report.
- **The `/accounts/search/` limit-contract migration** — unchanged (verified this session: the frontend never calls the endpoint — the invoice form uses the plain `/accounts/` list with `account_type`; a backend-only contract nicety).
- **The capped-default flip** — unchanged.
- **The ruff mechanical batch** (936 production findings); **the audit-log INSERT policy** (DDL); **BE-L3 config-class locking**; **BE-L4 Peppol log-state locking**; **CSV errors[] raw strings**; **dead-letter design; UEN checksum; NULL-context SELECT tradeoff; H-05b models; PaymentsTab prefill; TanStack incompatibility; the membership-cache window; the journal detail N+1; the P20-era FE-M2/M3 designs; CI hardening; the version-story reconciliation** — the P21/P23/P24/P25/P26/P27 deferred registers carry forward unchanged.

## 5. Acceptance criteria

- The query-level pins (all executed): a paginated request on each of the four surfaces issues a `LIMIT`-bounded SELECT and a SQL `COUNT(*)` — never an unbounded fetch; the envelope stays byte-identical (the P24 suite green, the e2e 43/43).
- The backend suite green (1021+4P/0F/5S); no frontend component change; the one web config change (the ratchet) verified by `test:coverage` at the raised floor; the dependency bump verified by the full web matrix.
- `npm audit` reports **0** across dev+prod.
- `skills/` untouched by code checks; `git status` shows only the intended files.
- Plan + report saved under `docs/` in the `REMEDIATION_*_P28*` convention; the session log `docs/session_54.md`; the worklog updated.

## 6. Open decisions (resolved with judgment)

- **The sprint scope — the push-down, not the accounts/search migration:** the push-down is the register's standing #1 and a production cost on every list page; the accounts/search endpoint has no frontend consumer (verified) — its contract migration stays deferred. The dependency closure joins because it is mechanical, verified dev-only, and de-risks the toolchain.
- **The services return querysets (not pagination params on the services):** the minimal-diff design — the views already own the pagination decision (`parse_limit_offset`), the services' filter logic is untouched, and the direct-call tests (`len()`, indexing) behave identically on a queryset. Pushing limit/offset into the services would duplicate the parse/validate contract the views already carry.
- **The RLS evaluation-scope risk is nil (verified):** every queryset evaluation point (serializer iteration, `.count()`, the slice) runs inside the request under the tenant context; there is no caching or deferred evaluation of these returns anywhere in the tree.
- **The ratchet raises only the whole-suite floor:** the per-glob tiers need their own measured numbers (the text report's directory rows do not aggregate the same way the globs match); raising them blind risks a red gate on rounding. Registered as follow-up rather than guessed.
- **`npm audit fix` (not `--force`):** the dry-run set is entirely in-range semver bumps; `--force` could cross majors and is not needed — all 17 resolve without it.
- **No new e2e spec:** the push-down is invisible to the browser (the response bytes are the contract, already pinned by the P24 suite and the e2e); the query-level truth needs the backend capture-context specs, not a UI walk.
