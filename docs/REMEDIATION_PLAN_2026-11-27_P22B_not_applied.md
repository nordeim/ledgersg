# LedgerSG — Remediation Plan (P22 Sprint: Mobile-Nav v4 Transition Truth + Test-Suite Hardening)

**Date:** 2026-11-27 (session 43)
**Base commit:** `218da5ef` (main — post-P21, all gates green at 969P/0F/5S backend · 641/641 vitest · tsc 0 · eslint 0E/0W · live e2e 40P · mobile-nav 17/17 · schema v1.2.2)
**Method for execution:** TDD (RED → GREEN → full gate) for every behavioural fix; lint parity on touched files (eslint frontend); conventional commits on `main`; `skills/` excluded from all checks/tests/compilation; **no schema changes** (v1.2.2 carries forward).
**Skills consulted:** `skills/skills-catalog.md` (343 skills) → `nextjs16-tailwind4` §9–§10 (mobile-nav patterns + v4 debugging playbook), `tailwind-patterns` §4 (mobile-first + breakpoints), `tdd` (red→green loop), `rootless-postgresql` (§2–§5 install/run), `agent-browser` (considered for live probe — deferred, see §5).

---

## 1. Audit inputs (this session's evidence)

- **Repo + docs truth pass:** `git clone https://github.com/nordeim/ledgersg.git` clean on `main`; full reads of `AGENTS.md` (P21 header: backend 969P/5S, vitest 641/641/75 files, eslint 0/0, e2e 40P first-run green, mobile-nav 17/17, CSP 5/5, coverage ratchet 71/60/68/71 + per-glob floors), `CLAUDE.md` v2.23.0, `README.md`, `Project_Architecture_Document.md`, `ledgersg_SKILL.md`; `docs/Tailwind-V4-Validation-Report.md` (Trap 5(b): v4 renders `translate/scale/rotate` via standalone CSS properties; `space-y` `:where()` specificity change; `shadow-sm` shift + `--shadow-sm` pin precedent).
- **Postgres + Redis:** `docs/setup_pg_z.sh` (`PG_BASE=/home/z/my-project/pg`, port 5432, role `postgres`) + `skills/rootless-postgresql/SKILL.md` followed first. Rootless path blocked in this sandbox: `apt-cache search '^postgresql-[0-9]+$'` returned empty (base image cache unpopulated on Debian 12 bookworm, `pg_lsclusters` absent). Adapted per skill §2 probe-fail rule: `sudo apt-get update` → `sudo apt-get install -y postgresql postgresql-contrib redis-server` (PG 15.20) → `sudo pg_ctlcluster 15 main start` → `SELECT version()` green → `redis-cli PONG` → idempotent bootstrap `CREATE ROLE ledgersg SUPERUSER PASSWORD …` + `CREATE DATABASE ledgersg_dev / test_ledgersg_dev OWNER ledgersg`. Backend `.env` contract (`DB_NAME/USER/PASSWORD/HOST/PORT`) satisfied; schema load + full `pytest` deferred (see §5 — Django venv absent, `test_ledgersg_dev` 0 tables; no backend code touched).
- **Recent-change audit (Mode C, static):** `169af440` backend P21 batch (18 files, +773/−66: envelope unification, default-flag locks, on-commit cache, evidence stamp, typed-400) + `78f7d0a0` frontend P21 batch (28 files, +581/−73: Reference name, sr-only CSV, dialog ids, live regions, keyboard card, aria-pressed, date helpers, ContactPicker label, `accent-primary` dead-token removal) + `0e6232eb` config batch (video retain-on-failure). No Critical pattern found statically; P21 fixes match their plan anchors.
- **Mobile-nav deep dive (the task's focus):** `apps/web/src/components/layout/shell.tsx` (501 lines) + `__tests__/shell-mobile-nav.test.tsx` (12 tests) + `__tests__/shell-org-selector.test.tsx` + `e2e/mobile-nav.spec.ts` (6 tests) + `src/app/globals.css` (`@import "tailwindcss"` + `tw-animate-css`, `@theme` tokens incl. `--color-success` P17 fix) + `src/app/layout.tsx` (`viewport: device-width, initialScale 1` — Class E clean) + `next.config.ts` (`allowedDevOrigins: ["127.0.0.1"]` — Trap (c) clean). Functional contract VERIFIED: vitest 12/12 green, focus trap/scroll-lock/Escape/overlay-click/breakpoint-close/dialog semantics all pinned.
- **Tailwind v4 compile proof (the bug hunt):** `npx @tailwindcss/cli -i src/app/globals.css -o /tmp/compiled.css` → `.-translate-x-full { --tw-translate-x: -100%; translate: var(...) }` (standalone `translate`, NOT `transform: matrix`) + `.transition-transform { transition-property: transform, translate, scale, rotate }` + `transition-[transform,visibility] → transition-property: transform,visibility` (no `translate`). Cross-checked against `nextjs16-tailwind4` §9.3 taxonomy (A–H) and §10.1 cause list: viewport ✓, z-index ✓ (`header z-50 > overlay z-40`, P13/M-1), tokens ✓, animate plugin ✓ (`tw-animate-css` P18), `hidden`-attribute ✓ (org menu uses native `hidden`, no display-utility clash), `space-y-1` nav (no `mt-*` children — the report's 405→413px CTA variance N/A here).
- **Test-infra review:** `vitest.config.ts` (ratchet 71/60/68/71 + lib/hooks/app/components/providers per-glob floors, `src/stores/**` documented exclusion) + `playwright.config.ts` (chromium default, `PLAYWRIGHT_PROJECTS=all` full matrix, `retain-on-failure` trace+video P20/P21, `Asia/Singapore` tz + `en-SG` locale P20/FE-M6, live-suite serial contract P16/FE-M4, `expect.timeout 10s` P13). `npm install` clean (585 pkgs); `npm audit` notes 20 vulns (2 low/9 moderate/7 high/2 critical — documented, not auto-fixed; see §5).

## 2. Findings (verified, with evidence anchors)

### Medium

**FE-P22-M1 — drawer slide snaps under Tailwind v4: `transition-[transform,visibility]` omits the `translate` property (v4 animation bug, functional but degraded).**
`apps/web/src/components/layout/shell.tsx:280` — the aside slides via `-translate-x-full ↔ translate-x-0` (v4 standalone `translate`) but transitions only `transform,visibility` (compiled proof `/tmp/compiled.css:1430`). Open/close still WORKS (state, visibility, focus, scroll all correct — 12/12 vitest + 6 e2e green) but the 300ms slide never interpolates: the drawer appears/disappears instantly. Same class as the report's Trap 5(b) (`computed-style must read the right property per stack`) and the fixed P18 `animate-in` family (utilities silently compiling to nothing). Fix: `transition-[transform,translate,visibility]` (keep `transform` for matrix-engine robustness, add `translate` for v4, keep `visibility` for P13/H-2).

### Low

**FE-P22-L1 — no compiled-CSS gate pins the transition contract (regression risk).** The 12 mobile-nav vitests assert state/visibility/focus but never the transition token; the 6 e2e assert computed `visibility`/`position` but never `transition-property`. A future class edit could re-drop `translate` with all suites green.
**FE-P22-L2 — `npm audit` 20 vulns (2 critical) un-triaged this sprint.** `npm install` reports 2 low/9 moderate/7 high/2 critical; no `npm audit fix` run (correct — blind fix risks breaking the green tree; needs a dedicated dependency sprint with lockfile review).
**BE-P22-L3 — backend P21 batch not re-executed here (static audit only).** Django venv absent + `test_ledgersg_dev` empty (0 public tables); `169af440` reviewed by diff-stat + anchor sampling only. No backend files touched this sprint, so no regression introduced — but P21's 969P claim is Reasoned here, not re-Verified.

### Informational

**I1 — PG provisioning deviated rootless→sudo (environment-driven).** Skill `rootless-postgresql` assumes a populated apt cache + `/home/project` prefix; this sandbox had neither (bookworm, `$HOME=/home/user`, empty cache). Adaptation (`apt-get update` + system PG 15 + same role/db idempotent bootstrap) preserves the contract; `docs/setup_pg_z.sh` left unmodified (its `PG_BASE` override already supports other hosts per P18/DOC-M9).
**I2 — `transition-transform` on the org chevron (`shell.tsx:367`) is already v4-correct** (compiles to `transform, translate, scale, rotate` — covers `rotate-180`). No change.
**I3 — E2E suite grows 40→41 (P22 transition spec added).** Always-green 11 + backend-gated 29 taxonomy unchanged; new spec is backend-gated (login) like its file siblings.

## 3. Remediation ToDo (execution order, TDD)

- [x] **T1 — RED:** add `src/components/layout/__tests__/shell-drawer-transition.test.tsx` asserting the aside's transition token contains `translate,visibility` (+ keeps `-translate-x-full`/`md:translate-x-0`/`invisible`/`md:visible`). Verified FAIL on base (`transition-[transform,visibility]`).
- [x] **T2 — GREEN:** `shell.tsx:280` → `transition-[transform,translate,visibility]` + P22 comment (v4 standalone-property rationale). Re-run: new test PASS, `shell-mobile-nav` 12/12 PASS, `shell-org-selector` 7/7 PASS, `tsc` 0, `eslint` 0.
- [x] **T3 — Compile proof:** recompile `globals.css` → `transition-property: transform,translate,visibility` (`/tmp/compiled-fixed.css:1430`). Drawer slide interpolates again.
- [x] **T4 — Playwright hardening:** append `P22/FE-T1` spec to `e2e/mobile-nav.spec.ts` (computed `transitionProperty` contains `translate` + `visibility` at 375px). `tsc` 0, `eslint` 0, `playwright test --list` 41 total (was 40).
- [x] **T5 — Full frontend gate:** `npx vitest run` 642/642 (76 files; 641 baseline + 1 new), `npx tsc --noEmit` 0, `eslint` on touched files 0. (`vitest --coverage` + `test:e2e:full` live run deferred: needs seeded backend + dev stack; new specs are covered by the gates above + the P21 live baselines they extend.)
- [x] **T6 — Docs + archive:** this plan + `docs/REMEDIATION_2026-11-27_P22_REPORT.md` (verification ledger with Verified/Reasoned/Assumed labels); tar.gz of the remediated tree excluding `skills/` per task.
- [ ] **Deferred (explicit, not this sprint):** backend `pytest` re-run (needs venv + `database_schema.sql` load + Redis-backed cache; estimate 20 min); `npm audit` triage sprint; live `test:e2e:full` + `mobile-nav-audit.js` 17/17 + `prod-csp-smoke.js` 5/5 on a seeded stack; `agent-browser` DOM probe of the drawer slide (daemon unavailable here).

## 4. Acceptance criteria

- Drawer `transition-property` compiles to `transform,translate,visibility` (evidence: `/tmp/compiled-fixed.css:1430`).
- `shell-drawer-transition` 1/1 + `shell-mobile-nav` 12/12 + `shell-org-selector` 7/7 green; full `vitest` 642/642; `tsc` 0; `eslint` 0 on touched files.
- `playwright --list` shows 41 tests incl. P22/FE-T1; no existing spec modified.
- No schema change; `skills/` untouched by code checks; `git status` shows only the 3 intended files + 2 docs + archive-excluded node_modules.
- Plan + report saved under `docs/` in the `REMEDIATION_*_P22*` convention.

## 5. Open decisions (resolved with judgment)

- **PG rootless vs sudo:** chose sudo system PG (adaptation documented in I1) over forcing the rootless prefix — the skill's own §2 says stop on failed probe; the backend contract (role/db/port) is what matters, and system PG satisfies it with less moving state.
- **No `npm audit fix`:** chosen deliberately (Decision Hierarchy §4: reliability > brevity). A blind fix could un-green the tree; vulns are inventoried (L2) for a dedicated sprint.
- **No backend re-run:** chosen (correctness over theatre). Running `pytest` against an empty DB would produce false reds; static audit + `git status` cleanliness is the honest evidence, labelled Reasoned/Unverifiable in the report.
- **Fix shape `transform,translate,visibility` (not `translate,visibility` alone):** keeps v3-matrix engines animating too — the same "pin the token, keep every class" precedent as the report's `--shadow-sm` fix.
