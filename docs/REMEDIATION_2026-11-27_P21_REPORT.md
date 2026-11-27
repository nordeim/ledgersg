# LedgerSG — Remediation Report (P21 Sprint: The List-Envelope Unification, the InvoiceNow Evidence Stamp, the Cache-Commit Truth & the Banking A11y Batch)

**Date:** 2026-11-27 (session 42)
**Base commit:** `67512bf1` (main — post-P20, all gates green)
**Plan:** `docs/REMEDIATION_PLAN_2026-11-27_P21.md` (validated against the codebase before execution — every High/Medium anchor hand-verified in source by the lead)
**Source inputs:** three parallel deep audits (Mode C) with lead hand-verification of every High finding, plus the documented P20 baselines reproduced on the session-40 workspace (rootless PG 17 per `docs/setup_pg_z.sh`; Redis 8; the schema loaded into both databases — `test_ledgersg_dev` recreated and loaded this session; the dev stack live on :8000 + :3000; the demo substrate bootstrapped through the public API).
**Method:** TDD (RED → GREEN → full gate) for every behavioural fix; lint parity on touched files (ruff at/below base on every touched file, the new test file clean; eslint 0E/0W whole-tree); conventional commits on `main`; `skills/` excluded from all checks/tests/compilation; **no schema changes** (v1.2.2 carries forward).

---

## 1. Verification Ledger (executed evidence)

| Gate | Result |
|---|---|
| Backend `pytest --reuse-db --no-migrations -q` | **969 passed, 0 failed, 5 skipped** (950 baseline + 19 new P21 tests; 974 collected) |
| Frontend `npx tsc --noEmit` | 0 errors |
| Frontend `npx vitest run` | **641/641 passed** (75 files; 627 baseline + 14 new P21 tests) — two consecutive full runs green |
| `npx vitest run --coverage` | **green at the ratchet** (exit 0; every tier above its floor — the P20 floors unchanged) |
| `npx eslint .` (whole tree incl. `e2e/`) | **0 errors, 0 warnings** (parity maintained) |
| `npm run test:e2e:full` (live stack, remediated code) | **40 passed, 0 failed** (the p10 picker locator updated for the FE-L2 visible-label rename; one earlier login-flake rerun after the Redis flush) |
| The runtime-role gate (`scripts/rls_smoke.py --base :8001` as `ledgersg_app`) | **13/13 steps green** (the :8001 instance restarted with the P21 code) |
| Mobile-nav live probe (`scripts/mobile-nav-audit.js`) | **17/17 at 375/800/1280** — **the navigation works; no TailwindCSS v4 bug exists** (thirteenth consecutive live settlement; the FE audit's compile-verified dead-token sweep found exactly one dead utility — `accent-primary` — fixed this sprint) |
| The production-CSP smoke (`scripts/prod-csp-smoke.js`) | **5/5** (after `npm run build:server` green) |
| The live envelope | `GET /api/v1/auth/organisations/` (the former bare array) verified live returning `{"results": [...], "count": 1}` |
| The bootstrap script | `scripts/bootstrap_demo_substrate_session40.sh` — the dual-shape fallback retired (reads `results`); the §9 contract otherwise unchanged |
| Screenshots | **8 new** (`docs/screenshots/128-135_*_session42.png`) — DOM-verified per surface, md5-unique, non-blank pixel-verified; the P21 proofs: the Reference input named (filled **by label**), the CSV input `sr-only` + label-resolved, the payment card's `role="button"`, the loader live region (captured mid-delay), the lexical GST year heading, the org selector reading the unified envelope |
| Schema | v1.2.2 — unchanged this sprint (no DDL) |

## 2. What Was Done

### Phase 1 — backend: the envelope + the cache/evidence/locking batch (each: RED → GREEN → suite)

- **BE-P21-M6 (the envelope unification — the deferred register's big-ticket item)** Every LIST endpoint now returns `{results, count}`. The 7 non-conforming sites: `core/views/organisations.py:55` (orgs list) + `:216` (fiscal years), `core/views/auth.py:335` (`my_organisations_view` — the repo's one bare array), `journal/views.py:202` (trial balance — `totals` + `as_of_date` survive) + `:267` (entry types), `gst/views.py:202` (IRAS tax-code info) + `:339` (the return-periods POST — `message` survives). Report-style `{data: {...}}` payloads unchanged — the documented convention is *lists → results, reports → data*. The frontend consumers (`use-fiscal` + `fiscal-card` + the auth-provider via one typed `fetchOrganisations` helper), the e2e helpers (p10/p11/banking/invoices — 6 casts), and the bootstrap script were migrated in the same commit. **Bonus truth fix:** `tests/security/test_rls_isolation.py:59` read `response.data.get("data", [])` against the accounts list's `{results}` — a vacuous assertion that always passed (even if isolation broke); now reads the real envelope. Pinned by the 7 new envelope contract tests + the updated shape tests (`test_organisation_api`, `test_journal_workflow`, `test_gst_calculation`, `test_auth_org_context`).
- **BE-P21-M1 (the bank-account default-flag locking)** `set_default` now locks the org's account set (sorted, the `create_entry` pattern — the one-default invariant is org-wide, so two concurrent `set_default` calls serialize instead of leaving two defaults); `update`/`deactivate` read through a private `_get_locked` and save with `update_fields` (the full-row writes clobbered concurrently-committed `opening_balance`-class edits). The deactivate audit `old_data` snapshot no longer records the already-mutated `is_default`. Pinned by the lock-spy, the racing-save no-clobber probe (T2's committed 999.00 survives), and the update_fields capture.
- **BE-P21-M2 + M3 (the cache-commit truth)** The dashboard cache is now invalidated by `void_document` and by manual journal entries (`create_entry`) — the P5/H-3 completion (approve/payments/filings had it; void and manual entries did not) — and EVERY mutation-path invalidation/deletion is registered via `transaction.on_commit` (the two service helpers + the `create_entry` balance deletes): a delete inside the open transaction re-seeds the stale value in the delete→commit window; on_commit fires immediately in autocommit contexts, so non-transactional callers keep the old behavior. Pinned by the `django_capture_on_commit_callbacks` probes (not-called-inline + fires-on-execute) and the seeded-key persistence probes.
- **BE-P21-M4 (the InvoiceNow evidence stamp)** `invoicenow_sent_at` — the column the void/unallocate restore reads (`"SENT" if stamped else "APPROVED"`, the P16/L2 design) — is now stamped on a DELIVERED transmission (`_update_log_with_result`, one `.update()` with an `isnull=True` filter: stamp-once, no status write, the transition map untouched). The branch was dead code (an exhaustive writer sweep found zero writers). Pinned by the DELIVERED-stamp test.
- **BE-P21-M5 (the ValidateBalanceView typed-400 body)** Malformed `lines` — non-numeric debit/credit, dict or string bodies — are clean 400 envelopes (was `AttributeError`/`InvalidOperation` 500s). Pinned by the three malformed-body tests + the valid-body unchanged test.
- **BE-P21-I4b** the redundant function-local `Decimal` import in `apps/invoicing/views.py` removed (P20/L1 added the module-level one).

### Phase 2 — frontend: the banking a11y batch + the envelope consumers + the timezone class (vitest RED first)

- **FE-P21-H1** the Make-Payment Reference input carries `aria-label="Reference"` (the in-file "Notes" pattern, 14 lines below the miss). Pinned by the by-role-name test and live (capture 128: filled **by label**).
- **FE-P21-H2** the CSV import's file input is `sr-only`, not `hidden` — display:none removed it from the tab order AND the a11y tree; keyboard-only users had no path to import a statement. Pinned by the class + label-association test and live (capture 129: `csv-class:sr-only csv-by-label:1`).
- **FE-P21-M1** the import dialog's ids are unique (`import-bank-account`) — the co-mounted TransactionFilters' `bank-account` id no longer collides in the portal DOM. Pinned by the co-mount test (was 2 elements, now 1 + 1).
- **FE-P21-M2** every remaining spinner-only loader is a live region (`role="status"` + `aria-live="polite"` + sr-only text where the loader had no text): banking-client ×2, settings-client ×2, contacts-client ×2, reports-client ×5, fiscal-card, invoicenow-settings-card, allocation-section, reconcile-form. Pinned by the per-surface tests and live (capture 131: the skeleton carries `role="status"`, captured mid-delay).
- **FE-P21-M3** the timezone class completed: `isoYearOf` (the GST year read lexically — `new Date(asAt).getFullYear()` read the RUNNER's year and the F5 tab queried the wrong year's returns for timezones behind UTC) + `localTodayISO` (local calendar day — was the UTC day) in `src/shared/format.ts`, consumed by the reports client (gstYear + defaults), both payment forms, and the payment schema defaults. Pinned by 5 helper tests + the lexical-year probe (capture 132).
- **FE-P21-M4** the payment card carries the P19 transaction-row keyboard contract (`role="button"` + `tabIndex` + Enter/Space + focus-visible, only when a handler is wired). Pinned by the keyboard-activation test and live (capture 130).
- **FE-P21-M5** the reconcile dialog's match selection exposes `aria-pressed` (was border/bg-only — invisible to AT). Pinned by the pressed-state test.
- **FE-P21-L1** the dead `accent-primary` utility (no `--color-primary` token exists) → `accent-[var(--color-accent-primary)]`, compile-verified through the repo's own postcss pipeline with a new design-tokens gate.
- **FE-P21-L2** the ContactPicker takes an optional `labelId`; the invoice form wires the visible "Customer" span — the visible label is now the accessible name (`aria-labelledby` outranks the built-in aria-label). The submit-path unit test + the p10 e2e locator were updated to the new name (the intentional contract change).
- **FE-P21-L3** the `aria-controls` regions always exist (transaction-row's details region + payment-list's allocations wrapper render `hidden` when collapsed) — the attribute resolves in both states.
- **FE-P21-L5 + I4** playwright `video: "retain-on-failure"` (matching the P20 trace rationale — local retries:0 meant on-first-retry recorded nothing); the package.json trailing newline restored.
- **Envelope consumers** `use-fiscal`'s `FiscalYearsResponse` + `fiscal-card` read `results`; the auth-provider reads the org list through one typed `fetchOrganisations` helper (4 call sites); the e2e org-list helpers + the fiscal-card/settings-page/auth-provider test mocks updated to the new shape.

### Phase 3 — cross-cutting: the docs truth pass + the script/env alignment

- **The X-P21 doc batch (9 Medium + 5 Low, one pass):** README badge 1,555 → 1,650; the README test-execution section (1,596/937/619/942 → 1,650/969/641/974); the README milestone order (P21 first, P20 second — P18 was first); CLAUDE's misattributed "P18" block retitled to the P19 sprint it carried the gate of; AGENTS header (P18 → P21) + `Database: v1.2.1` → v1.2.2 + `P0–P17` → P0–P21 + the current-truth block refreshed; the SKILL quick-ref v1.2.2 + the NUMERIC widening attributed to v1.1.0 (was v1.2.0); the PAD lint row "0 errors / 5 warnings" → 0E/0W + the ruff register re-measured (1307/936); the ci.yml header (969, P21) + the eslint step comment (0 warnings since P19); the API guide's superseded "Current" labels → "Historical" + the "Last Updated" line P21; the README stack table Tailwind 4.0 → 4.2 (the lockfile truth).
- **API guide 3.2.0:** the P21 addendum — the 7-route envelope-change table (old shape → new shape) + the behavioural notes (the evidence stamp, the on-commit invalidation, the typed-400 body, the default-flag locks); the metrics row post-P21.
- **DEPLOYMENT.md:** the header re-verified frame (session 42 / P21, 969P/641) + the §7 expected outputs + the frontend gate counts.
- **README/CLAUDE/AGENTS/PAD/SKILL:** the P21 milestone sections (README + CLAUDE), the status headers (CLAUDE/AGENTS/SKILL frontmatter), the PAD P21 note + version bumps (README v0.3.6/v0.6.6 rows, SKILL 2.9.0, PAD 3.15.0).
- **AGENTS.md** gained the P21 lessons section (the bare-array envelope debt, on_commit as the only honest invalidation point, the dead evidence column, the vacuous-assert envelope trap, sr-only vs display:none).
- **.env.example (the owner's named task):** all three files verified truthful variable-by-variable by the cross-cutting audit (nothing stale, nothing missing, both apps, the decouple caveat present) — no P21 change reads a new env var; the deliverable already existed and is committed; no changes required this sprint.
- **Bootstrap script:** the dual-shape org-list fallback retired (`results` only, the comment updated).

### Phase 4 — gates, captures, deliverables

The full gate matrix re-run green (§1); 8 DOM-verified screenshots
(`scripts/capture-screenshots-session42.js`); this report;
`docs/session_42.md`; the worklog entry; the docs truth pass; the
conventional commits and the SSH-wrapper push to main.

## 3. Incidents & lessons (recorded for future sessions)

1. **The patch-context lifetime trap (test-side):** the first
   on_commit probe failed for a TEST reason — the `patch` context
   manager exited with the `with` block, so executing the captured
   callbacks ran the REAL invalidator, not the spy. The fix: nest the
   patch AROUND the capture. The vacuous-RED discipline caught it (the
   assert message showed `spy.call_count == 0` post-execution).
2. **The login flake reproduced (the documented class):** one e2e run
   failed at an API login after ~40 logins; the Redis flush + rerun
   pattern resolved it (the P4 lesson holds). The ISOLATED rerun
   initially kept failing for a different reason — the npm script's
   inline `E2E_API_URL` differs from a direct env override (the
   double-prefix 404); always re-run isolated specs with
   `E2E_API_URL=http://127.0.0.1:8000`.
3. **The a11y rename ripples to locators (by design):** the FE-L2
   visible-label rename changed the ContactPicker's accessible name
   from "Search customer" to "Customer" — the unit submit-path test
   and the p10 e2e locator were updated to the new name in the same
   commit. An accessible name is a contract; rename it once, update
   every consumer.
4. **The dev servers were stale (the P13 lesson holding):** both
   backends run `--noreload` — they had to be restarted before the
   live envelope could be verified (the first live probe of the new
   shape only worked after the daemonized restart).
5. **The loader capture needed a delayed route:** the FE-M2 live proof
   captures the loading state by routing the bank-accounts response
   with a 4-second delay + `domcontentloaded` navigation — `networkidle`
   would consume the delay and the skeleton would be gone.

## 4. Deferred register (updated, carried forward)

**Fixed this sprint (removed from the register):** the list-envelope
unification (7 sites + the consumers + the bootstrap script + the
vacuous RLS assert); the InvoiceNow evidence stamp; the void/manual-entry
dashboard invalidation + the on_commit placement; the bank-account
default-flag locking; the ValidateBalanceView 400 contract; the two
banking a11y Highs + the import-dialog ids + the loader live regions +
the timezone class + the payment-card keyboard contract + the reconcile
selection semantics + the FE L-batch (L1/L2/L3/L5); the docs truth
batch; the API guide 3.2.0.

**Still deferred (with rationale):**
- **List pagination** — the per-view limit/offset design + frontend UX;
  the envelope prerequisite is NOW DONE (this sprint); `LedgerView`
  line-level materialisation is the first target.
- **ruff mechanical batch** — re-measured 936 production / 1307
  whole-tree (W293 ×376, I001 ×123, F401 ×121, B904 ×65, UP045 ×45);
  lint-parity-on-touched-files only this sprint.
- **Audit-log `INSERT WITH CHECK (TRUE)`** — needs the scoped INSERT
  policy design (or a SECURITY DEFINER write path); schema change, out
  of the no-DDL scope.
- **BE-L3 config-class locking** (coa/tax-code/contact/org services) —
  low blast radius; next locking pass.
- **BE-L4 Peppol log-state writes unlocked** — Celery retry
  interleaving; operational only.
- **BE-I3 CSV `errors[]` raw DB exception strings** — auth-gated;
  consider typed row-error messages.
- **Org-mid-flight dead-letter design; UEN checksum; NULL-context
  SELECT tradeoff; H-05b models; PaymentsTab prefill (no producer);
  TanStack React-Compiler incompatibility; the middleware
  membership-cache revocation window; the journal detail N+1;
  BE-M3-P20 fiscal close race; BE-M4-P20 reconcile FX comparator;
  BE-M6-P20 CSV dedupe (DDL); FE-M2-P20 route guard sentinel design;
  FE-M3-P20 drawer × dialog trap; X-L2/I1/I2 CI hardening; X-M8
  version-story reconciliation** — all carried forward unchanged.
