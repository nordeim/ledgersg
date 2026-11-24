# LedgerSG — Remediation Report (P13 Sprint: Transactional Truth, Header Consolidation & the Typed Suite)

**Date:** 2026-11-24 (session 27)
**Base commit:** `69f13325` (main — post-P12)
**Plan:** `docs/REMEDIATION_PLAN_2026-11-24_P13.md`
**Source audit:** the post-P12 audit executed LIVE this session: all
baselines reproduced first (backend 735P/0F/5S, tsc 0, vitest 518/518,
eslint 45, e2e default 11P + 26 gated, **live e2e:full 37P/0F/0S** — the
P12-era data-conditional skip now passes with data present), then the
sprint's focus — the mobile navigation menu + a possible TailwindCSS v4
bug — re-verified live with Playwright at 375×812 / 800×1024 / 1280×800
plus an @layer-aware matched-rule trace, and the documented v4 trap
classes swept across `src`. Three parallel deep-audit agents (frontend /
backend / docs-drift) + lead hand-verification of every Critical/High,
using the repo skills' taxonomies (`skills/nextjs16-tailwind4`,
`skills/tailwind-patterns`, `skills/tdd`, `skills/code-review-checklist`,
`skills/lint-and-validate`, `skills/rootless-postgresql`,
`skills/how-to-git-push-using-ssh-wrapper`).
**Method:** TDD (RED → GREEN → full gate). Every production-code change
has a regression test that failed for the documented reason first.

---

## 1. Verification Ledger (executed evidence)

| Gate | Result |
|---|---|
| Backend `pytest --reuse-db --no-migrations -q` | **750 passed, 0 failed, 5 skipped** (755 collected; 735 baseline + 15 new P13 tests) |
| `pytest tests/invariants -q` | **34 passed** (27 baseline + 7 new: the 2 B-1 rollback gates, 2 B-5 immutability gates, the B-6 naive-today gate, the B-11 reversal-atomicity gate, the B-13 tolerance gate) |
| `pytest tests/security -q` | **69 passed, 3 skipped** (66+3 baseline + 3 new B-7 copy-on-write gates) |
| `manage.py check` (testing settings) | 0 errors, 1 issue — the documented `django_ratelimit.W001` |
| Production boot gate | boots with a strong SECRET_KEY + LOG_DIR (the P11 fail-fast gates intact) |
| Frontend `npx tsc --noEmit` | 0 errors |
| Frontend `npx vitest run` | **530/530 passed** (60 files; 518 baseline + 12 new: 8 header-config, 2 shell visibility, 2 retry-policy) |
| `npm run test:coverage` | green at the ratchet — whole-suite 63/51/52/62 **plus the new `src/lib/**` per-glob floor 73/52/74/71** (P13/M-4) |
| `npm run build:server` | green |
| `npx eslint src` (whole tree) | **45 → 9 findings** — the 36 `no-explicit-any` cleared (W-3); the 9 remainder are exactly the documented deferred register (3 set-state-in-effect + 3 exhaustive-deps + 2 immutability + 1 incompatible-library) |
| `npm run test:e2e` (no backend) | 11 passed + 29 gated with reasons (40 specs) |
| `npm run test:e2e:full` (live stack) | **40 passed, 0 failed, 0 skipped** (40 specs — 37 baseline + 3 new P13 mobile-nav specs) |
| Backend ruff (touched files) | 310 → 305 findings on the touched set (no new debt; 5 cleared by the unused-import cleanup); the repo-wide register keeps its unchanged policy |
| Live mobile-nav re-verification | toggle/overlay/open/close/navigate/auto-close/keyboard/desktop-sticky all pass at 375/800/1280; the @layer-aware rule trace re-proves only `.inline-flex` + the media-gated `.md\:hidden` match the toggle (`display:flex` = correct flex-item blockification); the nav's `space-y-1` children carry no explicit margins (computed `margin-block-end:4px; margin-top:0px` — the pure v4 model, no trap-4 violation); no horizontal overflow; no console errors (the anonymous 401 + recharts mount noise are the documented classes) |
| Live header verification | the served headers are the consolidated table (dev CSP keeps the dev-only unsafe exemptions, script-src tight; COOP/CORP/COEP + the full Permissions-Policy present; X-XSS-Protection gone); **zero middleware-deprecation warnings at dev boot** (the file is deleted) |
| GST live proof | `POST /gst/calculate/` with `100.05 × 0.09` → `"gst_amount": "9.00"` (IRAS 2dp; pre-fix it returned the 3-dp `9.005`) |
| Screenshots | 8 new (`docs/screenshots/72-79_*_session27.png`) — pixel-verified (correct dims 1280×800 / 375×812, content-rich, md5-unique) with DOM truths asserted per surface |

## 2. The Sprint Verdicts

### The mobile navigation menu — WORKS (re-confirmed live, post-P12)

All P12 conclusions hold on a fresh environment: the toggle renders and
is keyboard-operable at 375, the overlay click/Escape/Tab-trap/scroll-lock/
focus-return behaviors are intact, nav links navigate to the
trailing-slash routes AND auto-close, the tablet and desktop bands behave.
Two genuine edge-state defects the P12 scope did not cover were found and
fixed this sprint (H-2, M-1 — see §3).

### The suspected TailwindCSS v4 bug — still does not exist (settled with a better trace)

The P12 rule-trace conclusion re-confirmed with a corrected,
`@layer`-recursing walker (v4 emits utilities inside CSSLayerBlockRule —
a flat walk finds nothing): only `.inline-flex` and the media-gated
`.md\:hidden` match the toggle; `display:flex` is correct CSS flex-item
blockification. The validation report's trap log swept clean: no
space-y/space-x container in the nav (or anywhere in the mobile-nav
surface) carries explicit-margin children; only 2 `shadow-sm` usages
exist app-wide (a v4-first app — the shadow-scale shift is by-design);
zero gradients; hex theme palette (no bare-HSL trap).

## 3. What Was Fixed

| # | Finding | Fix | Evidence |
|---|---|---|---|
| B-1 (Critical) | The DRF exception handler's 500 fallback returned a plain Response — DRF dispatch accepted it, the ATOMIC_REQUESTS wrapper saw a "successful" request and COMMITTED partial writes (runtime-reproduced: a register-halfway user persisted behind the 500). The C-04 contract was defeated one layer above `wrap_response` | `transaction.set_rollback(True)` before returning the 500 envelope (guarded by `in_atomic_block`; the JSON contract unchanged) | 2 RED tests → GREEN: handler-level (`get_rollback() is True`, the canary write gone after the atomic block) + full-dispatch (POST /auth/register/ with generate_tokens patched to raise → 500 envelope AND no user/org/membership persisted) |
| B-2 (High) | GST per-line rounding quantum was one decimal too fine: `Decimal(f"0.{('0'*rounding)}1")` built `0.001` for rounding=2 — sub-cent bases persisted mil-level GST (100.05 × 0.09 → 9.005) into lines, totals, journal postings and F5 boxes | `Decimal(1).scaleb(-rounding)` (the unit at the rounding place) | 2 RED sub-cent tests → GREEN (100.05 → 9.00; 100.06 → 9.01 half-up at cents) + the live curl proof |
| H-1 (High) | Dual header definitions: the middleware's CSP silently overrode next.config's — live-verified: the served CSP shipped `'unsafe-eval' 'unsafe-inline'` unconditionally plus Vercel-specific origins, defeating the P11/M-15 env-aware hardening in production | `src/middleware.ts` DELETED; all headers consolidated into `next.config.ts headers()` (COOP/CORP/COEP + `upgrade-insecure-requests` (production) + the full Permissions-Policy ported; the deprecated X-XSS-Protection dropped) | 8-test header-config gate (RED: 5 — the trio/upgrade/full-permissions missing, X-XSS present → GREEN: 8/8) + live served-header verification + the dev-boot deprecation warning gone |
| H-2 (High) | The CLOSED mobile sidebar stayed keyboard-focusable — `transform` does not remove from the tab order/a11y tree (~10 invisible focusables before the header at 375; WCAG 2.4.3/2.4.7) | `invisible md:visible` on the closed state + `transition-[transform,visibility]` (discretely-animatable — the slide-out stays visible through the transition) | RED vitest (the closed aside lacks `invisible`) → GREEN (9/9); e2e: `toHaveCSS("visibility","hidden")` on the closed aside + first nav link (CSS locator — the a11y-tree exclusion is the fix working), restored on open |
| M-1 (Medium) | The overlay (z-40) painted above the header (z-30): the X toggle was blurred/unclickable while the menu was open; no unit test could see it (jsdom has no layout) | Header raised to z-50 (DOM order after the aside ⇒ paints above the overlay) | e2e: `elementFromPoint` at the toggle's center resolves to the Close-navigation button + the click closes (all 6 mobile-nav specs green) |
| M-3 (Medium) | `mutations: { retry: 1 }` re-fired failed POSTs — including 4xx on non-idempotent payment endpoints (double-submission hazard) | `retry: 0` for mutations (React Query's default; idempotency keys belong on the backend) | RED config test → GREEN (mutations retry 0/false; the queries carve-out untouched) |
| B-5 (Medium) | `ImmutableModel.save()` raised a PLAIN ImmutabilityError (not the typed 409 variant, which had zero raisers) → surfaced as 500 | `common/models.py` now imports and raises the TYPED class (409 `immutable_record` envelope); the plain class is replaced outright (nothing imported it) | 2 RED tests → GREEN (typed raise through save; the handler maps it to the 409 envelope) |
| B-6 (Medium) | 17 naive-today/now calls in production code (8 `date.today()` from the audit + 9 `datetime.now()` the new gate caught in peppol/reporting) — wrong statutory dates 00:00–08:00 SGT on UTC containers | `timezone.localdate()` / `timezone.now()` sweep + unused-import cleanup | The new `test_no_naive_today.py` source-scan gate (RED: 17 offenders → GREEN: 0) |
| B-7 (Medium) | Copy-on-write drift: `SIMPLE_JWT` (dev) and `DATABASES` (dev/testing/production) mutated the base module's dicts in place (the P10 crash class) | Full-dict rebinding (`{**DATABASES, "default": {**DATABASES["default"], …}}`, `SIMPLE_JWT = {**SIMPLE_JWT, …}`) in all three modules | 3 RED identity gates → GREEN (identity assertions — value comparisons are maskable by .env resolution, the lesson is in AGENTS) |
| B-10 (Medium) | `send_invoicenow`/`get_invoicenow_status` used raw `.objects.get()` → DoesNotExist leaked as 500 instead of the typed 404 | Both now use `DocumentService.get_document` (the typed ResourceNotFound path) | 2 RED tests (500s) → GREEN (404 `not_found` envelopes) |
| B-11 (Medium) | `create_reversal` was a non-atomic two-phase write — outside a request transaction a marking-phase failure left an orphan reversal permitting a SECOND reversal (double-count) | Both phases wrapped in one `transaction.atomic()` | RED test (a patched marking-phase failure left the orphan) → GREEN (the reversal rolls back with the marking failure) |
| B-13 (Low) | Service balance tolerance 0.001 vs the DB trigger's 0.0001 — a 0.0002–0.001 imbalance passed the service and 500'd at COMMIT | Service tolerance aligned to `0.0001` (matching `database_schema.sql`) | RED test (0.0005 imbalance blew up at COMMIT) → GREEN (typed 400 at the service) |
| B-14 (Low) | The health endpoint's 503 body embedded `str(e)` — raw DB error strings to unauthenticated callers | Generic message in the body; the detail goes to the logger (`logger.exception`) | RED test (the marker string in the body) → GREEN (marker absent, log carries the traceback) |
| W-3 (Medium) | 36 `no-explicit-any` findings: 35 test-file `as any` mock casts + 1 production `any` | The 35 re-cast via the proven in-file `as unknown as ReturnType<typeof hook>` pattern (a brace-matching transform); `banking-client.tsx` got the real `BankAccount` type | eslint 45 → **9**; all 41 tests in the touched files green; no test-semantics change |
| M-4 (Medium) | Coverage excluded 57 of 104 source files; the "gst-engine 100%" claim was enforced nowhere | Vitest 4 per-glob thresholds: `"src/lib/**"` at the measured floor (73/52/74/71) on top of the whole-suite ratchet | `npm run test:coverage` green at both ratchets |
| L-1/L-8/D-9 (Low) | The middleware deprecation warning; the E2E env trio undocumented; root `.env.example` missing LOG_DIR | Middleware deleted (L-1 resolved by H-1); `apps/web/.env.example` gains the documented E2E section; root `.env.example` gains LOG_DIR + the P13 middleware note | grep-level cross-checks; live boot log |
| Playwright config | Assertion timeouts hand-rolled per spec; no a11y scan of the P12-hardened overlay | `expect: { timeout: 10_000 }` at config level; the mobile-nav spec gains the axe scan + the visibility/hit-target specs | All 40 specs green live |
| D-1..D-23 (docs) | Extensive docs drift (AGENTS header, PAD metrics, SKILL §4 runbook, README blocks/badge/quickstart, CLAUDE rows + the stale cookie-automation claim, the 36P/1S→40P/0F sweep, compose path, dead references, venv naming, Redis version, ci.yml comment, endpoint counts) + DEPLOYMENT.md's missing production-ops sections | Full docs truth pass + DEPLOYMENT.md §12.1–12.4 (systemd units, nginx TLS termination, the `ledgersg_app` runtime-role password, SMTP) + API guide v2.6.0 with the P13 verification addendum | Every count cross-checked against this table's executed output |

### Environment lessons (recorded)

- The sandbox recycle wiped PG's `usr/share` tree and the cluster's empty
  subdirs (including `pg_logical/snapshots` — a checkpoint-fatal gap the
  ensure script didn't cover) and Redis's extracted binaries; both
  recovered per `skills/rootless-postgresql` (debs re-extracted, subdirs
  restored, liblzf added).
- A ~60-line double-fork daemonizer gives `runserver`/`next dev` the same
  tool-call survival as pg_ctl/redis daemons — the one-call constraint of
  earlier sessions is lifted (Next dev still needs a manual restart for
  next.config.ts changes; HMR covers source only).
- A nohup'd `npm run dev` dies at call end even when pg/redis survive —
  true daemonization is the difference.

## 4. Deferred Debt Register (explicit — nothing silently dropped)

- **B-3** `TenantModel.save()`'s auto-org-from-context (raises instead of
  filling; needs a design decision on the contextvar layer) and the
  never-reset tenant contextvars.
- **B-4** `is_superadmin` phantom flag (fail-closed today; standardize on
  `is_superuser` or add the field — a policy decision).
- **B-8** the stale `config/settings/service.py` + its tracked service
  scripts (no RLS/audit middleware, wildcard hosts).
- **B-9** org-membership cache invalidation (no member-removal flow
  exists yet) + the cache read sitting outside the fail-secure try.
- **B-12** Peppol `.delay()` before commit (mitigated by the task retry;
  the `transaction.on_commit` pattern is the registered follow-up).
- **B-15..B-19** the standing posture items (CSP report parser, admin
  mount, refresh-cookie Origin check, report-only CSP, allocation
  locking, audit IP provenance, misc config debt).
- Frontend: M-2 (scroll-lock save/restore + the iOS real-device story),
  L-2 (refresh-redirect URL loss), L-3 (`data-scroll-behavior`
  unwired), L-4 (breakpoint-crossing sidebarOpen), L-5 (GST chart ARIA
  roles), L-6 (dead exports + the unused next-themes dep), L-7 (dialog
  semantics polish), L-9 (login half-failure window), L-10 (HSTS dev
  anomaly), the remaining 9 eslint findings (unchanged policies).
- The backend ruff register (~305 on the touched set; repo-wide 929-era
  debt with the unchanged policy) and the D-24 version-label sync.
- Everything carried forward unchanged from P11/P12's registers.

## 5. How to Verify (reproduction commands)

```bash
# backend gate
cd apps/backend && pytest --reuse-db --no-migrations -q   # 750P/0F/5S
pytest tests/invariants -q                                 # 34P
pytest tests/security -q                                   # 69P/3S

# frontend gates
cd apps/web && npm run typecheck && npm test               # 0; 530/530
npm run test:coverage && npm run build:server               # both green
npx eslint src    # 9 findings — 3 set-state-in-effect + 3 exhaustive-deps
                 # + 2 immutability + 1 incompatible-library

# e2e (no backend) + live gate (E2E_DEMO_* trio exported first)
npm run test:e2e               # 11P + 29 gated with reasons
export E2E_API_URL=http://127.0.0.1:8000 \
       E2E_DEMO_EMAIL=demo@ledgersg.sg \
       E2E_DEMO_PASSWORD=demo1234pass
npm run test:e2e:full          # 40P/0F/0S (40 specs)

# the P13 regression tests, by name
npx vitest run src/__tests__/headers-config.test.ts        # 8 (the header table)
npx vitest run src/components/layout/__tests__/shell-mobile-nav.test.tsx  # 9
npx vitest run src/lib/__tests__/api-client-retry-policy.test.ts          # 2

# live spot-proofs
curl -sI http://localhost:3000/login/ | grep -i content-security   # the consolidated CSP
curl -s -X POST .../gst/calculate/ -d '{"amount":"100.05","rate":"0.09",...}'  # gst 9.00
```

## 6. Commits

Conventional commits on `main` per plan §5: the backend transactional-truth
batch (B-1/B-2 + the contract batch), the settings copy-on-write fix, the
header consolidation + middleware deletion, the shell a11y pair (H-2+M-1)
+ the e2e additions, the mutation-retry fix, the typed-suite pass (W-3 +
configs), the .env.example pass, the screenshots, the docs truth pass,
the worklog/session/report — pushed via `docs/ssh_git_wrapper_v3.py
--remote git@github.com:nordeim/ledgersg.git` with remote-ref
verification. See `git log 69f13325..HEAD` for the full set.
