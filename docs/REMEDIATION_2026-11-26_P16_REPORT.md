# LedgerSG — Remediation Report (P16 Sprint: Production Truth — CSP Hydration, the Service-Path Middleware & the Deferred-Contract Sweep)

**Date:** 2026-11-26 (session 32)
**Base commit:** `d7f7d9b7` (main — post-P15, all gates green)
**Plan:** `docs/REMEDIATION_PLAN_2026-11-26_P16.md` (validated against the codebase before execution)
**Source inputs:** three parallel deep audits run this session (backend P15-diff + surrounding services; frontend api-client/shell/hooks/configs; cross-cutting status-claims/deployment/env truth) with lead hand-verification of every Critical/High finding in source and build artifacts, plus the live baselines reproduced at sprint start (834P/0F/5S · tsc 0 · vitest 532/532 · eslint 9 · mobile-nav 17/17).
**Method:** TDD (RED → GREEN → full gate) for every behavioural fix; lint parity on touched files (whole-tree 9 findings before = 9 after); conventional commits on `main`; `skills/` excluded from all checks/tests/compilation; no schema DDL this sprint (every fix is application-layer).

---

## 1. Verification Ledger (executed evidence)

| Gate | Result |
|---|---|
| Backend `pytest --reuse-db --no-migrations -q` | **860 passed, 0 failed, 5 skipped** (865 collected; 834 baseline + 26 new P16 tests) |
| `pytest tests/invariants -q` | **34 passed** |
| `pytest tests/security -q` | **76 passed, 3 skipped** (incl. the new middleware-presence settings gates) |
| `manage.py check` (testing settings) | 0 errors (the documented W001 only) |
| Frontend `npx tsc --noEmit` | 0 errors |
| Frontend `npx vitest run` | **554/554 passed** (64 files; 532 baseline + 22 new tests) |
| `npm run test:coverage` | green at both ratchets |
| `npx eslint src` | **9 findings** — exact parity with the pre-sprint register (the new code added zero) |
| `npm run build:server` | green (Next 16.4.6, all routes dynamic + the proxy registered) |
| **NEW — the production-CSP smoke** (`scripts/prod-csp-smoke.js`) | **5/5**: the served CSP carries a per-request nonce (`script-src 'self' 'nonce-…' 'strict-dynamic'`), no unsafe-inline in production, **hydration happened** (`window.next` booted — the pre-P16 production build could NOT hydrate), zero CSP-violation console errors, the app shell rendered |
| `npm run test:e2e` (no backend) | 11 passed + 29 gated with reasons (40 specs) |
| `npm run test:e2e:full` (live stack) | **40 passed, 0 failed, 0 skipped** |
| The runtime-role gate (`scripts/rls_smoke.py --base :8001` as `ledgersg_app`) | **13/13 steps green** (register → org 201 → contact → invoice → approve under RLS → bank account → payment+allocation → F5 create+compute) |
| Mobile-nav live probe (`scripts/mobile-nav-audit.js`) | **17/17 at 375/800/1280** — toggle, closed-drawer `visibility:hidden`, overlay, X hit-target, transition-aware close, no overflow, no console errors, sticky tablet/desktop, the v4 space-y trap sweep clean. **The navigation works; no TailwindCSS v4 bug exists** (settled live on the P16 tree, consistent with P12/P13/P15) |
| Screenshots | 8 new (`docs/screenshots/88-95_*_session32.png`) — DOM-verified per surface (incl. the new `role="dialog"` truth on the open mobile nav), md5-unique |
| Ruff parity (touched files) | no new findings on the touched set |

## 2. What Was Done

### Phase 0 — the production-truth headline

| # | Finding | Fix | Evidence |
|---|---|---|---|
| FE-C1 (Critical) | The production CSP (`script-src 'self'`) blocked Next's non-nonced inline bootstrap scripts on every page — **the shipped production app could not hydrate**; the dev-mode suite structurally could not catch it | The nonce-based CSP: `src/lib/csp.ts` (the testable builder — production `'self' 'nonce-<n>' 'strict-dynamic'`, dev keeps the documented exemption set) + `src/proxy.ts` (per-request nonce on request AND response headers — the documented Next 16 mechanism) + `force-dynamic` in the root layout (nonces require dynamic rendering) + the CSP REMOVED from `next.config.ts` headers (single source of truth — the P13/H-1 lesson) + the smoke gate | 8 builder unit tests; the headers-config test updated to assert NO CSP in next.config (the second-source trap); **the smoke 5/5 on the real standalone build** |

### Phase 1 — backend contracts (every task RED → GREEN)

| # | Finding | Fix | Evidence |
|---|---|---|---|
| BE-H1 | `config/settings/service.py` (the Docker/script API entrypoint) rebuilt MIDDLEWARE from scratch, dropping TenantContextMiddleware + AuditContextMiddleware + CSP + WhiteNoise — the shipped container path would 403 every org-scoped request with RLS seeing NULL and no audit attribution | Derived from base (`list(_BASE_MIDDLEWARE)`); a settings gate asserts all four entries in EVERY HTTP-serving settings module (base/development/production/service) | 4 new settings-gate tests (the service test was RED) |
| BE-H2 | `BulkAllocationSerializer` (the `POST /payments/{id}/allocate/` wire) still demanded APPROVED-only — the P14 instalment fix missed it; a PARTIALLY_PAID invoice 400'd on the dedicated endpoint | Shares the module-level `ALLOCATABLE_STATUSES`; the dead `AllocationCreateSerializer` (same stale check, zero consumers) deleted | 4 endpoint-level tests (PARTIALLY_PAID instalment + SENT accepted — both RED first; DRAFT/VOID refusals as controls) |
| BE-M1 | The payment-amount cap was TOCTOU — the DOCUMENT rows were locked but never the PAYMENT row | `Payment.objects.select_for_update().get(...)` at the top of `allocate()` | the spy-probe test (RED first) |
| BE-M2 (+L1) | `NaN`/`Infinity` box overrides could be FILED into the statutory record (`Decimal("NaN")` parses cleanly; PG numeric accepts it) | `money()` rejects non-finite; the box-override seam validates `is_finite()` in BOTH the view and the service; the three FX `.quantize()` paths moved to `money()` (HALF_UP) | NaN/Infinity tests (RED first) at both seams |
| BE-M3 | `quantity × unit_price` could overflow NUMERIC(19,4) (the individual P14 bounds permit a 19-integer-digit product) → unhandled 500 | The line-total bound in `InvoiceLineCreateSerializer.validate` (`≤ 99999999999999.9999`) | the in-bounds-fields/out-of-bounds-product test (RED first) |
| BE-M4 | Payment create + allocate was two transactions — an allocation 400 left an orphaned payment + journal entry | `create_received_with_allocations` / `create_made_with_allocations` (one atomic service method; the views consume them) | the rollback test (RED first) + the happy-path control |
| BE-M5 | `InvoiceLineAddView` silently dropped `discount_pct` (the create path applied it) | Forwards the validated field | both-endpoints-parity test |
| BE-M6 | System tax-code rows: the service permitted description/is_active edits the RLS WITH CHECK refuses (InsufficientPrivilege 500 under the app role); `deactivate` already refused system rows | `update_tax_code` refuses system rows with the typed 400 (mirror of `deactivate`) | RED first |
| BE-L2 | Releasing the last allocation blanket-reset documents to APPROVED — an InvoiceNow-sent document lost its transmission state | Evidence-based restoration: `SENT` if `invoicenow_sent_at` else `APPROVED` (both the void and unallocate paths); the email-only residual is REGISTERED (needs a lifecycle evidence column) | 2 tests (the SENT case RED first; the APPROVED control) |
| BE-L3 | `file_return`/`amend_return` lacked row locks (concurrent file/amend interleave) | `select_for_update` in both | the spy-probe test (RED first) |
| BE-L4 | The CSV latin-1 fallback re-read a consumed stream (`b""`) — non-UTF-8 statements "successfully" imported 0 rows | Read the bytes once, decode utf-8 then latin-1 | the latin-1 import test (RED first) |
| BE-L5 | Duplicate payment audit rows (the trigger AND manual writes) | The manual CREATE/VOID writes removed (the trigger is the truth; ALLOCATE/UNALLOCATE events stay — `payment_allocation` has no trigger) | the exactly-one-CREATE-row test (with the trigger's INSERT→'CREATE' vocabulary documented) |
| BE-L7 | Org-create validated the normalized UEN but stored the raw value (case-sensitive UNIQUE dodge) | The normalized form is written back | RED first |
| BE-L8/L9 | The period_lock docstring overstated the payment-void wiring; the advertised payment-void lock test never existed; the payment-void reversal date was UTC (`timezone.now().date()`) | Docstring corrected (the transitive enforcement documented); the payment-void lock test WRITTEN (the fallback-date path — RED first: the missing sequence was the test-side lesson); `timezone.localdate()` | 5/5 period-lock tests green |

### Phase 2 — frontend contracts (vitest RED → GREEN)

| # | Finding | Fix | Evidence |
|---|---|---|---|
| FE-H1 | The dashboard query key was inverted (`["dashboard", orgId]`) — all 10 mutation→dashboard invalidations were silent no-ops; the correct hook had zero importers | The page consumes `useDashboardMetrics` (the orgId-first key); the dead inline `DashboardData` interface removed | the QueryCache-key test (RED first); 7/7 in the truth suite |
| FE-H2 | Org creation dead-ended: `switchOrg` read the PRE-creation org list from a stale closure and silently skipped the selection + invalidation + persist | The provider's new `selectOrgById` (no list-state read; switchOrg delegates); the create flow uses it | the select-without-list test (RED first); the p10 org-creation e2e green live |
| FE-H3 | The frontend UEN regex rejected the ACRA other-entities form (LLP `T08LL1234A` — accepted by the BACKEND and written by the repo's own e2e) | The shared schema mirrors the backend's three ACRA forms; the dead duplicate `isValidUEN` deleted | 6 format tests (the T/S forms RED first) |
| FE-M1 | Open redirect via `?redirect=` on login (CWE-601) | Same-app paths only (`/…`, not `//host`, not absolute URLs) | 4 tests (the attacker cases RED first) |
| FE-M2 | The mobile drawer's scroll lock persisted after resizing past md with no visible escape | The drawer closes at the breakpoint crossing (matchMedia listener, cleanup-correct) | the crossing test (RED first; the matchMedia-mocking lesson) |
| FE-L4/L5 | The focus trap matched only a[href]+button; the modal drawer had no dialog semantics | The full focusable selector + `role="dialog"` `aria-modal="true"` on the open drawer | the planted-input trap test + the dialog-semantics test (both RED first); 12/12 in the shell suite; the mobile-nav probe re-run 17/17 |
| FE-L1/L2/L3 | `allowedDevOrigins` missing; the dead-code cluster (`use-dashboard` hooks, `createQueryHooks`, `ClientOnly`, `isValidUEN`); the dead `[orgId,"peppol"]` invalidation key | All fixed/deleted/aligned | tsc 0; eslint parity 9; the full vitest suite green |
| FE-M4 | The e2e DB-safety contract lived only in the npm script's `--workers=1` | `fullyParallel: !liveBackend` + `workers: 1` when `E2E_API_URL` is set — encoded in `playwright.config.ts` | the live run green; the config is now self-documenting |
| FE-I-1 | The single-flight refresh's shared-FAILURE path was untested under concurrency | The 3-parallel-401s + failing-refresh test (all reject, exactly 1 refresh) | 3/3 in the single-flight suite |

### Phase 3 — the docs truth pass + hygiene

- Every stale claim from the cross-cutting audit fixed: CLAUDE.md (the header counts, the P16 milestone + status table 860/554), README (the badge 1454, the Test-Suites section, the five dep versions, Redis required, the clone URL, the env table `DB_*`, the middleware.ts file-map entries, the roadmap zombie, v0.3.4, 29+1 tables), ledgersg_SKILL (the tech-stack table, the test-workflow block 860/34/76/554, lessons 64–69, the P16 project_state), PAD (v3.11.0, the Key Metrics heading + counts, the P16 note), AGENTS (the status header + the P16 patterns section), ci.yml (860/P16), the API guide (the stale metrics block relabelled, the nonexistent `/gst/register/` path corrected, the P16 addendum, the four newly-documented endpoints).
- `docs/DEPLOYMENT.md`: the P16 revision header (with the smoke in the verified-gates list), 554 vitest, **the §17 application note for existing v1.1.0 databases** (the idempotent sed extraction verified against the schema file), the production-CSP smoke step in §9 + §13.
- `.env.example` (web): PLAYWRIGHT_BASE_URL + PLAYWRIGHT_PROJECTS documented; all three templates re-verified against the code.
- Hygiene: the 7 tracked log files + the 49 `backup/`+`plan/` files untracked (the .gitignore's declared intent; kept locally), `*_log.txt` ignored, the mislabeled `Current_Project_Status.md` archived with a SUPERSEDED banner (renamed `Current_Project_Status_2026-03-14_archived.md`).
- The ruff register's documented baseline corrected to the measured truth (1216 whole-backend / ~735 production findings, ~75% mechanical; house style remains touched-file parity).

## 3. The mobile navigation (the sprint's named focus — settled live, third time)

The 17/17 live probe re-ran on the FULLY REMEDIATED tree (after the shell.tsx edits for FE-M2/L4/L5): toggle visible+operable at 375px, the closed drawer `visibility:hidden` (out of the tab order), the open drawer visible with the overlay + a real X hit-target, the transition-aware close, no horizontal overflow, zero console errors, sticky at 800/1280, and the v4 space-y trap sweep clean (no `space-y-*` child in the nav carries explicit margins). The Tailwind v4 setup is CSS-first clean (`@import "tailwindcss"` + `@theme`, no legacy config). **Verdict: the mobile navigation works as designed; there is no TailwindCSS v4 bug.** The P16 changes IMPROVED it: the open drawer now exposes `role="dialog"` + `aria-modal`, the focus trap covers the full focusable set, and a resize past md releases the scroll lock (verified in the screenshot DOM truths + the shell suite).

## 4. Deferred Debt Register (explicit — nothing silently dropped)

- **The ContactPicker WAI-ARIA combobox pattern** (FE-M3 — arrow keys, `aria-activedescendant`, Escape; a real a11y gap, a UI project — the first item for the next sprint).
- **Email-sent documents restore to APPROVED** on allocation release (the lifecycle-evidence column is the schema-tier fix; the InvoiceNow case IS covered).
- Backend list pagination (BE-L6 — an API contract change), the audit-log INSERT `WITH CHECK (TRUE)` forgery surface + the tax-code policy row-capture note (schema hardening, pairs with M-7-full), the coverage-exclude blind spots (FE-L6), the ruff mechanical debt (~833 auto-fixable; register re-baselined honestly this sprint).
- Everything carried forward from the P15 register: the UEN checksum + F-form foreign UENs, the H-3 DB-trigger layer, the H-05b attachment model, audit1 M-2/M-3/M-6b/M-8/M-9/M-7-full; audit2 M-01..M-05/M-07/M-08; B-3/B-4/B-8/B-9/B-12/B-15..B-19; the frontend L-batch; the 9 eslint findings (unchanged policies); the ruff register.

## 5. How to Verify (reproduction commands)

```bash
# backend gate
cd apps/backend && source .venv/bin/activate
export DB_NAME=test_ledgersg_dev DB_USER=ledgersg DB_PASSWORD=ledgersg_secret_to_change \
       DB_HOST=127.0.0.1 DB_PORT=5432
pytest --reuse-db --no-migrations -q   # 860P/0F/5S
pytest tests/invariants -q             # 34P
pytest tests/security -q               # 76P/3S

# frontend gates
cd apps/web
npm run typecheck && npm test          # 0; 554/554
npm run test:coverage && npm run build:server

# THE NEW production gate (P16/FE-C1)
node ../../scripts/prod-csp-smoke.js   # 5/5 (from the repo root)

# e2e + the live gates
npm run test:e2e                       # 11P + 29 gated
E2E_API_URL=http://127.0.0.1:8000 E2E_DEMO_EMAIL=demo@ledgersg.sg \
  E2E_DEMO_PASSWORD=demo1234pass npm run test:e2e:full   # 40P/0F/0S

# the runtime-role gate + the mobile-nav probe
DB_USER=ledgersg_app DB_PASSWORD=CHANGE_ME_IN_PRODUCTION \
  python manage.py runserver 127.0.0.1:8001 --noreload   # (daemonized)
python ../../scripts/rls_smoke.py --base http://127.0.0.1:8001  # 13/13
NODE_PATH=apps/web/node_modules node scripts/mobile-nav-audit.js  # 17/17
```

## 6. Commits

Conventional commits on `main` (see `git log d7f7d9b7..HEAD`): the CSP nonce + smoke; the service-path middleware + settings gates; the allocation instalment contract; the payment-service batch (lock, atomicity, non-finite, rounding, status restoration, audit dedup, localdate); the backend contract batch (line bound, discount_pct, system tax codes, return locks, CSV, UEN normalization); the frontend contract batch (dashboard key, selectOrgById, UEN forms, redirect guard, shell hardening, dead code, e2e config); the docs truth pass + the screenshots + the capture script; this report + the session log + the worklog. Pushed via `docs/ssh_git_wrapper_v3.py --remote git@github.com:nordeim/ledgersg.git` with remote-ref verification.
