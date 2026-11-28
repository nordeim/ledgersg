I'll start by setting up the workspace and understanding the project. Let me create a TODO plan first.
Repo cloned. Now let me review the core documentation files.
The persisted outputs are nesting. Let me use a more efficient approach to review the key sections.
Now let me read the session docs and remediation plan.
Now let me review the worklog tail, README, and other key docs.
Now let me check the key frontend files: the shell component, vitest and playwright configs.
Test configs are in place. Now let me check the DEPLOYMENT.md and set up the environment.
Now let me set up the environment. First, check current state of PG/Redis/processes.
Environment is fully reset. Let me install rootless PostgreSQL using the repo's setup script.
PG 17 is running. Now let me create the ledgersg role and databases per the skill's bootstrap.
TCP requires the password. Let me retry with PGPASSWORD.
Schema loaded. Now let me set up Redis per DEPLOYMENT.md §5.
Redis running. Now the backend venv install.
Django check green (the documented W001). Now the web install.
Native binaries good, Playwright chromium cached. Let me verify env files and playwright version match.
Now let me create the web .env.local and run the backend baseline test suite.
Backend baseline exact: 1036P/0F/5S. Now the web gates.
All static gates exact. Now the lint-mechanical gate and ruff counts.
All baselines exact. Now let me bootstrap the demo substrate and start the dev servers.
Both servers running. Now the mobile-nav audit — the named focus.
Browser version mismatch. Installing the matching chromium.
Mobile-nav 17/17 (thirty-fourth settlement). Now the dedicated Tailwind v4 translate probe.
Translate probe PASS. Now start the :8001 RLS instance and run the smoke suite.
RLS smoke 13/13. Now the live e2e suite.
E2E 43/43. Now npm audit and the production build + CSP smoke.
All gates reproduced exactly — the P32 state holds. Now the audit phase (Mode C).
The P32 slice holds exactly (148 = 45+38+35+13+12+4+1). Now deeper audit sweeps for new findings.
Found one truth finding. Let me sweep a few more surfaces for new findings.
This is a genuine finding — document currency vs hardcoded amount currencyIDs. Let me scope it fully.
Confirmed blind spot — tests only exercise SGD. Let me check the PDF generation and account model surfaces too.
PDF template is truthful. Let me sweep the remaining services for the same class.
Let me check the frontend reports client for currency display consistency.
Let me check the accounts search endpoint (deferred item) and the API guide alignment.
The audit is complete. Let me check org base_currency constraints before writing the plan.
The audit is complete. Now let me write the P33 remediation plan.
Plan saved. Now let me validate it against the codebase — check test conventions for the RED specs.
Plan validated against the codebase. Now Phase 1 — RED: writing the three currency-truth specs.
Route confirmed. Now the T3 spec.
Now run all three RED specs — they must fail for exactly the right reason.
T1 and T3 fail for the right reasons; T2 has a fixture error. Let me check the AccountType model.
The AccountType reference table has only coarse codes. Let me fix both specs to use the seeded codes.
The test DB schema was destroyed between runs. Let me check the custom test runner behavior.
I deviated from the documented invocation (`--reuse-db --no-migrations`) and pytest-django rebuilt the test DB. Let me restore it per the documented procedure.
All three specs now run. Let me verify the failure reasons are exactly the hardcoded currency.
**RED confirmed** — all 8 failures show exactly the hardcoded "SGD". Now Phase 2 — GREEN. First the Peppol generator thread.
Now verify T1 goes GREEN and the file stays lint-clean.
Pre-existing UP findings stay registered; my new spec's I001/E501 must be fixed. Let me clean the spec.
Spec bug — missing `cac` prefix in the namespace map. Fixing.
T1 GREEN (68/68 peppol). Now T5 — the reports denomination fix.
Now T6 — the account balance fix.
All GREEN. Now T7 — the full backend suite.
1047P/0F/5S (+11 gates). Verify lint counts and the mechanical ratchet.
Counts hold (148/73). Now Phase 3 — restart backends on remediated code and run the live gates.
E2E 43/43. Now the live API contract re-verification on the SGD substrate.
Wrong URL shapes. Let me redo with the documented correct routes.
The demo org has no Peppol access point. Let me verify the XML generation directly on the real document via the shell.
Live contracts verified. Now the screenshots — let me review the session-62 capture conventions.
Now let me write the session-64 capture script (shots 216-223).
All 8 captures OK. Now the pixel verification script.
All pixel-verified. Now the `.env.example` truth verification.
All env examples verified truthful. Now Phase 4 — the docs truth pass. Starting with README.
Now updating README with the P33 milestone.
README done. Now CLAUDE.md version bump and status block.
Now AGENTS.md header and the P33 lesson.
Now append the P33 lesson to the AGENTS.md tail.
Now DEPLOYMENT.md header and API guide.
Now the P33 report.
Now the session log and worklog entry.
All docs updated. Now the final verification pass before commit.
Env examples tracked and verified. Now the final gates on the exact final tree.
All final gates green. Let me review the headline diffs before committing.
Diffs verified. Now the commits following the repo convention.
All 3 commits made, tree clean. Now the SSH wrapper push — reading the skill first.
I have the runbook. Let me set up the push — check ssh binary and paramiko first.
Now deploy the paramiko ssh shim outside the repo.
Dry-run green — clean fast-forward. Executing the real push.
Push verified — remote main at `d1b149b4` == local HEAD, tracking ref synced, keys shredded.
**P33 Sprint delivered — the Currency-Truth Closure, pushed to `main` at `d1b149b4`.**

Environment provisioned from scratch through DEPLOYMENT.md's own steps (PG 17, Redis 8, both DBs + schema, venv, npm ci, demo substrate); every documented gate reproduced exactly before any change. The audit found the currency-truth class: the Peppol generator hardcoded `currencyID="SGD"` on all 11 amount elements (a USD invoice would transmit internally inconsistent UBL), plus the reports/account-balance hardcodes. All fixed via TDD (8 RED → GREEN, +11 tests): backend **1047P/0F/5S** · vitest 698/698 · e2e 43/43 · rls 13/13 · mobile-nav **17/17** — **working, no Tailwind v4 bug** (translate probe PASS). Byte-identical on the SGD substrate, verified live. 8 screenshots (216-223), `.env.example`s verified truthful, full docs truth pass.

Key deliverables: [P33 plan](/home/z/my-project/ledgersg/docs/REMEDIATION_PLAN_2026-11-28_P33.md) · [P33 report](/home/z/my-project/ledgersg/docs/REMEDIATION_2026-11-28_P33_REPORT.md) · [session 64 log](/home/z/my-project/ledgersg/docs/session_64.md) · [worklog](/home/z/my-project/ledgersg/worklog.md)

**Suggested next:** the credit-note XML minimality, the ISO-4217 currency allowlist, or the registered lint batches — all in the deferred register.
