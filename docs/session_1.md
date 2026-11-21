I'll start by internalizing the operating instructions and setting up a structured plan for this complex task.
Repo cloned. Now reviewing the key documentation files:
The docs are large. Let me read them in manageable chunks:
Now reading CLAUDE.md and README.md:
Now the Project Architecture Document:
Now reading the Code Review Audit Report (918 lines):
I now have a thorough understanding of the audit report. Let me mark task 2-3 progress and validate the audit findings against the actual codebase, plus review the skills catalog and PostgreSQL setup docs in parallel:
The setup script targets a different repo contract. Let me check the rootless-postgresql skill and the SSH push docs:
Let me check the backend env config, key files from the audit, and skills catalog:
Now I'll install PostgreSQL. The setup_pg_z.sh establishes a rootless PG at `/home/z/my-project/pg` on port 5432 with superuser postgres/postgres; I'll then adapt for LedgerSG's DB contract (role `ledgersg`, DBs `ledgersg_dev`/`test_ledgersg_dev`):
PG 17 running. Now let me check the schema's role requirements and set up the LedgerSG databases:
Now configuring the LedgerSG database contract (role `ledgersg`, DBs `ledgersg_dev` + `test_ledgersg_dev`) and loading the schema:
Schema loaded with all 30 tables. Now loading test DB and setting up the Python backend environment:
Found a real repo defect: `pip install -e ".[dev]"` fails due to missing hatch package config. Let me check the rest of pyproject.toml:
The pyproject.toml lacks hatch wheel package config — a real defect to fix later. For now, installing dependencies directly:
Django check passes (matches audit evidence #1). Now running test collection for the baseline:
468 tests collected, no collection errors (audit had 467 + 1 error). Running the full baseline test suite:
162 failed / 298 passed — much worse than documented. Let me analyze failure patterns:
Missing `requests` — an undeclared dependency (real defect). Installing and re-running:
The test failures confirm API contract mismatches (login returns `tokens.access` but tests expect `access_token`; `/me/` returns 404). Now let me validate the audit's critical findings directly against source:
All Critical/High audit findings verified against source. Checking remaining failure categories (RLS tests, peppol views):
RLS middleware throws `tenant_context_error` 500s. Let me find the underlying exception:
The generic `except Exception` masks the real cause. Checking testing settings (likely Redis cache unavailability):
testing.py requires a live Redis at localhost:6379 — that's what breaks the middleware membership cache. Let me check Redis availability (rootless like PG):
Redis running. Re-running the full test suite for the true baseline:
Baseline now matches docs exactly: 67 failed / 393 passed / 8 skipped (468 collected). Environment is fully reproducible. Now analyzing the 67 failures to separate real defects from fixture issues:
Key failure patterns: 404s (URL routing), `InFailedSqlTransaction` (real bug), `sequence_number` AttributeError (matches audit H-09). Let me check URL wiring:
URLs are registered. Let me see why the test gets 404:
The 67 failures mix test/view contract drift (`/profile/` vs `/me/`, `refresh_token` vs `refresh`) with real bugs. Audit validation is complete. Now let me consult the repo skills for the audit and planning phases:
Now let me run the repo's audit skill scanner (checklist_runner) per its Phase 3, and review the verification protocol skill:
Scanner output matches audit evidence #9 exactly (29 findings, 18 false-positive "criticals"). Audit validation is complete. Now deep-reading the files I'll remediate:
Now grounding the remediation in the actual DB schema — checking `gst.return` columns, `invoicing.document`/`document_line`, and enums:
Tax code seeds have the IRAS-correct f5 box mapping (SR→Box1/6, TX→Box5/7). Now reading the remaining remediation targets:
I now have full understanding of all P0 targets. Let me read the remaining pieces (approve_document, auth views refresh, audit_context):
All targets fully understood. Now creating the comprehensive remediation plan:
Plan created. Now validating it against the codebase — checking GST views, the skipped test, exception signatures, and conftest patterns:
Plan validated — all assumptions confirmed (plus `get_f5_json`/`get_upcoming_deadlines` also use phantom attrs, added to Task 5 scope). Let me check GST views' amend/pay endpoints, then begin TDD execution:
Beginning execution. **Task 1 (C-04)** — first reading conftest fixtures to write consistent tests:
Fixtures understood. Now writing the RED-phase tests for Task 1 (C-04):
RED confirmed for test 1 (exception swallowed). Test 2 needs the invoice dated inside the fiscal period — fixing the test setup:
Both RED tests fail for exactly the right reasons. **GREEN phase** — implementing the C-04 fixes:
C-04 GREEN (2/2 passed). **Task 2 (C-02)** — void reversal. First reading the skipped test's context:
Now implementing the un-skipped tests (RED phase for C-02):
RED confirmed: `void_reason` is empty (proves C-02). Checking the draft-void test failure type:
The status check raises the app's own ValidationError. Fixing the test to expect the right exception, then implementing GREEN:
Now the GREEN phase — deleting the duplicate placeholder and fixing `void_document`:
Found a real bug in `void_document_entry`: it uses `date.today()` but `create_entry` validates the fiscal period. Let me check `create_entry`:
The reversal must be dated in an open period. Fixing `void_document_entry` to fall back to the original entry's date when today's period is closed:
The reversal is created without `posted_by` (user not passed through). Fixing both call sites:
Same latent bug exists in the `change_document_status` posting path. Fixing it too:
`create_reversal` sets `reversed_by` but never flips `is_reversed` — violating the CHECK. Fixing:
Only the PDF `sequence_number` failure remains (H-09 partial). Since the test exists and the fix is small, fixing the invoice-number rendering now:
All 15 pass — C-02 complete (plus H-09 PDF-number partial). **Task 3 (C-03)** — RLS transaction fix. Reading the existing RLS test to model the new TransactionTestCase:
Writing the RED-phase TransactionTestCase for C-03 (asserts the setting is live *inside the view*, mirroring production autocommit):
Unique constraint on `uen` (empty default) collides with leftover rows. Making test orgs use unique UENs:
Unmanaged tables aren't truncated by Django — leftovers persist across runs. Using UUID-suffixed emails:
Perfect RED: `got ''` — exactly the C-03 evidence. **GREEN phase** — wrapping the request in a transaction that carries the SET LOCAL:
The edit left structural issues (unreachable code, removed UnauthorizedOrgAccess handling, missing import). Let me view and repair the full method:
Fixing the leftover indentation issue on `_get_org_role`:
Core C-03 fix works (3/4). My test used the wrong schema-qualified name for Contact. Checking the model's actual table:
My TransactionTestCase leaves unmanaged-table data behind (no auto-truncation). Adding tearDown cleanup:
Leftover rows from my earlier TransactionTestCase runs persist in the DB. Cleaning them once, then re-running:
RLS doesn't apply because `ledgersg` is a superuser (needed for schema loading). The correct test: prove the policy filters rows for the real app role (`ledgersg_app`). Verifying that role works first:
App role works. Rewriting the row-filter test to use the real app role with its own connection:
All 10 RLS tests pass. Applying the same transaction fix to `audit_context.py`:
Audit middleware runs inside the tenant transaction for org-scoped URLs, but non-org-scoped API paths (e.g. `/api/v1/auth/*`) still lose their SET LOCAL. Wrapping it in its own (nestable) transaction:
Running a broad regression check on the middleware changes:
67F→65F, 406 passing, no regressions. **Task 4 (H-01)** — journal balance queries. Writing RED tests:
conftest 作用域问题 —— 正在将测试移动到 `tests/invariants/`（继承了根配置）：
RED confirmed with the exact audit FieldError. **GREEN** — fixing the lookups and the N+1 in one pass:
My test asserted the old shape. Fixing it to the dict format the service returns:
All invariants green — H-01 done. Now **Task 5 (C-01 + H-14)** — the GST F5 rebuild. Writing the tie-out test (RED):
Fixture helper bug — triple `kwargs.pop("code")`. Fixing:
Line numbers must be unique per document. Fixing with a counter:
Simplifying with a per-document counter:
All 5 RED with the exact C-01a error (`invoicing.invoice_line does not exist`). **GREEN** — rewriting the F5 aggregation:
Now rewriting `return_service.py` — the whole workflow with real fields and the allowed status set:
Now updating the GST serializers (removing phantom fields):
Enum types don't support LIKE — casting to text:
All 5 F5 tests pass — C-01/H-14 remediated. Checking for stale references to the old service API:
Banking references are legitimate (real columns). Running the full suite to see overall state after C-01:
GST tests use non-org-scoped URLs but the app registers org-scoped ones. Checking the URL patterns and fixing the tests:
Two issues: view signature missing `org_id`, and my audit_context warning fired. Checking both:
Views need `org_id` params. Also need to diagnose the audit_context warning. Fixing views first, then investigating:
Formatting drift (4dp vs 2dp). Checking the other two failures, then fixing the view to quantize to 2dp:
The `test_gst_tax_code_info` test lacks the fixture param my URL patch needs. Fixing test signatures and the 2dp formatting:
The service needs to expose `box_mapping` and 2dp rates per the documented contract. Fixing:
All green. Now investigating the audit_context warning seen earlier:
Warning gone (it was the correct log+re-raise of the earlier TypeError). Full suite check:
53F/426P — 14 more fixed. **Task 6 (M-01/I-01)** — schema-model conformance gate:
The gate works — my type map needs inverting (field class → allowed DB types). Refining:
The gate found REAL pre-existing drift (ExchangeRate, OrganisationSetting models). Checking the actual schema to align the models:
Real drift confirmed. Checking model definitions and usage before aligning:
Both models are drifted and in use. Fixing them to match the schema (SQL-First):
The view uses Organisation directly, so fixing the drifted models is safe. Checking BaseModel first:
Writing the corrected models (ExchangeRate has no `updated_at` in schema, so no BaseModel; OrganisationSetting uses JSONField):
Conformance gate PASSES — 451 columns verified, 2 drifted models fixed. **Task 7** — security config + packaging. Writing RED tests:
All 8 RED for the right reasons. **GREEN** — first, the exact table DDL simplejwt expects:
Appending the SQL-First DDL for the blacklist tables to the schema file:
Now adding the actual §15b DDL before the changelog section:
Applying the DDL to both databases, then updating settings and auth_service:
Now adding the SECRET_KEY gate to production.py and RATELIMIT off in testing.py:
Now rewriting the auth_service token lifecycle:
Now fixing `logout_user` and adding the `_blacklist_all_user_tokens` helper plus the timezone import:
All 10 security tests GREEN. Now the pyproject fixes (NEW-1/NEW-2):
NEW-1 verified. **Task 8** — aligning auth tests with the served contract:
All auth_api tests pass. Checking the org-context test failures:
The URL exists in `apps/core/urls.py` but there's also an `apps/core/urls/` package — the AGENTS.md-documented dual-URL-config trap. Checking:
The active URL package is missing `set-default-org/` (it's only in the shadowed `urls.py`). Fixing the real one:
The view serves the documented nested contract (`{id, org: {...}, role: {...}}` per AGENTS.md); tests expect flat. Updating tests to the real contract:
These are the documented fixture-isolation failures (orgs without DocumentSequence rows). Checking the test fixtures:
The fixture only seeds a JOURNAL_ENTRY sequence. Checking what the real org seeder creates, then extending the fixture:
37F/454P — 30 more fixed than baseline. Grouping the remaining failures:
Serializer exposes nested `contact`, tests assert `contact_id` — updating the test assertions:
The tests use `date.today()` but the fiscal period fixture covers Jan 2024. Fixing all three:
32F/459P. Checking the remaining peppol/rls/permissions failures (outside the documented test_api_endpoints debt):
`create_account` passes phantom fields. Checking schema truth, then fixing:
The serializer's `is_bank` flows via kwargs to a real field — flow is correct now. Running the remaining security tests and full suite:
The peppol views return real data; tests assert the old "stub" contract. Updating tests to the real contract:
28F/463P. Checking the 2 non-test_api_endpoints failures:
Two small fixes — the leftover `test_mode` assertion and the duplicate `is_bank` kwarg:
27F/464P. Verifying ALL remaining failures are the documented test_api_endpoints debt:
Those are plain input serializers (no model validation) — fine. Full verification gate now:
27F/464P stable. The 1797 ruff errors are pre-existing repo-wide debt (never lint-enforced). Applying lint fixes only to files I touched (surgical, no mass-reformat):
Auto-fixing the touched files, then checking what remains:
Fixing the B904s in my new code:
The account balance helper queries a non-existent table. Fixing to use journal lines:
The view never existed in the schema. Rewriting the service to aggregate from `journal.line` directly:
**26F/465P/5S** — all remaining failures are the documented `test_api_endpoints.py` fixture debt. Execution complete. Now updating documentation:
Now updating README.md test-execution section and the status claims:
Now updating CLAUDE.md, AGENTS.md, and the PAD with the corrected architecture facts:
Now AGENTS.md troubleshooting additions and the PAD middleware/box corrections:
Docs updated. Now **Task 10** — reading the distillation skills to create `ledgersg_SKILL.md`:
Now writing `ledgersg_SKILL.md` (distilled from this remediation, per both skills' templates):
Now the final task — commit and push. Reading the SSH wrapper instructions:
The wrapper defaults to a different repo — I'll pass `--remote`. No ssh binary or paramiko here, so I'll deploy the Appendix-A shim. First, cleaning workspace artifacts and committing in logical groups:
Only whitespace fixes — safe. Making the logical commits:
All 8 commits in place. Final gate check, then setting up the SSH push infrastructure:
Committing the missed `__init__.py` and checking the leftover dir:
Working tree clean, paramiko ready. Deploying the ssh shim outside the repo and materializing the key:
Key verified. Running the wrapper dry-run with the shim on PATH:
Dry-run clean — auth verified, fast-forward push ready. Executing the real push:
All tasks complete. **Pushed to `main` and verified: remote ref `d559374` == local HEAD** (`nordeim/ledgersg`, 9 commits, fast-forward from `d7835238`).

## Handoff Summary

**Verified (executed in this environment):**
- Audit report validated against source — all 4 Critical + key High findings confirmed, plus 4 new findings (broken `pip install -e .`, undeclared `requests`, auth test/view contract drift, Redis test dependency)
- Environment: rootless PG 17 + Redis 8 + schema v1.0.2; baseline reproduced exactly (67F/393P/8S)
- **TDD remediation: 67F/393P/8S → 26F/465P/5S** (+72 passing; the 26 remaining are the pre-existing `test_api_endpoints.py` fixture debt, unchanged from baseline)
- Fixed: C-01 (F5 rebuilt on real schema, IRAS boxes, tie-out test), C-02 (void reverses GL), C-03 (RLS inside request transaction, proven via TransactionTestCase + app-role row filter), C-04 (no partial commits), H-01, H-05 (token rotation + blacklist, SQL-First DDL §15b), H-06/H-07, H-12, M-01 (conformance gate caught + fixed drifted `ExchangeRate`/`OrganisationSetting`), H-09 partial
- Docs aligned (README/CLAUDE/AGENTS/PAD + [remediation plan](/home/z/my-project/ledgersg/docs/REMEDIATION_PLAN_2026-11-21.md) + [report](/home/z/my-project/ledgersg/docs/REMEDIATION_2026-11-21_REPORT.md)); [ledgersg_SKILL.md](/home/z/my-project/ledgersg/ledgersg_SKILL.md) created; key shredded after push

**Deferred debt (explicit, in the plan §4):** H-02/H-03/H-04/H-08/H-10/H-11/H-13, M-02…M-16, L-*, `test_api_endpoints.py` fixture pass, GST payment schema extension.

**Suggested next steps:** pick up the P1 roadmap (rate history H-04 is the highest compliance value), then the `test_api_endpoints.py` fixture architecture pass.
