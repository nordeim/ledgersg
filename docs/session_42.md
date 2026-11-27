# Session 42 — the P21 sprint log (the list-envelope unification, the InvoiceNow evidence stamp, the cache-commit truth & the banking a11y batch)

The standing task cycle on the surviving session-40 workspace: the
workspace was refreshed (`git pull` — only `docs/session_41.md` had
landed), the environment was still live (rootless PG 17, Redis 8, both
dev servers, the venv, node_modules) and `test_ledgersg_dev` was
recreated and loaded with schema v1.2.2.

The baselines reproduced exactly before any change: **backend
950P/0F/5S · vitest 627/627 · tsc 0 · eslint 0E/0W · e2e 40/40 ·
rls_smoke 13/13 · mobile-nav 17/17** (the twelfth live settlement of
"no Tailwind v4 bug") **· prod-CSP 5/5**.

Three parallel deep audits (Mode C) scoped to the P20 diff + the
deferred register → **0 Critical / 2 High / 20 Medium / 15 Low / 13
Informational**; every High and every execution-scoped Medium
hand-verified in source. The headline findings: the list layer speaks
5 shapes across 30 sites (the deferred register's big-ticket item —
19 `{results,count}` + 1 `{results,totals}` + 6 `{data,count}` + 3
report-style `{data}` + 1 raw array), `invoicenow_sent_at` is read by
the void/unallocate restore but written by NOTHING (dead branch), the
dashboard cache is not invalidated by voids or manual journal entries
and every invalidation runs INSIDE the transaction (the re-seed race),
the bank-account default flag races (two concurrent set_defaults can
leave two defaults; full-row saves clobber concurrent edits),
ValidateBalanceView 500s on malformed bodies, and the two banking a11y
Highs (the unnamed Make-Payment Reference input; the keyboard-inaccessible
CSV import). The cross-cutting audit's pattern: the P20 truth pass
updated every doc's top status block but left second-tier surfaces
stale (9 Mediums + 5 Lows — counts, labels, one misattributed CLAUDE
milestone header). Bonus: the RLS isolation test read the wrong
envelope key with a default — a VACUOUS assertion that always passed.

The plan saved (`docs/REMEDIATION_PLAN_2026-11-27_P21.md`) and
anchor-validated, then executed TDD.

Phase 1 (backend, every fix RED first): the **envelope unification** —
7 sites → `{results, count}` (trial balance keeps `totals` +
`as_of_date`, the GST post keeps `message`; reports keep `{data}` —
*lists → results, reports → data*), the frontend + e2e + bootstrap
consumers migrated, the vacuous RLS assert fixed · the bank-account
default-flag locking (the org-wide sorted lock + `_get_locked` +
`update_fields`) · the void/manual-entry dashboard invalidation ·
every cache invalidation/deletion moved to `transaction.on_commit` ·
the `invoicenow_sent_at` stamp on DELIVERED (stamp-once, isnull
filter) · the ValidateBalance typed-400 body → **backend 969P/0F/5S
(+19 P21 tests)**.

Phase 2 (frontend, vitest RED first): the Reference accessible name ·
the `sr-only` CSV input (focusable + labelled, was display:none) · the
import dialog's unique ids · the loader live regions on every
remaining surface (banking/settings/contacts/reports/fiscal/
invoicenow/allocation) · the timezone class completed (`isoYearOf`
lexical GST year + `localTodayISO` local-calendar defaults) · the
payment-card keyboard contract · the reconcile `aria-pressed` · the
visible-label ContactPicker (`aria-labelledby`) · the dead
`accent-primary` token (compile-verified fix + a new design-tokens
gate) · the always-rendered `aria-controls` regions · playwright
`video: retain-on-failure` · the envelope consumers (use-fiscal,
fiscal-card, the auth-provider's one typed helper) → **vitest 641/641
(75 files, +14 P21 tests)**.

Phase 3 (cross-cutting): the docs truth pass (README badge/section/
order, CLAUDE's P19 block retitled + the P21 milestone, AGENTS
header/version/posture + the P21 lessons, SKILL quick-ref + the
NUMERIC v1.1.0 attribution, PAD lint row, ci.yml comments, the API
guide's "Current" labels + version 3.2.0 + the P21 addendum with the
7-route envelope table, DEPLOYMENT counts); the bootstrap script's
dual-shape fallback retired; the `.env.example`s re-verified truthful
(the audit's variable-by-variable table — no changes required).

The full gate matrix, all executed green on the remediated tree:
backend **969P/0F/5S** · vitest **641/641** · tsc 0 · eslint **0E/0W**
· **coverage green at the ratchet** · **e2e:full 40/40** · **rls_smoke
13/13 as `ledgersg_app`** (the :8001 instance restarted with the P21
code) · **mobile-nav 17/17** (the thirteenth settlement) · **prod-CSP
5/5** · build:server green. The stale `--noreload` backends were
restarted before the live gates (the P13 lesson); the live envelope
verified on :8000.

The deliverables: 8 DOM-verified screenshots
(`docs/screenshots/128-135_*_session42.png`, md5-unique, non-blank
pixel-verified — the P21 proofs: the Reference input filled by label,
the sr-only CSV input, the payment-card role=button, the loader live
region captured mid-delay, the lexical GST year, the org selector
reading the unified envelope); the P21 plan + this report; this log;
the worklog entry; the docs truth pass; the conventional commits and
the SSH-wrapper push to main.
