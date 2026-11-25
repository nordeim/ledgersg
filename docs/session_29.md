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
