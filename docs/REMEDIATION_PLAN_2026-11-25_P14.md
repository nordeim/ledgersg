# LedgerSG — Remediation Plan (P14 Sprint: Runtime-Role Truth, Statutory Immutability & Input Hardening)

**Date:** 2026-11-25 (session 29)
**Base commit:** `a0226f43` (main — post-P13 + the two independent audits)
**Source audits:** `docs/Code_Review_Audit_2026-11-24_independent_1.md`
(live-executed: DB + runserver + API probes — C-1/C-2/H-1…H-9/M-1…M-10) and
`docs/Code_Review_Audit_2026-11-24_independent_2.md` (source review —
H-01…H-05/M-01…M-08). Every Critical/High re-verified by hand in source this
session before this plan was written (see §1); one audit-2 claim (H-03
"hardcoded 9% everywhere") was re-verified as **partially false** — the
document path resolves dated rates via `tax_code_id`
(`get_tax_code_by_code(..., as_of=)`); only the documented no-code fallback
in the standalone calculator defaults to 9%.
**Baselines reproduced live before planning:** backend 750P/0F/5S ·
`npx tsc --noEmit` 0 · vitest 530/530 · eslint 9 (the documented deferred
register) · coverage green at both ratchets · `build:server` green · e2e
default 11P+29 gated · **live e2e:full 40P/0F/0S** (after seeding the demo
substrate; the fresh-DB bootstrap gap is finding F-A below) · the mobile-nav
P12/P13 contract re-verified live at 375/800/1280 (17/17 probe checks,
including the closed-drawer visibility, the X-toggle hit target and the v4
trap sweep — the nav works; no Tailwind v4 bug exists).
**Method for execution:** TDD (RED → GREEN → full gate), lint parity on
touched files, conventional commits on `main`, `skills/` excluded from all
checks/tests/compilation, schema changes as hand-written idempotent DDL
(SQL-First, never `makemigrations`).

---

## 1. Sprint audit verdicts (verified this session, before the plan)

### Baselines — reproduced exactly

All documented P13 gates reproduced on a fresh sandbox (PG 17 rootless via
`docs/setup_pg_z.sh` + `skills/rootless-postgresql`; Redis from debs; venv
rebuilt; `npm ci` + chromium-1208): backend **750P/0F/5S**, tsc **0**,
vitest **530/530**, eslint **9**, coverage **green**, build:server
**green**, e2e default **11P + 29 gated**, live e2e:full **40P/0F/0S**.

### The mobile navigation menu — WORKS (re-verified live, post-P13)

17/17 probe checks at 375/800/1280: the toggle renders and operates; the
closed drawer is `visibility:hidden` (P13/H-2 intact); the overlay renders;
the X toggle is the real `elementFromPoint` hit target (P13/M-1 intact);
after close the drawer is hidden again; no horizontal overflow; no
unexpected console errors; tablet/desktop bands pin the sidebar sticky;
the `space-y` children carry no explicit margins (the documented v4 trap
sweep is clean). **No TailwindCSS v4 bug exists** (re-confirmed; the P12/P13
rule-trace verdicts stand).

### The two independent audits — every Critical/High hand-verified in source

- **C-1 CONFIRMED** (`organisation_service.py:28-80`): `create_organisation`
  seeds CoA/tax codes/fiscal year/owner role with no RLS context; the seed
  SQL function is **not** SECURITY DEFINER; under the documented runtime
  role `ledgersg_app` the `coa.account` INSERT violates the RLS WITH CHECK
  → 500. The whole test/e2e stack runs as the SUPERUSER `ledgersg`, which
  bypasses RLS — that is why no test sees it (H-7).
- **C-2 CONFIRMED** (`return_service.generate_f5`): the status guard is
  `not in ("DRAFT","COMPUTED") and not force_recalculate` — `force=true`
  bypasses EVERY status including FILED/AMENDED; boxes are then overwritten
  and `status` set back to COMPUTED while `filed_at` stays populated.
- **H-1 CONFIRMED** (`payment_service.allocate` + serializers): only
  `allocations ≤ payment.amount` is checked — never
  `allocated_amount ≤ document.amount_due` (audit's live proof: 109.00
  invoice, 5000.00 allocation → 201, `amount_due = -4891`).
- **H-2 CONFIRMED** (`serializers/payment.py:86`): the API path demands
  `status == "APPROVED"` — a PARTIALLY_PAID invoice can never receive its
  second instalment (the service path already accepts PARTIALLY_PAID; the
  serializer is the blocker; SENT/OVERDUE are refused by both).
- **H-3 CONFIRMED** (no guard anywhere): posting/approving into a period
  whose F5 is already FILED is unrestricted; combined with C-2 the filed
  figures can then be silently overwritten.
- **H-4 CONFIRMED** (`document_service`): `SALES_CREDIT_NOTE` creation
  requires no `related_document`, no same-contact rule, no cap — an
  unlinked 5000.00 credit note against a 1000.00 invoice approves and
  drives F5 Box 1/6 negative.
- **H-5 CONFIRMED** (no `gst_registered` guard anywhere in the document
  path): a non-registered org can draft 9% GST lines (approval currently
  fails only incidentally on the missing control account).
- **H-6 CONFIRMED (live pg_class query)**: 10 tables without RLS —
  `core.organisation` (policies exist but RLS never ENABLED — the loop at
  `database_schema.sql:2372` skips it), `core.user_organisation`,
  `core.role`, `audit.event_log`, `gst.organisation_peppol_settings`,
  `gst.tax_code` (all carry `org_id`), plus the documented globals
  (`app_user`, `currency`, `account_type`, `account_sub_type` — correctly
  un-scoped).
- **H-7 CONFIRMED**: the suite, dev stack and e2e all run as the
  SUPERUSER; RLS is never exercised by any gate.
- **H-8 CONFIRMED (pip-audit/npm-audit, per the audit's tool output)**:
  backend `django 6.0.2` / `djangorestframework 3.16.1` / `lxml 6.0.2` /
  `weasyprint 68.1`; frontend `next 16.1.6` (critical advisory) / `zod`
  and transitives. CI treats the audits as advisory.
- **H-9 CONFIRMED** (`docker/Dockerfile:527`):
  `SECRET_KEY=django-secret-key-for-hf-space-$(date +%s)` — predictable;
  `service.py` skips the key-strength gate.
- **M-4 CONFIRMED** (`serializers.py:208`): `lines` is
  `ListField(child=DictField(), required=False)` — no line schema, no
  quantity/unit_price bounds; the view's `data["lines"]` KeyErrors on a
  missing field → 500.
- **M-5 CONFIRMED**: `ContactListCreateView` /
  `ContactDetailView.delete` / send use only `IsOrgMember` — the Viewer
  role can create/delete contacts and reach the send path.
- **M-10 CONFIRMED** (`tax_code_service.list_tax_codes`): the dedupe only
  runs when `effective_on` is supplied; without it system + org rows both
  return (the audit's 24-row duplicate list).
- **XXE (audit2 H-01) CONFIRMED** (`xml_validation_service.py:33,41,58`):
  `etree.parse()` / `etree.fromstring()` with default parser flags — no
  `resolve_entities=False`, `no_network`, `load_dtd=False`,
  `huge_tree=False`.
- **UEN (audit2 H-02 / audit1 M-1) CONFIRMED**
  (`contact_service._validate_uen`, `serializers/organisation.py:104`):
  four regexes including the invalid bare `^\d{10}$`; the org serializer's
  `startswith("M")` **rejects valid UEN-form GST numbers** and accepts
  garbage like `"XYZ"`.
- **F5 override control (audit2 H-05) CONFIRMED**: `file_return` accepts
  box6/box7/9–15 overrides with no reason/evidence requirement.
- **NRIC PayNow (audit2 H-04) CONFIRMED** (`bank_account` serializer):
  no masking anywhere; NRIC-type `paynow_id` round-trips in full.
- **M-6 (partial) CONFIRMED (live pg_proc query)**: `audit.log_change` is
  SECURITY DEFINER with **no pinned `search_path`**.
- **F-A (NEW, this session)**: `e2e/p11.spec.ts` `ensureDemoActivity`
  only force-computes an existing return — it never CREATES one, so a
  fresh-clone `npm run test:e2e:full` fails 2 specs (banking + F5 boxes)
  despite DEPLOYMENT.md §9's "self-bootstraps" claim. Fixed manually this
  session to reproduce the 40P baseline; the spec must create the return.
- **Audit2 H-03 REJECTED as stated** (see header): the document path is
  date-aware through `tax_code_id`; only the calculator's documented
  no-code fallback defaults to 9%. No code change; registered in §6.

---

## 2. Findings register (drives §3)

| ID | Sev | Source | Location | Finding |
|---|---|---|---|---|
| C-1 | **Critical** | audit1 | `organisation_service.py` | Org creation 500s under the documented runtime role `ledgersg_app` — seeding runs with no RLS context (the product cannot onboard a customer on the documented production path) |
| C-2 | **Critical** | audit1 | `return_service.generate_f5` | FILED/AMENDED F5 returns are silently mutable via `?force=true` (status regresses, boxes overwritten, `filed_at` kept) — the statutory record is not immutable |
| H-1 | High | audit1 | `payment_service.allocate` | Allocations may exceed the document balance (`amount_due` goes negative; invoice falsely PAID) |
| H-2 | High | audit1 | `serializers/payment.py` | Second instalment on a PARTIALLY_PAID invoice rejected ("must be APPROVED"); SENT/OVERDUE also refused |
| H-3 | High | audit1 | posting paths | No GST-lock on filed periods — invoices approve and journals post into a filed period |
| H-4 | High | audit1 | `document_service` | Credit notes require no original-invoice reference, no same-contact rule, no cap — negative F5 boxes reachable |
| H-5 | High | audit1 | `document_service` | GST charged by non-registered orgs / before `gst_reg_date` (only an incidental control-account guard) |
| H-6 | High | audit1 | `database_schema.sql` §12 | RLS incomplete: `core.organisation` (policies inert), `user_organisation`, `role`, `audit.event_log`, `gst.organisation_peppol_settings`, `gst.tax_code` unprotected |
| H-7 | High | audit1 | test infra | The whole gate runs as SUPERUSER — RLS/production-role behaviour never exercised |
| H-8 | High | audit1 | `pyproject.toml` / `package.json` | Known-vulnerable dependency set (Django, DRF, lxml, WeasyPrint, Next critical, zod); audits advisory-only |
| H-9 | High | audit1 | `docker/Dockerfile:527` | Predictable JWT signing key on the Docker path; `service.py` skips the key gate |
| H-04b | High | audit2 | banking serializers | NRIC PayNow identifiers unmasked (PDPA) |
| H-05b | High | audit2 | `return_service.file_return` | F5 box overrides (6/7, 9–15) accepted with no reason/evidence trail |
| M-1 | Medium | audit1 | `_validate_uen` + org serializer | UEN/GST-number validation is regex-only, mislabeled, includes a non-UEN pattern; valid UEN-form GST numbers rejected |
| M-4 | Medium | audit1 | `serializers.py:208` | Malformed document input → 500 (missing `lines` KeyError; no line-item schema/bounds) |
| M-5 | Medium | audit1 | invoicing views | Viewer role can create/delete contacts and reach the send path |
| M-6a | Medium | audit1 | `audit.log_change` | SECURITY DEFINER without pinned `search_path` |
| M-10 | Medium | audit1 | `list_tax_codes` | Duplicate tax-code rows (system + org copies) without `effective_on` |
| X-1 | High | audit2 | `xml_validation_service.py` | XXE / entity-expansion DoS — unhardened lxml parser on an attacker-adjacent input path |
| F-A | Medium | this session | `e2e/p11.spec.ts` | Fresh-DB e2e bootstrap gap: the F5 return is never created by `ensureDemoActivity` |
| M-7c | Low | audit1 | `database_schema.sql:1237` | Schema comment claims the Peppol API key is "Encrypted" — it is not (comment lie; encryption itself deferred) |

**Explicitly deferred (registered, carried forward — not silently dropped):**
audit1 M-2 (IRAS-conformant threshold monitor), M-3 (alert deadline
sourcing), M-6b (audit-coverage expansion to more tables), M-8
(trusted-proxy rate-limit key), M-9 (tax-document-grade PDF template),
M-7 full (Peppol key envelope encryption — comment honesty fixed as M-7c);
audit2 M-01 (boxes 9–15 sourcing), M-02 (Peppol credit-note send path),
M-03 (FX revaluation job / SGD-only lock), M-04 (XFF pinning — overlaps
M-8), M-07 (maker-checker), M-08 (restore drill); audit2 H-03 (REJECTED as
stated — documented calculator fallback only); L-*/I-* hygiene items
(docs archive, bottom-of-file import, console logging, cache TTL, admin
mount, AGPL note); everything carried forward from P13's deferred register
(B-3, B-4, B-8, B-9, B-12, B-15…B-19, M-2, L-2…L-10, ruff register,
D-24).

---

## 3. Task list (TDD; every production-code change ships with its failing test first)

| # | Finding(s) | Task | Tests (RED first) |
|---|---|---|---|
| 1 | C-2 | `generate_f5` refuses FILED/AMENDED **even with `force=true`** (typed 409 through the envelope; corrections go through `/amend/`); `review_return` likewise refuses FILED | `tests/invariants/test_filed_return_immutability.py` — file → force-recompute → 409 + row unchanged (box values + status + filed_at); review-after-file → 409 |
| 2 | H-1 | `allocate()` + the receive/make serializers reject `allocated_amount > document.amount_due` (row locked via `select_for_update`; VOID/DRAFT unallocatable) | Over-allocation → 400 with the outstanding figure in the message; `amount_due` never negative; allocation to VOID refused |
| 3 | H-2 | Allocation-eligible statuses aligned in BOTH layers: serializer + service accept `APPROVED, SENT, PARTIALLY_PAID, OVERDUE` | The full instalment cycle: partial payment → PARTIALLY_PAID → second allocation → PAID (previously 400 mid-cycle) |
| 4 | H-3 | Derived GST-lock: a shared guard `assert_not_gst_locked(org_id, the_date)` (a FILED/AMENDED return covering the date → typed 409) enforced at document approve, void, journal create/post, payment void | File a return covering a period → approve/void/manual-journal/payment-void dated inside it → 409s; posting after the period end stays green |
| 5 | H-4 | Credit notes: `related_document` REQUIRED for `*_CREDIT_NOTE` (must be the original SALES/PURCHASE invoice, same contact, not VOID); cumulative credited (incl. GST) capped at the original `total_incl` (typed 400, override via reason deferred to §6) | Unlinked CN → 400; cross-contact CN → 400; over-cap CN → 400; valid linked CN → 201 (existing CN flows stay green) |
| 6 | H-5 | GST-registration guard on tax lines: any line whose tax code has `rate > 0` (or an output-tax box) is rejected unless `org.gst_registered` AND `issue_date ∈ [gst_reg_date, gst_dereg_date]` (clean 400 naming the rule) | Non-registered org + SR 9% line → 400; pre-registration-date line → 400; registered org unchanged |
| 7 | H-6 + M-6a | Schema §17 (idempotent DDL, version v1.2.0): ENABLE RLS + policies for `core.organisation` (bootstrap-aware: NULL-context read/insert allowed — login/org-list/creation routes; org-scoped rows restricted), `core.user_organisation` (NULL-context read — the middleware membership check precedes context), `core.role`, `gst.organisation_peppol_settings` (strict org scope), `gst.tax_code` (`org_id IS NULL OR org_id = current`), `audit.event_log` (strict org scope; INSERT stays via the definer trigger); `ALTER FUNCTION audit.log_change(...) SET search_path = pg_catalog, audit, public`; models stay `managed=False`; conformance gate extended | New `tests/invariants/test_rls_conformance.py`: every table carrying `org_id` (minus the documented globals) has `relrowsecurity`; `pg_proc.proconfig` pins the audit function's search_path; both DBs patched in place (§17 procedure) |
| 8 | C-1 + H-7 | `create_organisation` sets the RLS context right after the org INSERT (`SELECT set_config('app.current_org_id', %s, true)` — transaction-local, same connection) so every seed (CoA SQL fn, tax codes, fiscal year, owner role) passes the WITH CHECK under ANY role; NEW runtime-role smoke script `scripts/rls_smoke.py` (repo `scripts/`, gitignored? no — committed under `apps/backend/scripts/`) boots nothing itself: run against a runserver started with `DB_USER=ledgersg_app` — register → create org → contact → invoice → approve → payment → F5, asserting 2xx at every step | Unit: the service issues the set_config before the seed call (spy on the cursor); the live gate step (§4 item 12) proves the whole path as `ledgersg_app` (the C-1 repro becomes the regression proof) |
| 9 | M-4 | Document-input hardening: a real nested line schema (`account_id` UUID, `description` ≤ 500, `quantity` > 0 bounded ≤ 10^6, `unit_price` ≥ 0 bounded < 10^13, optional `tax_code_id` UUID, `discount_pct` ∈ [0,100]); `lines` required (min_length=1) for document create; service re-validates defensively | Missing `lines` → 400 (was KeyError 500); negative unit_price → 400; 10^15 unit_price → 400; a valid document unchanged (e2e form payload shape stays compatible) |
| 10 | M-1 (+audit2 H-02) | Honest validators: `validate_uen` (3 real ACRA formats — business `8N+letter`, local company `9N+letter`, other entities `T/S+YY+2letters+4N+letter`; the bare `^\d{10}$` branch REMOVED with a documented reason); `validate_gst_reg_number` accepts M-form (`M`+8N+check letter) **and** UEN-form; org + register + contact serializers wired | Table-driven validator tests (valid/invalid per format); the previously-rejected valid UEN-form GST number now passes; garbage rejected |
| 11 | X-1 | One shared hardened lxml parser (resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False) used for schemas AND candidate documents in `xml_validation_service` | XXE payload (`file:///etc/passwd` entity) rejected without file access; billion-laughs payload rejected fast; valid UBL still validates |
| 12 | H-05b | `file_return` requires `override_reason` (≥ 10 chars) whenever `boxes` overrides are present; the reason + the computed-vs-filed delta are persisted into `notes` (auditable trail; schema unchanged) | File with boxes + no reason → 400; with reason → 200 and the notes carry the reason + deltas |
| 13 | H-04b | NRIC PayNow masking: bank-account serializers mask `paynow_id` for `paynow_type=NRIC` on READ (`S*****67A` — first char + last 3); write-path validation rejects values containing `*` (a masked echo cannot be persisted); PDPA note in the serializer docstring | Round-trip test: create with real NRIC → read masked → PATCH with the masked echo → 400; PATCH with a fresh NRIC → 200; mobile/VR-type IDs unmasked |
| 14 | M-5 | Viewer gates: contact create/delete + document send require `can_create_invoices` (the same verb the document-create path already uses) | Table-driven role×endpoint test: Viewer 403 on contact POST/DELETE + send; Manager/Owner 2xx |
| 15 | M-10 | `list_tax_codes` dedupe without `effective_on`: per `(code, effective_from, effective_to)` the org row shadows the system row (order already prefers org + newest) | The duplicate 24-row list → one row per code-and-band; `?effective_on=` resolution unchanged |
| 16 | F-A | `ensureDemoActivity` creates the F5 return (`POST /gst/returns/` MONTHLY current month) when the list is empty, then force-computes | Fresh-DB reasoning: the spec's own bootstrap creates the return (verified by wiping + running the suite subset in the gate) |
| 17 | H-8 | Dependency upgrades through the package managers (never hand-edited manifests): backend `pip install -U "django~=6.0.8" "djangorestframework>=3.18.2" "lxml>=6.1.0" "weasyprint>=70.0"`; frontend `npm install next@^16.4 zod@^4.6` (+ lockfile); full gate re-run; if a specific upgrade breaks incompatibly, revert THAT package and register it with evidence | The full gate (§4) on the upgraded tree; `pip-audit`/`npm audit --omit=dev` deltas recorded in the report |
| 18 | H-9 | Docker path: the entrypoint generates a strong per-boot key (`python -c "import secrets;..."`) when `SECRET_KEY` is unset; `service.py` gains the key-strength gate + `ALLOWED_HOSTS` from env | Settings-gate test for `service.py` (weak key → refuse); Dockerfile lint-level check (no fixed-prefix key) |
| 19 | M-7c | Schema comment honesty: `organisation_peppol_settings.access_point_api_key` documented as plaintext-at-rest with the encryption deferred to P15 (comment fix only — no migration churn) | Schema source check (the comment text) |
| 20 | — | `.env.example` truth pass: re-verify root + backend + web templates against every env read (grep cross-check); include in the commit per the sprint instructions | grep-level cross-check vs `os.environ`/`os.getenv`/`process.env` reads |
| 21 | — | Screenshots of the remediated surfaces (mobile nav open/closed, desktop, banking, reports/F5) → `docs/screenshots/80-87_*_session29.png`, pixel+DOM verified per convention | The capture driver's DOM assertions |
| 22 | D-batch | Docs truth pass: DEPLOYMENT.md (the C-1/H-7 runtime-role workflow §12.3 + §7 counts + upgraded versions + the rls_smoke gate step), `API_CLI_Usage_Guide.md` (the new 409/400/masking contracts + versions), README/CLAUDE/PAD/AGENTS/ledgersg_SKILL (P14 milestone + counts + new lessons) | Every claim checked against executed gate output |

## 4. Verification gate (all must be green before push)

1. `pytest --reuse-db --no-migrations -q` → 750 + new tests, 0 failed, 5 skipped
2. `pytest tests/invariants -q` and `pytest tests/security -q` → green (incl. the new RLS-conformance + filed-immutability + GST-lock gates)
3. `manage.py check` (testing settings) → 0 errors (the documented W001 only)
4. Production boot gate → still boots behind its gates
5. `npx tsc --noEmit` → 0; `npx vitest run` → 530 + new tests; `npm run test:coverage` green at both ratchets
6. `npx eslint src` → 9 findings (the documented deferred register; no new)
7. `npm run build:server` → green
8. `npm run test:e2e` → 11P + 29 gated
9. `npm run test:e2e:full` (live stack, demo trio) → 40P + the F-A hardened bootstrap
10. `manage.py shell`-level spot proofs: GST sub-cent (9.00) still green
11. The C-1 live repro inverted: `DB_USER=ledgersg_app` runserver → `POST /organisations/` → **201** (the `scripts/rls_smoke.py` walk: register → org → contact → invoice → approve → payment → F5)
12. RLS live assertions as `ledgersg_app`: cross-org SELECT blocked, own-org rows readable, `audit.log_change` search_path pinned
13. Mobile-nav re-probe (17/17) on the remediated tree
14. Screenshots present + DOM-verified
15. `git ls-files` hygiene gate (no `.env`, no keys, no `*.pyc`)

## 5. Commit plan

Conventional commits on `main` only, one per logical task: the
statutory-immutability fix (C-2), the allocation pair (H-1+H-2), the
GST-lock (H-3), the credit-note contract (H-4), the registration guard
(H-5), the schema §17 + RLS completion + search_path pin (H-6+M-6a), the
org-creation context + runtime-role smoke (C-1+H-7), input hardening
(M-4), the validators (M-1), the XXE hardening (X-1), the F5 override
control (H-05b), NRIC masking (H-04b), the viewer gates (M-5), the
tax-code dedupe (M-10), the e2e bootstrap fix (F-A), the dependency
upgrades (H-8), the Docker key (H-9), the .env.example pass, the
screenshots, the docs truth pass, the report/session/worklog. Push via
`docs/ssh_git_wrapper_v3.py --remote git@github.com:nordeim/ledgersg.git`
with remote-ref verification.

## 6. Deferred register

Everything in §2's deferred paragraph, unchanged and explicit. Design
decisions taken this sprint (recorded for the next auditor):
- **H-3** uses the *derived* lock (runtime check against FILED/AMENDED
  returns covering the date) rather than a schema change — no DDL, no
  enum churn; a DB-trigger enforcement layer is the registered P15 item.
- **H-6** organisation/user_organisation policies allow NULL-context
  reads (the login/org-list routes and the middleware's pre-context
  membership check require them); the app-layer membership checks remain
  the gate on those routes — the tradeoff is documented in the schema.
- **M-1** implements FORMAT validation only — no invented checksums (the
  ACRA check-letter algorithm is not an officially published spec;
  guessing one would reject valid numbers). Checksum verification is
  registered as a P15 decision with the official algorithm as input.
- **H-05b** persists the override reason + deltas in `notes` (schema
  unchanged); a dedicated evidence/attachment model is the P15 design.
