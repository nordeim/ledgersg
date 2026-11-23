# LedgerSG — Remediation Report (P12 Sprint: Mobile-Nav Truth & A11y Floor)

**Date:** 2026-11-23 (session 25)
**Base commit:** `ba4357d4` (main — post-P11 + the user's `docs/session_24.md` log)
**Plan:** `docs/REMEDIATION_PLAN_2026-11-23_P12.md`
**Source audit:** the post-P11 audit executed LIVE this session (not just in
source): baselines reproduced first (backend 735P/0F/5S, vitest 511/511,
typecheck 0, coverage ratchet green, build:server green, e2e 11P + 23 gated),
then the sprint's focus — the mobile navigation menu and a possible
TailwindCSS v4 bug — investigated with agent-browser at 375×812 / 800×1024 /
1280×800 against the running dev stack, with computed-style matched-rule
traces on the nav DOM and the repo skills' taxonomies
(`skills/nextjs16-tailwind4` §9/§10, `skills/tailwind-patterns`,
`skills/astro-7-patterns` §7, `skills/tdd`).
**Method:** TDD (RED → GREEN → full gate). Every production-code change has
a regression test that failed for the documented reason first.

---

## 1. Verification Ledger (executed evidence)

| Gate | Result |
|---|---|
| Backend `pytest --reuse-db --no-migrations -q` | **735 passed, 0 failed, 5 skipped** (unchanged — backend untouched this sprint) |
| Frontend `npx tsc --noEmit` | 0 errors |
| Frontend `npx vitest run` | **518/518 passed** (511 + 7 new mobile-nav a11y tests) |
| `npm run test:coverage` | green at the honest measured-floor ratchet |
| `npm run build:server` | green — the only build mode |
| `npx eslint src` (whole tree) | **79 → 45 findings** (every mechanical class cleared; no new findings; register re-documented) |
| `npm run test:e2e` (no backend) | 11 passed + 26 gated with reasons |
| `npm run test:e2e:full` (live stack) | **36 passed, 1 data-conditional skip, 0 failed** (37 specs — the 3 new mobile-nav specs included) |
| Live mobile-nav a11y re-verification | Escape closes (`aria-expanded:false`), body scroll locks (`overflow:hidden`) and unlocks on close, focus returns to the toggle (`focusOnToggle:true`), focus moves into the sidebar on open — all read live in the real browser |
| Live console | the Next.js `scroll-behavior` route-transition warning **gone** after `data-scroll-behavior="smooth"`; no errors |
| API guide live gate | login contract (tokens.access, len 407); 9/9 documented list endpoints HTTP 200 with `{results,count}`; journal mount truth both directions (404 vs 200); `/auth/organisations/` bare-array shape documented |
| Screenshots | 6 new (`docs/screenshots/66-71_*_session25.png`) — pixel-verified (correct dims, non-blank, content-rich) and md5-unique |

## 2. The Sprint Verdicts

### The mobile navigation menu — WORKS (verified live, not assumed)

Toggle renders and is keyboard-operable at 375 (36×36, Enter opens); hidden
at ≥768 (`display:none`); the sidebar opens (`translate:0px`) and closes
(`translate:-100%`, `left:-256`); the overlay renders `fixed z-40` and a
click closes; nav links navigate AND auto-close (live: `/ledger/` +
`aria-expanded:false`); the tablet band (800) shows the sticky sidebar with
the toggle hidden; no horizontal overflow at 375; no console errors.

### The suspected TailwindCSS v4 bug — does not exist in this code

The audit's prime suspect (computed `display:flex` on a toggle wearing
`md:hidden` + `inline-flex`) was settled by a **matched-rule trace** through
`document.styleSheets`: the only display rules matching the element are
`.inline-flex { display:inline-flex }` and the media-gated
`.md\:hidden { display:none }` (`min-width: 48rem`). `display:flex` is the
**correct CSS blockification of an inline-level flex item** (the toggle
lives in the flex header) — standard CSS, identical in v3. The v4 setup
itself is clean: `@import "tailwindcss"` + `@theme` in `globals.css`,
`@tailwindcss/postcss`, and **no legacy `tailwind.config.*`** (the #1 v4
failure class in the skill playbook — absent). The `-translate-x-full` /
`md:translate-x-0` / `transition-transform` (→ `transform, translate, scale,
rotate 0.3s`) behaviors all trace correctly to v4's cascade-layer model.

## 3. What Was Fixed

| # | Finding | Fix | Evidence |
|---|---|---|---|
| A-1 (Medium) | The open mobile menu violated all four §9.4 mandatory overlay a11y behaviors — Escape did nothing (live-verified: dispatched Escape with the menu open → `aria-expanded` stayed `true`), no focus trap, no body scroll lock, no focus return; the baseline claims WCAG 2.2 AA | The overlay floor in `shell.tsx`: a document keydown listener while open (Escape closes; Tab wraps within the sidebar's focusables), a `useEffect` locking `body.style.overflow` with cleanup, focus moved into the sidebar on open, a prev-state ref returning focus to the toggle on close | 7 vitest (`shell-mobile-nav.test.tsx` — RED: 6 failed for exactly the documented gaps, 1 overlay-guard pass) + the live re-verification row above |
| A-2 (Medium) | Zero authenticated mobile-nav coverage — `navigation.spec.ts` covers anonymous routes only | `e2e/mobile-nav.spec.ts`: 3 gated specs (toggle+Escape at 375; nav-link navigates AND auto-closes; desktop band toggle-hidden/sidebar-sticky) | All 3 green in `test:e2e:full`; clean gated skip with reason otherwise |
| A-3 (Medium) | The lint register drifted: documented "47 no-explicit-any" vs the real whole-tree **79** (36 any + 30 unused-vars + 13 react-hooks-v7 classes) — parity-on-touched-files hid accumulated debt | Truth pass: 30 unused-vars, 1 prefer-const, 1 no-unescaped-entities, the `CustomTooltip`-in-render anti-pattern (`static-components`), the dead shell `mounted` gate, `catch (error)` unused binding, the type-only `actionTypes` const, middleware's unused param — all cleared | eslint whole tree 79 → 45; vitest 518/518; tsc 0; coverage + build green; the truthful register documented in the plan/report |
| A-4 (Low) | `<html>` lacked `data-scroll-behavior="smooth"` — Next.js 16 warned on every route transition | The attribute on the root `<html>` | Live console: the warning is gone |
| A-5 (Low) | Dead `mounted` state in `shell.tsx` (set, never read; also a `set-state-in-effect` finding) | Removed with its effect | The finding count drop + suite green |
| A-6 (Low) | `CustomTooltip` defined inside `GSTF5Chart`'s render (`react-hooks/static-components` — remounts on every render) | Hoisted to module scope (unchanged props) | eslint class cleared; dashboard vitest green |
| A-7 (Info) | recharts 3.7 transient `width(-1)/height(-1)` mount warnings | Registered, not "fixed" — the chart was verified CORRECT at every viewport (SVG 422×200 at 1280; 293×200 at 375) and across table↔chart toggles; the warning is the library's ResizeObserver boot noise | Live probes at 375/800/1280 |
| A-8 (Low) | `API_CLI_Usage_Guide.md` stale: March-era metrics, no P11 truths, a misleading session-persistence limitation | v2.5.0: the 2026-11-23 live re-verification block (9/9 envelopes, journal mount, login contract, credit-note reversal truth, dashboard endpoint, bare-array org route), current metrics, the session-persistence section rewritten to the Playwright storageState truth | Every claim in the block executed live this session (logged) |
| A-9 (Info) | DEPLOYMENT.md counts + `.env.example` drift check | DEPLOYMENT patched to the P12 counts (518 vitest; 37 specs; 36/37 live-green); env examples re-checked — no new reads this sprint, no drift | grep vs the env-read audit |

### Spec lessons (recorded, cost an hour, worth a lesson)

The first live run failed 1 spec: `getByRole('link', { name: 'Ledger' })`
resolved to TWO elements — the Ledger nav link AND the logo ("L LEDGERSG"
**contains the substring "LEDGER"**) — a strict-mode violation that read
exactly like an app bug. Fixed by scoping to the navigation landmark +
`exact: true`; recorded in AGENTS.md patterns + the SKILL lessons.

## 4. Deferred Debt Register (explicit — nothing silently dropped)

- The 36 `no-explicit-any` findings (unchanged policy; parity maintained).
- The mounted-gate `set-state-in-effect` findings in `dashboard/layout.tsx`
  and `gst-chart-wrapper.tsx` — functional SSR guards; the canonical
  `useSyncExternalStore` replacement is behavior-sensitive, registered.
- The 3 `exhaustive-deps` findings (invoice-form, tax-breakdown-card,
  auth-provider) — semantics need case-by-case analysis.
- `ledger-table.tsx` `incompatible-library` (React-Compiler informational)
  and the 2 `immutability` findings in a test file.
- A-7: the recharts mount-noise class (chart verified correct).
- Everything carried forward unchanged from P11's register (base-currency
  reporting, audit READ surface, CSRF Origin-check, backend ruff debt, F5
  period-cut semantics, pay_return, full PINT Schematron, ledger pagination,
  invoice update_line, B6 envelope, aged netting, quote lifecycle enum, TB
  zero-activity, reports export, TAX-group coarse type, Storecove,
  dashboard trends, CoA page, Reg-11 remainder, password reset, contacts
  merge, email verification, blank-UEN modeling, e2e bootstrap script,
  coverage headroom).

## 5. How to Verify (reproduction commands)

```bash
# backend gate (unchanged)
cd apps/backend && pytest --reuse-db --no-migrations -q      # 735P/0F/5S

# frontend gates
cd apps/web && npm run typecheck && npm test                 # 0; 518/518
npm run test:coverage && npm run build:server                # green; green

# lint truth (the register)
npx eslint src   # 45 findings — 36 any + 3 set-state-in-effect + 3
                 # exhaustive-deps + 1 incompatible-library + 2 immutability

# e2e (no backend) + live gate
npm run test:e2e               # 11P + 26 gated with reasons
# with the dev stack up (DEPLOYMENT.md §9):
npm run test:e2e:full          # 36P/1S/0F (37 specs)

# the mobile-nav a11y floor (unit level)
npx vitest run src/components/layout/__tests__/shell-mobile-nav.test.tsx

# live a11y behaviors (agent-browser at 375, after login):
#   open → aria-expanded:true + body overflow:hidden + focus on the first
#   nav link → press Escape → aria-expanded:false + overflow:"" + focus on
#   the toggle
```

## 6. Commits

Conventional commits on `main`: the a11y fix + specs + plan
(`46fee23b`), the lint-debt truth pass (`01e0f4ac`), the spec-locator fix
(lives with the e2e commit), the screenshots commit, the docs/API-guide
commit, and the worklog/session/report commit — pushed via
`docs/ssh_git_wrapper_v3.py` with remote-ref verification. See
`git log ba4357d4..HEAD` for the full set.
