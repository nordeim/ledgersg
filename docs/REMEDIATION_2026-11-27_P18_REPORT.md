# LedgerSG — Remediation Report (P18 Sprint: Statutory-Record Locking, the Contrast Debt, the Celery Coverage Completion & the Fresh-Host Truth)

**Date:** 2026-11-27 (session 36 — executed across two context windows; the workspace, PG data, Redis, the double-forked dev stack and the saved plan all persisted across the outage, zero loss)
**Base commit:** `56f8f835` (main — post-P17, all gates green)
**Plan:** `docs/REMEDIATION_PLAN_2026-11-27_P18.md` (validated against the codebase before execution)
**Source inputs:** three parallel deep audits (backend concurrency/contracts/Celery; frontend compiled-CSS v4 ground truth + a11y contrast; cross-cutting docs/CI/scripts truth) with lead hand-verification of every High finding in source, plus the documented P17 baselines reproduced on the carried-forward workspace (882P/0F/5S · vitest 582/582 · tsc 0 · eslint 0E/5W · mobile-nav 17/17 — the environment had survived the context recycling as double-forked daemons).
**Method:** TDD (RED → GREEN → full gate) for every behavioural fix; lint parity on touched files; conventional commits on `main`; `skills/` excluded from all checks/tests/compilation; one additive schema section (§15c completion — v1.2.2), no other DDL.

---

## 1. Verification Ledger (executed evidence)

| Gate | Result |
|---|---|
| Backend `pytest --reuse-db --no-migrations -q` (as `DB_NAME=test_ledgersg_dev`) | **914 passed, 0 failed, 5 skipped** (882 baseline + 32 new P18 tests: 27 behavioural + 5 schema gates) |
| `pytest tests/invariants -q` | **34 passed** |
| `pytest tests/security -q` | **83 passed, 3 skipped** (78 baseline + 5 new §15c schema-gate tests) |
| `manage.py check` (development settings, live stack) | 0 errors (the documented W001 only) |
| Frontend `npx tsc --noEmit` | 0 errors |
| Frontend `npx vitest run` | **601/601 passed** (70 files; 582 baseline + 19 new P18 tests) |
| `npx eslint .` (whole tree incl. `e2e/`) | **0 errors, 5 warnings** — parity held |
| `npm run build:server` | green (Next 16.4.6 standalone + static copy) |
| `npm run test:e2e:full` (live stack) | **40 passed, 0 failed, 0 skipped** — the demo substrate bootstrap (DEPLOYMENT.md §9: user → org → contact, then the p11 `ensureDemoActivity` self-bootstrap) executed on the re-loaded v1.2.2 schema; a mid-session tool-call-tied backend restart taught the fresh-run lesson (both incidents below) |
| The runtime-role gate (`scripts/rls_smoke.py --base :8001` as `ledgersg_app`) | **13/13 steps green** (register → org 201 → contact → invoice → approve under RLS → bank account → payment+allocation → F5 create+compute) |
| Mobile-nav live probe (`scripts/mobile-nav-audit.js`) | **17/17 at 375/800/1280** — toggle, closed-drawer `visibility:hidden`, overlay, X hit-target, transition-aware close, no overflow, no console errors, sticky tablet/desktop, the v4 space-y trap sweep clean. **The navigation works; no TailwindCSS v4 bug exists** (seventh consecutive live settlement) |
| The production-CSP smoke (`scripts/prod-csp-smoke.js`) | **5/5** — nonce served, no unsafe-inline, hydration happened, zero violations, shell rendered |
| Screenshots | **8 new** (`docs/screenshots/104-111_*_session36.png`) — DOM-verified per surface, md5-unique, non-blank pixel-verified; the P18 proofs: the PAID badge pairing (`bg-success text-void`, live count 1), the settings "Registered" badge pairing (live count 1), the InvoiceNow card, and the animate-restored dialog (`animate-in` + `zoom-in-95` on the open Radix dialog, computed `animation: enter 0.2s` — the utilities compile and run again) |
| CI | a new `e2e` job runs the specs with no backend service (chromium-only; the 29 backend-gated specs skip via their own `test.skip(!apiUrl)` guards — no `--grep` filter is involved. P19/X-L1 erratum: an earlier draft of this row said "`--grep`-scoped", which does not match ci.yml); the coverage ratchet now enforces a measured `src/hooks/**` floor |
| Schema | **v1.2.2** — §15c completed with `django_session` + `django_admin_log` (idempotent, SQL-First, both local DBs re-loaded and re-verified at the fresh-load count of 30 domain tables) |

## 2. What Was Done

### Phase 0 — environment & baselines (carried-forward workspace)

The context window recycled mid-sprint; the workspace, PostgreSQL 17 data,
Redis 8 and the double-forked `next dev` all survived. The dev backend
(the one non-daemonized process) had died with its tool call — restarted
via `scripts/daemonize.py`, both DBs verified at v1.2.2, the demo
substrate re-bootstrapped. **Every documented baseline reproduced green**
before any change.

### The user-named focuses, settled live

**Mobile navigation:** 17/17 probe checks PASS on the remediated tree
(375/800/1280) — **no TailwindCSS v4 bug exists** (seventh consecutive
live settlement; the P18 shell changes — FE-M1's Escape nesting — were
re-probed specifically for regression risk).

**The real Tailwind v4 bug class (FE-L1):** the mobile nav was never
broken — but `tailwindcss-animate` (a v3 plugin) was silently dead under
v4, so every `animate-in`/`fade-in-0`/`zoom-in-95`/`slide-in-*` utility
on the Radix primitives (dialog, select, toast) compiled to **nothing**
— all enter/exit animations were missing. Fixed with the v4-native
`tw-animate-css@1.4.0` (pure CSS, `@import "tw-animate-css";` in
`globals.css`), gated by a compiled-CSS design-token test that builds
the CSS through the repo's own postcss pipeline and asserts the utility
classes exist, plus the live dialog capture (computed `animation: enter
0.2s`).

### Phase 1 — backend: statutory-record locking & the concurrency completion (each: RED → GREEN → suite)

- **BE-H1** `gst/return_service.py` — `generate_f5` + `review_return`
  now wrap in `transaction.atomic()` with `select_for_update()` on the
  return row and a post-lock status re-check (mirroring `file_return`).
  Pre-P18 a FILED statutory record could be raced: `generate_f5` read
  `COMPUTED`, passed the gate, `file_return` filed and committed, then
  `generate_f5.save()` ran unconflicted and overwrote every box value
  while `filed_at` stayed populated — the P14/C-2 regression shape
  reopened through a TOCTOU. Now refused with the FILED record intact.
- **BE-M2** `banking` — `unallocate()` locks payment + document (the
  `allocate` lock order); `unreconcile()` locks transaction → payment
  (the `reconcile` order); `ResourceNotFound` contract preserved via
  `select_related`.
- **BE-M4** `convert_quote_to_invoice` — quote row lock + post-lock
  status re-check (double-convert refused 400).
- **BE-M5** `add_line`/`remove_line` — the document row is locked for
  the line-number read+insert inside `atomic`; the residual
  `IntegrityError` is caught and typed (400, not 500).
- **BE-M6** `_validate_credit_note_reference` — the original document
  is locked for the cap read, and the validation runs inside
  `create_document`'s atomic block (racing credit notes jointly
  exceeding the cap are refused).
- **BE-M3** `journal_service.create_entry` — posting to a
  header/`not is_active` account is a typed 400; `archive_account`
  locks the row and re-checks the balance.
- **BE-M1** `peppol/tasks.py` — the three task bodies wrap in
  `common.tenant_context` (org resolved from the log row/task arg); the
  cleanup task's per-org dispatch contract is explicit.
- **BE-L3** the email task classifies `DoesNotExist`/`ResourceNotFound`
  as terminal (log + return, no retry).
- **BE-L5** `send_email` gated to APPROVED SALES_INVOICE (mirrors
  `send_invoicenow`).
- **BE-L6** `_validated_exchange_rate` catches
  `InvalidOperation`/`TypeError`/`ValueError` → `ValidationError` (garbage
  string → 400).
- **BE-L2** `<str:transaction_id>` → `<uuid:transaction_id>` on the
  banking routes (malformed → 404 at routing).
- **BE-L4** `create_return_periods` catches the UNIQUE violation → a
  clean typed refusal/skip.
- **BE-M7** `queue_task` under `CELERY_TASK_ALWAYS_EAGER=False`:
  `.delay` fires only after commit, never on rollback
  (`django_capture_on_commit_callbacks`).

### Phase 2 — schema §15c completion (v1.2.2, SQL-First, additive)

`django_session` + `django_admin_log` added to §15c (`CREATE TABLE IF
NOT EXISTS`, grants for `ledgersg_app`/`ledgersg_owner`); the
`django_celery_beat_*` tables stay a documented opt-in note (no beat in
the documented runtime). Header + §15c history bumped to **v1.2.2**;
§13 upgrade ladder updated. Both local DBs re-loaded idempotently. The
reload surfaced a real portability bug — `CREATE INDEX` names cannot be
schema-qualified — fixed in the SQL file; the fresh-load domain-schema
count re-verified at **30 tables**.

### Phase 3 — frontend: the contrast debt, the real Tailwind v4 fix, the escape nesting (vitest RED → GREEN)

- **FE-H1** the three `bg-success text-white` badges → `bg-success
  text-void` (invoice-detail PAID, settings "Registered", InvoiceNow
  "Configured") — the P17/FE-M1 token fix had made white-on-neon-green
  compile at **1.33:1** (AA needs 4.5:1). Pinned by a new permanent
  regression wall, `src/__tests__/contrast-pairings.test.ts`: every
  `bg-success`/`bg-alert` usage in `src/` must pair an approved
  foreground (`text-void`/`text-carbon`), enumerating files — the class
  of bug that slipped through a token test that never checked pairings.
- **FE-M2** the same pairing debt swept: `badge.tsx` + `button.tsx`
  destructive + the invoices OVERDUE badge (`text-white` → `text-void`;
  hover `bg-red-700` → `bg-alert/90`, staying in the token system).
- **FE-M3** `--color-text-muted: #666666` → `#8A8A8A` (the muted-on-
  carbon pair now measures ≥4.5:1); the header claim corrected to
  "WCAG AA (token pairs verified ≥ 4.5:1)" — pinned by a computed
  WCAG-ratio unit test over the pairs the components actually pair.
- **FE-M1** the drawer's Escape handler defers while the org menu is
  open (the menu consumes the first Escape — focus returns to the
  trigger; the second Escape closes the drawer).
- **FE-M4** the customer UEN schema → the shared normalizing
  `optionalUenSchema`; the new-organisation form validates via
  `uenSchema.safeParse` (one error-message source); the lowercase-UEN
  acceptance parity is pinned across all three surfaces.
- **FE-L1** `tw-animate-css@1.4.0` installed + imported (see the named
  focus above).
- **FE-L3** `hasUnsavedChanges` is reset on successful submit before
  `onSuccess`.

### Phase 4 — configs (the named ask: strengthen the existing suites)

- **CFG-L1** `.github/workflows/ci.yml`: a new `e2e` job — chromium-only
  Playwright install + `npx playwright test --grep` scoped to the 11
  no-backend specs; no backend service required.
- **CFG-L2** `vitest.config.ts`: the coverage ratchet now enforces a
  **measured** `src/hooks/**` floor (an honest ratchet — the header's
  aspirational 85% is no longer claimed without enforcement).
- **CFG-L3** `@types/uuid` removed — `uuid@13` ships its own types (the
  stalled `@types/uuid@10` was the major mismatch).

### Phase 5 — docs truth pass & the fresh-host deploy guide

- **DOC-H1** DEPLOYMENT.md §4: the expected fresh-load count corrected
  to **30** (the old 40 was measured on a polluted test DB) + the
  public-schema note + the dev-vs-migrated one-liner.
- **DOC-M1** §8/§12 + the backend Dockerfile: `collectstatic --noinput`
  before the production gunicorn boot (the manifest-bound storage made
  the step load-bearing); LOG_DIR mkdir noted.
- **DOC-M9** `docs/setup_pg_z.sh`: `PG_BASE` parametrized (default
  unchanged — the sandbox path keeps working verbatim); §3/§12.3 note
  the override.
- **DOC-M2/M3/L7** the API guide: the org PATCH URL fixed, the
  double-reversal attribution corrected, "409-class" → "typed 400"
  across SKILL/CLAUDE/README; a P18 addendum appended.
- **DOC-M4..M8** README: the tech-stack table refreshed to the real
  pins, Key Files `middleware.ts` → `src/proxy.ts` + `src/lib/csp.ts`,
  Redis marked required, the Docker section cross-referenced with the
  GitHub-HEAD caveat, `ENABLE_ADMIN` documented.
- **DOC-M7** both `.env.example`s (root + backend) gain `ENABLE_ADMIN`
  with the dev/prod default note; the full var list re-audited against
  the settings module — the user's named deliverable.
- **DOC-L1..L8** §11 `/login/` + `-L`; the CI header (882/2026-11-27);
  PAD ghost entries (`src/proxy.ts`, `lib/server/` removed, 16.4.6);
  README tree + venv path; SKILL §16/v1.1.0; the Makefile canonical
  pytest flags.
- **DEPLOYMENT.md** the fresh-host completeness pass: §1–§15 verified as
  a from-`git clone` path with the audit's gap list closed (prereqs
  incl. `python3-venv`/Node 20/Redis 7-8, `PG_BASE`, playwright
  `--with-deps`, collectstatic, ENABLE_ADMIN, the two Docker paths
  cross-referenced).

### Phase 6 — live gates, screenshots, deliverables

The full gate matrix re-run green (§1); 8 DOM-verified screenshots
(`scripts/capture-screenshots-session36.js`); this report;
`docs/session_36.md`; the worklog entry; the conventional commits and
the SSH-wrapper push.

## 3. Incidents & lessons (recorded for future sessions)

1. **The tool-call-tied backend.** The dev backend restarted at the end
   of window 1 was started inside a tool call, not through
   `scripts/daemonize.py` — it died with the call's timeout, mid-e2e-run
   (the log ends at the health check; 26 spec failures cascaded). Every
   long-lived process in this sandbox must be double-fork daemonized
   (the P13 lesson, re-learned). Both backends (8000/8001) ran
   daemonized for this session's gates.
2. **The fresh-DB e2e bootstrap contract.** On a re-loaded schema the
   full live gate needs DEPLOYMENT.md §9 steps 1–3 (user → org →
   **contact**) executed before the run: the p11 helper only *reuses*
   `contacts.results[0]`, and the banking spec (alphabetically first)
   needs one. A first run without the contact fails 3–5 specs; with it,
   40/40 in one pass. Additionally, a killed first run can leave the
   demo UEN patched onto the wrong contact (`contacts[0]` shifts once
   the intended substrate contact exists) — the guard then refuses the
   PATCH as a duplicate. The surgical fix (blank the incidental
   contact's profile fields) is recorded here; the idempotent re-run
   contract holds thereafter (the UEN guard excludes self).

## 4. Deferred register (carried forward, not dropped)

The full P16/P17 register carries forward (ContactPicker WAI-ARIA
combobox, in-app unsaved-work route guard, backend list pagination, the
audit-log `INSERT WITH CHECK (TRUE)` surface, the ruff ~1216 mechanical
register, UEN checksum, the H-3 DB-trigger layer, H-05b attachment
model, CSV size cap/dedup, CSP report-endpoint bound, positive
membership-cache invalidation design, journal serializer tolerance
alignment, `lines max_length`, `display_money` finite-gate consistency,
email-restore lifecycle evidence). New deferrals from this session's
audits: the PaymentsTab same-route prefill re-trigger (no current
producer), the list-envelope `{data}`/`{results}` unification, the
NULL-context SELECT policies on `core.user_organisation`/`core.role`
(documented tradeoff), the org-mid-flight dead-letter design beyond the
terminal classification, the remaining 5 eslint parity warnings.
