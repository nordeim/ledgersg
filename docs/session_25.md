# Session 25 Log — P12 Sprint: Mobile-Nav Truth & A11y Floor (2026-11-23)

## Setup and baselines

Repo refreshed at `ba4357d4` (post-P11 push `8ec6949b` + the user's
`docs/session_24.md` log; clean tree, fast-forward). Core docs re-reviewed
(AGENTS.md, CLAUDE.md, README.md, PAD, ledgersg_SKILL.md — all last touched
by the P11 truth-pass commits) and the session/remediation docs read
(session_23/24, the P11 plan + report, worklog). PostgreSQL 17 rootless had
SURVIVED the recycle (daemonized), Redis too — verified: both DBs reachable
(role `ledgersg`, schema-qualified apps under `core`/`coa`/`gst`/`journal`/
`invoicing`/`banking`/`audit`, the 8 `trg_audit_*` triggers wired to
`audit.log_change`). Venv + node_modules + playwright chromium persisted.
All baselines reproduced exactly before any change: backend **735P/0F/5S**,
vitest **511/511**, typecheck 0, coverage green, `build:server` green,
e2e 11P + 23 gated.

## The sprint focus — mobile nav + the suspected Tailwind v4 bug

The audit ran LIVE per the instructions: agent-browser (the repo skill) at
375×812 / 800×1024 / 1280×800 against the running dev stack, with the repo
skills' taxonomies as the checklists (`skills/nextjs16-tailwind4` §9 — the
A–H failure classes, §9.4 the mandatory overlay a11y set, §10 the v4 visual
debug playbook; `skills/tailwind-patterns`; `skills/astro-7-patterns` §7).

**Verdict 1 — the mobile nav works**: toggle visible/clickable/keyboard-
operable at 375 and hidden ≥768; sidebar opens/closes with the animated
`translate`; the overlay closes on click; nav links navigate AND
auto-close; desktop/tablet sticky; no overflow; no console errors. One
early "failure" was my own probe's selector (`a[href='/ledger']` vs the
real `/ledger/` trailing-slash contract) — re-verified truthful.

**Verdict 2 — no Tailwind v4 bug exists here**: the `display:flex` reading
on a `md:hidden` toggle was settled by a matched-rule trace through
`document.styleSheets` (only `.inline-flex` + the media-gated `.md:hidden`
match) — it is correct CSS flex-item blockification. The v4 setup is clean
(no legacy config — the #1 v4 failure class). The nav's transition/
translate utilities all trace to correct v4 cascade-layer behavior.

**Real findings:** the overlay's four §9.4 behaviors were ALL missing
(Escape verified non-functional live), no authenticated mobile-nav e2e
coverage existed, the lint register had drifted (documented 47 vs real 79),
`data-scroll-behavior` was missing, the shell carried a dead `mounted`
state, `CustomTooltip` rendered in-component, the recharts mount noise
(verified cosmetic — the chart is correct at every viewport), and the
API_CLI guide was stale.

## Remediation (TDD; plan `docs/REMEDIATION_PLAN_2026-11-23_P12.md`)

- **A-1** — the overlay floor in `shell.tsx` (Escape close, Tab-cycle
  trap, body scroll lock, focus-in on open, focus-return on close):
  7 vitest, RED 6/7 → GREEN 7/7; live re-verified in the real browser.
- **A-2** — `e2e/mobile-nav.spec.ts` (3 gated specs). First live run
  failed one spec — a Playwright strict-mode violation
  (`getByRole('link', { name: 'Ledger' })` matched the logo "L LEDGERSG"
  by substring) — fixed with landmark scoping + `exact: true`; recorded as
  a lesson (AGENTS patterns + SKILL lessons 51–54).
- **A-3** — the lint truth pass: 30 unused-vars, prefer-const,
  no-unescaped-entities, the tooltip hoist, the dead mounted gate, the
  unused catch binding, the type-only const object, middleware's unused
  param — **79 → 45** with every gate green.
- **A-4** — `data-scroll-behavior="smooth"` on `<html>`; the Next.js
  warning verified gone live.
- **A-8/A-9** — the API guide re-verified live (login contract, 9/9 list
  envelopes, journal mount both directions, the bare-array org route, the
  dashboard metrics endpoint) and rewritten to v2.5.0; DEPLOYMENT.md
  counts patched; env examples re-checked (no drift).

## Final gate (all executed)

backend **735P/0F/5S** (unchanged) · vitest **518/518** · typecheck 0 ·
coverage green · build:server green · eslint whole-tree **45** (register
truthful) · e2e default 11P + 26 gated · **live e2e:full 36P/1S/0F** (37
specs — the 3 new mobile-nav specs green) · live a11y behaviors re-verified ·
6 new screenshots (66–71_session25, pixel- + md5-verified) · docs truth pass
(README P12 milestone + counts, CLAUDE v2.16.0, AGENTS P12 patterns, PAD
v3.8.0 P12 note, SKILL v2.1.0 + lessons 51–54, API guide v2.5.0,
DEPLOYMENT counts) · worklog entry · commits on `main` pushed via the SSH
wrapper with remote verification.
