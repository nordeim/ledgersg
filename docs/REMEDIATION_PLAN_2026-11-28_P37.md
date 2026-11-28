# LedgerSG — Remediation Plan (P37 Sprint: The Credit-Note Reference Truth — The BillingReference Wiring + The Reason Note + The PDF Presentation)

**Date:** 2026-11-28 (session 72)
**Base commit:** `a7ce0c10` (main — post-P36 + the session-71 log)
**Method for execution:** TDD (RED → GREEN → full gate) for every behavioural change (two new specs, each RED on the base tree); `skills/` excluded from all checks/tests/compilation; **no schema changes** (v1.2.2 carries forward — the XSDs and the `.sch` are application artefacts); **no frontend component changes** (the web tree renders whatever the API sends; the credit-note surfaces are API-driven).
**Skills consulted:** `skills/skills-catalog.md` → `tdd` (the red→green loop, the vertical-slice rule), `code-review`/`code-review-checklist` (Mode C discipline — findings separated from fixes, severity taxonomy), `debugging-and-error-recovery` (root-cause isolation — the finding reproduced live before any fix), `rootless-postgresql` (the PG environment — verified running this session), `agent-browser` (the live mobile-nav + translate probes — re-executed this session, §1), `nextjs16-tailwind4`/`tailwind-patterns` (consulted for the mobile-nav focus — re-settled clean this session, §1).

---

## 1. Audit inputs (this session's evidence)

- **Repo + docs truth pass:** `git pull` to `a7ce0c10` (the session-71 narration log); full reads of `AGENTS.md`, `CLAUDE.md` v2.37.0, `README.md`, `Project_Architecture_Document.md` v3.26.0, `ledgersg_SKILL.md` v2.23.0, `worklog.md`, `docs/session_70.md`, `docs/session_71.md`, the P36 plan + report, `docs/Tailwind-V4-Validation-Report.md`, `skills/skills-catalog.md`.
- **The environment (survived the sandbox recycle — verified, not re-provisioned):** rootless **PG 17** on :5432 (both databases present, the v1.2.2 schema — 45 tables across the 8 schemas; the demo substrate accumulated across the e2e runs: 149 orgs, 45 journal entries, 1710 accounts, 37 documents incl. 1 credit note, 16 payments), **Redis 8** on :6379, the backend venv, the web tree `node_modules` (the dev servers had been reaped — the documented sandbox behavior; every live gate ran with the backends started INSIDE the same invocation, the session-66 lesson).
- **The baseline reproduction (pre-change, this session — all gates exact):** backend `pytest --reuse-db --no-migrations -q` **1114P/0F/5S** (31.39s) · vitest **698/698 (85 files)** · `npx tsc --noEmit` **0 errors** · whole-tree eslint **0E/0W** · live `test:e2e:full` **43/43 (2.4m)** · `rls_smoke.py` **13/13 as `ledgersg_app`** (the :8001 instance) · `mobile-nav-audit.js` **17/17** (the forty-second settlement) · the dedicated Tailwind v4 `translate` probe: **PASS** (mid-flight count 7; `transitionProperty "transform, translate, visibility"`; Escape closes) · `make lint-mechanical` exit 0 · the production ruff count **148** exact · the tests-tree count **73** exact · `npm audit` **0 across dev+prod**. **All documented gates reproduced exactly — the P36 state holds.**
- **The named focus — the mobile-nav verdict (forty-second settlement):** **WORKING as expected; NO remaining TailwindCSS v4 bug on this surface.** The live probe re-verified the full contract at 375/800/1280 and the `translate` probe re-sampled the slide mid-flight — the P23 fix (`transition-[transform,translate,visibility]` in `apps/web/src/components/layout/shell.tsx`) holds.
- **The standing test-suite task (vitest + playwright configs):** verified IN PLACE and current — `apps/web/vitest.config.ts` (jsdom, the setup file, the whole-suite + per-glob coverage tiers) and `apps/web/playwright.config.ts` (chromium default, the live-suite serialisation contract, the E2E_API_URL gating) driving **698 vitest specs (85 files) + 43 e2e specs** — all green this session.
- **The audit (Mode C) of the P36 slice** (commit `d78bddb1`, hand-verified in source this session): the `PINT-SG-ARITHMETIC` pattern holds (the six BR-CO rules with IDs + the documented omissions + the sound-bound rationale); the mapper's tax-currency truth holds (`invoice.currency or "SGD"`); the generator's guarded TaxCurrencyCode emission + `_format_percent_text` hold; the P36 specs green in the suite — **0 new findings in the P36 slice**.
- **The fresh findings (this session's audit — the presentation-layer sweep of the credit-note path P34 built):**

  - **(a) The original-invoice reference gap (reproduced via live probe on the real demo credit note):** the DB layer REQUIRES `related_document_id` for every credit note (`DocumentService._validate_credit_note_reference`, P14/H-4 — the docstring itself quotes the IRAS rule: "A credit note must show the number and date of the original tax invoice"); the IRAS e-Tax Guide on the GST InvoiceNow requirement §11.6 says the business "should indicate the number and date of the original invoice… when submitting credit note data to IRAS"; the Peppol PINT credit-note syntax carries it as `cac:BillingReference` → `cac:InvoiceDocumentReference` (→ `cbc:ID` 1..1, `cbc:IssueDate` 0..1 — verified on docs.peppol.eu, the IBG-03 group: IBT-025 + IBT-026). But **NEITHER presentation layer emits it**: the mapper builds no reference field, the generator emits no `cac:BillingReference` (probe on the real demo credit note `CN-00001` → original `INV-00001` (2026-01-01): **BillingReference elements: 0; occurrences of the original invoice number in the XML: 0**), and the PDF template (`invoice_pdf.html`, which credit notes render through) carries no reference block (grep: no `related_document` in the template). A receiver of the transmitted credit note cannot match it to the invoice it corrects; the IRAS "number and date" requirement is unmet by BOTH emitted artefacts while the DB enforces the data — the exact P33/P36 hazard class (a truth the data layer guarantees that the presentation layer drops).
  - **(b) The reason-note gap:** the Peppol PINT-SG rule **BR-111-GST-SG** (warning class) expects a credit note carrying a taxable GST category to have an invoice note giving the reason for credit; the repo's mapper drops the document's `notes` field entirely and the generator emits no `cbc:Note` on either path (the PDF already renders `document.notes` when present — the XML surface is the gap). The demo credit note carries `notes=''` (the field exists and flows through the create API).
  - **(c) The PDF heading truth (folded into (a)'s fix):** the invoice PDF template titles a credit note with the raw enum `{{ document.document_type }}` — it renders "SALES_CREDIT_NOTE" — while IRAS expects the document "Headed as 'Credit Note'" (the e-Tax Guide rate-change annex wording); the same template block already special-cases SALES_INVOICE → "TAX INVOICE".

**Combined findings (this session's audit): 0 Critical / 1 High / 1 Low.**

## 2. Findings (verified, with evidence anchors)

### High

**BE-P37-H1 — the credit-note original-invoice reference truth: the DB requires the reference, IRAS mandates it, the PINT syntax carries it — but neither the emitted UBL nor the PDF shows it.**
The transmission pipeline validates and transmits a credit note that cannot be matched to the invoice it corrects: no `cac:BillingReference`, no `cac:InvoiceDocumentReference/cbc:ID`, nothing in the PDF. The fix threads the DB's own guarantee through every presentation layer:

- **The mapper:** `"billing_reference": {"id": <original document_number>, "issue_date": <original document_date>}` when `invoice.related_document_id` is set (the guarded emission; `None` otherwise). The `invoice.related_document` access is one lazy FK walk — bounded and line-count-independent (the P29 discipline holds; the fetch site optionally gains `select_related("related_document")` on the credit-note path).
- **The generator:** `_create_billing_reference` emits `cac:BillingReference/cac:InvoiceDocumentReference/cbc:ID` (+ `cbc:IssueDate` when present) on the credit-note path only, positioned after the currency block and before the supplier party (the UBL 2.1 element order: …TaxCurrencyCode, PricingCurrencyCode, …, OrderReference, **BillingReference**, DespatchDocumentReference, …, AccountingSupplierParty…).
- **The XSDs:** `ubl-CommonAggregateComponents-2.xsd` gains the `BillingReference` element (→ `InvoiceDocumentReference` with `cbc:ID` 1..1 + `cbc:IssueDate` 0..1 — the PINT binding shape); `ubl-CreditNote.xsd` gains `<xs:element ref="cac:BillingReference" minOccurs="0"/>` in the true sequence position. The Invoice XSD stays untouched (the repo's invoice path never emits the element — the minimal honest shape; registered if self-billing ever grows it).
- **The Schematron pin:** a NEW `PINT-SG-REFERENCE` pattern with rule **BR-SG-07** (the repo's own next ID in the BR-SG series): `every ublcn:CreditNote root must carry cac:BillingReference/cac:InvoiceDocumentReference/cbc:ID`. Sound because the service layer enforces `related_document_id` unconditionally on both credit-note types (verified in source: the `create_document` atomic block calls `_validate_credit_note_reference` for `SALES_CREDIT_NOTE` and `PURCHASE_CREDIT_NOTE`); scoped to the CreditNote root only (invoices unaffected). The rule's rationale documented in the artefact (IRAS invoicing-customers "must show"; the InvoiceNow e-Tax Guide §11.6 "should indicate"; the repo's own P14/H-4 DB contract).
- **The PDF:** the info section gains the reference block for credit notes whose `related_document` is set ("Original Invoice: INV-00001 · 2026-01-01"); the heading renders "CREDIT NOTE" for the credit-note types (replacing the raw enum). The context builder gates the `related_document` read on the credit-note types (invoice PDFs keep their exact query count — the P29 gates hold).

### Low

**BE-P37-L1 — the `cbc:Note` emission gap (the BR-111-GST-SG reason note).**
The mapper drops `notes`; the generator emits no `cbc:Note`. **Fix:** the mapper carries `"note": invoice.notes or None`; the generator emits `cbc:Note` (guarded, when non-empty) on BOTH paths in the true UBL position (between `DueDate` and `DocumentCurrencyCode`); both root XSDs declare `cbc:Note` (0..1 — the repo emits at most one). Byte-identical for documents with empty notes (the guarded omission — every existing fixture that carries no note keeps its exact bytes; the demo documents carry notes='' → unchanged).

**DOC-P37-L2 — the docs truths roll forward with the sprint** (the standing DOC-L pattern): README badge/counts + the P37 milestone, CLAUDE 2.37.0 → 2.38.0, AGENTS header + the P37 lesson (the data-layer-guarantee-vs-presentation-layer-truth class), SKILL 2.23.0 → 2.24.0, PAD 3.26.0 → 3.27.0, DEPLOYMENT.md (the header re-verification line), the API guide v3.9.0 → v3.10.0 (the credit-note reference contract documented: the emitted BillingReference + the BR-SG-07 validation rule + the PDF presentation), ci.yml (the header counts), the worklog + the session-72 log.

## 3. The execution plan (phases, TDD)

### Phase 1 — RED: the two new specs

| Task | Test (RED first) |
|---|---|
| T1 | **The reference gate:** NEW `apps/peppol/tests/test_credit_note_reference_p37.py` (~13 gates) — (i) the `.sch` declares the `PINT-SG-REFERENCE` pattern with the BR-SG-07 role (RED: absent); (ii) the MAPPER emits `billing_reference` for a credit note with `related_document` set (number + issue date; the mock-document convention from the P36 mapper spec); (iii) the mapper omits it when `related_document_id` is None (an invoice payload); (iv) the generated credit-note XML carries `cac:BillingReference/cac:InvoiceDocumentReference/cbc:ID` == the original number (RED: the element is absent); (v) the emitted `cbc:IssueDate` equals the original's issue date; (vi) the full validation path: the generated credit note (with the reference) validates CLEAN through `validate_credit_note_xml` (XSD accepts the new element — RED: on the base tree the reference is absent so the clean-document assertion fails on the reference check); (vii) a hand-built credit note WITHOUT `BillingReference` FAILS with BR-SG-07 named (RED: passes clean — the gap); (viii) a hand-built credit note WITH the reference passes; (ix) an INVOICE without BillingReference still passes (the rule must not fire on the Invoice root); (x) the real-DB demo credit note round-trip (mapper → generator → validator) carries the reference and validates clean; (xi) the PDF: a credit note's rendered HTML carries the original invoice number (RED: absent); (xii) the PDF heading renders "CREDIT NOTE" for SALES_CREDIT_NOTE (RED: "SALES_CREDIT_NOTE"); (xiii) the invoice PDF control: no reference block, the heading unchanged (TAX INVOICE / the type code as before). |
| T2 | **The note gate:** NEW `apps/peppol/tests/test_note_emission_p37.py` (~6 gates) — (i) the mapper carries `note` from `invoice.notes`; (ii) the generated XML carries `cbc:Note` when notes is non-empty, on the invoice path (RED: absent); (iii) the same on the credit-note path; (iv) NO `cbc:Note` when notes is empty (the guarded omission — byte-stability for the existing fixtures); (v) the full validation path accepts the Note element on both roots (the XSD declarations); (vi) the note text round-trips exactly (no truncation, no escaping artefacts). |

### Phase 2 — GREEN: the fixes

| Task | Fix | Verification |
|---|---|---|
| T3 | **The mapper:** `xml_mapping_service.py` — the `billing_reference` block (guarded on `related_document_id`) + `"note": invoice.notes or None`. | T1 (ii)/(iii); T2 (i) |
| T4 | **The generator:** `xml_generator_service.py` — `_create_billing_reference` (the credit-note path, the UBL position) + the guarded `cbc:Note` emission on both paths (between DueDate and the currency block). | T1 (iv)/(v); T2 (ii)-(iv) |
| T5 | **The XSDs:** `ubl-CommonAggregateComponents-2.xsd` (the BillingReference/InvoiceDocumentReference shape) + `ubl-CreditNote.xsd` (the sequenced ref) + both root XSDs (`cbc:Note` 0..1). | T1 (vi); T2 (v) |
| T6 | **The Schematron:** `PINT-UBL-validation.sch` — the `PINT-SG-REFERENCE` pattern (BR-SG-07, the CreditNote-scoped rule, the documented rationale). | T1 (i)/(vii)-(ix) |
| T7 | **The PDF:** `invoice_pdf.html` — the credit-note reference block + the "CREDIT NOTE" heading; `document_service.py` `_get_pdf_context` — the credit-note-gated `related_document` context entry. | T1 (xi)-(xiii) |
| T8 | **The fixture truth:** the three synthetic credit-note mapped-data builders (`test_credit_note_completeness_p34.py`, `test_schematron_business_rules_p35.py`, `test_schematron_arithmetic_rules_p36.py`) gain the `billing_reference` key (the honest mapper shape — every credit note the service creates carries it; the P36 USD-fixture precedent). | the P34/P35/P36 suites green |
| T9 | **The full backend suite** — every existing pin holds. | `pytest --reuse-db --no-migrations -q` — expect **1114 + the new-gate count** passed, 0 failed, 5 skipped |

### Phase 3 — the full gate matrix + the screenshots + the live contracts

1. The complete gate set on the remediated tree (both backends restarted on the remediated code — the `--noreload` lesson): backend pytest · vitest **698/698 (85 files)** (web tree untouched) · `tsc` 0 · whole-tree `eslint` 0E/0W · live `test:e2e:full` **43/43** · `rls_smoke` **13/13** · `mobile-nav-audit.js` **17/17** (the forty-third settlement) · the `translate` probe re-PASS · `build:server` green + `prod-csp-smoke.js` 5/5 · `make lint-mechanical` exit 0 · the production ruff count stays **148** / tests **73** (the new specs clean by construction — line-length ≤ 100, no touched lint class).
2. **The live contract re-verification (with the DELIBERATE byte change documented):** on the demo substrate — the credit-note XML from the REAL demo credit note (CN-00001) carries `cac:BillingReference/cac:InvoiceDocumentReference/cbc:ID` = INV-00001 + the issue date and validates clean (`is_valid=True`, schema=0, schematron=0); the invoice XML on a real document is byte-identical to the P36 bytes (the guarded omissions — notes empty, no invoice-path BillingReference); the credit-note PDF renders the reference block + the heading; a reference-stripped control fails with BR-SG-07 named.
3. Screenshots: 8 DOM-verified captures (`docs/screenshots/248-255_*_session72.png`, md5-unique + non-blank pixel-verified, the session-70 capture conventions) — the P37 surfaces featured (the invoices list + the credit-note-adjacent surface if reachable through the API-driven UI), plus the standing set (the banking payments, the reports trial-balance, the ledger, the dashboard, the mobile drawer closed/open).
4. The `.env.example` truth verification (the config-readers sweep re-run; no new env vars expected — every fix reads DB fields and code artefacts, not the environment).

### Phase 4 — the docs truth pass

| Doc | Update |
|---|---|
| README.md | the badge/test arithmetic, the status-table rows, the P37 milestone section |
| CLAUDE.md | version 2.37.0 → 2.38.0, the status block, the P37 milestone block |
| AGENTS.md | the header gate row, the P37 lesson (the data-layer-guarantee-vs-presentation-layer-truth class — a reference the DB enforces that the emitted artefacts drop is a compliance gap the receiver feels) |
| ledgersg_SKILL.md | the quick-ref numbers, version 2.23.0 → 2.24.0 |
| Project_Architecture_Document.md | the test-count rows, version 3.26.0 → 3.27.0 |
| docs/DEPLOYMENT.md | the header re-verification line (session 72 / P37 — the live stack verified against the guide this session); any drift found corrected |
| API_CLI_Usage_Guide.md | v3.9.0 → v3.10.0: the credit-note reference contract documented (the emitted BillingReference on the credit-note XML; the BR-SG-07 validation rule + its failure message; the reason-note emission; the PDF presentation) |
| worklog.md | the session-72 entry |
| docs/session_72.md | the session log |

## 4. Deferred register (updated, carried forward)

**Fixed this sprint (removed from the register):** the credit-note original-invoice reference gap (the BillingReference wiring + the Schematron pin + the PDF presentation); the `cbc:Note` emission gap.

**Still deferred (with rationale, unchanged unless noted):**
- **The ruff semantic batch — 148 production findings** (unchanged this sprint unless the edits touch a lint class — they should not): UP045/UP006/UP007/UP035×105 (typing modernization; the mypy-gate conversation — mypy itself carries 1491 errors — stays the registered precondition), E501×38 + `ruff format` (160 files would reformat — the `make format` axis), S110×4 (the verified fail-closed XSD loads), N818×1 (the LedgerSGException rename — touches every importer; its own reviewed pass).
- **The tests/-tree residual — 73 findings** (E501×73 — the format axis).
- **The `unit_code` modeling gap (NEW, registered):** the mapper hardcodes `"EA"` (UN/EDIFACT "Each") because `document_line` carries no unit column — a schema decision (a `unit_code` column + mapper thread + XSD vocabulary) to register for its own sprint if per-line units ever matter; the IRAS/PINT surfaces accept EA today.
- **BR-CO-11/12:** the document-level allowance/charge arithmetic — N/A today (the generator emits neither element); when the mapper grows them, the BR-CO-13 rule must widen to the general form.
- **BR-CO-18:** "at least one VAT breakdown" — a deposit-only document legitimately carries zero tax subtotals; register until the deposit-only document question is settled.
- **The Invoice-path BillingReference declaration (NEW, registered):** the Invoice XSD does not declare `cac:BillingReference` (the repo's invoice path never emits it); if self-billing or invoice-level correction references ever grow, the declaration + rules ship with the feature.
- **The `/accounts/search/` limit-contract migration; the capped-default flip; the audit-log INSERT policy (DDL); BE-L3/BE-L4 locking; the CSV errors[] strings; dead-letter design; UEN checksum; the NULL-context SELECT tradeoff; H-05b models; PaymentsTab prefill; the TanStack incompatibility; the membership-cache window; the P20-era FE-M2/M3 designs; CI hardening (the mypy gate); the version-story reconciliation** — the P21–P36 deferred registers carry forward unchanged.

## 5. Acceptance criteria

- The two RED specs (executed): T1/T2 RED on the base tree for exactly the right reasons (the BillingReference absent from the generated XML; the reference-less document passing the .sch clean; the mapper emitting no reference/note; the PDF without the reference block/heading), GREEN after the fixes.
- The backend suite green (**1114 + the new-gate count** expected, 0 failed, 5 skipped); no frontend change; the web gates green at the standing ratchets.
- The live contract re-verification: the real demo credit note's XML carries the BillingReference (INV-00001 + the issue date) and validates clean; the invoice XML byte-identical to the P36 bytes; the reference-stripped control fails with BR-SG-07 named; the credit-note PDF renders the reference block + the heading.
- `make lint-mechanical` exit 0 (no lint class touched); the production ruff count stays **148**; the tests count stays **73** (the new specs clean by construction — line-length ≤ 100).
- `skills/` untouched by code checks; `git status` shows only the intended files.
- Plan + report saved under `docs/` in the `REMEDIATION_*_P37*` convention; the session log `docs/session_72.md`; the worklog updated; 8 pixel-verified screenshots (248-255).

## 6. Open decisions (resolved with judgment)

- **BR-SG-07 as a hard assert (not a warning):** the repo's own service layer enforces `related_document_id` unconditionally on both credit-note types (verified in source — the atomic create block), so the rule can never false-reject a document this system creates; the synthetic fixtures gain the honest shape (the P36 USD-fixture precedent). A warning-class posture would leave the transmission gateway silent on a missing reference the DB promises.
- **The Invoice XSD stays BillingReference-free:** the invoice path never emits the element; declaring it would advertise a shape the generator never produces (the minimal honest XSD). Registered for the future feature.
- **`cbc:Note` on BOTH paths (not credit-note-only):** BT-22 (invoice note) is a legal optional element on the invoice too; the guarded omission keeps every notes-empty document byte-identical; the reason-note rule (BR-111-GST-SG) is credit-note-flavoured but the note element itself is generic — emitting it on both paths is the simpler, honest shape.
- **`cbc:Note` 0..1 (not 0..unbounded):** the repo's data model carries ONE notes field per document — the XSD mirrors the emitter's truth (the P34 single-purpose-XSD philosophy).
- **The PDF read gating (credit-note types only):** reading `document.related_document` unconditionally would add a lazy FK query to every invoice PDF too; the type-gated context entry keeps the invoice PDF's query count exact (the P29 discipline).
- **No new e2e spec:** the reference truth is XML/PDF-level (pinned by the new backend specs); the browser surfaces render whatever the API sends (the P35/P36 precedent).
- **The UP batch / E501 + format axis / N818 / mypy gate stay out (again):** the registered preconditions are unchanged.
