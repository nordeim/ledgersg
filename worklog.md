# LedgerSG — Worklog

## 2026-11-23 — Session 23: P11 Sprint (Accounting Truth & Config Honesty)

**Base:** `1b3e267d` (main) · **Plan:** `docs/REMEDIATION_PLAN_2026-11-23_P11.md` · **Report:** `docs/REMEDIATION_2026-11-23_P11_REPORT.md` · **Session log:** `docs/session_23.md` (the first half's raw log: `docs/session_22.md`)

### Continuation across a context outage (zero loss)

The sprint was cut mid-Task-1 by a context-window outage; the workspace,
PG data, Redis, dev servers and the saved plan all persisted. The in-flight
test-fixture patch was completed on resume; all 17 commits were made after
the resume and gated before the push. Baselines reproduced exactly before
any change (backend 687P/5S, vitest 505/505, typecheck 0, e2e 11+20 gated).

### Audit (Mode C) — findings this session

Scanner pass clean (documented FP classes only). Three parallel deep-audit
agents + lead hand-verification of every Critical/High, including two
runtime reproductions (the production `django_redis` cache crash; the
`DEBUG=true, DEBUG_TOOLBAR=false` boot ImportError). Register: **C-1**
credit notes posted invoice-direction GL entries (AR debited instead of
credited — books overstated receivables since the engine shipped);
**C-2** production settings crashed at first cache touch; 7 Highs (the
contacts edit dialog's data-wipe, the F5 box-keys mismatch, the F5
computation pollution, the dashboard GST payable hardcode, the
debug_toolbar double gate, the Docker boot failures); 16 Mediums; 9 Lows.

### Remediation executed (TDD — 48 backend + 6 vitest + 3 e2e specs, all RED first)

Tasks 1–15 per the plan (the report's §2 table carries the
finding/fix/evidence of each). The headline accounting truth: credit notes
now post REVERSED journal lines and NET in the F5 computation (quotes
excluded); the dashboard GST payable is re-sourced from the F5 computation
(single statutory truth); the F5 boxes panel reads the real serializer
keys; the contacts edit dialog prefills from the DETAIL payload and a save
persists what it shows.

### The live gate

The full accounting loop verified against the running servers — ledger-level
proof of C-1 (the credit note's AR-CREDIT 817.50 mirror-imaging the
invoice's AR-debit 2725.00), F5 Box 1 = 3500.00 with credit notes netting,
dashboard gst_payable = 315.0000 matching F5 Box 8. Seven screenshots
(59–65_session23), pixel- and DOM-verified. The gate's own findings, all
fixed with regression tests: the register throttle's hardcoded 5/hour
literal (knob pattern — dev 120/h, production posture asserted unchanged),
the banking spec's consumed fixture (self-creating), the p10 contacts row
regex (generalized), the unscoped failed-login audit assertion (scoped to
the failing user), the sandbox process-cleanup behavior (backend + suite
in one call).

### Final state (all Verified)

Backend **735P/0F/5S**; invariants 27P; security 66P/3S; vitest **511/511**;
typecheck **0**; coverage green at the honest ratchet; `build:server` green;
default e2e **11 + 23 gated**; live e2e **33P/1S/0F**; screenshots 7;
docs truth-passed (README v0.3.0/v0.6.0 counts 1,280; CLAUDE v2.15; PAD
v3.8; SKILL v2.0.0 lessons 42–50; AGENTS P11 patterns; DEPLOYMENT.md P11
revision — fresh-host guide with the P11 spot checks, the register budget
and the Docker path marked statically-validated); `.env.example` re-audited
1:1 (backend gains `LOG_DIR`). All commits on `main`, pushed via the SSH
wrapper with remote-ref verification.

## 2026-11-23 — Session 20: P10 Sprint (Self-Serve Loop & Compliance Truth)

**Base:** `e37f12f0` (main) · **Plan:** `docs/REMEDIATION_PLAN_2026-11-22_P10.md` · **Report:** `docs/REMEDIATION_2026-11-22_P10_REPORT.md` · **Session log:** `docs/session_21.md`

### Environment (two sandbox recycles, recovered; zero pushed loss)

- The sandbox was recycled twice mid-sprint. Tasks 1–16 were pushed after every commit (the workspace-reset safeguard) and survived; the environment (PG data + binaries, Redis, venvs, node_modules, playwright browsers) was rebuilt from the documented runbooks both times — PG's wiped empty subdirs (pg_tblspc, pg_replslot, …) restored, Redis debs re-extracted, `uv sync --all-extras` + `npm ci` + `npx playwright install chromium` re-run.
- The uncommitted Task-17 work (the e2e spec + live-run fixes) was lost with the first recycle and rebuilt against the pushed state — its debugging conclusions (the register race, the demo-login failure pair) carried over and finally rooted-caused.
- All four baselines reproduced exactly before each continuation (668P/5S → 683P/5S after Tasks 1–8; 454 → 477 → 494 vitest; typecheck 0; e2e gated parity).

### Audit (Mode C) — findings this session

Scanner pass clean (all hits in the documented FP classes). Three parallel deep-audit agents + lead hand-verification of every Critical/High: **H-1** the invoice form created a contact on EVERY submission (duplicating UEN-less customers, 409-ing repeat UENs); **H-2** no registration page existed (the login link was a dead `#`; the register endpoint had zero consumers — the self-serve loop closed); **H-3** the GST F5 File button POSTed an always-DRAFT return while the review/amend endpoints sat unconsumed; plus the M/L register (PayNow PATCH parity, VOID fail-open, org-choice persistence, transmission error keys, dead contacts/bank-edit/allocations/fiscal-open/change-password/InvoiceNow surfaces, the export-mode lie, the never-passing 85% coverage gate, the truth/UI batch).

### Remediation executed (TDD — 19 backend + 51 vitest + 5 e2e specs, all RED first)

Tasks 1–16 per the plan (see the report's §2 table for the finding/fix/evidence of each). Task 14's "corrupted CI trigger" was corrected on the record: the file was never corrupt (`od -c` ground truth) — a tool-display artifact that eats the `[m` byte sequence in rendered output; the corrective commit documents it.

### The live gate — the phase that earned its name

Five production defects surfaced only when the product actually ran, each fixed with a RED regression test:

1. **The register bounce** (LG-1): the auth-provider's mount-time session check treated the anonymous 401 (an unauthenticated /register visitor gets it from /auth/me) as session expiry and bounced to /login — the form only ever worked by winning the race. Public auth pages are exempt now.
2. **The rate-limit 403 masquerade** (LG-2): a 35-login API burst tripped at #30 with a raw 403 "You do not have permission…" — django-ratelimit's `Ratelimited` (a bare PermissionDenied subclass) fell through DRF's fallback. Now the documented 429 contract.
3. **The missed third knob** (LG-3): `LOGIN_RATELIMIT_USER` 30/min blocked the grown suite's tail; dev raises to 120/min (production unchanged, asserted).
4. **The settings copy-on-write cascade** (LG-4): `development.py` mutated the shared base lists in place; importing it under other settings (the knob test) crashed a 79-test middleware cascade. Copy-on-write, per the file's own documented rule.
5. **The UEN 500** (LG-5): a taken organisation UEN was an unhandled IntegrityError on org-create and both PATCH paths (the detail PATCH has no serializer at all). Clean 400s everywhere; the blank-UEN schema modeling deferred explicitly.

Plus spec hygiene: the banking statement spec's silent "Marina" fixture-name dependency, the shell breadcrumb h2 duplicating each page's h1 (strict-mode + a11y), and the empty-list double CTA. **Canonical runs: e2e:full 30/30 green TWICE consecutively.**

### Final state (all Verified)

Backend **687P/0F/5S**; invariants 27P; security 55P/3S; vitest **505/505**; typecheck **0**; coverage green at the honest ratchet (62.88/52.33/51.97/63.19); `build:server` green (the only build — export retired); default e2e **11 + 20 gated**; live e2e **30/30 twice**; screenshots 53..58_session20 (6, content-verified); docs truth-passed (README v0.2.0/v0.5.2, counts 1,223; AGENTS P10 patterns ×6; DEPLOYMENT P10 revision + the live-gate bootstrap sequence; PAD/SKILL/CLAUDE updated); `.env.example` re-audited 1:1 (no new vars; the export-mode claim corrected). All commits on main, pushed via the SSH wrapper with remote-ref verification.

## 2026-11-22 — Session 18: P9 Sprint (Onboarding & Banking Truth)

**Base:** `b6bdfb40` (main) · **Plan:** `docs/REMEDIATION_PLAN_2026-11-22_P9.md` · **Report:** `docs/REMEDIATION_2026-11-22_P9_REPORT.md` · **Session log:** `docs/session_19.md`

### Environment (one incident, recovered; one deliberate reset)

- PG + Redis + venv + node_modules + live-phase scripts survived the session reset; the four P8 baselines reproduced EXACTLY before any change (647P/0F/5S, 418 vitest, typecheck 0, 9+14 e2e).
- **Incident (recovered, zero loss):** the dev DB had been wiped to a 2-table stub since P8 — schema reloaded from `database_schema.sql` (32 tables / 47 NUMERIC(19,4) verified) before the baseline run. A second deliberate drop-and-reload preceded the canonical live phase (fresh org for the e2e chain + screenshots).
- **Live-phase lesson:** killing the npm wrapper leaves `next-server` holding port 3000; a stale runserver served pre-fix code mid-debug. The teardown now pkills the process tree.

### Audit (Mode C) — findings this session

Scanner criticals in the documented FP classes (single production hit = the Storecove docstring placeholder, M-14 deferred). Three parallel deep-audit agents + lead hand-verification of every Critical/High: **O-1** the onboarding dead end (registration creates no org; the dashboard CTA links to a nonexistent route — the product unusable for self-serve users); **B-1** `JSON.stringify(FormData)` → `"{}"` (the statement import could never succeed); **B-2** the suggest-matches envelope mismatch (matches never rendered); **B-3/B-3b/B-5** the raw-UUID customer field, no allocation UI (the P5 engine unreachable; invoices could never reach PAID), the dead Make Payment state; **B-4** the dead Add Account buttons; **B-6** no void/unreconcile UI; **B-7** the tolerance NameError 500 (the P7 fix itself broken); **C-1** the convert envelope flat-read (`/invoices/undefined`); **C-2** the untyped invoices list; **C-3** InvoiceNow could transmit an APPROVED quote as a UBL Invoice (any member); **C-4** the account_type seed gap (empty account dropdown on fresh orgs); **C-5/C-6/D-1..D-4** the lying status_history, the conflated CONVERTED badge, the unbounded aged as-at, the invented dashboard figures; **S-1..S-4** the last garbage-date 500s, the transport-fault logout, the XSD fail-open, the stale root requirements.txt.

### Remediation executed (TDD — 21 backend + 36 vitest + 3 e2e specs, all RED first)

| Task | Change | Evidence |
|---|---|---|
| 1 (C-3) | InvoiceNow invoice-only + CanCreateInvoices | 2 RED → quote 400 / member 403 / invoice still queues |
| 2 (B-7/S-1/S-4) | tolerance + document-date 400s; NaN/Infinity rejected; requirements.txt retired | 4 RED (NameError + filter 500s) → 400s |
| 3 (C-1) | convert envelope pinned (HTTP test) + hook unwraps `.invoice` | RED: `/invoices/undefined` verbatim |
| 4 (C-2) | invoices list `type=SALES_INVOICE` + leak labelling | filter + badge tests |
| 5 (C-4) | seed backfills account_type; filter matches either column | 3 RED → fresh-org REVENUE list non-empty |
| 6 (B-1) | `api.postForm` + FormData-aware headers | 2 RED → real multipart at the fetch level |
| 7 (B-2) | suggest-matches envelope unwrap + field mapping | 1 RED against the real backend shape |
| 8 (O-1) | organisation creation page at the CTA's route | 5 tests; the Critical closed |
| 9 (B-4) | bank-account dialog (zod; bank-type GL picker) | 3 tests |
| 10 (B-3/B-5/K-5) | ContactPicker (real filter keys) + Make Payment form | 4 + 2 tests |
| 11 (B-3b) | allocation sections + Record Payment deep link + list amount fields | 5 + 1 + 1 tests |
| 12 (B-6) | payment Void (reason) + transaction Unreconcile | 2 + 2 tests |
| 13 (D-1) | aged `issue_date__lte=as_at` | 1 RED (post-as-at doc included) |
| 14 (D-2..D-4) | dashboard truth: invented boxes/trends removed, live links | the dashboard's first 4 tests |
| 15 (C-5/C-6/K-*) | status_history synthesis; badge gates on the link; VOID branch delegates | 3 backend + page tests |
| 16 (S-2/S-3) | transport-vs-auth session split; XSD fails closed | 1 + 1 RED |

### The live gate — three iterations, each a real finding

1. The deep link never opened the form (PaymentsTab reads params; the accounts tab is the default — the tab now defaults from `?receive=1`); the GL picker was empty (the seeded bank accounts are CHILDREN of the 1000 header — a type filter lifts the top-level-only default); the invoices specs desynced from the page's new filter.
2. The bank-account POST 400'd: the dialog sends `paynow_type: null`, the serializer rejected null, the DB column is nullable and the CHECK allows NULL ("" violates it) — both serializers accept null; `is_bank` ships end-to-end; the workflow spec made serial + idempotent; `--workers=1` for the full run; the strict-mode/locator semantics fixed (overlay scoping; the RCP- prefix; "Add Account" is NOT a substring of "Add Bank Account").
3. **Canonical run: e2e:full 26/26 + 6/6 screenshots** (two VLM-verified: the receive form's customer chip + allocation rows; the reconciled transaction at a 100% reconciliation rate).

### Final state (all Verified)

Backend **668P/0F/5S**; invariants 27P; security 53P/3S; vitest **454/454**; typecheck **0**; default e2e **9 + 17 gated**; live e2e **26/26**; screenshots 47..52_session18 (6, md5-unique, 2 VLM-verified); docs truth-passed (README v0.1.9/v0.5.1 counts 1,148; PAD v3.6; CLAUDE v2.13; ledgersg_SKILL v1.9 lessons 31–35; AGENTS P9 patterns; DEPLOYMENT §11 + P9 spot checks); `.env.example` cross-checked (no new vars). 20 commits on main, all pushed and remote-verified.

## 2026-11-22 — Session 16: P8 Sprint (Reporting Truth & Quote Lifecycle)

**Base:** `251b3577` (main) · **Plan:** `docs/REMEDIATION_PLAN_2026-11-22_P8.md` · **Report:** `docs/REMEDIATION_2026-11-22_P8_REPORT.md` · **Session log:** `docs/session_17.md`

### Environment (survivors reused; one incident, recovered)

- PG + Redis + venv + node_modules + live-phase scripts survived the session reset; schema v1.1.0 verified; baselines reproduced EXACTLY before any change: backend **624P/0F/5S**, vitest **398/398**, typecheck **0 errors**, e2e default **9 + 12 gated**.
- **Incident (recovered, zero loss):** a verification run without `--reuse-db` invoked pytest-django `create_test_db` against the DB named in `.env` (the working dev DB) — dropped and recreated empty. Root cause: `TEST.NAME` follows `DB_NAME` locally. Schema reloaded from `database_schema.sql`, suite re-run green before any commit. Lesson: a bare pytest run is destructive when `.env` points at the working DB — the documented invocation (`--reuse-db --no-migrations`) is the contract.

### Audit (Mode C) — findings this session

Scanner criticals all in the documented FP classes (spot-verified). Three parallel deep-audit agents + lead hand-verification of every Critical/High: **G-1** the P7/F-10 get_permissions() refactor applied to GSTRegistrationView (mutations are POST/DELETE, no PATCH) — any member could register/deregister GST (live, git-diff confirmed); **G-2** the P7/F-11 sweep's misses (banking UUID filters, ledger dates, unbounded ints, financial dates → 500s); **G-3/G-5/G-8** the void state machine contradicted STATUS_TRANSITIONS (OVERDUE voidable through NO endpoint; allocation rows orphaned; filler reason on the generic endpoint; InvoiceNow button enabled for statuses the backend refuses); **G-6** cc/bcc validated but never delivered, phantom message field; **G-7** blob downloads bypassed the P7 error-envelope parser with no onError; **R-1..R-4** the financial reports: garbage dates → 500, TB stub `{data:{}}`, BS never balanced (equity excludes current-period earnings), custom accounts invisible to P&L/BS (account_type_ref never set on API create); **R-5** no aged endpoint anywhere; **R-7/R-8** the reports page static + two dormant hooks pointing at 404 endpoints; **Q-1..Q-4b** quote conversion link never persisted (phantom converted_to_id), QUO/PINV prefixes vs seeded QT-/BILL-, filter-key mismatch (document_type vs type), static quotes pages, TAX INVOICE labelling on quote PDFs; **S-1/S-2/S-3** fiscal close precondition "TBD", settings round-trip truth, dead core-dashboard duplicate.

### Remediation executed (TDD — 23 backend + 20 vitest + 2 e2e specs, all RED first)

| Task | Change | Evidence |
|---|---|---|
| 1 (G-1) | GST registration: class-level CanManageOrg restored (POST/DELETE gated) | 2 RED (member 200s) → 403; +3 tests |
| 2 (G-2) | Banking UUID filters, ledger dates via parse helpers; parse_int_param min_value; financial dates validated; route single-prefixed /reports/financial/ | 10 new RED → 400s; suite 624→637 |
| 3 (G-3/G-5/G-8) | void_document accepts the advertised set (DRAFT journal-safe); PAID → credit-note guidance + map corrected; allocation guard; generic endpoint requires a reason; frontend Void/InvoiceNow gates truthful | 6 RED → GREEN; the old draft-void test updated; suite 643; vitest 399 |
| 4+5 (G-6/G-7) | cc/bcc reach the task; message field dropped from the contract (both sides); blob errors via the shared resolver; useInvoicePDF onError toast | 3 backend + 1 contract + 2 blob + 1 payload RED → GREEN; suite 646; vitest 402 |
| 6 (R-2/R-3) | TB delegates to the journal service; BS folds retained earnings + balanced flag; per-account lines | 4 RED (KeyError/500) → GREEN; suite 651 |
| 7 (R-4) | create_account links account_type_ref via GROUP_TO_COARSE_TYPE (by group name — category too coarse) | 3 RED → GREEN incl. custom revenue VISIBLE in the P&L end-to-end; suite 654 |
| 8 (R-5) | GET /reports/aged/ — per-contact bucket rows + totals mirroring the dashboard semantics | 5 RED (404s) → GREEN; suite 659 |
| 9 (R-7/R-8) | Tabbed reports client (TB/P&L/BS/GST F5/aged) + reports/gst-returns api-client families + use-reports hooks; the two 404-endpoint dormant hooks deleted | 5 hook + 5 page tests; vitest 412; gated e2e |
| 10 (Q-1..Q-3) | related_document persisted on convert; QT-/BILL- prefixes; useInvoices sends `type` | 3 RED → GREEN; suite 662 |
| 11 (Q-4b) | quote_pdf.html for SALES_QUOTE (no TAX INVOICE labelling) | 2 RED + invoice invariant; suite 665 |
| 12 (Q-4) | Quotes list/new/detail pages; documentType threaded through the form; useConvertQuote | 4 page + 1 payload tests; vitest 417; gated e2e |
| 13 (S-1/S-3) | Year close requires closed periods (400 names them); dead core dashboard deleted | 2 RED + invariants; the P7 routing test strengthened; suite 647 net (+4, −22 duplicates) |
| 14 (S-2) | Settings reset only on the user's save; AuthProvider.refreshOrganisations() → sidebar propagates | +1 propagation test; vitest 418 |

### Final gate (all Verified, executed)

- `pytest --reuse-db --no-migrations -q` → **0 failed, 647 passed, 5 skipped** · invariants 27P · security 53P/3S (posture unchanged)
- `npm test` → **418/418** · typecheck 0 errors · eslint parity/new-clean · e2e default 9 + 14 gated · **e2e:full 23/23** (first run 22/23 — the reports spec's isVisible() race, fixed with expect.poll)
- 6 real-data screenshots (`docs/screenshots/41..46_*_session16.png` — md5-unique; trial balance + quote detail **VLM-verified**: real rows, Balanced badge 2,616.00 == 2,616.00; QUOTATION framing with Convert/Void/Send/PDF/Print and 4,000 + 360 GST = 4,360)
- `.env.example` cross-checked: complete (both flags false positives — CORS via multiline config); P8 adds no env vars
- Docs truth pass: README (P8 milestone, 1,088 = 647 + 418 + 23, v0.1.8/v0.5.0), PAD v3.5, CLAUDE v2.12, ledgersg_SKILL v1.7→v1.8 (+lessons 26–30), AGENTS P8 patterns, DEPLOYMENT.md re-verified + P8 spot checks

### Deferred (registered, not dropped)

P7 register carried forward unchanged. New: InvoiceNow backend quote gate (frontend gated; backend polish), GST review transition route, aged AR/AP credit-note netting (allocation model decision), quote lifecycle vocabulary (ACCEPTED/REJECTED/EXPIRED — DB enum), reports export (PDF/CSV), TB zero-activity/fiscal-year modes, P&L/BS sub-group labels, the destructive-bare-pytest hazard (documented in report §3 + session log).

### Commits

14 conventional commits on `main` (12 code + 2 docs), **pushed incrementally after each task** via `docs/ssh_git_wrapper_v3.py` (paramiko shim; remote ref verified on every push; deploy key shredded after the final push). One commit-message body lost two backtick-quoted words to shell substitution (cosmetic; noted in report §5).

## 2026-11-22 — Session 14: P7 Sprint (API Truth & Permission Hardening)

**Base:** `9077381b` (main) · **Plan:** `docs/REMEDIATION_PLAN_2026-11-22_P7.md` · **Report:** `docs/REMEDIATION_2026-11-22_P7_REPORT.md` · **Session log:** `docs/session_15.md`

### Environment (fresh sandbox, rebuilt from the repo's own scripts)

- Rootless PostgreSQL 17 via `docs/setup_pg_z.sh` + `skills/rootless-postgresql/SKILL.md` (TCP psql hangs on the scram prompt — operate via socket + `PGPASSWORD`, the documented lesson); schema v1.1.0 loaded into BOTH databases and verified (47 NUMERIC(19,4) columns, seeded SR rate history, 30+2 tables); Redis 8 (liblzf prerequisite); `skills/` excluded from all checks per instructions.
- Baselines reproduced EXACTLY before any change: backend **588P/0F/5S**, vitest **383/383**, typecheck **0 errors**, e2e default **9 + 11 gated** — the documented P6 state.

### Audit (Mode C) — findings this session

Repo-skill scanners per `skills/skills-catalog.md` (criticals all in the documented FP classes) + two deep manual review passes (frontend P6 surfaces, backend views) + parallel audit subagents. Verified in source before planning: **F-1** the void flow sends `reason: ""` (every UI void 400s, hidden by F-7); **F-2** `/status/` compares against `"VOIDED"` while the enum is `VOID` — the `CanVoidInvoices` branch is DEAD CODE, any member could void any document (bypass live, reproduced); **F-3** org-create serializer declares a phantom `address` (TypeError 500 on the API's own advertised field); **F-4** the three fiscal routes live only in the shadowed `apps/core/urls.py` module (frontend 404s); **F-5** payment service accepts `gl_account=None` (raw IntegrityError 500); **F-6** frontend sends `to` as a string (Celery email task crashes silently while the UI toasts success); **F-7** api-client reads keys the backend never writes; **F-9** payables exclude PARTIALLY_PAID bills; **F-10** settings PATCHes are raw setattr + member-reachable; **F-11** malformed query params → raw 500s (banking tolerance probe silently defaults garbage); **F-12/F-13/F-14/F-17/F-18** frontend truthfulness + dead code (mock-era edit route, `useUpdateInvoice`, legacy server api-client, unwired PDF/InvoiceNow hooks); **F-15** missing permission classes; **F-16** ledger a11y; **F-19** (discovered during F-2 RED) `REST_FRAMEWORK` uses `DEFAULT_EXCEPTION_HANDLER` — DRF's key is `EXCEPTION_HANDLER`, so the custom exception handler NEVER ran.

### Remediation executed (TDD — 36 backend + 15 vitest + 1 e2e spec, all RED first)

| Task | Change | Evidence |
|---|---|---|
| 1 (F-2, F-19) | ChoiceField over the model status vocabulary + per-transition permission map + payment statuses reserved to the allocation service; exception-handler settings key fixed | 4 RED (the void bypass was live) + 2 posture gates; suite 588→595 |
| 2 (F-3) | Phantom `address` removed from the create serializer | 2 RED (500 TypeError) → 201; +2 tests |
| 3 (F-4) | Fiscal routes into the active urls package; close views `CanManageOrg` + tz-aware; shadowed module deleted (rode the F-3 commit — traced in report §5) | 3 RED (404s) → 200; suite 600 |
| 4 (F-5) | Service-seam ValidationError + payment-JE defense-in-depth guard (DB/serializer seams were already closed) | 3 RED at the true seams; suite 604 |
| 5 (F-7) | api-client reads `{error:{message}}` + DRF field errors (`ApiError.errors`) | 3 vitest RED→GREEN |
| 6 (F-1, F-8, F-12) | Radix/Shadcn Dialog + Textarea primitives; REQUIRED-reason void dialog; ledger invalidation; no-org guard + unhandled-rejection catch | 4 vitest RED→GREEN |
| 7 (F-6) | `RecipientListField` normalizes string→list + email-validates; hook type `to: string[]` (rode the frontend batch commit) | 3 RED → 200 with list delivered to the task |
| 8 (F-9) | Payables status filter includes PARTIALLY_PAID (rode the frontend batch commit) | 1 RED (docstring claimed it; code never did) → GREEN |
| 9 (F-12/F-14/F-17) | No-org states on ledger/settings/detail; org-derived GST columns; shell nav id + Demo User + dead New Invoice button | 2 vitest RED→GREEN + e2e |
| 12 (F-13/F-18) | Edit route + `useUpdateInvoice` + legacy server client deleted; `useInvoicePDF`/InvoiceNow wired on the detail page | 3 vitest RED→GREEN; typecheck gate caught 2 import misses |
| 10 (F-10) | Typed settings serializers + `can_manage_org` via `get_permissions()` (GET stays member-readable) | 5 RED → 403/400; suite 616 |
| 11 (F-11) | Shared `common/query_params.py` helpers (date/UUID/int → 400 naming the param) at all audited sites; tolerance-probe bare `except:` gone | 6 RED + sanity GREEN; ruff 119→117; suite 623 |
| 13 (F-15/F-16) | `can_view_reports` on dashboard metrics/alerts; `IsOrgMember` on org-scoped GST views; ledger `scope`/`aria-sort` | suite 624; +1 vitest; gated e2e |

### Final gate (all Verified, executed)

- `pytest --reuse-db --no-migrations -q` → **0 failed, 624 passed, 5 skipped** · invariants 27P · security 53P/3S (2 new posture gates)
- `npm test` → **398/398** · `npm run typecheck` → 0 errors · e2e default 9 + 12 gated · **e2e full 21/21** (live dev stack, dev DB bootstrapped through the public API; first run 18/21 — a spec-level strict-mode collision with the new shell link, scoped to main, re-run green)
- Frontend gates re-verified on the final tree post-session-resume: typecheck 0, vitest 398/398, e2e default 9 + 12 gated — identical; backend unchanged since `c9e42840` (zero backend diffs in the working tree)
- 6 real-data screenshots (`docs/screenshots/35..40_*_session14.png` — md5-unique, 1440×900, incl. the void dialog open)
- `.env.example` cross-check: web `BACKEND_URL` moved to the reserved section (its only reader was deleted as dead code); root index updated
- Docs truth pass: README (P7 milestone, 1,043 = 624 + 398 + 21), PAD v3.4, CLAUDE v2.11, ledgersg_SKILL v1.7 (+lessons 20–25), AGENTS P7 patterns, **DEPLOYMENT.md rewritten as a verified fresh-host step-by-step guide (§1–§15)**

### Deferred (registered, not dropped)

P6 register carried forward (H-02, M-1, M-10, M-11, M-14, H-07 ruff/eslint debt, F5 rate-basis, A-10, GST pay_return, contact picker, Reg-11, reports/quotes real pages — the P8 candidate, account_type seed population). New: B6 list-envelope standardization, invoice edit flow (needs a wider backend update contract), ledger pagination, settings form reset UX, org-state propagation to the auth provider, fiscal close precondition (B9), COA serializer dropped fields, checkSession transport-vs-401, dashboard service duplication (core vs reporting — the frontend only calls reporting).

### Commits

12 conventional commits on `main`, **pushed incrementally after each task** via `docs/ssh_git_wrapper_v3.py` (paramiko shim; remote ref verified on every push; deploy key shredded after the final push). Two `git add -A` sweeps traced in the report §5 (F-9 + F-6-backend + env files rode the frontend batch; the shadowed urls.py deletion rode the F-3 commit).

## 2026-11-22 — Session 12: P6 Sprint (C-5 Completion & Payment Posting Integrity)

**Base:** `20069486` (main) · **Plan:** `docs/REMEDIATION_PLAN_2026-11-22_P6.md` · **Report:** `docs/REMEDIATION_2026-11-22_P6_REPORT.md`

### Environment (rebuilt on surviving data after a workspace reset)

- The previous session's P6 work (11 commits, never pushed) was lost to a workspace reset — the second such loss. Re-cloned at the session-11 state; the PG data directory survived (empty subdirectories pg_logical/snapshots, pg_notify, ... stripped again — recreated the full PG17 set and the server recovered both databases with schema intact); Redis restarted from the surviving install; backend venv + web deps reinstalled; playwright 1.58.2 needed chromium 1208.
- Baselines reproduced before any change: backend **567P/0F/5S**, vitest **358/358**, typecheck **0 errors**, e2e default **10 + gated skips**, 74 pre-existing lint problems — the documented P5 state, exactly.
- Process lesson applied: **push after every commit** (the SSH wrapper + paramiko shim verified the remote ref each time); a workspace reset can no longer destroy a session's work.

### Audit (Mode C) — findings this session

Post-P5 audit, every finding re-verified in source with line numbers against the fresh clone: **F-4** allocate() blocks second allocations on PARTIALLY_PAID (payment_service.py:463); **F-5** the payment JE control-account fallback broad-matches `Q(account_type=…).first()` (622-623/651-654 — AR could land on 1010 Cash on Hand); **F-6** create_contact never sets AR/AP accounts; **F-7** unallocate() doesn't recompute amount_paid; **F-10** both org update allowlists forward a phantom `address` key while the real fields are filtered (organisations.py:109, organisation_service.py:282); **F-11** the detail serializer omits amount_paid/amount_due; **C-5** leftovers (detail/ledger/settings mock pages); **D-1** sync route params in a Promise-params Next.js. De-escalated: the `account_type` seed gap (the broad Q resolves only via its code arm today — latent fragility, closed by the F-5 fix). Scanner criticals: all in the documented false-positive classes.

### Remediation executed (TDD — 21 backend + 21 vitest + 3 e2e specs, all RED first)

| Task | Change | Evidence |
|---|---|---|
| 1+2 (F-4/F-5/F-6/F-7) | Guard widened to ("APPROVED", "PARTIALLY_PAID"); JE fallback → JournalService fail-closed resolvers; create_contact assigns 1200/2100 by type; unallocate recomputes amount_paid/status; test_views fixtures corrected | 10 tests RED→GREEN (RED evidence: "must be APPROVED", AR on 1010 decoy, no-raise fail-closed, stale amount_paid); suite 567→577 |
| 3 (F-10) | Both allowlists forward address_line_1/2, city, postal_code, country | 1 RED→GREEN (round-trip + phantom no-op); 579 |
| 4 backend (F-11) | Detail serializer gains amount_paid + amount_due (SerializerMethodField mirrors the DB generated column) | 2 RED→GREEN; 581 |
| 4 frontend (C-5 + D-1) | InvoiceDetail type (useInvoice retyped), full detail-client rewrite (payment state on every non-void doc, real mutations), await params, generateStaticParams dropped | 7 vitest RED→GREEN (358→365); gated e2e |
| 5 (C-5) | GET journal-entries/ledger/ (flat line rows, filters, org-scoped) + useLedger + props-driven ledger-table + client | 3 backend + 7 vitest RED→GREEN (372); gated e2e |
| 6 (C-5) | useOrganisation hooks + settings client (controlled inputs, GST register/deregister wiring) | 5 hook + 6 page tests RED→GREEN (383); gated e2e |
| 7 (E-1) | REFRESH_RATELIMIT_IP knob + config.ratelimits.refresh_ip; development raises refresh/DRF budgets copy-on-write; testing.py REST_FRAMEWORK mutation made copy-on-write (it corrupted the shared base dict — caught by the new posture gate) | 4 gates RED→GREEN; 588; security 51+3 |
| 9 (e2e fixes) | Payment state always rendered on non-void docs; settings e2e via getByLabel+toHaveValue | e2e full 18/20 → **20/20** |

### Final gate (all Verified, executed)

- `pytest --reuse-db --no-migrations -q` → **0 failed, 588 passed, 5 skipped** · invariants 27P · security 51P/3S
- `npm test` → **383/383** · `npm run typecheck` → 0 errors · e2e default 9 + 11 gated · **e2e full 20/20** (live dev stack, dev-DB bootstrapped through the public API)
- Ruff parity on every touched file (payment_service 30→26; the development.py 19→21 is the file's established star-import F405 idiom); eslint parity (new files clean)
- 6 real-data screenshots (`docs/screenshots/29..34_*_session12.png` — md5-unique, 1440×900, non-blank)
- `.env.example` cross-checked: complete; P6 adds no env vars (the E-1 knobs are Django settings)
- Docs truth pass: README (P6 milestone, 991 = 588 + 383 + 20, v0.1.6/v0.4.0), PAD (counts + Page Data Truth), ledgersg_SKILL v1.6.0 (+5 lessons), AGENTS NUMERIC(10,4) current-precision claims corrected to NUMERIC(19,4)/NUMERIC(12,6) (verified against information_schema)

### Deferred (registered, not dropped)

P5 register carried forward unchanged (H-02, M-1, M-10, M-11, M-14, H-07, frontend eslint debt, F5 rate-basis, A-10, GST pay_return, contact picker, Reg-11). New: none — the account_type seed-column population is optional hardening, superseded by the fail-closed resolver.

### Commits

11 conventional commits on `main`, **pushed incrementally after each task** via `docs/ssh_git_wrapper_v3.py` (paramiko shim; remote ref verified on every push; deploy key shredded after the final push). `.env.example` files verified and already tracked.

## 2026-11-21 — Session 11: P5 Sprint (Truth Restoration — Repo Hygiene, Real InvoiceNow, Accounting Integrity & Real Dashboard Data)

**Base:** `cfc74571` (main) · **Plan:** `docs/REMEDIATION_PLAN_2026-11-21_P5.md` · **Report:** `docs/REMEDIATION_2026-11-21_P5_REPORT.md`

### Environment (rebuilt from scratch)

- Rootless PG 17 (:5432) + Redis 8.0.2 (:6379) provisioned (`docs/setup_pg_z.sh` + rootless deb extraction incl. liblzf); schema v1.1.0 loaded in both DBs; backend venv (`pip install -e ".[dev]"`) + web `npm install`.
- Baselines reproduced before any change: backend **534P/0F/5S**, invariants 20P, security 47P/3S, vitest **354/354**, typecheck **0 errors**, e2e default **9+7 gated skips** — the documented P4 state, exactly.
- Operational: running pytest WITHOUT `--reuse-db` against the TEST-named DB recreates it EMPTY (schema gone) — reload `database_schema.sql` when that happens; `git stash pop` silently unstages staged `rm --cached` deletions (re-stage before committing).

### Audit (Mode C) — findings this session

Primary input: `docs/ledgersg-audit-report.md` (the independent audit of `7e4061f0`). Every Critical/High re-verified in source with commands and line evidence — all confirmed. Repo skills per `skills/skills-catalog.md`: code-review-and-audit, code-quality-standards, diagnosing-bugs, e2e-testing-lessons, writing-plans. NEW finding beyond the audit: `transmit_peppol_invoice_task` passes the LOG id to `transmit_invoice(invoice_id)` — the auto-transmit path can never succeed; the old task tests mocked the service and asserted the buggy call shape.

### Remediation executed (TDD — 33 backend + 4 vitest + 1 e2e, all RED first)

| Task | Change | Evidence |
|---|---|---|
| 1 (C-1/C-3/H-9) | Untracked .env/.env.local (re-added by P4 `git add -A`), 211 .pyc, 54 dist/, 10 .bak; .gitignore completed; CI per-run DB password + DB_* env + pyproject cache path; testing.py reads DB_* | hygiene greps zero; suite green through the settings change |
| 2 (C-4) | Deleted broken dead org_seed_service.py | zero references; ruff invalid-syntax 2→0 |
| 3 (C-2 + seam bug) | `execute_transmission_for_log` seam (updates the EXISTING log); task rewired; send_invoicenow creates a real log + queues the task (400 configure-first); get_invoicenow_status reports real rows; check task wired to the adapter; cleanup retention-safe (never deletes DELIVERED/REJECTED) | 12 tests RED→GREEN; 3 old task tests updated to the corrected contract; suite 534→546 |
| 4+5 (H-1/H-2) | allocate() persists document.amount_paid; void() posts create_reversal + releases allocations + restores status | 5 tests RED→GREEN; suite 546→551 |
| 6+7 (H-4/H-5/H-6) | `_resolve_control_account` exact+fail-closed (1200/2100/1600/2600); add_line 2dp GST base + 2dp total; create_entry enumerate; conftest fixture chart corrected; auth access_expires tz-aware | 7 tests RED→GREEN (RED evidence: output tax→2200, input→1200, duplicate line numbers crashed); suite 551→558 |
| 8 (H-3/H-10) | Cache invalidation wired into approve/void/payment×4/file_return; alerts view computes real overdue/unreconciled/unpaid counts | 4 tests RED→GREEN; suite 558→562 |
| 9 (M-5/M-6/M-7) | toggle_gst seeds GST control accounts (targeted idempotent helper); update_organisation allowlist; dead sequence code removed | 5 tests RED→GREEN; suite 562→567 |
| 10 (C-5 part 1) | Real invoices list page (mocks deleted; useInvoices + truthful states + search); hook retyped to the real backend row shape; new backend-gated e2e spec | 4 vitest RED→GREEN (354→358); e2e 16→17 |

### Final gate (all Verified, executed)

- `pytest --reuse-db --no-migrations -q` → **0 failed, 567 passed, 5 skipped**
- `pytest tests/invariants -q` → **27 passed** · `pytest tests/security -q` → **47 passed, 3 skipped**
- `manage.py check` → 0 errors (1 known W001) · ruff — zero new findings on touched files; new files clean
- Web: typecheck 0 errors · vitest **358/358** · eslint touched files 0E/0W · e2e default **9+8 gated skips**, full **17/17** (live backend; E2E_DEMO_PASSWORD for the 12+-char register policy)
- Live API: demo org created via the public API with the full 102-account seeded chart (incl. 1600/2600); three draft invoices created through the frontend payload contract (lines included)
- 5 new screenshots (`docs/screenshots/24..28_*_session11.png`), md5-unique, non-blank — incl. **26_invoices_real_data** (the C-5 evidence shot)
- Hygiene greps: `git ls-files` artifact count 0; CI has no static credential

### Deferred (registered, not dropped)

P0-P4 register unchanged; **C-5 remainder (invoice detail, ledger table, settings, reports/quotes) is the P6 candidate** — the list-page pattern is proven. Also carried: M-1 audit events, M-10 CSRF, M-11 static-export CSP, M-14 adapter 404-as-valid, transmission-log archival export, H-07/H-08 lint debt, F5 rate-basis, H-02 base-currency reporting, A-10 stale requirements.txt. See P5 report §3.

### Commits

Conventional commits on `main` per P5 plan §13; pushed via `docs/ssh_git_wrapper_v3.py` (key shredded after push).

---

## 2026-11-21 — Session 9: P4 Sprint (Cross-Reload Session Persistence, Evidence-Gated Refresh & Docs Truth)

**Base:** `33e176bf` (main) · **Plan:** `docs/REMEDIATION_PLAN_2026-11-21_P4.md` · **Report:** `docs/REMEDIATION_2026-11-21_P4_REPORT.md`

### Environment (reused, re-provisioned after the sandbox recycle)

- Rootless PG 17 (:5432) + Redis 8 (:6379) re-provisioned (`docs/setup_pg_z.sh`); schema v1.1.0 intact in both DBs; a stale `postmaster.pid` needed clearing once after the recycle.
- Baselines reproduced before any change: backend **519P/0F/5S**, vitest **349/349**, typecheck **0 errors**, e2e **9 passed + 4 gated skips** — the documented P3 state, exactly.
- Operational: the sandbox reaper kills detached dev servers BETWEEN tool invocations (silently); the whole e2e/screenshot phase runs inside ONE invocation (backend → readiness poll → playwright `webServer` → trap cleanup). The inverse trap: a `--noreload` dev server from the previous session still held :8000 serving pre-P4 code — one `Set-Cookie` header on login was the clue.

### Audit (Mode C) — findings this session

Repo skills: `code-review-and-audit` (standard mode scoped to `apps/`, every scanner "critical" manually re-verified — the documented false-positive classes), `code-quality-standards`, `diagnosing-bugs`, `e2e-testing-lessons`. Real findings (register in plan §0):

- **E-1 (High, UX + auth posture)**: cross-reload session persistence broken end-to-end — a THREE-LINK chain: (1) backend sets no refresh cookie (while the api-client header comment claimed "HttpOnly cookie" — the code never existed); (2) frontend discards the refresh token; (3) `fetchWithAuth`'s `&& accessToken` guard blocks the cold-reload refresh. Every reload/new tab/browser restart dropped the session; logout never blacklisted on user-initiated logout.
- **E-2 (Medium, docs)**: post-P3 stale claims — README "NUMERIC(10,4)" + 714 badge; PAD v3.1.0 metrics; ledgersg_SKILL non-negotiable #2 + stale overflow row; AGENTS pre-P3 rows.
- **E-3 (Low)**: no root `.env.example` (session directive). **E-4 (Low)**: DEPLOYMENT.md predates the cookie flow. **E-5 (Low)**: extend the vitest/playwright suites through the existing configs.

### Remediation executed (TDD)

| Task | Change | Evidence |
|---|---|---|
| 1 (E-1 backend) | `_refresh_cookie.py` helpers; login/register set the HttpOnly refresh cookie (Path=/api/v1/auth/, Lax, Secure=!DEBUG, 7d); refresh accepts body OR cookie (rotation+blacklist identical, re-sets rotated); logout blacklists + expires; change-password expires | 8 tests RED→GREEN; suite 519→527 |
| 2 (E-1 frontend) | refresh on the cold 401 + retry (guard dropped); header comment now true | vitest 349→351 (RED on the guard first) |
| 3 (E-5 + refinement) | e2e session spec (reload survival, post-reload nav, logout-ends-session); shell logout affordance; login rates as settings knobs (`LOGIN_RATELIMIT_IP/USER`, production unchanged, dev 60/min for the ~11-login e2e budget); **the evidence gate**: backend `session_hint` JS-readable marker cookie (set login/register/refresh; expired logout/password-change/failed-cookie-refresh), frontend refreshes only with evidence — anonymous 401s propagate (root cause of the e2e's 6 failures: refresh-on-every-401 flooded the 20/min refresh limit AND swallowed the login form's error behind a hard redirect) | 6 pytest + 3 vitest RED→GREEN; e2e 13→16, full run **16/16** |
| 4 (E-2) | README/PAD v3.2.0/CLAUDE v2.9.0/AGENTS session-9 lessons/ledgersg_SKILL v1.4.0 truth pass | truth greps clean (no 10,4 / 706 / 714 claims) |
| 5 (E-3/E-4) | root `.env.example` index; DEPLOYMENT.md cookie flow + reload smoke + SameSite=None caveat + counts | per-var cross-check vs both app templates |

### Final gate (all Verified, executed)

- `pytest --reuse-db --no-migrations -q` → **0 failed, 534 passed, 5 skipped**
- `pytest tests/invariants -q` → **20 passed** · `pytest tests/security -q` → **47 passed, 3 skipped**
- `manage.py check` → 0 errors (1 known W001) · ruff touched files clean
- Web: typecheck 0 errors · vitest **354/354** · eslint touched files: pre-existing findings only · e2e default **9 + 7 gated skips**, full **16/16**
- Live curl: login sets both cookies; cookie-only refresh 200 (rotated); garbage cookie 401 + both expired; bad login 401 + zero Set-Cookie
- 5 new screenshots (`docs/screenshots/19..23_*_session9.png`), md5-unique — incl. **23_dashboard_after_reload** (the E-1 evidence shot)

### Deferred (registered, not dropped)

P0-P3 register unchanged (H-02/H-08…H-13, M-*, L-*, I-*, B-6 eslint debt, F5 rate-basis, backend ruff debt); **cross-reload session persistence RESOLVED (E-1)**; e2e login-rate budget resolved structurally (settings knobs); NEW: cross-site `SameSite=None` cookie topology note (split-domain deployments). See P4 report §3.

### Commits

Conventional commits on `main` per P4 plan §8; pushed via `docs/ssh_git_wrapper_v3.py` (key shredded after push).

---

## 2026-11-21 — Session 7: P3 Sprint (Monetary Capacity, Truthful Invoice Form & Suite Depth)

**Base:** `5b237743` (main) · **Plan:** `docs/REMEDIATION_PLAN_2026-11-21_P3.md` · **Report:** `docs/REMEDIATION_2026-11-21_P3_REPORT.md`

### Environment (reused, re-verified)

- Rootless PG 17 (`/home/z/my-project/pg`, :5432) + Redis 8 (:6379) re-verified; schema loaded at v1.0.2 and **migrated in-place to v1.1.0** via the new §16 block during Task 1 (47 monetary columns widened; idempotent re-run verified).
- Baselines reproduced before any change: backend **514P/0F/5S**, frontend vitest **324/324**, typecheck **0 errors**, e2e **6/6** — the documented P2 state, exactly. P2 rate-effectiveness live-verified through the API (2023 SR → 0.0800).

### Audit (Mode C) — findings this session

Repo skills: `code-review-and-audit` (standard mode scoped to `apps/` + manual verification of all 24 scanner criticals — all false positives), `code-quality-standards`, `diagnosing-bugs`, `e2e-testing-lessons`, `writing-plans`, `planning-and-task-breakdown`. Real findings (full register in plan §0):

- **C-1 (= deferred H-03, Critical/compliance)**: 47 `NUMERIC(10,4)` columns cap all money at S$999,999.9999 — below the S$1M GST registration threshold; F5 Box 13 and ≥ S$1M lines/journal amounts raise `numeric field overflow` (verified live).
- **D-1 (High)**: New Invoice form submit was a TODO stub (`console.log` + mock UUID); `useCreateInvoice` dead code — the UI could not create documents.
- **D-2 (High, security + broken)**: `useInvoicePDF` read the token from `localStorage` — zero-JWT-exposure violation AND broken (token lives in module memory → `Bearer null` → 401).
- **D-3 (Medium)**: tax dropdown + preview hardcoded at 9%, ignoring the P2 `?effective_on=` API (backdated documents preview wrong).
- **D-4 (Low)**: `ALLOWED_HOSTS` missing from the backend `.env.example`.
- **D-5 (Low/coverage)**: e2e covered public navigation only (6 tests); no invoice-form or authenticated coverage.

### Remediation executed (TDD)

| Task | Change | Evidence |
|---|---|---|
| 1 (C-1/H-03) | Schema v1.1.0: 47 columns → NUMERIC(19,4); §16 idempotent in-place migration (generated-column drop→widen→re-add); 31 model/serializer sites; conformance gate asserts numeric precision (caught pre-existing `exchange_rate` 19,6 vs 12,6 — aligned DOWN); `add_line` applies `discount_pct` server-side | 5 tests RED→GREEN; census 0 × (10,4); suite 514→519 |
| 2 (D-3) | `useTaxCodes(orgId, effectiveOn?)` + `endpoints.gst`; engine `rateOverride` (fail-closed); form watches issue_date; dropdown shows `CODE · rate%` | 8 tests RED→GREEN |
| 3 (D-1) | `lib/invoice-submit.ts` pure adapter (contact+document payloads, readiness validation); `use-accounts` hook; per-line Account select; real submit flow + error banner; `useCreateInvoice` retyped | 14 tests RED→GREEN; `rg useCreateInvoice` 0 → 2 importers |
| 4 (D-2) | `fetchWithAuth` extracted; `api.blob()` on the single auth path; localStorage read deleted | 3 tests RED→GREEN; `rg localStorage…accessToken` empty |
| 5 (D-5) | `e2e/auth.spec.ts` + `e2e/invoices.spec.ts` (real UI login → client-side nav; account/tax-code/preview assertions; NO submission); `test:e2e:full`; Radix pointer-capture mocks in setup.ts | 13 e2e total; default 9+4skip; full 13/13 ×2 |
| 6 (D-4) | `ALLOWED_HOSTS` in backend `.env.example` | 15/15 settings-read vars listed |

### Final gate (all Verified, executed)

- `pytest --reuse-db --no-migrations -q` → **0 failed, 519 passed, 5 skipped** (+5)
- `pytest tests/invariants -q` → **20 passed** · `pytest tests/security -q` → 32 passed, 3 skipped
- `manage.py check` → 0 errors (1 known W001) · ruff: touched files 15 before == 15 after; new files clean
- Web: typecheck 0 errors · vitest **349/349** (+25; 26 files) · eslint on touched files clean · e2e default **9 passed + 4 gated skips**, full **13/13** (twice)
- 5 new screenshots (`docs/screenshots/14..18_*_session7.png`), hash-unique — incl. the new-invoice form with the account dropdown open and a S$1.5M line

### Deferred (registered, not dropped)

P0/P1/P2 register unchanged (H-02/H-08…H-13, M-*, L-*, I-*, B-6 eslint debt, F5 rate-basis, backend ruff debt); NEW this session: **cross-reload session persistence** (backend returns tokens in the body, sets no cookie; the provider discards the refresh token; `tryRefreshToken` posts an empty body the backend 400s — needs a design decision), the **invoice-form existing-contact picker**, and the **e2e login-rate budget** (7 logins/full-run vs 10/min-per-IP). See P3 report §3.

### Commits

Conventional commits on `main` per P3 plan §5; pushed via `docs/ssh_git_wrapper_v3.py` (key shredded after push).

---

## 2026-11-21 — Session 5: P2 Sprint (Test Gates & Rate-Effectiveness Truth)

**Base:** `4acece81` (main) · **Plan:** `docs/REMEDIATION_PLAN_2026-11-21_P2.md` · **Report:** `docs/REMEDIATION_2026-11-21_P2_REPORT.md`

### Environment (reused, re-verified)

- Rootless PG 17 (`/home/z/my-project/pg`, :5432) + Redis 8 (:6379) restarted; schema v1.0.2 confirmed in both DBs (30 domain tables; the seed's system SR rate history 0.07/0.08/0.09 is present in `test_ledgersg_dev` and drove the per-code `effective_on` design).
- Baselines reproduced before any change: backend **499P/0F/5S**, frontend vitest **321/321** — the documented P1 state, exactly.
- Installed chromium v1208 + headless shell to match `@playwright/test` 1.58.2 (session 3's executable-path workaround no longer needed).

### Audit (Mode C) — findings this session

Repo skills: `code-review-and-audit` (audit_runner standard mode + per-finding manual verification), `code-quality-standards`, `diagnosing-bugs`, `e2e-testing-lessons`, `browser-testing-with-devtools`. Scanner "criticals" = the same 21 session-3 false positives. Real findings (full register in plan §0):

- **B-1** (High, infra): playwright config declares 5 browser projects, only chromium installed → `npm run test:e2e` errors 24/30 tests pre-assertion.
- **B-2** (Medium, a11y): login page fails the repo's own axe e2e (no `<main>`, no `<h1>` — CardTitle is an h3; terms text 3.3:1 contrast); the scan also races the auth redirect chain.
- **B-3 = H-04** (High, compliance): rate history resolution broken end-to-end — unordered `.first()` (verified returning SR=0.07 today), unordered list endpoint, calculate endpoint fail-open to silent 9% with a triple-broken code branch, `add_line` no effectiveness check.
- **B-4** (Medium, env): web `.env.example` — 7/9 vars read nowhere; `BACKEND_URL` missing.
- **B-5** (Medium, gates): no typecheck script; `tsc --noEmit` red with 25 pre-existing test-file errors.
- **B-6** (Low, debt): eslint 87E/3755W repo-wide (pre-existing; registered).
- **B-7** (High, broken feature): `POST /gst/tax-codes/` always 500 (phantom `box_mapping` kwarg → TypeError; also fixed `chk_io_flag` compliance via is_input/is_output defaults).

### Remediation executed (TDD)

| Task | Change | Evidence |
|---|---|---|
| 1 (B-1) | playwright.config.ts: chromium default, `PLAYWRIGHT_PROJECTS=all` opt-in, list+html(open never) reporters | `--list`: 6 vs 30 tests; e2e 6/6 |
| 2 (B-2) | Login `<main>` + explicit h1; contrast fix; deterministic axe (await redirect) | 3 vitest RED→GREEN; e2e axe GREEN |
| 3 (B-7) | box_mapping kwarg removed; f5_* forwarded; `create_tax_code` io-flag defaults | 3 tests RED (TypeError) → 201 GREEN |
| 4 (B-3/H-04) | `get_tax_code_by_code(as_of)` + `is_effective()`; `list_tax_codes(effective_on=…)`; calculate: `tax_code`+`document_date`, legacy alias, fail-closed 404; `add_line` fails closed on stale codes | 12 tests RED→GREEN |
| 5 (B-4) | Truthful `.env.example` (live vars + reserved section) | per-var rg audit |
| 6 (B-5) | `typecheck` script; `test:all` chain; 25 errors repaired | tsc 0 errors; vitest still green |

### Final gate (all Verified, executed)

- `pytest --reuse-db --no-migrations -q` → **0 failed, 514 passed, 5 skipped** (+15 new)
- `pytest tests/invariants -q` → 15 passed · `pytest tests/security -q` → 32 passed, 3 skipped
- `manage.py check` → 0 errors (1 known W001) · ruff: touched files 19 before == 19 after (pre-existing only); new files clean
- Web: `npm run typecheck` → 0 errors (was 25) · `npm test` → **324 passed (25 files)** · `npm run test:e2e` → **6/6 (chromium)**
- 5 new screenshots (`docs/screenshots/09..13_*_session5.png`), hash-unique

### Deferred (registered, not dropped)

P0/P1 register unchanged (H-02/03/08/09r/10/11/13, M-*, L-*, I-*, backend ruff debt); NEW this session: **B-6** frontend eslint debt (87E/3755W), **F5 rate-basis semantics** (returns at computation date vs lines at document date — needs a period-cut decision, ties into H-02), and the frontend wiring of `?effective_on=` for the invoice form's tax-code dropdown. See P2 plan §4.

### Commits

Conventional commits on `main` per P2 plan §5; pushed via `docs/ssh_git_wrapper_v3.py` (paramiko shim; key shredded after push).

---

## 2026-11-21 — Session 3: P1 Sprint (Green Suite & Contract Truth)

**Base:** `342d16fb` (main) · **Plan:** `docs/REMEDIATION_PLAN_2026-11-21_P1.md` · **Report:** `docs/REMEDIATION_2026-11-21_P1_REPORT.md`

### Environment (rebuilt from scratch this session)

- Rootless PostgreSQL 17 via `docs/setup_pg_z.sh` + `skills/rootless-postgresql` (`/home/z/my-project/pg`, port 5432); role `ledgersg` (SUPERUSER, required by the schema's DO-block CREATE ROLE), databases `ledgersg_dev` + `test_ledgersg_dev`, schema v1.0.2 loaded in both (30 domain tables + 2 token-blacklist tables).
- Redis 8.0.2 (rootless .deb extraction, `/home/z/my-project/redis`) — hard prerequisite for the suite (middleware membership cache).
- Backend venv via `pip install -e ".[dev]"`; frontend `npm install`.
- Baseline reproduced EXACTLY as documented: 26 failed / 465 passed / 5 skipped; invariants 12P; security 32P/3S; frontend 321/321.

### Audit (Mode C) — findings this session

Used `skills/code-review-and-audit` (audit_runner standard mode + manual verification of every scanner finding), `code-quality-standards`, `diagnosing-bugs`, `writing-plans`, `planning-and-task-breakdown`. The 21 scanner "criticals" were individually verified as test-fixture/docstring false positives. Real findings (full register in the plan §0):

- **A-1** (High): `test_api_endpoints.py` org fixture missing `UserOrganisation.accepted_at` → 25 of the 26 documented failures.
- **A-2** (High): `DocumentSummaryView` — phantom `DOCUMENT_TYPE_CHOICES`, invalid `PAID_PARTIAL` enum literal (×2), phantom `total` attribute, int-vs-Decimal `.quantize()` crash on empty orgs; same literal in `contact_service.deactivate_contact`.
- **A-3** (High): CoA `get_trial_balance` LEFT JOINs the non-existent `coa.account_balance` view → 500.
- **A-4** (Medium): `ValidStatusTransitionsView` missing `org_id` kwarg → 500.
- **A-5** (Medium): `test_create_organisation` payload bugs (`gst_reg_date` missing; `entity_type: pte_ltd` not in the CHECK vocabulary).
- **A-6** (High, packaging): `django-celery-beat` + `django-ratelimit` imported by settings but undeclared in `pyproject.toml`; `requirements.txt`'s beat 2.8.1 pin forces a Django 5.x downgrade.
- **A-7/A-8** (Low): `.env`/`.env.local` tracked, no gitignore rules; `apps/web/.env.example` referenced by README but missing; backend example incomplete.
- **A-9** (Low): schema header still said v1.0.1.
- **A-10** (Info): stale root `requirements.txt` second manifest.

### Remediation executed (TDD)

| Task | Change | Evidence |
|---|---|---|
| 1 (A-1/A-5) | Fixture `accepted_at=timezone.now()`; test payload `gst_reg_date` + `PRIVATE_LIMITED` | 26F → 4F (the 4 = the real bugs) |
| 2 (A-2) | `DOCUMENT_TYPES`, outstanding set `[APPROVED, SENT, PARTIALLY_PAID, OVERDUE]`, `total_incl`, Decimal-safe sums; contact-service sweep | New `tests/integration/test_document_summary.py` 5/5 (RED→GREEN) |
| 3 (A-3) | Trial balance rewritten on `journal.line` ⋈ `journal.entry` with optional `fiscal_year_id` | +3 invariant assertions (RED→GREEN) |
| 4 (A-4) | `get(self, request, org_id: str)` | status-transitions test green |
| 5 (A-6) | `pyproject.toml`: `django-celery-beat==2.9.0`, `django-ratelimit>=4.1,<5` | Clean-venv install + `manage.py check` pass, Django stays 6.0.2 |
| 6 (A-7/A-8) | `apps/web/.env.example` (new), backend example completed, `.gitignore` rules, `git rm --cached` env files | fresh copies are git-ignored |
| 7 (A-9) | Schema header → v1.0.2 | grep |
| 8 | Docs aligned (README, CLAUDE.md v2.6.0, AGENTS.md session-3 lessons, P1 report) | claims match executed evidence |
| 9 | 8 dev-server screenshots in `docs/screenshots/` (login, post-login, dashboard, invoices, ledger, banking, settings, reports) | unique PNGs verified by hash |

### Final gate (all Verified, executed)

- `pytest --reuse-db --no-migrations -q` → **0 failed, 499 passed, 5 skipped** (first fully green run)
- `pytest tests/invariants -q` → 15 passed · `pytest tests/security -q` → 32 passed, 3 skipped
- `manage.py check` → 0 errors (1 known W001) · clean-venv install path works
- `npm test` (web) → 321 passed (24 files)
- Ruff: new files clean; touched legacy files carry only pre-existing debt (210 → 208 on those files)

### Deferred (registered, not dropped)

P0 register (H-02/03/04/08/09r/10/11/13, M-02…M-16, L-*, I-*) unchanged; plus repo-wide ruff debt (1,311 findings) and the stale root `requirements.txt` manifest decision. See plan §4.

### Commits

Conventional commits on `main` per plan §5; pushed via `docs/ssh_git_wrapper_v3.py` (paramiko shim; key shredded after push).

---

## 2026-11-23 — Session 25 (P12: Mobile-Nav Truth & A11y Floor)

**Base:** `ba4357d4` (post-P11 + the user's session_24 log). PG/Redis
survived the recycle (verified: schema-qualified DBs, audit triggers);
venv/node_modules/chromium persisted; all baselines reproduced first
(backend 735P/0F/5S, vitest 511/511, tsc 0, coverage + build green, e2e
11 + 23 gated).

**Sprint focus (per instructions):** the mobile navigation menu + a
possible TailwindCSS v4 bug — audited LIVE with agent-browser at
375×812/800×1024/1280×800 and the repo skills' taxonomies
(`nextjs16-tailwind4` §9/§9.4/§10, `tailwind-patterns`, `astro-7-patterns`
§7). **Verdict: the nav works; no v4 bug exists** — the `display:flex`
reading was correct flex-item blockification (matched-rule trace proved
only `.inline-flex` + media-gated `.md:hidden` apply; the setup has no
legacy config). Plan: `docs/REMEDIATION_PLAN_2026-11-23_P12.md`
(2 Mediums + 4 Lows + 2 Infos, 9 tasks).

### Remediation executed (TDD)

| Task | Change | Evidence |
|---|---|---|
| 1 (A-1) | The mobile-nav overlay a11y floor in `shell.tsx`: Escape close, Tab-cycle trap, body scroll lock, focus-in on open, focus-return on close | 7 vitest (RED 6/7 → GREEN 7/7) + live browser re-verification |
| 2 (A-2) | `e2e/mobile-nav.spec.ts` — 3 gated authenticated specs (open+Escape; navigate+auto-close; desktop band) | 3/3 green in the live full run; gated skip with reason otherwise |
| 3 (A-3) | Lint-debt truth pass: 30 unused-vars, prefer-const, no-unescaped-entities, CustomTooltip hoist, dead mounted gate, unused catch binding, type-only const, middleware param | eslint whole-tree **79 → 45**; vitest 518/518; all gates green |
| 4 (A-4) | `data-scroll-behavior="smooth"` on `<html>` | The Next.js route-transition warning verified gone live |
| 5 (A-8) | `API_CLI_Usage_Guide.md` v2.5.0 — live re-verification block (9/9 envelopes, journal mount, login contract, credit-note reversal, dashboard endpoint), current metrics, session-persistence truth | Every claim executed live this session |
| 6 (A-9) | DEPLOYMENT.md counts; env examples no-drift | grep-level re-audit |
| 7 | Screenshots 66–71_session25 (desktop dashboard/invoices/reports; mobile nav-open/closed/ledger) | pixel-verified + md5-unique |
| 8 | Docs truth pass: README (P12 milestone + 1,290 counts), CLAUDE v2.16.0, AGENTS P12 patterns, PAD v3.8.0, SKILL v2.1.0 + lessons 51–54 | claims match executed output |

### Final gate (all Verified, executed)

backend **735P/0F/5S** (unchanged) · vitest **518/518** · typecheck 0 ·
coverage green · build:server green · eslint **45** (truthful register) ·
e2e default 11 + 26 gated · **live e2e:full 36P/1S/0F (37 specs)** · the
a11y behaviors re-verified live · API contracts re-verified live · 6
screenshots verified.

### Deferred (registered, not dropped)

The 36 `no-explicit-any` findings (unchanged policy); the mounted-gate
`set-state-in-effect` pair (registered — behavior-sensitive to replace);
3 `exhaustive-deps`; the `incompatible-library` + 2 `immutability`
informationals; the recharts mount-noise class (chart verified correct);
everything carried forward from P11's register.

### Commits

Conventional commits on `main` per plan §5; pushed via
`docs/ssh_git_wrapper_v3.py` (paramiko shim; key shredded after push).

## 2026-11-24 — Session 27 (P13: Transactional Truth, Header Consolidation & the Typed Suite)

**Base:** `69f13325` (post-P12). The sandbox recycle wiped PG's
usr/share tree + empty cluster subdirs (pg_logical/snapshots was
checkpoint-fatal) and Redis's binaries — both recovered per
`skills/rootless-postgresql` (debs re-extracted, subdirs restored,
liblzf added); the DBs, demo substrate, venv rebuild (uv), npm ci and
chromium-1208 all re-established; baselines reproduced exactly
(735P/5S, 518 vitest, tsc 0, eslint 45, live e2e 37P/0F — the P12
data-conditional skip now passes). A double-fork daemonizer now keeps
the dev stack alive across tool calls (the one-call constraint is
lifted). Plan: `docs/REMEDIATION_PLAN_2026-11-24_P13.md` (1 Critical +
3 High + 10 Medium + the docs register, 20 tasks).

**Sprint focus (live):** the mobile nav re-verified working at
375/800/1280; **no Tailwind v4 bug** — re-settled with an
@layer-recursing rule trace (only `.inline-flex` + the media-gated
`.md\:hidden` match; the trap log swept clean). Two REAL nav edge-state
defects found and fixed: the closed drawer was keyboard-focusable
(H-2) and the overlay covered the X toggle (M-1).

### Remediation executed (TDD — 15 backend + 12 vitest + 3 e2e specs, all RED first)

| Task | Change | Evidence |
|---|---|---|
| 1 (B-1 Critical) | The DRF exception handler's 500 fallback now calls `transaction.set_rollback(True)` — unhandled exceptions can no longer COMMIT partial financial state | 2 gates: handler-level + full dispatch (a register-halfway user committed behind the 500 pre-fix; rolled back post-fix) |
| 2 (B-2) | GST quantum `Decimal(1).scaleb(-rounding)` — the IRAS 2dp unit (was 0.001) | Sub-cent tests: 100.05×0.09 → 9.00 (was 9.005); live curl proof |
| 3 (H-1+L-1) | middleware.ts deleted; ALL headers consolidated into next.config.ts (COOP/CORP/COEP, prod upgrade-insecure-requests, the full Permissions-Policy; X-XSS-Protection dropped) — production no longer ships unsafe-eval/inline | 8-test header-config gate (RED 5 → GREEN 8) + live served-header verification + the deprecation warning gone |
| 4 (H-2) | Closed drawer `invisible md:visible` + `transition-[transform,visibility]` | vitest (RED→GREEN 9/9) + e2e visibility assertions (a role locator CANNOT resolve the hidden link — the a11y exclusion IS the fix) |
| 5 (M-1) | Header z-50 — the X toggle is the real hit target while open | e2e elementFromPoint probe + click-closes |
| 6 (M-3) | mutations `retry: 0` (double-submission hazard removed) | config gate |
| 7 (B-5) | ImmutableModel raises the TYPED ImmutabilityError (409, not 500) | 2 gates incl. the handler envelope |
| 8 (B-6) | 17 naive date.today()/datetime.now() sites → timezone.localdate()/now() | the new source-scan gate (17 offenders → 0) |
| 9 (B-7) | SIMPLE_JWT + DATABASES copy-on-write in all settings modules | 3 identity gates (value comparisons are .env-maskable — the lesson) |
| 10 (B-10) | InvoiceNow endpoints → typed 404s (was raw DoesNotExist 500s) | 2 gates |
| 11 (B-11) | create_reversal atomic (both phases) — no orphan reversals | the marking-failure gate |
| 12 (B-13) | Service balance tolerance aligned to the DB trigger's 0.0001 | the 0.0005 boundary gate |
| 13 (B-14) | Health 503 body generic (detail to the logger) | the marker-string gate |
| 14 (W-3+M-4) | The 36 any-casts cleared (35 via the in-file typed-cast pattern; banking-client got the real BankAccount type) + per-glob coverage thresholds for src/lib | eslint **45 → 9**; coverage green at both ratchets |
| 15 (L-8+D-9) | .env.example: LOG_DIR in the root index + the documented E2E section in web | grep cross-checks |
| 16 | Playwright expect.timeout + the axe-scan/visibility/hit-target mobile-nav specs | 40 specs live-green |
| 17 | Screenshots 72–79_session27 (8, pixel+DOM verified, md5-unique) | the capture driver's DOM truths |
| 18–19 | Docs truth pass (AGENTS header + P13 patterns, PAD metrics, SKILL §4 + v2.2.0 lessons 55–58, README badge/blocks/quickstart + the P13 milestone, CLAUDE rows + the cookie-claim correction, DEPLOYMENT §12.1–12.4 production ops + the path/venv/Redis fixes, API guide v2.6.0 + the P13 addendum, ci.yml) | every count vs executed output |

### Final gate (all Verified, executed)

backend **750P/0F/5S** (invariants 34P; security 69P/3S; production
boots behind its gates) · vitest **530/530** · typecheck 0 · coverage
green (63/51/52/62 + src/lib 73/52/74/71) · build:server green ·
eslint **9** (the deferred register only) · e2e default 11 + 29 gated ·
**live e2e:full 40P/0F/0S (40 specs)** · the served headers + the boot
log verified live · the GST live proof (9.00) · 8 screenshots verified.

### Deferred (registered, not dropped)

B-3 (TenantModel auto-org), B-4 (is_superadmin policy), B-8 (stale
service.py+scripts), B-9 (membership-cache invalidation), B-12
(on_commit for Peppol), B-15..B-19, M-2 (scroll-lock hardening), L-2..L-7,
L-9, L-10, the 9 remaining eslint findings (unchanged policies), the
ruff register, D-24 — plus everything carried forward from P11/P12.

### Commits

Conventional commits on `main` per plan §5; pushed via
`docs/ssh_git_wrapper_v3.py --remote git@github.com:nordeim/ledgersg.git`
(paramiko shim; key shredded after push).

---

## 2026-11-26 — P15 Sprint: Tree Repair, P14 Completion & the Runtime-Role Gate (session 30)

**Base:** `4ad18d2e` · **Plan:** `docs/REMEDIATION_PLAN_2026-11-26_P15.md` ·
**Report:** `docs/REMEDIATION_2026-11-26_P15_REPORT.md`

The interrupted session-29 had committed its P14 work to wrong paths
(`2bcb43f0`): the Payment MODEL was overwritten by the payment SERIALIZER
(circular import — the backend could not run `manage.py check`), and the
C-1/C-2/H-05b/H-3 fixes sat stranded at `apps/backend/` root. This sprint
repaired the tree and completed the P14 remediation end to end.

### What was fixed (TDD where implementations were missing; every committed RED test diagnosed)

| Task | Fix | Evidence |
|---|---|---|
| R-0 (the repair) | Payment model restored from `2bcb43f0~1`; the stranded fixes relocated (period_lock, validators with both M-form lengths, the C-1 set_config block, the C-2/H-05b ports); 5 test-side bugs in the never-run RED suite fixed | backend boots (check green); the suite's failures map only to missing implementations |
| C-2 | FILED/AMENDED returns immutable — even `force=true` (409) | 5 tests + the tie-out ordering fix |
| H-1 + H-2 | allocation cap + the instalment status set | the committed contract tests green |
| H-3 | the GST period lock on approve/void/journal/payment-void | 4 tests (refusals + the after-period control) |
| H-4 | credit notes require + cap against the original invoice; `related_document_id` through the API | 9 guard tests + the P11 tests updated (8) |
| H-5 | the GST-registration guard (verified — the interrupted session placed it correctly) | 9 tests green |
| H-6 + M-6a + M-7c | schema **v1.2.0 §17**: RLS on the six remaining tenant tables; the audit log append-only; `audit.log_change` pins search_path; the §17c NULL-context role refinement (the live smoke exposed the pre-context role read) | conformance tests + the live psql probes |
| C-1 + H-7 | org creation sets the RLS context; **the runtime-role gate live: 13/13 smoke steps as `ledgersg_app`** (org creation 201 — the audit's 500 inverted) | rls_smoke + isolation probes (fail-closed, append-only) |
| M-4 | the line-item schema (merged into the existing serializer — F811 caught the duplicate); 400s not 500s | 7 tests |
| M-1 | honest ACRA/IRAS validators wired (both M-form lengths + the UEN form; the invalid `^\d{10}$` branch gone) | 23 parametrised cases + the serializer contracts |
| X-1 | the hardened lxml parser (`_HARDENED_PARSER_FLAGS` — the flags are write-only) | 5 tests |
| H-05b | override_reason required with box overrides; the reason + deltas persist into notes | 5 tests |
| H-04b | NRIC PayNow masking on read + masked-echo rejection (PDPA) | 4 tests |
| M-5 | the Viewer role is read-only (contacts + send gated on `can_create_invoices`) | 6 tests |
| M-10 | the tax-code band dedupe (org shadows system; history intact) | 3 tests (RED first) |
| H-8 | django 6.0.10, DRF 3.18.3, lxml 6.1.3, weasyprint 70, next 16.4.6, zod 4.6.7 — **0 known advisories on both production sets** | full gates on the upgraded tree |
| H-9 | the service.py key gate + env ALLOWED_HOSTS; the Docker per-boot strong key | 3 settings-gate tests |
| F-A + F-B | the e2e bootstrap creates the F5 return; linked-CN + cap-headroom + real-UEN contracts; **single-flight refresh** (the rotation race killed sessions mid-suite) | live e2e 40P/0F/0S + 2 vitest |

### Final gate (all Verified, executed)

backend **834P/0F/5S** (invariants 34P; security 72P/3S) · vitest **532/532**
· typecheck 0 · coverage green at both ratchets · eslint **9** ·
build:server green · e2e default 11P + 29 gated · **live e2e:full
40P/0F/0S** · **rls_smoke 13/13 as `ledgersg_app`** · GST live proof 9.00 ·
**mobile-nav 17/17 (the navigation works; no Tailwind v4 bug exists)** ·
8 verified screenshots (80-87_session30) · pip/npm audits clean.

### Deferred (registered, not dropped)

The UEN checksum (pending the official ACRA algorithm) + F-form foreign UENs;
the H-3 DB-trigger layer; the H-05b attachment model; everything carried
forward from the P14 §6 and P13 registers (audit1 M-2/M-3/M-6b/M-8/M-9/M-7-
full; audit2 M-01..M-05/M-07/M-08; B-3/B-4/B-8/B-9/B-12/B-15..B-19; the
frontend L-batch; the 9 eslint findings; the ruff register).

---

## 2026-11-26 — P16 Sprint: Production Truth (session 32)

**Base:** `d7f7d9b7` · **Plan:** `docs/REMEDIATION_PLAN_2026-11-26_P16.md` ·
**Report:** `docs/REMEDIATION_2026-11-26_P16_REPORT.md`

Three parallel deep audits (backend P15-diff, frontend, cross-cutting
truth) + lead verification of every Critical/High in source and build
artifacts. The headline finding: **the shipped production app could not
hydrate** — the static production CSP blocked Next's non-nonced inline
bootstrap scripts on every page, and the dev-mode suite structurally
could not catch it.

### What was fixed (TDD — every behavioural fix RED first)

| Task | Fix | Evidence |
|---|---|---|
| FE-C1 (Critical) | The nonce-based production CSP: `src/lib/csp.ts` + `src/proxy.ts` (per-request nonce on request+response headers), `force-dynamic` in the root layout (nonces require dynamic rendering — verified against the bundled Next 16 guide), the CSP removed from next.config (single source, the P13/H-1 trap) | 8 builder tests + **`scripts/prod-csp-smoke.js` 5/5 on the real standalone build** (nonce served, hydration happened, zero violations) |
| BE-H1 | service.py's from-scratch MIDDLEWARE (the Docker API entrypoint) had dropped TenantContext + AuditContext + CSP + WhiteNoise — derived from base now, gated in every HTTP-serving settings module | 4 settings-gate tests |
| BE-H2 | The dedicated `POST /payments/{id}/allocate/` still demanded APPROVED-only (the P14 instalment fix missed the wire serializer) — shares `ALLOCATABLE_STATUSES`; the dead twin serializer deleted | 4 endpoint-level tests |
| BE-M batch | The payment-row `select_for_update` (TOCTOU); NaN/Infinity box-override rejection (money() is_finite + both seams) + HALF_UP on the FX paths; the line-total NUMERIC(19,4) bound; atomic create+allocate (no orphaned payments behind 400s); `discount_pct` forwarded on line-add; system tax-code rows read-only; file/amend row locks | Each RED → GREEN |
| BE-L batch | CSV bytes-once decode (latin-1 actually imports); the normalized-UEN write-back; SENT restored on allocation release (the invoicenow_sent_at evidence; the email residual registered); the payment-void reversal date is localdate; the audit dedup (the trg_audit_payment trigger is the truth); the period_lock docstring corrected + the advertised payment-void lock test written | Each RED → GREEN |
| FE-H1 | The dashboard query key was inverted — all 10 mutation→dashboard invalidations were no-ops. The page now consumes `useDashboardMetrics` (orgId-first) | The QueryCache-key test |
| FE-H2 | Org creation dead-ended on a stale closure (`switchOrg` read the PRE-creation org list) — the provider's new `selectOrgById` selects without list state | The select-without-list test + the live p10 e2e |
| FE-H3 | The frontend UEN regex rejected the ACRA LLP/society forms the backend accepts — mirrors all three forms; the dead duplicate validator deleted | 6 format tests |
| FE-M/L batch | The open-redirect guard on `?redirect=`; the drawer closes at the md crossing (scroll lock released); the broadened focus trap + `role="dialog"`/`aria-modal`; the e2e serial contract in the Playwright config; the dead code swept; the single-flight shared-FAILURE path pinned | All RED → GREEN; eslint parity 9 held |
| Docs truth pass | Every stale count/version/claim fixed across CLAUDE/README/PAD/SKILL/AGENTS/ci.yml/API guide/DEPLOYMENT (incl. the §17 upgrade note + the smoke step); Current_Project_Status.md archived; 7 tracked logs + 49 backup/plan files untracked | The audit's consolidated table, row by row |

### The mobile navigation (the sprint's named focus — settled live, third time)

**17/17 live probe checks PASS on the remediated tree** (375/800/1280:
toggle, closed-drawer `visibility:hidden`, overlay, X hit-target,
transition-aware close, no overflow, no console errors, sticky
tablet/desktop, the v4 space-y trap sweep clean). The v4 setup is
CSS-first clean. **The navigation works; no TailwindCSS v4 bug exists.**
The P16 changes improved it: dialog semantics, the full focusable set in
the trap, and the resize-past-md lock release.

### Final gate (all Verified, executed)

backend **860P/0F/5S** (invariants 34P; security 76P/3S) · vitest
**554/554** (64 files) · typecheck 0 · coverage green at both ratchets ·
eslint **9** (exact parity) · build:server green (dynamic + proxy) ·
**the production-CSP smoke 5/5 (NEW)** · e2e default 11P + 29 gated ·
**live e2e:full 40P/0F/0S** · **rls_smoke 13/13 as ledgersg_app** ·
**mobile-nav 17/17** · 8 verified screenshots (88-95_session32).

### Deferred (registered, not dropped)

The ContactPicker WAI-ARIA combobox (the next sprint's first item);
email-sent documents restore to APPROVED (needs a lifecycle-evidence
column); backend list pagination; the audit-log INSERT WITH CHECK (TRUE)
forgery surface + the tax-code row-capture note (schema tier); the ruff
mechanical debt (register re-baselined honestly: ~1216 whole-tree);
plus everything carried forward from the P15 register (UEN checksum,
H-3 DB trigger, H-05b attachment model, M-2/M-3/M-6b/M-8/M-9/M-7-full,
audit2 M-01..M-08, B-3/B-4/B-8/B-9/B-12/B-15..B-19, the L-batch, the 9
eslint findings).

---

## 2026-11-27 — P17 Sprint: Concurrency Truth, the 400-Contract Sweep & the Celery Tenant Context (session 34)

**Base:** `e9b2626d` · **Plan:** `docs/REMEDIATION_PLAN_2026-11-27_P17.md` ·
**Report:** `docs/REMEDIATION_2026-11-27_P17_REPORT.md` · **Session log:**
`docs/session_34.md`

Executed across two context windows (plan + Phase 1 + most of Phase 2 in
window 1; completion, the docs truth pass, the live gates, the screenshots
and the push in window 2 — the workspace, PG, Redis and the double-forked
dev stack persisted, zero loss). Fresh clone: PostgreSQL 17 + Redis 8
rootless, both DBs schema-loaded, every documented baseline reproduced
green (860P/0F/5S · vitest 554/554 · tsc 0 · eslint src 9 · mobile-nav
17/17 · prod-CSP 5/5). Three parallel deep audits + lead verification of
every Critical/High; the session_29 `payment.py`/serializer regression
question settled via git history (no surviving regression — the P15 repair
+ the P16 allocation completion hold; the P17 guards then harden those
exact seams).

### What was fixed (TDD — every behavioural fix RED first)

| Task | Fix | Evidence |
|---|---|---|
| BE-H1 | The double-reversal guard: `select_for_update` + `is_reversed` re-check in `create_reversal` — two reversals of one journal entry posted the swap-side lines twice (every account 2x misstated, trial balance still balanced) | double-reversal refused 400; first reversal GREEN |
| BE-H2 | The double-void guard: row lock + `is_voided` re-check post-lock (the TOCTOU closed) | double-void refused; single void unchanged |
| BE-H3 | The Celery tenant context: NEW `common/tenant_context.py` (the middleware's SET LOCAL semantics, reusable); the invoicing/peppol task bodies wrap in it; the three dispatch seams dispatch **on commit** — real workers run inside the RLS tenant GUC, eager mode bit-identical | the GUC asserted mid-flight + a real RLS-enforced probe as `ledgersg_app` (a vacuous first test caught: the test connection ran as superuser) |
| BE-M batch | Typed GST box parse (None/dict/"garbage" → 400); bulk-allocation UUID field errors; UEN normalize-then-validate on org PATCH (case-dodge UNIQUE refused); tax-rate range on update; reconcile double-match typed 400 + payment/transaction locks; uuid route converters (404 not 500); `select_related` on the three list services; the negative-membership cache fix | each RED → GREEN (9-file API-contract batch + the concurrency batch) |
| BE-L batch | `/admin/` gated off outside DEBUG; the Django 6 `STORAGES` manifest migration (the legacy `STATICFILES_STORAGE` was a silent no-op — WhiteNoise compressed-manifest storage is actually active); `exchange_rate` at its true 6-dp wire precision | 2 settings-gate tests; the 6-dp round-trip test |
| Schema §15c (v1.2.1) | The Django framework tables, SQL-First, idempotent — the fresh-host pytest gap: transactional teardowns flush `django_session`/`django_admin_log`/`django_content_type`, absent from a schema-only v1.2.0 load | both DBs re-verified (30 domain tables / 47 numeric(19,4) columns — the fresh-load count; the dev DB's test twin carried 10 legacy migrate leftovers inflating earlier counts); header bumped |
| FE-M1 | The `--color-success: #00FF94` token — 14 dead `text-success`/`bg-success` usages across 10 files now compile (the PAID badge, reconcile forms, match scores, fiscal/InvoiceNow cards) | design-token gates + **2 live token elements on the Payments tab screenshot** |
| FE-M2 | The 6 eslint errors cleared with real refactors (the `mounted` trio → `useSyncExternalStore`/derive-during-render; the immutability pair → a hoisted capture; prefer-const) — no rule weakening | whole-tree **0 errors / 5 parity warnings**; the CI lint gate added (`--max-warnings 5`) |
| FE-M3/M4 | The proxy nonce-CSP orchestration unit-gated (request CSP + x-nonce + response CSP + rotation); the unsaved-changes `beforeunload` guard wired (the store's write side finally has a reader) | 4 + 6 tests |
| FE-L batch | The four dead CSP origins dropped; the dead utilities swept (`bg-background`/`text-foreground`); the dead code deleted (`useComplianceAlerts`, `useCurrentOrg`, the invoice-store's unconsumed fields + `createInvoiceLine`); the org-selector as a real Radix-contract menu (aria state, menuitemradio, Escape/outside-click, arrow-key roving, focus return); the redirect carry on refresh failure; the shared `uenSchema` on all three surfaces | 6 menu tests + the 3-form ACRA parity tests; deletion-only (tsc 0, suite GREEN) |
| Docs truth pass | DEPLOYMENT.md re-verified end to end (the §9 GST example fixed `M9034567K` — the old value failed the P15 validator live; §11 token/`ORG_ID`/Bearer flow — every probe re-executed; §4/§13 the v1.2.1 path; §7 counts + the pytest-runner note); README (badge/status/milestones/env tables/dead refs/URLs/footer); AGENTS/CLAUDE/PAD/SKILL normalized; the API guide P17 addendum; the AGPL-3.0 LICENSE; ci.yml (`DATABASE_URL` no-op removed + the lint gate); the tracked status artifact untracked; the scripts' self-resolving requires; both `.env.example`s corrected | the audit's findings row by row; the §9/§11 flows executed live |
| Deliverables | 8 DOM-verified screenshots (`docs/screenshots/96-103_*_session34.png`, md5-unique) incl. the open org-selector menu; `docs/session_34.md`; this worklog | `scripts/capture-screenshots-session34.js` |

### The named focuses (settled live)

**Mobile navigation:** 17/17 probe checks PASS on the remediated tree
(375/800/1280) — **no TailwindCSS v4 bug exists** (fifth consecutive live
settlement, this time on a fresh clone AND the remediated tree).
**`payment.py`/serializer (session_29):** git history + the live gates
confirm no surviving regression.

### Final gate (all verified, executed)

backend **882P/0F/5S** (887 collected; invariants 34P; security 78P/3S) ·
vitest **582/582** (69 files) · tsc 0 · whole-tree eslint **0 errors / 5
parity warnings** · build:server green · prod-CSP smoke **5/5** · e2e
default 11P + 29 gated · **live e2e:full 40P/0F/0S** (consecutive run) ·
**rls_smoke 13/13 as `ledgersg_app`** · **mobile-nav 17/17** · 8 verified
screenshots (96-103_session34) · schema **v1.2.1** (§15c).

### Deferred (registered, not dropped)

The full P16 register carries forward (ContactPicker WAI-ARIA combobox,
email-restore lifecycle evidence, list pagination, the audit-log INSERT
WITH CHECK surface, the ruff ~1216 mechanical register, UEN checksum,
H-3 DB-trigger layer, H-05b attachment model, the B/L batches) plus:
BE-M4's full invalidation design; the in-app route guard for unsaved
invoice work; BE-L5 (CSV size cap/dedup); the CSP report-endpoint log
bound; `display_money`/`round_half_up` consistency; journal serializer
tolerance; lines `max_length`; `get_allocations` org-filter
defense-in-depth; the 5 documented eslint warnings.

## 2026-11-27 — P18 Sprint: Statutory-Record Locking, the Contrast Debt, the Celery Coverage Completion & the Fresh-Host Truth (session 36)

**Base:** `56f8f835` · **Plan:** `docs/REMEDIATION_PLAN_2026-11-27_P18.md` ·
**Report:** `docs/REMEDIATION_2026-11-27_P18_REPORT.md` · **Session log:**
`docs/session_36.md`

Executed across two context windows (the audits, the plan, Phases 1–5
and most gates in window 1; the live e2e completion, the screenshots,
the deliverable docs and the push in window 2 — the workspace, PG data,
Redis and the double-forked dev stack persisted, zero loss). The P17
baselines reproduced green on the carried-forward workspace (882P/0F/5S
· vitest 582/582 · tsc 0 · eslint 0E/5W · mobile-nav 17/17). Three
parallel deep audits → 0 Critical / 3 High / 20 Medium / 20 Low; every
High hand-verified in source before planning. The window-2 incident
register: the dev backend restarted in window 1 was tool-call-tied and
died mid-e2e (the daemonize lesson re-learned — both backends ran
daemonized for the final gates); the fresh-schema e2e bootstrap contract
settled (user → org → contact per DEPLOYMENT §9 steps 1–3, then the p11
self-bootstrap; a killed first run can strand the demo UEN on the
incidental contact — surgically reset, the guard verified
self-excluding).

### What was fixed (TDD — every behavioural fix RED first)

| Task | Fix | Evidence |
|---|---|---|
| BE-H1 | The statutory-record locking: `generate_f5` + `review_return` wrap in `transaction.atomic()` + `select_for_update()` + post-lock status re-check (mirroring `file_return`) — pre-P18 a FILED F5 could be raced and overwritten with recomputeds while `filed_at` stayed populated (the P14/C-2 regression shape reopened through a TOCTOU) | file-then-recalculate race simulation → refused, FILED intact; review-after-file refused |
| BE-M batch (concurrency) | `unallocate`/`unreconcile` locks (the allocate/reconcile lock orders, `ResourceNotFound` preserved via `select_related`); `convert_quote_to_invoice` quote lock + re-check; `add_line`/`remove_line` document lock + typed IntegrityError; the credit-note cap read under the original's row lock inside `create_document`'s atomic; `create_entry` header/archived-account gate + `archive_account` lock | the P18 concurrency contract file (interleavings each RED → GREEN) |
| BE-M1/M7 (Celery) | the three Peppol task bodies wrap in `tenant_context` (org from the log row/task arg); `queue_task` under `ALWAYS_EAGER=False` fires `.delay` only after commit, never on rollback | the GUC asserted mid-flight (`django_capture_on_commit_callbacks` — the TestCase outer-transaction trap caught and fixed) |
| BE-L batch | email task terminal classification (no retry on `DoesNotExist`/`ResourceNotFound`); `send_email` gated to APPROVED SALES_INVOICE; `_validated_exchange_rate` typed 400 on garbage input; `<uuid:transaction_id>` route converters; `create_return_periods` UNIQUE catch → clean refusal | the API-contract RED file + 5 stale-contract tests updated with documentation |
| Schema §15c (v1.2.2) | `django_session` + `django_admin_log` completed into §15c (idempotent, SQL-First; the beat tables stay a documented opt-in); the reload exposed and fixed a real portability bug — index names can't be schema-qualified in `CREATE INDEX` | 5 schema-gate tests; both DBs re-loaded, fresh-load count re-verified (30 domain tables) |
| FE-H1/M2/M3 (the contrast debt) | the three `bg-success text-white` badges → `text-void` (PAID, Registered, Configured) + the badge/button-destructive/OVERDUE sweep; `--color-text-muted` → `#8A8A8A`; the header claim corrected to WCAG AA (pairs verified ≥4.5:1) — the P17 token fix had made white-on-neon-green compile at 1.33:1 | NEW permanent regression wall `contrast-pairings.test.ts` (every `bg-success`/`bg-alert` pairing enumerated, `text-white` fails) + the computed WCAG-ratio token test; **live: the PAID badge capture pairs `bg-success text-void`** |
| FE-M1/M4/L3 | the drawer Escape defers to the open org menu (nested close order); the customer UEN → shared normalizing `optionalUenSchema` + the org form `uenSchema.safeParse` (empty-UEN semantics preserved); `hasUnsavedChanges` reset on submit success | nested-state test; the ACRA parity tests; the guard-hook extension |
| FE-L1 (the real Tailwind v4 bug) | `tw-animate-css@1.4.0` (v4-native) + `@import` in globals.css — the `animate-in`/`fade-in-0`/`zoom-in-95`/`slide-in-*` families on the Radix primitives compile again (the v3 `tailwindcss-animate` plugin had silently died in v4 — all dialog/select/toast animations were missing) | the compiled-CSS design-token gate (built through the repo's own postcss pipeline); **live: the open dialog computes `animation: enter 0.2s`** |
| CFG batch | the CI `e2e` job (the 11 always-green no-backend specs, chromium-only); the coverage ratchet's measured `src/hooks/**` floor (the honest ratchet); `@types/uuid` removed (uuid@13 ships its own types) | ci.yml lint+schema valid; the ratchet green; install parity |
| Docs truth pass | DEPLOYMENT.md §4 count 30 + the collectstatic step (§8/§12 + the Dockerfile) + the `PG_BASE` parametrization + the fresh-host completeness pass; both `.env.example`s gain `ENABLE_ADMIN` (the full var list re-audited — the user's named deliverable); README/PAD/SKILL/CLAUDE/AGENTS/Makefile anchor fixes; the API guide corrections + the P18 addendum | the audit's findings row by row; §1–§15 re-walked as the from-`git clone` path |
| Deliverables | 8 DOM-verified screenshots (`docs/screenshots/104-111_*_session36.png`, md5-unique, non-blank pixel-verified) incl. the P18 proofs (the PAID badge pairing, the settings badges, the animate-restored dialog); `docs/session_36.md`; this worklog | `scripts/capture-screenshots-session36.js` |

### The named focuses (settled live)

**Mobile navigation:** 17/17 probe checks PASS on the remediated tree
(375/800/1280) — **no TailwindCSS v4 bug exists** (seventh consecutive
live settlement; the P18 shell changes re-probed for regression).
**The real Tailwind v4 class of bug:** the v3 animate plugin's utilities
silently compiling to nothing in v4 — fixed via the v4-native
`tw-animate-css`, gated by the compiled-CSS test + the live dialog
capture.

### Final gate (all verified, executed)

backend **914P/0F/5S** (invariants 34P; security 83P/3S) · vitest
**601/601** (70 files) · tsc 0 · whole-tree eslint **0 errors / 5
parity warnings** · build:server green · prod-CSP smoke **5/5** ·
**live e2e:full 40P/0F/0S** · **rls_smoke 13/13 as `ledgersg_app`** ·
**mobile-nav 17/17** · 8 verified screenshots (104-111_session36) ·
schema **v1.2.2** (§15c completed).

### Deferred (registered, not dropped)

The full P16/P17 register carries forward (ContactPicker WAI-ARIA
combobox, in-app unsaved-work route guard, list pagination, the
audit-log INSERT WITH CHECK surface, the ruff ~1216 mechanical
register, UEN checksum, H-3 DB-trigger layer, H-05b attachment model,
CSV size cap/dedup, CSP report-endpoint bound, positive
membership-cache invalidation, journal serializer tolerance, lines
max_length, display_money consistency, email-restore lifecycle
evidence) plus: the PaymentsTab same-route prefill re-trigger (no
current producer), the list-envelope `{data}`/`{results}` unification,
the NULL-context SELECT policies on `core.user_organisation`/`core.role`
(documented tradeoff), the org-mid-flight dead-letter design beyond the
terminal classification, the remaining 5 eslint parity warnings.

---

## P19 Remediation — 2026-11-27 (session 38): the remove_line truth gap, the modal semantics debt, the ContactPicker & the route guard

**Base:** `99786f6a` (post-P18, all gates green). **Plan:**
`docs/REMEDIATION_PLAN_2026-11-27_P19.md` (anchor-validated);
**report:** `docs/REMEDIATION_2026-11-27_P19_REPORT.md`.
**Method:** TDD (RED → GREEN → full gate) for every behavioural fix;
conventional commits on `main`; `skills/` excluded; no DDL (schema
v1.2.2 carries forward).

### The audits (three parallel, Mode C; every High verified in source)

0 Critical / 3 High / 16 Medium / 22 Low. The headline: the P18 commit
`51bd46c6` claimed "add_line/remove_line lock the document" — only
`add_line` got the lock, and the RED run exposed that `remove_line` had
never worked at all (an `invoice=` filter against the `document` FK —
FieldError on every call; zero prior test coverage). The frontend
Highs: the four hand-rolled banking modals (no focus trap/Escape/dialog
semantics on the payment + reconcile primary flows) and the mouse-only
transaction-row expander (WCAG 2.1.1 Level A — keyboard users could
not reach Reconcile).

### What was fixed (TDD — every behavioural fix RED first)

| Task | Fix | Evidence |
|---|---|---|
| BE-H1 | `remove_line`: atomic + `select_for_update` + post-lock DRAFT re-check + the real FK (mirrors `add_line`) — the P18 truth gap; the method was also broken end-to-end (FieldError) | lock spy + the Case-B race probe (the approver wins the lock → the locked re-read refuses; APPROVED intact) + the happy path |
| BE-M batch | `unallocate` lock re-order payment→allocation→document (the AB-BA deadlock vs void/allocate); the archive-gate `cache.delete` (journal postings never invalidated the 5-min cache); `create_entry` account locks (sorted pre-lock — the line order itself was a deadlock risk); the return-periods savepoint (the P18 catch poisoned ATOMIC_REQUESTS); the status-task FULL tenant-context wrap (the RLS write ran outside the P18 block); the journal-list prefetch (31→2 queries); the five `<str:…>` uuid route islands | the P19 concurrency/contract files (order probe, cache-seed probe, savepoint-forced branch, context tracker, query counts, route 404s) |
| BE deferred pair | journal serializer tolerance `0.001`→`0.0001` (the P13 trigger boundary — the create gate and the `balanced` flag now agree); `display_money` finite gate (NaN rendered as "NaN") | the boundary tests at 0.0005; NaN/Infinity refusals |
| FE-H1 | the four banking modals → Radix `Dialog` (accessible names; bounded `max-h` internal scroll; the five unlabeled internal X buttons removed) | role=dialog + Escape + labeled close (vitest + the live capture 112) |
| FE-H2 | the transaction-row header → `<button aria-expanded aria-controls>` (keyboard-operable) | Enter/Space expansion + the Reconcile reach (vitest + the live capture 113) |
| FE-M2 | **the ContactPicker WAI-ARIA 1.0 combobox (the register's oldest P16 item)**: `aria-controls`/`aria-haspopup`/`aria-autocomplete` + `aria-activedescendant` roving with `aria-selected`, arrows/Enter/Escape/Home/End, options as real list items | the keyboard-interaction matrix (9 picker tests) |
| FE-M3 | **the in-app unsaved-work route guard (the register's #2 item)**: `UnsavedRouteGuard` — a document-capture click interceptor + confirm dialog while the invoice store is dirty (modified clicks and external hrefs pass through) | 5 guard tests (intercept/confirm/cancel/external/clean) + the live capture 115 |
| FE-M/L batch | the UEN edit regex (bank-account); the PAID badge unified `bg-success`; `scope="col"` on the invoices tables; the line-editor row-context labels (the orphaned grid roles dropped); the aria batch (back links, form labels, `role="alert"`); the GST checkbox dead token; the contrast gate's `color-warning`; 4 of 5 eslint warnings fixed + the TanStack one documented | the pairing gate enumeration; the getByRole({ name }) matrix; **eslint 0E/0W** |
| X-M batch | the enforced CSP carries `report-uri` (production violations were invisible); the CSV 5MB/10k-row typed caps (worker OOM); the compose celery-beat removed (its scheduler tables are an intentional §15c omission — a deterministic crash-loop); the PG_BASE fresh-host completion | csp.test.ts; the CSV cap tests; compose config valid; script/doc paths derived |
| X-L batch | the e2e password fallback (8 chars could never log in); `uuid` dep dropped; ALLOWED_HOSTS via decouple; the ci-summary gate includes security-scan; the P18 report erratum + the ci.yml version | grep sweeps; CI YAML valid |
| Deliverables | 8 DOM-verified screenshots (`112-119_*_session38.png` — the Radix dialog, the keyboard row, the combobox, the route guard, the unified PAID badge, the overviews); the P19 report; `docs/session_38.md`; this worklog | `scripts/capture-screenshots-session38.js` |

### The named focus (settled live — ninth consecutive settlement)

**Mobile navigation:** 17/17 probe checks PASS on the remediated tree
(375/800/1280) — **no TailwindCSS v4 bug exists**. The P19 shell/modal
changes (the Radix-ified banking dialogs) re-probed clean.

### Final gate (all verified, executed)

backend **937P/0F/5S** (+23 P19 tests) · vitest **619/619** (72 files)
· tsc 0 · whole-tree eslint **0 errors / 0 warnings** · **e2e:full
40P/0F/0S** (five spec locators adapted to the new modal/a11y
contracts; one real discovery — the import dialog's unnamed
bank-account select, labeled) · **rls_smoke 13/13 as `ledgersg_app`**
· **mobile-nav 17/17** · **prod-CSP 5/5** · schema v1.2.2 (no DDL).

### Deferred (registered, not dropped)

List pagination; the `{data}`/`{results}` envelope unification; the
audit-log INSERT WITH CHECK policy (needs the schema design); the
dead-letter design; UEN checksum (needs the official algorithm); the
NULL-context SELECT tradeoff; H-05b models; the ruff mechanical batch;
the PaymentsTab same-route prefill (no producer); the TanStack
React-Compiler incompatibility (documented disable landed); the
middleware token-parse verification gap (defense-in-depth); the
journal detail serializer's per-entry source lookup.

## P20 Remediation — 2026-11-27 (session 40): the void/transition lock completion, the CSV transaction poisoning, the e2e first-run truth & the test-config ratchet

**Base:** `6ca32a96` (post-P19, all gates green). **Plan:**
`docs/REMEDIATION_PLAN_2026-11-27_P20.md` (anchor-validated);
**report:** `docs/REMEDIATION_2026-11-27_P20_REPORT.md`.
**Method:** TDD (RED → GREEN → full gate) for every behavioural fix;
conventional commits on `main`; `skills/` excluded; no DDL (schema
v1.2.2 carries forward). The environment was rebuilt from scratch this
session (fresh clone; rootless PG 17 + Redis 8 + the schema + the venv +
the dev stack + the demo substrate — the fresh-host story exercised
end-to-end before the audit).

### The audits (three parallel, Mode C; every High verified in source)

0 Critical / 6 High / 23 Medium / 17 Low. The headline: `void()`
recomputes and saves the affected documents WITHOUT the document row
lock (allocate/unallocate both hold it — a concurrently-committed
allocation is silently lost from `amount_paid`), the CSV import loop has
no savepoint (one DB-level row error poisons the transaction → untyped
500, the per-row `errors[]` contract never delivered), and
`transition_status()` still carries the unlocked gate + stale full-row
save that P19/BE-H1 fixed for `remove_line`. Frontend: the invoice
form's Notes/Terms textareas and the two icon-only back links are
unnamed (WCAG Level A on the money flows). Cross-cutting: the live e2e
suite is red-by-construction on the first run against a fresh DB
(banking runs 2nd, its helper requires a contact, the only contact
creator runs 7th) while DEPLOYMENT §9 claims self-bootstrapping.

### What was fixed (TDD — every behavioural fix RED first)

| Task | Fix | Evidence |
|---|---|---|
| BE-H1 (+M2) | `void()`: the affected documents `select_for_update()`-locked in sorted-id order BEFORE the allocation deletes; the recompute under the locks | the lock spy + the order-recording probe + the interleaving probe (T2's committed 50.00 allocation survives the void — `amount_paid` 50.00, never the stale 0.00) |
| BE-H2 | the CSV per-row savepoint + the `1E15` magnitude bound (typed row errors) | the poison-row test (the two valid rows import, the poison row lands in `errors[]`) + the Python-parse regression guards |
| BE-H3 | `transition_status()`: locked + post-lock re-validation + `save(update_fields=…)` | the lock spy + the Case-B probe (the stale DRAFT→SENT refused post-lock) + the no-clobber probe (the racing totals survive) |
| BE-M1/M5/L1/L2/L3 | the `allocate()` sorted document pre-lock; the `create_entry()` balance-cache invalidation; the module-level `Decimal` import (ruff F821); the allocate positive-amount guard; the unreconcile org filter | the order probe; the cache-seed probe; ruff clean on the touched file; the typed-refusal test; the captured-kwargs contract test |
| FE-H1/H2 | the invoice-form Notes/Terms `id`+`htmlFor` association; the named back links on both new pages | the by-role-name + association tests; the live captures 120/121 (`notes-by-label:1 terms-by-label:1 for-attrs:2`, `back-link-by-name:1`) |
| FE-M1/M4/M7/L2/L3 | the ContactPicker blur dismissal (rAF-deferred, mousedown wins); the gst-f5-chart valid ARIA row; `formatDateOnly` with `timeZone: "UTC"`; the brand `<h1>` → `<p>`; the loading live regions | the blur tests (Tab closes the box, mousedown still selects); the owned-structure assertion; the date-identity tests; the live captures 122/123/124 |
| CFG batch (the owner's named task) | vitest: `src/app/**`+`src/providers/**` measured + per-glob floors (app 73/64/71/73, components 82/74/68/83, providers 61/60/58/60), the whole-suite floor RAISED 62/51/52/63 → 71/60/68/71, `**/__tests__/**` excluded, the `src/stores/**` exclusion documented; playwright: `retain-on-failure` traces, `locale: "en-SG"` + `timezoneId: "Asia/Singapore"`; `test:all` gains `--coverage` | the coverage run green at the RAISED ratchet; the suite green under the pinned locale/timezone; schema-valid configs (the `strictPort` plan item shipped as an honest documented caveat — Playwright 1.58 has no such option) |
| X-H1 | the banking helper is contact-self-sufficient (idempotent create) + `scripts/bootstrap_demo_substrate_session40.sh` completes §9 steps 1-5 (idempotent, double-run verified) + the §9 false claim corrected | the fresh-DB first run green (the live gate); the script executed twice green |
| X-docs | DEPLOYMENT §3 `$PG_BASE` lifecycle + the `PG_MAJOR` honesty; the stale counts in DEPLOYMENT/AGENTS/PAD/ci.yml; the four wrong API-guide routes (errata in place) + the metrics row; the backend `.env.example` decouple caveat | doc review + the audit's variable-by-variable verification table |

### The named focus (settled live — eleventh consecutive settlement)

**Mobile navigation:** 17/17 probe checks PASS on the remediated tree
(375/800/1280) — **no TailwindCSS v4 bug exists**. The P20 a11y/config
changes (the `<p>` brand, the playwright pins) re-probed clean; the
Tailwind v4 hygiene sweep is CLEAN (the P18 tw-animate-css fix held; no
dead-token `-[var(--…)]` classes remain).

### Final gate (all verified, executed)

backend **950P/0F/5S** (+13 P20 tests) · vitest **627/627** (73 files)
· tsc 0 · whole-tree eslint **0 errors / 0 warnings** · **coverage
green at the RAISED ratchet (71/60/68/71, app+providers measured)** ·
**e2e:full 40P/0F/0S — green on the FIRST run of a fresh database** ·
**rls_smoke 13/13 as `ledgersg_app`** · **mobile-nav 17/17** ·
**prod-CSP 5/5** · build:server green · schema v1.2.2 (no DDL).

### Deferred (registered, not dropped)

List pagination; the `{data}`/`{results}` envelope unification
(re-measured ~20 + 6 + 1); the ruff mechanical batch (1299/788 — this
sprint cleared its one real latent bug); the audit-log INSERT policy;
the dead-letter design; UEN checksum; the NULL-context SELECT tradeoff;
H-05b models; the PaymentsTab prefill (no producer); the TanStack
incompatibility; the middleware register entry CORRECTED (simplejwt
5.5.1 verifies by default; the real residual is the membership-cache
window); the journal detail N+1; the fiscal close race (BE-M3); the
reconcile FX comparator (BE-M4); the CSV dedupe backstop (BE-M6, DDL);
the route-guard history design (FE-M2); the drawer×dialog trap (FE-M3);
the small FE batch (L1/L4/L5/L6/L8); the CI hardening batch (X-L2/I1/I2);
the version-story reconciliation (X-M8).

## P21 Remediation — 2026-11-27 (session 42): the list-envelope unification, the InvoiceNow evidence stamp, the cache-commit truth & the banking a11y batch

**Base:** `67512bf1` (post-P20, all gates green). **Plan:**
`docs/REMEDIATION_PLAN_2026-11-27_P21.md` (anchor-validated);
**report:** `docs/REMEDIATION_2026-11-27_P21_REPORT.md`.
**Method:** TDD (RED → GREEN → full gate) for every behavioural fix;
conventional commits on `main`; `skills/` excluded; no DDL (schema
v1.2.2 carries forward). The session-40 workspace survived — the
baselines were reproduced first (950P · 627/627 · tsc 0 · eslint 0E/0W
· e2e 40/40 · rls 13/13 · mobile-nav 17/17 (twelfth settlement) ·
prod-CSP 5/5; `test_ledgersg_dev` recreated + loaded).

### The audits (three parallel, Mode C; every High verified in source)

0 Critical / 2 High / 20 Medium / 15 Low / 13 Informational. The
headline: the list layer speaks 5 shapes across 30 sites (the
deferred register's big-ticket item), `invoicenow_sent_at` is read by
the void/unallocate restore but written by NOTHING (dead branch), the
dashboard cache is not invalidated by voids or manual entries and
every invalidation runs INSIDE the transaction (the delete→commit
re-seed race), the bank-account default flag races (two concurrent
set_defaults → two defaults; full-row saves clobber concurrent
edits), ValidateBalanceView 500s on malformed bodies, and the two
banking a11y Highs (the unnamed Reference input; the
keyboard-inaccessible CSV import). The cross-cutting audit found one
pattern: the P20 truth pass updated the top status blocks but left
second-tier doc surfaces stale (9M + 5L). Bonus truth finding: the
RLS isolation test read `.get("data", [])` against a `{results}`
endpoint — a VACUOUS assertion (always passed).

### What shipped (per phase)

| Area | The fix | The evidence |
|---|---|---|
| BE-M6 (the envelope) | every LIST endpoint returns `{results, count}`: the orgs list, fiscal years, the bare-array `/auth/organisations/`, the trial balance (+totals), entry types, IRAS info, the GST periods POST; reports keep `{data}` (lists → results, reports → data); the frontend + e2e + bootstrap consumers migrated | 7 new envelope contract tests + the updated shape tests + the vacuous RLS assert fixed + live (the :8000 org list verified) |
| BE-M1 | the bank-account default flag locked: set_default's org-wide sorted lock; update/deactivate via `_get_locked` + `update_fields` | the lock spy + the racing-save no-clobber probe (T2's 999.00 survives) |
| BE-M2/M3 | the dashboard cache invalidated by void_document + create_entry (the P5/H-3 completion); every mutation-path invalidation/deletion on `transaction.on_commit` | the capture-on-commit probes (not-inline + fires-on-execute) |
| BE-M4 | `invoicenow_sent_at` stamped on a DELIVERED transmission (stamp-once, isnull filter; the status/transition map untouched) | the DELIVERED-stamp test |
| BE-M5 | ValidateBalanceView typed 400s on malformed bodies (was AttributeError/InvalidOperation 500s) | the three malformed-body tests |
| FE-H1/H2 + M1/M2/M4/M5 | the Reference accessible name; the sr-only CSV input (was display:none — unfocusable); the import dialog's unique ids; the loader live regions on every remaining surface; the payment-card keyboard contract; the reconcile aria-pressed | the vitest probes + the live captures 128-131 |
| FE-M3 + L-batch | `isoYearOf` (the GST year lexically — the local-tz read queried the wrong year) + `localTodayISO` (local calendar day); the visible-label ContactPicker; the dead accent token (compile-verified); the always-rendered aria-controls; video retain-on-failure | 5 helper tests + the design-tokens gate + the captures 132/133 |
| X-docs | the 9M + 5L truth batch (README badge/section/order, CLAUDE's P19 retitle, AGENTS header/v1.2.2/P0–P21, SKILL quick-ref + NUMERIC v1.1.0, PAD lint row, ci.yml, the API guide 3.2.0 + the P21 addendum, DEPLOYMENT counts); the bootstrap script's dual-shape fallback retired | doc review; each count re-measured |

### The named focus (settled live — thirteenth consecutive settlement)

**Mobile navigation:** 17/17 probe checks PASS on the remediated tree
(375/800/1280) — **no TailwindCSS v4 bug exists**. The FE audit's
compile-verified dead-token sweep found exactly one dead utility
(`accent-primary`) — fixed this sprint with a compile gate.

### Final gate (all verified, executed)

backend **969P/0F/5S** (+19 P21 tests) · vitest **641/641** (75 files,
+14) · tsc 0 · whole-tree eslint **0 errors / 0 warnings** ·
**coverage green at the ratchet** · **e2e:full 40P/0F/0S** ·
**rls_smoke 13/13 as `ledgersg_app`** (the stale --noreload backends
restarted first — the P13 lesson) · **mobile-nav 17/17** ·
**prod-CSP 5/5** · build:server green · schema v1.2.2 (no DDL).

### Deferred (registered, not dropped)

List pagination (the envelope prerequisite is NOW DONE —
`LedgerView` line materialisation is the first target); the ruff
mechanical batch (re-measured 936 production / 1307 whole-tree); the
audit-log INSERT policy (DDL); the BE-L3 config-class locking; the
Peppol log-state locking; the CSV errors[] raw strings; dead-letter
design; UEN checksum; NULL-context SELECT; H-05b models; PaymentsTab
prefill; TanStack incompatibility; the membership-cache window; the
journal detail N+1; the P20-era FE-M2/M3 designs; CI hardening; the
version-story reconciliation.

## P23 Remediation — 2026-11-27 (session 44): the mobile-nav drawer slide truth + the vitest advisory closure

**Base:** `080ccc0b` (post-P21 + the P22B dry-run docs). **Plan:**
`docs/REMEDIATION_PLAN_2026-11-27_P23.md` (anchor-validated);
**report:** `docs/REMEDIATION_2026-11-27_P23_REPORT.md`. **Method:**
TDD (RED → GREEN → full gate) for the behavioural fix; conventional
commits on `main`; `skills/` excluded; no DDL (schema v1.2.2 carries
forward); no backend application code changes. The sandbox was
recycled — the environment was rebuilt from zero (rootless PG 17 via
`docs/setup_pg_z.sh` — the skill's §2 probes all passed natively this
time, no sudo fallback; Redis 8.0.2 on :6379 rootless; the venv;
`npm install`; `npx playwright install chromium`).

### The baselines (reproduced exactly before any change — the P22B
report's "Unverifiable here" rows resolved)

backend **969P/0F/5S** · vitest **641/641 (75 files)** · tsc 0 ·
eslint **0E/0W** · live e2e:full **40/40** · rls_smoke **13/13** ·
mobile-nav **17/17** (fourteenth) · prod-CSP **5/5** · the demo
substrate bootstrapped via the §9 script (idempotent double-run).

### The audits (Mode C; every finding hand-verified live)

The named focus settled: the mobile-nav functional contract is green
(12/12 + 7/7 + 17/17) — but **the one real Tailwind v4 bug is the
drawer's dead animation** (the P22B dry-run finding, still unfixed at
base): compile proof — `.-translate-x-full` compiles to the standalone
`translate` property while `transition-[transform,visibility]` omits
it; live proof (agent-browser, available this session) — the computed
`transitionProperty` reads `"transform, visibility"` with
`duration 0.3s` and `transform: none`: the 300ms slide never
interpolated. Plus: the vitest 4.0.18 criticals (2) with the fix
release 4.1.12 proven viable in-session; the docs second-tier surfaces
on P21 numbers; `.env.example` ×3 verified truthful (no changes).

### What shipped

| Area | The fix | The evidence |
|---|---|---|
| FE-M1 | `shell.tsx` transition list → `transition-[transform,translate,visibility]` (+ the Trap 5(b) rationale comment) | the RED→GREEN pair (the new vitest spec failed naming the missing token; the new e2e spec failed on `"transform, visibility"`); the compile proof (`transition-property: transform,translate,visibility`); the live re-probe (16 intermediate translate values sampled mid-flight) |
| FE-L1 | the animation-contract gates: `shell-drawer-transition.test.tsx` (the token + positioning contract) + the e2e `P23/FE-M1` (the computed style at 375px) | both RED→GREEN documented; the compiled-CSS gate the 13 prior settlements lacked |
| CFG-M2 | the vitest advisory closure: ^4.0.18 → **^4.1.12** (package.json + lockfile; the fixed 4.x line inside the caret range) | full suite green on it (642/642); `npm audit` **0 critical** (20 → 17 findings, all residual dev-tier; the production set clean) |
| X-docs | the second-tier truth pass (README badge/status/milestone, CLAUDE v2.24.0 + the stale backend row, AGENTS header + the P23 lessons, SKILL v2.10.0 quick-ref, PAD counts, DEPLOYMENT header/§7/§9, the API guide 3.2.1 P23 addendum, ci.yml) | each count re-measured against the executed gates |

### The named focus (settled live — fifteenth consecutive settlement)

**Mobile navigation:** 17/17 probe checks PASS on the remediated tree
(375/800/1280) — the navigation works; the ONE real v4-class animation
bug (the drawer's transition list omitting the standalone `translate`
property) is **fixed and gated** this sprint.

### Final gate (all verified, executed)

backend **969P/0F/5S** (re-verified; untouched) · vitest **642/642
(76 files)** on vitest 4.1.12 · coverage green at the ratchet · tsc 0 ·
whole-tree eslint **0 errors / 0 warnings** · live e2e:full **41/41**
(+1) · rls_smoke **13/13 as `ledgersg_app`** · mobile-nav **17/17**
(fifteenth) · prod-CSP **5/5** (rebuilt standalone) · `npm audit`
**0 critical** · 8 DOM-verified screenshots (`136-143`, incl. the
drawer captured mid-slide at `translate: -7.92%`) · schema v1.2.2 (no
DDL).

### Environment lesson (recorded)

The rls_smoke setup had ALTERed the `ledgersg_app` password, which
broke two RLS tests on the next pytest run (they rely on the schema's
documented dev default `CHANGE_ME_IN_PRODUCTION`) — the role was
restored, the :8001 instance restarted with the default, both gates
green. Role passwords are test-visible state: inventory environment
changes before diagnosing a red suite as a code regression.

### Deferred (registered, not dropped)

The remaining 17 dev-tier npm-audit findings (typescript-eslint/vite/
undici chains — major bumps, a dedicated dependency sprint); list
pagination (the envelope prerequisite done — `LedgerView` line
materialisation first); the ruff mechanical batch (936 production);
the audit-log INSERT policy (DDL); BE-L3/BE-L4 locking; the CSV
errors[] strings; dead-letter design; UEN checksum; the P21 deferred
register carried forward unchanged.

## P24 Remediation — 2026-11-27 (session 46): the server-side list pagination (the ledger line materialisation first target)

**Base:** `05daa36f` (post-P23 + the session-45 log). **Plan:**
`docs/REMEDIATION_PLAN_2026-11-27_P24.md` (anchor-validated);
**report:** `docs/REMEDIATION_2026-11-27_P24_REPORT.md`. **Method:**
TDD (RED → GREEN → full gate) for every behavioural change;
conventional commits on `main`; `skills/` excluded; no DDL (schema
v1.2.2 carries forward); no backend model changes. The session-44
environment was still live (the sandbox survived), so the setup phase
was verification-only: `git pull` to `05daa36f`, the DB/role/substrate
state probed, the demo login re-verified.

### The baselines (reproduced exactly before any change)

backend **969P/0F/5S** · vitest **642/642 (76 files)** · tsc 0 ·
eslint **0E/0W** · live e2e:full **41/41** · rls_smoke **13/13** ·
mobile-nav **17/17** (sixteenth settlement) · prod-CSP **5/5** · npm
audit **0 critical** (17 dev-tier; the production set 0).

### The named focus — settled first

**The mobile navigation menu works as expected; NO remaining
TailwindCSS v4 bug on that surface.** The live agent-browser probe
re-read the P23 fix (the computed `transitionProperty: "transform,
translate, visibility"`; the closed drawer `-100%`/hidden; a 120ms
mid-flight sample at `translate: -40.963%` — the slide interpolates;
the open drawer a `role="dialog"` at `0px`; Escape closes it) + the
17/17 probe + the 6 e2e specs in the 41/41 run.

### The audits (Mode C; every finding hand-verified)

The registered big-ticket deferral picked as the target: **no list
endpoint paginates** — the ledger endpoint returns the org's entire
line-level history in one payload (the P21 envelope was explicitly
the prerequisite). The ordering-prerequisite audit: the ledger/
entries/documents orders were already total (the schema's UNIQUE keys
+ line_number); contacts (`name`) and payments
(`-payment_date, -created_at`) lacked the unique final key — the
cross-page skip/dup hazard (Postgres tie order is not stable across
executions). The dormant `DEFAULT_PAGINATION_CLASS` settings path
(latent — surfaced only at the post-change restart).

### What shipped

| Area | The fix | The evidence |
|---|---|---|
| BE-M1 | the additive `?limit=&offset=` contract: `common/pagination.py` (typed 400s on garbage; limit ∈ [1, 1000]; `next`/`previous` absolute URLs carrying the caller's filters; `count` as the TOTAL) + `LedgerView` at the SQL level (`count()` + the queryset slice) + the five service-driven views at the envelope level (entries, documents, contacts, payments, transactions) + the legacy DRF classes restored verbatim (the settings string-reference lesson) | the 26 contract gates (both envelope modes pinned: byte-identical unpaginated; the paginated boundaries; the no-skip/no-dup walk; the typed 400s) + the live curl probe |
| I1 (tiebreakers) | contacts `name, id`; payments `-payment_date, -created_at, -id`; transactions `-transaction_date, -created_at, -id` | the forced-tie test (two same-name contacts paginate limit=1 without skip or dup) |
| FE-M2/L1 | the shared accessible `TablePagination` (nav landmark; the polite "Showing x–y of z" live region; boundary-disabled Previous/Next) + `useLedger` forwarding limit/offset **with the page identity in the queryKey** (the cache-paging trap) + the ledger client at page size 20 (the org change resets the page) | 13 component tests + the 3 hook tests (incl. the cache-paging pin) + the 2 page tests + the live e2e `P24/FE-P1` (Next advances to "Showing 21–36 of 36", Previous returns) |
| X-env | both `--noreload` backends restarted via the daemonizer before the live gates (the first e2e GREEN attempt had silently run the old backend) | the two AGENTS.md lessons (the restart rule; the latent settings-string crash) |
| X-docs | the truth pass (README badge 1697 + the P24 milestone, CLAUDE 2.25.0, AGENTS header + the P24 lessons, SKILL 2.11.0, PAD rows, DEPLOYMENT counts + §7/§9, the API guide 3.3.0 + the P24 pagination addendum with CLI recipes, ci.yml) | each count re-measured after the gates; the `.env.example`s re-verified truthful (no changes required) |

### Final gate (all verified, executed)

backend **995P/0F/5S** (+26) · vitest **660/660 (77 files)** (+18) ·
tsc 0 · whole-tree eslint **0 errors / 0 warnings** · **coverage
green at the ratchet** · **e2e:full 42P/0F/0S** · **rls_smoke 13/13
as `ledgersg_app`** · **mobile-nav 17/17** · **prod-CSP 5/5** ·
build:server green · schema v1.2.2 (no DDL). 8 DOM-verified
screenshots (144-151, the ledger page 1/page 2 headline pair).

### Deferred (registered, not dropped)

The SQL-level push-down for the five service-driven lists; the
frontend pagination wiring for invoices/contacts/payments/
transactions; the capped-default flip (after every consumer passes
explicit limits); the 17 dev-tier npm-audit findings (the dedicated
dependency sprint — the 49-package `audit fix` dry-run measured and
deliberately not applied); the ruff mechanical batch (936
production); the audit-log INSERT policy (DDL); BE-L3/BE-L4 locking;
the CSV errors[] strings; dead-letter design; UEN checksum; the P21
deferred register carried forward unchanged.
