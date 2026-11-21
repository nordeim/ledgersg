A previous session left workspace artifacts in place. Let me inspect the current state of the repo and any in-progress work.
Working tree is clean — the previous session completed and pushed P2 work. Now I'll execute the new phase (P3). Let me refresh from remote first.
Workspace refreshed. Now marking task 1 complete and reading the core docs.
Now let me read the remaining core docs.
Now the architecture doc and skill file.
Now the history docs (task 3).
session_6.md is the transcript of the previous P2 session. Now let me read the P2 plan and report, plus the deployment template.
Context is clear. Now let me read the deployment template and skills catalog, and check the current test-suite config state.
The catalog is established from prior sessions. Now let me validate the current state: recent changes, test configs, and environment.
Both test configs exist and are P2-green. Now let me validate the environment — check PostgreSQL/Redis status and reproduce the test baselines.
Both services are up (redis-cli just wasn't on PATH). Let me verify DB state and schema version.
That hung on a bad query. Let me run simpler checks separately.
The shell seems blocked by the earlier interactive psql password prompt. Let me test recovery.
Shell recovered. Now with PGPASSWORD set and no-prompt flags.
Both services healthy. Now verify schema state and reproduce the backend baseline.
Schema state matches. Now reproduce the backend test baseline (documented: 514P/0F/5S).
Backend baseline reproduced exactly (514P/0F/5S). Now frontend baselines.
All baselines reproduce the documented P2 state exactly. Let me spot-check the P2 code changes (the "recent changes" audit focus).
P2 service changes reviewed — solid. Now the views and document_service changes.
P2 diffs verified in source. Now auditing for the P3 scope: H-03 numeric overflow risk, the `effective_on` frontend wiring gap, and test-suite extension opportunities.
The dropdown uses a hardcoded list. Let me check the gst-engine rates and the schema's tax code list.
Now let me quantify the H-03 numeric overflow risk and check model max_digits.
Let me live-verify the H-03 overflow risk in the actual database.
H-03 verified live: hard overflow at 10^6. Now let me run the repo's audit skill (as prior sessions did) and check env templates.
The runner scanned the whole tree including `skills/` (excluded by instruction). Re-scoping to `apps/` only.
Same false-positive classes as sessions 3/5. Re-verifying the production-code hits.
All scanner criticals confirmed as false positives (docstrings/test fixtures/dynamic template literals). Now let me verify the P2 fix works live and demonstrate H-03 through the API.
Key results: P2 rate resolution verified live (2023→0.0800, list effective_on→single SR row). The calculate endpoint computes 2M fine (no persistence), so H-03 bites on the persist path. Let me check the iras-info endpoint and env templates.
`ALLOWED_HOSTS` is read but missing from the backend template — a small gap. Now let me check the invoice page structure and tax-code hook for the frontend wiring plan.
Notable: the invoice form submit is still a TODO stub. Let me check the invoices hook and API client for the real creation path.
Two real findings: the form's submit is a stub while `useCreateInvoice` exists unused, and `useInvoicePDF` reads the token from `localStorage` (prohibited + broken). Verifying usage:
Let me check whether the backend PDF endpoint exists and look at the invoicing URL config.
The backend PDF endpoint exists. Now let me check the document-create contract to scope the form-wiring task properly.
The line contract needs `account_id` — the form lacks it. Let me check the DecimalField shapes and the conformance gate before finalizing the plan.
The gate checks types only — I'll extend it for precision. Now let me verify the ALTER approach works on the generated column before committing to it.
As suspected — the generated column blocks the ALTER. Testing the drop-recreate sequence:
Migration approach validated. Let me check how orgId flows client-side (needed for the new hooks).
The audit is complete. Now writing the P3 remediation plan (task 8).
Plan saved. Now validating its assumptions against the codebase before execution.
`discount_pct`/`discount_amount` are real columns — the discount question resolves as a backend `add_line` fix. Now the accounts endpoint shape:
No accounts in either DB. Let me check how accounts get created (seed vs org setup vs fixtures).
All assumptions validated. Let me record the refinements in the plan, then begin execution.
Plan complete. Now executing **Task 1 (C-1/H-03)** — TDD: RED test first. Let me check the existing test patterns for document creation.
I have the pattern. Let me check the JournalService posting API for the journal-side test.
Now writing the RED test for Task 1.
**RED confirmed: 5/5 for the audited reasons** (47 live NUMERIC(10,4) columns — the schema rg count of 80 included comment lines). Now GREEN: patch the schema file.
Now generating the §16 migration from the live census and appending it.
Schema patched. Now applying the §16 migration to both databases.
47 columns widened in both DBs, zero stragglers. Verifying idempotency and the generated column:
Migration is idempotent and the generated column is restored. Now the model/serializer sweep:
All model sites widened. Now implementing `add_line` discount support:
Let me wire `discount_pct` through `_add_lines` too:
Now extending the conformance gate with precision assertions:
Two issues: the new gate caught a real pre-existing drift, and my test used a phantom attribute. Let me investigate both:
Both diagnosed: `exchange_rate` model over-declares (pre-existing drift my gate caught — schema is truth: 12,6), and my test used the phantom `total_amount` (model field is `total_incl`). Fixing both:
The fixture only opens January 2024 (documented in the skill's debugging guide). Dating the test documents inside it:
Task 1 invariants GREEN (20 passed). Full backend regression check:
**Task 1 complete**: 519P/0F/5S (+5 new), lint clean, both DBs migrated. Committing:
Task 2 (D-3) now — TDD RED first. Let me check the established hook-test pattern:
Now writing the RED tests for Task 2 (hook + engine rateOverride):
**RED confirmed.** Now implementing GREEN — first the engine rateOverride:
Now the tax-codes hook and the api-client `endpoints.gst` addition:
Hook + engine GREEN (62 tests). Now the component wiring — checking for an existing line-row test:
**RED confirmed** (no account select, static 9% preview). Implementing the line row:
The row now references `account_id` — adding it to the line schema:
The preview test passes (108.00 — server rate works). The two failures are jsdom/Radix pointer-capture issues. Checking the setup mocks:
Duplicate matches (trigger + option). Switching to `findAllByText`:
Line-row GREEN. Now Task 3's RED tests — the submit adapter:
RED confirmed. Implementing the adapter:
Adapter GREEN. Now the form-submit RED test:
That's the wiring gap (form passes no `accounts`). Let me see the form's remainder, then implement GREEN:
Now rewriting the invoice form with the full wiring:
The DOM-listener approach is hacky. Refactoring to `watch("issue_date")` and cleaning the rate map typing:
The form now needs auth context. Adding the mock (following the repo's hook-mocking pattern):
Existing tests use `fireEvent` for such interactions (bypasses jsdom pointer-events checks). Adjusting:
Let me try keyboard-driven selection (bypasses pointer events cleanly):
Four type errors — fixing each:
Typecheck clean. Full vitest regression check:
346/346 (324 + 22 new). Now **Task 4 (D-2)** — the PDF auth fix. Checking the existing api-client test:
Appending the blob-path RED tests:
RED confirmed. Implementing the api-client refactor:
Now fixing `useInvoicePDF` to use it:
Task 4 GREEN (10/10, no localStorage reads). Now **Task 5** — the new e2e specs:
13 e2e tests now (was 6). Running the default (backend-less) suite:
The login form uses native `required` validation, not zod text. Fixing the test to match the real contract:
The alert node is an empty placeholder. Asserting on the error text instead:
Default suite GREEN (9 passed, 4 gated-skips). Now the full run — first find the demo user's password:
The e2e needs a known password and a revenue account. Making the spec self-sufficient:
Setting the demo password and starting the backend for the full e2e run:
Auth tests pass. The me-response shape is wrong — checking the actual contract:
The backend refresh needs the token in the body — the frontend sends none. Let me see how the provider actually persists sessions:
Sessions live in memory only — so the e2e must do a real UI login and SPA-navigate. Checking the nav:
Rewriting the spec with real UI login + SPA navigation:
No login POST fired at all — checking the input constraints:
`minLength={8}` — "demo" never fires. Setting an 8-char demo password:
Login works now — just a trailing-slash regex mismatch:
All 3 GREEN. Full suite confirmation:
Passes consistently in isolation — the full-suite failure was a first-compile timeout under parallelism. Hardening timeouts:
Likely the login rate limiter (10/min per IP) from my repeated dev runs. Flushing the rate-limit cache and rerunning:
**Full e2e: 13/13 GREEN.** Confirming stability with a second run + default suite:
Both suites stable. Final frontend gate before committing Tasks 2-5:
Pre-existing errors; my change added one warning. Fixing it cleanly:
Object-identity deps break the memo. Reverting to the proven field-level pattern (pre-existing warnings, no new ones):
All gates green (349 vitest, 0 tsc, clean eslint, 13/13 full e2e). Committing Tasks 2-5 in four atomic commits:
Now Task 6 — the backend `.env.example` completeness fix:
Complete (15/15). Committing Task 6:
Now **Task 7** — starting with the deployment guide. Checking `setup_pg_z.sh`'s parameterization first:
The script provisions rootless PG; ledgersg adds its role/DBs. Writing the deployment guide:
Verifying the §16 extraction command from the guide actually works:
The extraction works. Now updating README.md:
Now CLAUDE.md → v2.8.0:
Now AGENTS.md session-7 lessons:
Now refreshing `ledgersg_SKILL.md` (v1.2.0 → v1.3.0):
Skill updated. Now **Task 8: screenshots**. Checking the existing naming and writing the capture script:
All 5 captured. Verifying uniqueness and content programmatically:
Screenshots verified. Now writing the P3 report:
Now the session log and worklog:
All docs written. Running the complete final gate on the full change set:
**All gates green.** Committing the docs batch:
8 commits, clean tree. Now the push — reading the wrapper skill instructions:
Shim and paramiko ready. Deploying the key securely:
Dry-run clean (fast-forward 5b23743..14217fd2). Executing the real push:
The wrapper's own step-6 verification already confirmed `remote main == local HEAD (14217fd)` before shredding — the independent probe fails only because the key is now destroyed (expected). Cleaning up dev servers and closing out:
## Session 7 — P3 Sprint complete

**Pushed:** 8 conventional commits to `main` (`5b237743..14217fd2`) via the SSH wrapper — remote ref verified, key shredded, working tree clean.

**Audit** (recent changes + skills-driven sweep): all 24 scanner "criticals" re-verified as false positives; real findings **C-1/H-03** (verified live: `numeric field overflow` — all money capped at S$999,999.9999, below the S$1M GST threshold), **D-1** (New Invoice submit was a console.log stub), **D-2** (PDF download read the token from `localStorage` — mandate violation and broken), **D-3** (hardcoded 9% preview), **D-4/D-5** (env + suite gaps).

**Remediation (TDD, all RED→GREEN):** schema **v1.1.0** with all 47 monetary columns at `NUMERIC(19,4)` + idempotent §16 in-place migration (applied to both DBs) + precision-enforcing conformance gate (caught a pre-existing `exchange_rate` drift) + server-side discount; the invoice form now really creates documents (account select + pure payload adapter); `api.blob()` on a single auth path; server-effective tax codes; 25 new vitest + e2e 6→13 tests (`test:e2e:full`).

**Final gate (executed):** backend **519P/0F/5S** · invariants 20P · security 32P/3S · vitest **349/349** · typecheck 0 · e2e **13/13** (default 9+4 gated skips).

**Delivered:** [P3 plan](/home/z/my-project/ledgersg/docs/REMEDIATION_PLAN_2026-11-21_P3.md) · [P3 report](/home/z/my-project/ledgersg/docs/REMEDIATION_2026-11-21_P3_REPORT.md) · [DEPLOYMENT.md](/home/z/my-project/ledgersg/docs/DEPLOYMENT.md) (fresh-host guide) · [session_7.md](/home/z/my-project/ledgersg/docs/session_7.md) · [worklog.md](/home/z/my-project/ledgersg/worklog.md) · refreshed [ledgersg_SKILL.md](/home/z/my-project/ledgersg/ledgersg_SKILL.md) (v1.3.0) · 5 new screenshots in `docs/screenshots/`.

**Suggested next:** the cross-reload session-persistence design (newly registered debt — the refresh flow posts an empty body), then H-02 base-currency reporting.
