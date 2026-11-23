# Session 23 Log — P11 Sprint: Accounting Truth & Config Honesty (2026-11-23)

Continued across a context-window outage (the first half's raw log is
`docs/session_22.md`). The workspace, databases, Redis, dev servers and the
saved plan all persisted across the boundary — the in-flight Task-1 test
fixture patch was completed on resume with zero re-work. All 17 commits were
made after the resume and gated before the push.

## Setup and baselines

Repo refreshed at `1b3e267d` (post-P10, clean tree); all five core docs and
the five session/remediation docs reviewed and validated against the
codebase. PostgreSQL 17 rootless per `docs/setup_pg_z.sh` + the
rootless-postgresql skill (role `ledgersg`, both DBs, schema v1.1.0 — 30
domain tables each; schema-qualified under `core`/`coa`/`gst`/`journal`/
`invoicing`/`banking`/`audit`); Redis 8 rootless, daemonized (it dies without
it); backend venv via `uv sync --all-extras`; frontend `npm ci` + playwright
chromium. All four baselines reproduced exactly before any change
(backend 687P/5S, vitest 505/505, typecheck 0, e2e 11 + 20 gated).

## Audit (Mode C)

Scanner pass clean (all hits in the documented FP classes). Three parallel
deep-audit agents; every Critical/High hand-verified with line numbers,
including two runtime reproductions: the production cache backend crash
(`django_redis` is a dev extra — production never installs it) and the
`DEBUG=true, DEBUG_TOOLBAR=false` startup ImportError (two gates disagreed
on the knob).

## The P11 plan

`docs/REMEDIATION_PLAN_2026-11-23_P11.md` — 2 Criticals, 7 Highs, 16
Mediums, 9 Lows, 19 tasks, verification gate, commit plan, deferred
register. Validated against the codebase before execution.

## Remediation (TDD, Tasks 1–15)

Every production change RED-first. Headlines:

- **C-1** credit notes posted invoice-direction GL entries — a credit note
  DEBITED the customer's AR. Direction now flips by document type; the F5
  computation nets credit notes and stops counting quotes (H-3).
- **C-2** production settings boot (builtin Redis cache, copy-on-write
  LOGGING, the `LOG_DIR` knob); **H-5** debug_toolbar has one gate.
- **H-1/M-3/M-4** the contacts edit dialog prefills from the DETAIL endpoint
  and a save persists uen/gst_reg_number/peppol_id (previously an
  unconditional save ERASED them with a success toast).
- **H-2/M-1/M-11** the F5 boxes panel reads the real box keys (every box
  previously rendered "—"); **H-4/M-7/L-2** the dashboard GST payable equals
  the F5 net GST, the chart takes raw values, single currency prefixes.
- **M-2/M-5/M-6** bank PATCH 404; typed org-settings PATCH; routing-layer
  UUID 404s. **M-8** the audit trail carries request context and emits
  LOGIN/LOGOUT. **M-9..M-16 + L-batch** CI/config/Docker/CSP truth,
  root hygiene, riders.

## The live gate

The full accounting loop verified against the running servers: contact
PATCH (gst_reg_number persists), invoice DRAFT→APPROVED (journal posted),
credit note APPROVED (reversed journal — the ledger proof), F5 computed
(boxes net credit notes), dashboard GST payable = 315.00 matching F5 Box 8.
Seven screenshots (`docs/screenshots/59-65_*_session23.png`), pixel- and
DOM-verified. Three new e2e specs (F5 boxes, contacts round-trip, dashboard
GST) with an idempotent `ensureDemoActivity` bootstrap.

The live gate's own findings, all fixed with regression tests: the register
throttle's hardcoded 5/hour literal (knob pattern applied — dev budget 120/h,
production posture asserted unchanged), the banking spec's consumed fixture
(self-creating now), the p10 contacts row regex (generalized to any real
row), the unscoped failed-login audit assertion (scoped to the failing
user), and the sandbox process-cleanup behavior (backend + e2e run in one
call).

## Final state (all Verified)

Backend **735P/0F/5S** (687 + 48); security 66P/3S; vitest **511/511**
(505 + 6); typecheck **0**; coverage green at the ratchet; `build:server`
green; default e2e **11 + 23 gated**; live e2e **33P/1S/0F**; screenshots 7
(content-verified); docs truth-passed (README v0.3.0/v0.6.0 + counts 1,280;
CLAUDE v2.15; PAD v3.8; SKILL v2.0.0 with lessons 42–50; AGENTS P11
patterns; DEPLOYMENT.md P11 revision — the fresh-host guide re-verified with
the P11 spot checks, the register budget and the Docker path marked
statically-validated); `.env.example` re-audited 1:1 (backend gains `LOG_DIR`).
All commits on `main`, pushed via the SSH wrapper with remote-ref
verification.
