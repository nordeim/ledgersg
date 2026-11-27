# LedgerSG — Remediation Plan (P18 Sprint: Statutory-Record Locking, the Contrast Debt, the Celery Coverage Completion & the Fresh-Host Truth)

**Date:** 2026-11-27 (session 36)
**Base commit:** `56f8f835` (main — post-P17, all gates green at 882P/0F/5S backend · 582/582 vitest · tsc 0 · eslint 0 errors/5 parity warnings · live e2e 40P/0F/0S · rls_smoke 13/13 · mobile-nav 17/17 · prod-CSP smoke 5/5 · schema v1.2.1)
**Method for execution:** TDD (RED → GREEN → full gate) for every behavioural fix; lint parity on touched files; conventional commits on `main`; `skills/` excluded from all checks/tests/compilation; one additive schema section (§15c completion — v1.2.2), no other DDL.

---

## 1. Audit inputs (this session's evidence)

Three parallel deep audits (Mode C) + lead hand-verification of every
Critical/High finding in source, plus the documented baselines reproduced
on the carried-forward workspace (PG 17 + Redis 8 rootless had survived the
context-window recycling as double-forked daemons; both DBs schema-loaded at
v1.2.1; the dev stack live):

- **Baselines reproduced** (all executed, green): backend **882P/0F/5S**
  (`DB_NAME=test_ledgersg_dev pytest --reuse-db --no-migrations -q`,
  18.2s) · vitest **582/582** (69 files) · `npx tsc --noEmit` 0 ·
  whole-tree `npx eslint .` **0 errors / 5 parity warnings** ·
  `manage.py check` 0E/1W · **mobile-nav live probe 17/17 at
  375/800/1280** — **the navigation works; no TailwindCSS v4 bug exists**
  (sixth consecutive live settlement). The P17 header claims matched the
  tree exactly.
- **Backend audit** (P17-diff focus + full money-mutation inventory +
  Celery coverage + contracts + security + tests + deps): **0 Critical,
  1 High, 7 Medium, 9 Low, 5 Informational.** The P17 flagship fixes
  (BE-H1/H2/H3, the 400-sweep, both settings gates, select_related, the
  negative-cache interim) all verified as documented and test-pinned. The
  material gaps: one statutory-record TOCTOU that survived the P16/P17
  lock pass (H-1), the BE-H3 task-body coverage standing at 2-of-5, a set
  of unlocked mutation seams in the same class P17 was closing, and the
  production-only `on_commit` branch having zero test coverage.
- **Frontend audit** (P17-diff focus + compiled-CSS v4 ground truth +
  a11y/contrast + React 19/query hygiene + configs): **0 Critical, 1 High,
  4 Medium, 3 Low, 6 Informational.** The P17 batch verified correct
  against its plan; the one High is a **contrast regression introduced by
  the FE-M1 token fix itself** (the token now compiles, three badges pair
  it with white text at 1.33:1). Tailwind v4 verdict: **CSS-first healthy,
  no systemic v4 bug** — the only dead utilities in the entire tree are
  the `tailwindcss-animate` family (the v3 plugin was never replaced by a
  v4-native one, so `animate-in`/`fade-in-0`/`zoom-in-95`/`slide-in-*`
  on the Radix primitives compile to nothing).
- **Cross-cutting truth audit** (DEPLOYMENT/API guide/env examples/CI/git
  hygiene/scripts/docker): **0 Critical, 1 High, 9 Medium, 8 Low,
  5 Informational.** The DEPLOYMENT.md §1–§13 flows re-executed live
  (all probes return the documented codes) — the material findings are the
  §4 schema count being measured on a polluted test DB (fresh load = 30,
  not 40), a missing `collectstatic` step for the now-manifest-bound
  production storage, and a set of stale README/PAD/SKILL anchors.

## 2. The findings (verified, with evidence anchors)

### High

**BE-H1 — `generate_f5`/`review_return` are unlocked TOCTOUs against the
locked `file_return`/`amend_return`: a FILED statutory record can be
regressed and overwritten.**
`apps/gst/services/return_service.py:201` (`generate_f5` — plain
`get_return`, no lock, no atomic; status gate at :211; unconditional
`save()` at :247) and `:288` (`review_return` — same shape, save at :271);
contrast `file_return` :332 which locks inside `transaction.atomic()`.
Interleaving: (1) `generate_f5` reads status `COMPUTED`, passes the gate;
(2) `file_return` locks, applies the overrides, sets `FILED`/`filed_at`,
commits; (3) `generate_f5.save()` runs unconflicted and overwrites every
box value with recomputeds and regresses status to `COMPUTED` **while
`filed_at` stays populated** — the exact P14/C-2 regression shape,
reopened through a race. The filed statutory record (box overrides + their
`notes` evidence trail) is destroyed.

**FE-H1 — the three `bg-success text-white` badges render at 1.33:1 — the
P17/FE-M1 token fix made them illegible.**
`src/app/(dashboard)/invoices/[id]/invoice-detail-client.tsx:51` (PAID
badge), `src/app/(dashboard)/settings/settings-client.tsx:216`
("Registered"), `src/app/(dashboard)/settings/components/invoicenow-settings-card.tsx:106`
("Configured"). Pre-P17 `bg-success` compiled to nothing (white text on
the dark card — readable by accident); post-P17 it compiles to `#00FF94`
and white-on-neon-green is **1.33:1** (WCAG AA needs 4.5:1). The sibling
implementations do it right (`match-suggestions.tsx:30`,
`reconcile-form.tsx:55`: `bg-success text-void` = 15.27:1). The
`bg-success` Button at invoice-detail:318 inherits `text-void` from the
default variant and is fine.

**DOC-H1 — DEPLOYMENT.md §4's schema-verification count is wrong for a
fresh host: the guide promises 40; a fresh v1.2.1 load yields 30.**
`docs/DEPLOYMENT.md:157-163` (repeated at `worklog.md:794`). The §4 query
counts the seven domain schemas; a fresh load carries exactly 29 domain
tables + 1 view (`audit.org_event_log`) = **30**. The "40" was measured on
`test_ledgersg_dev`, whose `core` schema carries 10 legacy
`manage.py migrate` leftovers (`django_session`, `django_admin_log`,
`auth_group*`, 6× `django_celery_beat_*`); §15c's 3 tables + the 2
token-blacklist tables live in `public` and are not counted by the query.
A fresh-host deployer following §4 step-by-step sees 30 where the guide
promises 40 and concludes the load failed.

### Medium (backend)

**BE-M1 — BE-H3 task-body coverage is 2-of-5: the three remaining Peppol
task bodies lack `tenant_context` and are dead-on-arrival on real workers.**
`apps/peppol/tasks.py:110` (`retry_failed_transmission_task`),
`:180` (`check_transmission_status_task`), `:251`
(`cleanup_old_transmission_logs_task`) — only
`transmit_peppol_invoice_task` (:65) and the invoicing email task wrap in
`tenant_context`. The live policy check: `gst.peppol_transmission_log`
policies are strict `org_id = core.current_org_id()` on all four commands
(no NULL-context escape), so on a real worker with a NULL GUC the retry
task sees 0 rows and retries to death, the status check returns `None`
silently, the cleanup deletes 0 rows. Latent today (no view dispatches
them) — dead the moment the manual-retry feature is wired.

**BE-M2 — `unallocate()` and `unreconcile()` take no locks: lost-update
races against the locked `allocate()`/`void()`/`reconcile()`.**
`apps/banking/services/payment_service.py:624-672` (plain read →
`allocation.delete()` → recompute → `document.save()`; compare `allocate()`
:439/:469 which locks payment and documents) and
`apps/banking/services/reconciliation_service.py:359-388` (`unreconcile` —
bulk update, no locks). Concurrent locked-allocate + unlocked-unallocate
on the same document → `amount_paid`/`status` computed from stale
allocation sets — the P5/H-1 invariant "the allocations table is the
truth" is silently violated.

**BE-M3 — manual journal lines can post to header and archived accounts —
ledger/TB divergence.**
`apps/journal/services/journal_service.py:242-250` — existence+org check
only. The schema documents the intent (`database_schema.sql:597`:
"is_header … cannot post to directly"); `get_trial_balance` filters
`is_active=True` (:568), so lines posted to an archived account vanish
from the TB while remaining in the ledger. No DB CHECK enforces either
rule. Also the `archive_account` balance check (`apps/coa/services.py:351`)
is unlocked (a concurrent posting can slip in before `is_active=False`).

**BE-M4 — `convert_quote_to_invoice` TOCTOU: concurrent converts create
two invoices from one quote.**
`apps/invoicing/services/document_service.py:521-566` — status check
outside the lock (there is no lock); two concurrent POSTs both pass the
gate → two live invoices + double journal postings once both are approved.

**BE-M5 — `add_line` line-number race → `uq_docline_doc_lineno`
IntegrityError → untyped 500.**
`apps/invoicing/services/document_service.py:321-322`
(`order_by("-line_number").first()` — read-then-write, no lock); the loser
of two concurrent line adds on the same DRAFT hits the UNIQUE constraint
(`database_schema.sql:1134`) and 500s — the exact class the P17
400-contract sweep exists to eliminate.

**BE-M6 — the credit-note cumulative-cap check is an unlocked TOCTOU.**
`apps/invoicing/services/document_service.py:684-714` —
`_validate_credit_note_reference` sums existing credits with no lock on
the original document; two concurrent credit notes each see the same
headroom and jointly exceed `original.total_incl` — P14/H-4's cap can be
defeated by racing.

**BE-M7 — the production-only `on_commit` branch of `queue_task` has zero
test coverage.**
`common/tenant_context.py:79` — `transaction.on_commit(lambda:
task.delay(...))`. Every test runs eager (immediate `.delay`); a regression
in the deferral (dispatch despite rollback, dropped kwargs) would be
invisible to the 882-test suite. The core of BE-H3 is the branch that only
executes in production.

### Medium (frontend)

**FE-M1 — nested Escape: the org-menu's Escape also closes the mobile
drawer and strands focus on an invisible element.**
`src/components/layout/shell.tsx:105-111` (drawer keydown) and `:184-189`
(menu keydown) — both attach document-level listeners with no mutual
guard. With the drawer open + the org menu open (the selector lives in
the sidebar footer, :330), one Escape fires **both** handlers: drawer
closes, menu closes, focus is returned to `orgTriggerRef` — now inside
`invisible -translate-x-full`. WCAG 2.4.3/2.4.7 — the exact concern the
P13/H-2 closed-drawer state was built to prevent.

**FE-M2 — `bg-alert text-white` fails AA at 3.64:1 in three surfaces.**
`src/components/ui/badge.tsx:15` (destructive), `src/components/ui/button.tsx:22`
(destructive), `src/app/(dashboard)/invoices/invoices-client.tsx:36`
(OVERDUE). Void-on-alert = 5.60:1 passes; the design system's established
convention is dark text on bright backgrounds (`text-void` on
accent-primary/secondary everywhere).

**FE-M3 — `--color-text-muted #666666` fails AA (3.55:1 on void) for the
informational strings it colours; the globals.css header claims
"WCAG AAA Contrast".**
`src/app/globals.css:40` + header line 6. Consumers: shell helper labels,
org-selector trigger, user email, contact emails (all 12–14px
informational text). #8A8A8A restores ≈5.9:1. The header's AAA claim is
inaccurate (several token pairs are AA-only) — correct the claim to AA.

**FE-M4 — the "shared uenSchema" is not actually shared: only the regex
is; the invoice customer field lacks the normalization the other two
forms and the backend apply.**
`src/shared/schemas/uen.ts:17-29` exports `uenSchema`/`optionalUenSchema`
consumed **only by the test file**; production code imports `uenRegex` and
hand-rolls the rest (`new-organisation-client.tsx:80`,
`src/shared/schemas/invoice.ts:60-64` with no trim/uppercase). A lowercase
`t08ll1234a` passes the org form and the backend (which normalizes) but
is rejected by the invoice customer schema. The error-message string is
duplicated verbatim in two places (drift risk).

### Medium (cross-cutting / docs)

**DOC-M1 — no `collectstatic` step anywhere, while production storage is
now manifest-bound.** P17/BE-L4 switched production to
`CompressedManifestStaticFilesStorage` — the documented production boot
never runs `python manage.py collectstatic` (zero mentions across
DEPLOYMENT/README/Dockerfile/compose). On a fresh host, production HTML
surfaces (browsable API, `/admin/` under `ENABLE_ADMIN`) 500 with
"Missing staticfiles manifest entry".

**DOC-M2 — the API guide documents a nonexistent URL for the P17 UEN
contract.** `API_CLI_Usage_Guide.md:118` says
`PATCH /api/v1/organisations/{id}/` — live: 404. The org detail view is
mounted at the org-scoped root: `PATCH /api/v1/{org_id}/`.

**DOC-M3 — double-reversal status drift: SKILL/CLAUDE/README say "409"/
"409-class"; the code returns a typed 400.**
`journal_service.py:432` raises `ValidationError` →
`common/exceptions.py:26` maps it to 400; `test_journal_workflow.py:340`
asserts 400. The API guide is the only doc that gets it right.

**DOC-M4 — README tech-stack tables carry pre-P15 versions contradicting
the same README.** `README.md:672` (Next 16.1.6), `:680` (zod 4.3.6),
`:686` (Django 6.0.2), `:687` (DRF 3.16.1), `:691` (WeasyPrint 68.1) vs
the actual pins (16.4.6 / 4.6.7 / 6.0.10 / 3.18.3 / 70.0) the README's own
badges carry.

**DOC-M5 — the README Key Files table lists the deleted
`apps/web/middleware.ts`** (`README.md:662`) — the CSP owner is
`src/proxy.ts` + `src/lib/csp.ts` since P16/FE-C1.

**DOC-M6 — the README claims Redis is "optional for development" — it is
a hard prerequisite** (the tenant-membership cache backs every
org-scoped request; `base.py:320-325`; DEPLOYMENT §5 documents the
500-without-Redis failure).

**DOC-M7 — `ENABLE_ADMIN` (the P17 /admin/ gate knob) is documented
nowhere and the "16 settings-read vars, all listed" claim is off by one**
(17 with `ENABLE_ADMIN`; missing from both `.env.example`s).

**DOC-M8 — two divergent, cross-undocumented Docker paths** — README's
root `docker/Dockerfile` builds from GitHub HEAD inside the build (not
the local tree); DEPLOYMENT's compose is backend-only. Label/cross-ref
them.

**DOC-M9 — the fresh-host PG path is hardcoded to the sandbox prefix
`/home/z/my-project`** (`docs/setup_pg_z.sh:8-11`, DEPLOYMENT §3/§12.3) —
parametrize with a `$PG_BASE` override so the documented-and-verified
method works verbatim on any host.

### Low (selected; full register in the audits and the report)

- **BE-L1** — §15c omits `django_session`/`django_admin_log`, so the
  `ENABLE_ADMIN` opt-in added in P17 breaks on a schema-only host; the
  `django_celery_beat_*` tables are absent while `DatabaseScheduler` is
  configured (latent). → complete §15c (v1.2.2, additive, idempotent).
- **BE-L2** — `suggest-matches` route left `<str>` while every sibling
  got `<uuid>` (`apps/banking/urls.py:80`) — same client error, different
  status (400 vs 404).
- **BE-L3** — org-deleted-mid-flight: tasks retry-to-death
  (`DoesNotExist` is a permanent error treated as transient,
  `apps/invoicing/tasks.py:38-43`).
- **BE-L5** — the email send path lacks the status/type gate its
  InvoiceNow sibling carries (`document_service.py:1005` vs `:1093`) — a
  VOID/DRAFT document can be emailed as a rendered tax invoice.
- **BE-L6** — `_validated_exchange_rate` doesn't catch `InvalidOperation`
  at the service seam (`payment_service.py:289`) — defense-in-depth gap.
- **BE-L4** — `create_return_periods` dedup TOCTOU → IntegrityError 500.
- **FE-L1** — the `tailwindcss-animate` utility family compiles to nothing
  in v4 (no v4-native replacement installed): `animate-in/out`,
  `fade-in-0/out-0/80`, `zoom-in-95/out-95`, `slide-in-from-*`,
  `slide-out-to-*` on `dialog.tsx`, `select.tsx`, `toast.tsx` — the Radix
  primitives lose their enter/exit animations silently. **This is a real
  Tailwind v4 class of bug** (the v3 plugin family silently dying in v4)
  — distinct from the mobile-nav question (settled: no bug).
- **FE-L3** — `hasUnsavedChanges` is never reset on successful submit
  (`invoice-form.tsx:135-141`) — benign today (guard unmounts on
  navigation), stale-`true` between unmount and next mount.
- **CFG-L1** — no CI job runs the 11 always-green no-backend e2e specs
  (CI stops at tsc+lint+vitest+build); the Playwright config itself is
  complete for its philosophy (serial-when-live, webServer reuse,
  chromium-default matrix).
- **CFG-L2** — the vitest coverage ratchet's header claims
  "Components 90% / Hooks 85%" but no per-glob floor is enforced for
  hooks (5 of 13 hooks measure 0–20%); `src/app/**`, `providers/**`,
  `stores/**` are wholesale-excluded. Add a measured hooks floor.
- **CFG-L3** — `@types/uuid ^10` paired with `uuid ^13` (major mismatch).
- **DOC-L1..L8** — §11 probe 308 vs 200 (`/login` needs `-L` or the
  trailing slash), CI header stale (860/P16 → 882/P17), PAD ghost entries
  (`middleware.ts`, `lib/server/`, Next 16.1.6), README tree `proxy.ts` at
  the wrong level, README venv `/opt/venv`, SKILL "NUMERIC since v1.2.0"
  (was v1.1.0/§16), API-guide double-reversal test attribution, Makefile
  `make test` missing the canonical flags.

## 3. The execution plan (TDD; each item RED → GREEN → targeted suite)

### Phase 1 — backend: statutory-record locking & the concurrency completion

| # | Task | Fix (files) | Tests (RED first) |
|---|------|-------------|-------------------|
| 1 | BE-H1 | `generate_f5` + `review_return`: wrap in `transaction.atomic()`, `select_for_update()` the return row, re-check status post-lock (mirror `file_return`) | `tests/integration/test_concurrency_contracts_p18.py`: file-then-recalculate race simulation → 400 + FILED intact; review-after-file refused |
| 2 | BE-M2 | `unallocate()`: lock payment + document rows (same lock order as `allocate`); `unreconcile()`: lock the transaction + payment (order: txn → payment, matching `reconcile`) | same file: interleaved allocate/unallocate keeps `amount_paid` consistent; unreconcile-after-reconcile keeps flags consistent |
| 3 | BE-M4 | `convert_quote_to_invoice`: `select_for_update` the quote + post-lock status re-check | double-convert refused 400; single convert unchanged |
| 4 | BE-M5 | `add_line`/`remove_line`: lock the document for the line-number read+insert; catch the residual `IntegrityError` → typed 400 | concurrent line-number collision → 400 not 500 |
| 5 | BE-M6 | `_validate_credit_note_reference`: lock the original document row for the cap read | racing credit notes refused when jointly exceeding the cap |
| 6 | BE-M3 | `create_entry` line loop: reject `is_header` and `not is_active` accounts (typed 400); `archive_account`: lock + re-check balance | posting to a header account → 400; archived → 400; TB/ledger consistency preserved |
| 7 | BE-M1 | Wrap the three Peppol task bodies in `tenant_context` (org resolved from the log row / task arg); `cleanup_old_transmission_logs_task` gets an explicit per-org dispatch contract | task-body GUC tests (mirror the P17 BE-H3 pattern); RLS-enforced probe for the retry task as `ledgersg_app` |
| 8 | BE-M7 | (test-only) `queue_task` under `CELERY_TASK_ALWAYS_EAGER=False` + `captureOnCommitCallbacks`: `.delay` fired only after commit; **not** fired on rollback | the new coverage test itself |
| 9 | BE-L2 | `apps/banking/urls.py:80` `<str:transaction_id>` → `<uuid:transaction_id>` | malformed id → 404 (route-level) |
| 10 | BE-L3 | `DoesNotExist`/`ResourceNotFound` → terminal (log + return, no retry) in both task bodies | org-deleted-mid-flight test: no retry, terminal result |
| 11 | BE-L5 | `send_email`: gate to APPROVED SALES_INVOICE (mirror `send_invoicenow`) | VOID/DRAFT email → 400 |
| 12 | BE-L6 | `_validated_exchange_rate`: catch `InvalidOperation`/`TypeError`/`ValueError` → `ValidationError` | garbage-string service call → 400 not 500 |
| 13 | BE-L4 | `create_return_periods`: catch the UNIQUE violation → typed skip/400 | concurrent duplicate period creation → clean refusal |

### Phase 2 — schema (SQL-First, additive): §15c completion → v1.2.2

| # | Task | Fix |
|---|------|------|
| 14 | BE-L1 | Add `django_session` + `django_admin_log` to §15c (idempotent `CREATE TABLE IF NOT EXISTS`, grants for `ledgersg_app`/`ledgersg_owner`); document the `django_celery_beat_*` decision (no beat in the documented runtime — the tables stay a documented opt-in note); bump the header + `§15c` history to **v1.2.2**; reload both local DBs; §13 upgrade ladder updated |

### Phase 3 — frontend: the contrast debt, the real Tailwind v4 fix, the escape nesting

| # | Task | Fix (files) | Tests (RED first) |
|---|------|-------------|-------------------|
| 15 | FE-H1 | the three `bg-success text-white` → `bg-success text-void` (invoice-detail PAID badge, settings Registered, InvoiceNow Configured) | a pairing regression test: every `bg-success`/`bg-alert` usage in `src/` pairs with an approved foreground (`text-void`/`text-carbon`) — enumerates files, fails on any `text-white` pairing |
| 16 | FE-M2 | `badge.tsx` + `button.tsx` destructive + invoices-client OVERDUE: `text-white` → `text-void`, hover `bg-red-700` → `bg-alert/90` (stays in the token system) | covered by the same pairing test |
| 17 | FE-M3 | `--color-text-muted: #666666` → `#8A8A8A`; header claim "WCAG AAA Contrast" → "WCAG AA+ (token pairs verified ≥4.5:1)" | a token-contrast unit test: computes WCAG ratios for the token pairs the components actually pair (text-primary/secondary/muted × void/carbon/surface; void × success/alert/primary/secondary) and asserts ≥4.5:1 |
| 18 | FE-M1 | the drawer's Escape handler skips while `orgSelectorOpen` (the menu consumes the first Escape; the drawer closes on the second) | nested-state test: drawer+menu open → one Escape closes only the menu (focus returns to the trigger, still visible); second Escape closes the drawer |
| 19 | FE-M4 | `invoice.ts` customer.uen → `optionalUenSchema` (normalizing); `new-organisation-client.tsx` → `uenSchema.safeParse` (one error message source); bank-account PayNow keeps `uenSchema` via the shared module | lowercase-UEN acceptance parity test across all three schemas |
| 20 | FE-L1 | `npm install tw-animate-css@1.4.0` (v4-native, pure CSS) + `@import "tw-animate-css";` in globals.css — the `animate-in`/`fade-in-0`/`zoom-in-95`/`slide-in-*` families compile again; Radix dialog/select/toast animations restored | design-token test extended: the animate utility classes referenced by `dialog.tsx`/`select.tsx`/`toast.tsx` exist in the compiled CSS (build the CSS via the repo's own postcss pipeline, as the audit did) |
| 21 | FE-L3 | `onSubmit` success: `setHasUnsavedChanges(false)` before `onSuccess` | the guard-hook test extended: submit success clears the store flag |

### Phase 4 — configs (the user's named ask: strengthen the existing suites)

| # | Task | Fix |
|---|------|------|
| 22 | CFG-L1 | `.github/workflows/ci.yml`: new `e2e` job — chromium-only Playwright install + `npx playwright test --grep` the 11 no-backend specs (the always-green set), no backend service needed |
| 23 | CFG-L2 | `vitest.config.ts`: measure the current `src/hooks/**` coverage, add the per-glob floor at the measured value (honest ratchet — prevents regression without faking the header's aspirational 85%) |
| 24 | CFG-L3 | `npm install -D @types/uuid@^13` (align the major; API surface used is stable) |

### Phase 5 — docs truth pass & the fresh-host deploy guide

| # | Task | Fix |
|---|------|------|
| 25 | DOC-H1 | DEPLOYMENT.md §4: expected count 30 (fresh v1.2.2 domain-schema load) + the public-schema note + the dev-vs-migrated-test-DB one-liner; `worklog.md` P17 entry corrected in passing |
| 26 | DOC-M1 | DEPLOYMENT.md §8/§12: `collectstatic --noinput` before the production gunicorn boot (+ LOG_DIR mkdir noted); `apps/backend/Dockerfile` gains the step (with the dummy-key/settings env) |
| 27 | DOC-M9 | `docs/setup_pg_z.sh`: `PG_BASE="${PG_BASE:-/home/z/my-project/pg}"` parametrization (default unchanged — the sandbox path keeps working verbatim); DEPLOYMENT §3/§12.3 note the override |
| 28 | DOC-M2/M3/L7 | API guide: org PATCH URL fixed; double-reversal attribution fixed; SKILL/CLAUDE/README "409-class" → "typed 400" |
| 29 | DOC-M4..M8 | README: tech-stack table refreshed to the real pins; Key Files `middleware.ts` → `src/proxy.ts` + `src/lib/csp.ts`; Redis "required"; Docker section cross-referenced + the GitHub-HEAD caveat labelled; `ENABLE_ADMIN` documented; counts 16→17 |
| 30 | DOC-M7 | `apps/backend/.env.example` + root `.env.example`: add `ENABLE_ADMIN` with the dev/prod default note (the "working .env.example that matches the codebase" ask — audit the full var list once more) |
| 31 | DOC-L1..L8 | §11 `/login/` + `-L`; CI header 882/2026-11-27; PAD ghost entries fixed (`src/proxy.ts`, `lib/server/` removed, 16.4.6); README tree + venv path; SKILL §16/v1.1.0; Makefile canonical flags |
| 32 | DEPLOYMENT.md | the fresh-host step-by-step completeness pass (the user's named ask): verify §1–§15 as a from-`git clone` path with the audit's gap list closed (prereqs incl. `python3-venv`/Node 20/Redis 7-8, `PG_BASE` note, playwright `--with-deps` note for the e2e gates, collectstatic, ENABLE_ADMIN, the two Docker paths cross-referenced) |

### Phase 6 — live gates, screenshots, deliverables

| # | Task |
|---|------|
| 33 | Full gate re-run: pytest (incl. the new P18 tests), vitest, tsc, eslint, `build:server`, e2e default + `e2e:full` on the live stack, `rls_smoke` 13/13 as `ledgersg_app`, mobile-nav 17/17, prod-CSP smoke 5/5 |
| 34 | Screenshots: `scripts/capture-screenshots-session36.js` — 8 DOM-verified, md5-unique captures under `docs/screenshots/` (`104-111_*_session36.png`), including the P18 surfaces: the contrast-fixed PAID badge (`bg-success text-void`), the settings/InvoiceNow cards, the animate-restored dialog open state |
| 35 | `docs/REMEDIATION_2026-11-27_P18_REPORT.md` (the P17-report convention), `docs/session_36.md`, the `worklog.md` entry |
| 36 | Conventional commits on `main`; push via `docs/ssh_git_wrapper_v3.py`; remote-ref verification |

## 4. Validation checkpoints (before execution)

1. Every finding above hand-verified against the tree by the lead (BE-H1,
   FE-H1, FE-M1, FE-M4, BE-M1 sighted in source this session; the
   contrast ratios computed independently).
2. The plan's file anchors re-checked at execution time (each Phase-1/3
   item opens with reading the current file in full).
3. Post-fix: the full gate matrix of Phase 6 must be green before any
   commit; the mobile-nav probe must stay 17/17 (the FE-M1/FE-L1 changes
   touch the shell and the primitives — regression risk to the settled
   verdict is nonzero and must be re-settled).
4. The pairing/contrast/token unit tests become permanent regression
   walls (the class FE-H1 slipped through — a token test that never
   checked the pairings).

## 5. Deferred register (carried forward, not dropped)

The full P16/P17 register carries forward (ContactPicker WAI-ARIA
combobox, in-app unsaved-work route guard, backend list pagination, the
audit-log `INSERT WITH CHECK (TRUE)` surface, the ruff ~1216 mechanical
register, UEN checksum, the H-3 DB-trigger layer, H-05b attachment model,
CSV size cap/dedup (BE-L5 full), CSP report-endpoint bound, positive
membership-cache invalidation design, journal serializer tolerance
alignment, `lines max_length`, `display_money` finite-gate consistency,
email-restore lifecycle evidence). New deferrals from this session's
audits: the PaymentsTab same-route prefill re-trigger (no current
producer), the list-envelope `{data}`/`{results}` unification, the NULL-
context SELECT policies on `core.user_organisation`/`core.role`
(documented tradeoff), the org-mid-flight dead-letter design beyond the
terminal classification, the remaining 5 eslint parity warnings.
