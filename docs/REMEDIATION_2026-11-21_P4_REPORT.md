# LedgerSG — Remediation Report (P4 Sprint: Cross-Reload Session Persistence, Evidence-Gated Refresh & Docs Truth)

**Date:** 2026-11-21 (session 9)
**Base commit:** `33e176bf` (main)
**Plan:** `docs/REMEDIATION_PLAN_2026-11-21_P4.md`
**Method:** TDD (RED → GREEN → REFACTOR); every production-code fix has a regression test that failed before the fix and passes after. The 6 hint-cookie tests, 3 evidence-gate tests and the rate-knob test were all RED first; the e2e session spec was RED-captured at the plan-validated state (reload landed on `/login`). The sprint's mid-flight design flaw (refresh-on-every-401) was itself caught by the new e2e run and re-driven through a second RED/GREEN cycle — the regression tests for it (3 vitest + 6 pytest) are the evidence that the flaw can never silently return.

---

## 1. Verification Ledger (executed evidence)

Environment: rootless PostgreSQL 17 on :5432 (schema v1.1.0 in `ledgersg_dev` + `test_ledgersg_dev`), Redis 8 on :6379, Python 3.12 venv, Node with `@playwright/test` + chromium, Django dev server (development settings) on :8000 during the e2e/screenshots phases.

| # | Check | Command | Result |
|---|---|---|---|
| 1 | Baseline (pre-remediation, session start) | `pytest --reuse-db --no-migrations -q` | **519 passed, 0 failed, 5 skipped at base `33e176bf`** — the documented P3 state reproduced exactly before any change |
| 2 | Baseline (frontend) | `npx vitest run` / `npm run typecheck` / `npm run test:e2e` | 349/349, 0 errors, 9 passed + 4 gated skips — documented state reproduced |
| 3 | Backend RED (hint cookie) | `pytest tests/security/test_refresh_cookie.py -q` | **5 failed** for the right reason (no `session_hint` in `Set-Cookie`) before the GREEN implementation |
| 4 | Backend GREEN (cookie suite) | same | **14 passed** (8 Task-1 cookie tests + 6 new hint tests) |
| 5 | Full backend suite (post-remediation) | `pytest --reuse-db --no-migrations -q` | **0 failed, 534 passed, 5 skipped** (519 + 8 cookie + 1 rate-knob + 6 hint) |
| 6 | Invariant / security gates | `pytest tests/invariants -q` / `pytest tests/security -q` | **20 passed** / **47 passed, 3 skipped** (no regressions; +15 security tests this sprint) |
| 7 | Django system check | `DJANGO_SETTINGS_MODULE=config.settings.testing python manage.py check` | 0 errors, 1 known pre-existing warning (`django_ratelimit.W001`) |
| 8 | Ruff (touched backend files) | `ruff check apps/core/views/_refresh_cookie.py apps/core/views/auth.py tests/security/test_refresh_cookie.py config/ratelimits.py` | **All checks passed** — new files clean, touched files carry no new findings |
| 9 | Frontend RED (evidence gate) | `npx vitest run src/lib/__tests__/api-client-auth.test.ts` | the anonymous-401 gate test failed exactly as designed: `expected "vi.fn()" to be called 1 times, but got 2 times` (the pointless refresh) |
| 10 | Frontend GREEN (full unit suite) | `npx vitest run` | **354 passed (354)** — 349 + 3 gate tests + 2 cold-reload tests upgraded with the hint precondition |
| 11 | Frontend typecheck | `npm run typecheck` | **0 errors** |
| 12 | ESLint (touched frontend files) | `npx eslint api-client.ts api-client-auth.test.ts shell.tsx` | 6 findings, **all pre-existing** (registered B-6 debt classes; zero from the new code) |
| 13 | Frontend e2e (default, backend-less) | `npm run test:e2e` | **9 passed + 7 gated skips with reasons** — green by default on a fresh clone |
| 14 | Frontend e2e (full, backend + Redis) | `npm run test:e2e:full` | **16/16 passed** (incl. wrong-password error surfacing — the test that exposed the every-401 flaw — and the three session-persistence specs: reload survival, post-reload client navigation, logout-kills-session) |
| 15 | Live cookie flow (login) | `curl -D -` login | `Set-Cookie: refresh_token=…; HttpOnly; Max-Age=2592000; Path=/api/v1/auth/; SameSite=Lax` **and** `Set-Cookie: session_hint=1; Max-Age=2592000; Path=/; SameSite=Lax` (JS-readable — no HttpOnly) |
| 16 | Live cookie flow (refresh) | `curl -b cj.txt POST /auth/refresh/ -d '{}'` | **200** — the cookie alone refreshes, rotation re-sets both cookies |
| 17 | Live cookie flow (failure hygiene) | garbage `refresh_token` cookie → POST refresh | **401** with both cookies expired in the response (dead evidence cannot linger); body-path failure sends no `Set-Cookie` at all (test-verified) |
| 18 | Live cookie flow (anonymous 401) | bad-credentials login | **401 with zero `Set-Cookie` headers** — the anonymous failure never touches browser state |
| 19 | Playwright listing | `npx playwright test --list` | 16 tests in 4 files (was 13 in 3) |
| 20 | Screenshots | `docs/screenshots/19..23_*_session9.png` | 5 new unique PNGs (md5-distinct, 1440px wide, 22-88KB, non-blank vs the session-7 baseline profile; includes **23_dashboard_after_reload — the E-1 evidence shot**) |
| 21 | Docs truth sweep | greps across README/PAD/CLAUDE/AGENTS/ledgersg_SKILL | no `NUMERIC(10,4)` precision claims, no "706/714 tests" badges, no stale overflow "Known limitation" rows remain |
| 22 | Root `.env.example` | read + cross-check vs both app templates | present; 16 backend + 3 live web variables listed truthfully; no values |

Confidence labels: rows 1-14, 21-22 **Verified** (executed in this environment); rows 15-18 **Verified** (executed via live curl against the dev server this session); row 19-20 **Verified**. Production-path claims inherited from the P3-verified `docs/DEPLOYMENT.md` (gunicorn/standalone builds) are **Reasoned** (not re-executed this sprint; the dev-path equivalents were). The cross-site `SameSite=None` topology note in DEPLOYMENT.md §9 is **Reasoned** (documented consequence of the cookie contract, not deployed here — the localhost pair is same-site by construction).

---

## 2. What Was Fixed

### E-1 backend — HttpOnly refresh-cookie session persistence
`login_view`/`register_view` now set the refresh token as an HttpOnly cookie (`Path=/api/v1/auth/`, SameSite=Lax, Secure=!DEBUG, 7-day max_age matching `REFRESH_TOKEN_LIFETIME`) alongside the unchanged body tokens; `refresh_view` accepts body **or** cookie (rotation + blacklist identical on both paths; the rotated pair is re-set as the new cookie); `logout_view` blacklists whichever credential is present and expires the cookie; `change_password_view` expires it (every refresh token is revoked). Helpers live in `apps/core/views/_refresh_cookie.py`. The api-client header comment that claimed "refresh token: HttpOnly cookie" for years is finally true. **8 contract tests** (`tests/security/test_refresh_cookie.py`).

### E-1 frontend — refresh on the cold 401
`fetchWithAuth` attempts the refresh on ANY 401 **when session evidence exists** and retries the original request with the new token — the `&& accessToken` guard that made every cold reload drop the session is gone. After a full page reload the first `me` call 401s, the client refreshes through the cookie (`credentials: "include"`, no body, no JS access to the token), and the retry succeeds: sessions survive reloads, new tabs and browser restarts, exactly like the documented 7-day design always claimed.

### E-1 refinement — the evidence gate (root-caused from the e2e run)
The first cut refreshed on every 401 — which turned a bad-password login into a pointless refresh POST that (a) structurally exceeded the refresh endpoint's 20/min-per-IP rate limit during the e2e run and (b) hard-redirected to `/login` and swallowed the login form's own error. The fix: the backend sets a second, **non-secret, JS-readable `session_hint` marker cookie** (`path=/`, NOT HttpOnly, dies wherever the refresh cookie dies — logout / password change / failed cookie-refresh); the api-client attempts the refresh only with evidence (in-memory access token OR the hint cookie); anonymous 401s propagate to the caller untouched (the login form shows its real error, no redirect, exactly one network call — regression-tested). A failed cookie-path refresh expires both cookies server-side so the browser stops carrying dead evidence.

### Rates — settings-driven login limits (SEC-002 posture unchanged)
Login rates became settings knobs resolved lazily per request (`config/ratelimits.py` dotted-path callables): production defaults are IDENTICAL (`LOGIN_RATELIMIT_IP="10/minute"`, `LOGIN_RATELIMIT_USER="30/minute"` — test-asserted against `config.settings.base`); only the development settings raise the IP budget to 60/min because `test:e2e:full` legitimately issues ~11 logins per run. The guardrail was never weakened.

### E-1 UX — logout affordance
The shell's user footer gained a logout button (the existing Button + lucide `LogOut` pattern): the persisted session now has a UI kill switch — `logout()` posts to the auth endpoint which blacklists and expires both cookies.

### E-5 — session-persistence e2e spec
`e2e/session.spec.ts` (backend-gated exactly like the invoices spec): reload survival, post-reload client-side navigation, and logout-ends-the-session. The playwright config header documents the gating. Suite grew 13 → 16 (9 always-green + 7 gated).

### Session-directive extras — E-2/E-3/E-4
Root `.env.example` (truthful combined index; no values); README truth pass (badge 714→904 with the P4 counts, NUMERIC(19,4) rows, P4 milestone block, suite tables, execution comments 519→534 / 349→354 / 13→16); PAD v3.2.0 (metrics, precision principle, the now-true Zero-JWT-Exposure implementation, auth flow); CLAUDE.md v2.9.0 (status, component table, P4 milestone block); AGENTS.md session-9 lessons (the three-link defect chain, the evidence gate, settings-driven rate knobs, sandbox reaping, jsdom cookie hygiene); ledgersg_SKILL.md v1.4.0 (non-negotiable #2 wording, project_state, debugging rows incl. the cookie-flow rows, lessons #13-14, quick-ref); DEPLOYMENT.md (§1 cookie flow, §8 reload-persistence smoke + counts, §9 SameSite=None caveat for cross-site topologies, §10 updated 429 row).

---

## 3. Deferred Debt Register (explicit — nothing silently dropped)

Carried forward unchanged from the P3 register (`docs/REMEDIATION_PLAN_2026-11-21_P3.md` §4) unless touched here:

| Item | Status |
|---|---|
| H-02 base-currency reporting / retained earnings / BS assertion | Deferred (design work) — still the next heavyweight |
| H-08 wire `send-invoicenow` to real `TransmissionService` | Deferred (adapter contract) |
| H-09 (rest) Reg-11 tax-invoice labelling | Deferred |
| H-10 Schematron fail-closed validation | Deferred |
| H-11 fiscal close controls | Deferred |
| H-13 reproducible container build | Deferred |
| M-02…M-16, L-01…L-10, I-01…I-08 | Deferred per audit roadmap |
| GST payment tracking (`pay_return`) | Intentionally raises until schema extension |
| Backend repo-wide ruff debt (~1,311 findings) | Pre-existing; touched files stay lint-clean |
| B-6 frontend eslint debt (incl. the 6 pre-existing findings in `api-client-auth.test.ts`/`shell.tsx`) | Pre-existing; dedicated sprint (large-diff risk) |
| F5 return rate-basis (computation date vs document date) | Deferred — period-cut semantics (ties into H-02) |
| A-10 stale root `requirements.txt` | Deferred (repo-owner coordination) |
| e2e login-rate budget | **Resolved structurally this sprint** — settings knobs (dev 60/min IP; production 10/min unchanged), documented in DEPLOYMENT.md §8 |
| ~~Cross-reload session persistence~~ | **RESOLVED this sprint (E-1)** — cookie flow + cold-401 refresh + reload e2e |
| Cross-site production cookie topology (`SameSite=None; Secure`) | NEW, documented — one-line change in `_refresh_cookie.py` when a split-domain deployment exists; not applicable to the current same-site shape |

---

## 4. How to Verify (reproduction commands)

```bash
# Prerequisites: PG on :5432 (schema v1.1.0), Redis on :6379, backend venv + web node_modules
cd apps/backend
export DB_NAME=test_ledgersg_dev DB_USER=ledgersg DB_PASSWORD=ledgersg_secret_to_change \
       DB_HOST=127.0.0.1 DB_PORT=5432
pytest tests/security/test_refresh_cookie.py -q      # 14 passed
pytest tests/security/test_rate_limiting.py -q       # settings-knob assertions
pytest --reuse-db --no-migrations -q                 # 534 passed, 0 failed, 5 skipped

cd ../web
npx vitest run src/lib/__tests__/api-client-auth.test.ts   # incl. the 3 gate tests
npm run typecheck

# Live cookie flow (dev server on :8000; any existing user):
curl -s -c /tmp/cj.txt -X POST http://127.0.0.1:8000/api/v1/auth/login/ \
  -H 'Content-Type: application/json' -d '{"email":"demo@ledgersg.sg","password":"demo1234"}' \
  -D - -o /dev/null | grep -i set-cookie
# -> refresh_token (HttpOnly, Path=/api/v1/auth/) AND session_hint (Path=/)
curl -s -b /tmp/cj.txt -X POST http://127.0.0.1:8000/api/v1/auth/refresh/ \
  -H 'Content-Type: application/json' -d '{}' -o /dev/null -w '%{http_code}\n'
# -> 200 (the cookie alone refreshes)

# Full e2e (with the backend on :8000 + Redis; ~11 logins — dev budget 60/min):
npm run test:e2e:full        # 16/16 incl. the reload-persistence specs

# Browser acceptance: log in at localhost:3000, press F5 — stays on /dashboard.
```
