# LedgerSG — Remediation Plan (P15 Sprint: Tree Repair, P14 Completion & the Live Gate)

**Date:** 2026-11-26 (session 30)
**Base commit:** `4ad18d2e` (main — post-P13, post the two independent audits,
the partially-committed P14 work and the four session-log commits)
**Source inputs:** `docs/REMEDIATION_PLAN_2026-11-25_P14.md` (the P14 plan —
partially executed then committed to WRONG PATHS by the interrupted session),
`docs/session_29.md` (both the P14 execution narrative AND the interrupted
repair session's narrative), `docs/partial_p14_remediation_changes.txt` (the
previous session's own path-warning note), the two independent audits
(`docs/Code_Review_Audit_2026-11-24_independent_1.md` — live-executed;
`docs/Code_Review_Audit_2026-11-24_independent_2.md` — source review), and
the P13 report (`docs/REMEDIATION_2026-11-24_P13_REPORT.md`).
**Method for execution:** TDD (RED → GREEN → full gate), lint parity on
touched files, conventional commits on `main`, `skills/` excluded from all
checks/tests/compilation, schema changes as hand-written idempotent DDL
(SQL-First, never `makemigrations`).

---

## 1. The state of `main` (verified this session, before the plan)

### Baselines reproduced live on a fresh sandbox

- Environment: rootless PG 17 via `docs/setup_pg_z.sh` (role `ledgersg`
  SUPERUSER + both DBs, schema v1.1.0 loaded, 0 errors), Redis 8.0.2 on
  :6379 from debs, backend `.venv` via `pip install -e ".[dev]"`,
  `npm ci`, Playwright 1.58.2 + chromium-1208.
- Frontend (unaffected by the corruption): `npx tsc --noEmit` **0 errors** ·
  `npx vitest run` **530/530 (60 files)** · `npx eslint src` **9 findings**
  (the documented deferred register).
- Backend: **DOES NOT BOOT** — see R-0.

### THE HEADLINE FINDING: commit `2bcb43f0` ("partial p14 changes") broke the tree

The interrupted session 29 (first half) executed most of the P14 plan but
committed its work to wrong paths. Verified in this session's clone:

| Damage | Evidence |
|---|---|
| **`apps/backend/apps/core/models/payment.py` DESTROYED** — the real `Payment` model file (TenantModel, PAYMENT_TYPES, FKs) was overwritten with the **payment serializer** code (plus the intended P14/H-2 fix) | `git show 2bcb43f0~1:…payment.py` = the model; the file at HEAD = `PaymentSerializer` importing `from apps.core.models import Payment, …` → **circular import**; `manage.py check` fails with `ImportError: cannot import name 'Payment' from partially initialized module` (reproduced live this session) |
| **Misplaced new modules** (their consumers import the CANONICAL paths): `apps/backend/gst/period_lock.py` (consumers: `journal_service.py:222`, `document_service.py:447,883` import `apps.gst.services.period_lock`), `apps/backend/gst/validators.py` (tests import `apps.core.validators`), `apps/backend/organisation_service.py` (a full rewrite carrying the C-1 `set_config` fix; canonical: `apps/core/services/organisation_service.py`), `apps/backend/return_service.py` (carrying the C-2 FILED-immutability + H-05b override-reason fixes; canonical: `apps/gst/services/return_service.py`) | `ls` + grep of import statements (this session) |
| **Correctly-placed P14 fixes that reference the misplaced modules** — `journal_service.py` (+9: the H-3 guard wiring), `document_service.py` (+171: the H-4 credit-note contract + H-5 GST-registration guard + H-3 wiring), `banking/services/payment_service.py` (+40: the H-1 row-lock + outstanding-balance cap + H-2 status set) | `git show 2bcb43f0 --stat`; diffs reviewed — the fixes themselves are sound |
| **P14 tests committed at the CORRECT location** (`apps/backend/tests/test_*_p14.py`, `tests/integration/test_payment_allocation_contract_p14.py`, `test_rls_conformance.py`) — all RED (never ran green: the backend cannot boot; several carry known test-side bugs the interrupted session diagnosed) | import graph + the session_29 second-half narrative |
| **Stranded helper scripts** — `scripts/daemonize.py`, `scripts/mobile-nav-audit.js`, `scripts/rls_smoke.py` (correctly placed at repo `scripts/`; the rls_smoke needs the M-1 format fixes the interrupted session never landed) | file review this session |
| **Known test-side bugs in the committed RED tests** (diagnosed in session_29's second half, fixes never landed): (a) `test_filed_return_immutability.py` imports DRF's `ValidationError` while the service raises `common.exceptions.ValidationError`; (b) `test_gst_period_lock_p14.py`'s approve-path tests skip the DRAFT→(SENT)→APPROVED state machine; (c) period-lock/input-validation test classes missing `@pytest.mark.django_db`; (d) the H-2 fixture creates `UserOrganisation` without `accepted_at`; (e) `test_gst_period_lock_p14` posting fixtures lack document lines | session_29 lines 156–168 + re-verified against the files this session |

**Net effect:** the current `main` is unbootable and unshippable. The repair
session (session_29 second half) diagnosed and fixed all of this in its own
workspace but was interrupted during Phase 2 (live e2e contract fixes) and
committed NOTHING except session-log docs (the four "update session log"
commits). This plan re-executes that work from scratch with the same
diagnoses as inputs.

### Re-verified from the P14 plan (still true at HEAD)

- H-6 gap live: `gst.tax_code`, `audit.event_log`, `core.user_organisation`,
  `gst.organisation_peppol_settings`, `core.role` carry `org_id` with NO RLS
  (query executed this session); `core.organisation` has policies but RLS
  never ENABLED; schema still at v1.1.0 (no §17).
- The M-form GST regex question SETTLED with primary sources this session:
  the OECD TIN guide (Singapore, Section II) gives ASGD = `ANNNNNNNC`
  (9 chars, M + 7 digits + check letter) while real-world IRAS-issued
  numbers on company documents are M + 8 digits + check letter (10 chars,
  e.g. `M90356174N` on FSM Global's forms, `M90001281J` on SIA's). Both
  lengths are accepted by the committed P14 test
  (`M90345678K` True, `M1234567A` True). Decision: `^M\d{7,8}[A-Z]$`
  (format-only; no invented checksum — the P14 §6 decision stands).

### The mobile navigation menu + TailwindCSS v4 (the standing questions)

The P12/P13 verdicts stand and this session re-validated the setup: the v4
installation is clean (`@import "tailwindcss"` + `@theme`, no legacy config
file — verified in `apps/web/src/app/globals.css`), the P12 overlay contract
and the P13 visibility/z-index fixes are in the tree, and no v4 trap pattern
(space-y with explicit-margin children, shadow-scale drift, bare-HSL vars)
exists on the nav surface. **The nav works; no Tailwind v4 bug exists.** The
live re-probe (17/17 checks at 375/800/1280 via `scripts/mobile-nav-audit.js`
against the daemonized dev stack) is gate item G-13 below — executed AFTER
the tree repair, since the backend cannot currently boot to serve the
authenticated surfaces.

---

## 2. Findings register (drives §3)

| ID | Sev | Source | Finding |
|---|---|---|---|
| R-0 | **Critical** | this session | The tree at HEAD is broken: Payment model destroyed, 4 misplaced modules, unbootable backend — the partially-committed P14 work |
| C-1 | **Critical** | audit1 / P14 | Org creation 500s under the documented runtime role `ledgersg_app` — seeding runs with no RLS context |
| C-2 | **Critical** | audit1 / P14 | FILED/AMENDED F5 returns silently mutable via `?force=true` |
| H-1 | High | audit1 / P14 | Payment allocations may exceed the document balance |
| H-2 | High | audit1 / P14 | Second instalment on a PARTIALLY_PAID invoice rejected (serializer APPROVED-only) |
| H-3 | High | audit1 / P14 | No GST-lock on filed periods |
| H-4 | High | audit1 / P14 | Credit notes require no original-invoice reference/same-contact/cap |
| H-5 | High | audit1 / P14 | GST charged by non-registered orgs / before `gst_reg_date` |
| H-6 | High | audit1 / P14 | RLS incomplete (6 tenant tables unprotected; audit fn `search_path` unpinned) |
| H-7 | High | audit1 / P14 | The whole gate runs as SUPERUSER — RLS never exercised |
| H-8 | High | audit1 / P14 | Known-vulnerable dependency set (backend: django 6.0.2 / DRF 3.16.1 / lxml 6.0.2 / weasyprint 68.1; frontend: next 16.1.6 critical / zod <4.6.6) |
| H-9 | High | audit1 / P14 | Predictable JWT signing key on the Docker path; `service.py` skips the key gate |
| H-04b | High | audit2 / P14 | NRIC PayNow identifiers unmasked (PDPA) |
| H-05b | High | audit2 / P14 | F5 box overrides (6/7, 9–15) accepted with no reason/evidence trail |
| X-1 | High | audit2 / P14 | XXE / entity-expansion DoS — unhardened lxml parser on an attacker-adjacent input path |
| M-1 | Medium | audit1+2 / P14 | UEN/GST-number validation regex-only, mislabeled, non-UEN pattern, valid UEN-form GST numbers rejected |
| M-4 | Medium | audit1 / P14 | Malformed document input → 500 (missing `lines` KeyError; no line-item schema/bounds) |
| M-5 | Medium | audit1 / P14 | Viewer role can create/delete contacts and reach the send path |
| M-6a | Medium | audit1 / P14 | `audit.log_change` SECURITY DEFINER without pinned `search_path` |
| M-7c | Low | audit1 / P14 | Schema comment claims the Peppol API key is "Encrypted" — it is not |
| M-10 | Medium | audit1 / P14 | Duplicate tax-code rows (system + org copies) without `effective_on` |
| F-A | Medium | P14 plan | Fresh-DB e2e bootstrap gap: `ensureDemoActivity` never CREATES the F5 return |
| F-B | Medium | session_29/2nd half | The live e2e suite's known contract breaks under the P14 fixes: (a) the api-client's parallel-401 double-refresh race (refresh #200 rotates the token; the concurrent second refresh sends the now-blacklisted old token → 401 → logout mid-suite) — needs single-flight refresh; (b) `e2e/p11.spec.ts` creates credit notes without the new `related_document_id` contract; (c) the p11 CN fixture reuses ANY paid invoice with no cap headroom (250.00 CN vs an 80.00 invoice now 400s); (d) `e2e/p10.spec.ts` registers orgs with pseudo-UENs the M-1 gate now rejects |
| D-1 | Medium | this session | Docs truth: every count/milestone/claim (README, CLAUDE, PAD, AGENTS, ledgersg_SKILL, DEPLOYMENT, API guide, worklog) still describes the P13 state and must reflect the repaired, P14-complete, upgraded tree |

**Explicitly deferred (registered, carried forward — not silently dropped):**
everything in the P14 plan §6 deferred register (audit1 M-2, M-3, M-6b,
M-8, M-9, M-7-full; audit2 M-01..M-05, M-07, M-08; UEN checksum pending the
official ACRA algorithm; DB-trigger enforcement layer for H-3; the evidence/
attachment model for H-05b) plus the P13 deferred register unchanged.

---

## 3. Task list (TDD; every production-code change ships with its failing test first)

### Phase 0 — Tree repair (R-0; no new features, restore + relocate)

| # | Task | Verification |
|---|---|---|
| 0.1 | Restore `apps/backend/apps/core/models/payment.py` from `2bcb43f0~1` (the real `Payment` TenantModel) | `manage.py check` boots (0 errors, the documented W001 only) |
| 0.2 | Port the stranded H-2 serializer fix (the `ALLOCATABLE_STATUSES` block + message) from the corrupted file into `apps/banking/serializers/payment.py`; delete nothing else | The corrupted file's diff vs the canonical serializer is fully ported; H-2 tests green |
| 0.3 | Move `gst/period_lock.py` → `apps/gst/services/period_lock.py` (byte-identical; it is correctly written) | H-3 imports resolve; `python -c "import apps.gst.services.period_lock"` |
| 0.4 | Move `gst/validators.py` → `apps/core/validators.py` with the M-form regex corrected to `^M\d{7,8}[A-Z]$` (OECD 9-char + real-world 10-char; both documented in the docstring) | M-1 table-driven tests (committed RED file) pass for BOTH M-forms |
| 0.5 | Port the C-1 fix (the `set_config('app.current_org_id', …, true)` block before `_seed_chart_of_accounts`) from the misplaced `organisation_service.py` into the canonical `apps/core/services/organisation_service.py` — port ONLY the fix; do not adopt the misplaced file's wholesale rewrite if it diverges from canonical (diff first; the interrupted session ported the block into the canonical file) | C-1 regression test green; full org-creation flow unchanged |
| 0.6 | Port the C-2 (FILED/AMENDED immutability) + H-05b (override_reason) fixes from the misplaced `return_service.py` into the canonical `apps/gst/services/return_service.py` (diff first; port the fix blocks, keep canonical structure) | C-2 tests green (after 0.7); H-05b tests green |
| 0.7 | Fix the committed RED tests' test-side bugs: (a) `test_filed_return_immutability.py` → import `common.exceptions.ValidationError`; (b) `test_gst_period_lock_p14.py` approve-path tests → SENT-first state machine + document lines on fixtures; (c) missing `@pytest.mark.django_db` marks; (d) `accepted_at=timezone.now()` on the H-2 fixture's membership; (e) `test_rls_conformance.py` → intersect the sweep with real tenant tables + env-overridable app-role password (schema §15 default) | The files run and their failures map ONLY to missing implementations (the honest RED state) |
| 0.8 | Delete the four misplaced files (`gst/`, `organisation_service.py`, `return_service.py` at `apps/backend/` root) | `ls` clean; no import references them |
| 0.9 | Full backend suite interim run + `manage.py check` | Expected: the pre-P14 baseline (750P/5S) + the committed P14 tests still RED where implementations are missing (Phase 1 scope) — every failure mapped |

### Phase 1 — Complete the P14 remediation (the RED tests' implementations)

| # | Finding(s) | Task | Tests (RED first where not already committed) |
|---|---|---|---|
| 1.1 | M-4 | Document-input hardening: a nested line schema (`account_id` UUID, `description` ≤ 500, `quantity` > 0 ≤ 10^6, `unit_price` ≥ 0 < 10^13, optional `tax_code_id` UUID, `discount_pct` ∈ [0,100]); `lines` required (min_length=1) for create; the view forwards `related_document_id` (H-4's API surface); service re-validates defensively | Missing `lines` → 400 (was KeyError 500); negative/oversized unit_price → 400; valid document unchanged; linked credit note creatable via API |
| 1.2 | X-1 | One shared hardened lxml parser (`resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False`) for schemas AND candidate documents in `xml_validation_service` | XXE payload rejected without file access; billion-laughs rejected fast; valid UBL still validates (the committed RED file's behavioral gates; config introspection replaced by a policy-constant assertion per the session-29 lesson) |
| 1.3 | H-04b | NRIC PayNow masking: bank-account serializers mask `paynow_id` for `paynow_type=NRIC` on READ (first char + last 3); write-path rejects masked echoes (values containing `*`); PDPA docstring | Round-trip: create real NRIC → read masked → PATCH masked echo → 400 → PATCH fresh NRIC → 200; mobile/VR IDs unmasked |
| 1.4 | M-5 | Viewer gates: contact create/delete + document send require `can_create_invoices` (module-level shared helper; `_check_permission` does not exist on those classes — add one) | Table-driven role×endpoint: Viewer 403 on contact POST/DELETE + send; Manager/Owner 2xx |
| 1.5 | M-10 | `list_tax_codes` dedupe without `effective_on`: per `(code, effective_from, effective_to)` the org row shadows the system row | The 23-row duplicate list → one row per code-and-band (SR keeps its legitimate 2007/2023 history bands — assert band uniqueness, not code uniqueness); `?effective_on=` unchanged |
| 1.6 | H-6 + M-6a + M-7c | Schema §17 (idempotent DDL, version v1.2.0): ENABLE RLS + policies for `core.organisation` (bootstrap-aware NULL-context read/insert), `core.user_organisation` (NULL-context read), `core.role`, `gst.organisation_peppol_settings` (strict org scope), `gst.tax_code` (`org_id IS NULL OR org_id = current`), `audit.event_log` (strict org scope; INSERT stays via the definer trigger); `ALTER FUNCTION audit.log_change(…) SET search_path = pg_catalog, audit, public`; M-7c comment honesty on `access_point_api_key`; models stay `managed=False`; reload BOTH DBs; conformance gate extended | `tests/test_rls_conformance.py`: every tenant table has `relrowsecurity`; `pg_proc.proconfig` pins the search_path; full suite green on the patched DBs (fixtures run as SUPERUSER — unaffected; `ledgersg_app` covered by 1.7) |
| 1.7 | C-1 + H-7 | The live runtime-role proof: `scripts/rls_smoke.py` fixed up (M-1-compliant UEN/GST generators, `is_bank=true` GL filter, the DRAFT→APPROVED canonical approve path) and run against a `DB_USER=ledgersg_app` runserver: register → create org → contact → invoice → approve → payment → F5, all 2xx | The C-1 repro inverted live (201 as `ledgersg_app`); RLS live assertions: cross-org SELECT blocked, own-org readable |
| 1.8 | H-8 | Dependency upgrades through the package managers: backend `pip install -U "django~=6.0.8" "djangorestframework>=3.18.2" "lxml>=6.1.0" "weasyprint>=70.0"` (uv), frontend `npm install next@^16.4 zod@^4.6` (+ lockfile); if a specific upgrade breaks incompatibly, revert THAT package and register it with evidence | Full backend suite + frontend gates on the upgraded tree; `pip-audit` / `npm audit --omit=dev` deltas recorded in the report |
| 1.9 | H-9 | Docker path: the entrypoint generates a strong per-boot key (`python -c "import secrets;…"`) when `SECRET_KEY` is unset; `service.py` gains the key-strength gate + `ALLOWED_HOSTS` from env (reload base-then-service in the test helper — the session-29 import-order lesson) | Settings-gate test: weak key → refuse (ImproperlyConfigured, the codebase convention); Dockerfile carries no fixed-prefix key |
| 1.10 | F-A | `ensureDemoActivity` creates the F5 return (`POST /gst/returns/` MONTHLY current month) when the list is empty, then force-computes | Fresh-DB e2e bootstrap reasoning + the live run green |
| 1.11 | M-1 wiring | Wire `validate_uen` / `validate_gst_reg_number` into the org-create/register + contact serializers (the register serializer's `startswith("M")` check is REPLACED; `OrganisationUpdateSerializer` keeps excluding `gst_reg_number` — owned by `GSTRegistrationSerializer` per P5/M-6; the committed test targets the real contract) | The committed table-driven validator tests + serializer round-trips; the previously-rejected valid UEN-form GST number now passes |
| 1.12 | — | `.env.example` truth pass: root + backend + web templates against every env read (grep cross-check `os.environ`/`os.getenv`/`process.env`); add the new optional test var (the app-role password) to the backend template | grep-level cross-check |

### Phase 2 — The live gate (F-B) + full verification

| # | Finding(s) | Task | Verification |
|---|---|---|---|
| 2.1 | F-B(a) | Single-flight refresh in `api-client.ts`: `tryRefreshToken` shares ONE in-flight promise across concurrent 401s (the second 401 awaits the same refresh instead of double-firing against the rotated token) | RED vitest: two parallel 401s trigger exactly ONE refresh call → GREEN; the live session spec stops logging out mid-suite |
| 2.2 | F-B(b,c,d) | e2e contract fixes: `p11.spec.ts` CN creation sends `related_document_id` (the H-4 contract) and its invoice-reuse logic requires cap headroom (a 250.00 CN needs ≥250.00 `total_incl - credited` headroom); `p10.spec.ts` registers with a real ACRA-format UEN | The live e2e:full suite green |
| 2.3 | — | The full verification gate (§4) end to end on the remediated, upgraded tree | All green |
| 2.4 | — | Screenshots of the remediated surfaces → `docs/screenshots/80-87_*_session30.png` (or the next free index), pixel + DOM verified per the repo convention | The capture driver's DOM assertions |
| 2.5 | D-1 | Docs truth pass: DEPLOYMENT.md (the C-1/H-7 runtime-role workflow §12.3, §7 counts, upgraded versions, the rls_smoke gate step, the P14/P15 contracts), `API_CLI_Usage_Guide.md` (the new 409/400/masking contracts + versions), README/CLAUDE/PAD/AGENTS/ledgersg_SKILL (P15 milestone + honest counts + the repair narrative + new lessons) | Every claim checked against executed gate output |
| 2.6 | — | worklog.md + session_30.md + the P15 report + the vitest/playwright suite status documented (both suites present and green — the sprint instruction's "add … by modifying the respective config files" is satisfied by the existing mature configs plus this sprint's additions; verified, not re-scaffolded) | Cross-checked |

---

## 4. Verification gate (all must be green before push)

1. `pytest --reuse-db --no-migrations -q` → 750 baseline + the P14 tests, 0 failed, ≤ the documented skips
2. `pytest tests/invariants -q` and `pytest tests/security -q` → green (incl. the new RLS-conformance, filed-immutability, GST-lock gates)
3. `manage.py check` (testing settings) → 0 errors (the documented W001 only)
4. Production boot gate → still boots behind its gates; `service.py` refuses weak keys
5. `npx tsc --noEmit` → 0; `npx vitest run` → 530 + the new single-flight tests; `npm run test:coverage` green at both ratchets
6. `npx eslint src` → 9 findings (the documented deferred register; no new)
7. `npm run build:server` → green
8. `npm run test:e2e` (no backend) → 11P + 29 gated
9. `npm run test:e2e:full` (live stack, demo trio) → 40P + the F-A hardened bootstrap
10. GST live spot-proof: the IRAS 2dp quantum still green (9.00)
11. The C-1 live repro inverted: `DB_USER=ledgersg_app` runserver → `POST /organisations/` → **201** (the rls_smoke walk)
12. RLS live assertions as `ledgersg_app`: cross-org SELECT blocked, own-org readable, `audit.log_change` search_path pinned
13. Mobile-nav re-probe (the 17/17 checklist) on the remediated tree at 375/800/1280
14. Screenshots present + DOM-verified
15. `git ls-files` hygiene gate (no `.env`, no keys, no `*.pyc`, no misplaced modules)
16. Ruff parity on touched files (no new findings vs the pre-P15 register)

## 5. Commit plan

Conventional commits on `main` only, one per logical task, mirroring the P14
plan §5 ordering: the Phase-0 tree repair (the Payment model restore + the
stranded-fix relocations — possibly split repair vs relocation), then the
Phase-1 completions in task order (input hardening, XXE, masking, viewer
gates, tax-code dedupe, schema §17 + RLS completion, the C-1 live proof,
dependency upgrades, Docker key, e2e bootstrap, validators wiring, env
templates), then the Phase-2 batch (single-flight refresh + the e2e contract
fixes), the screenshots, the docs truth pass, the report/session/worklog.
Push via `docs/ssh_git_wrapper_v3.py --remote git@github.com:nordeim/ledgersg.git`
with remote-ref verification (the paramiko shim if no OpenSSH binary).

## 6. Deferred register

Everything in §2's deferred paragraph, unchanged and explicit, plus:
- **UEN checksum** — format-only validation shipped; the official ACRA
  check-letter algorithm remains the P16 input (the OECD guide documents the
  structure but not the modulus; inventing one would reject valid numbers).
- **H-3 DB-trigger layer** — the derived runtime lock shipped; a
  `journal.entry` trigger is the P16 hardening item.
- **F-form foreign-company UENs** (`F000NNNNNC`/`FDDDNNNNNC` per the OECD
  guide) are not accepted by `validate_uen` — registered as a P16 decision
  (foreign-company onboarding scope).
