# LedgerSG — Remediation Report (P20 Sprint: The void/transition Lock Completion, the CSV Transaction Poisoning, the E2E First-Run Truth & the Test-Config Ratchet)

**Date:** 2026-11-27 (session 40)
**Base commit:** `6ca32a96` (main — post-P19, all gates green)
**Plan:** `docs/REMEDIATION_PLAN_2026-11-27_P20.md` (validated against the codebase before execution — every High/Medium anchor hand-verified in source by the lead)
**Source inputs:** three parallel deep audits (Mode C) with lead hand-verification of every High finding, plus the documented P19 baselines reproduced on a freshly-cloned, freshly-bootstrapped workspace (rootless PG 17 via `docs/setup_pg_z.sh` per `skills/rootless-postgresql`; Redis 8; the schema loaded into both databases; the dev stack live on :8000 + :3000; the demo substrate bootstrapped through the public API).
**Method:** TDD (RED → GREEN → full gate) for every behavioural fix; lint parity on touched files (ruff clean on the new test files; the F821 cleared); conventional commits on `main`; `skills/` excluded from all checks/tests/compilation; **no schema changes** (v1.2.2 carries forward).

---

## 1. Verification Ledger (executed evidence)

| Gate | Result |
|---|---|
| Backend `pytest --reuse-db --no-migrations -q` | **950 passed, 0 failed, 5 skipped** (937 baseline + 13 new P20 tests) |
| Frontend `npx tsc --noEmit` | 0 errors |
| Frontend `npx vitest run` | **627/627 passed** (73 files; 619 baseline + 8 new P20 tests) |
| `npx vitest run --coverage` | **green at the RAISED ratchet** — whole-suite floor 62/51/52/63 → **71/60/68/71**, with `src/app/**` + `src/providers/**` now measured (the P20 blind-spot fix) and new per-glob floors: app 73/64/71/73 · components 82/74/68/83 · providers 61/60/58/60 · `**/__tests__/**` excluded from measurement |
| `npx eslint .` (whole tree incl. `e2e/`) | **0 errors, 0 warnings** (parity maintained) |
| `npm run test:e2e:full` (live stack, remediated code) | **40 passed, 0 failed** |
| The runtime-role gate (`scripts/rls_smoke.py --base :8001` as `ledgersg_app`) | **13/13 steps green** |
| Mobile-nav live probe (`scripts/mobile-nav-audit.js`) | **17/17 at 375/800/1280** — **the navigation works; no TailwindCSS v4 bug exists** (eleventh consecutive live settlement) |
| The production-CSP smoke (`scripts/prod-csp-smoke.js`) | **5/5** (after `npm run build:server` green) |
| The e2e first-run truth (X-H1) | the banking helper is contact-self-sufficient; the §9 bootstrap script completes steps 1-5 idempotently (double-run executed green); the live suite 40/40 |
| Screenshots | **8 new** (`docs/screenshots/120-127_*_session40.png`) — DOM-verified per surface, md5-unique, non-blank pixel-verified; the P20 proofs: the Notes/Terms label association (by-label resolves + the `for` attrs), the named back link, the combobox blur dismissal (`aria-expanded true → false` across a Tab), the single-h1 dashboard (brand as `<p>`), the chart's valid ARIA row |
| Schema | v1.2.2 — unchanged this sprint (no DDL) |

## 2. What Was Done

### Phase 1 — backend: the locking/transaction completion (each: RED → GREEN → suite)

- **BE-P20-H1 (+M2)** `void()` — the affected documents are now `select_for_update()`-locked in **sorted-id order BEFORE** the allocation deletes, and the recompute runs under the locks. Pre-fix: a plain `filter().distinct()` read, an unlocked SUM, an unordered full-row save — a T2 `allocate()` committing between the SUM and the write was silently lost (`amount_paid` diverged from the allocations table until the next allocation event; the P14/H-1 "allocations are the truth" invariant). The sorted pre-lock also closes the AB-BA class between two concurrent voids over shared documents. Pinned by: the lock spy, the lock-order recording probe, and the interleaving probe (T2's committed 50.00 allocation survives the void — `amount_paid` 50.00, never the stale 0.00).
- **BE-P20-H2** CSV import — the per-row `BankTransaction.objects.create` now runs in its own `transaction.atomic()` **savepoint** (the exact class P19/BE-M4 fixed for `create_return_periods`), and the amount parse gained a magnitude bound (`abs(amount) >= 1E15` → a typed row error). Pre-fix: one DB-level row error (a NUMERIC(19,4) overflow — `money("1E+20")` is a 21-digit Decimal) poisoned the transaction, every subsequent row failed with "current transaction is aborted" (swallowed), and the final audit-log INSERT raised outside the try → untyped 500, the `errors[]` contract never delivered. Pinned by: the poison-row test (the two valid rows import, the poison row lands in `errors[]`) + the Python-parse regression guards.
- **BE-P20-H3** `transition_status()` — the row is locked (`select_for_update` inside the atomic), the transition map re-validated **post-lock** against the current status, and the save narrowed to `update_fields` (status + the approve fields). Pre-fix: the plain read + stale full-row save could overwrite a concurrent `approve_document()` commit (SENT written over an APPROVED, journal-posted document) and clobber concurrently-committed totals. Pinned by: the lock spy, the Case-B interleaving probe (the stale DRAFT→SENT transition refused post-lock), and the no-clobber probe (the racing totals update survives).
- **BE-P20-M1** `allocate()` — the deduplicated document ids are pre-locked in **sorted order** (the `create_entry` pattern, P19/BE-M2); the per-allocation loop reads the pre-locked instances. The user-supplied allocation order was an AB-BA deadlock vector. Pinned by the order-recording probe.
- **BE-P20-M5** `create_entry()` — `cache.delete(f"account_balance:{id}")` for every distinct account the entry touches. The 5-minute balance cache was seeded by balance GETs and never invalidated by postings (the P19 fix patched the archive gate only). Pinned by the cache-seed probe.
- **BE-P20-L1** the module-level `Decimal` import in `apps/invoicing/views.py` (ruff F821 — a latent NameError masked only by the serializer's default). Cleared.
- **BE-P20-L2** the `allocate()` service seam gates positive amounts (the DB CHECK turned zero/negative into an untyped IntegrityError for non-DRF callers). Pinned by the typed-refusal test.
- **BE-P20-L3** `unreconcile()`'s payment lock carries the `org_id=` filter every sibling lock carries. Pinned by the captured-kwargs contract test.

### Phase 2 — frontend: the a11y Highs + the guard/combobox hardening + the config ratchet (vitest RED first)

- **FE-P20-H1** the invoice form's Notes/Terms textareas: `id` + `htmlFor` pairing (register() does not generate ids — the bare labels left the two controls unnamed on the primary money-entry form). Pinned by the by-role-name + association tests, and live (capture 120: `notes-by-label:1 terms-by-label:1 for-attrs:2`).
- **FE-P20-H2** `aria-label="Back to invoices"` / `"Back to quotes"` on the two icon-only back links (the fix already existed in `invoice-detail-client`; these two routes were the outliers). Pinned live (capture 121: `back-link-by-name:1`).
- **FE-P20-M1** the ContactPicker dismisses its listbox on blur — a `requestAnimationFrame`-deferred close guarded by `wrapperRef.contains(document.activeElement)`, so the pointer `mousedown` selection still wins the race (the P19 contract) while Tab-away now closes (the WAI-ARIA pattern — the dangling open listbox overlay). Pinned by the two blur tests + live (capture 122: `aria-expanded` true→false across a Tab).
- **FE-P20-M4** the gst-f5-chart's data-table fallback: a real `role="row"` owning the `columnheader` cells (the old `rowheader`-as-container was an invalid ARIA owned structure the browsers pruned — the P19 FE-L1 class on a surface P19 did not touch). Pinned by the owned-structure assertion + live (capture 124).
- **FE-P20-M7** `formatDateOnly` in `src/shared/format.ts` — date-only strings render with `timeZone: "UTC"` (the UTC-parse + local-display off-by-one for timezones behind UTC); the invoice detail consumes the shared formatter. Pinned by the date-identity tests.
- **FE-P20-L2** the sidebar brand `<h1>` → `<p>` (every dashboard page rendered two h1s). Pinned live (capture 123: `h1-count:1 brand-as-p:2`).
- **FE-P20-L3** the primary loading blocks are live regions (`role="status"` + `aria-live="polite"`): the dashboard, invoices, and reports clients (the dashboard spinner also gained an sr-only text equivalent).
- **CFG batch (the owner's named task):** `vitest.config.ts` — `src/app/**` + `src/providers/**` measured (they were ratchet-invisible blind spots carrying most of the money-flow UI), `**/__tests__/**` excluded from measurement (the helper was silently counted), per-glob floors added for the app/components/providers tiers at their measured values, the whole-suite floor RAISED 62/51/52/63 → 71/60/68/71 (including the tiers raises the measured floor — a ratchet that rose with its surface), the `src/stores/**` exclusion documented; `playwright.config.ts` — `trace: "retain-on-failure"` (local runs have `retries: 0`, so `on-first-retry` produced no trace for local failures), `locale: "en-SG"` + `timezoneId: "Asia/Singapore"` pinned (date assertions were runner-dependent and masked the FE-M7 off-by-one); `package.json` — `test:all` gains `--coverage` (the local all-gates shortcut skipped the ratchet). **Errata recorded honestly:** the plan's `strictPort: true` is not a Playwright webServer option (1.58 rejects `port`+`url` together) — the residual reuse caveat is documented in the config comment instead.

### Phase 3 — cross-cutting: the first-run truth + the docs/env pass

- **X-P20-H1(a)** `banking.spec.ts`'s `ensureOutstandingInvoice` creates its own contact (idempotent, run-unique) — the helper's own comment showed that was the design intent. The cross-spec dependency (banking runs 2nd, the only contact creator runs 7th) is gone at the point of consumption: a fresh DB's first full run is green.
- **X-P20-H1(b)** `scripts/bootstrap_demo_substrate_session40.sh` genuinely completes §9 steps 1-5 (register/login, org, contact + profile PATCH, the invoice + linked credit note + approvals, the F5 compute — idempotent, double-run executed green), referenced from DEPLOYMENT §9 as the single pre-suite command; DEPLOYMENT §9's false "a fresh DB self-bootstraps on the first run" parenthetical corrected with the mechanism documented (it was red run 1 / green run 2 by construction).
- **X-P20-M1/L4** DEPLOYMENT §3: the lifecycle block derives from `$PG_BASE`; the `PG_MAJOR` fallback documented honestly (the shell cannot see the script's internal variable).
- **X-P20-M2/M9/M10** the stale P18-era counts refreshed everywhere the P19 truth pass missed: DEPLOYMENT (header/§7/§9), AGENTS.md (12-14 + 262-263, v0.3.4/v0.6.4 → v0.3.5/v0.6.5), Project_Architecture_Document.md (the P20 frame, 1,617 tests), the ci.yml header comment (X-L1).
- **X-P20-M4..M7 + L6** the four wrong API-guide rows corrected with in-place errata: the import path (`bank-transactions/import/` with the account in form data — not the nonexistent `bank-accounts/{id}/import-csv/`), the recompute route (`POST ?force=true` — not the nonexistent `generate/`), the unallocate row (service-level, no HTTP surface), the quote-convert route (body-parameterised); the metrics row refreshed to post-P20; the guide version bumped to 3.1.0.
- **.env.example (the owner's named task):** all three files verified truthful variable-by-variable by the cross-cutting audit (nothing stale, nothing missing, no root/per-app contradiction) — the deliverable already existed; this sprint added the decouple search-path caveat note to the backend example (X-P20-L3: python-decouple walks up parent directories — `apps/backend/.env` must exist or a repo-root `.env` silently wins).

### Phase 4 — gates, captures, deliverables

The full gate matrix re-run green (§1); 8 DOM-verified screenshots
(`scripts/capture-screenshots-session40.js`); this report;
`docs/session_40.md`; the worklog entry; the docs truth pass; the
conventional commits and the SSH-wrapper push.

## 3. Incidents & lessons (recorded for future sessions)

1. **The vacuous-RED traps again (P19 lesson holding):** two first-cut
   RED probes were rebuilt before any fix — the void lock-order test
   passed pre-fix for the wrong reason (it only asserted the post-void
   totals, which the unlocked path also produced; rebuilt to record the
   actual lock order), and the racing-seam interleaving fired once per
   document lock (the T2 insert duplicated; rebuilt with a fired-once
   guard).
2. **The environment is part of the test contract:** running the
   :8001 rls smoke instance required `ALTER ROLE ledgersg_app
   PASSWORD …`, which broke two suite tests that hardcode the schema's
   documented dev placeholder password (`CHANGE_ME_IN_PRODUCTION`) —
   the full suite went 2-red until the role password was restored. The
   tests rely on the documented dev default; keep it.
3. **Config-knowledge honesty:** two planned config changes were
   fact-checked against the installed tooling during GREEN —
   Playwright 1.58 has no `strictPort` webServer option (and rejects
   `port`+`url` together), and Vitest's measured set shifted when the
   app tier was included (it RAISES the floor — the blind spot was
   hiding good coverage). Both shipped as what the tool actually
   supports, with the residual caveats documented in place.
4. **The organisations list uses the `{data}` envelope** while the
   org-scoped lists use `{results}` — the bootstrap script now handles
   both (the documented envelope-inconsistency deferred register item,
   re-confirmed live).

## 4. Deferred register (updated, carried forward)

**Fixed this sprint (removed from the register):** the
void/transition/allocate lock completion (BE-H1/M1/M2/H3); the CSV
savepoint + magnitude bound (BE-H2); the posting-side balance-cache
invalidation (BE-M5); the three service-seam L-batch items
(BE-L1/L2/L3); the two a11y Highs + the combobox blur + the chart ARIA
+ the date off-by-one + the h1/loading a11y batch (FE); the
vitest/playwright/package config ratchet completion (the owner's named
task); the first-run e2e truth (X-H1) with the one-command §9
bootstrap; the DEPLOYMENT/API-guide/docs truth batch.

**Still deferred (with rationale):** list pagination (the per-view
design + frontend UX); the `{data}`/`{results}` envelope unification
(re-measured: ~20 + 6 + 1 raw array); the ruff mechanical batch
(re-measured 1299 whole-tree / 788 production; this sprint cleared the
one real latent bug it had surfaced); the audit-log INSERT WITH CHECK
policy (needs the schema design); the dead-letter design; the UEN
checksum (needs the official algorithm); the NULL-context SELECT
tradeoff; H-05b models; the PaymentsTab same-route prefill (no
producer); the TanStack React-Compiler incompatibility (documented
disable); the middleware register entry CORRECTED this sprint
(simplejwt 5.5.1 verifies by default — the real residual is the
membership-cache revocation window); the journal detail serializer
N+1; BE-M3 (fiscal close vs posting race — needs the period-lock
design); BE-M4 (reconcile FX comparator — needs the base_amount
decision); BE-M6 (CSV dedupe backstop — needs DDL); FE-M2 (route guard
vs history navigation — the sentinel-entry design); FE-M3 (drawer ×
Radix Dialog focus-trap stacking); FE-L1/L4/L5/L6/L8 (the small
frontend batch); X-L2/I1/I2 (CI hardening); X-M8 (the version-story
reconciliation).
