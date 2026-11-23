# LedgerSG — Remediation Plan (P11 Sprint: Accounting Truth & Deployment Truth — Credit-Note Direction, Production Boot, Wire-Contract Closure, CI/Config Honesty)

- **Date:** 2026-11-23
- **Branch:** `main` only (per repo convention)
- **Inputs:** post-P10 audit of the `1b3e267d` state. Findings gathered per `skills/skills-catalog.md`: the `vulnerability-scanner` scanner pass (all hits in the documented FP classes — test fixtures, dev-compose defaults, root legacy scripts, the f-string error message class; the `skills/` folder excluded per repo convention) plus three parallel deep-audit agents (P10-diff regression audit, deferred-register + configuration/infrastructure audit, fresh-surfaces gap audit) with `code-review-and-audit` / `code-quality-standards` discipline. Every Critical/High/Medium finding below was re-verified against the working tree with line numbers by the lead before this plan was written, including two runtime reproductions (the production-settings cache backend crash via a real `django.setup()` + cache resolve; the `DEBUG=true + DEBUG_TOOLBAR=false` `manage.py check` crash), one probe-test reproduction by the audit agent (bank PATCH 500), and byte-level re-verification of the CI trigger (the on-disk YAML reads `branches: [main]` — intact; the "ain" rendering is the documented tool-display artifact, BUT the P10 corrective comment inside the file itself carries display-mangled text on disk — cleaned in Task 11).
- **Method:** TDD (RED → GREEN → full gate), lint parity on touched files, conventional commits, `skills/` excluded from all checks/tests/compilation.
- **Baselines reproduced before any change (this session, exact):** backend **687 passed / 0 failed / 5 skipped**, vitest **505/505**, typecheck **0 errors**, e2e default **11 passed + 20 gated skips** — the documented P10 state, reproduced exactly before any change.

---

## 0. Audit Summary (the register this plan is built on)

P10 closed the self-serve loop and made the F5 lifecycle real. The post-P10 audit has four heads: **(a) accounting truth** (credit notes post with invoice-direction GL entries — every approved credit note *increases* AR/revenue/GST-output instead of reversing them; the F5 computation counts quotes and purchase orders, double-counts converted quotes, and *adds* credit notes instead of netting them; the dashboard's headline GST liability is structurally SGD 0.00 because journal lines never carry tax_code/tax_amount), **(b) production/deployment truth** (the production settings cannot boot org-scoped requests — `django_redis.cache.RedisCache` is undeclared in pyproject/lock, and the LOGGING file handler crashes when `/var/log/ledgersg` doesn't exist, plus the LOGGING dict is mutated in place; the backend Dockerfile installs neither `django-csp` nor `django-ratelimit` — both in INSTALLED_APPS/MIDDLEWARE — so the image cannot boot Django; docker-compose's DB password mismatches across services and its api command runs `migrate --run-syncdb`, violating SQL-First), **(c) wire-contract truth** (the P10 F5 "View boxes" panel reads `box1…box14` keys the serializer never sends — every box renders "—"; the GST deadlines banner reads `results` from an endpoint that sends `data`; the contacts edit dialog prefills from the list payload and PATCHes all eight fields — opening the dialog and saving erases the stored UEN/Peppol ID/address with a success toast; `gst_reg_number` edits are silently dropped — the update serializer has no such field), and **(d) config honesty** (the CI coverage ratchet is never executed in CI; the "Generate Test Report" step re-runs the entire 687-test suite for a stdout echo; the security-scan job installs only its own tools and `|| true`'s everything; `.gitignore` misses `coverage/`, `test-results/`, `playwright-report/`; dev tooling sits in production `dependencies`; the Makefile ships `migrate`/`migrations` targets the architecture forbids; 5 MB of tracked logs live in root `tests/`).

| ID | Severity | Location | Finding (Verified) |
|---|---|---|---|
| C-1 | **Critical** (statutory accounting corruption) | `apps/journal/services/journal_service.py:273-352`; trigger `document_service.py:420-428` | `post_invoice` posts SALES_CREDIT_NOTE identically to SALES_INVOICE: Dr AR, Cr Revenue, Cr GST-output. A credit note must reverse those. Approving any credit note **increases** AR, revenue and output-tax liabilities; GL/TB/aging/F5 all corrupted. Balanced entry → nothing catches it. The posting gate (`transition_status` APPROVED branch) explicitly includes both `*_CREDIT_NOTE` types — the wrong-direction entry lands. |
| C-2 | **Critical** (production cannot boot) | `config/settings/production.py:75-83,95-104` | (1) CACHES uses `django_redis.cache.RedisCache` but `django-redis` is in neither pyproject nor uv.lock — **reproduced**: `django.setup()` + cache resolve → `ModuleNotFoundError: No module named 'django_redis'`. The tenant-membership cache and django-ratelimit hit it on every org-scoped request. (2) LOGGING targets `/var/log/ledgersg/django.log` (no deploy step creates it — reproduced: `ValueError: Unable to configure handler 'file'`). (3) LOGGING mutates the shared base dict in place — the exact copy-on-write bug class P10 fixed in development.py. |
| H-1 | **High** (silent data loss) | `contacts/contacts-client.tsx:296-324` + `invoicing/serializers.py:13-22` | The edit dialog prefills from the LIST row (`ContactListSerializer` carries no `uen`/`peppol_id`/`address_line_1`/`postal_code`/`gst_reg_number`) → those fields prefill `""`, and `handleSave` PATCHes all eight fields unconditionally with `allow_blank=True` on the other side. Saving an email fix **erases UEN, Peppol ID and address** with a success toast. Peppol ID loss breaks InvoiceNow. The banking dialog (P10/M-6) solved the same problem correctly — contacts did not. |
| H-2 | **High** (feature dead + compliance lie) | `reports-client.tsx:687-727` vs `gst/serializers.py:223-241` | `F5_BOX_LABELS` uses `box1…box14`; the detail serializer sends `box1_std_rated_supplies`… — every box renders "—". The P10/H-3 headline deliverable (boxes visible before File) is non-functional; unit tests mocked idealized keys so nothing surfaced. |
| H-3 | **High** (statutory F5 corruption) | `gst/services/calculation_service.py:237-306` | `get_f5_box_amounts` has NO document-type filter — quotes reach APPROVED (`convert_quote_to_invoice` sets it) and SENT (status transitions allow DRAFT→SENT), so converted quotes **double-count** into Boxes 1/6/13 (quote + converted invoice carry the same lines); SENT purchase orders pollute Boxes 5/7; SALES_CREDIT_NOTE lines are **added** where IRAS requires netting. |
| H-4 | **High** (headline KPI structurally false) | `reporting/services/dashboard_service.py:276-308` vs `journal_service.py:246-262` | `calculate_gst_liability` filters `JournalLine.tax_code__is_output=True … Sum(tax_amount)` — but the ONLY `JournalLine.objects.create` site never sets `tax_code`/`tax_amount` (always NULL/0) → GST Payable (Box 8) is permanently SGD 0.00 on real data. |
| H-5 | **High** (documented env combination crashes every command) | `config/urls.py:20-25` vs `config/settings/development.py:77-83` | urls.py gates the debug_toolbar URLconf import on `settings.DEBUG`; INSTALLED_APPS gates on the `DEBUG_TOOLBAR` knob. `DEBUG=true + DEBUG_TOOLBAR=false` (a combination the backend `.env.example` documents) crashes `manage.py check`/`runserver` with `HistoryEntry … isn't in an application in INSTALLED_APPS`. **Reproduced by the lead this session.** |
| H-6 | **High** (image cannot boot) | `apps/backend/Dockerfile:36-41,84-88` | Installs deps by hand, not from pyproject/lock: no `django-csp`, no `django-ratelimit` (both INSTALLED_APPS/MIDDLEWARE) → ModuleNotFoundError at boot; unpinned `pip install -U django …` drifts from the 6.0.2 pin; unpinned django-celery-beat (the exact downgrade vector pyproject warns about); no default CMD (gunicorn commented out); HEALTHCHECK pings 7860 while compose maps 8000. |
| H-7 | **High** (stack cannot boot) | `apps/backend/docker-compose.yml:9 vs :46,75,101,60-62` | `POSTGRES_PASSWORD: ledgersg_secret_to_change` vs `DB_PASSWORD: ledgersg` in all three Django services → password auth fails on first `up`. The api command runs `migrate --run-syncdb` — permanently disabled in this architecture (managed=False mirrors; "never run migrations"). |
| M-1 | Medium | `use-reports.ts:324-333` vs `gst/views.py:526-527` | Deadlines endpoint returns `{"data": [...], "count": n}`; the hook types/reads `{results: []}` → the banner's `gstDeadlines.data?.results?.[0]` is always undefined — never renders. |
| M-2 | Medium (reproduced by probe test) | `banking/views.py:130` | Update view binds the instance via `BankAccount.objects.get(...)` — `DoesNotExist` is unhandled → **500** on a missing/deactivated account where GET/DELETE correctly return 404. |
| M-3 | Medium | `contacts-client.tsx:48-52` | Debounce is a no-op: `setTimeout` inside `useMemo` whose returned cleanup is never invoked — ~1 request per keystroke, stale intermediate values, timers survive unmount. The sibling ContactPicker does it correctly with `useEffect`. |
| M-4 | Medium | `contacts-client.tsx` EDIT_FIELDS vs `invoicing/serializers.py:63-80` | The dialog renders an editable "GST Registration No" field, but `ContactUpdateSerializer` has no `gst_reg_number` — DRF silently drops it; save says "Contact updated", nothing persisted. |
| M-5 | Medium (500 class on UI-reachable paths) | `core/views/organisations.py:96-131`; `core/serializers/organisation.py:196-204`; schema CHECKs `database_schema.sql:172-186,229-233` | Detail PATCH is a raw allowlist (no typing): `entity_type="PTE_LTD"` violates the DB CHECK, `base_currency="SGDD"` exceeds CHAR(3), `country="SGP"` exceeds CHAR(2) → IntegrityError/DataError 500s. The settings serializer leaves `gst_scheme`/`gst_filing_frequency` `allow_blank=True` (CHECK vocabulary violations), `timezone` max_length=63 vs the DB's VARCHAR(50), and PATCH `gst_registered: true` without `gst_reg_date` violates `chk_gst_consistency` — all 500s. The settings Base Currency input is free-text on the frontend. |
| M-6 | Medium | `journal/urls.py:30-55`, `gst/urls.py`, `banking/urls.py:32-77`, `invoicing/urls.py:34-55` + views | Garbage path UUIDs (`GET …/entries/abc/`) raise `ValueError` in raw `UUID(...)` → unhandled 500 across org-scoped detail routes (the P7/F-11 sweep covered query params only; banking's transaction route already uses the parse helper — the pattern exists). |
| M-7 | Medium | `gst-f5-chart.tsx:40-41` | `parseFloat("SGD 318.00")` → NaN → the compliance chart renders Box 8 as 0 for any real value (`Number.isFinite` guard hides it). The dashboard payload already carries raw `gst_payable`. |
| M-8 | Medium | `common/middleware/audit_context.py:43-47` vs schema `log_change()` (2199-2215) | The middleware sets `app.client_ip/user_agent/request_path` per request for the audit trigger to read — the trigger's INSERT never reads them (columns exist: `ip_address INET`, `user_agent TEXT`, `request_path VARCHAR(500)`, `session_id`); LOGIN/LOGOUT are in the CHECK vocabulary but never emitted by any code. |
| M-9 | Medium (config honesty) | `.github/workflows/ci.yml:152-157,194-199,220-230`; `pyproject.toml:110-119` vs `pytest.ini` | (a) "Generate Test Report" re-runs the entire 687-test suite (`|| true`) for a stdout echo — doubles backend CI time, garbage after failure. (b) The security job `pip install safety bandit` then `safety check || true` — scans its own two packages, never the project deps, cannot fail by design. (c) CI runs `npm test`, never `npm run test:coverage` — the P10/M-13 "REAL gate" ratchet is not enforced anywhere. (d) pytest config declared twice (pytest.ini wins; pyproject block dead). |
| M-10 | Medium | `.gitignore`; `docs/DEPLOYMENT.md:470` | Missing `coverage/`, `test-results/`, `playwright-report/` (all emitted by the current configs; `git add -A` history repeats). DEPLOYMENT.md claims a `*.key` rule that does not exist. |
| M-11 | Medium | `gst/services/return_service.py:456-461` | `get_upcoming_deadlines` filters `status__in=["DRAFT","COMPUTED"]` — a REVIEWED-but-unfiled return (the P10/H-3 wire added that state) is invisible to the deadline banner exactly one step before filing. |
| M-12 | Medium | `docker/Dockerfile:85-88` | The root full-stack image installs unpinned deps and misses `django-ratelimit` (INSTALLED_APPS → boot failure) and `requests` (the Storecove AP adapter). Frontend half already standalone-only (consistent with P10/M-12). |
| M-13 | Medium | `apps/backend/Makefile:54-58` | `migrate`/`migrations` targets ship the exact commands the architecture forbids (DEPLOYMENT.md:161-163 "Never run makemigrations"; CI/tests all use `--no-migrations`). |
| M-14 | Medium | `apps/web/package.json` | All dev/test tooling (vitest, playwright, testing-library, eslint, typescript, jsdom) in production `dependencies` — every prod install ships dev-only packages; `serve` is referenced by nothing (leftover from the retired static-export mode). |
| M-15 | Medium | `apps/web/next.config.ts:63,68` | CSP `script-src 'self' 'unsafe-eval' 'unsafe-inline'` applies in server (production) mode; `connect-src` hardcodes `http://localhost:8000` + placeholder external APIs instead of deriving from `NEXT_PUBLIC_API_URL`. |
| M-16 | Medium (repo hygiene + tooling breakage) | root `tests/`, `Agent-Browser-howto.md` (broken symlink), `GEMINI.temp`, `status_*.md` | 5 MB of tracked logs/screenshots in root `tests/` (backend.log ×2, nextjs_dev.log, openclaw logs); the broken tracked symlink **errors out rg-driven tooling** (verified: agent LS/Grep calls failed until scoped around it); `GEMINI.temp` 188 KB tracked. |
| L-1 | Low | `reports-client.tsx:534-563`, `banking-client.tsx:247-275`, `contacts-client.tsx:221-245` | The P10 action surfaces (Review/File/Amend; Edit/Deactivate) render for members who cannot perform them (backend 403s → error toast); the same sprint's fiscal/InvoiceNow cards gate correctly on `hasPermission`. |
| L-2 | Low | `dashboard-client.tsx:203,235,260,274,319,334` | `S$ {data.gst_payable_display}` renders `S$ SGD 318.00` — double currency prefix on every dashboard money card. |
| L-3 | Low | `dashboard_service.py:92,353,386,451`; `return_service.py:453`; `tax_code_service.py:197,270`; `journal_service.py:447` | `date.today()` (server-OS TZ) instead of `timezone.localdate()` — with TIME_ZONE=Asia/Singapore + USE_TZ, boundary windows (MTD start, deadline countdown, as-at default, effective-today resolution) are off by a day between 00:00–08:00 SGT in a UTC container. |
| L-4 | Low | `journal/views.py:360-361` | The ledger view filters `entry__is_reversed=False` while trial balance includes both sides — the ledger hides the original side of every reversal pair; rows no longer reconcile to the TB view by construction. |
| L-5 | Low (credential hygiene) | root `start_apps.sh`, `debug_ledger.py`, `reset_test_password.py`, `test_setup_seed_data.py`, `e2e_test_phases_7_15*.py`, `code_interpreter_qwen*.py`, `database_connect.sh`, `initialize_database.sh`, `run_test_suite.sh` | Stale session-transcript scripts with hardcoded absolute paths to nonexistent layouts; `start_apps.sh` contains **pasted live JWTs and a password hash**; `debug_ledger.py` hardcodes demo credentials; `database_connect.sh` begins with `exit 0`. All superseded by DEPLOYMENT.md's documented flow. |
| L-6 | Low | `common/exceptions.py:164-173` | The `isinstance(exc, ValidationError)` branch is dead code (shadows the LedgerSG ValidationError already handled above; the believed Django/DRF shapes never reach it). |
| L-7 | Low | `.github/workflows/ci.yml:14-24` (comment) | The P10 corrective comment contains display-mangled text **on disk** ("branches: ain, develop]" etc. — the `[m` sequences were eaten when the comment was written). The YAML itself is intact (byte-verified). |
| L-8 | Low | `database_schema.sql:2262-2265` + `payment_service.py:128,199,389,502,586`, `bank_account_service.py:92,222,275,316`, `reconciliation_service.py:237,313,363` | Every banking mutation produces TWO audit rows (the table trigger's full-row JSONB + the curated service event) — inflated storage, double-counted frequency. |
| L-9 | Low | `core/serializers/organisation.py:20-35` | `ensure_uen_available` is check-then-write — concurrent same-UEN requests can both pass and the loser still 500s via IntegrityError. Catch-at-write hardening (400) is the cheap fix. |

Verified-clean (explicit): the P10 live-gate fixes all hold (429 mapping, UEN 400s, anonymous-401 exemption, copy-on-write, PayNow update parity, VOID fail-closed); the P10 endpoints' permission gating is correct (FiscalPeriodOpenView, GSTReturnReviewView — `IsOrgMember` + manager gates, org-scoped fetches); the register page posts to the real rate-limited endpoint; journal `create_entry` core (balance invariant, ≥2 lines, fiscal checks, control-account resolution) is sound; every frontend hook endpoint exists (no 404-endpoint hooks remain); Decimal serialization clean (DecimalSafeJSONRenderer); query-param garbage sweep thorough; dashboard state-handling clean. Frontend hooks ↔ backend routes all resolve.

---

## 1. Task 1 (C-1 + H-3): credit-note accounting truth — the posting engine and the F5 computation

**Backend, RED first.**

- `post_invoice` gains a credit-note branch: for `*_CREDIT_NOTE` types the entry flips direction (sales credit note: Dr Revenue lines, Dr GST-output, Cr AR; purchase credit note: Cr expense lines, Cr GST-input, Dr AP). Debit notes keep invoice direction (a debit note *increases* the claim — same as invoice). RED: pytest that approves a SALES_CREDIT_NOTE and asserts the AR line is a CREDIT (today: debit) and the revenue line a DEBIT (today: credit); same for PURCHASE_CREDIT_NOTE (AP debit, expense credit, GST-input credit); the journal entry still balances (the invariants gate already proves the invariant).
- `get_f5_box_amounts`: (a) restrict to posting document types (exclude `SALES_QUOTE`, `PURCHASE_ORDER` — the SQL gains `AND d.document_type IN (...)` with the six posting types); (b) credit notes NET their boxes (sales credit: subtract from box1/box13 amounts and box6 output tax; purchase credit: subtract from box5/box7). RED: pytest that a converted quote's lines count once (not twice); a SENT quote contributes zero; a SALES_CREDIT_NOTE subtracts from Box 1 and Box 6; a PURCHASE_CREDIT_NOTE subtracts from Box 5/Box 7.
- The F5 tie-out invariant test gains a credit-note + converted-quote fixture.

## 2. Task 2 (C-2): production settings boot truth

**Backend, RED first (settings-gate tests, the P10 knob-test pattern).**

- CACHES: delete the `django_redis` override — inherit base's builtin `django.core.cache.backends.redis.RedisCache` (base.py:302-307; importable, verified). The `django-redis` dependency is NOT added (the builtin backend is the repo's own convention — same stack as base/testing).
- LOGGING: copy-on-write (`{**LOGGING, "handlers": {**LOGGING["handlers"], …}, "loggers": {…}}`) + `LOG_DIR` env knob (default `/var/log/ledgersg`) with the file path derived from it; DEPLOYMENT.md gains the `mkdir` step (Task 18).
- RED (pytest, no DB needed): a settings-gate test that imports `config.settings.production` fresh under its env contract and asserts (a) the cache backend module resolves (import the backend class path), (b) importing production does not mutate base's LOGGING (import base first, snapshot, import production, compare), (c) `LOG_DIR` override flows into the handler path.

## 3. Task 3 (H-1 + M-3 + M-4): the contacts edit dialog tells the truth

**Backend + frontend, RED first.**

- Backend: `ContactUpdateSerializer` gains `gst_reg_number` (CharField max_length=20, allow_blank — matching the model column). RED: pytest PATCH with gst_reg_number persists it (today: silently dropped).
- Frontend: the edit dialog prefills from the DETAIL endpoint (`useContact(orgId, contact.id)` — the hook exists) with the banking-dialog remount pattern (`key={contact.id}` so state resets per row); the dialog renders the detail-serializer fields; Save PATCHes the (now-truthfully-prefilled) fields. The contact row's UEN/Peppol badges come from the list payload — `uen`/`peppol_id` added to `ContactListSerializer` so the list shows what it claims (and the row badges become real).
- The search debounce: `useMemo` → `useEffect` with the cleanup (the ContactPicker pattern). RED: vitest asserting the debounced value settles after the timer (today: every keystroke fires).

## 4. Task 4 (H-2 + M-1 + M-11): the F5 panel, the deadlines banner, the deadlines filter

**Backend + frontend, RED first.**

- `F5_BOX_LABELS` maps to the serializer's real keys (`box1_std_rated_supplies` … `box14_reverse_charge_supplies`); the panel renders values, "—" only for undefined. RED: vitest with the REAL serializer payload shape (fixtures rebuilt from `get_boxes`'s actual keys).
- The deadlines hook types/reads the endpoint's actual envelope (`{data, count}`) — and the backend standardizes to `{results, count}` instead (the B6-family convention used by every other list endpoint): one-line backend change, both sides updated, contract test on each side. Chosen: backend standardizes (aligns with the repo's documented list convention and kills the class of bug).
- `get_upcoming_deadlines` includes `REVIEWED` in the status filter. RED: pytest that a REVIEWED return with a live due date appears (today: filtered out).
- The reports-page test fixtures rebuild from the real serializer shapes (the audit's "mocked idealized contracts" finding — the class that masked all three wire defects).

## 5. Task 5 (H-4 + M-7 + L-2): the dashboard's GST truth

**Backend + frontend, RED first.**

- `calculate_gst_liability` re-sources from document lines: a period filter over `invoicing.document_line` mirroring `get_f5_box_amounts`'s semantics (posting types only, credit notes netted — Task 1's helper) — output tax = box6 semantics, input = box7, net = box8. RED: pytest that an org with a real approved invoice reports non-zero output tax (today: always 0 — the journal lines carry no tax_code).
- `gst-f5-chart` consumes the raw numeric `gst_payable` from the dashboard payload (already returned) with proper money formatting — no more `parseFloat("SGD …")` NaN. RED: vitest that the chart renders a non-zero bar from a payload with gst_payable "318.0000".
- `dashboard-client` drops the `S$` prefixes on the six display-string sites (the backend's `SGD x` display strings are the truth). RED: vitest asserting no `S$ SGD` substring renders.

## 6. Task 6 (H-5): the debug_toolbar gates align

`config/urls.py:20` gates on `if "debug_toolbar" in settings.INSTALLED_APPS:` — the same knob development.py uses. RED: pytest (no DB) that constructs the URLconf with a settings stub where DEBUG=true but debug_toolbar absent from INSTALLED_APPS (today: import crash). Verified live before/after with `DEBUG_TOOLBAR=false manage.py check`.

## 7. Task 7 (M-2): bank-account PATCH 404

The update view routes its instance through `BankAccountService.get(...)` (raises ResourceNotFound → 404 — the GET/DELETE path's own pattern), removing the duplicate `.get`. RED: pytest PATCH on a random UUID → 404 (today: 500 — reproduced by the audit agent's probe).

## 8. Task 8 (M-5): the organisation PATCH paths fail with 400s, not 500s

**Backend, RED first.**

- Detail PATCH: route through a typed `OrganisationUpdateSerializer` (name/legal_name/uen/address fields as today, plus `entity_type` ChoiceField over the schema vocabulary, `base_currency` regex-3-char, `country` 2-char) — the raw allowlist dies; `ensure_uen_available` stays. RED: pytest PATCH `entity_type="PTE_LTD"` → 400 field error (today: IntegrityError 500); `base_currency="SGDD"` → 400; valid PATCH unchanged.
- Settings PATCH serializer: `gst_scheme`/`gst_filing_frequency` become ChoiceFields over the DB CHECK vocabularies; `timezone` max_length=50 (matches schema VARCHAR(50)); a `validate()` re-runs the GST-consistency pair (`gst_registered` requires `gst_reg_date`, mirroring the create serializer) using instance-merged effective values. RED: pytest for each of the four 500 paths → 400s.
- Frontend: the settings Base Currency input gains `maxLength={3}` (cheap truth on the UI side).

## 9. Task 9 (M-6): garbage path UUIDs 404 at the routing layer

Swap `<str:..._id>` → `<uuid:..._id>` in `journal/urls.py`, `gst/urls.py`, `banking/urls.py`, `invoicing/urls.py` detail routes (banking's transaction route keeps its parse helper — no behavior change there). Malformed UUIDs then fail routing (404) instead of raising `ValueError` in the view (500). RED: pytest parametrized garbage-UUID sweep across one route per file → 404 (today: 500).

## 10. Task 10 (M-8): the audit trail carries its context

**Backend + schema, RED first.** The schema file is the source of truth — update `database_schema.sql`'s `audit.log_change()` INSERT to read `current_setting('app.client_ip', true)`, `app.user_agent`, `app.request_path` into the existing `ip_address`/`user_agent`/`request_path` columns; emit LOGIN/LOGOUT audit rows from the auth views (login/logout success paths, curated payloads — user_id + ip + action, org_id via the user's default org or NULL for pre-org logins). RED: pytest that a login writes an `event_log` row with action LOGIN and the request's REMOTE_ADDR in ip_address (today: no row; the middleware's variables were never read). Schema reload into both local DBs after the change (the §16-style idempotent convention: DROP FUNCTION IF EXISTS + CREATE).

## 11. Task 11 (M-9 + M-10 + M-13 + M-14 + L-7): CI/config honesty batch

- **CI:** delete the "Generate Test Report" full-suite re-run step; the security job installs the project first (`pip install -e ".[dev]"`) and drops the `|| true` on `safety check` (bandit JSON gets uploaded as an artifact; npm audit stays advisory); the frontend job runs `npm run test:coverage` (the ratchet enforced in CI at last); `cache-dependency-path` already correct (P10). The display-mangled P10 corrective comment is rewritten cleanly (the on-disk YAML was always intact — byte-verified; the comment's mangled spelling gets fixed without changing its meaning).
- **pyproject:** delete the dead `[tool.pytest.ini_options]` block (pytest.ini wins — the warning is live).
- **.gitignore:** `coverage/`, `test-results/`, `playwright-report/`, `*.key` (and honor the DEPLOYMENT.md claim).
- **Makefile:** the `migrate`/`migrations` targets echo the SQL-First warning and exit 1 (truthful refusal over silent contradiction).
- **package.json:** move dev/test tooling to `devDependencies` (vitest, @vitest/coverage-v8, @playwright/test, @axe-core/playwright, @testing-library/*, @types/*, jsdom, eslint, eslint-config-next, typescript, @vitejs/plugin-react, serve-removal); drop `serve` (nothing references it — the static-export leftover). `npm ci` still installs both groups; the standalone image build later can use `--omit=dev`.
- Validation: `npm ci && npm run test:coverage && npm run build:server` locally green after the moves (the lockfile updates via npm, never hand-edited).

## 12. Task 12 (H-6 + H-7 + M-12): the Docker truth pass

No docker binary in this sandbox — **static validation + `docker compose config`-equivalent YAML parse where possible; claims labeled Reasoned where not executable.** The fixes are surgical and reviewable:

- `apps/backend/Dockerfile`: rebuild the backend stage from `pyproject.toml` (`pip install -e .` — every INSTALLED_APPS dep present by construction), pin python base, drop the unrelated FastAPI/Node/HuggingFace stages, real `CMD` (gunicorn), HEALTHCHECK/EXPOSE aligned to 8000.
- `docker-compose.yml`: `DB_PASSWORD` aligned with `POSTGRES_PASSWORD` on all three services; the api command becomes check-then-runserver (no migrate); a comment documents the SQL-First initdb volume.
- `docker/Dockerfile`: the missing `django-ratelimit` + `requests` added to its install list (pinned), unpinned `pip install -U` replaced with the pyproject install.
- DEPLOYMENT.md documents the Docker path honestly (Task 18: the step-by-step includes the docker compose route as optional, marked "validated statically, not built in this environment").

## 13. Task 13 (M-15): the CSP tells the truth in production

`next.config.ts`: `script-src 'self'` + (`'unsafe-eval' 'unsafe-inline'` only when `NODE_ENV === 'development'` — Next 16 standalone doesn't need them in prod); `connect-src` derives the API origin from `NEXT_PUBLIC_API_URL` (localhost default unchanged). RED: vitest can't easily gate next.config — validated by config read + a grep-level assertion in the docs sweep (marked Reasoned-verified); the dev server must still boot (the live gate exercises it).

## 14. Task 14 (M-16 + L-5): root hygiene — the repo stops carrying its session debris

`git rm -r tests/` (the 5 MB of tracked logs/screenshots — no code references them as imports; the AGENTS.md/status mentions are prose), `git rm Agent-Browser-howto.md` (broken symlink), `GEMINI.temp`, `status_10..16.md` + `status_new.md` (superseded by worklog), the stale root scripts (`start_apps.sh` with pasted JWTs, `debug_ledger.py`, `reset_test_password.py`, `test_setup_seed_data.py`, `e2e_test_phases_7_15*.py`, `code_interpreter_qwen*.py`, `database_connect.sh`, `initialize_database.sh`, `run_test_suite.sh` — all verified stale/broken/credential-carrying; DEPLOYMENT.md is the documented flow). Where a script has a keeper function (the service managers' parameterization), the fix is documented in DEPLOYMENT.md instead of keeping the broken copy. The broken untracked symlinks under skills/docs are left alone (skills/ is excluded). Frontend root screenshots (`frontend_*.png`) are superseded by docs/screenshots — removed. Validation: `git grep` for dangling references + the four gates re-run green.

## 15. Task 15 (L-1 + L-3 + L-4 + L-6 + L-9): the truth riders

- **L-1:** the F5 tab's Review/File/Amend actions gate on `hasPermission("can_file_gst")`; banking Edit/Deactivate on `can_manage_banking`; contacts row actions on `can_manage_org` (matching the backend's posture — contacts PATCH/DELETE is member-allowed today; the UI gates to managers only where the marquee actions are corrections. Decision: contacts row actions gate on `can_manage_org` — the truthful posture for correction surfaces).
- **L-3:** `date.today()` → `timezone.localdate()` at the 10 listed sites (behavior-identical in a SGT-located host; correct in UTC containers). RED: pytest that `tax_code_service.get_tax_code_by_code(as_of=localdate)` path resolves (the boundary is exercised by the existing suite after the swap).
- **L-4:** the ledger view drops the `entry__is_reversed=False` filter (both sides of a reversal pair visible; consistent with TB). RED: pytest that a reversed entry's original lines appear in the ledger list (today: filtered out).
- **L-6:** the dead `ValidationError` branch in `custom_exception_handler` is removed (dead code, shadowing).
- **L-9:** the three org write paths wrap the save in a try/except IntegrityError → re-raise the UEN 400 field error (the TOCTOU loser degrades to the same clean 400). RED: a test triggering the constraint via a direct model save through the same helper isn't practical — the except-arm is added and the existing serial tests stay green (documented Reasoned).

## 16. Task 16 (live gate): e2e + screenshots + docs

The e2e suite gains a p11 spec (gated, backend-live): the F5 boxes panel renders REAL values (computed return → panel open → assert non-"—" box text), the contacts edit round-trip (open dialog → prefilled UEN from the detail payload → save → the field persists), the dashboard GST payable non-zero after real activity. Existing specs updated where surfaces changed (the dashboard prefixes, the reports tab keys). Then screenshots `docs/screenshots/59..64_*_session22.png` (F5 boxes panel with values, contacts edit dialog prefilled, dashboard with real GST payable, settings org card, a credit-note-visible ledger or reports aged tab, bank accounts tab) — real UI login path, content-based waits, capture driver committed (`apps/web/scripts/p11_screenshots.mjs`).

## 17. Task 17: `.env.example` truth pass

Backend example gains `LOG_DIR` (Task 2's new knob) with the deploy default and the `/var/log/ledgersg` mkdir note; every other read re-audited 1:1 (config( / process.env sweep). Web example unchanged unless Task 13 introduces a var (it does not — `NEXT_PUBLIC_API_URL` is the existing read).

## 18. Task 18: docs truth pass + the DEPLOYMENT.md rewrite

- **DEPLOYMENT.md rewritten as the step-by-step fresh-host guide starting from `git clone`**: prerequisites (PG 16+, Redis, Node 20+, Python 3.12+), the rootless-PG appendix (the `docs/setup_pg_z.sh` + skill path this session used), schema load (both DBs), backend venv + `.env` (every var), frontend `npm ci` + `.env.local`, dev boot (backend runserver + web dev), the test gates with the exact invocations, the production build (build:server + start, the standalone output), gunicorn + production settings (with the LOG_DIR mkdir step and the SECRET_KEY gate), the Docker path (compose — marked statically-validated), the e2e live-gate bootstrap sequence, the deployment checklist with the current counts. Every command in the guide is one this session actually ran or is byte-derived from the repo's configs.
- README (counts, the P11 milestone section), CLAUDE.md, PAD, AGENTS.md (P11 patterns), ledgersg_SKILL (lessons 42+, version bump 1.9→2.0), worklog entry, `docs/session_23.md` (the session-22 log per the naming convention), `docs/REMEDIATION_2026-11-23_P11_REPORT.md`.

---

## 19. Verification Gate (definition of done for the sprint)

| # | Gate | Expected |
|---|---|---|
| 1 | `pytest --reuse-db --no-migrations -q` | all green (687 baseline + new, 0 failed) |
| 2 | `npm run typecheck` / `npx vitest run` / eslint (touched) | clean / all green / parity |
| 3 | `npm run test:coverage` | green at the ratchet (no lowering) |
| 4 | `npm run build:server` | green |
| 5 | `npm run test:e2e` (no backend) | green, new spec gated with reasons |
| 6 | `npm run test:e2e:full` (live stack, `--workers=1`) | all green |
| 7 | Accounting spot checks | approved SALES_CREDIT_NOTE → AR credited/revenue debited; F5: converted quote counts once; credit note nets its boxes; dashboard GST payable non-zero on real data |
| 8 | Contract spot checks | F5 panel shows values (no "—" row); deadlines banner renders with a REVIEWED return; contacts edit round-trip preserves UEN/Peppol; gst_reg_number PATCH persists; bank PATCH missing id → 404; org PATCH garbage entity_type/base_currency → 400; garbage path UUID → 404 |
| 9 | Production-settings spot check | `config.settings.production` imports + cache backend resolves + LOGGING copy-on-write (the settings-gate test) |
| 10 | CI YAML | parses; no full-suite re-run step; coverage step present; no `|| true` on safety |
| 11 | Screenshots | ≥ 6 new non-empty unique PNGs (content-verified) |
| 12 | Docs sweep | DEPLOYMENT.md = the fresh-host step-by-step; `.env.example` matches the code; no stale counts |
| 13 | `git status` clean; commit set matches §20 | all on `main` |

## 20. Commit Plan (conventional commits, single branch `main`)

1. `fix(journal,gst): credit notes post reversed entries and net in F5 — quotes excluded (P11/C-1, H-3)`
2. `fix(config): production settings boot — builtin Redis cache, LOG_DIR knob, copy-on-write (P11/C-2)`
3. `fix(web,invoicing): contacts edit dialog tells the truth — detail prefill, gst_reg_number, debounce (P11/H-1, M-3, M-4)`
4. `fix(web,gst): F5 boxes panel keys + deadlines envelope + REVIEWED deadline filter (P11/H-2, M-1, M-11)`
5. `fix(web,reporting): dashboard GST liability re-sourced — chart + prefix truth (P11/H-4, M-7, L-2)`
6. `fix(config): debug_toolbar gates align — INSTALLED_APPS is the single knob (P11/H-5)`
7. `fix(banking): account PATCH 404s on a missing id (P11/M-2)`
8. `fix(core): organisation PATCH paths 400 — typed detail serializer, choice fields, tz length (P11/M-5)`
9. `fix(api): garbage path UUIDs 404 at the routing layer (P11/M-6)`
10. `feat(audit): event context + LOGIN/LOGOUT emission (P11/M-8)`
11. `chore(ci,web): config honesty — coverage in CI, dead steps removed, devDeps split, gitignore, Makefile truth (P11/M-9, M-10, M-13, M-14, L-7)`
12. `fix(docker): images boot — pinned installs, CMD, compose credentials, no migrate (P11/H-6, H-7, M-12)`
13. `fix(web): CSP production truth — unsafe-* dev-only, connect-src from env (P11/M-15)`
14. `chore(repo): root hygiene — tracked logs, broken symlink, stale scripts removed (P11/M-16, L-5)`
15. `fix(web,core): truth riders — permission gates, localdate, ledger reversals, UEN TOCTOU (P11/L-1, L-3, L-4, L-6, L-9)`
16. `test(web,e2e): P11 specs — F5 boxes, contacts round-trip, dashboard GST (P11 live gate)`
17. `docs(screenshots): session 22 captures of the P11 surfaces (59-64)`
18. `docs: P11 truth pass — DEPLOYMENT fresh-host guide rewrite, README/PAD/CLAUDE/AGENTS/SKILL + .env.example`
19. `docs(worklog): session 22 worklog, session log, P11 report`

(Adjacent tasks may fold where they share a RED→GREEN cycle; push incrementally after each task — the workspace-reset safeguard.)

## 21. Deferred Debt Register (explicit, not silently dropped)

Carried forward unchanged from P10 §20 (H-02 base-currency reporting; M-1 audit READ surface — Task 10 makes the WRITES carry context, the GET /audit/events endpoint remains deferred; CSRF Origin-check; backend ruff debt; frontend eslint debt; F5 rate-basis semantics (Task 1 fixes direction/netting/type-filter — the period-cut semantics stay registered); pay_return; full PINT Schematron; ledger pagination (Task 15/L-4 fixes visibility, pagination itself stays registered); invoice update_line; B6 list-envelope (Task 4 standardizes the deadlines endpoint only); aged netting; quote lifecycle DB enum; TB zero-activity; reports export; TAX-group coarse type; Storecove authenticate; dashboard trends endpoint; CoA management page; Reg-11 remainder; password reset; contacts merge; email verification; blank-UEN schema modeling; e2e bootstrap as a repo script (P11 ships screenshots + spec; the bootstrap script stays a candidate); coverage ratchet headroom).

New this sprint (registered, not dropped):
- **Docker validation debt:** the Dockerfile/compose fixes are statically validated only (no docker binary in the environment); building the images on a docker host is the follow-up.
- **Audit L-8 dedup:** the banking double-emission (trigger + curated events) needs an ownership decision (keep curated + exempt tables from the trigger, or keep trigger + drop curated) — deferred with both options documented.
- **`get_f5_box_amounts` shared helper:** Task 1's type/netting logic and Task 5's dashboard re-source share semantics; a single shared SQL helper is the refactor candidate once both are green.
- **Frontend e2e permission-gate coverage:** L-1's gating is vitest-asserted; an e2e member-role run stays deferred (needs a second bootstrap user).

## 22. Open decisions resolved by this plan

- **C-1 mechanism:** flip direction inside `post_invoice` (one posting engine, type-aware) over a separate credit-note poster — the schema, transition gate, and reversal machinery all treat credit notes as posting documents already; the single engine keeps the invariants gate meaningful. Debit notes keep invoice direction (correct accounting).
- **C-2 cache:** inherit base's builtin RedisCache over adding `django-redis` — the builtin backend is the repo's own convention (base + testing use it), needs no new dependency, and the failure was the *undeclared override*, not the backend choice.
- **H-1 prefill:** detail-endpoint prefill (the hook exists) over widening the list serializer alone — the dialog needs the full field set regardless, and the list serializer widening rides along only to make the row badges truthful.
- **M-1 envelope:** the backend standardizes to `{results, count}` (the repo's list convention) rather than the frontend reading `.data` — aligns with every sibling endpoint and kills the bug class; both sides get contract tests.
- **Task 11 package split:** a single devDependencies move with `npm ci` validation (the lockfile updates through npm, never hand-edited); `serve` removed as the retired-mode leftover.
- **Task 14 removals:** everything removed is either verified-broken (exit-0 script, /home/project paths), superseded (status files vs worklog), or credential-carrying (start_apps.sh) — the session transcripts preserved in `docs/session_*.md` remain the history; the DEPLOYMENT.md rewrite becomes the single operational source.
- **M-8 scope:** trigger-side context columns + LOGIN/LOGOUT emission ship now; the READ surface and the dedup decision stay deferred (both registered).
- **Task 12 honesty:** no docker binary exists in this environment — the fixes ship as statically-validated surgical diffs with the limitation stated in the report and DEPLOYMENT.md, rather than claiming a built-and-booted image.
