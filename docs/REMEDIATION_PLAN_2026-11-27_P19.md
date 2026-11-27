# LedgerSG — Remediation Plan (P19 Sprint: The remove_line Truth Gap, the Modal Semantics Debt, the ContactPicker & the Route Guard)

**Date:** 2026-11-27 (session 38)
**Base commit:** `99786f6a` (main — post-P18, all gates green at 914P/0F/5S backend · 601/601 vitest · tsc 0 · eslint 0 errors/5 parity warnings · live e2e 40P/0F/0S · rls_smoke 13/13 · mobile-nav 17/17 · prod-CSP smoke 5/5 · schema v1.2.2)
**Method for execution:** TDD (RED → GREEN → full gate) for every behavioural fix; lint parity on touched files; conventional commits on `main`; `skills/` excluded from all checks/tests/compilation; **no schema changes** (v1.2.2 carries forward).

---

## 1. Audit inputs (this session's evidence)

Three parallel deep audits (Mode C) + lead hand-verification of every
High finding in source, plus the documented P18 baselines reproduced on
the carried-forward workspace (PG 17 + Redis 8 rootless survived as
double-forked daemons; both DBs at v1.2.2; the dev stack live on :8000
plus the rls_smoke instance on :8001; the demo substrate intact — user,
org, 2 contacts, CoA seeded):

- **Baselines reproduced** (all executed, green): backend **914P/0F/5S**
  (`pytest --reuse-db --no-migrations -q`, 19.7s) · vitest **601/601**
  (70 files, 84.7s) · `npx tsc --noEmit` 0 · whole-tree `npx eslint .`
  **0 errors / 5 parity warnings** · **mobile-nav live probe 17/17 at
  375/800/1280** — **the navigation works; no TailwindCSS v4 bug exists**
  (eighth consecutive live settlement).
- **Backend audit** (P18-diff soundness + lock-order/deadlock analysis +
  deferred-register re-verification): **1 High, 7 Medium, 8 Low, 3
  Informational** + 10 deferred verdicts (9 still valid, 1 resolved).
  The P18 locking pass is substantively sound — every claimed lock
  verified — **but `remove_line` was never locked despite the P18 commit
  claiming it** (H1, the truth gap), and two P18 fixes carry latent
  defects (the archive-gate cache read M1; the return-periods
  transaction poisoning M4).
- **Frontend audit** (P18-diff verification + WCAG 2.2 AA sweep +
  deferred-register): **2 High, 5 Medium, 9 Low, 7 Informational.**
  P18's five changes all verified sound. The Highs are a11y failures on
  the primary money flows: the four hand-rolled banking "modals" (no
  focus trap, no Escape, no dialog semantics — violating the repo's own
  library discipline) and the mouse-only transaction-row expander that
  blocks keyboard users from Reconcile entirely (WCAG 2.1.1 Level A).
- **Cross-cutting truth audit** (CI/e2e/coverage/schema/env/docs/compose):
  **0 High, 4 Medium, 5 Low, 6 Informational.** The P18 deliverables
  verified sound (env examples complete — no stale/missing vars; the CI
  e2e job and the honest coverage ratchet check out; schema §15c
  idempotent). Material findings: the enforced frontend CSP carries no
  report-uri (violations invisible in production), the CSV import has no
  size cap (worker OOM), the compose celery-beat service references
  tables §15c intentionally omits (deterministic crash-loop on the
  documented Docker route), and the P18 `PG_BASE` parametrization is
  incomplete (the fresh-host story breaks at exactly the step it fixed).

## 2. The findings (verified, with evidence anchors)

### High

**BE-P19-H1 — `remove_line` was never locked: the P18 commit `51bd46c6`
claims "add_line/remove_line lock the document" but only `add_line`
got the lock — a TOCTOU that can overwrite an APPROVED, journal-posted
document's totals.**
`apps/backend/apps/invoicing/services/document_service.py:418-440`:
plain `get_document()` → DRAFT gate → `line.delete()` →
`_recalculate_totals(document)`, with **no atomic block and no row
lock** (contrast the locked `add_line` at :319-416). Interleaving:
`remove_line` reads status DRAFT and passes the gate; `approve_document`
(which holds the document lock) approves and posts the journal entry;
`remove_line.delete()` + totals-save then land unconflicted — the
document's totals now disagree with the posted ledger on a money path.
The route is live (`documents/<uuid>/lines/<uuid:line_id>/` DELETE) and
the P18 concurrency test file has no remove-line probe. Also a truth
gap: the sprint register (P18 report §2) says it is fixed.

**FE-P19-H1 — the four banking "modals" are not dialogs: no focus trap,
no Escape, no dialog semantics on the payment-entry and reconciliation
primary flows.**
`src/app/(dashboard)/banking/banking-client.tsx:436` (Receive), `:456`
(Make), `:561` (Import), `:572` (Reconcile) — each a
`<div className="fixed inset-0 bg-black/50 z-50 …">` wrapping a plain
Card: no `role="dialog"`, no `aria-modal`, no `aria-labelledby`, no
focus trap (Tab escapes into the background page), no Escape handling,
no focus return, no scroll lock. This violates the project's own stated
discipline in `src/components/ui/dialog.tsx:10-12` ("never custom-build
modals") — the Radix Dialog primitive exists and IS used by the
contacts/bank-account/void dialogs. WCAG 2.4.3 / 4.1.2 / 2.1.2-adjacent.

**FE-P19-H2 — the transaction-row header is a mouse-only clickable div:
keyboard users cannot expand a bank transaction, therefore cannot reach
the Reconcile flow at all.**
`src/app/(dashboard)/banking/components/transaction-row.tsx:55-58` —
`<div className="p-4 cursor-pointer …" onClick={handleToggle}>` with no
`role`, no `tabIndex`, no key handler; the Reconcile/Unreconcile buttons
(:176-200) render only inside the expanded panel. WCAG 2.1.1 Level A
block on a primary banking flow.

### Medium (backend)

**BE-P19-M1 — `archive_account`'s zero-balance gate reads a 5-minute
stale cache; journal postings never invalidate it.**
`apps/backend/apps/coa/services.py:384-390` (the gate calls the cached
`get_account_balance`), `:415-434` (`account_balance:{id}`, TTL 300s),
`:346` (the only invalidation site — `update_account`). Sequence: GET
balance (seeds cache 0) → post a journal line → DELETE the account →
gate reads cached 0 → archived with live journal lines, and the lines
vanish from the trial balance (`is_active` filter, journal_service.py:586).
Defeats the P18/BE-M3 archive gate with no race required.

**BE-P19-M2 — `create_entry` vs `archive_account` is not actually
serialized: the account read in `create_entry` is a plain SELECT.**
`apps/journal/services/journal_service.py:247-249` vs the archive lock
at `coa/services.py:371-372`. The P18 comment claims "the pair is
closed", but a plain SELECT doesn't conflict with the archive row lock:
lines can land on an account archived a moment earlier.

**BE-P19-M3 — AB-BA deadlock: `unallocate` (allocation → payment) vs
`void`/`allocate` (payment → allocation rows).**
`apps/banking/services/payment_service.py:656-665` — unallocate locks
the allocation row FIRST, then payment, then document; `void` (:332)
holds the payment lock then DELETEs allocation rows; `allocate` (:530)
holds the payment lock then INSERTs allocation rows. Classic inversion
→ PG 40P01 → untyped 500 for one request. The P18 comment says "same
order allocate() takes (payment, then document)" — it omits that the
allocation row lock comes BEFORE the payment, which is the inversion.

**BE-P19-M4 — `create_return_periods`' IntegrityError catch poisons the
request transaction (the P18/BE-L4 fix is defective when it fires).**
`apps/gst/services/return_service.py:174-187` — `except IntegrityError:
continue` inside the `ATOMIC_REQUESTS` transaction without a savepoint;
the next loop query raises `TransactionManagementError` → 500 — the
exact untyped-500 the fix claimed to prevent. The P18 test never
exercises the catch (the `.exists()` pre-check short-circuits).

**BE-P19-M5 — `check_transmission_status_task`: the RLS write and the
adapter lookup run OUTSIDE `tenant_context`.**
`apps/peppol/tasks.py:231-263` — the `with tenant_context(org_id):`
block closes after the log lookup (:239); `get_adapter_for_org` (:243),
`adapter.check_status` (:244) and `log.save()` (:263) are outside. On a
real worker the settings query under RLS sees 0 rows → the error branch
returns a dict and the delivery-status write never lands. The P18 test
mocks TransmissionService so the RLS query never runs. Also the
docstring example (:223) omits the required `org_id` arg → TypeError
for copy-paste callers.

**BE-P19-M6 — journal list N+1: 3 queries per row, unpaginated.**
`apps/journal/serializers.py:75-87` (`obj.lines.all()` ×2 +
`obj.lines.count()` per entry) fed by `journal/views.py:80` with no
`prefetch_related`. O(3N+1) on the full org journal history.

**BE-P19-M7 — five non-UUID path converters still 500 on garbage ids
(the P17/BE-L2 class, unfixed islands).**
`apps/core/urls/__init__.py:47,53,61`
(`fiscal-years/<str:year_id>/close/`, `fiscal-periods/<str:period_id>/close/`,
`…/open/`) and `apps/coa/urls.py:38,41` (`<str:account_id>/`,
`<str:account_id>/balance/`) — malformed UUIDs raise untyped 500s
(Django `ValidationError` / SQL `DataError`); every sibling route was
converted to `<uuid:…>` in P17/P18.

### Medium (frontend)

**FE-P19-M1 — the bank-account EDIT path still uses the pre-P17
length-only PayNow UEN check (the shared ACRA regex never migrated).**
`src/app/(dashboard)/banking/components/bank-account-dialog.tsx:112` —
`id.length > 10` while the create/read schemas use `uenRegex.test(…)`
(`shared/schemas/bank-account.ts:63,121`). A malformed ≤10-char UEN
passes client validation on edit and only surfaces as a backend 400.

**FE-P19-M2 — the ContactPicker combobox is not WAI-ARIA operable (the
P16/P17/P18 deferred register's #1 item — still valid, unchanged).**
`src/components/contact-picker.tsx:121-135` (input), `:143-174`
(listbox) — no Escape, no ArrowDown/Up roving, no Enter-to-select, no
`aria-controls`, no `aria-activedescendant`, `aria-selected={false}`
hardcoded at :161, `role="option"` on nested buttons. Used by the
invoice form and both payment forms (primary flows). WCAG 2.2 AA miss.

**FE-P19-M3 — the in-app unsaved-work route guard is still absent (the
deferred register's #2 item).**
`src/hooks/use-unsaved-changes-guard.ts:17-20` registers the debt;
sidebar `shell.tsx:303-327` (8 Links) + `:480-486` (New Invoice) render
plain `Link`s. The invoice form's dirty state triggers only the
browser-level `beforeunload`; an in-app click on "Dashboard" silently
discards a dirty invoice — the exact failure mode P17 fixed for
tab-close only.

**FE-P19-M4 — the PAID badge renders two different greens for the same
status (list vs detail).**
`invoices-client.tsx:27` → `bg-accent-primary text-void` (#00E585) vs
`invoice-detail-client.tsx:51` → `bg-success text-void` (#00FF94). Both
pass AA and the pairing gate (accent-primary is in
APPROVED_FOREGROUNDS) — the gate cannot catch status-token drift.

**FE-P19-M5 — the two highest-traffic money tables (invoices list +
detail) are missing `scope="col"` while quotes/reports/ledger have it.**
`invoices-client.tsx:198-216` (6 `<th>`) and
`invoice-detail-client.tsx:502-515` (4 `<th>`); compliant exemplars:
`ledger-table.tsx:221-231` (scope AND aria-sort), `quotes-client.tsx:111-117`.
WCAG 1.3.1/H63.

### Medium (cross-cutting)

**X-P19-M1 — the enforced frontend CSP carries no report-uri: production
violations are invisible.**
`apps/web/src/lib/csp.ts:50-71` — `buildCsp()` ends at
`upgrade-insecure-requests`; the backend report-only CSP binds
`report-uri /api/v1/security/csp-report/` (exists + tested,
`config/urls.py:159`, `apps/core/views/security.py:25`), but the policy
browsers actually enforce has no reporting. The exact failure class
P16/FE-C1 fixed is now silent in prod.

**X-P19-M2 — the CSV import has no size cap (deferred item: cap
absent; dedup exists).**
`apps/backend/apps/banking/services/reconciliation_service.py:137-146`
— whole-file `read()` + full-string decode (memory doubled); no size or
row-count ceiling anywhere in the view/service. An authenticated
`CanManageBanking` user can OOM a worker with one oversized statement.

**X-P19-M3 — the compose celery-beat service uses DatabaseScheduler
whose tables §15c intentionally omits: deterministic crash-loop on the
documented Docker route.**
`apps/backend/docker-compose.yml:99-123` — the beat command is exactly
`--scheduler django_celery_beat.schedulers:DatabaseScheduler` while
`database_schema.sql:3262-3264` documents the beat tables as an
intentional omission pending a maintenance decision.

**X-P19-M4 — the P18 `PG_BASE` parametrization is incomplete (the
fresh-host story breaks at the step it fixed).**
`docs/setup_pg_z.sh:28` — the initdb check hardcodes
`/home/z/my-project/pg/root/...` instead of `${PG_ROOT}`;
`docs/DEPLOYMENT.md:118-124` hardcodes
`PGBIN=/home/z/my-project/pg/root/usr/lib/postgresql/17/bin` for the
CREATE ROLE/DATABASE steps. On any host exporting
`PG_BASE="$HOME/pg"`, the check always misses and the doc commands
point at a nonexistent path.

### Low (fix batch)

| ID | Location | Finding |
|---|---|---|
| BE-P19-L1 | peppol/tasks.py:319-325 | cleanup task filters `transmitted_at__lt=cutoff` — PENDING rows with NULL `transmitted_at` (worker died pre-transmit) never match and accumulate forever |
| BE-P19-L3 | gst/return_service.py:466 | `amend_return`'s `select_for_update()` has no `transaction.atomic()` (the P16 legacy — its P18 siblings all wrap) |
| BE-P19-L5 | reconciliation_service.py:449 | `suggest_matches` N+1 on `payment.contact.name` (no `select_related("contact")`) |
| BE-D1 | journal/serializers.py:181, :129 | serializer tolerance `> 0.001` vs service/DB trigger `0.0001` (deferred #5) — a 0.0002 imbalance passes the serializer then dies in the service; `balanced` flag can lie |
| BE-D2 | common/decimal_utils.py:70-96 | `display_money` has no `is_finite` gate (`display_money("NaN")` → `"NaN"`) — deferred #7, latent |
| FE-P19-L1 | invoice-form.tsx:433-436, invoice-line-row.tsx:118-125 | invalid grid ARIA: orphaned `row`/`rowgroup`/`rowheader` roles pruned by browsers — the line editor is an unlabelled field soup for SR users |
| FE-P19-L2 | receive/make-payment-form, reconcile-form, import-transactions-form | five icon-only X-close buttons with no accessible name |
| FE-P19-L3 | invoice-detail-client.tsx:147-152, 283-287 | the back link (icon-only) unnamed in the loaded/no-org states (the error-state twin has it) |
| FE-P19-L4 | receive/make-payment-form | payment/reconcile fields unlabelled for SR (SelectTrigger, dates); field errors not announced (no `role="alert"`) |
| FE-P19-L5 | new-organisation-client.tsx:217 | `accent-[var(--accent-primary,#e8ff17)]` — the token is `--color-accent-primary`, so the wrong fallback color always wins (the silent-dead-token class P17 fixed) |
| FE-P19-L6 | contrast-pairings.test.ts:113 | the ratio loop omits `color-warning` though `bg-warning text-void` is live (11.45:1, ungated) |
| FE-P19-L7 | five eslint parity warnings | 4 trivially fixable (e2e unused interface, tax-breakdown deps, auth-provider `router`, invoice-form lines memo); 1 is a documented TanStack/React-Compiler decision |
| FE-P19-L8 | contacts-client.tsx:306, settings-client.tsx:147-151 | UEN client validation not applied on the two UEN *edit* surfaces (create validates via the shared schema) |
| X-P19-L2 | e2e/*.spec.ts (~20 sites) | the demo-password fallback `"demo1234"` (8 chars) can never be valid under the 12-char register floor — the documented password is `demo1234pass` |
| X-P19-L3 | apps/web/package.json:56 | `uuid` runtime dep unused (all generation via `crypto.randomUUID()`) |
| X-P19-L4 | config/settings/service.py:34-38 | `ALLOWED_HOSTS` read via `os.environ` only, not `.env`-aware decouple (split semantics vs base.py) |
| X-P19-L5 | .github/workflows/ci.yml:336-344 | the ci-summary failure gate ignores the security-scan job result |
| X-P19-L1 | P18 report :28,146-148 + ci.yml:11 | the report describes a `--grep`-scoped CI e2e job; ci.yml has no grep (stronger, actually); ci.yml header version stale |

## 3. The plan (phased ToDo — TDD, every behavioural fix RED first)

### Phase 1 — backend (the money-path truth gap + the locking completion)

| # | Task | Fix | Test (RED first) |
|---|---|---|---|
| 1 | **BE-H1** | `remove_line`: wrap in `transaction.atomic()`, `select_for_update()` on the document, post-lock DRAFT re-check (mirror `add_line`) | the P19 concurrency contract file: approve-then-remove race → refused, APPROVED intact; remove-vs-remove interleaving |
| 2 | **BE-M3** | `unallocate`: re-order to payment → allocation → document | deadlock-order probe (the P18 sequential-pin pattern) |
| 3 | **BE-M1** | `archive_account`: bypass the cache for the gate (`cache.delete(key)` before the balance read) | seed cache → post journal line → archive must 400 |
| 4 | **BE-M2** | `create_entry`: `select_for_update()` the account row inside the existing atomic | archive-vs-post interleaving → post refused on archived |
| 5 | **BE-M4** | `create_return_periods`: per-period savepoint (`with transaction.atomic():` inside the try) | stub `.exists()` → force the IntegrityError branch → no TransactionManagementError |
| 6 | **BE-M5** | `check_transmission_status_task`: move lookup + adapter + save inside `tenant_context`; fix the docstring example | GUC probe at save time (probe the model write, not the mocked adapter) |
| 7 | **BE-M6** | journal list: `prefetch_related("lines")` + `annotate(line_count=Count)`; serializer reads the annotation | query-count assertion (assertNumQueries-style) |
| 8 | **BE-M7** | convert the 5 `<str:…>` routes to `<uuid:…>` (core fiscal ×3, coa account ×2) | garbage-id contract tests → 404 at routing |
| 9 | **BE-L1** | cleanup task: `| Q(transmitted_at__isnull=True)` with `created_at` fallback cutoff | PENDING row with NULL transmitted_at is cleaned |
| 10 | **BE-L3** | `amend_return`: wrap in `transaction.atomic()` | existing tests stay green (behavior-preserving wrap) |
| 11 | **BE-L5** | `suggest_matches`: `select_related("contact")` | query-count drop |
| 12 | **BE-D1** | journal serializer tolerance `0.001` → `0.0001` (create gate + `balanced` flag) | contract tests at the 0.0002 boundary |
| 13 | **BE-D2** | `display_money`: `is_finite` gate (mirror `money()`) | NaN/Infinity → typed error |

### Phase 2 — frontend (the modal semantics, the keyboard flows, the combobox)

| # | Task | Fix | Test (RED first) |
|---|---|---|---|
| 14 | **FE-H1** | the 4 banking modals → the Radix `Dialog` primitive (keep the inner Card as content; wire `onCancel` to `onOpenChange(false)`) | role="dialog", Escape closes, focus trap/return (the shell-mobile-nav test patterns) |
| 15 | **FE-H2** | transaction-row header → `<button type="button" aria-expanded aria-controls>` | keyboard user can expand + reach Reconcile |
| 16 | **FE-M1** | bank-account edit: `uenRegex.test(...)` (import from the shared schema) | edit-path mirror of the create-path test |
| 17 | **FE-M2** | ContactPicker: full WAI-ARIA 1.0 combobox — listbox id + `aria-controls`, `aria-activedescendant` roving, Escape/Enter/arrows/Home/End, `aria-selected` reflecting value | keyboard-interaction test matrix (open, navigate, select, escape, typeahead) |
| 18 | **FE-M3** | in-app route guard: a document-capture click interceptor (`useUnsavedRouteGuard(dirty)`) reading the invoice store's `hasUnsavedChanges` + confirm dialog (the void-dialog pattern); plain/modifier clicks pass through | dirty invoice + sidebar link click → confirm shown; confirm → navigates; cancel → stays |
| 19 | **FE-M4** | invoices list PAID badge → `bg-success text-void` | the pairing gate enumeration (already covers the file) + class assertion |
| 20 | **FE-M5** | `scope="col"` on the invoices list/detail `<th>`s | render + assert scope |
| 21 | **FE-L1** | invoice line grid: drop the decorative orphaned roles; label inputs with row context (`aria-label="Line N unit price"`) | a11y-tree assertion (labels carry row context) |
| 22 | **FE-L2/L3/L4** | the aria batch: `aria-label` on the 5 X-buttons + 2 back-links; label the payment-form SelectTriggers/inputs; `role="alert"` on field errors | getByRole({ name }) matrix |
| 23 | **FE-L5** | GST checkbox: `accent-primary` (the real token utility) | computed-style/token test |
| 24 | **FE-L6** | the contrast gate: add `color-warning` to the ratio loop | the gate itself (RED: temporarily assert the token exists in the loop) |
| 25 | **FE-L7** | fix 4 eslint warnings (unused interface, deps destructure, `router` dep, lines-memo identity); file the TanStack one as a documented disable | eslint 0E/1W → 0E/0W or documented |
| 26 | **FE-L8** | UEN edit validation: `optionalUenSchema` on blur/submit in contacts-edit + org-settings edit | the ACRA parity tests (mirror the create path) |

### Phase 3 — cross-cutting (the production observability + deployability)

| # | Task | Fix | Test (RED first) |
|---|---|---|---|
| 27 | **X-M1** | `buildCsp()`: `report-uri ${apiUrl}/api/v1/security/csp-report/` (production branch) | csp.test.ts: the directive present, the URL derived from the env |
| 28 | **X-M2** | CSV import: `csv_file.size` cap (~5MB) + row ceiling, typed 400 | oversized/beyond-ceiling file → typed refusal; at-limit → imports |
| 29 | **X-M3** | compose: drop the celery-beat service (aligns with §15c's documented decision) | docker-compose config -q (static validation, the documented method) |
| 30 | **X-M4** | `setup_pg_z.sh:28` → `${PG_ROOT}`; DEPLOYMENT §3 → `PGBIN` derived from `$PG_BASE` | shellcheck-style read-through + the documented command shapes |
| 31 | **X-L2** | e2e demo-password fallback → `demo1234pass` (~20 sites) | grep sweep + one spec run |
| 32 | **X-L3** | drop the unused `uuid` dep | `npm ls`/install parity + tsc/vitest green |
| 33 | **X-L4** | service.py `ALLOWED_HOSTS` → decouple `config(..., cast=Csv())` | settings unit test (the copy-on-write pattern) |
| 34 | **X-L5** | ci-summary: include `security-scan.result != 'success'` in the failure gate | workflow lint (yamllint/actionlint if available; else schema check) |
| 35 | **X-L1** | the P18 report erratum (the `--grep` mechanism) + ci.yml header version bump | docs-only; read-through |

### Phase 4 — gates, captures, deliverables

Full gate matrix re-run (backend · vitest · tsc · eslint · build ·
e2e:full on the live stack · rls_smoke 13/13 · mobile-nav 17/17 ·
prod-CSP 5/5 — the CSP smoke gains the report-uri assertion via X-M1);
session-38 screenshots (`docs/screenshots/`, the P19 proof surfaces:
the Radix-ified banking modals, the keyboard-expandable transaction
row, the ContactPicker combobox in the invoice form, the route-guard
confirm dialog); the docs truth pass; `docs/session_38.md`; the
worklog entry; the conventional commit series; the SSH-wrapper push
to `main`.

## 4. Deferred register (updated, carried forward)

**Fixed this sprint (removed from the register):** the ContactPicker
WAI-ARIA combobox and the in-app unsaved-work route guard (the two
oldest P16 items, if Phase 2 completes); the journal serializer
tolerance and `display_money` finite gate (the two S-effort
deferreds); the CSV size cap; the CSP report-uri.

**Still deferred (with rationale):**
- **List pagination** (BE) — needs a per-view design decision +
  frontend pagination UX; the envelope work below is its prerequisite.
- **List-envelope `{data}`/`{results}` unification** (BE) — 15
  `{results}` sites + 6 `{data}` sites + 1 raw array; a coordinated
  contract change across both tiers; the frontend currently parses
  both shapes, so it is debt, not breakage.
- **Audit-log `INSERT WITH CHECK (TRUE)`** (schema) — needs the scoped
  INSERT policy design (or a SECURITY DEFINER write path); schema
  change, out of P19's no-DDL scope.
- **Org-mid-flight dead-letter design** (BE) — needs the persistent
  failure-record model decision.
- **UEN checksum** (BE) — needs the official IRAS algorithm; the
  format-only validator honestly documents this.
- **NULL-context SELECT policies** (schema §17) — the documented
  pre-context membership tradeoff; unchanged.
- **H-05b attachment/threshold models** (BE) — schema-only tables
  without Django models; needs the feature decision.
- **ruff register** (BE) — 1279 mechanical findings (856 auto-fixable);
  batched, mechanical, zero-risk, but large; next dedicated pass.
- **The payments-tab same-route prefill re-trigger** (FE) — no current
  producer; keyed-remount fix registered for when one appears.
- **The TanStack `useReactTable` React-Compiler incompatibility** (FE)
  — upstream limitation; documented disable decision lands this sprint
  (FE-L7), the underlying incompatibility stays.
- **The 5 remaining eslint parity warnings** — 4 fixed this sprint; the
  TanStack one documented.

## 5. Plan validation checklist (pre-execution)

- [x] Every High/Medium anchor hand-verified in source this session
      (BE-H1, FE-H1, FE-H2, BE-M1/M2/M3/M5/M7, FE-M1/M4/M5, X-M1/M2/M3/M4 —
      the sed excerpts above)
- [x] The baselines reproduced green before planning (§1)
- [x] No schema changes required by any fix (all code/config/docs)
- [x] The TDD harnesses exist (the P18 concurrency contract file, the
      vitest a11y patterns in shell-mobile-nav/contrast-pairings, the
      csp.test.ts, the reconciliation tests)
- [x] `skills/` untouched by every fix
- [x] Deferral decisions recorded with rationale (§4)
