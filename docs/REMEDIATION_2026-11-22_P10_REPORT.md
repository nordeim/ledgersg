# LedgerSG — Remediation Report (P10 Sprint: Self-Serve Loop & Compliance Truth)

**Date:** 2026-11-22 → 2026-11-23 (session 20)
**Base commit:** `e37f12f0` (main)
**Plan:** `docs/REMEDIATION_PLAN_2026-11-22_P10.md`
**Source audit:** post-P9 audit re-verified in source with line numbers before
planning (scanner pass per `skills/skills-catalog.md` — all hits in the
documented FP classes — plus three parallel deep-audit agents; every
Critical/High finding re-confirmed against the working tree before
execution). The live e2e phase then surfaced FIVE additional production
defects the mocked gates structurally could not see (see §2, Tasks 18–19):
the anonymous-401 register bounce, the rate-limit 403 masquerade, the
dev-budget blocker, the settings copy-on-write cascade, and the UEN 500.
**Method:** TDD (RED → GREEN → full gate). Every production-code fix has a
regression test that failed for the documented reason before the fix and
passes after: **19 new backend tests + 51 new vitest tests + 5 new e2e
specs, all RED first.**
**Session incidents (recovered, zero loss):** the sandbox was recycled twice
mid-sprint; Tasks 1–16 were pushed incrementally and survived, the
environment (PG data, Redis, venvs, playwright) was rebuilt from the
documented runbooks, and the uncommitted Task-17 work was redone against the
pushed state.

---

## 1. Verification Ledger (executed evidence)

| Gate | Result |
|---|---|
| Backend `pytest --reuse-db --no-migrations -q` | **687 passed, 0 failed, 5 skipped** (668 P9 baseline + 19 new) |
| `pytest tests/invariants -q` | 27 passed (schema conformance + capacity + balance) |
| `pytest tests/security -q` | 55 passed, 3 skipped (RLS, tokens, cookies, posture gates) |
| Frontend `npx tsc --noEmit` | 0 errors |
| Frontend `npx vitest run` | **505/505 passed** (454 P9 baseline + 51 new) |
| `npm run test:coverage` | green at the honest measured-floor ratchet (P10/M-13) |
| `npm run build:server` | green — the ONLY build mode (P10/M-12 retired the export) |
| `npm run test:e2e` (no backend) | **11 passed, 20 gated with reasons** |
| `npm run test:e2e:full` (live stack) | **30/30 passed, 1 data-conditional skip — two consecutive fully-green runs** |
| Screenshots | 6 new (53–58_session20), all content-verified (element waits + pixel ratio) |
| Ruff (backend touched files) | exact parity with base — 4 fewer F405 (explicit re-bindings) |
| eslint (frontend touched files) | exact parity with base |
| Production posture gates | base `LOGIN_RATELIMIT_USER` still 30/min (asserted by test); anon/user DRF rates unchanged in base |

## 2. What Was Fixed

### The planned register (Tasks 1–17)

| # | Finding | Fix | Evidence |
|---|---|---|---|
| H-1 | Every invoice-form submission created a contact — repeat invoicing duplicated UEN-less customers and 409'd on repeat UENs | Two-mode Customer card: select-existing (default; `pickedContactId` drives the submit payload; no contact row created) or explicit new-customer; `ContactPicker.onSelect` mirrors the row into the zod-satisfying form state; `validateSubmissionReadiness` understands both modes | 6 vitest (RED: the duplicate POST fired) + the e2e wire assertion (picking issues ZERO createContact requests) |
| H-2 | The login page's "Create account" link was a dead `href="#"`; `POST /auth/register/` had zero frontend consumers — a self-serve user could not enter the product | `/register` page (12-char floor in markup), routes org-less fresh accounts to the P9 org-creation page; login links fixed; dead "Forgot password" removed | 8 vitest + 2 e2e render specs + the live self-serve loop spec |
| H-3 | The GST F5 File button POSTed a return that was always DRAFT (compute never wired); review/amend endpoints had zero callers; deadlines endpoint unconsumed | The F5 tab ships the whole lifecycle: create-periods dialog, compute, manager-gated review, file, amend, View-boxes panel, and the next-filing deadline banner — all against the real endpoints | 3 backend (route RED 404) + 5 vitest |
| M-1 | Bank-account UPDATE serializer rejected null/`""` PayNow where CREATE accepted it; a dangling pair (type without id) was silently stored | Mirror of the create contract in the update path incl. partial-PATCH effective-pair semantics (the view now passes the instance) | 3 backend (RED verbatim) |
| M-2 | `transition_status` VOID without `user_id` raised a bare 500 (`KeyError`-shaped) — the seam failed OPEN | The VOID branch fails closed: user_id required with a clean 400 naming the field | 1 backend (RED) |
| M-3 | The chosen organisation reset on every reload — `set-default-org` existed with zero callers | `switchOrg` persists fire-and-forget (a failed POST keeps the local switch) | 2 vitest (RED: no POST fired) |
| M-4 + L-6 | Transmission errors read keys the backend never sends; null-contact suggest-match rows crashed the render | Real key mapping + null-safe rows | 1 backend + 2 vitest |
| M-5 | Full contact CRUD existed in the backend with zero UI — a wrong Peppol ID/email (required for InvoiceNow) could never be corrected | `/contacts` page: search, type filters, edit dialog, deactivate with confirm; nav entry | 8 vitest + 1 e2e |
| M-6 | Bank accounts could be created but never edited or deactivated | Per-row Edit (prefilled; account number/currency/gl immutable per the backend contract) + deactivate confirm | 7 vitest |
| M-7 | Payment allocations were invisible (the serializer didn't even expose them) | Read-side allocation schema + payments-list allocation rows with a toggle | 1 backend + 3 vitest |
| M-8 | Fiscal periods could be closed but never opened — the approval error named an action no endpoint could perform | `POST /fiscal-periods/{id}/open/` (manager-gated) + the settings FiscalCard (create year, close/open periods) | 3 backend (route RED 404) + vitest |
| M-9 | The settings profile card claimed a change-password endpoint existed — it didn't | `POST /auth/change-password/` + the Change Password card (old/new/confirm; the backend expires the refresh cookie) | vitest (card RED) |
| M-10 | The InvoiceNow settings PATCH's error referenced a surface that didn't exist | The InvoiceNow settings card (participant id, AP config) against the real PATCH | vitest (RED) |
| M-11 | CI trigger "corrupted" (`branches: ain]`) | **Corrected record:** the file was never corrupt — the finding was a tool-display artifact that eats the `[m` byte sequence in rendered output; verified against raw bytes (`od -c`) at both the pre-fix and post-fix commits. The corrective commit documents the honest history | `git show` + od ground-truth |
| M-12 + M-13 | The static-export build was already broken (detail routes cannot `generateStaticParams` live IDs) yet still documented as a supported mode; the vitest 85% coverage gate had never passed (actual ~63%) | Export mode retired (config + scripts); standalone is the only build; the coverage ratchet sits at the measured floor (62.88/52.33/51.97/63.19) so it gates regressions without lying | build:server green; coverage green |
| L-1..L-5, L-7 | Quote back-links lied (variant-blind); dead Load-more buttons; the allocation section queried invoices unconditionally; the import result read a phantom wire shape; payment filters mislabelled; the banking page lacked its Suspense boundary | Truth batch, each with the test updated to the real contract | vitest suite green |

### The live gate's own findings (Tasks 18–19 — found by running the product)

| # | Finding | Fix | Evidence |
|---|---|---|---|
| LG-1 | The auth-provider's mount-time `checkSession` treated the anonymous 401 (an unauthenticated visitor on `/register` gets it from `/auth/me`) as session expiry → `clearAuth` + redirect to `/login`. The registration form only ever worked by winning that race; the e2e click landed mid-navigation ("element detached") | Public auth pages (`/login`, `/register`) are exempt from the redirect | 1 vitest (RED: the redirect fired) + the live loop now deterministic |
| LG-2 | django-ratelimit's blocked requests raise `Ratelimited` — a bare `PermissionDenied` subclass — which fell through DRF's fallback as **403 "You do not have permission to perform this action."**, indistinguishable from a real authz failure (the frontend api-client treats 403 as auth failure and bounces to /login). Reproduced: a 35-login burst tripped at #30 with exactly this body | `custom_exception_handler` maps `Ratelimited` to the documented **429 `rate_limit_exceeded`** contract (code/message/retry_after + `Retry-After` header) | 1 vitest-equivalent backend test (RED: 403 shape) + the API burst re-run all-200 |
| LG-3 | `LOGIN_RATELIMIT_USER` (30/min, `user_or_ip` = the IP for anonymous logins) was the third knob the P4/P6 pass missed — the grown e2e suite's tail tripped it | Development raises the budget to 120/min (production base 30/min unchanged, asserted) | 1 backend test (RED) |
| LG-4 | `development.py` mutated the shared base `INSTALLED_APPS`/`MIDDLEWARE`/`LOGGING` in place — importing it under other settings (the knob test does) injected debug_toolbar mid-run and crashed middleware loading (`HistoryEntry isn't in an application in INSTALLED_APPS`) — a 79-test cascade | Copy-on-write, per the file's own documented REST_FRAMEWORK rule | The cascade reproducer green; suite 687/5 |
| LG-5 | `core.organisation.uen` is UNIQUE at the DB level but nothing validated it — a taken UEN surfaced as an unhandled IntegrityError **500** on org-create AND both PATCH paths (the detail PATCH is a raw allowlist with no serializer) | `ensure_uen_available()` guards all three paths (blank skips — see the debt register); clean 400 field error | 2 backend tests (RED: IntegrityError 500) |
| LG-6 (spec hygiene) | The banking statement spec depended on the bootstrap customer being named "Marina" (a P9-era fixture name); the quotes/contacts headings strict-mode-resolved twice (a shell breadcrumb `h2` duplicated each page's `h1`); the invoices list's empty state adds a second "New Invoice" link in main | Run-unique statement description/reference; the breadcrumb demoted to an aria-hidden div (one h1 per page — also the a11y fix); `.first()` on the CTA | The live gate green twice consecutively |

## 3. Deferred Debt Register (explicit — nothing silently dropped)

Carried forward from P9 unchanged (see the P9 report §3): H-02 base-currency
reporting; M-1 audit-event READ surface; M-10 CSRF Origin-check; M-11 CSP
verification in standalone mode (narrowed by M-12 — headers now served via
`next.config` `headers()`; verify in P11); H-07 backend ruff debt; frontend
eslint debt (parity); F5 rate-basis; `pay_return` payment tracking; full PINT
Schematron; ledger pagination; invoice `update_line`; B6 list-envelope
standardization; aged netting; quote-lifecycle DB enum; trial-balance
zero-activity + fiscal-year mode; reports export; TAX-group coarse type;
Storecove authenticate semantics (M-14); dashboard trends endpoint; CoA
management page; Reg-11 remainder.

**New from P10:**

- **Blank-UEN schema modeling** (from LG-5): the DB column is
  `VARCHAR(20) UNIQUE` and the ORM writes `''` for blank — two orgs without
  a UEN collide at the DB (multiple NULLs would not). The serializer guard
  deliberately skips blanks, so the second blank-UEN org still 500s. Fix
  needs the null-vs-blank decision (model `null=True` + `''`→None
  normalization + the wire-contract change `""`→`null` in org responses +
  frontend type alignment) — its own task, not a rider.
- **E2E live-gate bootstrap as a repo script:** the bootstrap sequence
  (demo user → org → approved invoice) is documented in
  `docs/DEPLOYMENT.md` §9 but shipped as session tooling, not a committed
  script. P11 candidate: `apps/web/e2e/bootstrap.ts`.
- **Coverage ratchet headroom:** the gate sits at the measured floor;
  ratcheting upward (a few points per sprint) beats a jump to an aspirational
  number.

## 4. How to Verify (reproduction commands)

```bash
# Prerequisites: PG on :5432 (schema v1.1.0 loaded into ledgersg_dev AND
# test_ledgersg_dev), Redis on :6379, backend venv (uv sync --all-extras),
# web node_modules (npm ci), playwright chromium.
# ALWAYS --reuse-db --no-migrations (the documented invocation is the contract).

cd apps/backend
export DB_NAME=test_ledgersg_dev DB_USER=ledgersg DB_PASSWORD=... \
       DB_HOST=127.0.0.1 DB_PORT=5432 REDIS_URL=redis://127.0.0.1:6379/1
pytest --reuse-db --no-migrations -q        # 687 passed, 5 skipped

cd ../web
npx tsc --noEmit                            # 0 errors
npx vitest run                              # 505/505
npm run test:coverage                       # green at the ratchet
npm run build:server                        # green (the only build)
npm run test:e2e                            # 11 passed, 20 gated

# The live gate (bootstrapped dev DB — see DEPLOYMENT.md §9 for the demo
# user/org/invoice sequence; serial workers):
E2E_API_URL=http://127.0.0.1:8000 E2E_DEMO_EMAIL=demo@ledgersg.sg \
E2E_DEMO_PASSWORD=demo1234pass npm run test:e2e:full
# 30 passed, 1 data-conditional skip

# LG-2 spot check (the 429 contract): burst past a rate limit —
# the response is 429 rate_limit_exceeded with Retry-After, never a raw 403.
# LG-5 spot check: POST /api/v1/organisations/ with a taken UEN -> 400 {"uen": [...]}
```

## 5. Commits

All on `main`, pushed via the SSH wrapper with remote-ref verification:

```
a5fd6cc0 feat(web): registration page — the self-serve loop closes (P10/H-2)
cc3b4b78 fix(web,invoicing): invoice form picks real contacts — no duplicate rows (P10/H-1)
80eb5f90 feat(web): contacts management — list, edit, deactivate (P10/M-5)
03c322e0 feat(web,gst): the F5 tab tells the whole truth — boxes, periods, review/amend, deadlines (P10/H-3)
d011d1d8 fix(banking): update-serializer PayNow parity — null/"" stored, dangling pair refused (P10/M-1)
98e47271 fix(invoicing): the VOID seam fails closed — user_id required with a clean 400 (P10/M-2)
a460835e fix(web,api): the chosen org survives the refresh — set-default-org wired (P10/M-3)
333b6407 test(web): holder object for the switchOrg probe — react-hooks/globals parity (P10/M-3 follow-up)
0fe22c43 fix(peppol,web): transmission errors read the real keys; null-contact rows render (P10/M-4, L-6)
e3ee33bd feat(web): bank-account edit + deactivate (P10/M-6)
a16905ca feat(web): payment allocations visible (P10/M-7)
6dbe6e7b feat(core,web): fiscal periods can be opened — endpoint + settings card (P10/M-8)
a1d8edbf feat(web): change password + the profile-card truth (P10/M-9)
850f832a feat(web): InvoiceNow settings card (P10/M-10)
508e67fc fix(ci): the trigger actually gates — branches [main] (P10/M-11)
b1d01b23 docs(ci): correct the M-11 record — the trigger was never corrupted
8f7b5a2e chore(web): build-mode truth — export retired, coverage ratchet, Suspense (P10/M-12, M-13, L-7)
78ae5796 fix(web): truth/UI batch — quote back links, dead load-more, allocation gate, import rows, filter labels (P10/L-1..L-5)
de9f1b3d fix(core): rate-limited requests tell the truth (429) + the dev budgets the live gate needs (P10 live gate)
ad061203 fix(core): organisation UEN uniqueness is a clean 400, not an IntegrityError 500 (P10 live gate)
fa6a7232 fix(web,e2e): the self-serve loop survives its own session check + P10 specs (P10 live gate)
889109ba docs(screenshots): session 20 captures of the P10 surfaces (53-58)
0c65d944 docs(env): .env.example truth pass — standalone is the only build mode (P10)
```

Plus the closing docs commit (this report, the session-21 log, the worklog
entry, README/PAD/AGENTS/SKILL truth pass).
