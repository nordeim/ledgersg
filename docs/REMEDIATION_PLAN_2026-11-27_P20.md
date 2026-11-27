# LedgerSG — Remediation Plan (P20 Sprint: The void/transition Lock Completion, the CSV Transaction Poisoning, the E2E First-Run Truth & the Test-Config Ratchet)

**Date:** 2026-11-27 (session 40)
**Base commit:** `6ca32a96` (main — post-P19, all gates green at 937P/0F/5S backend · 619/619 vitest · tsc 0 · eslint 0E/0W · live e2e 40P/0F/0S · rls_smoke 13/13 · mobile-nav 17/17 · prod-CSP smoke 5/5 · schema v1.2.2)
**Method for execution:** TDD (RED → GREEN → full gate) for every behavioural fix; lint parity on touched files; conventional commits on `main`; `skills/` excluded from all checks/tests/compilation; **no schema changes** (v1.2.2 carries forward).

---

## 1. Audit inputs (this session's evidence)

Three parallel deep audits (Mode C) + lead hand-verification of every High
finding in source, plus the documented P19 baselines reproduced on a
freshly-cloned, freshly-bootstrapped workspace (rootless PG 17 via
`docs/setup_pg_z.sh`, Redis 8 on :6379, schema v1.2.2 loaded into both
databases, backend venv installed, the dev stack live on :8000 + :3000, the
demo substrate bootstrapped through the public API):

- **Baselines reproduced** (all executed, green): backend **937P/0F/5S**
  (`pytest --reuse-db --no-migrations -q`, 24.5s) · vitest **619/619**
  (72 files, 86.7s) · `npx tsc --noEmit` 0 · whole-tree `npx eslint .`
  **0 errors / 0 warnings** · **mobile-nav live probe 17/17 at
  375/800/1280** — **the navigation works; no TailwindCSS v4 bug exists**
  (tenth consecutive live settlement; the v4 setup re-verified clean:
  `@import "tailwindcss"` + `tw-animate-css`, no legacy config, no
  dead-token `-[var(--…)]` classes remain) · live e2e:full **40/40** (the
  second run — the first run on the fresh DB failed exactly one spec,
  the root cause of which is finding X-P20-H1 below) · rls_smoke **13/13**
  as `ledgersg_app` on the :8001 instance · prod-CSP smoke **5/5**.
- **Backend audit** (P19-diff soundness + lock-order matrix + fresh
  money-path sweep + deferred-register re-verification): **0 Critical,
  3 High, 6 Medium, 3 Low, 2 Informational.** The P19 work itself verified
  sound — every Phase 1 claim in the P19 report matches the code, and the
  P19 test files pass (23/23 re-run this session). The Highs are residual
  pre-P19-shape gaps in the exact classes P19 was closing: `void()` mutates
  documents without the document row lock (H1), the CSV import loop has no
  savepoint so one DB-level row error poisons the whole transaction and
  500s (H2), and `transition_status()` still carries the unlocked gate +
  stale full-row save that P19/BE-H1 fixed for `remove_line` (H3).
- **Frontend audit** (P19-diff verification + WCAG 2.2 AA sweep on the
  non-P19 money surfaces + the vitest/playwright config audit + Tailwind
  v4 hygiene): **0 Critical, 2 High, 7 Medium, 8 Low, 6 Informational.**
  All four P19 frontend claims verified true (the Radix banking modals, the
  keyboard transaction row, the WAI-ARIA ContactPicker, the
  UnsavedRouteGuard — each with correctness notes). The Highs are the same
  a11y failure class as P19 on surfaces P19 did not touch: the invoice
  form's Notes/Terms textareas have no accessible names (H1) and the two
  icon-only back links on /invoices/new + /quotes/new have empty accessible
  names (H2). The Tailwind v4 hygiene sweep is CLEAN (the P18 fix held; the
  P19 FE-L5 dead-token class has no remaining instances).
- **Cross-cutting truth audit** (CI truth + env-example truth + DEPLOYMENT
  walk + API-guide route verification + docs drift + the first-run e2e
  flake diagnosis): **0 Critical, 1 High, 10 Medium, 6 Low, 5
  Informational.** The env examples verified truthful variable-by-variable
  (nothing stale, nothing missing). The High is the first-run e2e flake —
  diagnosed to a spec-order dependency by construction, not timing:
  `banking.spec.ts` runs second (alphabetical), its
  `ensureOutstandingInvoice` helper requires `contacts.results[0]` to
  exist, and no earlier spec creates a contact (p10's picker helper — the
  only contact creator — runs 7th; p11's `ensureDemoActivity` also
  *requires* a contact). Fresh DB → deterministic red on run 1, green on
  run 2 — and DEPLOYMENT §9's "a fresh DB self-bootstraps on the first
  run" parenthetical is false.

**Combined: 0 Critical / 6 High / 23 Medium / 17 Low / 13 Informational.**
Every High hand-verified in source by the lead before this plan was
written.

## 2. The findings (verified, with evidence anchors)

### High

**BE-P20-H1 — `void()` recomputes and saves affected documents without the
document row lock, in nondeterministic order.**
`apps/backend/apps/banking/services/payment_service.py:381-410` —
`affected_documents` is a plain `filter(...).distinct()` read (no
`select_for_update`, no ordering), the payment's allocations are deleted,
then each document's `amount_paid` is recomputed via an unlocked
`PaymentAllocation` SUM and written with a full-row `document.save()`.
Interleaving: T2 `allocate()` holds the document lock, inserts its
allocation, recomputes, commits; T1 `void()` (whose SUM was computed
pre-T2-commit) then lands its unlocked UPDATE and **overwrites
`amount_paid` missing T2's allocation** (status can regress PAID →
PARTIALLY_PAID). This is exactly the invariant P14/H-1 established ("the
allocations table is the truth") — silently violated until the next
allocation event. `allocate()` (:470-479) and `unallocate()`
(:656-675, the P19/BE-M3 fix) both hold the document lock; `void()` is the
odd one out. Also the AB-BA class: two concurrent voids over shared
documents lock rows at UPDATE time in DB-dependent opposite orders
(BE-P20-M2 — fixed by the same change).

**BE-P20-H2 — CSV import: one DB-level row error poisons the transaction —
untyped 500, the per-row `errors[]` contract never delivered.**
`apps/backend/apps/banking/services/reconciliation_service.py:245-263` —
the per-row `BankTransaction.objects.create(...)` sits inside a
`try/except Exception` with **no savepoint**; the final
`AuditEventLog.objects.create` (line 265) is outside the try; the method
is `@transaction.atomic()`. Realistic trigger: `money()` has no magnitude
bound (`money("1E+20")` returns a 21-digit Decimal — verified live) while
`banking.bank_transaction.amount` is `NUMERIC(19,4)` (15 integer digits) —
an oversized CSV amount raises `DataError` on INSERT, the per-row except
swallows it, every subsequent row fails with "current transaction is
aborted" (also swallowed), and the audit-log INSERT raises outside the try
→ untyped 500 with full rollback. This is byte-for-byte the class
P19/BE-M4 fixed in `gst/return_service.create_return_periods` (the
savepoint around the guarded create); the import loop did not get the same
treatment.

**BE-P20-H3 — `transition_status()` still has the unlocked gate + stale
full-row save that P19/BE-H1 fixed for `remove_line`.**
`apps/backend/apps/invoicing/services/document_service.py:475-543` —
plain `get_document()` (:475) → transition-map check against the STALE
status (:478-483) → `with transaction.atomic():` mutates and full-row
`document.save()` (:543). No `select_for_update`, no post-lock re-read, no
`update_fields`. Reachable from `POST
/api/v1/{org}/invoicing/documents/{id}/status/` for every non-VOID/APPROVED
target (`SENT`/`OVERDUE` route here; views.py:357-360). A concurrent
`approve_document()` (which locks) can commit DRAFT→APPROVED + the journal
posting between this method's read and its save; the stale save then
writes `status="SENT"` over the APPROVED, journal-posted document — and
clobbers `total_excl/gst_total/total_incl` with pre-`add_line` values.

**FE-P20-H1 — the invoice form's Notes and Terms textareas have no
accessible name (the P19 FE-L4 class, on the form P19 itself touched).**
`apps/web/src/components/invoice/invoice-form.tsx:493-527` — `<label>`
without `htmlFor` + raw `<textarea {...methods.register(...)}>` with no
`id`/`aria-label` (register does not generate ids). The shared `Input`
component wires the pairing correctly; these two bypass it. WCAG
1.3.1/4.1.2 Level A on the primary money-entry form.

**FE-P20-H2 — the icon-only back links on /invoices/new and /quotes/new
have empty accessible names.**
`apps/web/src/app/(dashboard)/invoices/new/page.tsx:23-28` and
`apps/web/src/app/(dashboard)/quotes/new/page.tsx:25-30` —
`<Link href=…><ArrowLeft /></Link>` with no `aria-label`/sr-only text. The
identical pattern in `invoice-detail-client.tsx:147-153` carries
`aria-label="Back to invoices"` — the fix exists in the codebase and was
not applied to these two routes.

**X-P20-H1 — the live e2e suite is red-by-construction on the first run
against a fresh DB (spec-order dependency), and DEPLOYMENT §9 documents it
as self-bootstrapping.**
`apps/web/e2e/banking.spec.ts:64-70` — `ensureOutstandingInvoice` asserts
`contacts.results[0]?.id` is truthy but creates no contact; Playwright
runs files alphabetically (auth → banking → … → p10 → p11 …); the only
contact-creating helper (`p10.spec.ts`'s `ensurePickedCustomer`) runs 7th;
`p11.spec.ts`'s `ensureDemoActivity` also *requires* a contact
(:105-106) rather than creating one. Reproduced this session: run 1 failed
exactly `banking.spec.ts:151`, run 2 passed 40/40.
`docs/DEPLOYMENT.md:374-375` claims the p11 spec self-bootstraps a fresh
DB — false for the contact (step 3 is a manual precondition the guide
leaves as prose, and the parenthetical mis-attributes it).

### Medium (this sprint's execution scope)

**BE-P20-M1 — `allocate()` locks documents in user-supplied order (the
AB-BA class P19/BE-M2 closed for `create_entry`).**
`payment_service.py:470-479` — per-allocation
`select_for_update().get(id=document_id)` in request order. Two concurrent
allocations against overlapping document sets in opposite orders → PG
40P01 → untyped 500. Fix: the sorted deduplicated pre-lock (the
`create_entry` pattern).

**BE-P20-M5 — the `account_balance` 5-minute cache is still never
invalidated by journal postings.**
`apps/backend/apps/coa/services.py:422-441` — the P19/BE-M1 fix patched
the archive gate only; `create_entry` performs no invalidation, so
`GET /accounts/{id}/balance/` serves a pre-posting balance for up to 5
minutes (a stale money read on a user-facing surface). Fix: delete
`account_balance:{id}` for each distinct account touched in
`create_entry`.

**FE-P20-M1 — the ContactPicker never dismisses the listbox on blur.**
`apps/web/src/components/contact-picker.tsx:199-203` — the input's onBlur
is an intentional no-op (documented for the pointer case); dismissal paths
are Escape, selection, and a mousedown-only click-away. Tab-away leaves
the listbox open with `aria-expanded="true"` and focus elsewhere — a
WAI-ARIA pattern violation with real overlay consequences on the
payment/invoice forms. Fix: deferred-close on blur
(`requestAnimationFrame` + `contains(activeElement)` guard so mousedown
selection still wins), reset `activeIndex`.

**FE-P20-M4 — gst-f5-chart's "accessible data table" has an invalid ARIA
owned structure (the P19 FE-L1 class left behind).**
`apps/web/src/components/dashboard/gst-f5-chart.tsx:99-103` —
`role="table"` > `div role="rowheader"` containing three
`role="columnheader"` children; ARIA requires `table > row >
columnheader`. Browsers prune the invalid structure, defeating the
toggle's purpose.

**FE-P20-M5 — the vitest coverage ratchet has blind spots: `src/app/**`
and `src/providers/**` are excluded from measurement entirely, the
components tier has no per-glob floor, and the test helper is counted.**
`apps/web/vitest.config.ts:72-82`. Measured this session (temporary
config probe): src/app 74/65/72/74, src/components 83/75/69/84,
src/providers 62/62/59/61 — all healthy. Including them RAISES the
whole-suite measured floor (71.92/61.39/68.96/72.5 vs the current
measured set). Fix: drop `src/app/**` + `src/providers/**` from the
coverage exclude, add `**/__tests__/**` to the coverage exclude, add
per-glob floors for app/components/providers at the measured value, and
raise the whole-suite floor accordingly (raise, never lower).

**FE-P20-M6 — the Playwright e2e webServer has no `strictPort`, traces are
`on-first-retry` with local `retries: 0` (local failures leave no trace),
and the locale/timezone are unpinned.**
`apps/web/playwright.config.ts:61-86,118-123`. With
`reuseExistingServer: !CI`, anything on :3000 is silently adopted as the
server. Date rendering (`new Date("YYYY-MM-DD")` +
`toLocaleDateString("en-SG")`) is UTC-parse + local-display — runner
timezone dependent. Fix: `strictPort: true`, `trace: "retain-on-failure"`,
`locale: "en-SG"` + `timezoneId: "Asia/Singapore"` pinned.

**FE-P20-M7 — date off-by-one risk: UTC date-only parse + local-timezone
display.**
`apps/web/src/app/(dashboard)/invoices/[id]/invoice-detail-client.tsx:84-92`
(and the same pattern wherever date-only strings render). For timezones
behind UTC the dates display one day early. Fix: format date-only strings
with `timeZone: "UTC"`; pin the Playwright timezone (FE-P20-M6) so a
regression is catchable.

**X-P20-M1 — DEPLOYMENT §3's lifecycle block hardcodes the sandbox PG
path.**
`docs/DEPLOYMENT.md:132-137` — stop/status/log paths hardcode
`/home/z/my-project/pg/...` while the same section was parametrized to
`$PG_BASE` (X-M4). Fix: derive from `$PG_BASE`.

**X-P20-M2/M9/M10 — the P19 gate counts never landed in DEPLOYMENT.md,
AGENTS.md, or Project_Architecture_Document.md.**
`docs/DEPLOYMENT.md:9-12,244,330` (914P/601), `AGENTS.md:12-14,262-263`
(914P/601, v0.3.4/v0.6.4), `Project_Architecture_Document.md:6,50` (P18
frame, 1,555). The P19 truth-pass commit message says "refreshed
everywhere" but skipped these three files. Fix: one-pass refresh (937/619,
P19 frame, v0.3.5/v0.6.5).

**X-P20-M4/M5/M6/M7 — the API guide documents four nonexistent/wrong
routes.**
`API_CLI_Usage_Guide.md:316-320` (`import-csv/` path — the real route is
`bank-transactions/import/` with the account in form data, which the
guide's own P16 row documents), `:142` (`returns/{id}/generate/` — the
recompute is `POST ?force=true`, documented correctly in the P14 row),
`:143` (a `payments/allocations/{id}/` unallocate route that does not
exist — the service has no HTTP surface), `:144`
(`quotes/{id}/convert/` — the real route is `quotes/convert/` with the
id in the body). Fix: correct all four + add the post-P19 metrics row
(X-P20-L6).

### Low (this sprint's execution scope)

- **BE-P20-L1** — `apps/backend/apps/invoicing/views.py:409` uses `Decimal`
  at module scope where it is only imported function-locally in a later
  view (ruff F821; latent NameError — the serializer default masks it
  today). Fix: module-level import.
- **BE-P20-L2** — `allocate()` service seam does not validate positive
  amounts (DB CHECK → untyped IntegrityError for non-DRF callers;
  serializers gate it today). Fix: one-line typed guard.
- **BE-P20-L3** — `unreconcile()`'s payment lock lacks the `org_id=`
  filter every sibling lock carries. Fix: add the filter.
- **FE-P20-L2** — every dashboard page renders two h1s (the sidebar brand
  `shell.tsx:292-294` + the page h1). Fix: demote the brand to a `<p>`.
- **FE-P20-L3** — async loading/error states are silent to screen readers
  (no `role="status"`/`aria-live` on the loading blocks). Fix: wrap the
  loading blocks in `<div role="status" aria-live="polite">` on the
  primary money surfaces.
- **FE-P20-L7** — `test:all` omits the coverage ratchet. Fix: add
  `--coverage`.
- **X-P20-L1** — `.github/workflows/ci.yml:8` header comment still says
  914 (P18). Fix: refresh.
- **X-P20-L4** — DEPLOYMENT §3's `PG_MAJOR` fallback is shell-fiction (the
  script never exports it). Fix: document the actual path probe.

### Explicitly deferred this sprint (registered, not dropped — see §4)

FE-P20-M2 (route guard vs history navigation — the honest sentinel-entry
design decision), FE-P20-M3 (drawer × Radix Dialog focus-trap stacking —
needs the custom-event coordination design), BE-P20-M3 (fiscal close vs
posting race — needs the period-lock design), BE-P20-M4 (reconcile FX
comparator — needs the base_amount decision), BE-P20-M6 (CSV dedupe —
needs DDL, out of the no-DDL scope), FE-P20-L1/L4/L5/L6/L8 (MoneyInput id
derivation, dead inputRef, next-themes dep, contrast-gate rows, toast
assertiveness), X-P20-L2/L3 (SHA pinning, decouple search-path note —
the note lands with the env-example touch), X-P20-I1/I2 (Playwright CI
cache, audit-advisory reconciliation), and the P19-era register
(pagination, envelope unification, ruff batch, audit-log INSERT policy,
dead-letter, UEN checksum, NULL-context SELECT, H-05b, PaymentsTab
prefill, TanStack incompatibility, journal detail N+1).

## 3. The execution plan (phases, TDD)

### Phase 1 — backend: the locking/transaction completion (RED first)

| Task | Fix | Tests (RED first) |
|---|---|---|
| BE-H1 (+M2) | `void()`: `select_for_update()` the affected documents (sorted by id) BEFORE the allocation deletes; recompute under the locks | lock spy + the interleaving probe (T2 allocate commits between T1's read and write → T1's recompute sees T2's allocation; the unlocked SUM probe fails pre-fix) + the sorted-order probe |
| BE-H2 | CSV import: per-row `with transaction.atomic():` savepoint around the guarded create + a magnitude bound on the amount parse (typed row error, `abs < 10**15`) | poison-row test (an oversized amount row → 200-shaped response with that row in `errors[]`, the other rows imported) — currently raises outside the try |
| BE-H3 | `transition_status()`: `select_for_update()` the document, post-lock re-validation of the transition + the GST lock, `save(update_fields=…)` (status + the APPROVED timestamp fields) | the Case-B race probe (the approver wins the lock → the stale SENT transition refuses) + the no-clobber probe (totals untouched) |
| BE-M1 | `allocate()`: sorted deduplicated document pre-lock inside the atomic | order probe + the double-allocation cap re-check under the lock (existing tests stay green) |
| BE-M5 | `create_entry()`: `cache.delete(f"account_balance:{id}")` for each distinct account touched | cache-seed probe (seed cache → create_entry → balance read is fresh) |
| BE-L1/L2/L3 | the module-level `Decimal` import; the positive-amount guard in `allocate()`; the `org_id` filter on `unreconcile()`'s payment lock | ruff F821 gone; the guard raises the typed 400; the lock query count/filter asserted |

### Phase 2 — frontend: the a11y Highs + the guard/combobox hardening (vitest RED first)

| Task | Fix | Tests (RED first) |
|---|---|---|
| FE-H1 | the Notes/Terms textareas: `id` + `htmlFor` pairing | `getByRole("textbox", { name: "Notes" })` / "Terms & Conditions" |
| FE-H2 | `aria-label="Back to invoices"` / `"Back to quotes"` on the two icon-only Links | axe-style accessible-name assertions in the two page tests |
| FE-M1 | ContactPicker blur dismissal (rAF-deferred close, mousedown wins, activeIndex reset) | Tab-away closes the listbox + `aria-expanded=false`; mousedown selection still selects |
| FE-M4 | gst-f5-chart: real `role="row"` wrapper + `columnheader` cells | the ARIA owned-structure assertion |
| FE-M7 | date-only strings render with `timeZone: "UTC"` (invoice detail + the other date-only renders) | a date-rendering test pinned to a non-UTC timezone (`vi.setSystemTime` + a timezone-shifted TZ env… practical form: assert the formatter emits the string date lexically) |
| FE-L2/L3 | the brand `<h1>` → `<p>`; `role="status"` on the primary loading blocks | heading-count assertions; the status-role assertions |
| CFG batch (FE-M5/M6/L7 — the owner's named task) | vitest.config.ts: coverage exclude `**/__tests__/**`, un-exclude `src/app/**`+`src/providers/**`, per-glob floors (app 73/64/71/73, components 82/74/68/83, providers 61/61/58/60), whole-suite floor raised 62/51/52/63 → 71/60/68/71; playwright.config.ts: `strictPort: true`, `trace: "retain-on-failure"`, `locale: "en-SG"`, `timezoneId: "Asia/Singapore"`; package.json `test:all` gains `--coverage` | the ratchet itself is the gate (the coverage run must pass at the new floors); the playwright config schema-validates and the suite runs green under the pinned locale/timezone |

### Phase 3 — cross-cutting: the first-run truth + the docs/env pass

| Task | Fix | Tests |
|---|---|---|
| X-H1(a) | `banking.spec.ts`'s `ensureOutstandingInvoice` creates its own contact (idempotent, run-unique name) — the helper's own comment shows that was the design intent | the fresh-DB first run of the full suite is green (the live gate) |
| X-H1(b) | `scripts/bootstrap_demo_substrate_session40.sh` completed to genuinely mirror §9 steps 1-5 (contact + invoice/CN + F5, idempotent), referenced from DEPLOYMENT §9 as the single pre-suite command; §9's false self-bootstrap parenthetical corrected | executed against the live stack (idempotent double-run) |
| X-M1/L4 | DEPLOYMENT §3 lifecycle block derives from `$PG_BASE`; the `PG_MAJOR` fallback documented honestly | doc review (paths derived) |
| X-M2/M9/M10 | DEPLOYMENT/AGENTS/PAD count refresh (937/619, the P19 frame) | doc review |
| X-M4..M7 + L6 | the four API-guide route rows corrected (import path, force-recompute, the unallocate non-route, quotes/convert body) + the post-P19 metrics row | each row re-verified against the live urls |
| X-L1 | the ci.yml header comment (937, P19) | YAML lint |
| .env.example | the three examples verified truthful this session (audit); the backend one gains the decouple search-path caveat note (X-P20-L3) so operators know WHY `apps/backend/.env` must exist | the audit's variable-by-variable verification table |

### Phase 4 — gates, captures, deliverables

The full gate matrix (backend · vitest · tsc · eslint 0E/0W · live e2e:full
· rls_smoke · mobile-nav · prod-CSP); 8 DOM-verified screenshots
(`docs/screenshots/120-127_*_session40.png`); the P20 report
(`docs/REMEDIATION_2026-11-27_P20_REPORT.md`); the session log
(`docs/session_40.md`); the worklog entry; the docs truth pass; the
conventional commits and the SSH-wrapper push to main.

## 4. Deferred register (updated, carried forward)

**Fixed this sprint (removed):** the void/transition/allocate lock
completion (BE-H1/M1/M2 + H3); the CSV savepoint + magnitude bound
(BE-H2); the balance-cache posting invalidation (BE-M5); the two a11y
Highs + the combobox blur + the chart ARIA + the date off-by-one + the
h1/loading a11y batch (FE); the vitest/playwright config ratchet
completion; the first-run e2e truth (X-H1) + the DEPLOYMENT/API-guide
truth batch.

**Still deferred (with rationale):**
- **List pagination** (BE) — the per-view design + frontend UX; the
  envelope work below is its prerequisite.
- **List-envelope `{data}`/`{results}` unification** (BE) — re-measured:
  ~20 `{results, count}` sites + ~6 `{data}` sites + 1 raw array (the
  `my_organisations` view). Coordinated contract change across both
  tiers; the frontend parses both shapes, so it is debt, not breakage.
- **ruff register** (BE) — re-measured: 1299 whole-tree / 788 production
  (top: W293 ×341, I001 ×82, F401 ×81, B904 ×64, UP045 ×45). The
  mechanical batch is a dedicated pass; this sprint only clears the one
  real latent bug it surfaced (L1/F821).
- **Audit-log `INSERT WITH CHECK (TRUE)`** (schema) — needs the scoped
  INSERT policy design (or a SECURITY DEFINER write path); schema change,
  out of the no-DDL scope.
- **Org-mid-flight dead-letter design** (BE) — needs the persistent
  failure-record model decision.
- **UEN checksum** (BE) — needs the official IRAS algorithm.
- **NULL-context SELECT policies** (schema §17) — the documented
  pre-context membership tradeoff; unchanged.
- **H-05b attachment/threshold models** (BE) — needs the feature decision.
- **The PaymentsTab same-route prefill re-trigger** (FE) — verified again
  this audit: no producer exists (the only deep link is cross-route);
  keyed-remount fix registered for when one appears.
- **The TanStack `useReactTable` React-Compiler incompatibility** (FE) —
  upstream limitation; the documented disable is live and correct.
- **The middleware token parse register entry — CORRECTED this audit:**
  the P19 register said "parse without signature verification"; in
  simplejwt 5.5.1 `AccessToken(token)` DOES verify signature + expiry by
  default (`verify=True` default, `verify_signature` passed through), and
  org_id comes from the URL path, not the token. The real residual items
  are the membership-cache 5-minute revocation window and the broad
  `except Exception: pass` on parse (fail-safe but noisy) — both
  registered for the next hardening pass.
- **The journal detail serializer's per-entry source-document lookup**
  (BE) — confirmed still present; bounded (detail is per-entry today).
- **BE-M3 fiscal close vs posting race** — needs the period-lock design.
- **BE-M4 reconcile FX comparator** — needs the base_amount decision.
- **BE-M6 CSV dedupe backstop** — needs a UNIQUE constraint (DDL).
- **FE-M2 route guard vs history navigation** — the sentinel-entry design
  decision; documented as a known hole until designed.
- **FE-M3 drawer × Radix Dialog focus-trap stacking** — the custom-event
  coordination design.
- **FE-L1 MoneyInput id derivation / L4 dead inputRef / L5 next-themes
  dep / L6 contrast-gate rows / L8 toast assertiveness** — small batch,
  next frontend pass.
- **X-L2 SHA-pinned CI actions / X-I1 Playwright CI cache / X-I2
  npm-audit advisory stance** — CI hardening batch.
- **X-M8 the version-story reconciliation** (docs claim v0.3.5/v0.6.5;
  manifests say 0.1.0/1.0.0) — needs the bump-policy decision.
