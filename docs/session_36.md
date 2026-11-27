# Session 36 — the P18 sprint log (statutory-record locking, the contrast debt, the Celery coverage completion & the fresh-host truth)

Continuation of the P18 sprint across the context-window recycle (the
workspace, PG data, Redis and the double-forked dev stack all persisted;
the raw pre-recycle transcript is condensed to its decision points).

Window 1 (pre-recycle, condensed): the P17 baselines reproduced on the
carried-forward workspace (882P/0F/5S · vitest 582/582 · tsc 0 · eslint
0E/5W · mobile-nav 17/17 — seventh settlement of the "no Tailwind v4
mobile-nav bug" verdict). Three parallel deep audits (Mode C) → **0
Critical / 3 High / 20 Medium / 20 Low**; every High hand-verified in
source before planning: BE-H1 (the `generate_f5`/`review_return`
TOCTOU against a FILED statutory record — the P14/C-2 regression shape
reopened through a race), FE-H1 (the P17 token fix made three
`bg-success text-white` badges compile at 1.33:1), DOC-H1 (the §4 schema
count measured on a polluted test DB). The plan saved
(`docs/REMEDIATION_PLAN_2026-11-27_P18.md`), validated anchor by anchor,
then executed TDD:

Phase 1 (backend, every fix RED first): BE-H1 lock+re-check → 4/4;
BE-M2 unallocate/unreconcile locks (the `ResourceNotFound` contract
preserved via `select_related` — the double-lock trap avoided) → 6/6;
BE-M4 quote convert lock; BE-M5 add_line lock + typed IntegrityError
(the scripted re-indent for reliability); BE-M6 credit-note cap lock
inside `create_document`'s atomic; BE-M3 header/archived-account gate +
`archive_account` lock; BE-M1 the three Peppol task bodies in
`tenant_context` (the on-commit test rewritten with
`django_capture_on_commit_callbacks` — the TestCase outer transaction
otherwise defers callbacks forever); BE-L3 terminal classification;
BE-L2/L5/L6/L4 typed-400 batch; 5 pre-existing tests pinning the old
broken contracts updated with documentation → **backend 914P/0F/5S**.

Phase 2: schema §15c completed (v1.2.2 — `django_session` +
`django_admin_log`, idempotent); the reload exposed a real bug — index
names can't be schema-qualified in `CREATE INDEX` — fixed; both local
DBs re-loaded and re-verified at the fresh-load count (30 domain
tables); the §15c gate tests (5) green.

Phase 3 (frontend, vitest RED first): the pairing regression wall
(`contrast-pairings.test.ts` — the path-resolution bug `src/src` fixed;
wash forms `bg-alert/10` excluded, variant-merged/decorative excluded —
exactly the 10 offender lines RED) → FE-H1/M2/M3 GREEN; FE-M1 the
drawer Escape defers to the open org menu; FE-L3 the flag reset on
submit success; FE-M4 the shared `uenSchema` (empty-UEN keeps the
old empty-is-valid semantics — the regression caught and the contract
kept); FE-L1 `tw-animate-css@1.4.0` installed + imported (the *real*
Tailwind v4 bug: the v3 animate plugin's utilities silently compile to
nothing) → **vitest 601/601 (70 files)**.

Phase 4: the coverage ratchet's honest measured hooks floor; the
@types/uuid mismatch removed (uuid@13 ships its own types); the CI e2e
job (the 11 no-backend specs). eslint + build at parity.

Phase 5: the docs truth pass — both `.env.example`s (ENABLE_ADMIN + the
full var audit), DEPLOYMENT.md §4/§8/§12 + the Dockerfile collectstatic
step, `setup_pg_z.sh` PG_BASE parametrization, the README/PAD/SKILL/
CLAUDE/AGENTS/Makefile anchor fixes, the API guide P18 addendum.

Window 2 (this transcript, post-recycle): the environment audit — PG,
Redis and `next dev` alive as daemons, but the dev backend dead: its
log ends at the health check. Root cause: the window-1 restart was
tool-call-tied, not daemonized — the P13 lesson re-learned (recorded in
the report's incidents). Restarted via `scripts/daemonize.py` (PID
survives tool calls).

The live e2e gate on the re-loaded schema: the substrate archaeology —
the register succeeded at 05:58 but the schema re-load wiped it, and
the window-1 "bootstrapped" claim never landed on the restarted backend.
Re-bootstrapped (user → org, 102 CoA accounts seeded), then the e2e
saga: first run 26-cascade (the dead backend), then the contact-guard
discoveries — the p11 helper only *reuses* `contacts[0]`, and banking
(alphabetically first) needs one (DEPLOYMENT §9 step 3 executed outside
the specs); a killed first run had left the demo UEN on the incidental
"E2E Picked Customer" contact (the duplicate guard then refusing the
intended PATCH) — surgically reset, and the guard verified
self-excluding (idempotent re-runs hold).

**The full gate matrix, all executed green:** backend 914P/0F/5S
(invariants 34P; security 83P/3S) · vitest 601/601 · tsc 0 · eslint
0E/5W · build:server green · **e2e:full 40/40** · **rls_smoke 13/13 as
`ledgersg_app`** (the :8001 daemonized instance) · **mobile-nav 17/17**
· **prod-CSP 5/5**.

The deliverables: 8 DOM-verified screenshots
(`docs/screenshots/104-111_*_session36.png`, md5-unique, non-blank
pixel-verified — the PAID badge pairing live, the settings badges, the
animate-restored dialog with computed `animation: enter 0.2s`);
`docs/REMEDIATION_2026-11-27_P18_REPORT.md`; this log; the worklog
entry; the conventional commits and the SSH-wrapper push to main.
