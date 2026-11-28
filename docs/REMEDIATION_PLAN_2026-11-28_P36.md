# LedgerSG — Remediation Plan (P36 Sprint: The Peppol Arithmetic Truth — The BR-CO Calculation Rules + The Tax-Currency/Percent Truth)

**Date:** 2026-11-28 (session 70)
**Base commit:** `bda0dceb` (main — post-P35 + the session-69 log)
**Method for execution:** TDD (RED → GREEN → full gate) for every behavioural change (two new specs, each RED on the base tree); `skills/` excluded from all checks/tests/compilation; **no schema changes** (v1.2.2 carries forward); **no frontend component changes** (the web tree consumes whatever the backend sends; the validation contract gains arithmetic errors in the same shapes).
**Skills consulted:** `skills/skills-catalog.md` → `tdd` (the red→green loop, the vertical-slice rule), `code-review`/`code-review-checklist` (Mode C discipline — findings separated from fixes, severity taxonomy), `debugging-and-error-recovery` (root-cause isolation — every finding reproduced live before any fix), `rootless-postgresql` (the PG environment — verified running this session), `agent-browser` (the live mobile-nav + translate probes — re-executed this session, §1), `nextjs16-tailwind4`/`tailwind-patterns` (consulted for the mobile-nav focus — re-settled clean this session, §1).

---

## 1. Audit inputs (this session's evidence)

- **Repo + docs truth pass:** `git pull` to `bda0dceb` (the session-69 narration log); full reads of `AGENTS.md`, `CLAUDE.md` v2.36.0, `README.md`, `Project_Architecture_Document.md` v3.25.0, `ledgersg_SKILL.md` v2.22.0, `worklog.md`, `docs/session_68.md`, `docs/session_69.md`, the P35 plan + report, `docs/Tailwind-V4-Validation-Report.md`.
- **The environment (survived the sandbox recycle — verified, not re-provisioned):** rootless **PG 17** on :5432 (both databases present, the v1.2.2 schema — 45 tables across the 8 schemas; the demo substrate accumulated across the e2e runs: 101 orgs, 37 journal entries, 1308 accounts, 35 documents), **Redis 8** on :6379, the backend venv, the web tree `node_modules`. The dev servers had been reaped by the sandbox (the documented behavior — background children die between tool calls; the live gates ran with the backends started INSIDE the same invocation, the session-66 lesson).
- **The baseline reproduction (pre-change, this session — all gates exact):** backend `pytest --reuse-db --no-migrations -q` **1089P/0F/5S** (30.97s) · vitest **698/698 (85 files)** · `npx tsc --noEmit` **0 errors** · whole-tree eslint **0E/0W** · live `test:e2e:full` **43/43 (2.3m)** · `rls_smoke.py` **13/13 as `ledgersg_app`** (the :8001 instance) · `mobile-nav-audit.js` **17/17** (the fortieth settlement) · the dedicated Tailwind v4 `translate` probe: **PASS** · `make lint-mechanical` exit 0 · the production ruff count **148** exact · the tests-tree count **73** exact. **All documented gates reproduced exactly — the P35 state holds.**
- **The named focus — the mobile-nav verdict (fortieth settlement):** **WORKING as expected; NO remaining TailwindCSS v4 bug on this surface.** The live probe re-verified the full contract and the `translate` probe re-sampled the slide — the P23 fix (`transition-[transform,translate,visibility]` in `apps/web/src/components/layout/shell.tsx`) holds.
- **The standing test-suite task (vitest + playwright configs):** verified IN PLACE and current — `apps/web/vitest.config.ts` (jsdom, the setup file, the whole-suite + per-glob coverage tiers) and `apps/web/playwright.config.ts` (chromium default, the live-suite serialisation contract, the E2E_API_URL gating) driving **698 vitest specs (85 files) + 43 e2e specs** — all green this session.
- **The audit (Mode C) of the P35 slice** (commits `731f173d`..`42aeb76e`, hand-verified in source this session): the `.sch` rewrite holds (the true `dsdl` namespace, the `xslt` binding, the four namespace bindings, the five rules with IDs); the wiring holds (the load with the hardened parser + the fail-closed contract, the SVRL extraction as message+location dicts, the call in BOTH validate methods, `is_valid` folding both error lists); the formatter holds (`_format_validation_error_messages` at the transmission failure seam); the P35 specs green in the suite — **0 new findings in the P35 slice**.
- **The fresh findings (this session's audit — the registered arithmetic axis + the P33-class sweep of every remaining currency/rate surface):**

  - **(a) The arithmetic truth gap (the registered #1 P35-deferred candidate, now reproduced):** the `.sch` carries NO calculation rules — the XSD enforces structure, the P35 rules enforce the currency consistency and the presence floors, but NOTHING checks that the document's totals agree with its own lines. Reproduced via live probes on the real demo substrate: a real APPROVED invoice with `TaxInclusiveAmount` tampered +500.00 passes validation CLEAN (`is_valid=True`, schematron=0); the same document with one line's `LineExtensionAmount` tripled passes CLEAN. A real Peppol access point adds the EN 16931 BR-CO calculation rules on top of the XSD; without them LedgerSG's validation verdict overstates what was checked — a corrupted or tampered document (the transmission pipeline's own defensive purpose) sails through.
  - **(b) The TaxCurrencyCode hardcode (a P33-class survivor, found by sweeping every remaining currency surface):** `xml_mapping_service.py:67` hardcodes `"tax_currency": "SGD"`, and the generator emits `cbc:TaxCurrencyCode` with it on BOTH paths. For a non-SGD document the emitted UBL is internally inconsistent: `DocumentCurrencyCode=USD` beside `currencyID="USD"` amounts and `TaxCurrencyCode=SGD` — the exact P33 hazard class (a header that disagrees with the amounts), missed by P33's amount sweep and unpinned by any test (the P33 USD fixture ITSELF carries `"tax_currency": "SGD"` — the default-value-fixture blind-spot class the P33 docstring names). BR-SG-06 does not cover it (TaxCurrencyCode is not an amount element). All 35 demo documents are SGD, so the live substrate masks it today — the code path is wrong for every non-SGD document.
  - **(c) The Percent float artifact (the rate-formatting truth):** `xml_generator_service.py:426` formats the tax-category Percent as `str(float(rate) * 100)`. For the 7% rate rows that exist in the demo DB (`TaxCode.rate = Decimal('0.0700')`), `float(Decimal('0.07')) * 100` = `7.000000000000001` — the emitted `cbc:Percent` carries a float artifact (a financial document whose stated tax rate is a 16-digit approximation of 7; some receivers flag or reject it; it is numerically ~7 so nothing in the current stack catches it). The DB rate rows today: 0.0000/0.0700/0.0800/0.0900 — the 7% row makes the artifact live-able, not hypothetical.

**Combined findings (this session's audit): 0 Critical / 2 High / 1 Low.**

## 2. Findings (verified, with evidence anchors)

### High

**BE-P36-H1 — the arithmetic truth gap: no BR-CO calculation rules in the business-rule layer (the registered candidate, reproduced).**
The EN 16931 calculation rules are the layer a real Peppol access point adds above the XSD. The repo's generator computes every total from the DB's NUMERIC(19,4) Decimals (`_recalculate_totals`: `total_excl` = Σ line amounts, `gst_total` = Σ line GST, `total_incl` = `total_excl + gst_total`; the mapper: `payable = total_incl − amount_paid`, `prepaid = amount_paid`; the tax subtotals: per-code sums over non-deposit lines, deposits being GST-exempt) — so the invariants HOLD BY CONSTRUCTION in the emitted XML, which is exactly why the missing validation layer is worth adding: it converts construction-truth into checked-truth (the tampered-total probe passes clean today).

**Fix (one .sch pattern, six rules, each pinned by a spec):**
- **BR-CO-10**: Σ line `LineExtensionAmount` == document `LineExtensionAmount` (both document paths).
- **BR-CO-13** (the repo's no-allowance/charge form): `TaxExclusiveAmount` == `LineExtensionAmount` — the generator emits no document-level allowances/charges, so the general rule reduces to this; the reduction is documented in the artefact.
- **BR-CO-15**: `TaxInclusiveAmount` == `TaxExclusiveAmount` + `TaxAmount` (the tax amount 0 when the element is absent — the generator can omit TaxTotal on a zero-tax document's hand-built payload).
- **BR-CO-16**: `PayableAmount` == `TaxInclusiveAmount` − `PrepaidAmount` (prepaid 0 when absent).
- **BR-CO-14**: `TaxTotal/TaxAmount` == Σ `TaxSubtotal/TaxAmount` (the deposit exemption makes this exact: deposit lines carry GST 0, so the non-deposit subtotal sums equal the document total).
- **BR-CO-17** (the per-line-rounding-honest form): per tax subtotal, |`TaxAmount` − `TaxableAmount` × `Percent`/100| ≤ 0.005 × (line count) + the quantization guard. The DB computes GST per line rounded to 2dp (IRAS cent-level rounding), so the category tax is a sum of per-line roundings, NOT a rounding of the category sum — a naive equality rule would false-reject legitimate documents (3 × 5.55 at 9%: per-line 0.50 + 0.50 + 0.50 = 1.50 vs 16.65 × 0.09 = 1.4985). The line-count-scaled bound is SOUND (never false-rejects: each per-line rounding contributes at most half a cent) and still catches gross tampering (the +0.02 probe fails). The Peppol-validator practice (document totals to the cent; BR-CO-17 within one currency unit) is coarser than this on the rate axis and stricter on the totals axis — this repo's form is grounded in ITS OWN rounding model, which is the honest choice.

**The XPath-1.0 precision conversation (the registered precondition, resolved):** XPath 1.0 `sum()` computes in IEEE doubles while the mapper emits NUMERIC(19,4) decimal strings. The resolution, prototype-validated 39/39 against the real generator output: (i) every construction-exact rule compares with the half-unit-of-the-last-decimal guard — both sides within 0.00005, which absorbs the double representation error for any document whose amounts are within double-exact range (≈ 9 × 10^11 — far above the NUMERIC(19,4) capacity a real document approaches) while still failing on any real disagreement (the smallest DB scale is 0.0001); (ii) absent elements are read via `sum(node-set)` (empty = 0), NOT via arithmetic on the element (a missing element in a multiplication yields NaN and silently fails every comparison — the prototype's first iteration caught exactly this); (iii) relative paths from `LegalMonetaryTotal` use `../` (the parent IS the document root; `../../` escapes it — the prototype's first iteration caught this too).

**BE-P36-H2 — the TaxCurrencyCode hardcode: a P33-class currency-truth survivor.**
The mapper hardcodes `"SGD"`; the generator emits it unconditionally. **Fix:** the mapper carries the document currency (`invoice.currency or "SGD"` — the tax IS computed in the document currency; there is no divergence in the data model), and the generator emits `cbc:TaxCurrencyCode` ONLY when it differs from the document currency (the UBL semantic: the element exists to declare a DIFFERENT tax currency; BT-6-style redundancy is noise). Net effect on emitted bytes: SGD documents lose the redundant element (XSD `minOccurs="0"` — verified on both root XSDs), non-SGD documents stop declaring a false SGD tax currency. The P33 USD fixture's own `"tax_currency": "SGD"` is corrected to the honest shape (the fixture docstring says "the mapper's own shape" — post-fix the mapper never emits a divergent tax currency).

### Low

**BE-P36-L1 — the Percent float artifact: the tax rate formatted through a float.**
`str(float(rate) * 100)` emits `7.000000000000001` for the live 7% rate rows. **Fix:** format through Decimal: `format((Decimal(str(rate)) * 100).normalize(), "f")` — deterministic, float-free, plain-notation ("9" for 0.09, "7" for 0.07, "8.75" for 0.0875, "0" for zero; the `f` format spec avoids normalize's `1E+2` trap for integral values). Tolerates both Decimal and float inputs (the hand-built test payloads carry floats).

**DOC-P36-L2 — the docs truths roll forward with the sprint** (the standing DOC-L pattern): README badge/counts + the P36 milestone, CLAUDE 2.36.0 → 2.37.0, AGENTS header + the P36 lesson, SKILL 2.22.0 → 2.23.0, PAD 3.25.0 → 3.26.0, DEPLOYMENT.md (the header re-verification line), the API guide v3.8.0 → v3.9.0 (the arithmetic validation contract + the two deliberate emitted-byte changes documented), ci.yml (the header counts), the worklog + the session-70 log.

## 3. The execution plan (phases, TDD)

### Phase 1 — RED: the two new specs

| Task | Test (RED first) |
|---|---|
| T1 | **The arithmetic-rules gate:** NEW `apps/peppol/tests/test_schematron_arithmetic_rules_p36.py` (~12 gates) — (i) the `.sch` loads as a real ISO-Schematron schema; (ii) a clean generated invoice passes with the arithmetic rules ON (`schematron_errors == []`); (iii) a clean generated credit note passes; (iv) the tampered-`TaxInclusiveAmount` document FAILS with BR-CO-15 (+BR-CO-16) named (RED today: passes clean — the gap); (v) the tampered line amount FAILS with BR-CO-10; (vi) the tampered subtotal tax FAILS with BR-CO-14 (+BR-CO-17); (vii) the tampered `PayableAmount` FAILS with BR-CO-16; (viii) the tampered `TaxExclusiveAmount` FAILS with BR-CO-13 (+BR-CO-15); (ix) the no-TaxTotal edge (TaxInclusive inconsistent) fails, the consistent twin passes; (x) the per-line-rounding case (3 × 5.55 at 9% → tax 1.50) PASSES the sound bound, the +0.02 tamper FAILS with BR-CO-17; (xi) the float-artifact Percent ("7.000000000000001") still passes BR-CO-17 (tolerance absorbs the 1e-15 deviation); (xii) a `PrepaidAmount`-carrying document reconciles (and the drifted twin fails). |
| T2 | **The tax-currency/Percent truth gate:** NEW `apps/peppol/tests/test_tax_currency_percent_truth_p36.py` (~9 gates) — (i) the MAPPER emits `tax_currency` == the document currency for a USD document (RED today: "SGD"); (ii) the generated USD document carries NO `cbc:TaxCurrencyCode` (equal → omitted; RED today: "SGD"); (iii) a hand-built payload whose tax currency DIFFERS emits the element with the differing code (the UBL semantic preserved for future divergence); (iv) an SGD document omits it too (the redundancy retired); (v) the generated Percent for the 0.07 rate is exactly "7" (RED today: the float path; tested through the generator with a 0.07 category); (vi) the 0.09 rate formats as "9"; (vii) the 0.0875 rate formats as "8.75"; (viii) the zero rate formats as "0"; (ix) the XSD still accepts both changed outputs (the full validation path green on the changed bytes). |

### Phase 2 — GREEN: the fixes

| Task | Fix | Verification |
|---|---|---|
| T3 | **The H1 artefact:** `PINT-UBL-validation.sch` gains the `PINT-SG-ARITHMETIC` pattern — the six rules with IDs (BR-CO-10/13/14/15/16/17), each carrying a human message with the rule ID; the deliberate omissions documented in the artefact (BR-CO-11/12 N/A — the generator emits no document-level allowances/charges; BR-CO-18 registered — a deposit-only document legitimately carries no subtotals; the sound-bound rationale for BR-CO-17). | T1 (i)-(xii) GREEN; the P35 arithmetic-consistent fixtures still green (the P33/P34/P35 fixtures all carry 1000/90/1090-consistent totals — verified this session) |
| T4 | **The H2 mapper:** `xml_mapping_service.py` — `"tax_currency": invoice.currency or "SGD"` (the document currency; the tax is computed in it). | T2 (i) GREEN |
| T5 | **The H2+L1 generator:** `xml_generator_service.py` — the TaxCurrencyCode emission guarded (`only when != the document currency`, on BOTH the invoice and credit-note paths); the Percent formatted through `Decimal` (the `format(...normalize(), "f")` idiom, tolerant of float and Decimal inputs). | T2 (ii)-(ix) GREEN; the existing generator suite green (loose containment assertions only — verified: no element-presence pins on TaxCurrencyCode or Percent) |
| T6 | **The fixture truth:** the two USD fixtures (`test_xml_currency_truth_p33.py`, `test_schematron_business_rules_p35.py`) carry `"tax_currency": "USD"` (the honest mapper shape; the masked inconsistency retired). | the P33 + P35 suites green |
| T7 | **The full backend suite** — every existing pin holds. | `pytest --reuse-db --no-migrations -q` — expect **1089 + the new-gate count** passed, 0 failed, 5 skipped |

### Phase 3 — the full gate matrix + the screenshots + the live contracts

1. The complete gate set on the remediated tree (both backends restarted on the remediated code — the `--noreload` lesson): backend pytest · vitest **698/698 (85 files)** (web tree untouched) · `tsc` 0 · whole-tree `eslint` 0E/0W · live `test:e2e:full` **43/43** · `rls_smoke` **13/13** · `mobile-nav-audit.js` **17/17** (the forty-first settlement) · the `translate` probe re-PASS · `build:server` green + `prod-csp-smoke.js` 5/5 · `make lint-mechanical` exit 0 · the production ruff count stays **148** / tests **73** (the new specs clean by construction — line-length ≤ 100, no touched lint class).
2. **The live contract re-verification (with the two DELIBERATE byte changes documented):** on the SGD demo substrate — the invoice XML from a REAL APPROVED document still validates clean with the arithmetic layer ON (`is_valid=True`, schema=0, schematron=0); the credit-note XML from a real document validates clean; the tampered-total controls (TaxInclusive +500, a line amount ×3) FAIL with the BR-CO rules named. The two deliberate emitted-byte changes vs the P35 bytes: `cbc:TaxCurrencyCode` omitted (the redundancy retired) and `cbc:Percent` "9.0" → "9" (the canonical Decimal form) — both documented here and in the API guide.
3. Screenshots: 8 DOM-verified captures (`docs/screenshots/240-247_*_session70.png`, md5-unique + non-blank pixel-verified, the session-66 capture conventions) — the P36 surfaces featured (the invoices list + the peppol-adjacent surface if reachable), plus the standing set (the banking payments, the reports trial-balance, the ledger, the dashboard, the settings, the mobile drawer closed/open).
4. The `.env.example` truth verification (the config-readers sweep re-run; no new env vars expected — all three fixes read code artefacts and DB fields, not the environment).

### Phase 4 — the docs truth pass

| Doc | Update |
|---|---|
| README.md | the badge/test arithmetic, the status-table rows, the P36 milestone section |
| CLAUDE.md | version 2.36.0 → 2.37.0, the status block, the P36 milestone block |
| AGENTS.md | the header gate row, the P36 lesson (the construction-truth vs checked-truth class — a validation stack must check what the constructor guarantees, or tampering passes) |
| ledgersg_SKILL.md | the quick-ref numbers, version 2.22.0 → 2.23.0 |
| Project_Architecture_Document.md | the test-count rows, version 3.25.0 → 3.26.0 |
| docs/DEPLOYMENT.md | the header re-verification line (session 70 / P36 — the live stack verified against the guide this session); any drift found corrected |
| API_CLI_Usage_Guide.md | v3.8.0 → v3.9.0: the arithmetic validation contract documented (the BR-CO rules, the schematron_errors population on totals tampering, the VALIDATION_ERROR failure path carrying the rule IDs) + the two byte changes (TaxCurrencyCode omitted, the Percent canonical form) |
| worklog.md | the session-70 entry |
| docs/session_70.md | the session log |

## 4. Deferred register (updated, carried forward)

**Fixed this sprint (removed from the register):** the Schematron ARITHMETIC axis (the registered P35-deferred #1 candidate — closed as the six-rule BR-CO pattern with the sound rounding bound); the TaxCurrencyCode hardcode (the P33-class survivor); the Percent float artifact.

**Still deferred (with rationale, unchanged unless noted):**
- **The ruff semantic batch — 148 production findings** (unchanged this sprint unless the edits touch a lint class — they should not): UP045/UP006/UP007/UP035×105 (typing modernization; the mypy-gate conversation — mypy itself carries 1491 errors — stays the registered precondition), E501×38 + `ruff format` (160 files would reformat — the `make format` axis), S110×4 (the verified fail-closed XSD loads), N818×1 (the LedgerSGException rename — touches every importer; its own reviewed pass).
- **The tests/-tree residual — 73 findings** (E501×73 — the format axis).
- **BR-CO-11/12 (NEW, registered):** the document-level allowance/charge arithmetic — N/A today (the generator emits neither element); when the mapper ever grows doc-level allowances/charges, the BR-CO-13 rule must widen to the general form and the new rules must ship with it.
- **BR-CO-18 (NEW, registered):** "at least one VAT breakdown" — a deposit-only document (every line `is_bcrs_deposit`) legitimately carries zero tax subtotals (the mapper skips deposit lines); the rule would false-reject it. Register until the deposit-only document question is settled.
- **The `/accounts/search/` limit-contract migration** — unchanged (verified again: capped + typed; no frontend consumer).
- **The capped-default flip; the audit-log INSERT policy (DDL); BE-L3/BE-L4 locking; the CSV errors[] strings; dead-letter design; UEN checksum; the NULL-context SELECT tradeoff; H-05b models; PaymentsTab prefill; the TanStack incompatibility; the membership-cache window; the P20-era FE-M2/M3 designs; CI hardening (the mypy gate); the version-story reconciliation** — the P21–P35 deferred registers carry forward unchanged.

## 5. Acceptance criteria

- The two RED specs (executed): T1/T2 RED on the base tree for exactly the right reasons (the tampered totals passing clean; the USD mapper emitting "SGD"; the TaxCurrencyCode present-when-equal; the float-artifact Percent), GREEN after the fixes.
- The backend suite green (**1089 + the new-gate count** expected, 0 failed, 5 skipped); no frontend change; the web gates green at the standing ratchets.
- The live contract re-verification: on the SGD demo substrate the invoice AND credit-note XML from real documents still validate clean with the arithmetic layer ON; the tampered-total controls fail with the BR-CO rules named; the two deliberate byte changes (TaxCurrencyCode omitted; Percent canonical) verified and documented.
- `make lint-mechanical` exit 0 (no lint class touched); the production ruff count stays **148**; the tests count stays **73** (the new specs clean by construction — line-length ≤ 100).
- `skills/` untouched by code checks; `git status` shows only the intended files.
- Plan + report saved under `docs/` in the `REMEDIATION_*_P36*` convention; the session log `docs/session_70.md`; the worklog updated; 8 pixel-verified screenshots (240-247).

## 6. Open decisions (resolved with judgment)

- **The rounding conversation (the registered precondition):** resolved as the sound per-line bound (§2/H1) — NOT a fixed epsilon (dishonest for large line counts: the per-line 2dp roundings accumulate legitimately) and NOT strict equality (false-rejects 3 × 5.55 at 9%). The line count is read from the document itself (`count(../..//cac:InvoiceLine | ../..//cac:CreditNoteLine)` from the TaxSubtotal context — the per-category line count is NOT in the XML (lines carry no tax category), so the total line count is the conservative multiplier; the bound stays sound because the per-category deviation is bounded by its own line count ≤ the total).
- **The quantization guard 0.00005:** the half-unit of the last decimal place — absorbs the XPath-double representation error on any realistic magnitude, fails on any real disagreement (the DB's finest scale is 0.0001).
- **TaxCurrencyCode omitted-when-equal (not carried-equal):** the UBL semantic (the element declares a DIFFERENT tax currency); carrying it equal would trade a truth bug for a redundant element some validators flag. The divergence path stays open for a future data model that taxes in a different currency (the guarded emission handles it).
- **The Percent canonical form `format(...normalize(), "f")`:** deterministic across Decimal and float inputs, plain-notation always (the `1E+2` normalize trap avoided), scale-free ("9", "8.75" — not "9.0000"). The byte change from "9.0" is deliberate and documented.
- **BR-CO-11/12/18 registered, not faked:** each has a verified N/A or false-rejection rationale (§4).
- **No new e2e spec:** the arithmetic truth is XML-level (pinned by the new backend specs); the browser surfaces render whatever the API sends (the P35 precedent).
- **The UP batch / E501 + format axis / N818 / mypy gate stay out (again):** the registered preconditions are unchanged.
