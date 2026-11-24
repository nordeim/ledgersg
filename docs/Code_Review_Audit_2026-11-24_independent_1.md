# LedgerSG — Independent Code Review, Audit & Regulatory-Compliance Validation

| | |
|---|---|
| **Repository** | `github.com/nordeim/ledgersg` — branch `main`, commit `e514fb31` ("update session log") |
| **Audit date** | 2026-11-24 |
| **Mode** | C — Audit / Review (findings only; **no application code was modified**) |
| **Method** | Reproduce the documented baseline → run static gates → execute the real stack and probe it → review high-risk code → cross-check IRAS requirements against a primary source |
| **Skills applied** | `code-review-and-audit` (tiered pipeline, severity/finding format, native-CLI fallback), `verification-and-review-protocol` (evidence-before-claims), `code-review-checklist` (12-category scan) |
| **Confidence labels** | **Verified** = executed and observed · **Reasoned** = inferred from code, not executed · **Assumed** = depends on a stated assumption · **Unverifiable** = environment could not check |

---

## 1. Executive Summary

LedgerSG is a well-structured SQL-first Django/Next.js platform with a genuinely strong engineering culture: the documented test baseline **reproduces**, tenant isolation holds at the API layer, journal balancing and concurrency control work, and the frontend gates are clean. The remediation history in the repo is real, not marketing.

The audit nevertheless found that **the headline claim — "Production Ready ✅ / Security 100% / IRAS 2026 Compliant" — is not supported by the evidence**. The two most important reasons:

1. **The product cannot onboard a customer when run the way the deployment guide says to run it.** The guide (§12.3) instructs operators to switch to the non-superuser role `ledgersg_app`. Under that role, `POST /organisations/` returns **500**, because the service seeds the chart of accounts without setting the RLS tenant context. Every test, the dev stack and the e2e suite run as a **SUPERUSER**, which bypasses RLS entirely, so none of them could see it.
2. **Statutory GST records are not protected.** A *FILED* F5 return can be silently recomputed (status regresses `FILED → COMPUTED`, boxes change), and invoices/journals can be posted into a period whose F5 is already filed.

| Severity | Count | IDs |
|---|---:|---|
| 🔴 **Critical** | **2** | C-1, C-2 |
| 🟠 **High** | **9** | H-1 … H-9 |
| 🟡 **Medium** | **10** | M-1 … M-10 |
| 🟢 **Low** | **4** | L-1 … L-4 |
| ⚪ **Informational** | **4** | I-1 … I-4 |

**Release recommendation: do not release to production** until C-1, C-2 and H-1…H-5 are fixed and a CI job exercises the application as the real runtime DB role (H-7).

---

## 2. Verification Ledger (what was actually run)

| # | Check | How | Result | Confidence |
|---|---|---|---|---|
| 1 | Backend baseline "750 passed / 0 failed / 5 skipped" | `pytest --reuse-db --no-migrations` on PG 15.18 + Redis 7.2.4, Python 3.12.16, schema loaded as superuser | **747 passed, 5 skipped, 3 failed** — the 3 failures are the PDF tests, caused by my WeasyPrint stub (no Pango in sandbox). 747 + 3 = 750 → baseline reproduced | Verified |
| 2 | Same suite as the **production role** `ledgersg_app` | same, `DB_USER=ledgersg_app` | **349 passed, 28 failed, 391 errors.** Dominant causes: fixtures inserting tenant rows with no RLS context (`document_sequence` ×223, `account`, `contact`) and flush privileges. Shows the suite validates only the superuser path (see H-7) | Verified |
| 3 | Schema load | `psql -f database_schema.sql` | 30 domain tables, 47 `NUMERIC(19,4)` columns — matches docs. Only error: the schema's own PG≥16 guard (sandbox is PG15) | Verified |
| 4 | RLS coverage | `pg_class.relrowsecurity` | 19 of 41 tables in the app schemas have RLS; `core.organisation` has policies but RLS **not enabled** (H-6) | Verified |
| 5 | Live API probes (5 scripts, 2 tenants + Viewer user) | `runserver` + `requests` | Findings C-1, C-2, H-1…H-5, M-4, M-5, M-10 | Verified |
| 6 | Route/permission introspection | Django URL resolver | 84 API routes; only health/root/CSP-report/register/login/refresh are `AllowAny`; 72 org-scoped routes use `IsAuthenticated` | Verified |
| 7 | Backend lint | `ruff check .` | 1,185 findings (812 auto-fixable); 2 `F821`, 1 `F402` real | Verified |
| 8 | Backend dependency audit | `pip-audit -r <frozen venv>` | Django, DRF, lxml, WeasyPrint, pytest have advisories (H-8) | Verified |
| 9 | Frontend typecheck | `tsc --noEmit` | 0 errors | Verified |
| 10 | Frontend unit tests | `vitest run` | **530/530 passed** (60 files) | Verified |
| 11 | Frontend lint | `eslint .` | 10 problems (5 errors, 5 warnings) vs documented "9" | Verified |
| 12 | Frontend dependency audit | `npm audit --omit=dev` | 8 advisories (1 critical, 5 high, 2 moderate) | Verified |
| 13 | Skill scripts | `skills/code-review-and-audit/scripts/` | Only `audit_runner.py` and `checklist_runner.py` exist; the other phase scripts are absent. Per the skill's own "never claim a missing script ran" rule I used native CLI equivalents. `checklist_runner.py` was **not** executed (its invocation failed on my first attempt and I substituted the manual 12-category review) | — |

### Environment caveats (these bound what the evidence proves)
- PostgreSQL **15.18**, not 16+ (the schema's version guard fired but is non-fatal). Behaviour differences between 15 and 16 are not expected to affect any finding but are **unverified**.
- **WeasyPrint was stubbed**; PDF output (tax-invoice particulars, credit-note layout) was reviewed from the template only.
- **Not run**: Playwright e2e, Docker builds, Celery workers, live Storecove/InvoiceNow/IRAS endpoints, load tests, browser accessibility checks.

---

## 3. Findings

### 🔴 CRITICAL

#### C-1 — Organisation creation returns HTTP 500 under the documented production DB role
- **Location:** `apps/backend/apps/core/services/organisation_service.py:28-80` (`create_organisation` → `_seed_chart_of_accounts`); policies in `database_schema.sql:2362-2430`
- **Description:** The service inserts the organisation and immediately calls `core.seed_default_chart_of_accounts(...)`, which `INSERT`s into `coa.account` with `org_id = <new org>`. RLS `WITH CHECK (org_id = core.current_org_id())` rejects the row because `app.current_org_id` was never set for this transaction (the tenant middleware has no org in the URL for this route).
- **Evidence (Verified):**
  ```
  POST /api/v1/organisations/  (server running as ledgersg_app)  -> 500
  psycopg.errors.InsufficientPrivilege: new row violates row-level security policy for table "account"
  CONTEXT: SQL statement "INSERT INTO coa.account (org_id, code, name, ...
  ```
  The same request succeeds as the superuser. Test-suite fixtures hit the identical error (223× `document_sequence`, 9× `account`, 7× `contact`).
- **Impact:** A self-serve user can register but can **never create an organisation**, so the product is unusable after following `docs/DEPLOYMENT.md §12.3` (switch to `ledgersg_app`). Staying on the superuser to work around it disables RLS — the platform's core multi-tenancy guarantee.
- **Recommended fix:** In `create_organisation`, directly after the organisation insert, run `SELECT set_config('app.current_org_id', %s, true)` (transaction-local) before seeding CoA, fiscal year, sequences, tax codes. Add a CI job that provisions `ledgersg_app` and runs a smoke subset (register → create org → contact → invoice → approve → payment → F5) as that role.
- **Confidence:** Verified

#### C-2 — A FILED GST F5 return is silently mutable (status regresses, boxes overwritten)
- **Location:** `apps/backend/apps/gst/views.py` (`GSTReturnDetailView.post`, `force=true` path ≈ line 367) and the F5 service
- **Description:** `POST /gst/returns/{id}/?force=true` recomputes a return without checking its status. It accepted a `FILED` return, overwrote the boxes from live ledger data and set `status` back to `COMPUTED`, while `filed_at` stayed populated.
- **Evidence (Verified):**
  ```
  file    -> 200 "GST return filed successfully"          (Box1 = -4000.00, Box6 = -360.00)
  <post a backdated invoice into the same period (see H-3)>
  compute (force=true) on the FILED return -> 200
  GET return -> status "COMPUTED", box1 -3900.0000, box6 -351.0000, filed_at still set
  ```
- **Impact:** The statutory record of what was submitted to IRAS is lost and cannot be reconstructed; an auditor sees a "COMPUTED" return with a filing timestamp. Violates the "immutable audit trail / 5-year retention" claim for filed returns.
- **Recommended fix:** (1) Reject compute/recompute when `status IN ('FILED','AMENDED')` with 409; corrections must go through `/amend/` which creates a new linked version. (2) Add a DB trigger that blocks `UPDATE` of box columns and `status` regression once `FILED`. (3) Regression test: file → recompute → expect 409 and unchanged row.
- **Confidence:** Verified

---

### 🟠 HIGH

#### H-1 — Payment allocations may exceed the invoice balance (AR corruption)
- **Location:** `apps/banking/serializers/payment.py:68-90, 163-189` and the allocation service
- **Description:** Validation checks `sum(allocations) <= payment.amount` and "document is APPROVED", but never `allocated_amount <= document.amount_due`.
- **Evidence (Verified):** invoice total 109.00; `POST /banking/payments/receive/` with `amount=5000, allocation=5000` → **201**; document becomes `PAID`, `amount_paid=5000.0000`, `amount_due=-4891.0000`.
- **Impact:** Negative receivables, a falsely settled invoice, and (not examined — **Reasoned**) an AR/bank posting that does not match the invoice. Breaks dashboard AR, aged-AR and reconciliation.
- **Fix:** In the service, lock the document row (`select_for_update`) and reject allocations > `amount_due` (400); disallow allocation to `VOID`/`DRAFT`; add a DB `CHECK (amount_paid <= total_amount)`.
- **Confidence:** Verified (GL effect Reasoned)

#### H-2 — Cannot allocate a second payment to a `PARTIALLY_PAID` invoice (and, by code, `SENT`/`OVERDUE`)
- **Location:** `apps/banking/serializers/payment.py:79-88` (`validate_document_id`: `if document.status != "APPROVED"`)
- **Evidence (Verified):** after a 400.00 partial payment the invoice is `PARTIALLY_PAID` (due 690.00); receiving 690.00 allocated to it → **400** `"Document must be APPROVED before allocation."`
- **Impact:** Instalment payments — a normal SMB workflow — cannot be completed through the API/UI; the invoice can never reach `PAID`. For `SENT`/`OVERDUE` documents the same predicate applies (**Reasoned**; I could not reach `SENT` via the status endpoint — `APPROVED→SENT` is not a permitted transition).
- **Fix:** Accept `status IN ('APPROVED','SENT','PARTIALLY_PAID','OVERDUE')`; test the full instalment cycle.
- **Confidence:** Verified (SENT/OVERDUE Reasoned)

#### H-3 — No lock on periods whose GST return has been filed
- **Evidence (Verified):** after filing the Feb-2026 F5, a new invoice dated 2026-02-25 was created (201) **and approved (200)**, and a manual journal dated 2026-02-10 was posted (201). The only posting guard found is "no open fiscal period".
- **Impact:** Ledger and filed return diverge silently; combined with C-2, the filed number can then be overwritten. IRAS expects post-filing corrections via amendment/voluntary disclosure, not silent back-posting.
- **Fix:** On `file`, set the covered `core.fiscal_period` to a GST-locked state (or add a `gst_locked_through` date on the org) and reject posting/approval/void/payment-void dated inside it, enforced by a DB trigger on `journal.entry` as well as in services.
- **Confidence:** Verified

#### H-4 — Credit notes need not reference the original invoice; oversized credit notes are approved
- **Evidence (Verified):** a 1,000.00 invoice and a **5,000.00** `SALES_CREDIT_NOTE` (no link) → created 201, approved 200, `related_document: null`. F5 then reports negative Box 1 / Box 6.
- **Regulatory basis (IRAS, primary source):** *"A credit note must show the number and date of the original tax invoice"* (iras.gov.sg → *Invoicing customers → credit note*). The schema has `related_document`, but nothing requires it.
- **Impact:** Non-conformant credit notes; output tax can be reduced without a supporting invoice; negative F5 boxes are not a valid F5 entry.
- **Fix:** Require `related_document` for `*_CREDIT_NOTE`; require same contact; cap cumulative credited ≤ original total (incl. GST) unless a documented reason code is supplied; include original number/date on the PDF and PINT-SG payload.
- **Confidence:** Verified

#### H-5 — GST can be charged by a non-registered organisation / before the registration date
- **Evidence (Verified):**
  - Non-GST org: draft invoice with an `SR 9%` line → **201**, `total_incl = 109.0000`. Approval was refused only because the GST *control account* does not exist (`"No GST Output Tax control account found…"`) — an incidental guard with a misleading message, not a compliance rule.
  - GST-registered org with `gst_reg_date = 2026-01-01`: invoice dated **2025-12-15** with 9% GST → created 201 (approval refused only because no fiscal period exists before Jan-2026).
- **Impact:** A non-registered business must not charge GST or issue a tax invoice. Any later change that seeds control accounts, or a fiscal year that starts earlier, silently removes the only barrier.
- **Fix:** In `DocumentService.add_line/create_document`, reject any tax code with rate > 0 / output-tax box unless `org.gst_registered` **and** `issue_date >= org.gst_reg_date` (and `<= gst_dereg_date` if present); return a clear 400.
- **Confidence:** Verified

#### H-6 — Row-Level-Security coverage is materially incomplete (docs claim every table is covered)
- **Evidence (Verified, `pg_class`):** RLS is enabled on 19 tables. **Not** protected despite carrying tenant data:
  - `core.organisation` — four policies exist but `relrowsecurity = f`, so they are **inert** (the loop at `database_schema.sql:2392` skips it; the "special case" block only adds policies). The app role can read every tenant's name, UEN and GST number.
  - `audit.event_log` (has `org_id`; holds before/after row images of every audited table), `gst.organisation_peppol_settings` (holds the AP API key — see M-7), `core.user_organisation`, `gst.tax_code` (org-specific codes), `core.role`.
- **Docs claim:** PAD §Database: *"Every table (30 total) has RLS enabled."* — false.
- **Impact:** Defence-in-depth failure: any missing `org_id` filter, SQL injection or future ORM mistake leaks across tenants; the audit log of one tenant is readable under another's context.
- **Fix:** `ALTER TABLE core.organisation ENABLE ROW LEVEL SECURITY` (keep the permissive INSERT policy); add org-scoped policies for the tables above (for `gst.tax_code`: `org_id IS NULL OR org_id = core.current_org_id()`); add a conformance test that fails if any table with an `org_id` column lacks `relrowsecurity`.
- **Confidence:** Verified

#### H-7 — The entire test and e2e stack runs as a SUPERUSER, so RLS is never exercised
- **Evidence (Verified):** `ledgersg` is `rolsuper = t` (DEPLOYMENT §3); superusers bypass RLS even with `FORCE`. Re-running the suite as `ledgersg_app` yields 349 pass / 28 fail / 391 error (§2 row 2). C-1 and H-6 are direct consequences.
- **Impact:** "750 tests green" proves business logic, not tenant isolation or production-role behaviour. The "RLS enforced" claim is untested end-to-end.
- **Fix:** Run CI against `ledgersg_app` (DDL/schema load as owner, runtime as app). Fix fixtures to set `app.current_org_id` (a `tenant_context(org_id)` helper) rather than weakening the role. Keep a small superuser-only tier for schema-conformance tests.
- **Confidence:** Verified

#### H-8 — Known-vulnerable dependencies (backend and frontend); CI does not gate on them
- **Evidence (Verified, tool output; advisory text not independently re-verified):**
  - Backend: `django 6.0.2` (fixed 6.0.8; 2 advisories), `djangorestframework 3.16.1` (fixed 3.17.2/3.18.2; 5), `lxml 6.0.2` (6.1.0), `weasyprint 68.1` (70.0; 4), `pytest 9.0.2` (dev; 9.0.3).
  - Frontend (prod): `next 16.1.6` (**critical**, fix 16.4.6), `zod` (<4.6.6, high — it is used to validate request payloads), `nanoid`, `postcss`, `sharp`, `source-map-js` (high), `uuid`, `baseline-browser-mapping` (moderate).
  - Context: the Next.js *rewrites request-smuggling* advisory is **not exploitable in the shipped config** — `rewrites()` returns `[]` outside `NODE_ENV=development` (`next.config.ts:148-166`). The image-cache and transitive advisories still apply.
  - CI: `npm audit … || true`; `bandit … || true`; there is no `pip-audit` step.
- **Impact:** Unpatched framework CVEs on an internet-facing financial app.
- **Fix:** Upgrade Django ≥ 6.0.8, DRF ≥ 3.18.2, lxml ≥ 6.1.0, Next ≥ 16.4.6, zod ≥ 4.6.6; make `npm audit --omit=dev --audit-level=high` and `pip-audit` blocking; keep Dependabot/Renovate on.
- **Confidence:** Verified (applicability of each advisory Reasoned)

#### H-9 — Single-container Docker path generates a predictable JWT signing key
- **Location:** `docker/Dockerfile:523-527` (`SECRET_KEY=django-secret-key-for-hf-space-$(date +%s)`), `config/settings/service.py` (no key gate, `ALLOWED_HOSTS = ["*"]`); README "Docker Deployment" points at this Dockerfile.
- **Description:** The key is a fixed prefix plus the container start time in epoch seconds, and the `service` settings module does not enforce the H-06 key-strength gate that `production.py` has. JWTs are HS256 signed with this key.
- **Impact:** Anyone who can estimate the start time can brute-force the key (a few million candidates) and forge access tokens for any user → full tenant takeover.
- **Fix:** Generate with `python -c "import secrets;print(secrets.token_urlsafe(64))"` at first boot (persisted outside the image) or require it via env; apply the same key gate in `service.py`; restrict `ALLOWED_HOSTS`.
- **Confidence:** Reasoned (image not built or run)

---

### 🟡 MEDIUM

| ID | Finding | Evidence / location | Fix | Confidence |
|---|---|---|---|---|
| **M-1** | **Identity/registration inputs are not validated.** Org creation accepts GST no. `"XYZ"`, UEN `"garbage!!"` and `base_currency "ZZZ"` (all **201**). The only GST check is `startswith("M")` (`serializers/organisation.py:104`), applied to the *register* serializer only — and it **rejects valid numbers**: IRAS states a GST number may be UEN-form (e.g. `123456789A`) or M-form (`M21234567K`). | Probe 3; `organisation.py:104`; IRAS *Invoicing customers* | Validate UEN against the ACRA-published formats (including the check letter) and GST numbers against the IRAS-published forms (UEN-form and M-form — the exact patterns must be taken from IRAS/ACRA specifications, not guessed), ideally confirming against the IRAS GST register; validate `base_currency` against `core.currency` on create, as the PATCH path already does. | Verified |
| **M-2** | **GST registration-threshold monitoring is not IRAS-conformant.** `query_gst_threshold_status` sums `total_excl` of *all* invoices/debit notes over a rolling 365 days — includes exempt/out-of-scope lines, ignores credit notes, has no prospective (next-12-months) test, and `gst.threshold_snapshot` is never written. IRAS' retrospective test is by calendar year; registration is due within 30 days of breach. README marks this "✅ Complete". | `reporting/services/dashboard_service.py:347-376` | Compute taxable turnover (standard + zero-rated supplies, net of credit notes) per the IRAS tests; persist snapshots; alert at 80/90/100% with the 30-day deadline. | Reasoned |
| **M-3** | **Compliance alert uses a different, wrong filing deadline.** Hard-codes day **30** of the month after a *calendar* quarter and ignores the org's `gst_filing_frequency`/stagger; the F5 module correctly returns period-end + 1 month (e.g. 2026-03-31). Jul/Oct/Jan quarters are off by a day, monthly/staggered filers are wrong. | `dashboard_service.py:~415-430` vs F5 `filing_due_date` | Source the deadline from the next open `gst.return` row. | Reasoned |
| **M-4** | **Malformed input produces HTTP 500 instead of 400.** (a) `POST /documents/` without `lines` → `KeyError` (`data["lines"]` on an optional field, `invoicing/views.py:~197`); (b) negative `unit_price` → 500; (c) `unit_price = 999999999999999` → 500. | Probe 3 | Make `lines` required or `.get("lines", [])`; validate `unit_price ≥ 0`, `quantity > 0`, and max magnitude (< 10^15) with 400s. | Verified |
| **M-5** | **Read-only `Viewer` role can perform some writes.** Viewer `POST /invoicing/contacts/` → **201**; `DELETE` a contact and `POST …/send/` reach the service layer (400 only on business validation). Role flags `can_manage_users`, `can_manage_coa`, `can_export_data` are never referenced by name outside role serializers, so the permission matrix is not reflected in code. (CoA, tax-code, journal, Peppol-settings, banking and document writes **were** correctly 403.) | Probe 2; `grep` | Gate contacts/send behind `can_create_invoices`; gate send/PDF/export behind `can_export_data`; add a table-driven test of role × endpoint. | Verified |
| **M-6** | **Audit-trail coverage is partial and the writer is weakly hardened.** `audit.log_change` is attached to only 8 tables (organisation, document, document_line, journal entry/line, gst_return, payment, contact). Not audited: payment_allocation, bank_account/transaction, **coa.account**, **gst.tax_code**, **user_organisation (role changes)**, fiscal_period open/close, org settings, Peppol settings. The `SECURITY DEFINER` function has **no pinned `search_path`** (`pg_proc.proconfig` empty) — a known privilege-escalation pattern. `audit.event_log` has no RLS and no trigger blocking `UPDATE/DELETE` by the table owner. | `database_schema.sql:2142-2281`; `pg_proc` query | `SET search_path = pg_catalog, audit, public` on the function; add triggers for the listed tables; add a `BEFORE UPDATE OR DELETE` guard trigger on `audit.event_log`. | Verified |
| **M-7** | **Peppol/Storecove API key stored in plaintext** although the schema comment says `-- Encrypted` and model help-text says "encrypted at app level". No encryption code exists in the repo. The table is also outside RLS (H-6). | `database_schema.sql:1237`; `peppol/models.py:179`; grep for `encrypt\|fernet` | Envelope-encrypt (e.g. `cryptography.Fernet`, key from env/KMS) or store a secret reference; fix the comments. | Verified |
| **M-8** | **Rate-limit key is `REMOTE_ADDR`.** `@ratelimit(key="ip")` with no `RATELIMIT_IP_META_KEY`/trusted-proxy handling, while the documented topology is gunicorn on `127.0.0.1` behind nginx. All clients then share the proxy's address: 10 logins/min **for the whole user base** (self-inflicted lockout), or — if someone "fixes" it by trusting raw `X-Forwarded-For` — trivial bypass. | `apps/core/views/auth.py:30,112,113,155`; DEPLOYMENT §12.2 | Resolve the client IP from a trusted proxy chain (`RATELIMIT_IP_META_KEY` callable that takes the right-most untrusted hop) and test it behind nginx. | Reasoned |
| **M-9** | **Invoice/credit-note PDF is not tax-document-grade (template review only).** Heading prints the raw enum (`SALES_CREDIT_NOTE`) — no "Credit Note" title; no reference to the original invoice; per-line GST **rate** is not shown (only the tax-code letters); `document.bcrs_deposit_total` does not exist on the model or schema, so the BCRS block can never render (Django swallows the missing variable); no SGD conversion block (documents carry no currency at all, so foreign-currency invoicing is unsupported). | `invoicing/templates/invoicing/invoice_pdf.html:99-176`; model/schema grep | Add title map, original-invoice reference, rate column, remove/define BCRS total; confirm with a rendered PDF in an environment with Pango. | Reasoned |
| **M-10** | **`GET /gst/tax-codes/` returns duplicate codes** — 24 rows including two `SR`/`ZR`/`ES`/`OS`/`NA`/`TX`/`BL` rows effective 2024-01-01 (system rows plus per-org copies). UI dropdowns show duplicates; correctness depends on the shadowing rules in `get_tax_code_by_code`. | Probe 2 output | Return org rows where they shadow system rows, or flag `source`. Add a uniqueness test per (org, code, effective_from). | Verified |

### 🟢 LOW

- **L-1 Lint/dead code.** `ruff`: 1,185 findings (364 `W293`, 81 unused imports, 56 `B904`…). Real items: `tests/conftest.py:301,320` use undefined `Contact` (latent `NameError`); `invoicing/views.py:452` shadows the imported `status` module with a loop variable (a later `status.HTTP_*` in that scope would break); bare `except…pass` in `common/middleware/tenant_context.py:214` and `common/exceptions.py:212`. `S608` at `gst/services/calculation_service.py:257` is a **false positive** (only `%s` placeholders are interpolated). *Verified.*
- **L-2 Doc-vs-reality lint drift.** ESLint reports 10 problems (5 errors), docs say 9. *Verified.*
- **L-3 Exposure hygiene.** `/admin/` is mounted at the default path; `development`/`service` settings use `ALLOWED_HOSTS` wildcard; CI treats `bandit`/`npm audit` as advisory. *Verified/Reasoned.*
- **L-4 Membership cache TTL 300 s.** Removing a user from an org leaves access for up to 5 minutes (plus the 15-min access-token life). `tenant_context.py:232-247`. *Reasoned.*

### ⚪ INFORMATIONAL

- **I-1 Documentation drift.** PAD "647 passed / 398 frontend tests" vs README 750/530; PAD "every table has RLS" (see H-6); README clone URL `github.com/ledgersg/ledgersg` vs actual `nordeim/ledgersg`; "Security 100%", "WCAG AAA" and "IRAS 2026 Compliant" badges are unsupported by this audit; PAD lists 30 tables while the live DB has 41 across the app schemas (Django/celery-beat tables included); several root-level report files duplicate each other (≈90 files) and obscure the canonical docs.
- **I-2 Negative F5 boxes** are reachable (follow-on of H-4); the IRAS form does not accept negative amounts.
- **I-3 Document numbers are allocated at DRAFT creation** (`INV-00001` on create). Acceptable because creation is atomic and there is no draft-delete endpoint, but a future delete feature would create gaps in a sequence IRAS expects to be serial.
- **I-4 `tests/test_db_conn.py`** is a script wrapped as a test (`sys.exit`) — it fails on any non-UTF8 cluster and asserts nothing about the app.

---

## 4. Regulatory Compliance Matrix (IRAS / Singapore)

| Requirement | Status | Basis |
|---|---|---|
| GST rate history 7% → 8% (2023) → 9% (2024) with effective dates | ✅ Correct | Seed + `tax-codes` output (Verified) |
| Rate resolution by document date, fail-closed on unknown code | ✅ | `ledgersg_SKILL` §8 #16–17 + probe (`/gst/calculate` 9.00 on 100.00) |
| F5 filing due date = period end + 1 month | ✅ in F5 module (Verified `2026-03-31`) ❌ in alerts (M-3) | |
| F5 statutory record immutability after filing | ❌ **C-2** | Verified |
| No back-posting into a filed period | ❌ **H-3** | Verified |
| Only GST-registered persons charge GST / issue tax invoices | ❌ **H-5** | Verified |
| Credit note shows original tax-invoice number/date | ❌ **H-4** | IRAS primary source + Verified |
| Tax-invoice particulars on the printed document (GST rate, "Tax Invoice"/"Credit Note" titles) | ⚠️ **M-9** | Template review only |
| GST/UEN number validity | ❌ **M-1** (rejects valid UEN-form GST numbers; accepts garbage) | IRAS + Verified |
| GST registration threshold (S$1M; retrospective + prospective; 30-day deadline) | ⚠️ **M-2** | Reasoned |
| Foreign-currency invoices show SGD amounts | ⚠️ Not supported at document level (**M-9**) | Reasoned; secondary source |
| 5-year record retention / immutability of financial records | ⚠️ Journals immutable by trigger (✅); audit coverage partial & owner-mutable (**M-6**); filed F5 mutable (**C-2**) | Verified |
| InvoiceNow / PINT-SG | ⚠️ XML generation + XSD validation exist; live AP delivery **not verified**; API key plaintext (**M-7**) | Reasoned |
| Double-entry integrity | ✅ unbalanced journal rejected; DB deferred balance trigger; concurrent approve safe | Verified |
| PDPA (personal data) | ⚠️ PII encryption at rest not implemented (self-declared SEC-005); no retention/erasure design reviewed | Not assessed in depth |

> Regulatory statements above were checked against IRAS' *Invoicing customers* page (credit-note and GST-number formats). Threshold and filing rules are stated from established IRAS practice and should be re-confirmed by the compliance owner before relying on them.

---

## 5. What Passed (so it is not re-litigated)

| Area | Evidence |
|---|---|
| Documented baseline is reproducible | 747 + 3 (stub-induced) = 750 passed; 5 skipped; frontend 530/530; typecheck 0 errors |
| API tenant isolation | User B → org A URLs: **403**; B's own org URL with A's document/contact/account IDs: **404**; cross-tenant contact/account injection into a B document: 404 (Verified) |
| Role gating on most mutations | Viewer got 403 on CoA, tax-codes, journals, Peppol/org settings, banking, document PATCH/status (Verified) |
| Concurrency on approval | 6 parallel approves → exactly one 200 (Verified) |
| Ledger controls | Unbalanced manual journal → 400; posting with no open fiscal period → 400; void of an allocated invoice → 400 (Verified) |
| Authentication design | HS256 15-min access, 7-day rotating refresh with blacklist; refresh cookie `HttpOnly`, `SameSite=Lax`, `Secure=!DEBUG`, `Path=/api/v1/auth/`; production SECRET_KEY strength gate; no `dangerouslySetInnerHTML`/token `localStorage` in the web app (Verified by grep/code) |
| Money handling | 47 `NUMERIC(19,4)` columns; `money()` rejects floats (existing invariants gate) |
| Container hygiene (backend image) | `USER ledgersg`, pinned `gunicorn` CMD, health-check |
| SQL injection | f-string SQL in the F5 query interpolates only placeholders (false positive) |
| CSP | Env-aware, production without `unsafe-eval/inline` (code review) |

---

## 6. Remediation Roadmap

| Priority | Work | Findings |
|---|---|---|
| **P0 — before any production traffic** | Set RLS context in org creation; CI/test tier on `ledgersg_app`; freeze FILED returns (API + DB trigger); lock filed periods | C-1, H-7, C-2, H-3 |
| **P1 — financial correctness** | Allocation ≤ balance + instalment statuses; credit-note linkage/cap; GST-registration guards on tax lines | H-1, H-2, H-4, H-5 |
| **P1 — security** | Enable/extend RLS (organisation, audit, peppol settings, tax_code…); dependency upgrades + blocking audits; fix Docker key generation | H-6, H-8, H-9 |
| **P2 — compliance depth** | UEN/GST validators; IRAS-conformant threshold monitor; single source of filing deadlines; PDF tax-document template; FX/SGD amounts | M-1, M-2, M-3, M-9 |
| **P2 — hardening** | Input validation (400s), contact/send/export role gates, audit triggers + `search_path`, Peppol key encryption, trusted-proxy rate limiting, tax-code dedupe | M-4…M-8, M-10 |
| **P3 — hygiene** | Ruff/ESLint debt, admin exposure, cache TTL, docs truth pass | L-1…L-4, I-* |

### Suggested regression tests (write RED first)
1. `test_org_create_as_app_role` — connect as `ledgersg_app`; `POST /organisations/` → 201 and CoA rows exist. *(C-1)*
2. `test_filed_return_is_immutable` — file → `POST …?force=true` → 409; row unchanged. *(C-2)*
3. `test_cannot_post_into_gst_locked_period` — after file, approve/ journal/ void dated inside the period → 409. *(H-3)*
4. `test_allocation_cannot_exceed_amount_due`; `test_second_instalment_on_partially_paid`. *(H-1, H-2)*
5. `test_credit_note_requires_original_and_cap`. *(H-4)*
6. `test_non_registered_org_rejects_gst_lines`; `test_line_before_gst_reg_date_rejected`. *(H-5)*
7. `test_every_org_id_table_has_rls` (query `pg_class`/`information_schema`). *(H-6)*
8. Table-driven `role × endpoint` authorization test. *(M-5)*

---

## 7. Reproduction Notes

Sandbox recipe used (no root): `uv python install 3.12`; Postgres 15.18 from the Debian `.deb` extracted with `dpkg-deb -x` (contrib extensions required by the schema: `pg_trgm`, `btree_gist`, `pgcrypto`); Redis 7.2.4 built from source; **databases must be created `ENCODING 'UTF8'`** (an `SQL_ASCII` cluster makes psycopg3 return `bytes` and fails `tests/test_db_conn.py` — an environment effect, not a defect); `weasyprint` stubbed on `PYTHONPATH`.

Key probes (all against a live `runserver`):
```bash
# C-1: run the server with DB_USER=ledgersg_app, then
curl -X POST :8000/api/v1/organisations/ -H "Authorization: Bearer $T" -d '{...valid org...}'   # -> 500 (RLS violation)
# C-2 / H-3: file the Feb return, create+approve an invoice dated in Feb, then
curl -X POST ":8000/api/v1/$ORG/gst/returns/$RID/?force=true" -H "Authorization: Bearer $T"      # -> 200, status COMPUTED
# H-1: invoice due 109.00
curl -X POST :8000/api/v1/$ORG/banking/payments/receive/ -d '{... "amount":"5000.00","allocations":[{"document_id":"$DOC","allocated_amount":"5000.00"}]}'  # -> 201, amount_due -4891
# H-2: after a partial payment, allocate the remainder -> 400 "Document must be APPROVED before allocation."
```

## 8. Not Verified / Out of Scope
Real PDF rendering; live InvoiceNow/Storecove/IRAS interaction; Playwright e2e and browser accessibility (WCAG claims); Docker image builds; Celery task behaviour under failure; load/performance claims in the PAD ("<50 ms", "95% cache hit"); DELETE protection on `journal.entry` rows (an UPDATE guard exists; DELETE behaviour was not tested); BCRS regulatory accuracy; PG16-specific behaviour; PDPA assessment; all findings in the prior audit files in this repo were treated as inert background and were **not** relied upon.

## 9. Hand-off
- **Fixed in this audit:** nothing (Mode C).
- **Deferred decisions for the owner:** how to model a GST-locked period (flag on fiscal period vs org cut-off date); whether credit notes may exceed the original with a reason code; whether to keep the `SECURITY DEFINER` audit writer or move to a dedicated audit role.
- **Delivery note:** the report is committed locally on `main` (Conventional Commit). It was **not pushed** — the SSH wrapper in `docs/DEPLOYMENT.md §15` needs a deploy key that is not available in this environment; push with the documented `ssh_git_wrapper_v3.py --key-file … --remote git@github.com:nordeim/ledgersg.git`.
