Repo cloned successfully. Let me set up a task plan and begin the deep review.
Now let me read the Project Architecture Document and key session docs.
Now let me read the P4 plan and report to learn the conventions for remediation planning.
Now let me skim AGENTS.md and README.md key sections to complete the picture.
I have a good picture now. Let me check the session_9 log convention and the key skills, then start environment setup.
Now let me start environment setup. First, the PG setup script and skill:
Now let me set up PostgreSQL using the repo's adapted script:
PG 17 is up. Now create the ledgersg role and databases, then load the schema:
Schema loaded. Now Redis — the suite's hard prerequisite:
Redis is up. Now the backend venv and frontend install (in parallel would be nice, but let me do backend first):
Now reproduce the documented baselines. Backend first:
Backend baseline matches exactly. Now frontend:
All four baselines reproduce exactly (534P/0F/5S backend, 354/354 vitest, 0 typecheck errors, 9+7 e2e). Let me update progress and start the audit phase.
The catalog confirms the established skill set. Now let me validate the new audit report's findings against the codebase, starting with the Criticals:
C-2/C-4 confirmed. Now C-5 (frontend mocks) and C-3 (CI):
All audit findings verified in source. Now deeper study of the code paths I'll remediate — payment allocate, journal reversal, account codes:
I have everything needed. Let me check the .env tracking history and the testing settings, then write the remediation plan:
The audit is validated. Let me study the Peppol transmission path to complete my remediation design:
Important discovery — the task/service wiring has an ID mismatch bug. Let me verify the model and adapter:
I now have complete validated understanding. Let me write the P5 remediation plan:
Plan saved. Now validating the plan's remaining assumptions against the codebase:
Plan fully validated against the codebase. Now executing — starting with Task 1 (repo hygiene):
Now update `.gitignore`, CI password, and testing.py:
The CI test step must export `DB_*` for my testing.py change. Let me check how base.py's `config` works and fix the CI env:
Now the testing.py env-based DB config:
Task 1 green. Task 2 — remove the broken dead module:
Tasks 1-2 done. Task 3 (InvoiceNow) — first study test patterns and Celery config:
The test fixture itself has the wrong account map — key intel for Task 6. Let me probe the blast radius:
Task 3 RED tests. First check the Peppol settings model:
Now writing the RED tests for Task 3:
10 RED for the right reasons, 2 preserved contracts pass. Now GREEN — the service seam first:
Now fix the task and the cleanup task:
Now rewire `send_invoicenow` and `get_invoicenow_status` in document_service.py:
The model uses `document_id` (UUIDField) not an FK, and `peppol_message_id` is a UUIDField. Fixing my tests:
The service needs local imports (established pattern to avoid cycles):
`transmitted_at` is `auto_now_add` — must bypass via queryset.update in tests, and `created_at` doesn't exist. Fixing:
Fixing the UUID serialization and updating the old task tests that encoded the buggy wiring:
Task 3 GREEN (546 passed). Ruff check and commit Tasks 1-3:
My change added 5 F405 findings (star-import `config`). Adding the explicit import:
My 3 new B904s need `from` clauses:
All lint-clean. Committing Tasks 1-3:
The stash-pop unstaged things. Let me verify what Task 1's commit actually captured:
The commit is missing the untracked-file removals. Investigating:
The stash cycle reverted the untracks. Re-doing them and amending the Task 1 commit:
The deletions are unstaged (stash-pop artifact). Staging explicitly this time:
Tasks 1-3 committed. Now Tasks 4+5 — RED tests for amount_paid and void reversal:
Running without `--reuse-db` may have reset the test DB. Checking and restoring:
The model default is `""` which violates the CHECK; passing explicit NULL works:
Perfect RED — 4 failures for exactly the right reasons. Now GREEN:
Now the void() reversal + allocation release:
The method is `create_reversal`, and I must mirror the smart reversal-date fallback. Fixing:
Tasks 4+5 GREEN (551 passed). Lint check and commit:
Now Tasks 6+7. First, check how tests can call the SQL seed function:
Writing the RED tests for Tasks 6+7. First check which existing tests post purchase invoices with GST (blast radius):
Clear. Writing the RED test file for control accounts, money precision, and line numbering:
The conftest already seeds sequences — using get_or_create:
The seed function already seeds all sequences. Removing my duplicate creation:
The conftest org already has sequences — the seed function will conflict. Clearing them first (mirrors a fresh org):
RED confirmed for the right reasons. Fixing the `posted_by` NOT NULL (need a real user):
All 6 RED for exactly the right reasons. Now GREEN — rewriting the resolvers:
The first script failed before writing — resolvers not yet replaced. Re-applying:
Duplicates exist (the exact anti-pattern #8). Removing the leftover old definitions:
Now update the conftest fixture to the real chart and fix the naive datetime:
558 passed, full regression clean. Lint and commit:
Task 8 — RED tests for dashboard cache invalidation + real alerts:
The fail-closed resolver works — my test org needs the 2600 account:
Both RED for exactly the right reasons. Now GREEN — the real alerts view:
Now wire cache invalidation into the mutation services:
Task 9 — RED tests for org service fixes:
RED confirmed. Now GREEN — fix the service:
The toggle's full-chart reseed conflicts — it must seed ONLY the GST accounts. Checking the exact schema definition:
Task 10 — frontend invoices list. Study the patterns first:
The backend returns `document_number/contact_name/total_incl`. Writing the RED vitest tests:
RED confirmed (component missing). Now implementing:
Now retype `useInvoices` to the real backend contract:
All clean. Now extend the e2e spec for the list page:
Default e2e green with the new gated spec. Committing Task 10:
Now the final gate. Full verification round first:
`.env.example` verified accurate. Adding the testing.py note, then the docs truth pass:
Docs done. Now the full e2e + screenshots in a single invocation (the reaper lesson). First check the dev DB state:
Dev DB is empty — bootstrap the demo user first, then the single-invocation run:
The create endpoint requires `lines`. Checking the real frontend contract:
All 3 invoices created. Now the single-invocation e2e:full + screenshots script:
17/17 e2e green. Now screenshots (verify backend alive in the same invocation):
Need the frontend too. Starting both in one invocation:
The `networkidle` wait hangs on Next dev's HMR socket. Fixing the script:
The script wrote to the wrong relative path — checking:
All 5 screenshots captured. Verify non-blank + hash-unique, and check the invoices shot shows real data:
All verified. Visual check of the key evidence shot (real invoices list):
Screenshots verified. Now the session log, P5 report, and worklog:
Now update worklog.md with the session 11 record:
All 10 P5 commits on main. Now the push — reading the SSH wrapper instructions:
Now deploy the shim outside the repo and materialize the key:
Dry-run green. Real push:
The P5 sprint is complete and pushed. Here is the summary:

## Session 11 (P5 Sprint: Truth Restoration) — Complete

**Setup & validation**: Cloned the repo, rebuilt the environment from scratch (rootless PG 17 + Redis 8 + both venvs), and reproduced all four P4 baselines exactly (534 backend / 354 vitest / 0 typecheck errors / 9+7 e2e). Every Critical/High finding from `docs/ledgersg-audit-report.md` was re-verified in source — plus I found a bug the audit missed: the Peppol task passed a **log id** where an **invoice id** was expected, so auto-transmit could never succeed.

**Remediation (TDD — 38 new tests, all RED first)**, per the validated plan `docs/REMEDIATION_PLAN_2026-11-21_P5.md`:
- **Repo hygiene** (C-1/C-3/H-9): untracked the `.env` files (re-committed by a P4 `git add -A`), 211 `.pyc`, 54 `dist/`, 10 `.bak`; CI now uses a per-run generated DB password
- **Real InvoiceNow** (C-2): send/status wired to the real transmission pipeline; retention-safe cleanup that never deletes delivery evidence (IRAS 5-year)
- **Accounting truth** (H-1/H-2): `allocate()` writes `amount_paid`; payment void reverses the journal and releases allocations
- **Fail-closed control accounts** (H-4): output tax no longer lands on Accrued Expenses (2600/1600/1200/2100 exact)
- **Money/lines** (H-5/H-6), **dashboard truth** (H-3/H-10), **org service** (M-5/M-6/M-7), **real invoices list page** (C-5 part 1)

**Final gate (all executed)**: backend **567P/0F/5S**, invariants 27P, vitest **358/358**, typecheck 0 errors, e2e **17/17 full**, ruff/eslint clean on touched files, 5 verified screenshots, docs truth pass, worklog + session log + report updated.

**Pushed**: 10 conventional commits (`24692ff2..5cdaf70d`) to `main` via the SSH wrapper — remote verified at `5cdaf70 == local HEAD`, deploy key shredded. The `.env.example` is included and tracked.

**Suggested next**: P6 — the remaining mock pages (invoice detail, ledger, settings, reports) using the now-proven list-page pattern.
