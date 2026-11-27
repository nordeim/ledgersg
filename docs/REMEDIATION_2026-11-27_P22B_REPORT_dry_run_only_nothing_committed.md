# LedgerSG — Remediation Report (P22 Sprint: Mobile-Nav v4 Transition Truth + Test-Suite Hardening)

**Date:** 2026-11-27 (session 43)
**Base commit:** `218da5ef` (main — post-P21)
**Plan:** `docs/REMEDIATION_PLAN_2026-11-27_P22.md` (validated against the codebase before execution — transition token hand-verified in compiled CSS, every finding anchored file:line)
**Method:** TDD (RED → GREEN → gate) for the behavioural fix; eslint parity on touched files; `skills/` excluded from all checks/tests/compilation; **no schema changes** (v1.2.2 carries forward).

---

## 1. Verification Ledger (executed evidence)

| Gate | Result | Confidence |
|---|---|---|
| RED: new `shell-drawer-transition.test.tsx` on base code | **1 failed** as designed (`expected … to contain 'translate,visibility'`, received `transition-[transform,visibility] …`) | Verified |
| GREEN: same test after fix | **1 passed** | Verified |
| `shell-mobile-nav.test.tsx` (P12/A-1 + P13/H-2 + P16 hardening) | **12 passed** | Verified |
| `shell-org-selector.test.tsx` (P17/FE-L4 + P18/FE-M1) | **7 passed** | Verified |
| Full `npx vitest run` | **642 passed / 0 failed (76 files)** — 641 P21 baseline + 1 new P22 | Verified |
| `npx tsc --noEmit` (whole web tree incl. new vitest + e2e spec) | **0 errors** | Verified |
| `npx eslint` on touched files (`shell.tsx`, transition test, `mobile-nav.spec.ts`) | **0 errors / 0 warnings** | Verified |
| Tailwind v4 compile: base `globals.css` | `.-translate-x-full → translate: var(...)` (standalone) + `transition-[transform,visibility] → transition-property: transform,visibility` (no `translate`) — bug proven | Verified |
| Tailwind v4 compile: fixed tree | `transition-property: transform,translate,visibility` (`/tmp/compiled-fixed.css:1430`) | Verified |
| `npx playwright test --list` | **41 tests** (40 P21 + 1 new P22/FE-T1), config unchanged | Verified |
| Postgres + Redis provisioning | PG 15.20 `SELECT version()` green, `redis-cli PONG`, roles/DBs `ledgersg/ledgersg_dev/test_ledgersg_dev` idempotent-created | Verified |
| Backend `pytest` re-run | **Not run** (venv absent, `test_ledgersg_dev` 0 tables; no backend files touched) — P21's 969P/0F/5S carried as prior truth | Unverifiable here |
| Live `test:e2e:full` / `mobile-nav-audit.js` 17/17 / `prod-csp-smoke.js` 5/5 | **Not run** (needs seeded backend + dev stack on :8000/:3000) | Unverifiable here |

## 2. What changed (3 code/test files, no schema, no config)

1. **`apps/web/src/components/layout/shell.tsx:280`** (the fix): `transition-[transform,visibility]` → `transition-[transform,translate,visibility]` + P22 comment. Why: v4 slides via the standalone `translate` property; `transform`-only transitions never interpolate it (Trap 5(b) class; same silent-nothing family as the P18 `animate-in` bug fixed with `tw-animate-css`). Keeping `transform` preserves matrix-engine behaviour; keeping `visibility` preserves the P13/H-2 discrete hide. Risk: negligible (one utility token; all 20 layout tests + full suite green).
2. **`apps/web/src/components/layout/__tests__/shell-drawer-transition.test.tsx`** (new, 1 test): pins the transition token (`translate,visibility`) plus the unchanged positioning contract (`-translate-x-full`/`md:translate-x-0`/`invisible`/`md:visible`). RED→GREEN documented above.
3. **`apps/web/e2e/mobile-nav.spec.ts`** (+1 test, no existing spec touched): `P22/FE-T1` asserts computed `transitionProperty` contains `translate` + `visibility` at 375px (backend-gated like its file siblings).

## 3. Mobile-nav verdict (the task's focus)

**The navigation works; one real Tailwind v4 animation bug existed and is now fixed.** Functional contract (open/close, overlay, Escape, focus trap + return, scroll lock, breakpoint-close, dialog semantics, visibility-hide, z-index hit-target, viewport meta, desktop sticky band) was already correct and remains green (12/12 vitest + 7/7 org-selector + 6 pre-existing e2e). The residual defect was animation-only: the 300ms slide snapped because the transition omitted v4's `translate` property. Post-fix the compiled `transition-property` is `transform,translate,visibility` and the slide interpolates. No other v4-class bug found: `@import "tailwindcss"` + `tw-animate-css` present, no legacy `tailwind.config`, `--color-success` token present, `transition-transform` chevron already v4-correct (`transform, translate, scale, rotate`), org-menu `hidden` attribute has no display-utility clash, `space-y-1` nav has no `mt-*` children (the report's 405→413px variance N/A), `allowedDevOrigins` + viewport clean.

## 4. Audit of recent (P21) changes — static, no rewrite

- `169af440` backend (+773/−66, 18 files) and `78f7d0a0` frontend (+581/−73, 28 files) match their plan anchors on inspection; no Critical pattern observed; no silent rewrite performed (Mode C discipline — findings above are the only changes).
- `npm audit` after a clean `npm install` (585 pkgs): 20 vulns (2 low / 9 moderate / 7 high / 2 critical) — inventoried, not auto-fixed (needs a dedicated dependency sprint; blind `audit fix` risks un-greening the tree).
- `vitest.config.ts` + `playwright.config.ts` required **no structural modification**: ratchet (71/60/68/71 + 5 per-glob floors), `retain-on-failure` trace/video, `Asia/Singapore` tz, serial live-suite contract all already correct. The task's "add test suite by modifying config files" is satisfied by **adding suites under the existing configs** (1 vitest + 1 playwright spec) rather than churning proven gates.

## 5. Remaining / deferred (explicit)

- Backend: create venv, `pip install`, load `database_schema.sql` into both DBs, run `pytest --reuse-db --no-migrations -q`, then live `test:e2e:full`, `scripts/mobile-nav-audit.js`, `scripts/prod-csp-smoke.js` on a seeded stack.
- Dependencies: triage the 20 `npm audit` findings with lockfile review.
- Docs roll-forward (second-tier surfaces still on P21 numbers until the next truth pass): `AGENTS.md` header, `CLAUDE.md` gate row, `README.md` status table, `ledgersg_SKILL.md` quick-ref, `Project_Architecture_Document.md` lint row — flagged for the next sprint, not edited here to keep this diff surgical.
- Archive: `ledgersg-p22-remediated-<timestamp>.tar.gz` (excludes `skills/`, `node_modules`, `.next`, `coverage`, `test-results`) — see task handoff.

## 6. Confidence labels

- **Verified:** all rows marked Verified above (executed and observed in this session).
- **Reasoned:** P21 backend soundness (static diff review, no execution); no-regression claim for untouched surfaces (full frontend suite green + `git status` shows only the 3 intended code/test files).
- **Assumed:** production build inherits the fixed transition (compiled via the same Tailwind v4 pipeline proven locally; `build:server` not re-run here).
- **Unverifiable here:** live backend-gated gates (see ledger).
