# Session 27 (2026-11-24) — P13 Sprint: Transactional Truth, Header Consolidation & the Typed Suite

The workspace had been reset by a sandbox recycle; the repo re-cloned from
`main` at `69f13325` (post-P12). The prior session-27 attempt was
interrupted during its audit phase (no commits, no plan on disk — only the
prep scripts in the workspace `scripts/` dir survived, now reused).

## Environment recovery (the documented P10 playbook)

- PG's extracted binary tree lost `usr/share/postgresql/17` (timezonesets)
  and the cluster lost empty subdirs incl. `pg_logical/snapshots`
  (checkpoint-fatal — a gap `ensure_pg.sh` didn't cover; the debs
  re-extracted and all subdirs restored per `skills/rootless-postgresql`).
  The dev + test DBs and their data survived (30+2 tables, 8 distinct
  `trg_audit_*` triggers, the demo substrate intact).
- Redis binaries were gone — debs re-extracted + `liblzf1` added (the
  prior session's LD_LIBRARY_PATH requirement).
- Backend venv + node_modules rebuilt (uv sync / npm ci); playwright
  chromium re-installed (1208 for 1.58.2).
- NEW: a double-fork daemonizer keeps runserver + next dev alive across
  tool calls (the one-call constraint of sessions ≤26 is lifted; recorded
  in AGENTS + the worklog).

## Doc review + alignment

AGENTS/CLAUDE/README/PAD/ledgersg_SKILL digested (via parallel explore
agents + lead reading), then session_25/26, the P12 plan/report and the
worklog — the post-P12 state confirmed against the codebase: all
baselines reproduced exactly (backend 735P/5S; tsc 0; vitest 518/518;
eslint 45; e2e default 11+26 gated; live e2e:full **37P/0F/0S** — the
P12 data-conditional skip passes now that data exists).

## The sprint focus (live, not by inspection)

- **The mobile navigation menu works** — full re-verification at
  375/800/1280 (toggle, overlay, Escape/Tab/scroll-lock/focus-return,
  navigate+auto-close, desktop sticky, no overflow, no errors).
- **No Tailwind v4 bug** — settled this time with an @layer-RECURSING
  matched-rule trace (the P12-era flat walk predated Next 16's layer
  emission; mine initially had the same blind spot — a CSSStyleRule's
  `cssRules` is an empty CSSRuleList, not null, so the walk never
  matched): only `.inline-flex` + the media-gated `.md\:hidden` apply;
  `display:flex` is correct flex-item blockification. The validation
  report's trap log swept: no space-y+explicit-margin children on any
  nav surface (computed margin-block-end 4px / margin-top 0px — pure v4),
  2 shadow-sm usages app-wide, zero gradients, hex palette.

## The audit (three parallel agents + lead hand-verification)

Frontend: H-1 (dual header definitions — the middleware's CSP silently
won, live-verified: vercel.live + unconditional unsafe-eval/inline
defeated the P11/M-15 hardening), H-2 (the CLOSED sidebar
keyboard-focusable — WCAG 2.4.3/2.4.7), M-1 (overlay z-40 above the
header — the X toggle not the real hit target), M-3 (mutation retry: 1 —
double-submission), M-4 (coverage excludes 57 of 104 files), W-3 (36
any-casts: 35 mechanical + 1 production). Backend: B-1 (the exception
handler's 500 fallback COMMITS partial writes — runtime-reproduced), B-2
(the GST quantum off by one decimal — interpreter-proven 9.005 vs 9.00),
B-5..B-14 (typed ImmutabilityError, date.today() sweep, copy-on-write
drift, InvoiceNow 404s, reversal atomicity, tolerance alignment, health
hygiene). Docs: the D-1..D-23 drift register. Every Critical/High
hand-verified by the lead before the plan.

## The plan + execution (TDD)

`docs/REMEDIATION_PLAN_2026-11-24_P13.md` — 20 tasks, validated against
the codebase site-by-site before execution. All code tasks RED first:
B-1 (2 rollback gates; the dispatch canary was the bug's own proof),
B-2 (sub-cent fixtures), H-1 (an 8-test header-config gate), H-2/M-1
(vitest + e2e visibility/hit-target), B-5/B-6/B-7/B-10/B-11/B-13/B-14,
M-3, W-3 (the 35 casts via a brace-matching transform — first version
dropped the closing brace, caught by eslint parse errors, reverted and
fixed), M-4 (per-glob thresholds at the measured floor), the playwright
expect-timeout + axe-scan additions, the .env.example pass, screenshots
72–79, the docs truth pass (AGENTS header, PAD, SKILL §4 + lessons
55–58, README blocks + P13 milestone, CLAUDE rows + the cookie-claim
correction, DEPLOYMENT §12.1–12.4 production ops, API guide v2.6.0).

## The final gate (all executed)

backend **750P/0F/5S** (invariants 34P; security 69P/3S; production
boots) · vitest **530/530** · tsc 0 · coverage green (63/51/52/62 +
src/lib 73/52/74/71) · eslint **9** (any-casts cleared) · build:server
green · e2e default 11+29 gated · **live e2e:full 40P/0F/0S** · the
served headers + boot log verified live (no deprecation warning) · the
GST sub-cent live proof (9.00) · 8 pixel-verified screenshots.

## Push

Conventional commits on `main` via `docs/ssh_git_wrapper_v3.py --remote
git@github.com:nordeim/ledgersg.git` (the paramiko shim; remote-ref
verified; key shredded after push).
