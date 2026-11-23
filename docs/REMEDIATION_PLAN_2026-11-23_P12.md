# LedgerSG — Remediation Plan (P12 Sprint: Mobile-Nav Truth & A11y Floor)

**Date:** 2026-11-23 (session 25)
**Base commit:** `ba4357d4` (main — post-P11, includes `docs/session_24.md`)
**Source audit:** post-P11 audit executed live this session. Method per the
repo convention: baselines reproduced first (backend 735P/0F/5S; vitest
511/511; typecheck 0; e2e 11P + 23 gated; coverage ratchet green;
`build:server` green), then the focused live audit of the **mobile
navigation menu** and **TailwindCSS v4** per the sprint instructions —
agent-browser at 375×812 / 800×1024 / 1280×800 against the running dev
stack, computed-style rule traces on the nav DOM, plus the repo skills
(`skills/nextjs16-tailwind4` §9 failure taxonomy + §9.4 mandatory overlay
a11y; `skills/tailwind-patterns`; `skills/astro-7-patterns` §7; `skills/tdd`).
**Method for execution:** TDD (RED → GREEN → full gate), lint parity on
touched files, conventional commits on `main`, `skills/` excluded from all
checks/tests/compilation.

---

## 1. Sprint audit verdict (what was verified live)

### The mobile navigation menu — WORKS as expected

| Check (375×812 unless noted) | Result | Evidence |
|---|---|---|
| Toggle button renders, visible, 36×36 | ✓ | computed rect + `aria-label="Open navigation"` |
| Toggle `display:none` at ≥768px | ✓ | computed at 1280: `display:none`, `offsetParent:null` |
| Sidebar closed: `translate:-100%`, `left:-256` | ✓ | computed style trace |
| Toggle click opens: `translate:0px`, `left:0`, `aria-expanded:true` | ✓ | live click |
| Overlay renders `fixed z-40`, overlay click closes | ✓ | computed + live click (`left:-256`, expanded:false) |
| Nav link click navigates AND auto-closes | ✓ | `/ledger/`, `left:-256`, `expanded:false` |
| Keyboard: Enter on focused toggle opens | ✓ | live |
| Tablet 800×1024: sidebar sticky at 256, toggle hidden | ✓ | computed |
| No horizontal overflow at 375 | ✓ | `scrollWidth == clientWidth` |
| Console errors | none | warnings only (see findings) |

### The TailwindCSS v4 suspect classes — NO v4 bug

- **CSS cascade traced rule-by-rule** on the nav DOM: the only display rules
  matching the toggle are `.inline-flex { display:inline-flex }` and the
  media-gated `.md\:hidden { display:none }` (`min-width: 48rem`). The
  earlier `display:flex` reading is **correct CSS blockification** — an
  inline-level child of a flex container (the header) computes its outer
  display to `flex`. Not a bug, not v4-specific.
- Setup is clean v4: `@import "tailwindcss"` + `@theme` in `globals.css`,
  `@tailwindcss/postcss` plugin, **no legacy `tailwind.config.*`** (the #1
  v4 failure class in the skill playbook — absent).
- Overlay/sidebar/toggle classes (`md:hidden`, `-translate-x-full`,
  `md:translate-x-0`, `transition-transform` → `transform, translate, scale,
  rotate 0.3s`) all behave exactly per the v4 cascade-layer model; the
  sidebar animates the native `translate` property and the transition covers
  it.
- The trailing-slash hrefs (`/ledger/`) are app-wide routing truth (pathname
  and rendered anchors agree), not a nav defect; one audit probe initially
  mis-selected `a[href='/ledger']` and mis-read it as a broken nav —
  re-verified with the real href contract.

### Baseline gates reproduced (post-P11 state intact)

backend 735P/0F/5S · invariants/security unchanged · vitest 511/511 ·
typecheck 0 · coverage ratchet green · `build:server` green · e2e 11P+23
gated · CI YAML parses (unchanged since P11) · PG (schema-qualified, 8
`trg_audit_*` triggers → `audit.log_change` verified) · Redis alive.

---

## 2. Findings register

| ID | Sev | Location | Finding (evidence) |
|---|---|---|---|
| A-1 | Medium | `apps/web/src/components/layout/shell.tsx` | The mobile nav overlay misses all four §9.4 mandatory overlay a11y behaviors: **no Escape-close** (live-verified: dispatched Escape with menu open → `aria-expanded` stays `true`), no focus trap, no body scroll-lock while open, no focus-return to the trigger. Baseline claim is WCAG 2.2 AA. |
| A-2 | Medium | `apps/web/e2e/` | Zero authenticated mobile-nav coverage: `navigation.spec.ts` tests anonymous routes + viewport smoke only; nothing exercises toggle→open→navigate→auto-close (the core mobile nav contract). |
| A-3 | Medium | `apps/web/src` (lint) | Lint-debt drift: the documented register says "47 `no-explicit-any` findings"; the truthful current state is **79 findings on src (45 errors / 34 warnings)** — 36 no-explicit-any + **30 no-unused-vars (21 in `banking/__tests__/page.test.tsx`, 14 in `banking-client-transactions.test.tsx`)** + 13 react/react-hooks-v7 findings. The debt grew silently across sprints (parity was only checked on touched files). |
| A-4 | Low | `apps/web/src/app/layout.tsx:56` | `<html>` lacks `data-scroll-behavior="smooth"` — Next.js 16 warns on every route transition (live-observed in console). |
| A-5 | Low | `apps/web/src/components/layout/shell.tsx:57-65` | Dead `mounted` state — set in an effect, never read (also one of the `set-state-in-effect` findings). |
| A-6 | Low | `apps/web/src/components/dashboard/gst-f5-chart.tsx:57` | `CustomTooltip` defined inside the component body (`react-hooks/static-components`) — recreated every render; the classic remount anti-pattern. |
| A-7 | Info | recharts 3.7 | Transient `width(-1) height(-1)` mount warnings before the ResizeObserver fires — chart verified correct at 375/800/1280 (SVG 293×200 / 422×200) and across table↔chart toggles. Console noise only; registered, not a rendering defect. |
| A-8 | Low | `API_CLI_Usage_Guide.md` | Stale vs the remediated codebase: metrics from 2026-03 (468 collected/393 passing; frontend 321), no credit-note reversal truth (P11/C-1), the "session not persisting" limitation is stale (Playwright storageState carries the HttpOnly cookie session — the P4/E-1 e2e specs prove it), endpoint contracts need re-verification. |
| A-9 | Info | `docs/DEPLOYMENT.md`, `.env.example` | Validate against the remediated tree (P11 revision exists; verify + P12 spot checks). |

**Explicitly re-registered (not this sprint, carried forward):** the 36
`no-explicit-any` findings (unchanged policy — parity maintained, no new
ones); the mounted-gate `set-state-in-effect` findings in
`dashboard/layout.tsx` and `gst-chart-wrapper.tsx` (functional SSR guards;
the `useSyncExternalStore` canonical replacement is a behavior-sensitive
change — registered, not risked this sprint); 3 `exhaustive-deps`
(`invoice-form`, `tax-breakdown-card`, `auth-provider` — semantics need
case-by-case analysis); `ledger-table.tsx` `incompatible-library`
(React-Compiler informational); 2 `immutability` in a test file.

---

## 3. Task list (TDD; every code change ships with its failing test first)

| # | Finding | Task | Tests (RED first) |
|---|---|---|---|
| 1 | A-1 | Mobile-nav overlay a11y floor in `shell.tsx`: Escape keydown closes the open menu; body scroll-lock (`overflow:hidden`) while open, restored on close; focus moves into the sidebar on open and returns to the toggle on close; simple Tab-cycle trap within the sidebar+header while open | `src/components/layout/__tests__/shell-mobile-nav.test.tsx` — Escape closes; overlay click closes; focus return; scroll lock lifecycle; toggle re-open after close |
| 2 | A-2 | `e2e/mobile-nav.spec.ts` — authenticated, backend-gated spec: 375px: toggle visible → open → navigate via Ledger link → sidebar closed + `/ledger/` + Escape-close behavior; 1280px: toggle hidden, sidebar sticky | The spec itself (gated skip w/ reason when no backend; runs under `test:e2e:full`) |
| 3 | A-3 | Lint-debt truth pass: remove the 30 unused-vars + 1 prefer-const + 1 no-unescaped-entities (mechanical, test-behavior-preserving); hoist `CustomTooltip` out of `GSTF5Chart` (A-6); remove the dead `mounted` state (A-5). Update the documented register to the truthful post-fix count. | Full vitest 511 must stay green (no test-semantics change); dashboard chart vitest still green after the tooltip hoist |
| 4 | A-4 | `data-scroll-behavior="smooth"` on the `<html>` in the root layout | Root-layout render test (attribute present); live console re-check — the Next.js warning disappears |
| 5 | A-8 | `API_CLI_Usage_Guide.md` alignment: truthful metrics (735P/5S backend, 511 vitest), credit-note /approve posts a REVERSED journal (P11/C-1), session-persistence section rewritten to the storageState truth, live re-verification of the documented endpoint contracts (login, list envelope `{results,count}`, journal-entries mount, approve flow) | Live curl gate against the running stack (executed, logged) |
| 6 | A-9 | `DEPLOYMENT.md` validation + P12 spot checks; `.env.example` no-drift check | grep-level diff against the env-read audit |
| 7 | — | Screenshots of the remediated surfaces (mobile nav open/closed, desktop, plus a P11-surface re-capture) → `docs/screenshots/` (session-25 series), pixel+DOM verified | Screenshot driver asserts DOM truths per surface |
| 8 | — | Docs truth pass: README counts/milestone, CLAUDE.md, AGENTS.md P12 patterns, PAD note, `ledgersg_SKILL.md` lesson + version bump | Claims checked against executed gate output |
| 9 | — | P12 report (`docs/REMEDIATION_2026-11-23_P12_REPORT.md`), session log, `worklog.md` entry, final commit + SSH-wrapper push | The final gate below |

## 4. Verification gate (all must be green before push)

1. `pytest --reuse-db --no-migrations -q` → 735P/0F/5S (backend untouched; must not regress)
2. `npx tsc --noEmit` → 0
3. `npx vitest run` → ≥ 511 + new shell tests, 0 failed
4. `npm run test:coverage` → green at the ratchet
5. `npm run build:server` → green
6. `npx eslint src` → findings strictly ≤ pre-fix set minus the fixed classes; **no new findings**, updated truthful register
7. `npm run test:e2e` → 11P + gated (24 now) with reasons
8. `npm run test:e2e:full` (live stack) → all green incl. the new mobile-nav spec
9. Live agent-browser re-verification: Escape closes the open menu, focus returns to the toggle, body scroll locks, the Next.js scroll warning is gone
10. Screenshots present + DOM-verified; API guide commands executed against the live stack

## 5. Commit plan

Conventional commits on `main` only, one per logical task: the a11y fix,
the e2e spec, the lint-debt truth pass, the root-layout attribute, the
docs/API-guide pass, the screenshots, the worklog/session/report. Push via
`docs/ssh_git_wrapper_v3.py` with remote-ref verification (the documented
paramiko shim path).

## 6. Deferred register

Carried forward unchanged from P11 §carried-forward (H-02 base-currency
reporting; audit READ surface; CSRF Origin-check; backend ruff debt; F5
period-cut semantics; pay_return; full PINT Schematron; ledger pagination;
invoice update_line; B6 list-envelope; aged netting; quote lifecycle enum;
TB zero-activity; reports export; TAX-group coarse type; Storecove;
dashboard trends; CoA page; Reg-11 remainder; password reset; contacts
merge; email verification; blank-UEN modeling; e2e bootstrap script;
coverage headroom) **plus** the new A-7 (recharts mount noise),
the mounted-gate `set-state-in-effect` replacements (A-5-adjacent), the 3
exhaustive-deps, the incompatible-library informational, and the 36-item
`no-explicit-any` register (unchanged policy).
