# LedgerSG — Remediation Report (P17 Sprint: Concurrency Truth, the 400-Contract Sweep & the Celery Tenant Context)

**Date:** 2026-11-27 (session 34 — executed across two context windows; the workspace, PG data, Redis, the double-forked dev stack and the saved plan all persisted across the outage, zero loss)
**Base commit:** `e9b2626d` (main — post-P16, all gates green)
**Plan:** `docs/REMEDIATION_PLAN_2026-11-27_P17.md` (validated against the codebase before execution)
**Source inputs:** three parallel deep audits run this session (backend concurrency/contracts; frontend tokens/hooks/shell/env; cross-cutting docs-truth) with lead hand-verification of every Critical/High finding in source, plus the live baselines reproduced on a **fresh clone** (backend 860P/0F/5S · invariants 34P · security 76P/3S · vitest 554/554 · tsc 0 · eslint 9 (src) · mobile-nav 17/17 · prod-CSP smoke 5/5 — PostgreSQL 17 + Redis 8 reinstalled rootless, both DBs schema-loaded, `ledgersg_app` at the documented dev password).
**Method:** TDD (RED → GREEN → full gate) for every behavioural fix; lint parity (whole-tree 0 errors / 5 warnings, the documented register); conventional commits on `main`; `skills/` excluded from all checks/tests/compilation; one additive schema section (§15c — v1.2.1), no other DDL.

---

## 1. Verification Ledger (executed evidence)

| Gate | Result |
|---|---|
| Backend `pytest --reuse-db --no-migrations -q` (as `DB_NAME=test_ledgersg_dev`) | **882 passed, 0 failed, 5 skipped** (887 collected; 860 baseline + 22 new P17 tests) |
| `pytest tests/invariants -q` | **34 passed** |
| `pytest tests/security -q` | **78 passed, 3 skipped** (76 baseline + the 2 new settings gates: `/admin/` off outside DEBUG, the `STORAGES` manifest backend) |
| `manage.py check` (development settings, live stack) | 0 errors (the documented W001 only) |
| Frontend `npx tsc --noEmit` | 0 errors |
| Frontend `npx vitest run` | **582/582 passed** (69 files; 554 baseline + 28 new tests) |
| `npx eslint .` (whole tree incl. `e2e/`) | **0 errors, 5 warnings** — the 6 P16-era errors cleared (3 set-state-in-effect, 2 immutability, 1 prefer-const), warnings at the documented parity |
| `npm run build:server` | green (Next 16.4.6 standalone + static copy) |
| `npm run test:e2e` (no backend) | 11 passed + 29 gated with reasons (40 specs) |
| `npm run test:e2e:full` (live stack) | **40 passed, 0 failed, 0 skipped** (second consecutive full run; the first run on the fresh DB self-bootstraps the demo substrate — one interaction failure, then 40/40) |
| The runtime-role gate (`scripts/rls_smoke.py --base :8001` as `ledgersg_app`) | **13/13 steps green** (register → org 201 → contact → invoice → approve under RLS → bank account → payment+allocation → F5 create+compute) |
| Mobile-nav live probe (`scripts/mobile-nav-audit.js`) | **17/17 at 375/800/1280** — toggle, closed-drawer `visibility:hidden`, overlay, X hit-target, transition-aware close, no overflow, no console errors, sticky tablet/desktop, the v4 space-y trap sweep clean. **The navigation works; no TailwindCSS v4 bug exists** (settled live on the P17 tree, consistent with P12/P13/P15/P16) |
| The production-CSP smoke (`scripts/prod-csp-smoke.js`) | **5/5** — nonce served, no unsafe-inline, hydration happened, zero violations, shell rendered |
| Screenshots | **8 new** (`docs/screenshots/96-103_*_session34.png`) — DOM-verified per surface (incl. the open org-selector menu: `role="menu"` + `menuitemradio` + `aria-expanded="true"` — the new P17 contract), md5-unique, non-blank pixel-verified; the Payments tab shows **2 live `text-success` elements** (the FE-M1 token — pre-P17 those classes compiled to no CSS) |
| CI | the `DATABASE_URL` no-op removed; **a lint gate added** (`npx eslint . --max-warnings 5`) so the error count can never drift silently again |
| Docs | every command in `docs/DEPLOYMENT.md` §1–§13 re-executed live this session (incl. the corrected §9 GST example `M9034567K` — 201 — and the rewritten §11 token/`ORG_ID`/Bearer flow — all six spot-checks return the documented codes) |

## 2. What Was Done

### Phase 0 — environment & baselines (fresh clone)

The workspace had been reset: the repo re-cloned, PostgreSQL 17 + Redis 8
installed rootless (`docs/setup_pg_z.sh` + `skills/rootless-postgresql/SKILL.md`),
both databases created and schema-loaded, `ledgersg_app` restored to the
documented dev default. **Every documented baseline reproduced green** before
any change — including the `eslint src` = 9 parity check (the 11-finding
whole-tree delta was the `e2e/` pair, resolved this sprint).

### The session_29 (P14) regression check — the user-named focus, settled via git history

`git log --follow` on `apps/banking/services/payment_service.py` and the
serializers confirms the P15 tree repair landed: the Payment model is intact
(the corrupted `2bcb43f0` overwrite was reverted in P15), the
`ALLOCATABLE_STATUSES` instalment contract is present in **both** the wire
serializer and the dedicated allocate endpoint (the P16 BE-H2 completion),
and no P14-era strand survived. The P16 header claims matched the tree —
no new regression found; the P17 concurrency guards then hardened exactly
these seams (double-void, double-allocate, double-reconcile).

### Phase 1 — backend concurrency & contract batch (each: RED test → GREEN fix → suite)

- **BE-H1** `journal_service.create_reversal` — `select_for_update` row lock
  + `is_reversed` re-check; a second reversal is refused (400). Pre-P17 two
  reversals posted the swap-side lines twice (every account misstated 2x
  while the trial balance stayed balanced).
- **BE-H2** `payment_service.void` — row lock + `is_voided` re-check post-lock
  (the TOCTOU closed); the single void unchanged.
- **BE-H3** — NEW `common/tenant_context.py`: a context manager that opens
  the RLS tenant GUC exactly like the middleware (`SET LOCAL` inside a
  transaction). The invoicing + peppol task bodies wrap in it; the three
  dispatch seams in `document_service.py` dispatch **on commit**; eager mode
  stays bit-identical. Real Celery workers no longer run unscoped.
- **BE-M1** typed GST box parse (`None`/dict/"garbage" → 400, NaN stays 400).
- **BE-M2** bulk-allocation `document_id` UUID validation (400 field error —
  pinned as a regression guard; DRF 3.18 already converted the raw case).
- **BE-M3** UEN normalize-then-validate on org PATCH (shared helper; the
  case-dodge UNIQUE collision refused).
- **BE-M6** tax-rate range on the tax-code update serializer (9 / -1 → 400).
- **BE-M5** reconcile double-match guard + payment/transaction locks (typed 400).
- **BE-L2** `<uuid:transaction_id>` converters on the two banking routes
  (malformed id → 404 at the routing layer, not a 500).
- **BE-L3** `/admin/` gated off outside DEBUG (settings-gate tested).
- **BE-L4** the Django 6 `STORAGES` dict migration (the legacy
  `STATICFILES_STORAGE` setting was a silent no-op; the WhiteNoise
  compressed-manifest storage is actually active now — settings-gate tested).
- **BE-L1** `exchange_rate` validated/stored at its true 6-dp wire precision
  (the `money()` 4-dp quantize no longer truncates FX rates; monetary
  products stay 4-dp).
- **BE-M7** `select_related` on the payments/documents/transactions list
  services — query-count gates pin the O(1) FK behavior.
- **BE-M4 interim** the tenant middleware stops caching negative membership
  lookups (a rejected request can no longer poison the org cache).
- **Schema §15c (v1.2.1)** — the Django framework tables, SQL-First
  (`CREATE TABLE IF NOT EXISTS`, idempotent). The fresh-host pytest gap:
  transactional test-class teardowns flush `django_session` /
  `django_admin_log` / `django_content_type`; on a schema-only v1.2.0
  database every transactional teardown errored. Schema header bumped to
  v1.2.1; both local DBs re-verified (40 tables in the seven domain
  schemas, 47 numeric(19,4) columns).

### Phase 2 — frontend contract batch (vitest RED → GREEN)

- **FE-M1** `--color-success: #00FF94` added to the `@theme` block — the 14
  dead `text-success`/`bg-success` usages across 10 files now compile
  (the PAID badge, reconcile forms, match scores, fiscal and InvoiceNow
  cards). Gated by `src/__tests__/design-tokens.test.ts`.
- **FE-M2** the 6 eslint errors cleared with real refactors (no rule
  weakening): the `mounted`-pattern trio moved to
  `useSyncExternalStore`/derive-during-render; the immutability test pair
  got a hoisted capture; `prefer-const` in `p11.spec.ts`. Whole tree:
  **0 errors / 5 warnings** (parity). CI lint gate added.
- **FE-M3** the proxy nonce-CSP orchestration is unit-gated (request CSP +
  `x-nonce` forwarding + response CSP + per-request rotation).
- **FE-M4** the unsaved-changes guard is wired: a `beforeunload` listener
  fires only while `hasUnsavedChanges` (the store's write side finally has
  a reader).
- **FE-L1** the four dead CSP origins dropped (fonts are self-hosted; the
  two API origins map to reserved env flags).
- **FE-L2** the `bg-background`/`text-foreground` dead utilities swept to
  real tokens in the three filter files + `alert.tsx`.
- **FE-L3** dead code deleted: `useComplianceAlerts`, `useCurrentOrg`
  (threw during render), the invoice-store's unconsumed fields and
  `createInvoiceLine` (the store now owns exactly the
  `hasUnsavedChanges` contract).
- **FE-L4** the org-selector is a real menu (the Radix contract): trigger
  `aria-haspopup`/`aria-expanded`/`aria-controls` (menu stays mounted so
  the id resolves), `menuitemradio` + `aria-checked`, Escape/outside-click
  close, arrow-key roving with wrap, focus lands on the current org, focus
  returns to the trigger.
- **FE-L5** the refresh-failure redirect carries `?redirect=<path>`.
- **FE-L6** a shared `uenSchema` (the full ACRA contract) reused by the
  invoice form, the bank-account PayNow field and the new-organisation form.

### Phase 3 — docs truth pass + hygiene (no code behavior)

- **`docs/DEPLOYMENT.md`** — the fresh-host guide re-verified end to end:
  the §9 GST example fixed (`M9034567K` — the old value failed the P15
  honest validator, reproduced live), §7 counts normalized (882/78/34), the
  §11 cookie-jar bug fixed (single jar + a `TOKEN`/`ORG_ID` export step +
  Bearer headers on the JWT-only probes — every probe re-executed live),
  §9 credit-note bootstrap documents `related_document_id`, §4/§13 carry
  the v1.2.1 §15c upgrade path, and the runner note (pytest is the runner;
  `DB_NAME=test_ledgersg_dev` overrides the dev `.env`).
- **`README.md`** — the badge (1454 → 1504), the status table, P16+P17
  milestone blocks, the test-metrics sections, the env-var tables (the
  `DATABASE_URL` claim replaced by the five `DB_*` vars; the reserved
  flags marked), the dead refs (`start_apps.sh`, `SECURITY_AUDIT.md`,
  `E2E_TEST_EXECUTION_SUMMARY.md`, `src/middleware.ts`), the dashboard
  endpoint in the diagram (`/reports/dashboard/metrics/`), the issues URL
  (`nordeim/ledgersg`), the footer.
- **`AGENTS.md` / `CLAUDE.md` / `Project_Architecture_Document.md` /
  `ledgersg_SKILL.md`** — status snapshots, counts, versions and the
  quick-reference cards normalized to the P17 truth; the SKILL's false
  "local `.env`s are git-tracked" claim inverted; the stale
  `p11_bootstrap.py` mirror noted as historical; PAD's
  `/home/project/Ledger-SG/` absolute path retired.
- **`API_CLI_Usage_Guide.md`** — the P17 addendum (every new 400 contract,
  the reversal/void/reconcile guard semantics, the on-commit dispatch +
  worker RLS note, the uuid route converters, the admin gate) + the
  version bump.
- **Hygiene** — the AGPL-3.0 `LICENSE` added (the README badge + pyproject
  claimed it; the link was dead), the ci.yml `DATABASE_URL` no-op removed
  + the lint gate added, `apps/backend/database_connection_status.txt`
  untracked, the three repo-root scripts got the self-resolving
  `@playwright/test` require (the `prod-csp-smoke.js` pattern), the root
  `.env.example`'s middleware note updated for the P16 proxy, and the
  `apps/web/.env.example` reader map corrected (`src/proxy.ts`).

### Phase 4 — the full verification gate + deliverables

All gates green (see §1). 8 screenshots. `docs/session_34.md`, this
report, and the worklog entry. Conventional commits on `main`, pushed via
the SSH wrapper with remote-ref verification.

## 3. The mobile navigation & the session_29 regression check (the sprint's named focuses — settled live)

**Mobile navigation: 17/17 live probe checks PASS on the P17 tree**
(375/800/1280: toggle, closed-drawer `visibility:hidden`, overlay, X
hit-target, transition-aware close, no overflow, no console errors, sticky
tablet/desktop, the v4 space-y trap sweep clean). **The navigation works;
no TailwindCSS v4 bug exists** — settled live for the fifth consecutive
sprint (P12 → P17), this time on a fresh clone AND the remediated tree.
The P17 work improved the shell further: the org-selector is now a
keyboard-operable menu, and the invoice form guards unsaved work.

**`payment.py` / serializer (session_29, P14 partial completion):**
git history confirms no surviving regression — the P15 tree repair
reverted the corrupted `2bcb43f0` overwrite, the P16 allocation-instalment
contract completed the wire/allocate pair, and the P17 guards close the
remaining mutation races on exactly those seams. The suite's 22 new
backend tests pin the contracts.

## 4. Deferred Debt Register (explicit — nothing silently dropped)

The full P16 register carries forward (ContactPicker WAI-ARIA combobox,
email-restore lifecycle-evidence column, backend list pagination, the
audit-log INSERT WITH CHECK forgery surface + tax-code row-capture note,
the ruff ~1216 mechanical register, UEN checksum pending the official ACRA
algorithm, H-3 DB-trigger layer, H-05b attachment model, B-3/B-4/B-8/B-9/
B-12/B-15..B-19, the P11/P12 L-batch) **plus this sprint's new**: BE-M4's
full invalidation design (needs the membership-management surface); the
in-app route navigation guard for unsaved invoice work (the `beforeunload`
guard covers tab-close/refresh; intercepting Next client-side navigation
needs a router-level guard); BE-L5 (CSV size cap / bulk dedup); the CSP
report-endpoint log bound; `display_money`/`round_half_up` finite-gate
consistency; journal serializer tolerance alignment; lines `max_length`;
`get_allocations` org-filter defense-in-depth; the 5 remaining eslint
warnings (documented register).

## 5. How to Verify (reproduction commands)

```bash
# Backend (test_ledgersg_dev at schema v1.2.1 — §4 of DEPLOYMENT.md)
cd apps/backend
export DB_NAME=test_ledgersg_dev DB_USER=ledgersg DB_PASSWORD=ledgersg_secret_to_change \
       DB_HOST=127.0.0.1 DB_PORT=5432
pytest --reuse-db --no-migrations -q      # 882 passed, 5 skipped
pytest tests/invariants -q                # 34 passed
pytest tests/security -q                  # 78 passed, 3 skipped

# Frontend
cd ../web
npx tsc --noEmit                          # 0 errors
npx vitest run                            # 582/582 (69 files)
npx eslint .                              # 0 errors, 5 warnings
npm run build:server                      # green
npx playwright test --project=chromium    # 11 passed + 29 gated (no backend)

# Live stack (backend :8000 + frontend :3000 + Redis + the §9 demo bootstrap)
E2E_API_URL=http://127.0.0.1:8000 E2E_DEMO_EMAIL=demo@ledgersg.sg \
E2E_DEMO_PASSWORD=demo1234pass npx playwright test --project=chromium   # 40/40

# The runtime-role gate (second backend as ledgersg_app, §12.3)
DB_NAME=ledgersg_dev DB_USER=ledgersg_app DB_PASSWORD=CHANGE_ME_IN_PRODUCTION \
DB_HOST=127.0.0.1 DB_PORT=5432 DJANGO_SETTINGS_MODULE=config.settings.development \
  python manage.py runserver 127.0.0.1:8001 --noreload &
python ../../scripts/rls_smoke.py --base http://127.0.0.1:8001   # 13/13

# The named-focus probes
node scripts/mobile-nav-audit.js           # 17/17
node scripts/prod-csp-smoke.js             # 5/5 (after build:server)
node scripts/capture-screenshots-session34.js  # 8 DOM-verified shots
```

## 6. Commits

Conventional commits on `main` (see `git log e9b2626d..HEAD`): the P17
plan; the concurrency guards (reversal/void/reconcile); the Celery tenant
context + on-commit dispatch; the 400-contract sweep; the settings gates
(admin/STORAGES) + the schema §15c v1.2.1 bump; the N+1 fixes + the
negative-cache fix; the frontend contract batch (token, guard, menu,
schema, lint-zero, CSP origins); the CI lint gate + the DATABASE_URL
removal; the LICENSE; the docs truth pass (DEPLOYMENT/README/AGENTS/
CLAUDE/PAD/SKILL/API guide) + the root `.env.example`; the screenshots +
the capture script; this report + the session log + the worklog. Pushed
via `docs/ssh_git_wrapper_v3.py --remote git@github.com:nordeim/ledgersg.git`
with remote-ref verification and key shredding.
