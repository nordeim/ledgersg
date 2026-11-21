Workspace state check: the previous session's P6 work (11 commits, never pushed) was lost to
a workspace reset — the remote was still at the session-11 state. Two prior losses taught
the lesson: push early. Surviving artifacts (PG data, Redis dump, the e2e bootstrap script,
the screenshot script) were recovered; the full P6 workflow was re-executed with an
incremental-push safeguard after every commit.

Repo re-cloned at the session-11 state (`20069486`). Key documents re-read to rebuild
context (README, AGENTS, PAD, ledgersg_SKILL, session_11/12, P5 plan + report, worklog).
PG data directory survived the reset but the standard empty subdirectories
(pg_logical/snapshots, pg_notify, ...) were stripped again — recreated the full PG17 set and
the server recovered the ledgersg_dev + test_ledgersg_dev databases with schema intact.
Redis restarted from the surviving install. Backend venv + web dependencies reinstalled;
playwright 1.58.2 needed chromium 1208 (cache had 1200) — installed.
All four P5 baselines reproduced exactly (567P/0F/5S backend, 358/358 vitest, 0 typecheck
errors, 10-passed default e2e, 74 pre-existing lint problems).
Audit re-verified against the fresh clone with line numbers: F-4 (allocate() blocks second
allocations on PARTIALLY_PAID — a dead-end state since P5/H-1), F-5 (payment JE broad
Q(account_type=...).first() control-account fallback — AR could land on 1010 Cash on Hand),
F-6 (create_contact never sets AR/AP accounts), F-7 (unallocate() doesn't recompute
amount_paid), F-10 (org update allowlists forward a phantom `address` field — the real
address fields are filtered out), F-11 (detail serializer omits amount_paid/amount_due),
C-5 leftovers (detail/ledger/settings pages render mocks), D-1 (sync route params in a
Promise-params Next.js). The scanner's raw criticals all fall in the documented
false-positive classes (skills/ tree, fixtures, dev credentials).
P6 plan written and validated against the codebase, saved as
docs/REMEDIATION_PLAN_2026-11-22_P6.md.
Tasks 1+2 (F-4/F-5/F-6/F-7): RED suite apps/banking/tests/test_payment_posting_p6.py — 9
failed for the documented reasons (the F-5 decoy test showed AR literally landing on 1010
Cash on Hand; the fail-closed test renames code AND name so neither resolver arm can match).
GREEN: guard widened to ("APPROVED", "PARTIALLY_PAID"); the JE fallback now resolves through
JournalService._get_ar_account/_get_ap_account (P5/H-4 fail-closed resolver); create_contact
assigns default control accounts by contact type; unallocate recomputes amount_paid and
derives the status. test_views fixtures corrected to the real contract (the old fixtures
silently posted AR to the 1100 bank account — the F-5 defect in action). 577P/0F/5S. Ruff
parity. Committed — and the SSH wrapper set up (paramiko shim + deploy key) with the first
safeguard push verified remotely.
Task 3 (F-10): RED — address fields not updatable. GREEN — both allowlists forward the real
model fields; phantom key is a no-op. 579P. Committed + pushed.
Task 4 backend (F-11): RED serializer/endpoint tests in tests/integration/. GREEN — detail
serializer gains amount_paid + amount_due (SerializerMethodField mirroring the DB generated
column). 581P. Committed.
Task 4 frontend: 7 RED page tests against the mock. GREEN — InvoiceDetail type in
use-invoices (useInvoice retyped — it was typed as the client form schema, a type lie), full
detail-client rewrite (payment state, real mutations, truthful states), page.tsx awaits
params (D-1) and drops generateStaticParams. 365/365 vitest, typecheck clean, gated e2e
added. Committed + pushed.
Task 5: RED backend tests for the flat line-level ledger endpoint (the aggregated entries
list cannot drive a line-level table). GREEN — GET journal-entries/ledger/ (entry⋈line⋈
account rows, date/account/source filters, org-scoped). Frontend: useLedger hook +
props-driven ledger-table rewrite + client with loading/error/empty states; endpoints.journal
added to the api-client map. 372/372. Committed + pushed.
Task 6: useOrganisation hooks (detail + PATCH + GST register/deregister, cache-invalidating)
+ settings client replacing the hardcoded defaultValue cards (the GST card drives the
endpoints that seed the GST control accounts). 383/383. Gated settings e2e. Committed +
pushed.
Task 7 (E-1, discovered during e2e bring-up): the first full e2e run 429'd mid-suite — the
refresh endpoint's hardcoded 20/min decorator literal plus the DRF anonymous 20/min budget
stacked on it. P4 settings-knob pattern applied: REFRESH_RATELIMIT_IP (base 20/minute —
production unchanged), config.ratelimits.refresh_ip lazy resolver, development raises the
refresh + DRF budgets copy-on-write. The posture gate test then caught a latent defect:
testing.py's in-place REST_FRAMEWORK mutation corrupted the shared base dict for every other
module in the process — fixed copy-on-write. 588P/0F/5S, security 51+3. Committed + pushed.
e2e full with dev-DB bootstrap via the public API (demo org + contact + 3 invoices with the
real line contract: account_id + tax_code_id per line): first run 18/20 — two real defects
exposed and fixed (the detail page hid the payment state on unpaid invoices — Amount Paid /
Amount Due now render for every non-void document; and getByDisplayValue is unavailable in
this Playwright — getByLabel + toHaveValue instead). Re-run: 20/20.
Screenshots: 6 real-data captures (29-34, _session12) through the real UI login path with
content-based waits — unique md5s, 1440x900, non-blank; the detail capture shows the real
document with its payment state. Committed + pushed.
.env.example verification: every env var read by the code is documented in the three
templates; P6 introduced no new env vars (the E-1 knobs are Django settings). No changes
needed.
Docs truth pass: README (P6 milestone module, counts 991 = 588 + 383 + 20, versions
v0.1.6/v0.4.0, overall P0-P6), PAD (counts + a Page Data Truth section), ledgersg_SKILL
(v1.6.0 project_state + 5 new P6 lessons 15-19), AGENTS.md NUMERIC(10,4) current-precision
claims corrected to NUMERIC(19,4)/NUMERIC(12,6) (verified against information_schema; the
line-821 P3 history note stays — accurate history).
P6 report + this session log + worklog written; final commits pushed via the SSH wrapper
(key shredded after the push).

## Session 12 (P6 Sprint: C-5 Completion & Payment Posting Integrity) — Complete

**Setup & validation**: Re-cloned at the session-11 state after a workspace reset destroyed
the previous session's unpushed 11 commits (second loss — the push safeguard is now
standard). Environment rebuilt on the surviving PG data (empty-dir restoration trick), all
four P5 baselines reproduced exactly (567P/5S, 358 vitest, 0 typecheck errors, 10 e2e
default). Every audit finding re-verified in source with line numbers.

**Remediation (TDD — 21 backend + 21 vitest tests + 3 e2e specs, all RED first)**, per the
validated plan `docs/REMEDIATION_PLAN_2026-11-22_P6.md`:
- **Payment posting integrity** (F-4/F-5/F-6/F-7): PARTIALLY_PAID accepts second
  allocations; the payment JE resolves AR/AP through the fail-closed exact resolver (1200/
  2100 — the broad `.first()` could post AR to 1010 Cash on Hand); contacts get control
  accounts at creation; unallocate recomputes amount_paid/status/amount_due
- **Org address truth** (F-10): the phantom `address` allowlist key replaced with the real
  model fields — an organisation address can finally be updated through the API
- **Invoice detail truth** (F-11 + D-1): amount_paid/amount_due on the detail serializer;
  the detail page is real end-to-end; route params awaited
- **C-5 closed**: real ledger page (new flat line-level endpoint + useLedger + props-driven
  table) and real settings page (useOrganisation + GST register/deregister wiring) — every
  dashboard page now renders real backend data
- **E-1**: refresh/DRF throttle budgets as settings knobs (production posture unchanged);
  the testing.py shared-dict corruption fixed copy-on-write

**Final gate (all executed)**: backend **588P/0F/5S**, invariants 27P, security 51P+3S,
vitest **383/383**, typecheck 0 errors, e2e **20/20 full** (two real defects the first run
exposed were fixed), ruff/eslint parity on touched files, 6 verified screenshots,
`.env.example` cross-checked, docs truth pass (AGENTS NUMERIC precision corrected), worklog
+ session log + report updated.

**Pushed**: 11 conventional commits to `main` via the SSH wrapper — pushed incrementally
after each task (the workspace-reset safeguard) with the remote verified after every push;
the deploy key was shredded after the final push.

**Suggested next**: P7 candidates from the deferred register — the audit-event coverage
beyond banking (M-1), CSRF hardening for the cookie-auth endpoints (M-10), and the
reports/quotes pages which still render template shells.
