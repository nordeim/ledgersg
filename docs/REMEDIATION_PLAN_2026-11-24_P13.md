# LedgerSG — Remediation Plan (P13 Sprint: Transactional Truth, Header Consolidation & the Typed Suite)

**Date:** 2026-11-24 (session 27)
**Base commit:** `69f13325` (main — post-P12)
**Source audit:** the post-P12 audit executed LIVE this session (not just in
source): all baselines reproduced first (backend 735P/0F/5S; tsc 0; vitest
518/518; eslint 45; e2e default 11P + 26 gated; **live e2e:full 37P/0F/0S** —
the P12-era data-conditional skip now passes with data present), then the
sprint's focus — the mobile navigation menu and a possible TailwindCSS v4
bug — re-verified live with Playwright at 375×812 / 800×1024 / 1280×800 plus
an @layer-aware matched-rule trace, and the documented v4 trap classes
(`docs/Tailwind-V4-Validation-Report.md` trap log: space-y selector rewrite,
shadow-scale shift, bare-HSL theme, oklab gradients) swept across `src`.
Three parallel deep-audit agents (frontend / backend / docs-drift) + lead
hand-verification of every Critical/High finding, using the repo skills'
taxonomies (`skills/nextjs16-tailwind4`, `skills/tailwind-patterns`,
`skills/agent-browser`-equivalent live probing, `skills/tdd`,
`skills/code-review-checklist`, `skills/lint-and-validate`,
`skills/rootless-postgresql`, `skills/how-to-git-push-using-ssh-wrapper`).
**Method for execution:** TDD (RED → GREEN → full gate), lint parity on
touched files, conventional commits on `main`, `skills/` excluded from all
checks/tests/compilation.

---

## 1. Sprint audit verdicts (what was verified live this session)

### The mobile navigation menu — WORKS as expected (re-confirmed post-P12)

Toggle renders and is keyboard-operable at 375 (36×36, Enter opens, focus
moves in, body scroll locks); the sidebar opens (`translate:0px`) and closes
(`translate:-100%`); the overlay renders `fixed z-40` and click-closes;
Escape closes with focus returning to the trigger; the Tab trap cycles
within the overlay; nav links navigate to the trailing-slash routes AND
auto-close; the tablet band (800) shows the sticky sidebar with the toggle
hidden; the desktop band (1280) pins the sidebar with `position:sticky`; no
horizontal overflow at 375; no console errors (the anonymous `/auth/me/` 401
is the documented evidence-gated probe; the recharts `width(-1)` warnings
are the registered A-7 mount noise). The P12/A-1 overlay floor is intact.

### The suspected TailwindCSS v4 bug — does not exist (settled with an @layer-aware rule trace)

The P12 matched-rule trace conclusion re-confirmed with a corrected
`@layer`-recursing walker (the P12-era probe predated Next 16's layer
emission): the only display rules matching the toggle are
`@layer(utilities) .inline-flex { display:inline-flex }` and
`@media((min-width: 48rem)) @layer(utilities) .md\:hidden { display:none }`;
the computed `display:flex` is correct CSS flex-item blockification. The v4
setup is clean (`@import "tailwindcss"` + `@theme`, hex palette — no
bare-HSL trap, no legacy config). The trap-log sweep: the nav's `space-y-1`
children carry **no explicit margins** (first link computed
`margin-block-end:4px; margin-top:0px` — the pure v4 model, no
double-margin violation); only 2 `shadow-sm` usages exist app-wide (a
v4-first app — the shadow-scale shift is by-design, not a port defect);
zero `bg-gradient-to-*` usages.

### Two REAL mobile-nav defects found beyond the P12 scope (fixed this sprint)

The mechanics work, but the audit found two genuine defects in the nav's
edge states: **H-2** the CLOSED off-canvas sidebar remains keyboard-focusable
(~10 invisible focusables before the header at mobile width — WCAG
2.4.3/2.4.7), and **M-1** the overlay (z-40) paints ABOVE the header (z-30),
so the "Close navigation" X toggle is blurred/unclickable while the menu is
open (pointer events land on the overlay; only its onClick-close masks the
bug). Both fixed with TDD (Tasks 11–12).

### Baselines reproduced (post-P12 state intact)

backend 735P/0F/5S · vitest 518/518 · typecheck 0 · eslint 45 (the
documented register) · e2e default 11P + 26 gated · **live e2e:full
37P/0F/0S (37 specs)** · PG (schema-qualified, 8 distinct `trg_audit_*`
triggers) · Redis alive (rebuilt from debs after the recycle; PG's
`usr/share` tree and empty cluster subdirs restored per
`skills/rootless-postgresql`).

---

## 2. Findings register

| ID | Sev | Location | Finding (evidence) |
|---|---|---|---|
| B-1 | **Critical** | `common/exceptions.py:199-208` | The custom DRF exception handler's fallback converts UNHANDLED exceptions into a normal `Response(500)` — DRF's dispatch accepts it, so neither Django's `ATOMIC_REQUESTS` wrapper nor the tenant middleware's request transaction observes an exception → **partial writes COMMIT** (runtime-reproduced). The C-04 contract ("unexpected exceptions MUST propagate") is defeated one layer above `wrap_response`. Live on non-atomic paths: `add_line`/`remove_line`/`_recalculate_totals`, `create_reversal`'s post-commit `original.save()`, `send_invoicenow`'s log creation, `transition_status`'s generic branch. |
| B-2 | **High** | `apps/gst/services/calculation_service.py:60-63` | GST per-line rounding quantum is one decimal place too fine: `Decimal(f"0.{('0'*rounding)}1")` with `rounding=2` yields **`0.001`**, not `0.01` (interpreter-verified: `100.05 × 0.09 → 9.005` persisted instead of the IRAS-mandated `9.00`). The docstring says 2dp. Suite never tripped it because fixtures use round amounts. Half-mil GST amounts flow to line rows, `gst_total`, journal GST postings and F5 boxes. |
| H-1 | **High** | `apps/web/src/middleware.ts` vs `next.config.ts` | Dual CSP/header definitions; the middleware's version wins (live-verified: served CSP contains `https://vercel.live`, `img-src … https:`, `vitals.vercel-insights.com`, and ships `'unsafe-eval' 'unsafe-inline'` unconditionally) — silently overriding the P11/M-15 env-aware hardening that gates those exemptions to dev only. Standalone server mode (the only production path since P10/M-12) runs middleware in production. |
| H-2 | **High** | `apps/web/src/components/layout/shell.tsx:154-161` | The CLOSED mobile sidebar (`-translate-x-full`) remains keyboard-focusable — transform does not remove from tab order. At mobile width, Tab lands on ~10 invisible focusables (logo, 8 nav links, logout) before the header toggle. WCAG 2.4.3/2.4.7. |
| M-1 | **Medium** | `shell.tsx:147` vs `:289` | Overlay `z-40` paints above the header `z-30`: while the menu is open, the X ("Close navigation") toggle is blurred under `bg-void/80 backdrop-blur-sm` and its pointer events land on the overlay. No current test can catch it (jsdom has no layout; the e2e never clicks the toggle while open). |
| M-3 | **Medium** | `apps/web/src/lib/api-client.ts:478-480` | `mutations: { retry: 1 }` re-fires every failed mutation once — including 4xx on non-idempotent POSTs (`/banking/payments/receive/`, `make/`, `allocate/`). A network timeout after the server processed a payment re-sends it. Queries have a 401/403 carve-out; mutations have none. |
| B-5 | Medium | `common/models.py:100,106` vs `common/exceptions.py:34-39` | `ImmutableModel.save()` raises a PLAIN `ImmutabilityError` (not the typed `LedgerSGException` 409 variant, which has zero raisers) → surfaces as 500 via B-1's fallback. Violates the C-04 typed-exception contract. |
| B-6 | Medium | 8 production sites | `date.today()` remains in production code (P11/L-3 claimed complete): `document_service.py:506-507` (quote-conversion issue/due dates — ledger-dated!), `gst/serializers.py:200` (F5 deadline days-remaining), `journal/views.py:208,246`, `invoicing/views.py:479`, `reporting/views.py:318`, `organisation_service.py:174`. With `TIME_ZONE=Asia/Singapore` on UTC containers, 00:00–08:00 SGT the UTC date is a day behind → wrong statutory dates. |
| B-7 | Medium | `config/settings/development.py:96-97`, `testing.py:30-36`, `production.py:69` | Copy-on-write pattern drift (the P10 crash class, P11 rule): `SIMPLE_JWT[...] = …` and `DATABASES["default"][…] = …` mutate the BASE module's dicts in place (runtime-verified: importing development changes base's `ACCESS_TOKEN_LIFETIME` to 1h and base's DB name to `ledgersg_dev`). |
| B-10 | Medium | `document_service.py:905,981` | `send_invoicenow`/`get_invoicenow_status` use raw `.objects.get()` → `DoesNotExist` leaks as 500 (via B-1) instead of the typed 404 contract every sibling uses. |
| B-11 | Medium | `journal_service.py:421-435` | `create_reversal` is a non-atomic two-phase write (entry + `original.save()` after); outside a request transaction (Celery/shell) a failure between the phases permits a SECOND reversal (double-count). |
| B-13 | Low | `journal_service.py:203` vs `database_schema.sql:1742` | Service balance tolerance ≤0.001 vs the DB trigger's ≤0.0001: an imbalance of 0.0002–0.001 passes the service check and fails at COMMIT with an unhandled DB error. |
| B-14 | Low | `config/urls.py:62` | Health endpoint 503 body carries `"error": str(e)` — raw DB error strings to unauthenticated callers. |
| L-1 | Low | `apps/web/src/middleware.ts` | Next 16.1 emits the middleware→proxy deprecation warning at every dev boot. Resolved BY H-1's consolidation (delete middleware; port COOP/CORP/COEP/`upgrade-insecure-requests` + the fuller Permissions-Policy into `next.config.ts headers()`; drop the deprecated `X-XSS-Protection`). |
| L-8 | Low | `apps/web/.env.example` | The `E2E_API_URL`/`E2E_DEMO_EMAIL`/`E2E_DEMO_PASSWORD` trio (read by all 12 gated specs) is documented only in spec comments and DEPLOYMENT.md — not in the env template. |
| M-4 | Medium | `apps/web/vitest.config.ts:44-53` | Coverage excludes `src/app/**`, `src/providers/**`, `src/stores/**` — 57 of 104 non-test source files, including files WITH dedicated tests (banking-client, auth-provider). The header's "lib/gst-engine.ts: 100%" claim is enforced nowhere. Fix via Vitest 4 per-glob thresholds. |
| W-3 | Medium | 36 eslint `no-explicit-any` | 35 are test-file `mockReturnValue({...} as any)` casts (20 + 14 in the two banking test files, 1 in api-client-auth.test.ts) — mechanically fixable with a typed helper; 1 is production (`banking-client.tsx:132` — `accountsData: { results: any[] }` where the real `BankAccount` type exists). |
| D-1..D-23 | High→Low | docs | Extensive docs drift (the docs-audit register): AGENTS header (~9 months stale), PAD metrics tables (P5-era), SKILL §4 runbook counts, README frontend-test block + 932 badge, CLAUDE status row + stale cookie-automation claim, the systemic "36P/1S" (now 37P/0F/0S) across six locations, root `.env.example` missing LOG_DIR, DEPLOYMENT compose path + missing production-ops sections (systemd/nginx/TLS/runtime-role/SMTP), README venv/psql-order errors, dead `e2e_test_phases_7_15_simplified.py` references, AGENTS dead `npm run build` claim, ci.yml comment, Redis version claim, endpoint-count normalization, venv-name standardization. |

**Explicitly deferred (registered, carried forward — not silently dropped):**
B-3 (`TenantModel.save()` auto-org — raises instead of filling; needs a
design decision on the contextvar layer), B-4 (`is_superadmin` phantom flag
— fail-closed today; policy decision needed), B-8 (stale `service.py` +
tracked service scripts), B-9 (org-membership cache invalidation — no
member-removal flow exists yet; plus Redis-outage fail-open path),
B-12 (Peppol `.delay()` before commit — mitigated by the task's retry),
B-15 (CSP report parser), B-16..B-19 (standing posture items), M-2 (scroll
lock save/restore + iOS story — real-device), L-2 (refresh-redirect URL
loss), L-3 (`data-scroll-behavior` unreferenced), L-4 (breakpoint-crossing
sidebarOpen), L-5 (GST chart ARIA roles), L-6 (dead exports + unused
`next-themes` dep), L-7 (dialog semantics polish), L-9 (login half-failure
window), L-10 (HSTS dev anomaly), D-24 (version-label sync), the backend
ruff register (929 findings — unchanged policy), and everything carried
forward from P11/P12's deferred registers.

---

## 3. Task list (TDD; every production-code change ships with its failing test first)

| # | Finding | Task | Tests (RED first) |
|---|---|---|---|
| 1 | B-1 | `transaction.set_rollback(True)` in the exception-handler fallback before returning the 500 envelope (keeps the JSON contract; restores the atomic-rollback guarantee at the handler layer) | `tests/invariants/test_atomic_rollback.py` — new test: a DRF view that writes then raises must leave NOTHING committed (asserts through full dispatch, TransactionTestCase) |
| 2 | B-2 | GST quantum: `Decimal(1).scaleb(-rounding)` (the literal fix); keep ROUND_HALF_UP | Sub-cent regression: `100.05 × 0.09 → 9.00` (currently 9.005); assert line gst_amount cents-level |
| 3 | B-5 | `ImmutableModel` raises the TYPED `ImmutabilityError` (409); the plain class becomes an alias for the typed one (import compatibility) | Existing immutability test updated to assert 409 through the handler; new case asserting the typed envelope |
| 4 | B-6 | `timezone.localdate()` sweep across the 8 sites | A grep-gate test (like the P11 register-throttle gate): production code must not call `date.today()` |
| 5 | B-7 | Copy-on-write completion: `SIMPLE_JWT = {**SIMPLE_JWT, …}` in development/testing; full-dict rebinding for `DATABASES` in all three modules | Settings-gate test: importing development must NOT mutate base's SIMPLE_JWT/DATABASES (the P10 crash class regression) |
| 6 | B-10 | `send_invoicenow`/`get_invoicenow_status` use `get_document`-style typed 404 | 2 RED tests (missing document → 404 typed envelope, not 500) |
| 7 | B-11 | `create_reversal` wraps both phases in one `transaction.atomic()` | A test that forces the second phase to fail and asserts no orphan reversal/no unmarked original |
| 8 | B-13 | Service balance tolerance aligned to the DB trigger's `0.0001` | A 0.0002-imbalance entry: typed 400 at the service layer (currently passes service, 500s at COMMIT) |
| 9 | B-14 | Health endpoint returns a generic error message (detail logged, not leaked) | Test asserting the 503 body has no exception text |
| 10 | H-1 + L-1 | Delete `src/middleware.ts`; consolidate ALL response headers into `next.config.ts headers()` — port COOP/CORP/COEP, `upgrade-insecure-requests` (CSP directive), the fuller Permissions-Policy; keep the P11/M-15 env-aware CSP; drop deprecated `X-XSS-Protection` | A vitest unit test over the header table (asserts the prod CSP has no `unsafe-*`, all cross-origin headers present); live re-verification: served headers match, and the dev-boot deprecation warning is GONE |
| 11 | H-2 | The closed sidebar is `invisible` below md (visibility removes from tab order + a11y tree) with a transform-compatible transition (`transition-[transform,visibility]`), restored when open or ≥md | `shell-mobile-nav.test.tsx`: new closed-state test — with the menu closed, the nav links report `visibility:hidden` and cannot take focus; open → visible |
| 12 | M-1 | Header raised to `z-50` (DOM order after the aside ⇒ paints above the z-40 overlay) | `e2e/mobile-nav.spec.ts`: new step — with the menu open, the X toggle is the real click target (click closes; a hit-target assertion on the toggle's bounding box vs the overlay) |
| 13 | M-3 | `mutations: { retry: 0 }` (React Query default; double-submission hazard removed) | api-client config test asserting the mutation retry policy |
| 14 | W-3 + M-4 | (a) A typed `asQueryResult`-style helper clears the 35 test-file `as any` casts; (b) `banking-client.tsx:132` gets the real `BankAccount` type; (c) `vitest.config.ts` gains per-glob coverage thresholds (`src/lib/**` at the measured floor with gst-engine effectively gated) | The suites stay green (no test-semantics change); eslint `no-explicit-any` count 36 → 0; coverage gate green at the new per-glob ratchet |
| 15 | L-8 + D-9 | `.env.example` truth pass: root gains `LOG_DIR`; `apps/web/.env.example` gains a documented E2E section (`E2E_API_URL`, `E2E_DEMO_EMAIL`, `E2E_DEMO_PASSWORD` — test-tooling only) | grep-level cross-check vs every env read (the D-audit method) |
| 16 | — | Playwright config truth pass: `expect.timeout` standardization (10s), plus the mobile-nav spec gains an Axe scan of the OPEN overlay (locks the a11y floor in CI) | The suite itself (37 specs stay green; the new a11y assertions pass) |
| 17 | — | Screenshots of the remediated surfaces (mobile nav open/closed incl. the focusable-closed fix, desktop, plus current surfaces) → `docs/screenshots/` (session-27 series), pixel+DOM verified | Screenshot driver asserts DOM truths per surface |
| 18 | D-1..D-23 | Docs truth pass: AGENTS header/status, PAD metrics, SKILL §4 counts, README blocks + badge, CLAUDE table + cookie claim, the 36P/1S→37P/0F/0S sweep, ci.yml comment, Redis version, venv naming, endpoint counts | Every claim checked against executed gate output |
| 19 | D-14 + D-6 | `docs/DEPLOYMENT.md`: add the production-ops sections (process management via systemd, reverse proxy + TLS termination, the `ledgersg_app` runtime-role password, SMTP note — or explicit scope-out); fix compose path, §4 psql path, §11 cookie-jar nit; `API_CLI_Usage_Guide.md` e2e row + spot re-verification | Live-command re-verification where applicable |
| 20 | — | P13 report (`docs/REMEDIATION_2026-11-24_P13_REPORT.md`), session log, `worklog.md` entry, final commit + SSH-wrapper push | The final gate below |

## 4. Verification gate (all must be green before push)

1. `pytest --reuse-db --no-migrations -q` → 735P + new tests, 0 failed, 5 skipped
2. `pytest tests/invariants -q` and `pytest tests/security -q` → green (posture unchanged)
3. `npx tsc --noEmit` → 0
4. `npx vitest run` → 518 + new tests, 0 failed
5. `npm run test:coverage` → green at the ratchet (incl. new per-glob thresholds)
6. `npm run build:server` → green
7. `npx eslint src` → `no-explicit-any` 36 → 0; total findings ≤ 45 − 36 = 9 (the documented deferred classes only); no new findings
8. `npm run test:e2e` → 11P + gated with reasons
9. `npm run test:e2e:full` (live stack, demo env) → 37P + new steps, 0 failed
10. Live re-verification: served headers match the consolidated table (prod CSP has no `unsafe-*`); the middleware deprecation warning is gone from the dev boot; closed-sidebar links are `visibility:hidden` at 375; the X toggle closes the open menu as the real hit target
11. GST arithmetic spot-proof on the live stack (sub-cent line → 2dp gst_amount)
12. Screenshots present + DOM-verified

## 5. Commit plan

Conventional commits on `main` only, one per logical task: the exception
rollback + GST quantum + the backend contract batch (or split: B-1 alone,
B-2 alone, the typed-404/atomicity/tolerance batch), the settings
copy-on-write fix, the header consolidation + middleware deletion, the
shell a11y pair (H-2 + M-1), the mutation-retry fix, the typed-suite pass
(any-casts + configs), the .env.example pass, the screenshots, the docs
truth pass, the worklog/session/report. Push via
`docs/ssh_git_wrapper_v3.py --remote git@github.com:nordeim/ledgersg.git`
with remote-ref verification.

## 6. Deferred register

Everything in §2's deferred paragraph, plus P11/P12's carried-forward
registers unchanged. The backend ruff register (929) and the frontend
remaining 9 lint findings keep their unchanged policies — measured, not
weakened.
