# LedgerSG — Remediation Plan (P16 Sprint: Production Truth — CSP Hydration, the Service-Path Middleware & the Deferred-Contract Sweep)

**Date:** 2026-11-26 (session 32)
**Base commit:** `d7f7d9b7` (main — post-P15, all gates green at 834P/0F/5S backend · 532/532 vitest · tsc 0 · eslint 9 · live e2e 40P/0F/0S · rls_smoke 13/13 · mobile-nav 17/17 · schema v1.2.0)
**Method for execution:** TDD (RED → GREEN → full gate) for every behavioural fix; lint parity on touched files; conventional commits on `main`; `skills/` excluded from all checks/tests/compilation; schema untouched this sprint (no DDL needed — every fix is application-layer).

---

## 1. Audit inputs (this session's evidence)

Three parallel deep audits (Mode C) + lead hand-verification of every
Critical/High finding in source, plus the live baselines reproduced:

- **Baselines reproduced** (fresh sandbox, environment rebuilt where recycled):
  backend 834P/0F/5S (invariants 34P, security 72P/3S — after restoring the
  `ledgersg_app` role password to the documented dev default
  `CHANGE_ME_IN_PRODUCTION`, which the session-30 smoke had rotated:
  environmental, not a code defect) · tsc 0 · vitest 532/532 (61 files) ·
  eslint 9 · mobile-nav live probe **17/17 PASS** (375/800/1280: toggle,
  closed-drawer `visibility:hidden`, overlay, X hit-target, transition-aware
  close, no overflow, no console errors, sticky tablet/desktop, the v4
  space-y trap sweep clean) — **the navigation works; no TailwindCSS v4 bug
  exists** (the P12/P13/P15 verdicts re-settled live; the v4 setup is
  CSS-first-clean: `@import "tailwindcss"` + `@theme`, no legacy config).
- **Backend audit** (P15 diff + surrounding services): 0 Critical, 2 High,
  6 Medium, 9 Low — every High/Medium verified in source by the lead.
- **Frontend audit** (api-client single-flight, shell/nav, hooks, configs):
  1 Critical, 3 High, 4 Medium, 6 Low — every Critical/High verified in
  source and build artifacts by the lead.
- **Cross-cutting truth audit** (every status claim vs the tree): 2 High,
  14 Medium, 9 Low — a consolidated stale-claims table drives §4.
- A display artifact was caught and dismissed per the P10/M-11 lesson
  (the bash tool ate `[h` in `a[href]` — the Read tool showed the bytes
  intact; no finding).

## 2. The findings (verified, with evidence anchors)

### Critical

**FE-C1 — the production CSP blocks Next.js's inline bootstrap scripts: the
shipped production app cannot hydrate.** `next.config.ts:75-77` — production
branch is `script-src 'self'` while every prerendered page in the actual
build output (`.next/server/app/*.html`, verified) carries 3 executable
inline scripts with NO nonce (`<script id="_R_">`, `self.__next_f.push(...)`
payloads). Browsers block them under the strict CSP → no hydration → the
router, in-memory-token auth, forms and queries are all inert server HTML.
The suite cannot catch it: every test runs against `next dev` (dev CSP
allows `unsafe-inline`), so the production CSP branch has zero coverage —
the exact "silently weakens in the untested quadrant" class. The P13/H-1
lesson (middleware headers override next.config headers — one source of
truth) governs the fix design.

### High

**BE-H1 — `config/settings/service.py` drops TenantContextMiddleware +
AuditContextMiddleware (+ CSP + WhiteNoise) while being the shipped API
entrypoint.** `service.py:99-108` rebuilds MIDDLEWARE from scratch and omits
all four; base.py:73-86 has them. The Docker/script path (`backend_api_service.sh`,
`docker/Dockerfile` gunicorn) serves the API with no org-context middleware →
every org-scoped endpoint 403s for non-superusers (fail-closed availability
outage), RLS sees NULL org on every request, and the audit trigger loses
ip/user-agent/path attribution. `test_settings_gates.py` covers only the
key gate — no middleware-presence gate exists.

**BE-H2 — `BulkAllocationSerializer` still enforces APPROVED-only: the
P14/H-2 instalment fix missed the wire endpoint.**
`apps/banking/serializers/allocation.py:221-224` rejects everything but
APPROVED while the service (`payment_service.py:473`) and the embedded-path
serializer (`serializers/payment.py:93`) accept
`("APPROVED","SENT","PARTIALLY_PAID","OVERDUE")`. `POST
/api/v1/{org}/payments/{id}/allocate/` 400s on a PARTIALLY_PAID invoice —
the exact defect P14/H-2 claimed to fix. The dead sibling
`AllocationCreateSerializer` (same stale check, zero consumers) compounds
the confusion.

**FE-H1 — the dashboard query key is inverted: all 10 mutation→dashboard
invalidations are no-ops.** `dashboard-client.tsx:63` uses
`queryKey: ["dashboard", orgId]`; every invalidation uses
`[orgId, "dashboard"]` (`use-invoices.ts:194,231,264,445`,
`use-banking.ts:100,254,288,355,459`). TanStack prefix matching requires
the key to START with the prefix → never matches. The dashboard shows stale
GST payable / receivables / cash after every mutation (staleTime 60s,
refetchOnWindowFocus disabled globally). The correct hook
`useDashboardMetrics` (`use-dashboard.ts`, key `[orgId,"dashboard","metrics"]`)
has zero importers. Unit tests assert the wrong-key convention too.

**FE-H2 — stale closure in `useCreateOrganisation.onSuccess`: the new org is
never selected; self-serve onboarding dead-ends.**
`use-organisation.ts:203-211` runs `refreshOrganisations()` then
`switchOrg(org.id)` — but `switchOrg` (`auth-provider.tsx:262-281`) reads
`organisations` from the closure captured at mutation time (the pre-creation
list). For a fresh registrant the list is `[]` → the `if (org)` guard
silently skips `setCurrentOrgId`, the query invalidation AND the
`set-default-org` persist → the dashboard renders the "No Organisation
Selected" dead-end until a manual reload. The p10 e2e only asserts the URL,
so the green suite hides it.

**FE-H3 — the frontend UEN validator rejects the ACRA "other entities"
format (LLPs, societies).** `shared/schemas/invoice.ts:13` —
`/^[0-9]{8,9}[A-Z]$/` accepts only the business (8-digit) and local-company
(9-digit) forms. The backend's own validator (`apps/core/validators.py`)
accepts all three ACRA forms incl. `T08LL1234A` (`^[TS]\d{2}[A-Z]{2}\d{4}[A-Z]$`),
and the repo's own e2e writes that exact LLP UEN. An LLP customer fails
invoice-form validation — the frontend is stricter than the backend on the
product's core market. A dead duplicate `isValidUEN` (`lib/utils.ts:112`,
zero importers) carries the same wrong regex.

### Medium (backend)

- **BE-M1** — payment-amount cap TOCTOU: `allocate()` locks the DOCUMENT
  rows (`select_for_update`, payment_service.py:459) but never the PAYMENT
  row; two concurrent allocations against different documents each read
  `already_allocated = 0` and can jointly exceed the payment amount.
  Fix: `Payment.objects.select_for_update().get(...)` at the top of `allocate()`.
- **BE-M2** — `NaN`/`Infinity` box overrides can be filed into the statutory
  record: `gst/views.py:393-395` parses `Decimal(str(v))` (NaN/Infinity parse
  fine), `return_service.py:347-352` catches only TypeError/ValueError/
  ArithmeticError, the serializer's `boxes` child is untyped; non-derived
  boxes (e.g. box9) pass every CHECK and persist into a FILED return.
  Fix: reject non-finite values at the override seam + harden `money()`.
- **BE-M3** — `quantity × unit_price` can overflow NUMERIC(19,4) → unhandled
  500 (DataError at INSERT). Individual bounds (M-4) permit a 19-integer-digit
  product; the column holds 15. Fix: bound the product in
  `InvoiceLineCreateSerializer.validate` (and in `add_line`'s path).
- **BE-M4** — payment create + allocate is two transactions
  (`banking/views.py:281-293` and `324-336`): an allocation 400 leaves the
  payment + journal entry committed — money recorded, nothing allocated,
  response says failed. Fix: one service-level atomic method.
- **BE-M5** — `InvoiceLineAddView` silently drops `discount_pct`
  (`invoicing/views.py:397-406` forwards every field EXCEPT it; the
  document-create path forwards it): the same payload yields a discounted
  line via one endpoint and an undiscounted line via the other.
- **BE-M6** — system tax-code rows: `update_tax_code` permits description/
  is_active edits the RLS policy's WITH CHECK then refuses (InsufficientPrivilege
  → unhandled 500 under the app role; tests pass because they never run
  under RLS). `deactivate_tax_code` already refuses system rows — align.
  (The policy's row-capture gap — an UPDATE could set org_id to capture a
  system row — is latent defense-in-depth; the API serializer cannot set
  org_id. Register the schema note; fix the service this sprint.)

### Medium (frontend)

- **FE-M1** — open redirect via `?redirect=` on login (`login/page.tsx:40-42`
  pushes the param verbatim): post-auth phishing vector (CWE-601). Fix:
  same-app targets only.
- **FE-M2** — mobile drawer locks body scroll with no visible escape after
  resizing to desktop: the lock keys off `sidebarOpen` only; at ≥md the
  overlay and X are `md:hidden` but `overflow:hidden` persists. Fix: release
  the lock + close the drawer on breakpoint crossing (matchMedia).
- **FE-M4** — the e2e DB-safety contract lives in an npm script
  (`--workers=1` in `test:e2e:full`) not the config
  (`fullyParallel: true`): `npx playwright test` with E2E_API_URL set races
  the p11 check-then-create helpers. Fix: encode serial semantics in the
  config.

### Low (selected — the ones that carry correctness weight; the rest ride the register)

- **BE-L1** — raw `.quantize()` (HALF_EVEN) on three payment FX paths instead
  of `money()` (HALF_UP) — sub-cent drift; fix with the money() hardening in BE-M2.
- **BE-L2** — allocation release resets fully-unallocated documents to
  APPROVED even when they were SENT/OVERDUE — the "billed" state is
  irreversibly erased by an allocate→unallocate cycle. Fix: restore the
  pre-allocation status (evidence-based; see task B8 for the mechanism).
- **BE-L3** — `file_return`/`amend_return` lack `select_for_update` —
  concurrent file/amend interleave. Fix: row lock inside the atomic block.
- **BE-L4** — CSV import latin-1 fallback is dead code (the utf-8 attempt
  consumed the stream; the second `read()` returns `b""` → non-UTF-8 files
  silently import 0 rows). Fix: read bytes once, decode twice.
- **BE-L5** — duplicate audit rows for payments (the `trg_audit_payment`
  trigger AND manual `AuditEventLog.objects.create` in PaymentService).
  Fix: drop the manual writes (trigger coverage is the schema's truth).
- **BE-L7** — org-create validates `uen.strip().upper()` but stores the raw
  value (case-sensitive UNIQUE pre-check dodge). Fix: write the normal form back.
- **BE-L8/L-9** — period_lock docstring overstates the payment-void wiring +
  the advertised payment-void test doesn't exist; `timezone.now().date()`
  vs `timezone.localdate()` inconsistency between the two void paths
  (00:00–07:59 SGT divergence). Fix both with the real lock test.
- **FE-L1** — `allowedDevOrigins` missing despite the repo's own documented
  trap (dev chunks blocked on the 127.0.0.1 origin). One-liner.
- **FE-L2/L-3** — dead code cluster (`use-dashboard.ts` both hooks unused —
  fixed by consuming `useDashboardMetrics` in FE-H1; `createQueryHooks`;
  `isValidUEN` — fixed by FE-H3; `debounce`/`generateId`/`truncateText`/
  `sleep`; the dead `[orgId,"peppol"]` invalidation key).
- **FE-L4/L-5** — focus-trap selector omits input/select/textarea/[tabindex]
  (complete for today's contents, fragile for tomorrow's) + the drawer
  implements the full modal contract without `role="dialog"`/`aria-modal`.
- **FE-I-1** — the single-flight refresh's shared-FAILURE path is untested
  under concurrency (one test to add: 3 parallel 401s + failing refresh →
  3 ApiError rejections, exactly 1 refresh call, auth cleared).

### Docs & hygiene (the cross-cutting truth audit)

Consolidated stale-claims table (all file:line verified):
CLAUDE.md:6 (750P/530 → 834P/532) · README Test-Suites section (1320/750/530
→ 1406/834/539...) — five lines · README badges + tech tables (Django
6.0.2→6.0.10, Next 16.1.6→16.4.6, DRF 3.16.1→3.18.3, zod 4.3.6→4.6.7,
WeasyPrint 68.1→70.0) · README "Redis optional for development" (it is a
hard dev prerequisite) · README clone URL (ledgersg/ledgersg → nordeim/ledgersg)
· README env table (`DATABASE_URL` unread; `DB_*` omitted; reserved
`NEXT_PUBLIC_ENABLE_*` presented as functional) · README file map listing
the removed `middleware.ts` · DEPLOYMENT.md:260 (518→532 vitest) ·
DEPLOYMENT.md missing the §17 (v1.2.0 RLS) upgrade note for existing
databases (only §16 is documented) · API guide's stale "Current Test
Metrics" block + the nonexistent `POST /gst/register/` path (the real route
is `POST /api/v1/{org_id}/gst/`) + four undocumented high-traffic endpoints
· ledgersg_SKILL tech-stack table + the "current state" block (750/27/66/530
→ 834/34/72/532) · Current_Project_Status.md is a March-era fossil under a
"Current" name (banner + rename) · 7 tracked log files (root + docker/) incl.
one embedding a PGPASSWORD export · backup/ + plan/ (49 files, 2.4MB zip)
tracked despite .gitignore listing both · CI comment (750+/P13 → 834/P15)
· PAD "Key Metrics (P13)" label over P15 values · v0.3.2-vs-v0.3.3 + "30
domain tables" + §4b cross-ref + the zombie session-persistence roadmap
item · PLAYWRIGHT_BASE_URL undocumented in apps/web/.env.example.

**Registered (NOT fixed this sprint — the deferred debt register):** the
ContactPicker WAI-ARIA combobox pattern (FE-M3 — a real a11y gap, but a UI
project; next sprint's first item), backend list pagination (BE-L6 — API
contract change), the ruff register re-baseline (current truth: 1216
whole-backend / 735 production findings, ~75% mechanical; house style
remains touched-file parity — the DOCUMENTED count gets corrected this
sprint so the register is honest), the coverage-exclude blind spots
(FE-L6), the audit-log INSERT `WITH CHECK (TRUE)` forgery surface +
tax-code policy row-capture note (schema-tier hardening, pairs with the
registered M-7-full Peppol encryption item), plus everything carried
forward from the P15 register (UEN checksum, H-3 DB trigger layer, H-05b
attachment model, M-2/M-3/M-6b/M-8/M-9, audit2 M-01..M-08, B-3/B-4/B-8/
B-9/B-12/B-15..B-19, the frontend L-batch, the 9 eslint findings).

## 3. Execution plan (TDD; ordered by risk, then dependency)

### Phase 0 — the production-truth headline (FE-C1)

- **F1. CSP nonce via `proxy.ts`** (the Next 16 pattern): per-request nonce
  (crypto random, base64), CSP header set on BOTH the request (so Next
  applies the nonce to its bootstrap scripts) and the response; the
  production `script-src` becomes `'self' 'nonce-<n>' 'strict-dynamic'`;
  the DEV branch keeps `'unsafe-eval' 'unsafe-inline'` (dev overlays).
  **Single source of truth (the P13/H-1 lesson): the CSP block MOVES OUT of
  `next.config.ts` headers entirely** — every other header stays there.
  `style-src` keeps `'unsafe-inline'` (React `style=` attributes are
  CSP-governed without it; Next auto-nonces only its OWN generated style
  tags — the documented compromise; script-src is the XSS-critical
  directive). **Nonces require dynamic rendering** (verified against the
  bundled Next 16 guide + the prerender manifest: all 15 routes are
  currently static shells): the root layout opts the app into
  `dynamic = "force-dynamic"` — the per-request render cost is a thin
  server-component shell for a login-gated dashboard app (acceptable, the
  documented trade). A unit test gates the strategy table; a **new
  production smoke script** (`scripts/prod-csp-smoke.js`) builds
  standalone, boots it on a scratch port, loads a page in chromium and
  asserts (a) the served CSP header carries a nonce, (b) hydration
  happened (the Next router marker), (c) zero console violations — the
  gate class the dev-mode suite structurally cannot cover.

### Phase 1 — backend contracts (each task: RED test → GREEN fix → suite)

- **B1 (BE-H2):** replace the APPROVED-only literal in
  `BulkAllocationSerializer` with the shared `ALLOCATABLE_STATUSES`; delete
  the dead `AllocationCreateSerializer`; endpoint-level RED test first
  (allocate against a PARTIALLY_PAID document through the VIEW → 201).
- **B2 (BE-M1):** `select_for_update` on the Payment row at the top of
  `allocate()`; RED test = a seed-wrapper probe proving the payment row is
  locked (the P15 pattern for lock assertions) or the cap under
  transaction interleaving.
- **B3 (BE-M4):** one atomic service method `create_received_with_allocations`
  / `make_...` consumed by both views; RED test = allocation failure rolls
  the payment + journal entry back (0 payments, 0 JEs after the 400).
- **B4 (BE-M2 + L1):** `money()` rejects non-finite (NaN/Inf) with the
  typed error; the box-override seam validates `is_finite()`; the three
  `.quantize()` FX paths move to `money()`. RED tests: NaN and Infinity
  overrides → 400 (not a FILED NaN); `money("NaN")` raises.
- **B5 (BE-M3):** the line-total bound (`quantity * unit_price` ≤
  `Decimal("99999999999999.9999")`) in `InvoiceLineCreateSerializer.validate`
  (mirrored in `add_line` for the view path); RED test = in-bounds fields,
  out-of-bounds product → 400.
- **B6 (BE-M5):** forward `discount_pct` in `InvoiceLineAddView`; RED test =
  the same payload through both endpoints yields the same line amount.
- **B7 (BE-M6):** `update_tax_code` refuses system rows (mirror
  `deactivate_tax_code`); RED test = PATCH a system row → the typed 400,
  not InsufficientPrivilege.
- **B8 (BE-L2):** allocation release restores the pre-allocation status:
  persist the status at first allocation — investigate the existing
  evidence (`sent_at`-class columns / status history) during execution; the
  smallest honest mechanism wins; RED test = allocate→unallocate a SENT
  document → SENT, not APPROVED.
- **B9 (BE-L3):** `select_for_update` in `file_return`/`amend_return`.
- **B10 (BE-L4):** CSV decode fallback reads the bytes once, tries utf-8
  then latin-1; RED test = a latin-1 statement file imports its rows.
- **B11 (BE-L7):** org-create writes the normalised UEN back; RED test =
  `"12345678a"` stores `"12345678A"` and the collision pre-check catches
  the case-variant.
- **B12 (BE-L8/L9):** the payment-void GST-lock test (the advertised-but-
  missing spec) + `timezone.localdate()` in the payment void path + the
  period_lock docstring corrected.
- **B13 (BE-L5):** drop the manual PaymentService audit writes (the
  trigger is the truth); test = one payment mutation → one audit row.
- **B14 (BE-H1):** `service.py` derives MIDDLEWARE from base (list copy —
  base has no debug_toolbar; the from-scratch list was drift); settings-gate
  RED test first: every HTTP-serving settings module (base, development,
  production, service) MUST contain TenantContextMiddleware +
  AuditContextMiddleware (+ CSP + WhiteNoise on the paths that serve
  static/API).

### Phase 2 — frontend contracts (vitest RED → GREEN; e2e where live)

- **F2 (FE-H1):** `dashboard-client.tsx` consumes `useDashboardMetrics`
  (the dead hook with the CORRECT key — deletes the dead code AND fixes the
  key in one move); RED test = the invalidation after a payment mutation
  refetches (assert the query-cache invalidation contract); update the
  wrong-key test convention.
- **F3 (FE-H2):** the provider exposes `selectOrgById` (no list-state read)
  used by the create path (setCurrentOrgId + invalidate + persist); RED
  test = create org → currentOrgId is the new org (jsdom, mocked api).
- **F4 (FE-H3):** the shared UEN regex mirrors the backend's three ACRA
  forms (`/^(?:\d{8}[A-Z]|\d{9}[A-Z]|[TS]\d{2}[A-Z]{2}\d{4}[A-Z])$/`);
  delete the dead `isValidUEN`; RED tests = T08LL1234A passes, the
  branch-registration 10-digit form still fails.
- **F5 (FE-M1):** the login redirect guard (same-app paths only; `//host`
  and absolute URLs fall back to /dashboard); RED test table.
- **F6 (FE-M2):** the drawer closes + the scroll lock releases on crossing
  into ≥md (matchMedia change listener, cleanup correct); vitest with a
  mocked matchMedia.
- **F7 (FE-L1):** `allowedDevOrigins: ["127.0.0.1"]` in next.config.ts.
- **F8 (FE-L2/L3 + I-1):** dead-code sweep (`createQueryHooks`, `ClientOnly`,
  the unused lib/utils helpers, the dead `[orgId,"peppol"]` invalidation
  key) + the single-flight shared-FAILURE concurrency test (3 parallel
  401s, failing refresh → 3 rejections, 1 refresh call, auth cleared).
- **F9 (FE-L4/L5):** the shared `getFocusable()` selector (a[href], button,
  input, select, textarea, [tabindex]:not([tabindex="-1"]) — visibility-
  filtered) used by the trap + a planted-input unit test; `role="dialog"`
  `aria-modal="true"` on the open mobile aside.
- **F10 (FE-M4):** the e2e contract moves into `playwright.config.ts`
  (`fullyParallel: false`; the live project runs serial) so the npm script
  is convenience, not the only guard.

### Phase 3 — the docs truth pass + hygiene (no code behavior)

- **D1:** every row of the stale-claims table (§2) fixed across CLAUDE.md,
  README.md, ledgersg_SKILL.md, PAD, AGENTS.md (status header already
  truthful), API_CLI_Usage_Guide.md, docs/DEPLOYMENT.md, ci.yml comments;
  Current_Project_Status.md gets the SUPERSEDED banner + dated rename.
- **D2:** DEPLOYMENT.md gains the §17 application snippet (the idempotent
  DO blocks for existing v1.1.0 databases) + the prod-CSP smoke step in the
  verification section; API guide gains the corrected route + the four
  undocumented endpoints (receive/make payments, bank-transactions import,
  gst returns deadlines, journal-entries ledger).
- **D3:** `.env.example` (web) documents PLAYWRIGHT_BASE_URL +
  PLAYWRIGHT_PROJECTS; re-verify all three templates against the code.
- **D4 (hygiene):** untrack the 7 log files + the backup/ zip + plan/*.md
  (the .gitignore already declares the intent; `git rm --cached` keeps the
  local copies), add `*_log.txt` to .gitignore, correct the P11
  "tracked logs removed" over-claim in the status docs.
- **D5:** the ruff register's documented count corrected to the measured
  truth (1216 whole-backend / 735 production; touched-file parity
  unchanged).

### Phase 4 — the full verification gate + deliverables

- Backend: `pytest --reuse-db --no-migrations -q` (baseline 834P + the new
  tests, 0 failed), invariants, security, `manage.py check`, ruff parity on
  touched files.
- Frontend: tsc 0, vitest (532 + the new specs), eslint parity (≤9),
  coverage green at both ratchets, `build:server`.
- **NEW: the prod-CSP smoke (F1) green** — the gate that would have caught
  FE-C1.
- e2e default (11P + 29 gated) + live `test:e2e:full` (40P/0F/0S) against
  the daemonized stack; `rls_smoke` 13/13 as `ledgersg_app`; the mobile-nav
  probe 17/17 re-run AFTER the shell.tsx edits (F6/F9 touch that file).
- Screenshots: the remediated surfaces (8+) → `docs/screenshots/
  88-*_session32.png` ff., pixel + DOM verified, md5-unique.
- `.env.example` truth-checked; `worklog.md` + `docs/session_32.md` + the
  P16 report; conventional commits on `main`; push via the SSH wrapper.

## 4. Risks & mitigations

- **The nonce mechanism** (Next applying the request-CSP nonce to its
  scripts) is framework-documented but must be proven in THIS repo's
  standalone build — the smoke script is the proof; if the mechanism fails,
  the fallback is `'strict-dynamic'` with a documented hash/allowlist review
  (never a silent `unsafe-inline` in production).
- **B8's status restoration** may lack an evidence column — if so, the
  mechanism stores the pre-allocation status on the payment allocation
  (app-layer only; no DDL this sprint) or registers the design honestly.
- **The middleware gate test** must import service.py WITHOUT importing
  development.py in the same process (the P10/LG-4 copy-on-write lesson);
  isolate per-module in subprocess assertions if needed.
- **e2e serialisation** (F10) slows the default suite marginally — the
  default path has no shared backend state, so `fullyParallel` stays for
  the no-backend project; only the gated live specs serialise.
- Every fix lands with its RED test committed in the same logical commit;
  no test is deleted or weakened to pass (the wrong-key vitest convention
  gets CORRECTED, not removed — it asserted the bug).
