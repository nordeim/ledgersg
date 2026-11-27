# LedgerSG — Remediation Plan (P23 Sprint: The Mobile-Nav Drawer Slide Truth + The Vitest Advisory Closure + The Test-Suite Hardening)

**Date:** 2026-11-27 (session 44)
**Base commit:** `080ccc0b` (main — post-P21 + the P22B dry-run docs; all gates green at 969P/0F/5S backend · 641/641 vitest · tsc 0 · eslint 0E/0W · live e2e 40P · rls_smoke 13/13 · mobile-nav 17/17 · prod-CSP 5/5 · schema v1.2.2)
**Method for execution:** TDD (RED → GREEN → full gate) for every behavioural fix; lint parity on touched files (eslint frontend); conventional commits on `main`; `skills/` excluded from all checks/tests/compilation; **no schema changes** (v1.2.2 carries forward); no backend application code changes (the backend suite was re-executed fresh this session and is green — see §1).
**Skills consulted:** `skills/skills-catalog.md` (343 skills) → `nextjs16-tailwind4` §9 (mobile-nav patterns) + §10 (the v4 debugging playbook), `tailwind-patterns` §4 (mobile-first + the breakpoint system), `tdd` (the red→green loop; vertical slices, seams at the public interface), `agent-browser` (the live DOM probe — **available this session**, unlike the P22B dry run), `code-review`/`debugging-and-error-recovery` (the Mode C discipline), `rootless-postgresql` §2–§5 (the PG install).

---

## 1. Audit inputs (this session's evidence)

- **Repo + docs truth pass:** `git clone https://github.com/nordeim/ledgersg.git` clean on `main` @ `080ccc0b`; full reads of `AGENTS.md`, `CLAUDE.md` v2.23.0, `README.md`, `Project_Architecture_Document.md`, `ledgersg_SKILL.md` v2.9.0, `worklog.md`, `docs/session_42.md`, `docs/session_43.md`, the P21 plan + report, the **P22B dry-run plan + report** (`docs/REMEDIATION_PLAN_2026-11-27_P22B_not_applied.md` — the P22 fixes were designed, verified, then deliberately NOT committed), and `docs/Tailwind-V4-Validation-Report.md` (Trap 5(b): v4 renders `translate/scale/rotate` via the standalone CSS properties; the Trap-4 space-y `:where()` specificity note; the `--shadow-sm` pin precedent).
- **Postgres + Redis (the task's named setup):** `docs/setup_pg_z.sh` + `skills/rootless-postgresql/SKILL.md` followed first — the skill's §2 probes ALL passed on this Debian 13 trixie sandbox (non-root uid 1001, `/home/z/my-project` writable, apt-cache populated with `postgresql-17`), so the rootless path worked natively (no sudo fallback needed this time): rootless **PG 17** on :5432, role `ledgersg` (SUPERUSER) + `ledgersg_app` (runtime role, schema-created), databases `ledgersg_dev` + `test_ledgersg_dev` created and loaded with schema **v1.2.2** (36 base tables across the 7 schemas + seeded tax codes 16 / roles 5 / account types 8; RLS active on 24 tenant tables); **Redis 8.0.2** on :6379 (rootless: `apt-get download` + `dpkg-deb -x` prefix, the same pattern the PG skill documents, adapted for the redis `.deb` + its `liblzf1` dependency).
- **The full 8-gate baseline reproduced on this fresh clone (all executed, green — the P21 claims re-Verified here, resolving the P22B report's "Unverifiable here" rows):** backend `pytest --reuse-db --no-migrations -q` **969P/0F/5S** (22.05s; venv `pip install -e ".[dev]"` clean) · vitest **641/641 (75 files)** · `npx tsc --noEmit` **0 errors** · whole-tree `npx eslint .` **0 errors / 0 warnings** · live `test:e2e:full` **40/40** (fresh-DB bootstrap via `scripts/bootstrap_demo_substrate_session40.sh`, the documented first-run flake class re-run clean) · `rls_smoke.py` **13/13 as `ledgersg_app`** on the :8001 instance · `mobile-nav-audit.js` **17/17** (375/800/1280 — the fourteenth consecutive live settlement) · `prod-csp-smoke.js` **5/5** (`build:server` green). Playwright chromium installed fresh (the sandbox cache was empty — the DEPLOYMENT §9 `npx playwright install chromium` step).
- **The named focus — the mobile-nav deep dive (Mode C, the P22B findings re-verified LIVE this session):** the functional contract is GREEN (12/12 vitest `shell-mobile-nav` + 7/7 `shell-org-selector` + 6 e2e + the 17/17 probe). The **one real Tailwind v4 bug is animation-only and is still unfixed** (the P22B dry run never applied its fix — `git grep` confirms `transition-[transform,visibility]` at `shell.tsx:280`):
  - **Compile proof** (this session, `npx @tailwindcss/cli -i src/app/globals.css -o /tmp/compiled.css`): `.-translate-x-full { --tw-translate-x: -100%; translate: var(--tw-translate-x) var(--tw-translate-y) }` — the drawer slides via the **standalone `translate` property** (v4), while `.transition-\[transform\,visibility\] { transition-property: transform,visibility }` — **`translate` is NOT in the transition list**, so the `duration-300 ease-in-out` has nothing to interpolate: the drawer SNAPS open/closed instead of sliding.
  - **Live proof** (agent-browser CDP probe of the running dev stack, pre-fix): the aside's computed style = `transitionProperty: "transform, visibility"`, `transitionDuration: "0.3s"`, `translate: "-100%"` (closed) / `"0px"` (open — the functional flip works), `transform: "none"` (so the `transform` entry animates nothing on this element), `visibility: "hidden"`/`"visible"` (the P13/H-2 discrete flip, correct). The 300ms budget is dead config.
  - **The v4 hygiene sweep re-verified clean:** `@import "tailwindcss"` + `tw-animate-css` present (P18); no legacy `tailwind.config`; `--color-success` token present (P17); the two `transition-transform` chevrons (org selector `shell.tsx:367`, payment-list `:163`) already v4-correct (compile: `transform, translate, scale, rotate`); the org menu uses the native `hidden` attribute (no display-utility clash); the nav's `space-y-1` has no explicit-margin children (the Trap-4 405→413px variance N/A — re-probed by `mobile-nav-audit.js` check 17); `viewport` meta Class E clean; `allowedDevOrigins` Trap (c) clean; every other `translate-*` usage in `src/` is static icon centering (no transition intended — audited file-by-file).
- **Test-infra review:** `vitest.config.ts` (the 71/60/68/71 whole-suite ratchet + 5 per-glob floors + the documented `src/stores/**` exclusion) and `playwright.config.ts` (chromium default, serial live-suite contract P16/FE-M4, `retain-on-failure` trace+video P20/P21, `Asia/Singapore`/`en-SG` pins, `expect.timeout 10s`) both structurally correct — the P22B conclusion re-affirmed: the task's "add vitest and playwright test suite by modifying the respective config files" is satisfied by **adding suites under the existing configs** (1 vitest spec + 1 playwright spec) rather than churning proven gates.
- **npm audit (fresh `npm install`, 585 pkgs): 20 findings — 2 low / 9 moderate / 7 high / 2 critical.** The 2 criticals are `vitest` + `@vitest/coverage-v8` (GHSA-82fw-gwwq-j7x9 path traversal + GHSA-qxg6-89mg-rqv8 code injection) — dev-tier only; the production dependency set (next/react/tailwind/zod…) has zero advisories. A controlled bump viability was **proven this session**: `--no-save` install of vitest 4.1.12 + coverage-v8 4.1.12 (the fixed 4.x line — a minor bump inside the `^4.0.18` range) → full suite **641/641 green**. The remaining 18 (brace-expansion, typescript-eslint ×7, vite, undici, browserslist, js-yaml, picomatch, flatted, minimatch, @babel/core, esbuild, @humanfs/node — all dev-tier) need major bumps; `npm audit fix` is a proven no-op for them and a blind fix could un-green the tree.
- **Docs truth audit (re-measured):** the top status blocks were P21-truthful; the **second-tier surfaces still sit on P21 numbers** (README badge `1650`/status-table rows, AGENTS header gate row, CLAUDE.md status/gate rows, `ledgersg_SKILL.md` quick-ref, PAD lint row, DEPLOYMENT.md header counts + §7/§11, the API guide version/metrics rows) — the P22B report's registered roll-forward, which lands this sprint with the P23 numbers. Both `.env.example`s re-verified truthful **variable-by-variable against the code this session** (`config("…")` sweep: 17 backend vars incl. `CORS_ALLOWED_ORIGINS`; web `NEXT_PUBLIC_API_URL` + `NEXT_OUTPUT_MODE`) — no changes required.

**Combined findings (this session's audit): 0 Critical / 0 High (functional) / 2 Medium / 4 Low / 3 Informational** — every execution-scoped finding hand-verified in source/live (anchors below).

## 2. Findings (verified, with evidence anchors)

### Medium

**FE-P23-M1 — THE headline (the task's named focus): the mobile drawer's 300ms slide never interpolates — `transition-[transform,visibility]` omits v4's standalone `translate` property (the P22B dry-run finding, re-verified live, still unfixed).**
`apps/web/src/components/layout/shell.tsx:280` — the aside slides via `-translate-x-full ↔ translate-x-0` (compiled to the standalone `translate` property in v4) but transitions only `transform,visibility`. Open/close still WORKS (state, visibility, focus, scroll-lock, overlay, Escape all correct — 12/12 vitest + 17/17 live probe) but the drawer appears/disappears instantly: the 300ms slide is dead config. Same bug class as the Tailwind-V4-Validation-Report's Trap 5(b) (`computed-style must read the right property per stack`) and the P18 `animate-in` family (utilities silently compiling to nothing). Fix: `transition-[transform,translate,visibility]` — keep `transform` (matrix-engine robustness), add `translate` (the v4 property), keep `visibility` (the P13/H-2 discrete hide). Evidence: `/tmp/compiled.css` (this session), the agent-browser computed-style probe above, and the P22B plan §2 M1.

**CFG-P23-M2 — vitest 4.0.18 ships 2 CRITICAL advisories (dev-tier).**
`apps/web/package.json` devDependencies pin `vitest@^4.0.18` + `@vitest/coverage-v8@^4.0.18`; the lockfile resolves 4.0.18. GHSA-82fw-gwwq-j7x9 (@vitest/mocker path traversal / arbitrary file read) + GHSA-qxg6-89mg-rqv8 (code injection via unauthenticated manual mock registration) — both fixable at **4.1.12, a minor bump inside the existing caret range**. Viability proven in-session (641/641 green on 4.1.12 before reverting to baseline). Fix: `npm install -D vitest@^4.1.12 @vitest/coverage-v8@^4.1.12` (updates package.json + package-lock.json — a committed, deliberate change, never a blind `audit fix`), then the FULL gate matrix (vitest + coverage + tsc + eslint + e2e + build) re-run green.

### Low

**FE-P23-L1 — no compiled-CSS gate pins the transition contract (regression risk).** The 12 mobile-nav vitests assert state/visibility/focus and the 6 e2e assert computed `visibility`/`position`/hit-target — none assert `transition-property`. A future class edit could re-drop `translate` with every suite green (exactly how this bug survived 13 "no Tailwind v4 bug" settlements: the probes checked the functional contract, not the animation contract). Fix: the new vitest spec (below) pins the class token; the new e2e spec pins the computed `transitionProperty` in a real browser.

**CFG-P23-L2 — the remaining 18 npm-audit findings (7 high) un-triaged.** All dev-tier chains (typescript-eslint 8.x stack, vite 6/7, brace-expansion, undici, …) needing major bumps — registered for a dedicated dependency sprint with lockfile review (the P22B decision, re-affirmed; the production set is clean).

**DOC-P23-L3 — the second-tier doc surfaces sit on P21 numbers** (the P22B-registered roll-forward): README badge + status table, AGENTS header, CLAUDE.md status/gate rows, SKILL quick-ref, PAD lint row, DEPLOYMENT header/§7/§11 counts, API-guide version/metrics. Every count re-measured after the gates; each doc updated with the P23 numbers + the P23 milestone frame.

**INFO-P23-L4 — `test:all` runs `vitest run --coverage` (not the new spec in isolation) — the coverage gate must stay green after the new spec lands** (a new test file with 100% coverage of itself cannot lower the ratchet; verified by running the coverage gate).

### Informational

**I1 — the P22B dry-run artifacts stay as the historical record** (`docs/REMEDIATION_PLAN_2026-11-27_P22B_not_applied.md` + `docs/REMEDIATION_2026-11-27_P22B_REPORT_dry_run_only_nothing_committed.md`); P23 applies the same verified fix design with corrected attribution (P23 labels — the P22 labels never shipped code). No P22/P22A plan files exist to collide with; the applied-sprint numbering continues P23.
**I2 — the `transition-transform` org chevron (`shell.tsx:367`) and the payment-list chevron are already v4-correct** (`transform, translate, scale, rotate` — covers `rotate-180`). No change.
**I3 — the e2e suite grows 40→41** (the P23 transition spec, backend-gated like its file siblings); vitest 641→642 (75→76 files); backend unchanged at 969P (no backend code touched).

## 3. The execution plan (phases, TDD)

### Phase 1 — RED: the transition-contract tests (vitest + playwright)

| Task | Test (RED first) |
|---|---|
| T1 | New `apps/web/src/components/layout/__tests__/shell-drawer-transition.test.tsx` (1 test, mirroring the in-file mock conventions of `shell-mobile-nav.test.tsx`): the aside's class token contains `transition-[transform,translate,visibility]` (the exact compiled token) and keeps the positioning contract `-translate-x-full` / `md:translate-x-0` / `invisible` / `md:visible`. **Expected RED on base:** the token reads `transition-[transform,visibility]` — the assertion failure names the missing `translate`. |
| T2 | New e2e case in `apps/web/e2e/mobile-nav.spec.ts` (`P23/FE-T1`, no existing spec modified): at 375px the aside's computed `transitionProperty` contains both `translate` AND `visibility` (the animation contract + the P13/H-2 discrete hide), and `transitionDuration` is non-zero (the budget is live). Backend-gated like its file siblings. |
| T3 | Compile proof after GREEN: `npx @tailwindcss/cli` → `.transition-\[transform\,translate\,visibility\] { transition-property: transform,translate,visibility }` (the `/tmp/compiled-fixed.css` convention). |

### Phase 2 — GREEN: the fix + the vitest advisory closure

| Task | Fix | Verification |
|---|---|---|
| T4 | `shell.tsx:280`: `transition-[transform,visibility]` → `transition-[transform,translate,visibility]` + the P23 comment (the v4 standalone-property rationale + the Trap 5(b) reference). | T1 GREEN · `shell-mobile-nav` 12/12 · `shell-org-selector` 7/7 · `tsc` 0 · `eslint` 0 on touched files |
| T5 | The vitest advisory closure: `npm install -D vitest@^4.1.12 @vitest/coverage-v8@^4.1.12` (package.json + package-lock committed). | Full `npx vitest run` 642/642 (76 files) · `npm audit` → criticals 0 (the 18 dev-tier remainder reported) · coverage gate green at the ratchet |
| T6 | The agent-browser live re-probe on the remediated stack: computed `transitionProperty` reads `transform, translate, visibility` (the pre-fix probe's mirror — the P22B deferred item, closed this session). | the CDP probe output recorded in the report |

### Phase 3 — the full gate matrix + the deliverables

The complete gate set on the remediated tree: backend `pytest` 969P/0F/5S (unchanged — no backend code touched; re-run for the record) · vitest 642/642 · coverage green at the ratchet · `tsc` 0 · whole-tree `eslint` 0E/0W · live `test:e2e:full` **41/41** · `rls_smoke` 13/13 · `mobile-nav-audit.js` 17/17 (the fifteenth settlement — now with the slide animating) · `prod-csp-smoke` 5/5 (the production build inherits the fixed transition via the same Tailwind pipeline — verified by the smoke's hydration gate + the compile proof).

Deliverables: 8 DOM-verified screenshots (`docs/screenshots/136-143_*_session44.png`, md5-unique + non-blank pixel-verified, mirroring the session-42 capture script conventions: the drawer closed/open at 375, the desktop band, the banking loader live region, the org selector, the ledger + invoices + settings surfaces on the remediated stack); the P23 report (`docs/REMEDIATION_2026-11-27_P23_REPORT.md`); the session log (`docs/session_44.md`); the worklog entry; the docs truth pass (§2 DOC-L3); the `.env.example` re-verification note; the conventional commits + the SSH-wrapper push to main.

### Phase 4 — the docs truth pass

| Doc | Update |
|---|---|
| README.md | badge (642+41+969 = the new arithmetic), the status-table gate rows, the P23 milestone section (the drawer-slide truth + the vitest advisory closure) |
| CLAUDE.md | version 2.23.0 → 2.24.0 header, the status block, the P23 milestone block |
| AGENTS.md | the header gate row, the P23 lessons (the "animation contract needs its own gate" pattern) |
| ledgersg_SKILL.md | quick-ref numbers, version 2.9.0 → 2.10.0 |
| Project_Architecture_Document.md | the lint/test count rows |
| docs/DEPLOYMENT.md | the header re-verification line (session 44 / P23), §7 counts (969P), §9/§11 counts (vitest 642, e2e 41), the `npm audit` note (criticals closed at the dev tier, 18 registered) |
| API_CLI_Usage_Guide.md | the version row 3.2.0 → 3.2.1 + a P23 addendum (no API-surface change — the sprint is presentation/test-tier; the route table re-verified against the live urls) |
| .github/workflows/ci.yml | the header comment counts |
| `.env.example` ×3 | re-verified truthful (no changes) — the verification noted in the report |

## 4. Deferred register (updated, carried forward)

**Fixed this sprint (removed from the P22B dry-run's deferred list):** the drawer transition fix (FE-M1); the transition-contract gates (L1); the vitest critical advisories (M2); the agent-browser live probe (the P22B deferral — agent-browser available this session); the P22B report's "Unverifiable here" backend rows (the full 8-gate baseline re-executed fresh: 969P · rls 13/13 · e2e 40/40 · mobile-nav 17/17 · CSP 5/5); the second-tier docs roll-forward (L3).

**Still deferred (with rationale, unchanged from the P21/P22B registers):**
- **List pagination** — the per-view limit/offset design + the frontend UX (`LedgerView` line materialisation the first target; the envelope prerequisite is done).
- **The remaining 18 npm-audit findings (7 high)** — dev-tier chains needing major bumps (typescript-eslint 8.x stack, vite, undici…); a dedicated dependency sprint with lockfile review.
- **The ruff mechanical batch** — re-measured 936 production findings (W293 ×376, I001 ×123, F401 ×121…); a dedicated pass, lint-parity-on-touched-files only this sprint.
- **The audit-log INSERT policy** (DDL); **BE-L3 config-class locking**; **BE-L4 Peppol log-state locking**; **CSV errors[] raw strings**; **dead-letter design; UEN checksum; NULL-context SELECT tradeoff; H-05b models; PaymentsTab prefill; TanStack incompatibility; the membership-cache window; the journal detail N+1; the P20-era FE-M2/M3 designs; CI hardening; the version-story reconciliation** — the P21 deferred register carries forward unchanged.

## 5. Acceptance criteria

- The aside's compiled `transition-property` reads `transform,translate,visibility` (evidence: the compile proof + the live CDP re-probe).
- `shell-drawer-transition` 1/1 + `shell-mobile-nav` 12/12 + `shell-org-selector` 7/7 green; full vitest **642/642 (76 files)** on vitest **4.1.12**; coverage green at the ratchet; `tsc` 0; whole-tree `eslint` 0E/0W.
- `playwright --list` shows **41 tests** incl. `P23/FE-T1`; live `test:e2e:full` 41/41.
- `npm audit`: **0 critical** (2 low + 9 moderate + 7 high dev-tier remainder, reported in the report — the production set clean).
- Backend untouched-but-re-verified: `pytest` 969P/0F/5S; `rls_smoke` 13/13; `mobile-nav-audit.js` 17/17; `prod-csp-smoke` 5/5.
- No schema change; `skills/` untouched by code checks; `git status` shows only the intended files (the 3 code/test files + package.json + package-lock.json + the docs + the screenshots).
- Plan + report saved under `docs/` in the `REMEDIATION_*_P23*` convention; the session log `docs/session_44.md`; the worklog updated.

## 6. Open decisions (resolved with judgment)

- **Apply the P22B-designed fix under the P23 label (not P22):** the P22B sprint was an explicit dry run — nothing shipped, so its "P22" labels have no shipped code to attribute. P23 is the next applied sprint number; the P22B docs stay as the not-applied historical record (I1).
- **The vitest bump (4.0.18 → 4.1.12) — apply, not defer:** the P22B session deferred ALL npm-audit work (its environment couldn't even run the backend). This session has the full gate matrix runnable, the bump is inside the existing caret range (a minor, semver-compatible fix release), and the viability is already proven (641/641 green on 4.1.12 in the probe). Closing 2 criticals with a re-verified green tree beats carrying them. The other 18 findings still defer (major bumps — the P22B decision holds).
- **Fix shape `transform,translate,visibility` (not `translate,visibility` alone):** keeps matrix-engine behaviour (`transform`) and the P13/H-2 discrete hide (`visibility`) while adding the v4 standalone `translate` — the same "pin the token, keep every class" precedent as the report's `--shadow-sm` Trap-5 fix.
- **No backend changes:** the backend suite was re-executed fresh and green; the audit found no backend defect in scope; the sprint stays surgical (frontend + test-tier only).
- **agent-browser used for the live probe (the P22B deferral closed):** available at `/usr/local/bin/agent-browser` this session; the pre-fix probe captured the defect's live computed-style, the post-fix probe closes the loop. Playwright remains the e2e engine (the repo's proven gate).
