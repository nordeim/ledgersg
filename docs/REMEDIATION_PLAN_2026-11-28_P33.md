# LedgerSG — Remediation Plan (P33 Sprint: The Currency-Truth Closure — The Peppol Amount currencyID Thread + The Reports/Account-Balance Denomination Truth)

**Date:** 2026-11-28 (session 64)
**Base commit:** `e8cce197` (main — post-P32 + the session-63 log)
**Method for execution:** TDD (RED → GREEN → full gate) for every behavioural change (three new specs, each RED on the base tree); `skills/` excluded from all checks/tests/compilation; **no schema changes** (v1.2.2 carries forward); **no frontend component changes** (the web tree consumes whatever currency the backend sends — the reports hook already types `currency: string`, the shared `formatMoneyWithCurrency` already maps codes to symbols).
**Skills consulted:** `skills/skills-catalog.md` → `tdd` (the red→green loop), `code-review`/`code-review-checklist` (Mode C discipline), `debugging-and-error-recovery` (root-cause isolation on any RED surprise), `rootless-postgresql` (the PG environment — provisioned fresh this session via `docs/setup_pg_z.sh`), `agent-browser` (the live mobile-nav + translate probes — executed this session, §1), `nextjs16-tailwind4`/`tailwind-patterns` (consulted for the mobile-nav focus — re-settled clean this session, §1).

---

## 1. Audit inputs (this session's evidence)

- **Repo + docs truth pass:** fresh `git clone` (the workspace had been reset); full reads of `AGENTS.md`, `CLAUDE.md` v2.33.0, `README.md`, `Project_Architecture_Document.md` v3.22.0, `ledgersg_SKILL.md` v2.19.0, `worklog.md`, `docs/session_62.md`, `docs/session_63.md`, the P32 plan + report, `docs/Tailwind-V4-Validation-Report.md`.
- **The environment (provisioned fresh this session):** rootless **PG 17** installed via `docs/setup_pg_z.sh` (fresh data dir — the sandbox recycle had wiped the prefix); the `ledgersg` SUPERUSER role + `ledgersg_dev` + `test_ledgersg_dev` created; the v1.2.2 schema loaded into BOTH databases; **Redis 8** rootless on :6379; the backend venv rebuilt (`pip install -e ".[dev]"`, `manage.py check` green); the web tree `npm ci` (0 vulnerabilities; the persisted esbuild/unrs-resolver install-script approvals honoured); Playwright chromium re-provisioned for 1.58.2; the demo substrate bootstrapped via `scripts/bootstrap_demo_substrate_session40.sh` (36 ledger lines, 12 approved invoices, F5 computed).
- **The baseline reproduction (pre-change, this session — all gates exact):** backend `pytest --reuse-db --no-migrations -q` **1036P/0F/5S** (28.91s) · vitest **698/698 (85 files)** · `npx tsc --noEmit` **0 errors** · whole-tree eslint **0E/0W** · live `test:e2e:full` **43/43 (2.8m, first run)** · `rls_smoke.py` **13/13 as `ledgersg_app`** (the :8001 instance re-provisioned; the role's dev password reset to the schema default) · `mobile-nav-audit.js` **17/17** (the thirty-fourth settlement) · the dedicated Tailwind v4 `translate` probe (`scripts/translate-probe-session53.js`): **PASS** (7 mid-flight samples, `transitionProperty "transform, translate, visibility"`) · `npm audit` **0 across dev+prod** · `build:server` green + `prod-csp-smoke.js` **5/5** · `make lint-mechanical` exit 0 (the extended P32 class set) · the production ruff count **148** exact (UP045×45, E501×38, UP006×35, UP007×13, UP035×12, S110×4, N818×1) · the tests-tree count **73** exact (E501×73). **All documented gates reproduced exactly — the P32 state holds.**
- **The named focus — the mobile-nav verdict (thirty-fourth settlement):** **WORKING as expected; NO remaining TailwindCSS v4 bug on this surface.** The live probe re-verified the full contract at 375/800/1280 (toggle visible/operable, closed `visibility:hidden`, overlay present, the X hit target, no horizontal overflow, no console errors) and the `translate` probe re-sampled the slide mid-flight (7 intermediate values, the standalone `translate` property in `transitionProperty`) — the P23 fix (`transition-[transform,translate,visibility]` in `apps/web/src/components/layout/shell.tsx`) holds.
- **The standing test-suite task (user instruction: "add vitest and playwright test suite by modifying the respective config files in the repo"):** verified IN PLACE and current — `apps/web/vitest.config.ts` (jsdom, the setup file, the whole-suite + six per-glob coverage tiers) and `apps/web/playwright.config.ts` (chromium default, the live-suite serialisation contract, the E2E_API_URL gating, the pinned locale/timezone), driving **698 vitest specs (85 files) + 43 e2e specs (12 files)** — all green this session. This sprint's three new backend specs join the same suites.
- **The audit (Mode C) of the P32 slice** (commits `cac95db0`..`e8cce197`, hand-verified in source this session): the conftest placement holds (`tests/integration/conftest.py` carries `payment_fixture`; only the three function-level `_receive` imports remain — the documented companion-API contract); the service seams hold (no `reversal`/`old_status`/`fiscal_period` dead bindings); the per-class residual matches the register exactly; `make lint-mechanical` green — **0 new findings in the P32 slice**.
- **The fresh findings (this session's one-class-deeper sweep — the currency-truth class):** every surface that reports or transmits a monetary amount was audited for what currency it claims:
  - **The Peppol amount-currency truth (the headline):** `apps/peppol/services/xml_mapping_service.py` maps the document's own currency (`invoice.currency or "SGD"`) into `DocumentCurrencyCode`/`TaxCurrencyCode`, but `apps/peppol/services/xml_generator_service.py` hardcodes `currencyID="SGD"` on **all 11 amount elements** (`TaxAmount` ×3, `TaxableAmount`, `LineExtensionAmount`, `TaxExclusiveAmount`, `TaxInclusiveAmount`, `PayableAmount`, `PrepaidAmount`, the line `LineExtensionAmount`, `PriceAmount`). A USD- or EUR-denominated document transmits **internally inconsistent UBL** — `DocumentCurrencyCode=USD` beside `currencyID="SGD"` amounts — a Peppol PINT-SG validation/compliance hazard on the InvoiceNow path. The existing generator tests (`apps/peppol/tests/test_xml_generator_service.py`) build every payload with `"currency": "SGD"` — the blind-spot class this repo's sprints keep closing (the fixture masks the hardcode).
  - **The financial-reports denomination truth:** `apps/reporting/views.py` hardcodes `"currency": "SGD"` in all three report responses (trial_balance line ~157, profit_loss ~213, balance_sheet ~279) while the ledger they aggregate is denominated in the **org's `base_currency`** (`CHAR(3)`, default SGD, settable — `apps/core/models/organisation.py:166`). The PDF template already renders the truthful value (`{{ org.base_currency }}` in `invoice_pdf.html:179`) — the API responses are the untruthful surface.
  - **The account-balance currency truth:** `apps/coa/views.py:190` returns `"currency": "SGD"` behind a literal `# TODO: Get from org settings` while the Account model carries its own `currency` field (`apps/core/models/account.py:39`) — the TODO is answerable today.
  - **Verified truthful (no change):** the invoice PDF (`org.base_currency`), the invoicing serializers (the document's real `currency` field), the banking services (`data.get("currency", "SGD")` — the caller's value wins), `tax_currency: "SGD"` in the Peppol mapping (IRAS GST is accounted in SGD even for foreign-currency invoices — the correct statutory posture, kept as the documented decision), the frontend `formatMoneyWithCurrency` (code→symbol map, already consumes any ISO code).

**Combined findings (this session's audit): 0 Critical / 1 High / 2 Medium / 0 Low.**

## 2. Findings (verified, with evidence anchors)

### High

**BE-P33-H1 — the Peppol amount-currency truth: the document currency never reaches the amount elements' `currencyID` attributes (11 hardcoded sites).**
Three concrete harms:
1. **A non-SGD document transmits non-conformant UBL** — `DocumentCurrencyCode` and every amount `currencyID` disagree; a Peppol access point validating PINT-SG can reject or, worse, accept and mis-render the document.
2. **The hardcode is invisible to the suite** — every existing generator test uses SGD fixtures, so the register cannot see the defect (the same fixture-masks-the-bug class as P1/A-2).
3. **The truth is one seam away** — the mapped data already carries `"currency"`; the generator just never threads it past the header.

**Fix:** thread `mapped_data["currency"]` (falling back to `"SGD"`) into `_create_tax_total`, `_create_monetary_total`, and `_create_invoice_line` — each gains a `currency` parameter; every `.set("currencyID", "SGD")` site uses it. The `generate_credit_note_xml` path emits no amount elements (header-only — the pre-existing registered design) and needs no change. Byte-identical for SGD documents (the default substrate); truthful for every other denomination.

### Medium

**BE-P33-M1 — the financial-reports denomination truth: the three report views hardcode `"currency": "SGD"` instead of the org's `base_currency`.** The trial balance, P&L and balance sheet aggregate the org's ledger — whose denomination IS `base_currency`. A USD-based org (representable: CHAR(3), settable at creation and via the typed PATCH allowlist) receives reports claiming SGD. **Fix:** each view reads the org's `base_currency` (one indexed-PK `values_list` query per report request — negligible beside the report's own aggregates) and renders it. Byte-identical for SGD orgs.

**BE-P33-M2 — the account-balance currency truth: `AccountBalanceView` hardcodes `"currency": "SGD"` behind a TODO while the Account model carries its own `currency` field.** The balance is the account's own balance — the account's currency is the truthful denomination. **Fix:** return `account.currency`. Byte-identical for SGD accounts (the model default); the TODO retires.

### Low

**DOC-P33-L1 — the docs truths roll forward with the sprint** (the standing DOC-L pattern): README badge/counts + the P33 milestone, CLAUDE 2.33.0 → 2.34.0, AGENTS header + the P33 lesson (the fixture-currency blind-spot class), SKILL 2.19.0 → 2.20.0, PAD 3.22.0 → 3.23.0, DEPLOYMENT.md (the header re-verification line + a full fresh-host walkthrough re-validation against the current tree — this session provisioned the entire stack from scratch through it), the API guide (v3.5.0 → v3.6.0: the three currency fields documented with their truth semantics — a contract-visible change for non-SGD orgs), `.env.example`s re-verified (no new env vars expected), the worklog + the session-64 log.

## 3. The execution plan (phases, TDD)

### Phase 1 — RED: the three currency-truth specs

| Task | Test (RED first) |
|---|---|
| T1 | **The Peppol currencyID gate:** NEW `apps/peppol/tests/test_xml_currency_truth_p33.py` — builds a mapped payload with `"currency": "USD"` (the mapper's own shape, a minimal valid invoice: supplier/customer/tax_totals/monetary_totals/one line), generates the XML, parses it with lxml, and asserts **every** amount element carries `currencyID="USD"` (TaxAmount, TaxableAmount, the monetary totals, the line amounts, PriceAmount) AND `DocumentCurrencyCode == "USD"`. RED on the base tree: the 11 sites read "SGD". |
| T2 | **The reports denomination gate:** NEW `apps/reporting/tests/test_report_currency_truth_p33.py` — an org with `base_currency="USD"` + seeded CoA; GET the three report endpoints; assert `"currency": "USD"` in each response. RED on the base tree: all three read "SGD". |
| T3 | **The account-balance currency gate:** NEW `apps/coa/tests/test_account_balance_currency_p33.py` — an account created with `currency="USD"`; GET the balance endpoint; assert `"currency": "USD"`. RED on the base tree: reads "SGD". |

### Phase 2 — GREEN: the fixes

| Task | Fix | Verification |
|---|---|---|
| T4 | **The H1 thread:** `generate_invoice_xml` extracts `currency = mapped_data.get("currency") or "SGD"` and passes it to `_create_tax_total(tax_data, currency)`, `_create_monetary_total(totals_data, currency)`, `_create_invoice_line(line_data, currency)`; all 11 `.set("currencyID", "SGD")` sites become `.set("currencyID", currency)`. | T1 GREEN; the existing generator suite green (SGD fixtures — byte-identical output); the transmission-service suite green |
| T5 | **The M1 truth:** the three report views read `Organisation.objects.values_list("base_currency", flat=True).get(id=org_id)` once per request and render it in the `currency` field. | T2 GREEN; the existing financial-reports suite green (SGD orgs — byte-identical) |
| T6 | **The M2 truth:** `AccountBalanceView` returns `account.currency`. | T3 GREEN; the existing coa suite green |
| T7 | **The full backend suite** — every existing pin holds. | `pytest --reuse-db --no-migrations -q` **1039P/0F/5S** expected (+3 the new gates) |

### Phase 3 — the full gate matrix + the screenshots

1. The complete gate set on the remediated tree (both backends restarted on the remediated code — the `--noreload` lesson): backend `pytest` **1039P/0F/5S** · vitest **698/698 (85 files)** (web tree untouched) · `tsc` 0 · whole-tree `eslint` 0E/0W · live `test:e2e:full` **43/43** · `rls_smoke` **13/13** · `mobile-nav-audit.js` **17/17** (the thirty-fifth settlement) · the `translate` probe re-PASS · `npm audit` **0** (dev+prod) · `build:server` green + `prod-csp-smoke.js` **5/5** · **the live API contract re-verification** (the reports endpoints + the account-balance endpoint on the SGD demo substrate → byte-identical `"currency": "SGD"`; a Peppol XML round-trip on the demo substrate → byte-identical SGD output; the not-found 404 + a typed-400 body — byte-stable).
2. Screenshots: 8 DOM-verified captures (`docs/screenshots/216-223_*_session64.png`, md5-unique + non-blank pixel-verified, the session-62 capture conventions) — the P33 headline surfaces featured (the reports trial-balance tab + the banking payments tab — the denomination surfaces), plus the standing set (the invoices list, the ledger, the dashboard, the quotes, the mobile drawer closed/open).
3. The `.env.example` truth verification (the config-readers sweep re-run; no new env vars expected — the currency fixes read the DATABASE, not the environment).

### Phase 4 — the docs truth pass

| Doc | Update |
|---|---|
| README.md | the badge/test arithmetic (backend 1039), the status-table rows, the P33 milestone section |
| CLAUDE.md | version 2.33.0 → 2.34.0, the status block, the P33 milestone block |
| AGENTS.md | the header gate row, the P33 lesson (the fixture-currency blind spot — a test fixture at the default value masks a hardcode at the same value) |
| ledgersg_SKILL.md | the quick-ref numbers, version 2.19.0 → 2.20.0 |
| Project_Architecture_Document.md | the test-count rows, version 3.22.0 → 3.23.0 |
| docs/DEPLOYMENT.md | the header re-verification line (session 64 / P33 — the guide followed end-to-end on a FRESH host this session: every step executed from the sandbox reset to the green matrix); any drift found during the walkthrough corrected |
| API_CLI_Usage_Guide.md | v3.5.0 → v3.6.0: the reports + account-balance `currency` fields documented with their truth semantics (`org.base_currency` / the account's own currency; byte-identical for the SGD default); the Peppol amount `currencyID` truth noted on the InvoiceNow section |
| worklog.md | the session-64 entry |
| docs/session_64.md | the session log |

## 4. Deferred register (updated, carried forward)

**Fixed this sprint (removed from the register):** the Peppol amount-currency hardcode (BE-P33-H1 — 11 sites); the financial-reports denomination hardcode (BE-P33-M1 — 3 sites); the account-balance currency TODO (BE-P33-M2 — 1 site).

**Still deferred (with rationale, unchanged unless noted):**
- **The ruff semantic batch — 148 production findings** (unchanged this sprint — the currency fixes touch no lint class): UP045/UP006/UP007/UP035×105 (typing modernization; the mypy-gate conversation — mypy itself carries 1491 errors — stays the registered precondition), E501×38 + `ruff format` (160 files would reformat — the `make format` axis), S110×4 (the verified fail-closed XSD loads), N818×1 (the LedgerSGException rename — touches every importer; its own reviewed pass).
- **The tests/-tree residual — 73 findings** (E501×73 — the format axis).
- **The credit-note XML minimality** (NEW, registered this sprint): `generate_credit_note_xml` emits header-only UBL (no tax/monetary totals, no lines) — a pre-existing design; the transmission path works and is tested, but a full PINT-SG credit note would carry the amounts. Its own reviewed pass if taken.
- **The ISO-4217 validation of `base_currency`/`currency` inputs** (NEW, registered this sprint): CHAR(3) with no code-list check — a typo like "USDD" is rejected only by the length validators. A shared ISO-4217 allowlist is the clean closure; its own pass (it touches org creation + PATCH + the banking serializers).
- **The `/accounts/search/` limit-contract migration** — unchanged (verified again: capped + typed; no frontend consumer).
- **The capped-default flip; the audit-log INSERT policy (DDL); BE-L3/BE-L4 locking; the CSV errors[] strings; dead-letter design; UEN checksum; the NULL-context SELECT tradeoff; H-05b models; PaymentsTab prefill; the TanStack incompatibility; the membership-cache window; the P20-era FE-M2/M3 designs; CI hardening (the mypy gate); the version-story reconciliation** — the P21–P32 deferred registers carry forward unchanged.

## 5. Acceptance criteria

- The three RED specs (executed): T1/T2/T3 RED on the base tree for exactly the right reason (the hardcoded "SGD"), GREEN after the fixes.
- The backend suite green (**1039P/0F/5S** expected — +3 the new gates); no frontend change; the web gates green at the standing ratchets.
- The live contract re-verification: on the SGD demo substrate the reports/account-balance/Peppol outputs are **byte-identical** (the SGD default path never changes); the currency fields documented in the API guide.
- `make lint-mechanical` exit 0 (no lint class touched); the production ruff count stays **148**; the tests count stays **73** (the new specs are clean by construction — line-length ≤ 100).
- `skills/` untouched by code checks; `git status` shows only the intended files.
- Plan + report saved under `docs/` in the `REMEDIATION_*_P33*` convention; the session log `docs/session_64.md`; the worklog updated; 8 pixel-verified screenshots (216-223).

## 6. Open decisions (resolved with judgment)

- **Thread the currency as a parameter, not instance state:** the generator methods stay pure functions of their arguments (`_create_tax_total(tax_data, currency)`) — an instance attribute would couple the service to one document per instantiation and invite cross-document bleed in any future reuse. The parameter list grows by one; the call sites are all inside the two generate methods.
- **`or "SGD"` fallback at the extraction point:** the mapper already defaults (`invoice.currency or "SGD"`), but the generator is a public seam (the transmission service calls it directly with mapped data) — the defensive default keeps a hand-built payload honest without inventing a validation layer the mapper already owns.
- **`tax_currency` stays "SGD"** (the mapping service): IRAS GST is accounted in SGD even for foreign-currency invoices — the statutory posture. Documented here as the decision, not changed.
- **The reports read the org per request (no cache):** one indexed-PK query per report request; the report aggregates dominate. A cache would add invalidation surface for zero measurable gain at this scale.
- **The account's own currency (not the org's base) for the balance view:** the balance is the account's balance; `Account.currency` is the model's own truth. For the (rare) mixed-denomination CoA this is the honest answer; the ledger-level reports stay on `base_currency` (the ledger's denomination).
- **No new e2e spec:** the currency fixes are API-level truths pinned by the three new backend specs; the browser surfaces render whatever the API sends (the reports client doesn't render currency; the PDF already used `org.base_currency`). The live re-verification covers the byte-stability claim.
- **The credit-note XML minimality is registered, not fixed:** expanding the credit-note UBL to full PINT-SG (tax totals + lines) is a compliance feature, not a truth fix — its own sprint with the Peppol validation suite extended.
- **The UP batch / E501 + format axis / N818 / mypy gate stay out (again):** the registered preconditions are unchanged.
