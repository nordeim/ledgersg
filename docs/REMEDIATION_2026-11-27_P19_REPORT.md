# LedgerSG — Remediation Report (P19 Sprint: The remove_line Truth Gap, the Modal Semantics Debt, the ContactPicker & the Route Guard)

**Date:** 2026-11-27 (session 38)
**Base commit:** `99786f6a` (main — post-P18, all gates green)
**Plan:** `docs/REMEDIATION_PLAN_2026-11-27_P19.md` (validated against the codebase before execution — every High/Medium anchor hand-verified in source)
**Source inputs:** three parallel deep audits (Mode C) with lead hand-verification of every High finding, plus the documented P18 baselines reproduced on the carried-forward workspace (914P/0F/5S · vitest 601/601 · tsc 0 · eslint 0E/5W · mobile-nav 17/17 — the environment had survived as double-forked daemons; the dev backend and the :8001 rls instance were re-daemonized on the remediated code for the live gates).
**Method:** TDD (RED → GREEN → full gate) for every behavioural fix; lint parity on touched files (achieved 0E/0W — better than parity); conventional commits on `main`; `skills/` excluded from all checks/tests/compilation; **no schema changes** (v1.2.2 carries forward).

---

## 1. Verification Ledger (executed evidence)

| Gate | Result |
|---|---|
| Backend `pytest --reuse-db --no-migrations -q` | **937 passed, 0 failed, 5 skipped** (914 baseline + 23 new P19 tests) |
| Frontend `npx tsc --noEmit` | 0 errors |
| Frontend `npx vitest run` | **619/619 passed** (72 files; 601 baseline + 18 new P19 tests) |
| `npx eslint .` (whole tree incl. `e2e/`) | **0 errors, 0 warnings** — the 5 parity warnings cleared (4 fixed, 1 documented TanStack disable) |
| `npm run test:e2e:full` (live stack) | **40 passed, 0 failed** |
| The runtime-role gate (`scripts/rls_smoke.py --base :8001` as `ledgersg_app`) | **13/13 steps green** |
| Mobile-nav live probe (`scripts/mobile-nav-audit.js`) | **17/17 at 375/800/1280** — **the navigation works; no TailwindCSS v4 bug exists** (ninth consecutive live settlement) |
| The production-CSP smoke (`scripts/prod-csp-smoke.js`) | **5/5** — nonce served, no unsafe-inline, hydration, zero violations, shell rendered (the policy now also carries the report-uri, X-M1) |
| Screenshots | **8 new** (`docs/screenshots/112-119_*_session38.png`) — DOM-verified per surface, md5-unique, non-blank pixel-verified; the P19 proofs: the Radix-ified Receive dialog (role=dialog + aria-label + labeled close), the keyboard-expanded transaction row (aria-expanded + aria-controls), the ContactPicker combobox (aria-activedescendant + aria-selected), the route-guard confirm dialog (stay + discard), and the unified PAID badge on the list (bg-success, live count 9) |
| Schema | v1.2.2 — unchanged this sprint (no DDL; the compose file no longer references the intentionally-omitted beat tables) |

## 2. What Was Done

### Phase 1 — backend: the truth gap + the locking/transaction completion (each: RED → GREEN → suite)

- **BE-P19-H1** `remove_line` — **the P18 commit `51bd46c6` claimed "add_line/remove_line lock the document" but only `add_line` got the lock.** Worse, the RED run exposed that `remove_line` filtered `InvoiceLine` by `invoice=` (the FK is `document`) — the method raised FieldError on EVERY call (an untyped 500 on a live route; no existing test ever exercised it). Now: `transaction.atomic()` + `select_for_update()` + post-lock DRAFT re-check + the real FK — mirrored from `add_line`. The race probe pins Case B (the approver wins the lock; the locked re-read refuses).
- **BE-M3** `unallocate` lock re-order — payment → allocation → document (was allocation-first: the AB-BA inversion against `void`/`allocate` → PG 40P01 → untyped 500). The allocation is read unlocked for ids, re-fetched under the payment lock.
- **BE-M1** `archive_account` — the zero-balance gate now `cache.delete()`s the 5-minute `account_balance` cache before reading (journal postings never invalidated it; a cached zero archived accounts with live lines that then vanished from the trial balance).
- **BE-M2** `create_entry` — the account rows are locked (`select_for_update`) inside the entry's atomic, **pre-locked in sorted order** (a user line order could deadlock two concurrent entries on overlapping account sets — the same inversion class BE-M3 closed).
- **BE-M4** `create_return_periods` — the per-period create runs in its own savepoint; the P18 `IntegrityError` catch without one poisoned the `ATOMIC_REQUESTS` transaction (the next loop query raised `TransactionManagementError` — the exact untyped-500 that fix claimed to prevent; the P18 test never exercised the branch).
- **BE-M5** `check_transmission_status_task` — the **whole body** now runs inside `tenant_context` (the P18 wrap closed after the log lookup: the adapter lookup and the RLS-scoped `log.save()` ran outside — on a real worker the delivery-status write matched 0 rows and silently never landed). The docstring example also gained its required `org_id`.
- **BE-M6** journal list — `prefetch_related("lines")`: the list serializer's 3-queries-per-row (31 queries for 10 entries) is now 2 total.
- **BE-M7** the five `<str:…>` route islands converted to `<uuid:…>` (core fiscal ×3, coa account ×2) — malformed ids 404 at routing like every sibling.
- **BE-L3** `amend_return`'s bare lock wrapped in `transaction.atomic()`.
- **BE-L5** `suggest_matches` — `select_related("contact")` (the N+1).
- **Deferred #5** journal serializer tolerance `0.001` → `0.0001` (the service + DB-trigger boundary, P13/B-13) — the create gate and the detail `balanced` flag now agree with the trigger.
- **Deferred #7** `display_money` — the `is_finite` gate (NaN propagated through `quantize` and rendered the literal string "NaN").
- **BE-L1 INVALIDATED during RED verification** (recorded so it is not re-raised): the audit's "PENDING rows with NULL transmitted_at never get cleaned" — `gst.peppol_transmission_log.transmitted_at` is `NOT NULL DEFAULT NOW()` + `auto_now_add`; NULL cannot exist.

### Phase 2 — frontend: the modal semantics, the keyboard flows, the combobox, the route guard

- **FE-H1** the four banking "modals" (Receive/Make/Import/Reconcile) were hand-rolled `fixed inset-0` divs — no focus trap, no Escape, no dialog semantics on the payment-entry and reconciliation primary flows, violating the repo's own `ui/dialog.tsx` discipline. All four are Radix `Dialog`s now (accessible names via `aria-label`; bounded `max-h-[90vh]` internal scroll for the tall reconcile form; the forms' five unlabeled internal X buttons removed — the Dialog's labeled close covers them).
- **FE-H2** the transaction-row header is a real `<button aria-expanded aria-controls>` — a keyboard-only user could not expand a transaction, therefore could not reach Reconcile at all (WCAG 2.1.1 Level A).
- **FE-M2** **the ContactPicker WAI-ARIA 1.0 combobox — the deferred register's oldest item (carried since P16).** Full pattern: `aria-controls` + `aria-haspopup="listbox"` + `aria-autocomplete="list"` + `aria-activedescendant` roving with `aria-selected`, ArrowDown/Up with wrap, Enter-to-select, Escape, Home/End; the options are real `role="option"` list items (select on `mousedown` — pre-blur); the empty-state row is `aria-hidden`.
- **FE-M3** **the in-app unsaved-work route guard — the deferred register's #2 item.** `UnsavedRouteGuard` (document-capture click interceptor): while the invoice store is dirty, a primary-button click on a same-app anchor is intercepted (preventDefault + stopPropagation in the capture phase), a Radix confirm dialog offers Stay / Discard-and-leave; confirm clears the flag then navigates. Modified clicks (new tabs) and external/hash/mailto hrefs pass through. Mounted in the invoice form beside the beforeunload hook.
- **FE-M1** the bank-account EDIT path's PayNow-UEN length-only check → the shared ACRA `uenRegex` (the create path's validator).
- **FE-M4** the invoices-list PAID badge unified on `bg-success text-void` (was `bg-accent-primary` — two greens for the same status across its two primary surfaces).
- **FE-M5** `scope="col"` on the invoices list/detail `<th>`s (the two highest-traffic money tables were the outliers).
- **FE-L1** the invoice line editor's decorative orphaned `row/rowgroup/rowheader` roles dropped (browsers pruned them — an unlabelled field soup for SR users); every line input now carries row-context labels ("Line N unit price" …).
- **FE-L2/L3/L4** the aria batch: the banking X buttons (removed with FE-H1), the two unnamed invoice-detail back links, the payment/import form field labels (`aria-label` on SelectTriggers/inputs) and `role="alert"` on field errors.
- **FE-L5** the GST checkbox's `accent-[var(--accent-primary,#e8ff17)]` — a non-existent variable whose wrong fallback always won — → `accent-primary` (the token utility).
- **FE-L6** the contrast gate's ratio loop now covers `color-warning` (`bg-warning text-void` is live at 11.45:1).
- **FE-L7** the five eslint parity warnings: 4 fixed (unused interface, unstable lines-memo identity, tax-breakdown deps destructure, auth-provider `router` dep), 1 documented disable (the TanStack `useReactTable` React-Compiler incompatibility — an upstream library limitation, recorded at the call site).
- **FE-L8** the two UEN *edit* surfaces (contacts dialog + org settings) validate with the shared `optionalUenSchema`.

### Phase 3 — cross-cutting: production observability + deployability

- **X-M1** the **enforced** frontend CSP now carries `report-uri ${apiUrl}/api/v1/security/csp-report/` (production branch) — the backend endpoint existed and was tested, but the policy browsers enforce had no reporting: production violations were invisible (the exact failure class P16/FE-C1 fixed would have returned silently).
- **X-M2** the CSV import: a 5 MB size cap (before the memory-doubling decode) + a 10,000-row ceiling, both typed refusals — an authenticated `CanManageBanking` user could OOM a worker with one oversized statement.
- **X-M3** the compose `celery-beat` service removed — its `DatabaseScheduler` requires the `django_celery_beat_*` tables §15c intentionally omits: the documented Docker route crash-looped deterministically.
- **X-M4** the `PG_BASE` parametrization completed: `setup_pg_z.sh`'s initdb check uses `${PG_ROOT}` (was a hardcoded sandbox path — the check always missed on any other host); DEPLOYMENT §3's `PGBIN` derives from `$PG_BASE` (was hardcoded prefix + major).
- **X-L2** the e2e demo-password fallback `demo1234` → `demo1234pass` (18 sites) — the 8-char fallback could never log in under the 12-char register floor.
- **X-L3** the unused `uuid` runtime dependency removed (all generation is `crypto.randomUUID()`).
- **X-L4** `service.py`'s `ALLOWED_HOSTS` read via decouple (the `os.environ`-only read gave service mode split `.env` semantics).
- **X-L5** the ci-summary failure gate includes the `security-scan` job (a required-status check on ci-summary alone would have masked dependency-vulnerability failures).
- **X-L1** the P18 report's `--grep` mechanism claim corrected by erratum (the CI e2e job relies on the specs' own `test.skip(!apiUrl)` guards — no grep exists); the ci.yml header version bumped.

### Phase 4 — gates, captures, deliverables

The full gate matrix re-run green (§1); 8 DOM-verified screenshots
(`scripts/capture-screenshots-session38.js`); this report;
`docs/session_38.md`; the worklog entry; the docs truth pass; the
conventional commits and the SSH-wrapper push.

## 3. Incidents & lessons (recorded for future sessions)

1. **The vacuous-RED traps.** Two first-cut RED probes passed for the
   wrong reasons and were rebuilt before any fix was written: the
   create-serializer tolerance test failed validation on a missing
   `source_type` (not the balance gate); the tenant-context
   savepoint-depth probe passed because Django 6's
   `connection.savepoint_state` is a monotonic counter, not a depth
   gauge — the replacement wraps `tenant_context` with an enter/exit
   tracker. The lesson: a RED that passes for the wrong reason is worse
   than no test — verify the failure is the contract.
2. **The e2e spec adaptations are contract updates, not appeasements.**
   The P19 modal/a11y changes shifted five e2e locators (the
   fixed-position div → the dialog role; the clickable div → the
   expander button; generic line labels → row-context labels; the
   header-button name now includes "Unreconciled" → exact-name
   matching). Each adaptation documents the new contract in place.
3. **The one real e2e discovery:** the import dialog's bank-account
   select was unreachable by name (the label association did not
   surface as an accessible name in the a11y tree) — labeled
   `aria-label="Bank account"`, the same FE-L4 class as the payment
   forms.
4. **The h1 truth convention:** the header logo renders the FIRST h1
   on every page — page-level truth probes must use the LAST (the
   session-36 script knew this; the first-cut session-38 script did
   not).

## 4. Deferred register (updated, carried forward)

**Fixed this sprint (removed from the register):** the ContactPicker
WAI-ARIA combobox and the in-app unsaved-work route guard (the two
oldest P16 items); the journal serializer tolerance and the
`display_money` finite gate (the two S-effort deferreds); the CSV size
cap; the CSP report-uri; the compose beat contradiction; the PG_BASE
fresh-host completion; the eslint parity warnings.

**Still deferred (with rationale):**
- **List pagination** (BE) — needs a per-view design decision + a
  frontend pagination UX; the envelope work below is its prerequisite.
- **List-envelope `{data}`/`{results}` unification** (BE) — 15
  `{results}` sites + 6 `{data}` sites + 1 raw array; a coordinated
  contract change across both tiers; the frontend parses both shapes,
  so it is debt, not breakage.
- **Audit-log `INSERT WITH CHECK (TRUE)`** (schema) — needs the scoped
  INSERT policy design (or a SECURITY DEFINER write path); schema
  change, out of the no-DDL scope.
- **Org-mid-flight dead-letter design** (BE) — needs the persistent
  failure-record model decision.
- **UEN checksum** (BE) — needs the official IRAS algorithm; the
  format-only validator honestly documents this.
- **NULL-context SELECT policies** (schema §17) — the documented
  pre-context membership tradeoff; unchanged.
- **H-05b attachment/threshold models** (BE) — schema-only tables
  without Django models; needs the feature decision.
- **ruff register** (BE) — the mechanical batch (was 1279 at audit
  time); next dedicated pass.
- **The PaymentsTab same-route prefill re-trigger** (FE) — no current
  producer; keyed-remount fix registered for when one appears.
- **The TanStack `useReactTable` React-Compiler incompatibility** (FE)
  — upstream limitation; the disable decision landed (FE-L7); the
  incompatibility itself stays.
- **The middleware token parse without signature verification** (BE-L2
  from this sprint's audit) — defense-in-depth gap; views re-authenticate,
  so no exploit was found; registered for the next hardening pass.
- **The journal detail serializer's per-entry source-document lookup**
  (BE-M6's residual) — N+1 on the detail list surface; the prefetch
  landed on the list; the detail path is used per-entry today.
