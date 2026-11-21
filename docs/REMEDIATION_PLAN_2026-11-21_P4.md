# LedgerSG — Remediation Plan (P4 Sprint: Session Persistence, Suite Depth & Docs Truth)

**Date:** 2026-11-21 (session 9)
**Base commit:** `33e176bf` (main)
**Source:** this session's audit (below) + the deferred-debt register of `docs/REMEDIATION_PLAN_2026-11-21_P3.md` §4 (the cross-reload session-persistence item is the session-7 handoff's "suggested next") + the session-9 user directives (vitest + playwright suite work via the config files; root `.env.example`; deployment-guide verification; screenshots; worklog; push)
**Execution mode:** Mode B/D — TDD (RED → GREEN → REFACTOR), surgical fixes
**Plan validated against:** live codebase + rootless PostgreSQL 17 (schema v1.1.0 in `ledgersg_dev` + `test_ledgersg_dev`) + Redis 8 on :6379; all four baselines reproduced exactly before planning — backend `pytest` **519 passed / 0 failed / 5 skipped**, invariants **20 passed**, security **32 passed / 3 skipped**, frontend `vitest` **349/349 (29 files)**, `tsc --noEmit` **0 errors**, playwright default **9 passed + 4 gated skips**; `manage.py check` 0 errors (1 known W001).

**Post-writing validation (plan checked against code before execution):**
- The three-part session-persistence defect chain independently reproduced in source (see E-1 evidence; each file/line cited and re-read after planning).
- The backend already ships every prerequisite for a cookie-based refresh flow: `CORS_ALLOW_CREDENTIALS = True` (`config/settings/base.py:299`), `CORS_ALLOWED_ORIGINS` includes the web origins, and the api-client already sends `credentials: "include"` on every request including `tryRefreshToken` (`src/lib/api-client.ts:63-67, 128-134`) — so the browser will store and replay the cookie with **zero frontend transport changes**.
- DRF `Response` objects support `response.set_cookie(...)`; the auth views are plain `@api_view` functions returning `Response` (verified in `apps/core/views/auth.py`).
- The refresh rotation contract is intact for the cookie path: `auth_service.refresh_access_token()` rotates + blacklists (H-05) and returns the new pair; setting the rotated token as the new cookie keeps the invariant (the old cookie is dead after first use).
- Playwright chromium is installed (v1208 + headless shell); `E2E_API_URL` gating pattern is established (`e2e/invoices.spec.ts`) — the new session spec reuses it verbatim.
- The vitest api-client tests already mock `global.fetch` with response sequences (`src/lib/__tests__/api-client-auth.test.ts`) — the cold-reload refresh test extends the established pattern.
- No new environment variables are required by the cookie flow (secure/samesite derive from `DEBUG`).

---

## 0. Audit Summary (what this plan is built on)

Focus per instructions: **recent code changes** (the P3 sprint commits `2b6b6a82..33e176bf`) plus the repo-included skill-driven sweep (`skills/code-review-and-audit` standard mode scoped to `apps/` + manual verification of every scanner finding, `code-quality-standards` severity discipline, `diagnosing-bugs` root-cause loop, `e2e-testing-lessons` for the suite work).

Severity taxonomy: Critical / High / Medium / Low / Info. Counts: **0 Critical, 1 High, 2 Medium, 3 Low.**

### P3-sprint change review (recent changes — verified good)

- `api-client.ts` (`fetchWithAuth` + `api.blob()`), `use-tax-codes.ts`, `use-accounts.ts`, `invoice-submit.ts`, `invoice-form.tsx`, `invoice-line-row.tsx`, `e2e/auth.spec.ts`, `e2e/invoices.spec.ts` — all re-read in full this session; the P3 report's claims hold (single auth path, fail-closed rates, pure adapter, green-by-default gating).
- Backend P3 changes re-verified in source: `add_line` server-side discount (quantization correct), §16 idempotent migration (re-load of both DBs this session confirmed the count-then-skip guard and the restored `amount_due` GENERATED ALWAYS column), conformance gate including precision assertions.
- Scanner sweep: 21 backend + 6 web "criticals" — **every one manually re-verified as a false positive** (test fixtures with literal test passwords, docstrings mentioning "JWT Bearer token", an endpoint path string containing "password", comments describing the P3 fix). The same false-positive classes documented in sessions 3/5/7; no new classes. The two `any`-type web hits (`banking-client.tsx:115`, an api-client-auth test mock) are the registered **B-6 frontend eslint debt** — kept deferred (dedicated sprint, large-diff risk, per the standing register).

### Findings (register for this sprint)

- **E-1 (High, UX + auth security posture): Cross-reload session persistence is broken end-to-end.** Three independent links in the chain (all verified in source this session):
  1. **Backend sets no refresh cookie.** `login_view`/`register_view`/`refresh_view` return the token pair in the body only (`apps/core/views/auth.py:80-84, 46-49, 112-113`). The api-client's own header comment claims "Refresh token: 7 day expiry, HttpOnly cookie" (`src/lib/api-client.ts:9`) — the code that would set that cookie has never existed.
  2. **The frontend discards the refresh token.** `login()` stores only `response.tokens.access`; `response.tokens.refresh` is never persisted anywhere (`src/providers/auth-provider.tsx:137-147`).
  3. **The client-side refresh path cannot fire on a cold reload.** `fetchWithAuth` only attempts refresh when `response.status === 401 && accessToken` (`src/lib/api-client.ts:70`) — after a full page reload `accessToken` is null, so even with a cookie-based backend the retry would never be attempted; the 401 propagates, `checkSession`'s catch redirects to `/login`. (Session 7 observed the symptom — "tryRefreshToken posts an empty body the backend 400s" — and registered the design work; the third link is new this session.)
  Consequence: **every full page reload, every new tab, and every browser restart drops the user's session** despite a 7-day refresh token design. Also related: `logout()` posts no body, so the issued refresh token is never blacklisted on user-initiated logout (`logout_view` reads `request.data.get("refresh")` only — `apps/core/views/auth.py:129-131`).
- **E-2 (Medium, docs): post-P3 stale claims in the core docs.** `README.md:63` still advertises "NUMERIC(10,4) Precision" (schema has been 19,4 since v1.1.0) and the tests badge says 714; `Project_Architecture_Document.md` ("NUMERIC(10,4) for everything", "706 Tests Passing", v3.1.0/2026-03-12 header) contradicts the P3 state; `ledgersg_SKILL.md:30` non-negotiable #2 says "Money is NUMERIC(10,4)" and the debugging guide still carries "numeric field overflow → Known limitation; widen in the versioned patch when scheduled" (fixed in P3); `AGENTS.md` carries pre-P3 stale rows (Redis caching listed as long-term while shipped).
- **E-3 (Low, env): no root-level `.env.example`** (explicit session directive). Both app-level templates are truthful (P2 B-4 + P3 D-4); the repo root has none to point a fresh operator at them.
- **E-4 (Low, deployment): `docs/DEPLOYMENT.md` predates this sprint** — after E-1 it must be updated (login/refresh/logout now also set/rotate/delete an HttpOnly refresh cookie) and its commands re-verified against the remediated tree (explicit session directive: step-by-step fresh-host guide from `git clone`).
- **E-5 (Low, suite directive): extend the vitest + playwright suites.** The configs exist and are green (P2/P3): `apps/web/vitest.config.ts` (jsdom, RTL setup, coverage thresholds, `src/**/*.{test,spec}.{ts,tsx}` include) and `apps/web/playwright.config.ts` (chromium default, `PLAYWRIGHT_PROJECTS=all` opt-in, `E2E_API_URL` gating documented in the header). The session directive is satisfied by **extending the suites through these configs** (new tests land in the established include/gating patterns); no behavioral config change is required, and none will be made gratuitously (surgical-diff discipline).

---

## 1. Task 1 (E-1 backend): HttpOnly refresh-cookie flow

**Problem.** See E-1 chain. The design decision (open question in the P3 register — "cookie-based or body-based refresh persistence design is feature work") is resolved here: **cookie-based**, because the repo mandate already says refresh tokens belong in HttpOnly cookies (AGENTS.md §Security Posture, api-client header), `CORS_ALLOW_CREDENTIALS` is already on, and a body-based design would require the frontend to hold the refresh token in JS memory — contradicting the zero-JWT-exposure posture the repo documents.

**Fix (surgical, additive):**
1. New `apps/core/views/_refresh_cookie.py` (or inline helpers in `apps/core/views/auth.py` — decision: a small private helper module keeps the four call sites one-line): `set_refresh_cookie(response, refresh_token)` and `delete_refresh_cookie(response)` using `path="/api/v1/auth/"`, `httponly=True`, `samesite="Lax"`, `secure=not settings.DEBUG`, `max_age=7 days` (matching `SIMPLE_JWT REFRESH_TOKEN_LIFETIME`).
2. `login_view` and `register_view`: set the cookie alongside the body tokens (body contract unchanged — backward compatible for API clients).
3. `refresh_view`: accept `request.data.get("refresh")` **or** the `refresh_token` cookie; on success set the rotated pair as the new cookie (rotation contract preserved).
4. `logout_view`: accept body **or** cookie, blacklist whichever is present, and **delete** the cookie on the response.
5. `change_password_view`: revoke-all already runs; also delete the cookie (every outstanding refresh token is dead server-side).

**TDD (RED first).** New `tests/security/test_refresh_cookie.py` (service-level + view-level, `pytest.mark.django_db`):
- login sets an HttpOnly refresh cookie with the auth path and SameSite=Lax;
- register sets the same cookie;
- refresh **with the cookie and no body** returns 200 + new access + a rotated cookie (old token blacklisted: a second refresh with the OLD cookie value 401s);
- body refresh still works (backward compat — existing `test_auth_api.py` stays green untouched);
- logout with the cookie (no body) blacklists it and expires the cookie;
- change-password expires the cookie.

**Done when:** the new suite is green; `pytest --reuse-db --no-migrations -q` overall count 519 → ~525 with 0 failures.

**Files:** `apps/core/views/auth.py`, new `apps/core/views/_refresh_cookie.py`, new `tests/security/test_refresh_cookie.py`. **Dependencies:** none.

---

## 2. Task 2 (E-1 frontend): refresh on cold 401 + truthful comments

**Problem.** Link 3 of the chain: `fetchWithAuth`'s `&& accessToken` guard plus the stale header comment.

**Fix.**
1. `src/lib/api-client.ts` — attempt refresh on any 401 (drop `&& accessToken`; the refresh request itself is a plain `fetch`, so no retry loop; on refresh failure clear auth and throw `ApiError(401)` exactly as today). Update the file header comment to describe the real design (access in module memory; refresh in the HttpOnly cookie set by login/refresh; browser replays it via `credentials: "include"`).
2. `src/providers/auth-provider.tsx` — no transport change required (the browser stores the login cookie automatically because `api.post` already sends credentials); comment only where it aids the next reader.

**TDD (RED first).** Extend `src/lib/__tests__/api-client-auth.test.ts`:
- a request with **no in-memory access token** that 401s still triggers the refresh POST and retries the original request with the new token (fails on the current `&& accessToken` guard — the E-1 link-3 regression test);
- refresh failure without an access token clears auth and throws `ApiError` with status 401 (existing behavior preserved).

**Done when:** vitest green (349 → ~351); `npm run typecheck` 0 errors; the e2e session spec (Task 3) passes against the live backend.

**Files:** `src/lib/api-client.ts`, `src/lib/__tests__/api-client-auth.test.ts`. **Dependencies:** Task 1 (for the live-backend verification only; unit tests are mock-based and land independently).

---

## 3. Task 3 (E-5 + session directive): e2e session-persistence spec

**Fix.** New `apps/web/e2e/session.spec.ts` (backend-gated exactly like `e2e/invoices.spec.ts` — `test.skip(!apiUrl, reason)`):
- real UI login → dashboard;
- `page.reload()` → **still authenticated** (URL stays `/dashboard`, the shell renders) — the user-visible acceptance test for E-1, impossible before this sprint;
- one more client-side navigation after the reload (sidebar link) to prove the session is functional, not cosmetic.

The spec performs **no financial writes** (same rule as the invoices spec). `playwright.config.ts` header comment gains one line documenting the session spec's gating (config-file touch per the directive; no behavioral change). Vitest additions shipped by Tasks 1-2 land through the existing `vitest.config.ts` include pattern (already picks up `src/**/__tests__`).

**TDD / verification.** RED: run the spec against the pre-remediation code once at this plan-validated state (capture: reload lands on `/login`). GREEN after Tasks 1-2. `npm run test:e2e` (no env) stays green — the new spec skips with a reason.

**Done when:** default suite green (9+1 passed, 4+1 gated skips); `npm run test:e2e:full` green including the new spec (login-rate budget: 8 UI logins/full-run now — still under the 10/min-per-IP limit; flush Redis if a run fails only on login).

**Files:** new `apps/web/e2e/session.spec.ts`, `apps/web/playwright.config.ts` (comment). **Dependencies:** Tasks 1-2 for GREEN; none for the RED capture.

---

## 4. Task 4 (E-2): documentation truth pass

Surgical edits, no rewrites:
1. `README.md` — "NUMERIC(10,4) Precision" row → NUMERIC(19,4); tests badge → the P4 counts; P4 milestone block (session persistence + suites); testing section gains the session spec.
2. `Project_Architecture_Document.md` — precision principle → NUMERIC(19,4); stale test metrics/endpoint counts corrected; header version/date bumped with a P4 note.
3. `CLAUDE.md` → v2.9.0 — status line + P4 milestone block (cross-reload persistence fixed; suite counts).
4. `AGENTS.md` — session-9 lessons appended (the three-link defect chain pattern: comment claims a cookie that no code ever set; `&& accessToken` guard blocks cold-reload refresh; e2e reload-persistence as the acceptance test).
5. `ledgersg_SKILL.md` → v1.4.0 — non-negotiable #2 wording ("Money is NUMERIC(19,4)" — the P3 leftover); debugging rows: replace the stale "Known limitation; widen when scheduled" overflow row with the real P3 state, add cookie-flow rows (login sets / refresh rotates / logout deletes; cold-reload refresh now works); project_state line; quick-ref additions.

**Dependencies:** Tasks 1-3 complete (claims must match executed evidence).

---

## 5. Task 5 (E-3 + E-4): root `.env.example` + deployment guide verification

1. **New root `.env.example`** — a short, truthful index: points to `apps/backend/.env.example` and `apps/web/.env.example`, lists the combined variable set with one-line purposes (backend: DEBUG, SECRET_KEY, DJANGO_SETTINGS_MODULE, ALLOWED_HOSTS, DB_*, REDIS_URL, CORS_ALLOWED_ORIGINS, RATELIMIT_ENABLE, DEBUG_TOOLBAR, CELERY_ALWAYS_EAGER, SENTRY_DSN, ADMIN_EMAIL — verified 15/15 by the D-4 audit; web: NEXT_PUBLIC_API_URL, BACKEND_URL, NEXT_OUTPUT_MODE — verified by B-4). No secret values. Committed to main per the directive.
2. **`docs/DEPLOYMENT.md`** — §1 auth description gains the cookie flow (login/refresh set + rotate the HttpOnly refresh cookie; logout/change-password delete it; cross-reload persistence is the verified behavior); §8 verification checklist gains the reload-persistence check; any command re-verified against the remediated tree (spot-executed during Task 6's dev-server phase).

**Dependencies:** Tasks 1-3 (the behavior being documented).

---

## 6. Task 6: screenshots, session log, worklog, report, commit & push

1. Dev servers (backend :8000 development settings, web `next dev`) + chromium; create the demo user/org/revenue account through the **public API** (register → create org → set default org → create REVENUE account) in `ledgersg_dev`; capture **5 new screenshots** into `docs/screenshots/` following the `NN_page_sessionN.png` convention → `19..23_*_session9.png` (login, dashboard, invoices list, new-invoice form, **dashboard after a full page reload — the E-1 evidence shot**), hash-unique PNGs.
2. `docs/session_9.md` — the session log (session_7 convention).
3. `worklog.md` (repo root) — session 9 record: audit findings, remediation table, gate evidence, deferred register.
4. `docs/REMEDIATION_2026-11-21_P4_REPORT.md` — the verification ledger (Verified/Reasoned/Assumed labels, reproduction commands).
5. Conventional commits on `main` per §7; push via `docs/ssh_git_wrapper_v3.py` with `--remote git@github.com:nordeim/ledgersg.git` (the wrapper's baked-in default is a stale different repo — always override) per `docs/how-to-git-push-using-ssh-wrapper_SKILL.md`; key deployed 0600 outside the repo, shredded after push.

---

## 7. Verification Gate (definition of done for the sprint)

Environment: PG :5432 (schema v1.1.0 in both DBs), Redis :6379, `DB_*` env per P3 report §4.

| # | Check | Expected |
|---|---|---|
| 1 | `pytest --reuse-db --no-migrations -q` | **0 failed**, 519 + ~6 new passed, 5 skipped |
| 2 | `pytest tests/invariants -q` / `pytest tests/security -q` | 20 passed / 32+6 passed, 3 skipped |
| 3 | `DJANGO_SETTINGS_MODULE=config.settings.testing python manage.py check` | 0 errors (1 known W001) |
| 4 | `ruff check` on touched backend files | no new findings |
| 5 | `cd apps/web && npm run typecheck` | 0 errors |
| 6 | `npm test` | 349 + ~2 new passed, 0 failed |
| 7 | `npm run test:e2e` (no backend env) | green — gated specs skip with reasons (10 total now) |
| 8 | `npm run test:e2e:full` (backend + Redis up) | green incl. the reload-persistence spec |
| 9 | Cookie flow (manual/live) | login response carries `Set-Cookie: refresh_token=…; HttpOnly; Path=/api/v1/auth/`; `curl` refresh with cookie + empty body → 200; reload keeps the session |
| 10 | Docs truth sweep | no "NUMERIC(10,4)" precision claims / "706|714 tests" / stale overflow rows in README, PAD, CLAUDE, AGENTS, ledgersg_SKILL |
| 11 | Root `.env.example` | present, truthful (per-var cross-check vs the two app templates) |
| 12 | Screenshots | 5 new non-empty unique PNGs (hash-verified) |
| 13 | `git status` clean; commit set matches §8 | all changes committed on main |

Claims labelled **Verified** / **Reasoned** / **Assumed** in the report.

---

## 8. Commit Plan (conventional commits, single branch `main`)

1. `feat(auth): HttpOnly refresh-cookie flow — set/rotate/delete + cookie fallback on refresh/logout (E-1 backend)`
2. `fix(web): refresh on cold 401 — cross-reload session persistence via the refresh cookie (E-1 frontend)`
3. `test(web): e2e reload-persistence spec (E2E_API_URL-gated) + playwright config note (E-5)`
4. `chore(env): root .env.example index for both apps (E-3)`
5. `docs: P4 truth pass — README/PAD/CLAUDE/AGENTS/ledgersg_SKILL + DEPLOYMENT cookie flow (E-2/E-4)`
6. `docs(worklog): session 9 worklog, session log, report + screenshots`

---

## 9. Deferred Debt Register (explicit, not silent)

Carried forward unchanged from `docs/REMEDIATION_PLAN_2026-11-21_P3.md` §4 unless touched here:

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
| B-6 frontend eslint debt (87 errors / 3,755 warnings; incl. `banking-client.tsx` `any`) | Pre-existing; dedicated sprint (large-diff risk) |
| F5 return rate-basis (computation date vs document date) | Deferred — period-cut semantics decision (ties into H-02) |
| A-10 stale root `requirements.txt` | Deferred (repo-owner coordination) |
| `test_api_endpoints.py` local fixture duplication | Deferred cleanup |
| Invoice form: existing-contact picker | Still deferred (backend supports reuse; searchable picker is feature work) |
| e2e login-rate budget (8 UI logins/full-run post-P4 vs 10/min-per-IP) | Documented in DEPLOYMENT.md §8; unchanged posture |
| ~~Cross-reload session persistence~~ | **RESOLVED this sprint (E-1)** — cookie flow + cold-401 refresh + reload e2e |

---

## 10. Open decisions resolved by this plan (recorded for the next reader)

- **Cookie-based vs body-based refresh persistence** (the P3 open question): cookie-based — mandated by the repo's own zero-JWT-exposure posture, already-credentialed CORS, and zero frontend transport changes. Body refresh stays supported for API clients (backward compatible).
- **Cookie scope:** `Path=/api/v1/auth/` (the browser never sends it to data endpoints — smallest exposure surface), `SameSite=Lax` (localhost:3000→localhost:8000 is same-site; document the `None`+`Secure` caveat for cross-site production topologies in DEPLOYMENT.md), `HttpOnly`, `Secure = !DEBUG`, `max_age = 7d`.
- **Directive interpretation — "add vitest and playwright test suite by modifying the respective config files":** both config files exist and are green (P2/P3, reproduced this session); the directive is satisfied by extending the suites through the existing configs (established include/gating patterns) + the one config-file touch where a comment documents the new gating. No gratuitous config churn (surgical-diff discipline).
