# LedgerSG — Comprehensive Code Review & Regulatory Compliance Audit

**Repository:** `https://github.com/nordeim/ledgersg`
**Commit audited:** `e514fb3` ("update session log", P13 truth pass, session 27)
**Audit date:** 2026-11-24
**Auditor mode:** Mode C — Audit / Review (*findings only; no upstream source was modified*)
**Prior baseline:** `LedgerSG_Code_Review_Audit_Report_2026-11-21.md` (commit `82ecd62`, 4 Critical / 14 High / 16 Medium / 10 Low / 8 Info)
**Stack:** Django 6.0.2 REST API (`apps/backend`) + Next.js 16 / React 19 web app (`apps/web`) + PostgreSQL 16 (hand-written SQL schema, RLS) + Redis 7 + Celery
**Skill pipeline (from repo `skills/`):** `code-review-and-audit` (deep profile) orchestrating `code-review-checklist`, `code-quality-standards` (Six-Axis), `api-and-interface-design`, plus finance-domain lenses `gl-reconciler` (GL ↔ subledger tie-out) and `month-end-closer` (period-close discipline), and `encrypt-decrypt` (secret & PII-handling lens). Catalog reference: `skills/skills-catalog.md` (345 skills).

**Documents read in full:** `AGENTS.md` · `CLAUDE.md` · `README.md` · `Project_Architecture_Document.md` v3.8.0 (P13) · `ledgersg_SKILL.md` · `docs/DEPLOYMENT.md` (fresh-host verified guide) · `docs/REMEDIATION_2026-11-21…24` P1–P13 reports · the 2026-11-21 audit report.

---

## 0. Executive summary

The November-21 audit left LedgerSG **not releasable for production bookkeeping or IRAS filing**: a dead GST F5 pipeline, voids that never reversed the ledger, discarded RLS tenant context, and 500-path partial commits. The P11–P13 remediation trail (50+ commits between `82ecd62` and `e514fb3`, each phase carrying a live-verification report) has **genuinely closed all four Criticals** — the fixes are present in the source reviewed, with dedicated regression and isolation tests alongside them.

What remains is a different, narrower risk profile. The bookkeeping core is sound for standard-rated SGD flows; the edges that touch the regulator and real money need closing before a paid pilot files a live return.

| Severity | Count | Release gate |
|---|---|---|
| 🔴 Critical | **0** | No release-blocker open. All four Nov-21 Criticals verified remediated (Reasoned — see §1). |
| 🟠 High | **5** | Must fix before any production pilot holding real tenant money or filing IRAS returns. |
| 🟡 Medium | **8** | Fix within the next sprint; several become High at multi-currency / multi-tenant scale. |
| 🟢 Low | **5** | Schedule; hygiene and hardening. |
| ⚪ Info | **4** | Backlog / scoping notes. Includes one commendation (BCRS). |

### Verdict

> **GO for a controlled pilot — with conditions. NOT YET for open production or unsupervised IRAS filing.**
>
> - Controlled pilot (sandbox + a handful of real SMBs, supervised filings): **GO once P14 closes H-01…H-05** and the full gate (pytest + Vitest + typecheck + build + 40 live e2e) is re-run green on the release commit.
> - Open production: requires P15 (maker-checker, boxes 9–15 sourcing, restore drill, retention rule).

### Six-axis scorecard (0–5)

| Axis | Score | Basis |
|---|---|---|
| Correctness | **4.0** / 5 (▲ from 1.5) | F5 pipeline functional, credit-note reversal polarity fixed, fail-closed control accounts, IRAS 2dp per-line rounding, TB/P&L/BS tie-out + void guards. |
| Security | **4.2** / 5 (▲ from 2.0) | RLS inside request transaction, rollback-on-500, httpOnly refresh rotation, rate limits, env-aware CSP, production SECRET_KEY gate. |
| Regulatory compliance | **3.8** / 5 (new axis) | F5 lifecycle + box identities DB-enforced, PINT-SG XSD+Schematron, BCRS exemption. Residual: historic GST rates, UEN checksum, override evidence, manual e-filing. |
| Reliability | **4.0** / 5 (▲) | Atomic postings, reversal atomicity, typed 404/409/429 contracts, Celery seam fixed, health error hygiene. |
| Maintainability | **3.4** / 5 (≈) | Clean service seams; drag from 100+ root markdown files, dual Python manifests, deferred lint tail (ESLint ~45, ruff ~305). |
| Performance | **3.8** / 5 (≈) | Tenant-membership Redis cache, per-glob coverage thresholds; no N+1/load study re-run in this pass. |

### Confidence protocol used throughout

- **Verified** — executed or read directly in source by this auditor.
- **Reasoned** — logical inference from code + remediation reports, not executed here.
- **Assumed** — based on a stated assumption (flagged where used).
- **Unverifiable** — this offline environment did not permit verification (no DB/Redis/browser; no test process launched).

---

## 1. Reconciliation with the 2026-11-21 audit (all four Criticals closed)

| # | Nov-21 defect | Current state at `e514fb3` | Evidence observed | Confidence |
|---|---|---|---|---|
| C-01 | F5 pipeline non-functional (phantom tables/attributes, serializer crash) | **Remediated** | `return_service.generate_f5()` assigns real columns (box1/2/3/4/5/6/7/8/13/14); `get_f5_box_amounts()` sources from ledger; DB CHECKs `chk_box4_total`/`chk_box8_net`; F5 panel + deadlines re-verified live (P11). | Reasoned |
| C-02 | Voids never reversed the GL (`pass` placeholder) | **Remediated** | Credit notes post REVERSED entries and NET in F5 (P11); `void_document()` enforces allocation guards, closed-period refusal, mandatory reason + actor; PAID→void refused (credit-note remedy); `create_reversal` atomic (P13/B-11, tolerance B-13). | Reasoned |
| C-03 | RLS `SET LOCAL` discarded before views; audit without actor | **Remediated** | `TenantContextMiddleware` joins the request atomic before `SET LOCAL app.current_org_id/user_id`; `AuditContextMiddleware` carries IP/UA/path; `ATOMIC_REQUESTS=True`; isolation tests (`test_rls_isolation`, `test_rls_transaction_isolation`, `middleware/test_rls_context`). | Reasoned |
| C-04 | `wrap_response` 500s committed partial writes | **Remediated** | DRF exception handler rolls back instead of committing 500 (P13/B-1); typed `ImmutabilityError`→409 (B-5); payment/void/allocation paths `@transaction.atomic` with fail-closed control accounts. | Reasoned |

Confidence is **Reasoned, not Verified**, for one explicit reason: this pass ran offline (cloned source only) and did not re-execute the 1,320-test gate. The fixes are present in source and each carries phase-level live verification in-repo; re-running the gate on the release commit is P14 item zero (see §8, I-02).

---

## 2. Open findings — High severity

### H-01 — UBL/XML parser not hardened against XXE / entity-expansion DoS
- **Location:** `apps/backend/apps/peppol/services/xml_validation_service.py:33,42,58`
- **Description:** Invoice/CreditNote XSDs are loaded with `etree.parse()` and candidate documents with `etree.fromstring(xml_string.encode("utf-8"))` using lxml defaults. No shared `XMLParser(resolve_entities=False, no_network=True, huge_tree=False, load_dtd=False)` was observed. A validation/transmission path that accepts XML is exactly where a hostile document arrives.
- **Evidence:** `schema_doc = etree.parse(self.INVOICE_SCHEMA_PATH)`; `xml_doc = etree.fromstring(xml_string.encode("utf-8"))`. No `XMLParser(...)` construction in the file; no `resolve_entities` / `no_network` flags. (lxml defaults beat stdlib, but billion-laughs-class expansion and external-DTD SSRF remain the caller's duty to switch off.)
- **Impact:** Malicious UBL → CPU/memory exhaustion or local-file/SSRF disclosure during validation. Likelihood moderated (self-generated XML is the common path) — stays High because the input is attacker-adjacent.
- **Severity:** High · **Confidence:** Verified
- **Recommended fix:** One shared hardened parser for every parse/fromstring (schemas once, documents per call). Add regression tests: (a) `<!ENTITY xxe SYSTEM 'file:///etc/passwd'>` rejected without file access; (b) billion-laughs rejected fast. Reject with typed 400, never echo the payload.

### H-02 — UEN validation is regex-only: no ACRA checksum, accepts a non-UEN, partnership pattern incomplete
- **Location:** `apps/backend/apps/invoicing/services/contact_service.py:266–300` (`_validate_uen`)
- **Description:** Four regexes only: `^\d{9}[A-Z]$`, `^\d{8}[A-Z]$`, `^[TS]\d{2}[A-Z]{2}\d{4}[A-Z]$`, and `^\d{10}$` ("GST-registered businesses"). No check-digit verification against ACRA's UEN structure; the all-numeric 10-digit branch is not a UEN; the T/S pattern omits valid prefixes/entity-type letters. Invalid counterparties pass the API and fail later — at InvoiceNow transmission or filing.
- **Evidence:** Read `_validate_uen` in full: `strip().upper()`, length 8–10 gate, four `re.match` patterns, `any(...)`. No checksum routine anywhere in the function.
- **Impact:** Bad counterparty master data → Peppol participant-ID mismatches, rejected InvoiceNow deliveries, unreconciled GST counterparty queries. For a compliance product, master-data validation is a control.
- **Severity:** High · **Confidence:** Verified
- **Recommended fix:** Implement ACRA-structure validation (9-digit other-entities with check letter; 10-digit local companies `YYYYNNNNNK` with century sanity; T/S-issued with entity-type + check letter via the published modulus). Drop or quarantine the bare `^\d{10}$` branch ("legacy identifier — manual review"). Ship warn-then-enforce behind a per-org strict flag for one release.

### H-03 — GST rate is a single hardcoded 9%: no rate-by-date for the 7% → 8% → 9% history
- **Location:** `apps/backend/apps/gst/services/calculation_service.py:22` (`DEFAULT_GST_RATE = Decimal("0.09")`)
- **Description:** All GST math defaults to 9%. Singapore's rate was 7% (to 31 Dec 2022), 8% (2023), 9% (from 1 Jan 2024) with IRAS transitional time-of-supply rules. Backdated corrections, late-entered 2023 purchases, or credit notes referencing 2023 supplies compute at 9% unless every line is manually overridden — the document path defaults all unspecified lines to 9%. No effective-date rate table or time-of-supply guard observed. This is the highest-probability compliance misstatement left in the codebase.
- **Evidence:** `calculate_document_gst(lines, default_rate=DEFAULT_GST_RATE)`; no rate-history table or dated-band lookup in the gst service.
- **Impact:** Wrong GST on any pre-2024 document entered today → wrong input-tax claims, wrong F5 boxes 6/7.
- **Severity:** High · **Confidence:** Verified
- **Recommended fix:** Dated rate table (effective_from, rate, transitional note) seeded with the three bands; resolve from the document's time-of-supply date with explicit per-line override winning; review warning on date/band mismatch. Tests: 2022/2023/2024 invoices, backdated purchase, credit note inheriting original supply date.

### H-04 — NRIC-based PayNow identifiers in cleartext with no observed masking (PDPA)
- **Location:** `apps/backend/apps/core/models/bank_account.py:17` · `apps/backend/apps/banking/serializers/bank_account.py:53–185`
- **Description:** `paynow_type=NRIC` with 9-char `paynow_id` is validated for length but no masking, redaction, or restricted-field handling was observed in the API layer, and no PDPA collection/purpose statement for NRIC was found in the reviewed surface. NRIC numbers are protected identifiers under Singapore's PDPA.
- **Evidence:** Model choices include `("NRIC","NRIC")`; serializer enforces 9-char NRIC; backend-wide NRIC grep hits only these banking paths + tests — no masking helper, redaction decorator, or notice reference observed. (Response-shape tracing was not exhaustive — hence Reasoned.)
- **Impact:** NRIC disclosure via list/detail, logs, or exports → breach-notification territory even with auth in place.
- **Severity:** High · **Confidence:** Reasoned
- **Recommended fix:** Mask by default (last-3 + checksum letter), explicit permission for full view, exclude from logs/exports, in-UI collection notice + retention/deletion-on-deactivation statement, masked-by-default test.

### H-05 — Filer can override computed F5 boxes 6/7 (and 9–12/15) with no evidence workflow
- **Location:** `apps/backend/apps/gst/services/return_service.py:26–40` (`OVERRIDABLE_BOX_FIELDS`) · `file_return()`
- **Description:** Derived boxes 4/8 are correctly server-recomputed and never accepted — good. But box6, box7, and boxes 9–15 are filer-overridable via the `boxes` dict on `file_return()`, with no supporting-document attachment, adjustment reason code, or second-reviewer requirement observed. Filed figures can diverge from the subledger on a free-text trail.
- **Evidence:** Allow-list explicitly includes `box6_output_tax`, `box7_input_tax_claimable`, `box9/10/11/12/14/15`; `file_return(org_id, return_id, filed_by_id, filing_reference, boxes)` persists overrides. The DRAFT→COMPUTED→REVIEWED→FILED→AMENDED machine is the right skeleton — the override itself is ungated.
- **Impact:** In an IRAS dispute, "the API accepted it" is not a defence; the 5-year supporting-record chain breaks at filing.
- **Severity:** High · **Confidence:** Verified
- **Recommended fix:** Keep overrides (bad-debt relief, tourist refunds, pre-registration claims legitimately need judgment) but gate them: mandatory reason + delta-vs-computed, ≥1 attachment reference, and reviewer≠preparer / filer≠reviewer before FILED whenever an override is present. Persist computed-vs-filed deltas immutably.

---

## 3. Open findings — Medium severity

### M-01 — F5 boxes 9–15 effectively manual (no automated sourcing)
- **Location:** `return_service.generate_f5()` box-assignment block · `calculation_service.get_f5_box_amounts()`
- **Description:** Boxes 1–8/13/14 are computed; boxes 9 (MES/IGT imports), 10 (tourist refund), 11 (bad-debt relief), 12 (pre-registration), 15 (e-marketplace) rely on filer override. Reverse-charge (box14) is carried but its sourcing from purchase-side postings was not fully traced.
- **Impact:** Systematic under-claim/misstatement for traders, importers, tourist-facing retailers. **Severity:** Medium · **Confidence:** Reasoned
- **Fix:** Source from schema-known flags (AP scheme → 9; write-offs → 11; pre-reg schedule → 12; reverse-charge postings → 14), each computed-with-override under the H-05 control.

### M-02 — InvoiceNow is invoice-only; CreditNote has schema but no send path
- **Location:** `apps/backend/apps/peppol/` (`ubl-CreditNote.xsd` present) · `transmission_service.transmit_invoice()` · PAD P9
- **Description:** The UBL CreditNote XSD + Schematron ship, but the transmission seam is invoice-only ("InvoiceNow invoice-only"). A sales credit note corrects local books but cannot travel the Peppol channel of its original invoice.
- **Impact:** Counterparty reconciliation friction; a message-set gap a B2B pilot customer will notice. **Severity:** Medium · **Confidence:** Reasoned
- **Fix:** Extend the existing `execute_transmission_for_log` seam to credit notes (mapping → generation → validation → AP send) behind the same approval flow.

### M-03 — No observed automated period-end FX revaluation run
- **Location:** `journal_service` (`FX_REVALUATION` source type) · `config/celery.py` · `exchange_rate` model
- **Description:** Vocabulary + currency models exist, but no beat-scheduled unrealised gain/loss revaluation routine was observed. SGD-only books unaffected; any USD/MYR/IDR trading SMB hits this at its first month-end.
- **Impact:** Misstated P&L/BS for foreign-currency traders. **Severity:** Medium · **Confidence:** Reasoned (routine may live outside sampled paths)
- **Fix:** Ship the job (schedule + postings + next-period reversal + report) **or** explicitly scope to SGD-only and enforce a base-currency lock at org creation.

### M-04 — Audit IP trusts X-Forwarded-For with no pinned trusted-proxy count
- **Location:** `apps/backend/common/middleware/` — `AuditContextMiddleware._get_client_ip`
- **Description:** Leftmost XFF value taken as client IP; the code honestly notes (M-14) this is client-controlled without a pinned proxy count. Behind any proxy/CDN the stored audit IP is spoofable.
- **Evidence:** `x_forwarded_for.split(",")[0].strip()`, no hop count; in-code NOTE defers to deployment config. **Severity:** Medium · **Confidence:** Verified
- **Fix:** `TRUSTED_PROXY_HOPS` setting (or platform edge header), default `REMOTE_ADDR`; document the proxy contract in DEPLOYMENT §12.

### M-05 — Stale root `requirements.txt` is a second, conflicting Python manifest
- **Location:** `requirements.txt` (root) vs `apps/backend/pyproject.toml` (canonical)
- **Description:** DEPLOYMENT §1 correctly says ignore the root file ("stale second manifest — do not use"). A conflicting manifest at root is a version-drift / wrong-tree-install vector.
- **Severity:** Medium · **Confidence:** Verified
- **Fix:** Delete (or one-line pointer) + CI guard failing on reappearance. Single-manifest rule.

### M-06 — Five-year IRAS record-retention posture not stated in reviewed surface
- **Location:** `docs/DEPLOYMENT.md` §12 · fiscal-close / document lifecycle
- **Description:** Fiscal-close preconditions, void-reason retention, and audit trail exist — but no explicit ≥5-year retention/immutability rule (no-delete windows, backup-retention schedule, export-on-exit) was found in the sampled surface. Flagged **Assumed**: absence in sample ≠ absence in product.
- **Impact:** A pilot customer asking for the retention design gets an operational answer, not a compliance answer. **Severity:** Medium · **Confidence:** Assumed
- **Fix:** Publish the rule (source docs, F5 versions incl. overrides, audit events ≥5y, immutable after FILED/closed period), wire to backup retention + org export, add to the filing checklist.

### M-07 — No maker-checker (segregation of duties)
- **Location:** `apps/core/permissions.py` · `approve/void_document` · `review/file_return`
- **Description:** Authorisation, membership gates, and actor stamps exist (P7). Not observed: reviewer≠preparer / filer≠reviewer enforcement — one user can approve, void, review, and file.
- **Impact:** Fraud/error concentration; external auditors raise it before signing a pilot. **Severity:** Medium · **Confidence:** Reasoned
- **Fix:** Optional per-org SoD policy (default ON for filing), enforced with 403 + reason; toggleable for sole proprietors.

### M-08 — Backup/restore/PITR documented but not evidenced as exercised
- **Location:** `docs/DEPLOYMENT.md` §12 · `docker/` · schema loader notes
- **Description:** Roles, schema loading (superuser DO blocks), Redis, Gunicorn, secrets hygiene covered. No restore-drill record (dump/PITR + RLS re-verification + F5 re-compute match) found in sampled reports. An untested restore is not a control.
- **Severity:** Medium · **Confidence:** Reasoned
- **Fix:** Run + record a restore drill, publish RTO/RPO, repeat quarterly. One page suffices.

---

## 4. Open findings — Low severity & informational

| ID | Title | Severity | Confidence | Location | Fix (one line) |
|---|---|---|---|---|---|
| L-01 | 100+ markdown files at repo root bury the source of truth | Low | Verified | root `*.md` (~90) + `docs/` (~70) | Archive to `docs/archive/YYYY-MM/`; six canonical root files + `docs/README` index. |
| L-02 | Bottom-of-file import (circular-import workaround) | Low | Verified | `invoicing/services/contact_service.py` tail | Break seam (protocol/lazy import), top-level imports. |
| L-03 | UEN TOCTOU closed at API; assert DB unique guard in CI | Low | Reasoned | `contact_service` + P11/L-9 | Concurrent-insert test pinning `(org_id, uen)` uniqueness. Status: Partially remediated. |
| L-04 | `console.error/debug` in shipped auth module | Low | Verified | `apps/web/src/lib/api-client.ts` | Debug-gated logger; never log token material. |
| L-05 | Deferred lint tail (ESLint ~45, ruff ~305) needs burn-down owner | Low | Reasoned | PAD metrics; P12 79→45 | Keep gates; ~20/week; CI fails on new-issue delta only. |
| I-01 | AGPL-3.0 network copyleft needs a recorded commercial answer | Info | Verified | `apps/backend/pyproject.toml` | Licence-model note in README + counsel sign-off before paid pilots. |
| I-02 | 1,320-test claim not re-executed in this offline pass | Info | Unverifiable | PAD metrics | Cite as "per P13 live verification"; attach CI log on release commit. |
| I-03 | Manual-reference filing correctly scoped — keep UX explicit | Info | Reasoned | `file_return(filing_reference)` | Label "Record myTax filing" + acknowledgement capture + countdown. |
| I-04 | **BCRS exemption correctly implemented (commendation)** | Info | Reasoned | `calculation_service.calculate_line_gst` | None — preserve; reuse flag discipline for future schemes. |

---

## 5. Regulatory compliance deep-dive

### 5.1 IRAS GST F5 (GST-registered SMBs, 9% regime)

Core computation is correct: per-line `ROUND_HALF_UP` to the cent unit (P13/B-2 fixed a mil-level quantum bug: `Decimal(1).scaleb(-rounding)`), document aggregation with BCRS exclusion, quotes excluded from supplies, credit notes netting (P11), box-4/box-8 identities DB-enforced, full DRAFT→…→AMENDED lifecycle with periods/compute/review/file/amend/deadlines, and the dashboard liability re-sourced to F5 net GST (P11/H-4).

| Box | Label | State |
|---|---|---|
| 1–3 | Standard / zero-rated / exempt supplies | Computed |
| 4 | Total supplies | Derived (server-only + CHECK) |
| 5 | Taxable purchases | Computed (overridable — gate per H-05) |
| 6–7 | Output tax / input tax | Computed (overridable — gate per H-05; historic-rate risk H-03) |
| 8 | Net GST | Derived (server-only + CHECK) |
| 9–12, 15 | Imports-schemes / tourist refund / bad-debt / pre-reg / e-marketplace | Override-only (source per M-01) |
| 13–14 | Total revenue / reverse charge | Computed (deepen 14 sourcing per M-01) |

Filing is manual-reference (`filing_reference` free text) — correct scope (no public IRAS F5 submission API), must stay explicit in UX (I-03). Retention posture must be published (M-06).

### 5.2 InvoiceNow / Peppol PINT-SG

Generation → mapping → XSD + Schematron validation → Storecove AP send → transmission log + retry is wired, including the P5/C-2 log/invoice-id seam fix. Gaps: hardened parser (H-01), credit-note send path (M-02), UEN-driven participant-ID quality (H-02).

### 5.3 ACRA UEN, BCRS, PDPA

UEN: regex-only (H-02). BCRS: clean implementation at the right layer (I-04). PDPA: NRIC PayNow IDs need restricted-field treatment (H-04); XFF audit-IP caveat (M-04); retention statement (M-06).

---

## 6. Security review (OWASP-2025 lens, proportionate to scope)

- **Access control:** org-membership gates + status-transition authorisation (P7) + transaction-scoped RLS + isolation tests. No IDOR/bypass observed in sampled paths. SoD absent (M-07).
- **Auth/session:** access-in-memory, HttpOnly refresh rotation, evidence-gated 401 refresh, login/register/refresh throttles, password validators, production SECRET_KEY gate. No finding.
- **Injection:** sampled `cursor.execute` sites parameterised; no concatenated SQL observed (Reasoned). XXE/entity-expansion open (H-01). XSS posture: single header source, env-aware CSP (unsafe-* dev-only), no `dangerouslySetInnerHTML` encountered in sampled components.
- **Secrets:** env-driven; no hardcoded keys; production refuses defaults (Verified). Stale manifest risk (M-05).
- **Rate limiting / availability:** DRF throttles + `django-ratelimit` with 429 contract; mutations exempt from retry (double-submit fix P13/M-3); health error hygiene.
- **Logging/PII:** structured logging present; NRIC/log-exclusion gap (H-04); console logging in web auth (L-04).
- **Dependencies:** pinned majors (Django 6.0.2, Next 16.1.6, redis-py 6.4.0, lxml 6.0.2). A full CVE/SCA sweep was out of scope and is recommended pre-pilot (`pip audit` / `npm audit` + Dependabot).

---

## 7. Architecture & code-quality notes

Service-layer seams are clean (`GSTCalculationService`, `GSTReturnService`, `JournalService`, `DocumentService`, `PaymentService` with fail-closed control accounts, `TransmissionService` with the decoupled log seam). Double-entry vocabulary covers sales/purchase invoices, credit/debit notes, quotes/orders, payments, fees, FX revaluation, year-end, opening balances, reversals. Money is `NUMERIC(19,4)` with `money()`/`sum_money()` helpers; frontend mirrors with `decimal.js` + `gst-engine.ts`.

Drag factors: documentation sprawl (L-01), dual manifests (M-05), deferred lint tail without owner (L-05), bottom-of-file import (L-02). None affects runtime; all affect the next audit's cost. The P1–P13 remediation discipline itself — small commits, per-phase live verification, honest "honest floor" coverage language — is the strongest maintainability signal in the repo and should be kept as the working method.

---

## 8. Verification ledger

| Check | Method | Result | Confidence |
|---|---|---|---|
| Per-line rounding quantum = IRAS cent unit | Read `calculate_line_gst` | Pass (P13/B-2 present) | Verified |
| F5 box-4/box-8 server-derived, never accepted | Read allow-list + `generate_f5` | Pass | Reasoned |
| C-01…C-04 remediated | Git log P11–P13 × defect descriptions + spot-reads | Pass | Reasoned |
| RLS SET LOCAL in-request-transaction | Read both middlewares + `ATOMIC_REQUESTS` | Pass + isolation tests present | Reasoned |
| 500-path rollback | Read `wrap_response`/handler + P13/B-1 | Pass; typed 409/404/429 observed | Reasoned |
| Refresh-token discipline | Read `api-client.ts` contract | Pass (httpOnly, no storage JWT, no mutation retry) | Verified |
| Secrets hygiene | Grep + production SECRET_KEY gate | Pass (env-driven, defaults refused) | Verified |
| Raw-SQL parameterisation | Grep `cursor.execute` sample | Pass on sampled sites | Reasoned |
| Password validators | Read settings | Pass (4 validators) | Verified |
| Full 1,320-test gate | Not executed (no DB/Redis/browser here) | Not run — cite P13 live counts as reported | Unverifiable |

---

## 9. Remediation roadmap

**P14 — pre-pilot (2–4 weeks; gates the paid pilot):** H-01 hardened XML parser + tests · H-02 ACRA UEN behind strict flag · H-03 dated GST-rate table + time-of-supply · H-05 F5 override control · H-04 NRIC masking + notice. Plus: re-run the full gate green on the release commit and attach the log (I-02); run `pip/npm audit` (dependency sweep deferred from this pass).

**P15 — pilot hardening (30–60 days):** M-07 maker-checker · M-01 boxes 9–15 sourcing · M-02 Peppol CreditNote path · M-03 FX job or SGD-only lock · M-04 proxy-hop pinning · M-08 restore drill with RTO/RPO · M-06 five-year retention rule.

**Backlog:** L-01 docs archive · M-05 manifest deletion + CI guard · L-02 import cycle · I-01 AGPL model in writing · I-03 myTax UX labelling.

---

## 10. Definition-of-Done self-check (§19/§20)

- Every requested element addressed (clone → read AGENTS/CLAUDE/README/PAD/SKILL/DEPLOYMENT → skills-guided audit → markdown deliverable + browsable report)? **Yes.**
- Findings classified by severity with location/evidence/impact/fix/confidence; nothing inflated; clean code commended (I-04)? **Yes.**
- No code modified upstream; no guardrail weakened; no secret logged; no placeholder values? **Yes.**
- Unverifiable items explicitly labelled with what would verify them? **Yes (§8, I-02).**
- Markdown deliverable in output location (`public/LedgerSG_Comprehensive_Audit_2026-11-24.md`, mirrored by the in-app download)? **Yes.**
- UI justified (report navigation/filtering), responsive, keyboard-operable, no parent-layout assumptions? **Yes.**
- Remaining debt handed off cleanly (§9)? **Yes — P14/P15/backlog with owners' actions.**

*Audit skein: `code-review-and-audit` → `code-review-checklist` → `code-quality-standards` → `gl-reconciler`/`month-end-closer` tie-out lens → this report. All non-trivial claims carry confidence tags; tool output inconsistent with code would have been re-verified, not accepted.*
