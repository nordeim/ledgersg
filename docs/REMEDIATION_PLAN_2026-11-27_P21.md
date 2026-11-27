# LedgerSG — Remediation Plan (P21 Sprint: The List-Envelope Unification, the InvoiceNow Evidence Stamp, the Cache-Commit Truth & the Banking A11y Batch)

**Date:** 2026-11-27 (session 42)
**Base commit:** `67512bf1` (main — post-P20, all gates green at 950P/0F/5S backend · 627/627 vitest · tsc 0 · eslint 0E/0W · live e2e 40P/0F/0S · rls_smoke 13/13 · mobile-nav 17/17 · prod-CSP smoke 5/5 · schema v1.2.2)
**Method for execution:** TDD (RED → GREEN → full gate) for every behavioural fix; lint parity on touched files (ruff backend, eslint frontend); conventional commits on `main`; `skills/` excluded from all checks/tests/compilation; **no schema changes** (v1.2.2 carries forward — the audit-log INSERT policy design stays deferred).

---

## 1. Audit inputs (this session's evidence)

Three parallel deep audits (Mode C) + lead hand-verification of every High
finding in source, plus the documented P20 baselines reproduced on the
surviving session-40 workspace (rootless PG 17 up, Redis 8 on :6379, schema
v1.2.2 loaded into both databases — `test_ledgersg_dev` recreated and loaded
this session, backend venv installed, the dev stack live on :8000 + :3000,
the :8001 rls instance healthy):

- **Baselines reproduced** (all executed, green): backend **950P/0F/5S**
  (`pytest --reuse-db --no-migrations -q`, 20.5s) · vitest **627/627**
  (73 files, 88.8s) · `npx tsc --noEmit` 0 · whole-tree `npx eslint .`
  **0 errors / 0 warnings** · **mobile-nav live probe 17/17 at
  375/800/1280** — **the navigation works; no TailwindCSS v4 bug exists**
  (twelfth consecutive live settlement; the v4 setup re-verified clean:
  `@import "tailwindcss"` + `tw-animate-css`, no legacy config; the FE
  audit's compile-verified dead-token sweep found exactly one dead utility —
  `accent-primary`, finding FE-P21-L1) · live e2e:full **40/40 on the
  first run** · rls_smoke **13/13** as `ledgersg_app` on the :8001
  instance · prod-CSP smoke **5/5** (build:server green).
- **Backend audit** (P20-diff soundness + lock-order matrix + cache/commit
  placement + Peppol delivery path + envelope/pagination/ruff re-measure):
  **0 Critical, 0 High, 6 Medium, 5 Low, 4 Informational.** All 8 P20
  backend fixes verified sound and test-pinned (13/13 re-run). The residual
  findings: the bank-account default flag TOCTOU + unlocked full-row saves
  (M1), the dashboard cache not invalidated by void / manual journal
  entries (M2), cache invalidation executing before commit (M3), the
  never-written `invoicenow_sent_at` evidence column (M4), the
  ValidateBalanceView 500s on malformed bodies (M5), and no list
  pagination with `LedgerView` materialising every line (M6 — deferred with
  its prerequisite done this sprint).
- **Frontend audit** (P20-diff verification + WCAG 2.2 AA sweep on the
  banking/settings/contacts/reports surfaces + Tailwind v4 compile-verified
  hygiene + config/coverage/dead-code/query-key sweeps): **0 Critical,
  2 High, 5 Medium, 5 Low, 5 Informational.** All 10 P20 frontend fixes
  verified sound (avg 9.1/10). The Highs are the same a11y failure class as
  P20 on surfaces P20 did not touch: the Make-Payment "Reference" input has
  no accessible name (H1) and the CSV import file input is
  keyboard-inaccessible (H2). Query-key sweep CLEAN; type-safety CLEAN
  (zero `any`/`@ts-ignore` in src); coverage green at every tier with the
  whole-suite measured at 72.07/69.21/61.74/72.61 vs the 71/60/68/71 floor.
- **Cross-cutting truth audit** (docs drift + CI truth + env-example truth
  + DEPLOYMENT fresh-host walk + API-guide route verification + endpoint
  count): **0 Critical, 0 High, 9 Medium, 5 Low, 4 Informational.** The
  DEPLOYMENT walk, both `.env.example`s (variable-by-variable), the API
  guide's ~45 route references (all four P20 errata verified holding), the
  CI pipeline, session_41 and the worklog are all truthful. The Mediums are
  one pattern: the P20 truth pass updated every doc's top status block but
  left second-tier surfaces stale (README badge + test-execution section +
  milestone order, CLAUDE's P18 gate row, AGENTS header/DB version/posture
  rows, SKILL quick-ref, PAD lint row).

**Combined: 0 Critical / 2 High / 20 Medium / 15 Low / 13 Informational.**
Every High and every execution-scoped Medium hand-verified in source by the
lead (file:line anchors below) before this plan was written.

## 2. The findings (verified, with evidence anchors)

### High

**FE-P21-H1 — the Make-Payment form's Reference input has no accessible
name (the P20 FE-H1 class, on the payables money form P20 did not touch).**
`apps/web/src/app/(dashboard)/banking/components/make-payment-form.tsx:240-247`
— `<label className="text-sm text-text-secondary">Reference</label>` with
no `htmlFor`, followed by a raw `<Input>` with no `id`/`aria-label` (the
in-file "Notes" twin at :253-255 carries `aria-label="Notes"` — the fix
pattern exists 14 lines below). WCAG 1.3.1/4.1.2 Level A on the payables
money-entry form.

**FE-P21-H2 — the CSV import file input is keyboard-inaccessible (WCAG
2.1.1 Level A).**
`apps/web/src/app/(dashboard)/banking/components/import-transactions-form.tsx:176-191`
— `<input id="csv-file" type="file" className="hidden" />` (`display:none`
removes the input from the tab order and the a11y tree) with a
`<label htmlFor="csv-file">` that is not focusable. Keyboard-only users
have no path to import a bank statement; the e2e suite masks it
(`setInputFiles` bypasses the UI). Fix: `sr-only` instead of `hidden`
(visually hidden, focusable, in the a11y tree) — the native file input
then opens the picker on Enter/Space.

### Medium (this sprint's execution scope)

**BE-P21-M1 — the bank-account default flag TOCTOU + unlocked full-row
saves (the exact P20 class, on the banking config surface).**
`apps/backend/apps/banking/services/bank_account_service.py:290-327`
(`set_default`): a plain `get()` read, an unlocked
`filter(org_id, is_default=True).update(is_default=False)`, then a
full-row `bank_account.save()` — two concurrent `set_default` calls
(reachable via `PATCH is_default: true`, `banking/views.py:118`) can
interleave to leave **two defaults**, and the full-row save clobbers
concurrent `opening_balance` edits. `update()` (:167-238) and
`deactivate()` (:240-286, the "only active account" count check) carry the
same unlocked shape. Fix: `select_for_update()` on the target + the
current default inside the atomic, `update_fields` on the saves (the P20
`transition_status` pattern).

**BE-P21-M2 — the dashboard cache is not invalidated by void or by manual
journal entries (the P5/H-3 completion the invalidation contract claims).**
`_invalidate_dashboard_cache` call sites: `document_service.py:934`
(approve only — `void_document` at :938-1027 has NO call although a void
reverses ledger postings and changes outstanding AR) and nothing in
`journal_service.create_entry` (manual entries shift revenue/expense
totals the dashboard reads). Fix: call the invalidator in `void_document`
and `create_entry` (local import, exception-guarded — the established
pattern).

**BE-P21-M3 — cache invalidation executes before commit (the re-seed
race).**
`apps/backend/apps/journal/services/journal_service.py:318-323` (the P20
`account_balance` deletes) and `apps/backend/apps/banking/services/payment_service.py:435,611`
(the dashboard invalidations) all run INSIDE the open `@transaction.atomic()`
— a cache read in the delete→commit window re-seeds the pre-commit value
from the DB (invisible under READ COMMITTED) and it then survives to TTL.
Fix: `transaction.on_commit()` for every cache delete/invalidate on the
mutation paths.

**BE-P21-M4 — `invoicenow_sent_at` is never written; the evidence-based
"restore to SENT" branch is dead code.**
Readers: `payment_service.py:421-423, 738-740`
(`"SENT" if document.invoicenow_sent_at else "APPROVED"` — the P16/L2
evidence-based restore design). Writers: none anywhere (exhaustive sweep
of apps/ config/ common/ + the SQL). The Peppol pipeline ends at
`_update_log_with_result` setting `log.status = "DELIVERED"`
(`peppol/services/transmission_service.py:276-294`) without stamping the
document. Fix: stamp `document.invoicenow_sent_at = timezone.now()` in the
success branch (the column already exists in schema + model —
`core/models/invoice_document.py:130`); the document status stays
APPROVED (the transition map is not touched — the evidence column is
consulted only at restore time).

**BE-P21-M5 — `ValidateBalanceView` 500s on malformed bodies (the P7/F-11
class, missed on this body).**
`apps/backend/apps/journal/views.py:325-326` —
`Decimal(str(line.get("debit", 0)))` over raw `request.data["lines"]`:
`"debit": "abc"` → `decimal.InvalidOperation` → untyped 500; `lines` as a
dict/string → `AttributeError` (`.get` on a string key). Fix: the shared
typed-parse helpers (`common.query_params` / the P7 pattern) → clean 400s.

**BE-P21-M6 (→ the envelope unification, promoted from L1 to this
sprint's named task) — the list envelope has 5 shapes across 30 sites.**
Re-measured (audit + lead verification): 19 `{results, count}` sites + 1
`{results, totals}` + 6 `{data, count}` + 3 report-style `{data: {...}}` +
1 raw array. The unified contract: **lists return `{results, count}`;
single-report payloads keep `{data: {...}}`.** The seven non-conforming
list sites (all verified in source):
`core/views/organisations.py:55` (OrganisationListCreateView.get) ·
`core/views/organisations.py:216` (FiscalYearListView.get) ·
`core/views/auth.py:335` (`my_organisations_view` — raw array) ·
`journal/views.py:202` (TrialBalanceView — `{data, count, totals,
as_of_date}`) · `journal/views.py:267` (EntryTypesView) ·
`gst/views.py:202` (TaxCodeIrasInfoView) · `gst/views.py:339`
(GSTReturnListCreateView.post — `{message, count, data}`). Frontend
consumers: `use-fiscal.ts` (`FiscalYearsResponse.data`) +
`fiscal-card.tsx:61` (`yearsData?.data`) + `auth-provider.tsx` (4 call
sites reading the raw array). Tests pinning the old shapes:
`test_organisation_api.py:22-27,185-186`, `test_journal_workflow.py:224,278,280`,
`test_gst_calculation.py:132,135`, `test_auth_org_context.py` (the
my_organisations raw-array asserts). Scripts:
`scripts/bootstrap_demo_substrate_session40.sh:36-39` (the dual-shape
fallback — simplifies to `results`). **Bonus truth finding:** the RLS
isolation test reads `response.data.get("data", [])` against the
accounts list which returns `{results}` —
`tests/security/test_rls_isolation.py:59` asserts a vacuous empty list
(always passes, even if isolation broke). Fixed together.

**FE-P21-M1 — duplicate DOM id "bank-account" → wrong label association
when the import dialog opens.**
`transaction-filters.tsx:94,101` AND `import-transactions-form.tsx:149,157`
both use `htmlFor="bank-account"` / `id="bank-account"`. The import dialog
(Radix portal, opened from the Transactions tab that renders the filters)
co-mounts above the always-rendered filters; `getElementById` resolves
first-in-DOM → the dialog's "Bank Account" label points at the background
filter's select. Fix: run-unique ids (the import form's become
`import-bank-account`).

**FE-P21-M2 — the P20 live-region class applied to 5 blocks; ~13
same-class loaders remain (WCAG 4.1.3 AA).**
`banking-client.tsx:49-55,151-160` · `settings-client.tsx:64-70,87-93` ·
`contacts-client.tsx:108-112,346-350` ·
`reports-client.tsx:266-270,330-334,384-388,468-472,641-645` ·
`fiscal-card.tsx:45-58` · `invoicenow-settings-card.tsx:26-39` ·
`allocation-section.tsx:94-98` — spinner-only loading blocks, no
`role="status"`, no text equivalent. Fix: the P20 pattern
(`role="status"` + `aria-live="polite"` + sr-only text).

**FE-P21-M3 — the FE-M7 timezone class residuals: the GST year derived in
the local timezone; UTC "today" defaults.**
`reports-client.tsx:119` —
`new Date(asAt).getFullYear()` on a UTC-parsed date-only string reads the
LOCAL year → for a runner behind UTC, "2026-01-01" yields 2025 and the GST
F5 tab queries the wrong year's returns. `reports-client.tsx:44-50` —
`todayISO()` returns UTC-today (`toISOString().slice(0, 10)`) as the
default report/payment dates (yesterday for users behind UTC; the same
pattern at `receive-payment-form.tsx:53` and `make-payment-form.tsx:50`).
Fix: the GST year lexically from the ISO string (`Number(asAt.slice(0,
4))` — deterministic, timezone-free); `todayISO` from LOCAL date parts
(matching the pinned Asia/Singapore runner and the SG user base).

**FE-P21-M4 — the payment card is a clickable div with no keyboard
contract (the P19 transaction-row class, unfixed here).**
`payment-card.tsx:25-29` — `<Card onClick={...}>` with `cursor-pointer`
but no `role`/`tabIndex`/keydown. Latent today (the onClick chain ends in
a write-only `setSelectedPaymentId`) but becomes mouse-only the moment a
real handler lands. Fix: the P19 pattern (`role="button"`, `tabIndex={0}`,
Enter/Space keydown, focus-visible styling).

**FE-P21-M5 — the reconcile dialog's match selection is invisible to
assistive tech.**
`reconcile-form.tsx:115-146` — the match buttons convey selection only via
`border-accent-primary bg-accent-primary/10`; no `aria-pressed`, no
radiogroup semantics. Fix: `aria-pressed` on the toggle buttons (the
lightest correct semantics for a single-select list of option buttons).

**X-P21 doc batch (9 Medium + 5 Low — one consolidated truth pass).**
M1 README:3 badge `tests-1555` (P18-era; truth 1,617) · M2 README:385-427
the whole test-execution section carries P19 counts (937/619) · M3
README:114-141 milestone order (P18 first, P20 second) · M4 CLAUDE:54-69
the "P18" block shows the P19 gate row; no P19 section exists · M5
AGENTS:5-6 header says "P18 remediated" · M6 AGENTS:264 `Database: v1.2.1`
· M7 AGENTS:268 "P0–P17 remediated" · M8 ledgersg_SKILL:725 quick-ref
`v1.2.1` · M9 PAD:55 the P20 metrics lint row "0 errors / 5 warnings".
Lows: API guide:90,126 two superseded addenda labeled "Current" · API
guide:6 "Last Updated" line attributes P17 · README:699 Tailwind "4.0"
(lockfile: 4.2.1) · ledgersg_SKILL:32 NUMERIC widening attributed to
v1.2.0 (shipped v1.1.0) · ci.yml:189-197 the eslint step comment still
describes the 5-warning register (0 today).

### Low (this sprint's execution scope)

- **FE-P21-L1** — `new-organisation-client.tsx:217` `accent-primary` is a
  compile-verified dead utility (no `--color-primary` token exists; the
  token is `--color-accent-primary`). Fix: the compiling form.
- **FE-P21-L2** — `invoice-form.tsx:362-367` the visible "Customer" span
  carries a dangling `id="customer-picker-label"` nothing references (the
  picker self-names). Fix: `aria-labelledby` on the picker (visible label
  becomes the accessible name — the better a11y outcome).
- **FE-P21-L3** — `transaction-row.tsx:65-66` and `payment-list.tsx:158-159`
  `aria-controls` points at an id rendered only when expanded (invalid
  while collapsed). Fix: the id always rendered (content conditional
  inside the region).
- **FE-P21-L5** — `playwright.config.ts:76` `video: "on-first-retry"` with
  local `retries: 0` records no video for local failures — the exact flaw
  the P20 trace comment documents and fixed for traces. Fix:
  `retain-on-failure`.
- **FE-P21-I4** — `package.json` lost its trailing newline in the P20
  commit. Restored.
- **BE-P21-I4b** — `invoicing/views.py:482` the redundant function-local
  `Decimal` import (P20/L1 added the module-level one). Removed.

### Explicitly deferred this sprint (registered, not dropped — see §4)

Full list **pagination** (BE-P21-M6's scope-mate — now unblocked by the
envelope unification, its stated prerequisite; needs the per-view
limit/offset design + the frontend UX, incl. `LedgerView` line-level
materialisation); the **ruff mechanical batch** (re-measured 936
production / 1307 whole-tree; top: W293 ×376, I001 ×123, F401 ×121, B904
×65 — a dedicated pass, lint-parity-on-touched-files only this sprint);
the audit-log INSERT WITH CHECK policy (schema DDL); BE-P21-L3 config-class
locking (coa/tax-code/contact/org services — low blast radius, next
locking pass); BE-P21-L4 Peppol log-state locking; the rest of the P20
deferred register carries forward unchanged (dead-letter design, UEN
checksum, NULL-context SELECT tradeoff, H-05b models, PaymentsTab prefill,
TanStack incompatibility, FE-M2/M3 designs, the FE L-batch remainder,
CI hardening, version-story reconciliation).

## 3. The execution plan (phases, TDD)

### Phase 1 — backend: the envelope unification + the cache/commit +
evidence/locking batch (RED first)

| Task | Fix | Tests (RED first) |
|---|---|---|
| BE-M6 (the envelope) | the 7 sites → `{results, count}` (TrialBalance keeps `totals` + `as_of_date`; the GST post keeps `message`; `my_organisations` gains the envelope); report-style `{data: {...}}` payloads unchanged (documented convention) | the shape-pinning tests updated to the new contract FIRST (test_organisation_api, test_journal_workflow, test_gst_calculation, test_auth_org_context) → RED → views → GREEN; the vacuous RLS isolation assert (`test_rls_isolation.py:59`) fixed to read `results` and actually assert isolation |
| BE-M1 | `set_default`/`update`/`deactivate`: `select_for_update` on the target (+ the current default in set_default), `update_fields` saves | the lock-spy + the two-defaults interleaving probe (T1/T2 concurrent set_default → exactly one default) + the no-clobber probe |
| BE-M2 | `_invalidate_dashboard_cache` in `void_document` + `create_entry` | the cache-seed probe (seed → void → the dashboard read is fresh; seed → manual entry → fresh) |
| BE-M3 | every mutation-path cache delete/invalidate → `transaction.on_commit` | the commit-window probe (a read between the mutation and the commit must not re-seed the stale value; on_commit fires post-commit — assert the cache state after the outer transaction exits) |
| BE-M4 | stamp `invoicenow_sent_at` on the DELIVERED branch (the document status untouched) | the delivery test (successful transmission → the document row carries the stamp; failure → no stamp) |
| BE-M5 | `ValidateBalanceView`: typed parse of `lines` (list-of-dicts, numeric debit/credit) → 400 envelope on garbage | the malformed-body tests (non-numeric debit → 400, lines-as-dict → 400, valid body → 200 unchanged) |

### Phase 2 — frontend: the banking a11y batch + the envelope consumers +
the timezone class (vitest RED first)

| Task | Fix | Tests (RED first) |
|---|---|---|
| FE-H1 | `aria-label="Reference"` on the Make-Payment input (the in-file Notes pattern) | `getByRole("textbox", { name: "Reference" })` |
| FE-H2 | the CSV input `sr-only` (focusable, a11y-tree present; the label keeps its click target) | the input is focusable + labelled (`toHaveFocus` walk / by-role with name "CSV File") |
| FE-M1 | unique ids in the import dialog (`import-bank-account`, `csv-file` stays — it is unique) | the dialog's label resolves to the dialog's select (no duplicate id in the co-mounted DOM) |
| FE-M2 | the ~13 loaders → `role="status"` + `aria-live="polite"` + sr-only text (the P20 pattern) | the status-role assertions per surface (banking/settings/contacts/reports/fiscal/invoicenow/allocation) |
| FE-M3 | `gstYear` lexical (`Number(asAt.slice(0, 4))`); `todayISO`/`firstOfYearISO` local-date-based | the year-derivation test (pinned non-UTC system time → the lexical year; todayISO matches the local calendar date) |
| FE-M4 | payment-card: `role="button"` + `tabIndex` + Enter/Space + focus-visible | the keyboard-activation test |
| FE-M5 | reconcile match buttons `aria-pressed` | the pressed-state assertion |
| FE-L1/L2/L3/L5/I4 | the dead `accent-*` token → the compiling form; the Customer label wired via `aria-labelledby`; `aria-controls` ids always rendered; playwright `video: "retain-on-failure"`; the package.json newline | the token compiles (the design-tokens gate pattern); the by-labelledby resolution; the collapsed-state controls resolution; config schema-valid |
| Envelope consumers | `use-fiscal.ts` interface + `fiscal-card.tsx:61` → `results`; `auth-provider.tsx` reads `{results}` from the orgs list | the hook/component tests updated to the new shape (RED first) |

### Phase 3 — cross-cutting: the docs truth pass + the script/env/doc alignment

| Task | Fix | Verification |
|---|---|---|
| X-doc batch | the 9 Mediums + 5 Lows (README badge/test-section/milestone-order, CLAUDE P18→P19 gate row + a P19 section, AGENTS header/v1.2.2/posture, SKILL quick-ref + the NUMERIC v1.1.0 attribution, PAD lint row, the API guide "Current"/"Last Updated" labels, README Tailwind 4.2.1, the ci.yml comment) + every doc's P21 milestone frame | doc review; each count re-measured against the executed gates |
| API guide | the 7 unified-envelope rows documented (the old shapes as errata) + the metrics row + version 3.2.0 | each route/shape re-verified against the live urls |
| DEPLOYMENT.md | the §7/§9 counts refreshed to the P21 gate; any envelope reference aligned | doc review |
| bootstrap script | the dual-shape fallback simplified to `results` + the stale inconsistency comment removed; the script re-run green (idempotent double-run) against the live stack | executed |
| .env.example | verified truthful variable-by-variable by the audit (nothing stale, nothing missing, both apps) — the deliverable already exists and is committed; no changes required this sprint | the audit's verification table; re-checked |
| README/PAD/CLAUDE/AGENTS/SKILL | the P21 milestone sections (the gate, the envelope convention, the evidence stamp, the cache-commit truth) | doc review |

### Phase 4 — gates, captures, deliverables

The full gate matrix (backend · vitest · tsc · eslint 0E/0W · coverage at
the ratchet · live e2e:full · rls_smoke · mobile-nav · prod-CSP);
8 DOM-verified screenshots (`docs/screenshots/128-135_*_session42.png`);
the P21 report (`docs/REMEDIATION_2026-11-27_P21_REPORT.md`); the session
log (`docs/session_42.md`); the worklog entry; the docs truth pass; the
conventional commits and the SSH-wrapper push to main.

## 4. Deferred register (updated, carried forward)

**Fixed this sprint (removed):** the list-envelope unification (7 sites +
the frontend consumers + the bootstrap script + the vacuous RLS assert);
the bank-account default-flag locking; the void/manual-entry dashboard
invalidation; the on_commit cache placement; the `invoicenow_sent_at`
evidence stamp; the ValidateBalanceView 400 contract; the two banking
a11y Highs + the import-dialog id + the loader live regions + the
timezone class + the payment-card keyboard contract + the reconcile
selection semantics + the FE L-batch (L1/L2/L3/L5); the docs truth batch.

**Still deferred (with rationale):**
- **List pagination** — the per-view limit/offset design + frontend UX
  (the envelope prerequisite is now DONE; `LedgerView` line-level
  materialisation is the first target).
- **ruff mechanical batch** — re-measured 936 production / 1307
  whole-tree (W293 ×376, I001 ×123, F401 ×121, B904 ×65, UP045 ×45).
- **Audit-log `INSERT WITH CHECK (TRUE)`** — needs the scoped INSERT
  policy design (or a SECURITY DEFINER write path); schema change, out of
  the no-DDL scope.
- **BE-L3 config-class locking** (coa/tax-code/contact/org services) —
  low blast radius; next locking pass.
- **BE-L4 Peppol transmission-log state writes unlocked** — Celery
  retry interleaving; operational only.
- **BE-I3 CSV `errors[]` raw DB exception strings** — auth-gated;
  consider typed row-error messages.
- **Org-mid-flight dead-letter design; UEN checksum; NULL-context SELECT
  tradeoff; H-05b models; PaymentsTab prefill (no producer); TanStack
  React-Compiler incompatibility; the middleware membership-cache
  revocation window; the journal detail N+1; BE-M3-P20 fiscal close race;
  BE-M4-P20 reconcile FX comparator; BE-M6-P20 CSV dedupe (DDL);
  FE-M2-P20 route guard sentinel design; FE-M3-P20 drawer × dialog trap;
  X-L2/I1/I2 CI hardening; X-M8 version-story reconciliation** — all
  carried forward unchanged.
