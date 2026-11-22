# Session 18 Log — P9 Sprint: Onboarding & Banking Truth (2026-11-22)

Workspace refreshed from the remote (`git pull` brought in `session_18.md`, the P8 raw narrative — the naming convention continues: P9 sprint = session 18, screenshots 47..52_session18, log → session_19.md). Operating docs + P8 artifacts re-read and validated against the tree; the documented state held (647P/5S backend, 418 vitest, typecheck 0, 9+14 e2e — all four baselines reproduced EXACTLY before any change).

Environment: PG + Redis up via the resilient helper. Session-start incident (recovered): the dev DB had been wiped to a 2-table stub since P8 — schema reloaded from `database_schema.sql` (32 tables, 47 NUMERIC(19,4)), suite re-run green before any change. A second drop-and-reload preceded the canonical live phase so the e2e chain and screenshots ran against a freshly bootstrapped org.

Audit (Mode C) per `skills/skills-catalog.md`: the standard scanner pass (one production hit — the documented Storecove docstring placeholder, M-14 deferred) + three parallel deep-audit agents (P8-diff regression audit, deferred-register validation, fresh-surfaces gap audit — the banking frontend had NEVER been remediated by any sprint and its mock-based tests hid three contract breaks). The lead hand-verified every Critical/High finding before planning, including: **the onboarding dead end** (registration creates no organisation; the dashboard's only CTA links to a route that does not exist — a self-serve user cannot use the product at all), the multipart FormData stringify (`"{}"` with a JSON content-type — no bank transaction could ever enter the app), the reconciliation envelope mismatch (the form always said "No matching payments found"), the raw-UUID customer field, the dead Add Account buttons, the dead Make Payment state, the quote-convert flat read (`/invoices/undefined` on every conversion), the untyped invoices list, the InvoiceNow quote-transmission path, the account_type seed gap, the tolerance NameError 500, and the XSD fail-open.

Plan written and validated (`docs/REMEDIATION_PLAN_2026-11-22_P9.md`), then executed task-by-task in TDD with a push after every commit (18 code commits):

- **Task 1 (C-3)** InvoiceNow invoice-only: 2 RED → the type gate + `CanCreateInvoices` parity.
- **Task 2 (B-7/S-1/S-4)**: 4 RED (a NameError 500 and two garbage-date 500s) → the shared helpers + NaN/Infinity rejection; the root requirements.txt retired.
- **Task 3 (C-1)**: the convert envelope pinned at the HTTP level + the hook unwraps `.invoice` (RED: `/invoices/undefined` verbatim).
- **Task 4 (C-2)**: the invoices list sends `type=SALES_INVOICE`; leaked types are labelled.
- **Task 5 (C-4)**: the seed backfills `account_type`; the filter matches either column (3 RED → fresh-org revenue dropdown non-empty).
- **Task 6 (B-1)**: `api.postForm` + FormData-aware headers (2 RED — the import could never succeed).
- **Task 7 (B-2)**: the suggest-matches hook unwraps `{results, count}` and maps contact/score (1 RED against the real envelope).
- **Task 8 (O-1)**: the organisation-creation page ships at the route the dead CTA always targeted (5 tests; the Critical closed).
- **Task 9 (B-4)**: the bank-account dialog (zod via the previously-unconsumed schema; native selects after the Radix-in-jsdom fight; 3 tests).
- **Task 10 (B-3/B-5/K-5)**: the ContactPicker (server-side search with the backend's real filter keys) + the Make Payment form.
- **Task 11 (B-3b)**: allocation sections in both payment forms (clamped inputs) + the invoice detail's Record Payment deep link + `amount_paid`/`amount_due` on the list serializer.
- **Task 12 (B-6)**: payment Void (reason required) + transaction Unreconcile.
- **Task 13 (D-1)**: the aged report bounds by `issue_date__lte=as_at` (a post-as-at document was included).
- **Task 14 (D-2/D-3/D-4)**: the dashboard's invented GST boxes and static trends REMOVED (not backfilled); the dead CTAs route to /reports; the dashboard's first test file.
- **Task 15 (C-5/C-6/K-1..K-4)**: status_history synthesized from timestamps; the CONVERTED badge gates on the persisted link; the generic endpoint's VOID branch delegates to the one engine; housekeeping.
- **Task 16 (S-2/S-3)**: checkSession keeps the session on transport faults (only 401/403 clear); the XSD path fails CLOSED.

Live phase — three iterations, each surfacing real defects the unit gates structurally could not see (never suppressed):

1. **Iteration 1** (22/26): the Record Payment deep link never opened the form — PaymentsTab reads the `?receive=1` params, but the Banking page defaults to the accounts tab, so PaymentsTab never mounted (the tab now defaults from the param; regression-tested). The dialog's GL picker was empty — the seeded bank accounts are CHILDREN of the 1000 header, hidden by the list service's top-level-only default even with a type filter (a type filter lifts the restriction now). The invoices specs were desynced from the page's new type filter.
2. **Iteration 2** (24/26... 4 failed): the bank-account POST 400'd — the dialog sends `paynow_type: null` and the ModelSerializer rejected null while the DB column is nullable and the CHECK allows NULL ("" violates it). Both serializers accept null now; the payload contract is pinned in the dialog's unit test. The is_bank query param ships end-to-end (the dialog had queried the plain list and filtered client-side — the same children problem). The workflow spec was made serial + idempotent, `--workers=1` for the full run, and the strict-mode/locator semantics fixed (overlay scoping, the RCP- prefix, substring reality: "Add Account" is NOT a substring of "Add Bank Account").
3. **Iteration 3 — the canonical run**: DB reset, fresh bootstrap, **e2e:full 26/26** (the banking workflow: dialog → deep link + picker + allocation → multipart import → rendered 100% match → reconcile → invoice Paid), **6/6 screenshots** captured and verified (two VLM-checked: the receive form with the customer chip and the allocation rows; the reconciled transaction with the 100% reconciliation rate).

Also diagnosed during the live phase: a stale orphaned dev server (the npm wrapper kill leaves next-server holding port 3000; a stale runserver served pre-fix code) — the teardown now pkills the process tree (lesson 35).

Docs phase: README (P9 milestone, 1,148 = 668 + 454 + 26, v0.1.9/v0.5.1), PAD v3.6 (+Page Data Truth for banking/org-creation/dashboard), CLAUDE v2.13, ledgersg_SKILL v1.9 (+lessons 31–35), AGENTS P9 patterns, DEPLOYMENT re-verified with P9 spot checks, `.env.example` cross-checked (P9 adds no env vars), P9 report + this session log + worklog.

**Delivered:** 20 commits on `main` (18 code + 2 docs, all pushed), all gates green (backend 668P/0F/5S, vitest 454/454, typecheck 0, e2e 26/26 live + 9+17 default), 6 verified screenshots, `.env.example` verified. Deferred debt registered in the report §3 (contacts/CoA pages, bank-account edit/deactivate, payment detail, GST lifecycle UI, bills creation UI, dashboard computed trends, the Load-more dead buttons).
