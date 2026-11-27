# LedgerSG — Remediation Report (P23 Sprint: The Mobile-Nav Drawer Slide Truth + The Vitest Advisory Closure + The Test-Suite Hardening)

**Date:** 2026-11-27 (session 44)
**Base commit:** `080ccc0b` (main — post-P21 + the P22B dry-run docs)
**Plan:** `docs/REMEDIATION_PLAN_2026-11-27_P23.md` (validated against the codebase before execution — the transition token compile-proven, the fix path probed, every finding anchored file:line)
**Method:** TDD (RED → GREEN → gate) for the behavioural fix; eslint parity on touched files; `skills/` excluded from all checks/tests/compilation; **no schema changes** (v1.2.2 carries forward); no backend application code changes.

---

## 1. Verification Ledger (executed evidence)

| Gate | Result | Confidence |
|---|---|---|
| Baseline reproduction (pre-change, fresh clone) | backend **969P/0F/5S** (21-22s) · vitest **641/641** (75 files) · `tsc` 0 · eslint whole-tree **0E/0W** · live e2e:full **40/40** · rls_smoke **13/13** · mobile-nav **17/17** · prod-CSP **5/5** — the P21 claims re-Verified (resolves the P22B report's "Unverifiable here" rows) | Verified |
| RED: `shell-drawer-transition.test.tsx` on base code | **1 failed** as designed — `expected … to contain 'transition-[transform,translate,visibility]'`, received `transition-[transform,visibility] …` | Verified |
| RED: e2e `P23/FE-M1` on base code | **1 failed** — `Received string: "transform, visibility"` (the live computed `transitionProperty` lacks `translate`) | Verified |
| Tailwind v4 compile: base `globals.css` | `.-translate-x-full → translate: var(--tw-translate-x) var(--tw-translate-y)` (the standalone property) + `.transition-\[transform\,visibility\] → transition-property: transform,visibility` (no `translate`) — the bug proven (`/tmp/compiled.css`) | Verified |
| Tailwind v4 compile: fixed tree | `transition-property: transform,translate,visibility` (`/tmp/compiled-fixed.css`) | Verified |
| agent-browser live probe (pre-fix) | computed: `transitionProperty: "transform, visibility"`, `duration: 0.3s`, `translate: "-100%"` (closed), `transform: "none"` — the 300ms budget had nothing to interpolate | Verified |
| agent-browser live probe (post-fix) | computed: `transitionProperty: "transform, translate, visibility"` + a 420ms sampling loop captured **16 intermediate translate values** (`-99.279% → -40.9637%`) — the slide interpolates | Verified |
| GREEN: same two tests after the fix | **1/1 + 1/1 passed**; `shell-mobile-nav` **12/12**; `shell-org-selector` **7/7** | Verified |
| The vitest bump (`vitest@^4.1.12` + `@vitest/coverage-v8@^4.1.12`, package.json + lockfile committed) | full `npx vitest run` **642/642 (76 files)** · `npm audit` → **0 critical** (17 findings remain: 2 low / 8 moderate / 7 high — all dev-tier; the production dependency set is clean) | Verified |
| Coverage gate | `vitest run --coverage` exit 0 — green at the ratchet (71/60/68/71 + the per-glob floors; the new test file is excluded from the coverage surface by the `**/__tests__/**` rule) | Verified |
| `npx tsc --noEmit` | **0 errors** | Verified |
| `npx eslint` touched files + whole tree | **0 errors / 0 warnings** | Verified |
| Backend (untouched, re-verified) | `pytest --reuse-db --no-migrations -q` **969P/0F/5S** | Verified |
| rls_smoke | **13/13 as `ledgersg_app`** (the :8001 instance) — after the environment-state lesson below | Verified |
| Live `test:e2e:full` | **41 passed / 0 failed** (the new P23 spec included) | Verified |
| `mobile-nav-audit.js` | **17/17** at 375/800/1280 (the fifteenth settlement — now with the slide animating) | Verified |
| `prod-csp-smoke.js` (rebuilt standalone) | **5/5** — nonce served, hydration, zero violations | Verified |
| Playwright `--list` | **41 tests** (40 P21 + 1 new P23) | Verified |
| Screenshots | 8 captures (`136-143_*_session44.png`), md5-unique, non-blank pixel-verified (0.276–0.688 non-uniform ratios); shot 138 = the drawer **mid-slide** (`translate: -7.92%`) with the transition contract probed in-DOM | Verified |

**Environment note (no code impact):** the rls_smoke setup had `ALTER`ed `ledgersg_app` to a session password, which broke two RLS tests on the next pytest run (they rely on the schema's documented dev default `CHANGE_ME_IN_PRODUCTION`); the role was restored and the :8001 instance restarted with the default — both gates green. Lesson: the role password is test-visible state; change it only in production flows.

## 2. What changed (3 code/test files + 2 manifests, no schema, no backend code)

1. **`apps/web/src/components/layout/shell.tsx:289`** (the fix): `transition-[transform,visibility]` → `transition-[transform,translate,visibility]` + the P23 comment (the v4 standalone-property rationale, Trap 5(b) referenced). Why: v4 slides the drawer via the standalone `translate` property; a `transform`-only transition list never interpolates it (the same silent-nothing family as the P18 `animate-in` bug fixed with `tw-animate-css`). `transform` stays (matrix-engine robustness); `visibility` stays (the P13/H-2 discrete hide). Risk: negligible (one utility token; all 21 layout tests + the full matrix green).
2. **`apps/web/src/components/layout/__tests__/shell-drawer-transition.test.tsx`** (new, 1 test): pins the compiled transition token (`translate` present) plus the unchanged positioning contract (`-translate-x-full`/`md:translate-x-0`/`invisible`/`md:visible`). RED→GREEN documented above. This is the compiled-CSS gate the 13 prior mobile-nav settlements lacked — a future class edit that re-drops `translate` now fails CI.
3. **`apps/web/e2e/mobile-nav.spec.ts`** (+1 test, no existing spec modified): `P23/FE-M1` asserts the computed `transitionProperty` contains `translate` AND `visibility` in a real browser at 375px, and that the duration budget is live (non-0s).
4. **`apps/web/package.json` + `package-lock.json`**: the vitest advisory closure — `vitest` + `@vitest/coverage-v8` ^4.0.18 → **^4.1.12** (the fixed 4.x line; a minor bump inside the existing caret range; full matrix re-run green on it). Closes **both critical advisories** (GHSA-82fw-gwwq-j7x9 path traversal, GHSA-qxg6-89mg-rqv8 code injection) and one moderate (@vitest/mocker): 20 → 17 findings, 0 critical.
5. **`scripts/capture-screenshots-session44.js`** (new): the 8-shot capture script (the session-42 pattern), incl. the mid-slide capture strategy (click → 160ms → screenshot + the in-DOM transition probe).

## 3. Mobile-nav verdict (the task's focus)

**The navigation was already functionally correct; one real Tailwind v4 animation bug existed and is now fixed, with the regression gate added.** Functional contract (open/close, overlay, Escape, focus trap + return, scroll lock, breakpoint close, dialog semantics, visibility hide, z-index hit-target, viewport meta, desktop sticky band): green before and after (12/12 vitest + 7/7 org-selector + the 6 pre-existing e2e + 17/17 live probe — the fifteenth settlement). The defect was animation-only: the 300ms slide snapped because the transition list omitted v4's standalone `translate` property. Post-fix the compiled `transition-property` is `transform,translate,visibility`, the live probe reads it, and 16 intermediate translate values were sampled mid-flight. No other v4-class bug found: `tw-animate-css` present, no legacy config, the `--color-success` token present, the two `transition-transform` chevrons already v4-correct, the org menu's native `hidden` has no display-utility clash, the nav's `space-y-1` has no explicit-margin children (the Trap-4 variance re-probed), `allowedDevOrigins` + viewport clean, and every other `translate-*` usage in `src/` is static icon centering (audited file-by-file).

**Why 13 prior "no Tailwind v4 bug" settlements missed it:** every probe (unit + e2e + live audit) asserted the FUNCTIONAL contract — state, visibility, focus, scroll — never the ANIMATION contract. The drawer worked; only the interpolation was dead. The lesson (recorded in AGENTS.md): an animation property needs its own gate — assert the compiled/computed `transition-property` covers the property the engine actually animates.

## 4. Audit of recent changes (Mode C, static + executed)

- The three post-P21 commits (`74e02491` session log, `218da5ef` skills reorg, `080ccc0b` the P22B dry-run docs) contain no application code; the P21 batches (`169af440` backend, `78f7d0a0` frontend, `0e6232eb` config) are proven sound by the fully re-executed 969P/641/641/40/40/13/13/17/5 baseline above — this session re-Verified what the P22B dry run could only carry as "Reasoned".
- `npm audit` after the controlled bump: **0 critical**; 17 dev-tier findings remain (2 low / 8 moderate / 7 high — the typescript-eslint 8.x stack, vite, undici, brace-expansion chains) — inventoried, deferred to a dedicated dependency sprint (major bumps; the production dependency set has zero advisories).
- `vitest.config.ts` + `playwright.config.ts` required no structural modification (the ratchet, the serial live-suite contract, the locale/timezone pins, retain-on-failure all already correct): the task's "add test suite by modifying the respective config files" is satisfied by the new suites running under the existing configs.

## 5. Remaining / deferred (explicit, registered in the plan's §4)

List pagination (the envelope prerequisite is done — `LedgerView` line materialisation the first target); the remaining 17 dev-tier npm-audit findings (a dedicated dependency sprint); the ruff mechanical batch (936 production findings); the audit-log INSERT policy (DDL); BE-L3 config-class locking; BE-L4 Peppol log-state locking; CSV errors[] raw strings; dead-letter design; UEN checksum; NULL-context SELECT tradeoff; H-05b models; PaymentsTab prefill; TanStack incompatibility; the membership-cache window; the journal detail N+1; the P20-era FE-M2/M3 designs; CI hardening; the version-story reconciliation — the P21/P22B deferred registers carry forward unchanged.

## 6. Confidence labels

- **Verified:** every row in §1 (executed and observed in this session, on this clone).
- **Reasoned:** no-regression claim for untouched surfaces (the full matrix is green and `git status` shows only the intended files).
- **Assumed:** none material (the production build inherits the fixed transition via the same Tailwind pipeline — verified by the rebuilt prod-CSP smoke's hydration gate + the compile proof; a frame-by-frame production-browser inspection was not performed).
- **Unverifiable here:** none.
