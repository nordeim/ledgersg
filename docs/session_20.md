I'll resume the P8 remediation from where it stopped. First, let me verify the current workspace state — the working tree should hold Task 3 changes plus the uncommitted P8 plan, with Tasks 1+2 already pushed.
The repo state is much further along than the summary suggested — P8 appears fully completed locally (all 15 tasks, through the final worklog/report/screenshots commit `8bb9ebee`), with a clean working tree. The current prompt references `session_17.md`, the P8 report, and `session_18.md` — consistent with this being the **P9 cycle (session 17)**. Let me verify whether the P8 commits were pushed and check the key file.
P8 is fully complete and **pushed** (local main == origin/main, 0 unpushed commits). The SSH key file was cleaned up (as per protocol), so I'll recreate it from the current message when pushing. This run is the **P9 cycle (session 17)**: review P8 outputs, audit, plan `REMEDIATION_PLAN_2026-11-22_P9.md`, execute with TDD, then push.

Let me refresh and read the P8 outputs first.
`git pull` brought in one new commit: `b6bdfb40 update session log` which created `docs/session_18.md` — the placeholder for this session (P9/session 17), same pattern as prior cycles. Now let me read the P8 outputs.
P8 is fully verified complete. Now this run is the **P9 sprint**. Let me read the remaining P8 outputs (session_17.md polished log, worklog) and check the session-numbering convention precisely.
The convention is now clear: P8 sprint = "session 16" work → polished log `session_17.md`, raw narrative `session_18.md` (pulled at P9 start). So **P9 sprint = session 18 work**: screenshots `47..*_session18.png`, polished log → `session_19.md`, worklog entry "Session 18".

Let me set up my P9 sprint plan and start the environment + docs review.
Session numbering confirmed (P7=14, P8=16 → **P9=Session 18**). Services are up. Now let me verify the DB state and review the core docs (P8 truth-pass versions).
psql timed out waiting for a password prompt. Let me retry with PGPASSWORD set properly, and read the P8 plan in parallel.
The dev DB has only **2 tables** — it was wiped since P8 (likely by a sandbox PG data reset). The documented recovery: drop/recreate + reload `database_schema.sql` as postgres. Let me investigate and recover.
`ledgersg_dev` only holds the 2 token_blacklist tables — a stray partial state. The repo's `docs/setup_pg_z.sh` is the documented setup path. Let me check what it does before running the recovery.
The setup script covers the PG server itself (already running). The DB recovery is the documented P8 procedure. Let me check the testing settings contract first, then recover.
Confirmed the contract: pytest uses the schema-loaded DB named in `.env` (`ledgersg_dev`) with `--reuse-db`. Now the documented recovery — drop/recreate + reload the schema.
Only 2 tables after load — suspicious. The domain tables may live in non-public schemas, or the load partially failed. Let me check properly.
Schema recovered and verified: **32 tables across 7 domain schemas + public, 47 NUMERIC(19,4), 0 load errors** — the canonical state. (The earlier `public`-only count of 2 was misleading; the pre-recovery DB was indeed a partial stub missing the live-phase framework tables anyway.)

Now reproduce the P8 baselines exactly.
Backend baseline reproduced exactly: **647 passed, 5 skipped**. Now the frontend gates.
All four baselines reproduced **exactly** (647P/5S backend, 0 typecheck errors, 418/418 vitest, 9+14 e2e). Now the audit phase — first the skills catalog and the P8 plan's deferred register (the P9 candidate pool).
Now let me check the audit tooling convention from AGENTS.md and dispatch the P9 audit.
Prior convention: a standard secrets scanner pass + parallel deep-audit agents. Let me run the scanner pass now.
One scanner hit — the Storecove placeholder (documented FP class from prior sessions). Quick verification, then dispatch the deep audits.
Scanner profile confirmed (single hit = documented docstring FP; M-14 deferred). Now dispatching the three parallel deep-audit agents, mirroring the P8 audit structure that caught the live G-1 regression.
Three strong audit reports: consolidated register is **1 Critical, ~10 High** across the three agents, including two "grew-worse" deferred items and one unregistered live 500. Per my discipline, I must lead-verify every Critical/High myself before planning. Let me verify them in batches.
C-1 and F1 confirmed exactly as reported. Next verification batch.
Both confirmed (InvoiceNow has no type gate + loose permission; tolerance raises bare `ValidationError` = NameError). Next batch.
#18 confirmed (seed never writes the VARCHAR; filter reads it). Let me finish verifying H2, H3, H4, and the payment form (H1).
H2, H3, H4 all confirmed. Final verification batch — H1, H5/H6, and the medium findings that will shape the plan.
All Critical/High findings verified by hand. Quick final batch on the mediums, then I write the P9 plan.
All findings verified. Now let me look at the P8 plan's structure to mirror its conventions, then write the P9 plan.
P8 plan structure captured. Before writing the P9 plan, let me validate the key task assumptions against the codebase (serializer shapes, endpoint params, form seams).
All seams validated. Now writing the P9 remediation plan.
Plan saved. Now validating the remaining plan assumptions against the codebase before executing.
All plan assumptions validated (org POST uses `OrganisationCreateSerializer` + full-setup service; metrics carry `gst_payable` only; `allocations` inline field confirmed; `related_document` needs adding to the list serializer for the C-6 badge).

Plan validated — starting execution. **Task 1 (C-3): InvoiceNow quote gate.** Let me study the existing test pattern first.
Writing the Task 1 RED test.
The test DB lost its schema again — the same signature as the P8 incident. Let me diagnose immediately.
That query hit the wrong database (no `-d` flag → the `postgres` DB). Let me check `ledgersg_dev` specifically.
Found it: `ledgersg_dev` was dropped to a 2-table stub — a subagent ran a bare pytest to verify a finding (agent A's "live DB not runnable" remark), which triggered the documented `create_test_db` drop. My audit prompts forbade file edits but not suite runs — lesson registered. Recovering now (the documented 30-second path).
RED confirmed for the right reasons (the quote test currently sails past the missing type gate all the way to the Celery broker; the member test gets non-403; the happy path with the mocked task passes). Let me check Redis is actually alive (kombu got connection refused), then implement GREEN.
RED is precise: **500 instead of 400** — the quote sails past the only guard into the transmission pipeline (eager Celery then fails on the AMQP transport). Now GREEN: the type gate + permission alignment.
Wrong file for the first edit — the service change belongs in `document_service.py`. Redoing correctly.
任务 1 GREEN (21 个测试通过，包括所有现有的 peppol 测试)。完整回归 + Lint，然后提交。
Full suite **650 passed** (647+3). Checking whether the 29 ruff errors are pre-existing parity or new from my edits.
Parity clean (29 pre-existing, 0 new). Committing Task 1 with the plan document, then pushing. First, recreate the SSH key from the user's message.
Task 1 pushed and verified (`5311cfee`). Now **Task 2 (B-7 + S-1 + S-4)** — the hardening riders. Let me study the CASES pattern and the suggest-matches view.
The defect is exactly as registered (bare `ValidationError` = NameError; plus the same raw `UUID()` cast class P8 fixed in siblings). Let me check the journal-view fix pattern and the invoicing list flow, then write RED.
Writing the RED tests for Task 2 (extending the CASES register).
RED confirmed — the NameError is visible verbatim in the failure output. GREEN now.
All 21 CASES pass. Now the S-4 rider and the banking test regression check.
Full suite **654 passed**. But ruff flagged 3 fixable on banking/views.py — checking if my edit introduced an unused import.
The tree is clean (Task 2 already committed) — that's why stash was empty. Comparing against the parent commit instead.
All 3 remaining findings are pre-existing (parent had 5; my edit resolved 2). Parity improved. Pushing Task 2.
Task 2 pushed. Now **Task 3 (C-1): the convert envelope, pinned end to end**. Reading the existing P8 quotes tests and hook test patterns.
Critical detail to check before writing the pin test: what `@wrap_response` does to a successful payload.
`wrap_response` passes success payloads through — the envelope is exactly `{"message", "invoice"}`. Writing the backend pin test + studying the hook test pattern.
Writing the backend pin test and the frontend RED test.
Backend envelope pinned. Now the frontend RED — the hook test against the real backend shape.
RED confirmed (`/invoices/undefined` verbatim). GREEN — the hook fix.
All 3 are pre-existing (original file imports), but they're trivial autofixes on a file I touched — fixing on sight per the P8 precedent, amending into the unpushed commit.
Task 3 pushed. Now **Task 4 (C-2): the invoices list shows invoices**. Reading the client and its tests.
Now updating the page test — asserting the filter argument and the badge rendering.
Pre-existing warning (line 16, untouched by my edit) — parity holds. Full suite, commit, push Task 4.
Task 4 pushed. Now **Task 5 (C-4): seeded accounts carry account_type**. Finding the seed function and how orgs get their chart.
The structure is clear. Let me see the account_type codes and find where the seed function ends.
Insertion point found. Let me check the schema-conformance invariant (my SQL edit must not break it) and the coa service API, then write RED.
Conformance gate compares columns only — my UPDATE is safe. Writing the RED test.
3 RED as documented. GREEN — the seed backfill + the OR-filter.
Now the service OR-filter and the DB function refresh.
GREEN. Full suite + conformance gate, then commit and push Task 5.
Parity exact (29/29, test file clean). Committing and pushing Task 5.
Task 5 pushed. Now **Task 6 (B-1): real multipart for statement import.** Reading the api-client request core and existing tests.
Writing the RED tests: the fetch-level form test and the hook-level import test.
Full RED. GREEN — the `postForm` helper + FormData-aware headers + the hook switch.
All green (422/422, auth path unaffected by the header change). Committing and pushing Task 6.
Task 6 pushed. Now **Task 7 (B-2): reconciliation matches render.** Reading the hook, its tests, and the form.
Confirmed — the test mocks the wrong shape entirely. Rewriting the hook tests to the REAL backend envelope (RED).
RED confirmed. GREEN — the hook unwrap + field mapping.
Form tests pass (6/6), typecheck 0 errors, full suite 422. Committing and pushing Task 7.
Task 7 pushed. Now **Task 8 (O-1): organisation creation — the Critical onboarding fix.** Examining the existing seams.
All seams confirmed. Let me check the shared UI form components, then write the RED test + implementation.
Writing the RED test for the org-creation page.
RED. Now implementing: the endpoint, the hook, and the page.
Now the hook — appending `useCreateOrganisation` to use-organisation.ts.
Now the page and client component.
The test needs a QueryClientProvider wrapper. Fixing the render helper.
5/5 GREEN. Full gates + commit + push.
All gates green (427 vitest, 0 type errors, eslint clean). Committing and pushing Task 8.
The Critical is closed. Now **Task 9 (B-4): the bank account dialog.** Reading the serializer fields and the banking client buttons.
`is_bank` is exposed and my C-4 fix makes the GL validation work for seeded accounts. Building the dialog + wiring. First, the page test structure.
Schema's ready and unconsumed. Writing the dialog component and its test.
Wiring the dead buttons in banking-client.
The state landed in `PaymentsTab` but the buttons live in `AccountsTab` — let me check the component structure and fix the placement.
The dialog must render in every branch (loading/error/empty/list). Let me restructure the component cleanly.
Typecheck clean. Writing the dialog test.
Two matches (the Radix listbox stays mounted). Fixing with role-scoped queries.
The repo pattern for Radix portals is raw `.click()`. Switching the submit test's portal interactions.
Radix Select is fighting the test harness. Let me check the repo's established form-select pattern (invoice-form's posting-account select).
The canonical pattern: keyboard navigation. Applying it.
Let me probe whether the Radix selection actually commits inside the dialog.
Radix-in-dialog jsdom quirks are eating time. Pragmatic call: native `<select>` for the dialog's form controls (fully testable, keyboard-accessible, same styling). Converting.
Found it — the mock GL id `"gl-bank-1"` isn't a UUID and the zod schema requires one. Fixing the fixture.
3/3 GREEN. Full gates for the restructured banking client.
The restructure broke existing tests — investigating.
The page tests auto-mock the hooks module (undefined exports) — the dialog now needs stubs. Fixing both test files' mocks.
All banking tests green (102). Checking that eslint error from before, then full gates.
`any[]` is pre-existing (the original interface, untouched). Parity holds. Full gates and commit.
Task 9 pushed. Now **Task 10 (B-3 + B-5 + K-5): real contact picking + Make Payment.** Reading the current pieces.
The make schema even includes allocations (Task 11 ready). Building Task 10: the contacts hook fix, picker component, and both forms.
Now the shared ContactPicker component.
Integrating the picker into the receive form.
Now the MakePaymentForm — reading the receive form fully to mirror it accurately.
Typecheck clean. Checking the existing receive-form test for the contact field references.
Only 2 tests to update. Patching them and writing the new picker + make-form tests.
Two component issues: the dropdown needs focus to open, and a prefilled `value` must display its contact (needed for Task 11's deep link too). Fixing both.
The chip body still reads `selected`. Fixing to `effectiveSelected` throughout, plus the bank-account aria-label.
The clear-test needs a controlled harness (fixed-prop artifact). For the make test, let me probe which field fails validation.
My fixture IDs are invalid UUIDs again (`a-…`, `s-…` prefixes) — zod correctly rejects them. Fixing fixtures.
The probe passes — let me inspect the actual test file's state and run it isolated.
The raw `.click()` isn't act-wrapped, so the state update hasn't flushed before the query. Using `fireEvent.click` instead.
Clear test green. Checking the make test's actual call args now.
The flow works — MoneyInput formats to `"250.00"`. Fixing the assertion.
All 108 banking tests green, typecheck clean. Full gates + commit Task 10.
Task 10 pushed. Now **Task 11 (B-3b): allocations + Record Payment deep link.** Checking the list serializer fields and hook filters.
The list serializer lacks `amount_paid`/`amount_due` — allocation rows need them. Backend RED first.
Backend GREEN. Now the frontend: hook filter, types, allocation section, deep link.
Now the allocation section component.
Now integrating the section + prefill props into both payment forms.
Both forms done. Now the deep link — the invoice detail Record Payment action.
Now the banking side — PaymentsTab reads the deep-link params.
Typecheck clean. Writing the Task 11 tests.
Controlled-value harness needed (my mock never feeds allocations back). Fixing the test.
5/5. Adding the prefill payload test and the detail-page gating test.
Same missing aria-label on the receive form's bank trigger. Fixing.
The bank fixtures use `"acc1"` — not UUIDs. Fixing.
The `c-` prefix again — my prefill id isn't a UUID. Fixing.
All green. Now the invoice-detail gating test.
All green. Full gates + backend regression + commit Task 11.
Two mock gaps from the new hooks. Fixing both test files.
Task 11 pushed (443 vitest). Now **Task 12 (B-6): correction paths.** Reading the two list components.
Void requires a reason. Implementing the row wrappers with inline reason forms.
Now the PaymentList row wrapper with the reason form, and the transaction unreconcile.
Typecheck clean. Updating the affected test files with the new hooks and cases.
My insertion clobbered the `mockUsePayments` declaration. Fixing.
10/10. Now the transaction side.
The actions live in the expanded section. Expanding first in the test.
The handler is on the inner div, not the card. Adjusting the test.
All green (447/447, 0 type errors). Committing and pushing Task 12.
Task 12 pushed. Now **Task 13 (D-1): aged report honours as_at.** Writing the RED test.
The aged tests live in the app dir (collected — the glob matches everywhere). Reading its fixtures.
RED as documented. GREEN — the date bound.
Task 13 pushed (661 backend). Now **Task 14 (D-2/D-3/D-4): dashboard truth.** Reading the surfaces.
Now implementing the dashboard truth pass. First check what the dashboard tests assert.
No dashboard tests exist at all — which is exactly how the fake data survived. Writing RED first.
All RED. Verifying the harness matches the real data flow before implementing.
Harness works — just a fixture collision (two "SGD 40,000.00"). Fixing, then implementing.
Now the GST chart — only real data.
The chart's table section still indexes the old 5-item array. Fixing it.
4/4. Checking the chart's toggleable table view for stale rows.
The 2 errors are pre-existing; the 2 unused-import warnings are mine. Cleaning them.
All green (451 tests, 0 errors, eslint parity restored). Committing and pushing Task 14.
Task 14 pushed. Now **Task 15 (C-5/C-6 + housekeeping): the truth batch.** Checking the model timestamps first.
3 RED. Applying GREEN across the batch.
The `at` values should be ISO strings for a clean contract. Fixing the serializer.
Backend GREEN. Frontend half: the stale type + the truthful badge.
The P8 test encoded the conflated contract. Updating it to the truthful one.
The engine accepts DRAFT/SENT only — the APPROVED row correctly has no Convert button. Fixing my assertion.
`transition_status` receives `user_id`, not `user`. Checking both signatures to bridge correctly.
7/7 workflow tests pass. Full suite + ruff parity, then commit.
Task 15 pushed. Now **Task 16 (S-2 + S-3): session + Peppol posture.** Reading both surfaces (plus fixing the leftover C408 nit in my test file).
No provider tests exist — writing both RED tests.
Backend S-3 GREEN (117 peppol tests). Now the checkSession half.
The test hung. Let me inspect the provider's structure before retrying.
The command had a stray quote that hung the shell — nothing ran. Cleaning up and redoing.
RED precise (network fault currently redirects; 401 already does). GREEN — the split.
The patch aborted on the import line — checking the actual import.

继续任务 16 —— checkSession 补丁因导入行而中断。让我检查一下实际的导入。
The import line includes `setAccessToken, clearAuth` — my pattern didn't match, so nothing was written. Applying the patch correctly now.
2/2 GREEN. Full gates, then commit Task 16.
All green (453 tests, 0 type errors, 1 warning). Verifying the warning is pre-existing parity, then committing.
Parity holds (the exhaustive-deps warning is pre-existing). Committing and pushing Task 16.
All 16 code tasks complete and pushed. Now **Task 17: the live gate** — banking e2e spec, screenshots, docs truth pass, report, session log, worklog. Updating my plan status first.
P8 的 live-phase 脚本是可复用的。让我研究一下 import CSV contract 和 capture script，然后构建 banking e2e spec。
CSV 契约已明确。让我检查一下 import form UI 和 bootstrap tail（已审批的发票金额）。
我来阅读一下 `reconcile form` 和 `payment form` 的 `submit selectors`，以便构建一个健壮的 spec。
I have all the selectors. Writing the banking e2e spec — the full P9 workflow loop.
Let me review and fix the spec's third test — I left a stray locator and need to verify the import button labels.
Fixing the third test's selectors — checking the import form title for scoping.
Now rewriting the spec with correct scoping.
Now checking the default e2e run (gated skips), then updating the capture script.
Default e2e correct (9 passed + 17 gated). Reading the rest of the capture script.
Default gating verified. Now writing the P9 capture script with the six new screenshots.
Fixing the invalid regex line in the capture script.
Syntax OK. Now the P9 live-phase runner.
Before the expensive live run, let me verify combobox collisions on the Payments tab (PaymentFilters).
One more flow check — the import form's success behavior (inline result vs auto-close).
The overlay closes on success (`onSuccess` → `setShowImportForm(false)`). The spec is sound — running the full P9 live phase now (single invocation, reaper-proof).
22/26 passed; 4 failures to diagnose plus a capture-script bug (`.first()` — property, not method, in Python Playwright). Let me get the failure details.
"No bank-type accounts" — the GL select is empty. Let me check the actual DB state for the demo org's chart.
Chart has 3 bank-type accounts, but the dialog saw none. Let me check the other error contexts and probe the API directly.
The e2e caught a **real bug in my Task 11 deep link**: the params are read in `PaymentsTab`, but the Banking page defaults to the **Accounts tab** — so `PaymentsTab` never mounts and the receive form never opens. Let me verify the tab structure and fix.
Confirmed — `defaultValue="accounts"` strands the deep link. Before fixing, let me also probe the accounts API for test 1's "No bank-type accounts" failure.
0 bank rows in the API despite 3 in the DB — and 65 vs 102 accounts. Let me check for multiple orgs.
One org (the demo org) has the 102 accounts with 3 bank rows, yet the API returns 65 rows with `is_bank: false` for all. Something's off in the serializer/model mapping. Checking the Account model.
The reaper killed the debug backend. Restarting and probing in one shot.
The API omits the bank rows entirely — 65 of 102. Let me read `list_accounts` fully for hidden filters.
**Root cause found**: `list_accounts` defaults to **top-level accounts only** (`parent__isnull=True`) when no code/search/parent filter is given — the `account_type` filter doesn't lift it. The bank accounts (1100 series, children of the 1000 header) are invisible to the dialog, and the leaf revenue accounts are invisible to the invoice form. My C-4 backfill was necessary but not sufficient. Let me check the seed's revenue children, then fix with a RED test.
Good news: revenue accounts are top-level (the form works); only the **bank accounts are children**. Adding the RED test for the type-filter + children case.
Backend fix GREEN (666 passed). Now the deep-link tab fix in BankingClient.
Adding the regression test for the deep-link tab default.
My new test needs the `useBankAccounts` mock set. Fixing.
The tab switched (progress) — the payments content now needs its hooks mocked too.
The fix works (aria-selected="true") — the query just collides with the filter's inner tabs. Scoping with `.first()`.
The transactions test file's navigation mock lacks `useSearchParams`. Adding it.
All green (454 tests, 0 type errors). Two e2e-discovered bugs fixed. Now the fourth failure — the pre-existing invoices spec. Checking the list ordering hypothesis.
The list IS ordered — but let me check the spec's API fetch: my C-2 type filter may have desynced it from the page.
Confirmed: the spec fetches without `?type=` — it sees QT-00001 (newest, 2026-11-05) as results[0] while the page now correctly lists invoices only (my C-2 fix). Aligning the spec's fetch to the page's contract.
Now fixing the capture script's `.first()` property bug and re-verifying.
Both fixes in. Let me verify the invoices spec's remaining assertions tolerate a PAID first invoice (the banking test settles it before the invoices spec runs).
The void-flow spec may now pick the PAID invoice (no Void button since P8). Let me read its target selection and the bootstrap invoice dates.
All 3 invoices share one issue date, so INV-00003 (settled to PAID by the banking test) will be the first row — the void spec clicks row #1 and expects a Void button. Fixing the spec to target a voidable row.
Typecheck clean. Committing the e2e-discovered production fixes + spec, then re-running the live phase.
Re-running the full live phase with the fixes in place.
e2e failed again — let me see which tests and why.
**Still empty** — my service fix covered the `account_type` path, but the dialog queries the **plain list** (no type) and filters `is_bank` client-side; the top-level-only default still hides the bank children. The clean fix: an `is_bank` filter param end-to-end. RED test first.
Now the frontend: the hook gains `is_bank`, the dialog uses it.
Dialog tests pass. Verifying test 2's failure this run was just the cascade.
The is_bank fix is in. Before re-running, let me diagnose the capture script's button timeout from the web dev log.
Only 14 root GETs in the log — the capture never hit this server. A stale server may be holding port 3000. Checking.
A run-2 orphan server (06:23) still holds port 3000, and the backend is up. Let me reproduce the capture steps directly to see the actual page state.
Reproduced: in the empty state only "**Add Bank Account**" exists — and "Add Account" isn't a substring of it. The capture script's literal locator can never match. Fixing with a regex that covers both branches.
All capture locators verified against the substring semantics. Now improving the live-phase teardown (the run-2 orphan survived `kill $WEB_PID` — npm wrapper died, next-server child lived) and cleaning up before the re-run.
State is clean for a full re-run. Running the live phase again.
Big progress — tests 1+2 passed (bank account + payment settled), 5/6 shots captured. Two e2e failures left: banking test 3 and the quotes spec. Checking both.
Two distinct issues. Checking the DB for the payment and reading the quotes spec assertions.
No payment row at all, yet test 2 passed (settled row was visible). Something concurrent or a config issue. Checking the playwright workers config.
`fullyParallel: true` — **my three banking tests run concurrently with each other and every other spec**, racing on shared live data. That also explains the odd states. Let me verify the payment table name and read the quotes spec failure.
The bank account AND payment both vanished after their tests passed. Something concurrently destructive. Checking every e2e spec for API mutations.
Nothing destructive in the specs. Let me examine the run-3 backend log for the actual requests and DB.
The bank-account POST returned **400** at 14:52 — yet test 1 passed. And an approve at 14:55:29 from another spec. Let me see the full request trail and reproduce the 400.
The tail truncated the failure list — likely 4 failed (all banking + quotes). The root issue: the bank-account POST 400s. Restarting the backend to reproduce the exact error.
**Found it**: the serializer rejects `null` paynow fields — the dialog sends `paynow_type: null` when unset. The e2e caught a contract break the mocked unit test couldn't see. Checking the serializer + model to fix both sides properly.
The model says `blank=True` but the DB CHECK (per the P8 lesson) only allows NULL or enum values. Checking the actual schema constraint.
Column is nullable; the serializer just needs `allow_null`. Writing the backend RED test (POST with null paynow → 201).
Two `validate` methods (create + update) — scoping with more context.
Both validators share the context — and the "" → None normalization is correct for both. Applying to both deliberately.
Backend GREEN (668). Pinning the wire contract in the dialog's unit test, then diagnosing the quotes spec failure.
The quotes snapshot looked healthy — suspicious. But first, a structural issue I must fix: `fullyParallel: true` runs my banking tests 1→2→3 **concurrently** — a workflow chain racing itself. Serializing the spec.
Cross-file parallelism also races my writer-spec against the reader-specs on the shared live DB. Setting `--workers=1` for the full run only.
State check before re-run — counting approves in the run-3 log to understand the document states.
One approve in the log, but two drafts became approved. Checking journal-entry timestamps to date the approvals.
The quotes spec failed in both runs — possibly a real break, not a race. Let me look at the failure screenshot.
The snapshot shows a healthy page — everything the spec asserts exists. I need the verbatim error. Bringing up the stack and running just the quotes spec.
Quotes passes in isolation — the run-3 failure was concurrency (now eliminated by `--workers=1`). Verifying the banking chain with all fixes.
The debug backend never started — a stale backend (pre-fix serializer) still holds port 8000. Killing it and re-running.
Test 1 passes now. Test 2 fails at line 82 — checking.
The form opened perfectly — the URL just carries a trailing slash (`/banking/?receive=1`). Fixing the regex.
Test 1 isn't idempotent — the previous run's account persists (duplicate 400). Unique-ifying the fixture, then I'll reset the DB for a clean final run.
Now resetting the DB for the clean canonical run and executing the final live phase.
24 passed, only test 2 failing now. Checking its failure point.
The re-run failed only because the backend was down (live phase tore it down). Restarting the stack and re-running test 2 properly.
**Strict-mode collision**: the form's submit and the tab's header button both match "Receive Payment". Scoping to the overlay.
Test 2 passes end to end. Now test 3.
The import works (test got to reconcile) but no match row renders. Checking the DB and the reconcile form state.
The payment is numbered **"RCP-00001"** (not "REC-") — my match regex missed it. Checking the match row's actual structure, then fixing the matcher.
The match renders perfectly (100% score) — only my `/rec-/i` regex is wrong (payments are numbered "RCP-"). Fixing.
The reconcile worked — "Reconciled" just appears twice (badge + timestamp). Scoping with `.first()`.
State exhaustion from repeated debug runs (both outstanding invoices settled). The spec is correct for a fresh bootstrap. Resetting and running the final canonical live phase.
**26/26 e2e passed, 6/6 screenshots captured** — the live gate is green. Running the final full gates, then committing.
Live gate pushed. Now VLM-verifying the two key screenshots.
The CLI isn't printing results. Checking the VLM skill's invocation pattern.
Screenshot 49 verified (customer chip + allocation section real). Now screenshot 50.
Both screenshots VLM-verified (Reconciled badge, 100% rate, real allocation rows). Now the docs truth pass — starting with `.env.example` and surveying the P8 docs conventions.
`.env.example` aligned (P9 adds no env vars). Now the docs pass — reading the P8 milestone format in README to mirror.
Writing the P9 docs pass — README first.
The earlier edits died before writing. Re-applying the milestone and table rows.
README done. Now CLAUDE.md, PAD, ledgersg_SKILL, AGENTS, DEPLOYMENT.
Docs done. Now the P9 report — first gathering the commit graph.
Now the session log and worklog entry.
Final verification sweep and the closing commit.
Both hits are legitimate historical references. Final docs commit and push.
The P9 sprint is complete — remote `main` == local HEAD (`2a7b498e`), 19 commits pushed, deploy key shredded.

**What shipped this session (Onboarding & Banking Truth):**

- **The Critical closed (O-1):** organisation creation ships at the route the dashboard's dead-end CTA always targeted — self-serve users can now actually use the product
- **The payment workflow is real end to end:** true-multipart statement import, rendered reconciliation matches, a searchable contact picker, inline allocations that settle invoices, the Record Payment deep link, the bank-account dialog, and void/unreconcile corrections — the P5/P6 engine finally has a UI
- **Truth fixes:** the dashboard's invented GST boxes/trends removed, the invoices list type-filtered, seeded accounts filterable, the quote-convert envelope pinned, InvoiceNow invoice-only, aged reports as-at bounded, XSD fail-closed, sessions survive transport faults
- **The live gate earned its keep:** three e2e iterations surfaced three contract breaks no mocked unit test could see (null-PayNow 400, the deep-link tab default, the is_bank children invisibility) — each root-caused and fixed, ending **26/26 live e2e green**

**Final state (all verified):** backend 668P/0F/5S · vitest 454/454 · typecheck 0 · e2e 9+17 gated / 26/26 live · 6 screenshots (2 VLM-verified) · docs truth-passed · `.env.example` cross-checked.

Next-step candidates are registered in the report §3: contacts/CoA management pages, bank-account edit/deactivate, the GST lifecycle UI, and bills creation.
