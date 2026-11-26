I'll start by setting up my task plan and refreshing the workspace.
The repo exists locally. Let me refresh it with git pull:
Repo is up to date on main. Now let me review the project structure and key documentation:
Now let me review the key documentation. Starting with CLAUDE.md and the Architecture Document:
Now let me review the session documents and remediation history:
Now let me read the two independent audit reports and the worklog:
Let me read the full first audit report:
Now let me read the worklog and delegate the large doc digestion to parallel Explore agents:
Let me delegate digestion of the large docs to parallel Explore agents while I review operational docs:
Docs digested. Now let me check the existing environment state and set up PostgreSQL:
The sandbox was recycled — PG, Redis, venv, and node_modules are all gone. Let me read the rootless-postgresql skill and set up the environment:
Now let me run the PG setup script and set up Redis:
Now load the schema into both databases and set up Redis:
PG and Redis are up. Now let me rebuild the backend venv and frontend node_modules in parallel:
Environment rebuilt. Now let me reproduce the documented baselines — first the backend suite:
Backend baseline matches exactly: 750P/0F/5S. Now frontend gates:
All baselines reproduced (750P/5S, tsc 0, 530/530, eslint 9). Let me validate key P13 changes exist in the codebase:
All P13 changes validated. Now let me create the daemonizer for the dev stack (per the P13 environment lesson) and start the servers:
The dev stack is live. Let me check the demo user state and verify the mobile nav with a live Playwright probe:
Dev DB is empty. Let me bootstrap the demo substrate per DEPLOYMENT.md §9:
Demo user + org created. Let me run the default e2e suite and then the full live suite (which self-bootstraps demo activity):
Two failures on a fresh DB — likely data-bootstrap related. Let me investigate:
Documents were created, but the GST return is missing — let me check the ensureDemoActivity logic:
Found a real gap: `ensureDemoActivity` never CREATES the F5 return when missing — it only force-computes an existing one. This is a fresh-DB bootstrap gap (finding for the plan). Let me create the return now and re-run:
The return now computes (Box 1 = 830.00). Interesting: the create endpoint returns "Created 0 return periods" while a DRAFT return was created — let me quickly check that backend logic:
The return now exists. Let me re-run the full live e2e suite:
Full live gate green: 40/40. Now let me run coverage + build gates, and do the live mobile-nav verification (the sprint focus):
The frontend daemon died after the e2e run. Let me restart both and re-probe:
The login page has no sidebar — I need to authenticate first. Let me fix the probe:
One timing-sensitive failure — the visibility transition keeps the drawer visible during slide-out. Let me verify with a longer wait:
Mobile nav verified working (17/17), no Tailwind v4 bug — consistent with P12/P13 verdicts. Baselines all reproduced. Now let me hand-verify the audit findings in source before planning the remediation:
H-6 confirmed — and it has a subtle interplay with the middleware's membership check. Let me read the middleware ordering:
Let me verify a few more details — file_return status handling and the seed functions:
All findings verified. Now let me write the P14 remediation plan following the repo's naming convention:
Plan saved. Now let me validate the plan's task sites against the codebase before executing:
All sites validated. Beginning TDD execution — **Task 1 (C-2: FILED return immutability)**. First, the RED test:
Now writing the RED test for C-2 (FILED immutability):
The services raise the custom `common.exceptions.ValidationError`. Let me fix the test import and re-check:
2 RED for the genuine C-2 bug. Now the GREEN fix:
C-2 GREEN. Now **Tasks 2+3 (H-1 allocation cap + H-2 instalment statuses)** — RED tests first:
Now writing the RED tests for H-1 + H-2:
The journal requires `posted_by` (P10/M-2 fail-closed). Fixing the helper to pass the user:
4 genuine RED failures (H-1 over-allocation + H-2 statuses). Now the GREEN fixes — first checking how `amount_due` is computed:
Void deletes allocations, so no voided-payment exclusion is needed. Simplifying to match the recompute convention:
Now the serializer fix (H-2):
H-1/H-2 GREEN with no regressions. Now **Task 4 (H-3: filed-period GST lock)**. Checking import structure to place the guard:
Now writing the H-3 RED tests:
The posting needs document lines. Adding them to the fixture:
Correct RED state: 3 genuine failures + the control passing. Now the GREEN fix — creating the shared guard:
Now wiring the guard into the posting paths:
Now the manual journal path:
Now the void_document path (my test uses it directly):
The refusal works — the doc correctly stays at SENT (pre-approve state). Fixing the assertion:
H-3 GREEN, no regressions. Now **Tasks 5+6 (H-4 credit-note linkage + H-5 GST-registration guard)** — RED tests:
7 RED for the right reasons. Now the GREEN fix — checking create_document's signature:
Now adding the validation logic before document creation:
Now adding the two validator methods:
My H-4 contract change broke existing tests that encode the old unlinked-credit-note contract. Updating them to the new (audit-mandated) contract:
Massive errors — the test DB may be corrupted. Let me investigate:
The test DB lost its tables. Let me check the testing settings for the test-DB naming:
The schema reload at test setup must have failed partway. Let me test the schema load path directly:
The manual load went to the dev DB (env default) — the demo substrate needs re-bootstrap later. Let me diagnose the test-runner schema load failure:
Root cause found: `CREATE EXTENSION` without `WITH SCHEMA` installs into the connection's first `search_path` schema (`core`) — the schema file's own `DROP SCHEMA core CASCADE` then destroys the extension operators mid-load. The fix — pin extensions to `public`:
Both DBs reloaded with pinned extensions. Now the critical check — the full test suite:
Let me check the PostgreSQL log for what drops the tables:
Let me empirically determine what the runner's load leaves behind:
Let me instrument the test runner to find the real failure:
The probe passes on a freshly loaded DB — so something DURING the session destroys it. Let me find what:
Let me bisect which test file destroys the DB:
`apps/` destroys the DB. Bisecting within apps/:
All reporting files fail at setup. Let me replicate the full setup path including migrate:
The manual setup works (45 tables) — so the destroyer is pytest-django's `--no-migrations` path. Let me check its implementation:
I see my methodology error — the documented invocation requires `--reuse-db` and my bisect commands omitted it. Re-running correctly:
The DB "destruction" was my missing `--reuse-db` flag — suite is healthy. Now fixing the 2 dashboard tests for the H-4 contract:
Full suite green: 775P/5S. Now **Task 7 (H-6 + M-6a: RLS completion + audit search_path pin)** — the schema §17 patch. Let me check the §16 style first:
Now writing the §17 section:
Now updating the schema header version and applying §17 to both DBs:
§17 live. Now **Task 8 (C-1: org-creation RLS context)**:
Now the RLS conformance + C-1 regression tests:
The spy recursed. Simpler mechanism test — assert the context is set when the seed runs:
All RLS/C-1 tests green. Now the **H-7 runtime-role smoke script**:
Now the live C-1/H-7 proof — setting the app-role password and booting a second backend as `ledgersg_app`:
C-1 is fixed and proven live (201 as ledgersg_app). Debugging the account code check:
The accounts endpoint returns 4100 but the bank GL should be an `is_bank` account (1100), per the P9 convention. Fixing the smoke script:
**14/14 steps green as `ledgersg_app`** — C-1 + H-7 proven live. Let me run the full suite and commit the completed tasks:
Two fixes needed: the conformance test must intersect with tenant tables, and the isolation test needs the app-role password from env:
The app-role backend died when I rotated the password back. Restarting with the restored credentials and re-verifying:
14/14 green again. Now committing the completed backend tasks as logical conventional commits:
5 commits done. Continuing with **Tasks 9+10 (M-4 input validation + M-1 UEN/GST validators)** — RED tests:
Now creating the validators module and wiring everything:
Now the M-4 line-item schema in the document create serializer:
30/30. Critical follow-up: the documents view must pass `related_document_id` through (otherwise the API can't create linked credit notes):
Now **Task 11 (X-1: XXE hardening)**:
Now the XXE regression tests:
lxml doesn't expose parser flags for introspection — the behavior tests are the proof. Replacing the config test with a DTD-loading probe:
Internal-subset DTD defaults aren't the threat vector — dropping that probe, keeping the 4 behavioral gates:
Now **Tasks 12+13 (H-05b F5 override reason + H-04b NRIC masking)**:
Now implementing both fixes — the serializer masking + write validation, and the file_return override reason:
Now **Tasks 14+15 (M-5 Viewer gates + M-10 tax-code dedupe)**:
Now writing the M-5 RED tests and applying the gates:
`_check_permission` doesn't exist on those classes. Adding a shared module-level helper:
The blank-UEN uniqueness collision (a known deferred issue) — giving test orgs unique UENs:
All 6 pass. Now **M-10 (tax-code dedupe)**:
The ORM can't create system rows (null org). Using raw SQL for those:
The schema seed already carries 3 dated SR bands — the dedupe works. Fixing the test to assert band uniqueness:
Now **F-A (e2e bootstrap fix) + H-9 (Docker key)**, then the full regression run:
Now the M-7c schema comment honesty fix + full regression run:

I'll start by setting up a task plan and checking the current workspace state.
The workspace has been reset — no local repo exists. Cloning fresh:
Repo cloned successfully. Now let me review the documentation. First, let me see the docs folder structure:
Now let me read the key session and remediation documents to understand the current state:
Now let me read the partial P14 changes file and the P13 report:
Let me check what the "partial p14 changes" commit actually contains and the current state of the codebase:
Now let me understand the backend structure to compare against those committed paths:
The situation is now clear: the previous session committed several P14 fixes to **wrong file paths** (misplaced at `apps/backend/` root instead of the Django app packages). Let me delegate digestion of the large docs to parallel Explore agents while I verify the codebase state myself:
Both doc digests are complete. Now let me read the operational files myself — the skills catalog, PG setup script, and SSH wrapper instructions:
The setup script creates rootless PG. Now let me find the relevant skills in the catalog (grep the persisted output) and read the rootless-postgresql skill:
Now let me set up PostgreSQL using the repo's setup script:
PG 17 is up. Now create the LedgerSG roles and databases, then load the schema:
Schema loaded into both DBs (30 tables). Now let me check the schema version, set up Redis, and start building the environments:
Schema is at v1.1.0 — confirming the P14 §17 RLS patch was never committed. Now let me set up Redis and build the backend/frontend environments:
Redis is running. Now let me build the backend venv and frontend node_modules in parallel:
Both environments built. Now let me verify the state of P14 fixes — checking whether the correctly-placed service files import from the misplaced modules:
Critical discovery — the real service files import `from apps.gst.services.period_lock import assert_not_gst_locked` but the file was misplaced at `apps/backend/gst/period_lock.py`. Let me check what the tests expect and verify the actual runtime state:
Tests import from the CORRECT locations while fixes sit in misplaced files — the tests will be RED. Let me reproduce the actual gate state. First check the test settings:
**The committed HEAD is broken** — circular import in `payment.py` makes the backend unable to even run `manage.py check`. Let me inspect the damage:
The previous session overwrote the **models** file with **serializer** code — the real `Payment` model definition was destroyed. Let me verify with git history:
Fully confirmed: commit `2bcb43f0` corrupted the codebase. Let me diff the other "correctly placed" modified files against their pre-P14 state to assess which changes are sound:
The correctly-placed fixes reference `apps.gst.services.period_lock` which doesn't exist. Let me map ALL the broken wiring — where each misplaced module is expected:
Let me check which serializer-layer fixes exist in the real serializer files:
Let me check the remaining P14 task states — XXE hardening, viewer gates, tax-code dedupe, Docker key, and the e2e bootstrap:
Vitest and Playwright are already configured. Now let me complete the damage map — comparing the corrupted model file against the real payment serializer:
M-5 confirmed unfixed. Now let me verify the frontend baseline and remaining items:
Vitest baseline green (530/530). Let me check a few remaining audit points and pip-audit availability:
All versions confirmed. Now let me review the DEPLOYMENT.md and API guide structure to plan the doc updates:
Now I have the full picture. Let me check what the committed P14 test files cover so the plan maps them correctly:
All P14 tests exist and are RED (awaiting their fixes). I now have everything needed. Let me update my todo list and write the remediation plan:
Plan saved. Now let me validate the plan's key assumptions against the codebase before executing:
The plan aligns with the tests. Let me verify the current RLS state in the live DB to scope §17 precisely:
§17 scope confirmed: 6 tables need RLS. Let me study the schema's §12 RLS section to match its style:
Let me check the `current_org_id()` helper function definition and the middleware context mechanism:
Let me verify the org_id columns on the six §17 target tables:
The plan is fully validated. Now executing **Phase 0 — tree repair**. Starting with the Payment model restore:
Backend boots (only the documented W001). Now the H-2 serializer fix — porting the stranded fix block:
Now moving the misplaced period_lock.py to its expected home:
Now Phase 0.5 — porting the C-1 fix into the canonical organisation service:
Now check whether views pass `override_reason` and `related_document_id` through:
Two view wirings are missing. Let me check the file serializer then wire both:
Now wire `related_document_id` through the document create view:
Wait — existing test fixtures use pseudo-UENs like `TP<hex>`. Let me check what conftest and other tests use before this gate breaks the suite:
There's a subtle mismatch: the committed P14 test expects `M1234567A` (7 digits) valid, but the stranded validator regex only accepts M+8 digits+letter. Let me verify the real IRAS format before deciding:
Authoritative sources (OECD TIN guide: ASGD = `ANNNNNNNC`, 9 chars) confirm the real M-form is M + 7 digits + check letter, with a 10-char older variant. The committed test is right; the stranded regex was wrong. Fixing the validator:
`OrganisationUpdateSerializer` deliberately excludes the regulatory `gst_reg_number` (owned by `GSTRegistrationSerializer` per the P5/M-6 design). The committed test targets the wrong serializer — a defect in the never-run RED suite. Correcting it to exercise the real contract:
Now let me run the full backend suite to see the interim state after Phase 0:
789 passed — the remaining failures map exactly to my Phase 1 tasks. Let me diagnose each group. First the filed-return immutability failures (the C-2 fix was ported — why still failing?):
The fix works — the test must be asserting differently. Let me read the test:
The test imports the DRF ValidationError while the service raises `common.exceptions.ValidationError`. Fixing the test import (the session-29 fix that never landed):
The tieout test reveals an ordering bug: unknown-box validation must run before the override_reason check. Let me fix the ordering in `file_return`:
C-2/H-05b green. Now diagnosing the fixture ERRORs in the period-lock and input-validation files:
The committed test class lacks `@pytest.mark.django_db` marks (never ran in session 29 — backend was broken). Fixing:
Now check the period-lock test file for the same issue and run both:
M-4 tests are properly RED (implementation pending). Diagnosing the period-lock control test:
The two approve-path tests don't respect the DRAFT→SENT→APPROVED state machine. Fixing them to put the document in SENT first (as the void test already does):
The posting needs document lines (session-29 lesson). Let me check how the credit-note test creates them:
Let me get the full InvoiceLine model to fill all required fields at once:
All 4 period-lock tests green. Now the P11 credit-note tests broken by the H-4 contract change:
The netting test needs the CN linked to the same invoice it nets (not `_make_document`'s internal original). Rewriting it explicitly:
The test DB lost its tables — the session-29 "DB destruction" phenomenon. Let me investigate the test infra's schema handling:
My single-file runs omitted `--reuse-db` — pytest-django recreated the test DB empty (the session-29 methodology trap). Reloading the schema and re-running with both flags:
Dashboard green. Now the GST registration test failures:
Now the RLS isolation test:
The test asserts the schema's own §15 default password — my manually-created role diverged from the schema provisioning. Aligning both (env-overridable test + schema-default role password):
Let me get the full-suite interim state:
809 passed. Let me diagnose the C-1 mechanism test before committing Phase 0:
The SpyCursor recurses when Django calls `cursor.execute()` without a with-block (session-29's "spy recursed" bug — fix never landed). Rewriting the spy to delegate without context-manager emulation:
C-1 mechanism green. Phase 0 complete — let me run lint parity on touched files, then commit:
Lint parity improved (156 → 150 findings on touched files). Committing Phase 0:
Phase 0 committed. Now **Phase 1.1 — M-4 line-item schema**. Let me study how create_document consumes lines:
Now implementing the M-4 nested line schema (RED → GREEN):
M-4 GREEN (29/29). Now **1.2 — X-1 XXE hardening**:
lxml's XMLParser doesn't expose its construction flags (session-29 lesson). Converting the config test to assert the policy constant — the single source of truth:
Now update the config test to assert the policy constant:
X-1 GREEN. Now **1.3 — H-04b NRIC PayNow masking**:
Now the same guard in the update serializer:
The tests construct the serializer without the org context. Fixing the test (never ran in session 29):
The fixture accounts aren't bank-type GL accounts. Adding a proper bank GL to the fixture:
H-04b GREEN. Now **1.4 — M-5 viewer gates**:
M-5 GREEN. Now **1.5 — M-10 tax-code dedupe**:
Writing the M-10 RED test first, then the fix:
Now adding the M-10 RED test and implementing the dedupe:
RED for the right reason (23 rows, 16 unique bands). Now the GREEN fix:
The band-uniqueness gate passed; my assertion was too strict (SR's 2007/2023 bands are legitimate history). Fixing the assertion:
M-10 GREEN. Now the big one — **1.6: schema §17 (H-6 + M-6a + M-7c)**. Let me study the schema structure:
I have the complete design. Writing §17 into the schema:
Now the version header, changelog, M-7c comment fix, and the stale §12 comment:
Now reload both DBs with the updated schema (§17 included):
§17 live — only the 4 documented globals lack RLS. Running the conformance tests:
The proconfig arrives as a parsed array, not a dict. Fixing the test's normalization:
Django's infra tables (created by migrate in the `core` schema) aren't tenant data — the sweep must intersect with actual tenant tables. Fixing the test's semantics:
All RLS/security green. Full backend suite check:
**830 passed / 0 failed / 5 skipped** — all P14 tests green. Committing Phase 1:
Now **1.7 — the live runtime-role proof**. Let me read the rls_smoke script:
The smoke script's generated UEN/GST numbers don't match the new M-1 formats. Fixing the generators:
The smoke reached the CoA check — the account codes need verifying. Checking what the seed actually provides:
The accounts list defaults to top-level only — bank GLs need the `is_bank=true` filter (the session-29 lesson). Fixing the smoke script:
The API's canonical approve path is DRAFT→APPROVED (the dedicated endpoint). Checking how the e2e suite approves to match the realistic flow:
**13/13 steps green as `ledgersg_app`** — C-1/H-7 proven live. Now **1.8 — H-8 dependency upgrades**:
uv is available — the proper manifest updater. Let me see the full deps:
Backend deps upgraded. Running the full suite on the upgraded tree:
Backend green on upgraded deps. Now the frontend upgrades:
0 vulnerabilities. Verifying frontend gates on the upgraded tree:
`npm audit fix --omit=dev` pruned the dev dependencies. Restoring the full tree:
9 eslint findings — exactly the documented register. Now vitest:
Build green. Recording the audit deltas and running coverage:
All gates green. Now **1.9 — H-9 Docker key + service.py gates**. Writing the RED test first:
The codebase convention is `ImproperlyConfigured` (production pattern). Rewriting the test to match, then implementing:
Now implementing the service.py gates and the Dockerfile fix:
The mock doesn't affect the cached base module. Fixing the reload helper to reload base too:
Found it — the helper imports `service` BEFORE reloading `base`, so the import executes against the stale weak key and raises immediately. Fixing the order:
The gate refuses boot without a strong key (correct). Verifying the positive path:
H-9 GREEN. Now **1.11 — F-A e2e bootstrap fix**:
F-A done. Now **1.12 — the .env.example truth pass**:
All templates match the code. Adding the new optional test var to the backend template:
Committing the H-8/H-9/F-A batch:
Now **Phase 2 — verification**. Restarting the dev stack on upgraded deps and checking the demo bootstrap:
Bootstrapping the demo substrate (register + org + contact) on the dev backend:
Starting the frontend dev server, then the full live e2e:
6 e2e failures to diagnose. Let me look at the details:
The log shows the classic double-refresh race: refresh #200 rotates the token, the parallel second refresh sends the now-blacklisted old token → 401 → logout. Let me examine the client's refresh single-flight:
`tryRefreshToken` has no single-flight — concurrent 401s double-refresh and the second gets the blacklisted token. Let me check the existing test harness and write the RED test:
Writing the RED single-flight refresh test:
RED confirmed. Implementing the single-flight fix:
Single-flight GREEN. Re-running the live session spec:
Session fixed. Now the p11 specs:
The e2e's credit-note creation lacks the new `related_document_id` contract. Fixing the spec:
The p11 spec reuses ANY paid invoice as the CN's original — the banking spec's 80.00 invoice can't cap a 250.00 credit note. Fixing the reuse logic to require cap headroom:
p11 green. Now the banking and p10 specs:
The p10 spec uses a pseudo-UEN — now rejected by the M-1 gate (as the audit mandates). Fixing the spec to a real ACRA format:
