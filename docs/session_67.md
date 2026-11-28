I'll continue with the ledgersg task. Let me set up the TODO plan and start by checking the workspace state.
The workspace exists with prior work. Let me check the full state — git sync status, what's been done, and what remains.
The repo is 1 commit behind origin. Let me pull the latest changes and inspect what's new.
Workspace refreshed. Now let me read the core documents. First, check sizes to plan reading:
session_65.md shows the previous session completed P33 (currency-truth closure) and pushed to main. Now I'm starting a new cycle (P34). Let me read the core documents to build understanding.
Now let me read the key sections of CLAUDE.md and the other core docs:
The docs have very long lines. Let me create folded versions for reading:
Now let me check AGENTS.md structure and read its key sections:
I now have full context of the standing state. Let me quickly verify the test configs and remaining doc structures, then check the environment state:
PG 17 and Redis are still running. Let me verify the databases, schema, and backend health:
The dev DB has an incomplete schema (missing journal tables). Let me inspect and rebuild it per the documented procedure:
Table names are `journal.entry`/`journal.line` — my query was wrong. Let me check the substrate:
Dev DB is populated (5 orgs, 21 entries, 25 invoices, 504 accounts). Environment survived the recycle. Let me update the todo list and run the backend baseline:
Django check green (the documented W001). Now the backend baseline suite:
Backend baseline exact: **1047P/0F/5S**. Now the web gates:
静态检查已全部通过。现在进行 lint-mechanical 门控和 ruff 计数：
The make target needs the venv on PATH. Let me check the Makefile and run the documented scopes:
All static gates exact: lint-mechanical exit 0, production 148, tests 73. Now the live gates — let me check server state and start them:
All three servers are already running (started post-P33 in the prior session; tree unchanged since). Let me verify server currency and run the live gates:
Servers confirmed running remediated code. Now the live e2e suite:
e2e 43/43 exact. Now RLS smoke and mobile-nav audit:
All live gates exact — mobile-nav 17/17 + translate probe PASS (no Tailwind v4 bug, the thirty-sixth settlement). Let me run npm audit to complete the baseline:
npm audit 0. **Baseline fully reproduced — the P33 state holds exactly.** Now the audit phase (Mode C). First, re-verify the P33 slice in source:
P33 slice holds. Now let me scope the P34 candidates — the credit-note XML generator first:
The credit-note path is header-only — not even the parties. Let me check what the mapper provides for credit notes:
The mapper produces full data; the credit-note generator discards parties, totals and lines. Let me check the validation service and the invoice line structure to mirror:
The structure is clear. Now let me check the validation service (does it validate against an Invoice XSD only?) and its schemas directory:
**Sharp finding**: `validate_invoice_xml` (line 207) validates against the Invoice XSD even when the document is a CreditNote — and the transmission service calls it for both types. Let me verify the XSDs and the test expectations:
Both XSDs share the Invoice-2 target namespace. Let me check the generator's namespaces and the CreditNote XSD's structure:
The credit-note path has a triple defect. Let me check the existing test expectations before concluding:
The existing test deliberately doesn't assert `is_valid`. Let me empirically reproduce the triple defect via the Django shell:
**All three credit-note defects REPRODUCED**: header-only XML (H1a), the transmission validator rejects the CreditNote root (H1b), and even the dedicated validator rejects it due to the XSD namespace mismatch (H1c). The credit-note Peppol path can never transmit successfully.

Now let me scope the ISO-4217 candidate — where currency inputs enter:
Let me verify the mapper emits full data for credit notes too (checking its line/totals mapping):
The mapper maps everything for both types — the generator discards it. Let me read the full CreditNote XSD to plan the conformant output:
The XSD requires parties, totals, and lines — all discarded by the generator. Let me check the transmission tests to see what's pinned on the credit-note branch:
The transmission tests mock the validator entirely — the defect is invisible to the suite. Let me complete the sweep with the AP adapter and a few adjacent surfaces:
AP adapter is type-agnostic — fine. Let me verify the org create flow for base_currency:
The audit is complete. Let me consult the skills catalog for the planning phase as instructed:
Now let me verify no existing test fixtures use non-ISO currency codes that would break under the new validator:
The SGDD test stays valid (still a 400). Let me scope the bank account serializers precisely:
The scope is complete — 5 input surfaces. Let me check the existing UEN validator pattern for consistency:
Let me check the schema-fixes test to see what's pinned on the XSDs:
The audit is complete. Now let me write the P34 remediation plan following the repo's naming convention:
Plan saved. Now let me validate it against the codebase — first, the P33 spec as the template for the new specs:
Now let me verify the banking test conventions for the ISO-4217 spec:
The plan is validated. Let me check the banking conftest fixtures for the spec split:
All conventions verified. Now Phase 1 — writing the RED specs. First, the credit-note completeness spec:
Now the ISO-4217 spec (org surfaces, root tests/):
Now the banking serializer spec — first check the fixture patterns:
Now run all three specs RED — they must fail for exactly the right reasons:
**RED confirmed: 8 failed for exactly the right reasons, 2 designed controls pass.** Now the ISO-4217 specs:
Mixed RED with anomalies to investigate — the default-SGD control failed and "US" passed unexpectedly. Let me check:
The UEN in my payload is invalid — the tests would fail/pass for the wrong reason. Let me check the payment fixture errors too, then fix the payload:
Fixing both spec issues — the BankAccount import and the invalid UEN payload:
Payment fixtures still error. Let me see the detail:
The BankAccount fixture needs explicit `paynow_type=None` (the "" default violates the DB CHECK):
**RED confirmed: 7 failed, 4 designed controls pass.** Let me verify the failure reasons name the currency defect exactly:
**Phase 1 RED complete: 15 RED + 6 designed controls = 21 new gates.** Now Phase 2 — GREEN. First, the generator completeness fix:
Now add the `_create_credit_note_line` helper after `_create_invoice_line`:
Now T5 — the XSD correction (namespace → CreditNote-2, InvoiceLine → CreditNoteLine, InvoicedQuantity → CreditedQuantity):
Now T6 — the transmission service validator dispatch:
I need to check for the now-duplicated Step 3 validation call:
The old Step 3 would overwrite the type-aware result — removing the duplicate:
Now T7 — the shared ISO-4217 module:
Let me correct the currency list — CNH was never ISO, HRK was replaced by EUR (2023), ANG→XCG (2025), ZWL→ZWG (2024):
Now wire the five input surfaces. The organisation serializers first:
Now add the `validate_base_currency` methods to both serializers:
Now the three banking validators:
Now replace the two payment `validate_currency` bodies (they're identical):
Now T8 — strengthen the deliberately-weak existing validation test:
Now add the vocabulary unit gate to pin the allowlist decisions:
The edit consumed the org class declaration — restoring it:
Now run all the new specs GREEN:
24/25 pass. The last failure exposes a deeper pre-existing issue — the header elements are emitted in the `cbc:` namespace but the XSD declares them locally. Let me check whether the INVOICE path has the same problem:
**The TDD gate caught a deeper pre-existing defect**: the generated INVOICE also fails its XSD — the validation layer has been decorative for BOTH paths. The root cause is the single-file XSDs' namespace structure (they declare cbc/cac children in the target namespace). Let me enumerate the exact emitted structure, then restructure the XSDs properly:
The restructure must not break the existing schema-fixes tests. Let me read them fully:
The old XSDs never even declared the `currencyID`/`unitCode` attributes — more evidence the layer was decorative. Let me check the Invoice XSD's exact contract before restructuring:
Confirmed — zero attribute declarations in both XSDs; the validation layer was fully decorative. Now the root-cause fix: restructure into the true three-namespace UBL shape. First the cbc schema:
Now the cac (aggregates) schema:
Two fixes needed in the cac schema — the TaxCategory ID must reference `cbc:ID` (the generator emits it in the cbc namespace) and Percent should be optional:
Now rewrite the Invoice and CreditNote root XSDs as ref-based sequencers:
One ref bug — `PartyIdentification` is a cac element, not cbc:
The entire peppol directory is GREEN — 133 passed. Let me strengthen the customization-ID test fixture for precision (the failure should be exactly the missing element):
Now add the invoice-side acceptance gate to the P34 spec — pinning the deeper discovered fix:
All green. Now the full backend suite (T9):
**Backend suite: 1073 passed / 0 failed / 5 skipped** — exactly +26 gates, all existing pins hold. Now the lint truth:
Production count moved 148→149 — one new finding from my edits. Let me find it:
My new helper added a UP006 finding. Fixing with the modernized annotation:
Lint truth restored: **148 / 73 exact**. Re-verify the full suite:
All green. Now update the P34 plan to record the mid-sprint discovery (the honest documentation of scope deepening):
Plan amended. Now Phase 3 — restart both backends on the remediated code (the `--noreload` lesson):
Both backends restarted on remediated code. Now the live gates — RLS smoke first:
The backends die with the shell session. Using `setsid` to detach them properly:
The `&` backgrounding swallowed the `cd`. Using absolute paths:
Both backends respond. Now the RLS smoke and e2e suite:
The backends die between tool calls despite setsid. Let me consult the background-terminals skill for the proper mechanism:
The bg_* tools aren't in my toolset. Let me test what survives between Bash calls:
Processes don't survive between Bash calls in this sandbox. The pre-existing servers (postgres, redis, next dev) may still be alive — only new children die. Let me check:
Postgres/redis/web survive; only new children die per call. I'll run the backends and all live gates within a single Bash invocation:
**All live gates exact: rls 13/13, mobile-nav 17/17, translate PASS, e2e 43/43.** Now the production build + CSP smoke:
build:server green + prod-CSP 5/5. Now the live API contract re-verification on the SGD substrate:
The Peppol verification is perfect — both invoice and credit-note XML from real documents now validate live (is_valid=True, errors=0, SGD byte-stable). The login failed for parts A/B — let me find the demo credentials:
Let me reset the demo user's password via the shell first:
The response shape is `tokens.access`, not `access_token`. Fixing the script:
Part A is perfect — the typed 400s and live normalization. The reports URLs must differ — let me check:
The `currency` key sits at the top level, beside `data`. Fixing the probe:
All live contracts verified. Let me check the full change set and update todos:
The change set is exactly as intended. Now the screenshots — let me check the session-64 capture conventions:
I have the conventions. Let me write the session-66 capture script (shots 224-231):
All 8 captures OK. Now the pixel verification:
All pixel-verified (variance 438–931). Let me visually confirm one capture:
The DOM truths + pixel variance are the repo's established verification standard — all passed. Now the .env.example truth verification:
`.env.example` verified truthful — all 18 backend vars + 2 web vars covered, no new env vars from P34. Now the docs truth pass. First the README structure:
Let me view the doc anchors to update precisely:
Now the docs truth pass. README first:
The long line reproduction failed. Let me do surgical edits instead:
The badge is already 1814 — the first MultiEdit partially applied. Let me check the current state:
MultiEdit applies sequentially and stops at failures — badge applied, rest didn't. Applying the remaining edits individually:
README updated. One more row (P0–P33 → P0–P34), then CLAUDE.md:
Now CLAUDE.md — version, status, backend counts, and the P34 milestone:
The old P33 status line needs removing (only the latest status stays):
Now update CLAUDE.md's backend count and add the P34 milestone section:
CLAUDE.md done. Now AGENTS.md — the header truth block and the P34 lesson:
Now the P34 lesson at the AGENTS.md tail:
Now the SKILL, PAD, DEPLOYMENT, API guide and ci.yml updates:
Now the DEPLOYMENT.md header line and the API guide P34 addendum:
Docs updated. Now the P34 report:
Now the session log and the worklog entry:
All deliverables written. Now the final verification pass on the exact final tree:
The change set is exactly as intended. Now the commits following the repo convention:
All 3 commits made, tree clean. Now the SSH wrapper push — reading the skill first as instructed:
The wrapper defaults to ely-beauty — I must pass the ledgersg remote. Let me check the ssh shim (deployed by the previous session) and set up the key:
The shim exists. Let me verify its shebang and set up the key:
The shim works with system python3. Now materialize the key (0600, outside the repo) and run the sanity check:
The key parses. Now the dry-run against the ledgersg remote:
Dry-run green — clean fast-forward. Executing the real push:
**Push verified — remote main @ 4525000c == local HEAD, tracking ref synced, keys shredded.** All tasks complete:
**P34 Sprint delivered — the Credit-Note Peppol Truth + the ISO-4217 Currency-Input Truth, pushed to `main` at `4525000c`.**

Workspace pulled to `9381124d`; the environment survived the sandbox recycle and was verified end-to-end (PG 17 + both databases + the demo substrate, Redis 8, venv, both dev servers). Every documented baseline reproduced exactly before any change: backend 1047P/0F/5S, vitest 698/698, e2e 43/43 first-run, rls 13/13, mobile-nav **17/17 + translate probe PASS — working, no Tailwind v4 bug** (the 36th/37th settlements), ruff 148/73, npm audit 0.

The audit found the SALES_CREDIT_NOTE InvoiceNow path triply broken (all reproduced live): a header-only generator, the CreditNote root validated against the **Invoice** XSD (doomed to FAILED), and an artefact CreditNote XSD. The TDD RED gate then exposed the defect one level deeper — **the generated invoice also failed its own XSD; the validation layer was decorative for both paths** (mis-declared child namespaces, zero amount attributes). Fixed at the root: both XSDs restructured into the true three-namespace UBL shape. Plus the ISO-4217 allowlist on all five currency inputs. All TDD (15 RED → GREEN, +26 tests): backend **1073P/0F/5S** · vitest 698/698 · e2e 43/43 · rls 13/13 — both XML types now validate clean on real demo documents, SGD byte-stable, the typed currency 400s verified live. 8 pixel-verified screenshots (224-231), `.env.example` truthful, full docs truth pass (CLAUDE 2.35.0, API guide v3.7.0 with the P34 addendum, 2 new AGENTS lessons).

Key deliverables: [P34 plan](/home/z/my-project/ledgersg/docs/REMEDIATION_PLAN_2026-11-28_P34.md) · [P34 report](/home/z/my-project/ledgersg/docs/REMEDIATION_2026-11-28_P34_REPORT.md) · [session 66 log](/home/z/my-project/ledgersg/docs/session_66.md) · [worklog](/home/z/my-project/ledgersg/worklog.md) · [README](/home/z/my-project/ledgersg/README.md) · [DEPLOYMENT.md](/home/z/my-project/ledgersg/docs/DEPLOYMENT.md) · [API guide](/home/z/my-project/ledgersg/API_CLI_Usage_Guide.md)

**Suggested next:** the registered candidates — the Schematron axis (wiring the PINT-UBL-validation.sch above the now-real XSD layer), the UP typing batch (needs the mypy-gate conversation), or the E501/format axis.
