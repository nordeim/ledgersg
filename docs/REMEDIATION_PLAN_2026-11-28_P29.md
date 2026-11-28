# LedgerSG — Remediation Plan (P29 Sprint: The Detail-View N+1 Closure + The Per-Glob Coverage Ratchet Raise + The Missing shared Tier)

**Date:** 2026-11-28 (session 55)
**Base commit:** `6f398bf3` (main — post-P28 + the session-54/55 logs)
**Method for execution:** TDD (RED → GREEN → full gate) for every behavioural change; eslint parity on touched files; conventional commits on `main`; `skills/` excluded from all checks/tests/compilation; **no schema changes** (v1.2.2 carries forward); the response bytes stay **byte-identical** (select_related/prefetch_related change HOW rows travel, not WHAT the serializer emits).
**Skills consulted:** `skills/skills-catalog.md` → `tdd` (the red→green loop), `code-review`/`debugging-and-error-recovery` (Mode B/C discipline), `rootless-postgresql` (the PG environment — live from the prior sessions, re-probed this session), `agent-browser` (the live mobile-nav + translate probes — executed this session, §1), `nextjs16-tailwind4`/`tailwind-patterns` (consulted for the mobile-nav focus — the surface re-settled clean, §1).

---

## 1. Audit inputs (this session's evidence)

- **Repo + docs truth pass:** `git pull` to `6f398bf3` clean on `main`; full reads of `AGENTS.md`, `CLAUDE.md` v2.29.0, `README.md`, `Project_Architecture_Document.md` v3.18.0, `ledgersg_SKILL.md` v2.15.0, `worklog.md`, `docs/session_54.md`, `docs/session_55.md`, the P28 plan + report, and `docs/Tailwind-V4-Validation-Report.md`.
- **The environment (live, re-probed):** rootless **PG 17** on :5432 (the dev databases loaded), **Redis** on :6379, the backend venv, `node_modules`, the dev stack (:8000 health 200, :8001 health 200, :3000 `next dev`). **No environment repair was required this session.**
- **The baseline reproduction (pre-change, this session — all gates exact):** backend `pytest --reuse-db --no-migrations -q` **1025P/0F/5S** (28.79s) · vitest **698/698 (85 files)** (107.20s) · `npx tsc --noEmit` **0 errors** · whole-tree `npx eslint . --max-warnings 5` from `apps/web` **0E/0W** · live `test:e2e:full` **43/43 (2.4m, deterministic, first run)** · `rls_smoke.py` **13/13 as `ledgersg_app`** · `mobile-nav-audit.js` **17/17** (the twenty-sixth settlement) · the dedicated Tailwind v4 `translate` probe (`scripts/translate-probe-session53.js`): **PASS** (7 mid-flight samples, closed `-100%`/hidden → open `0px`/`role="dialog"` → Escape closes). `npm audit` **0 across dev+prod**.
- **The named focus — the mobile-nav verdict (twenty-sixth settlement):** **WORKING as expected; NO remaining Tailwind v4 bug on this surface.** (Probe output this session: mid-flight count 7, `transitionProperty: "transform, translate, visibility"`.)
- **The audit (Mode C) of the P28 slice** (`446b1f36`, `641c322b`, `d86c3afa`, `dfcde539`, `93279333` — hand-verified in source this session): the four services return lazy querysets with the `select_related`/`order_by` chains carried; the four views count via `.count()`; the query-level gates + the raised whole-suite ratchet are in place — **0 new findings in the P28 slice**.
- **The test-suite standing task (user instruction: "add vitest and playwright test suite by modifying the respective config files"):** verified IN PLACE and current — `apps/web/vitest.config.ts` (jsdom, the setup file, the whole-suite + five per-glob coverage tiers) and `apps/web/playwright.config.ts` (chromium default, the live-suite serialisation contract, the E2E_API_URL gating), driving **698 vitest specs (85 files) + 43 e2e specs (11 files)**. This sprint ADDS to them (the new query-count specs, §3 T1).

**Combined findings (this session's audit): 0 Critical / 1 High / 1 Medium / 1 Low.**

## 2. Findings (verified, with evidence anchors)

### High

**BE-P29-H1 — the detail-view N+1: a detail page costs one detail PER LINE, not one detail (the registered "journal detail N+1", sized across ALL THREE detail surfaces).**
The P28 sprint closed the LIST-surface cost class (a page fetched the whole table); the DETAIL-surface sibling remains — three services fetch the row with a plain `.objects.get(...)` and the serializers walk FKs per line / per related object:

1. **`apps/invoicing/services/document_service.py:152-164`** — `get_document` returns `InvoiceDocument.objects.get(id=document_id, org_id=org_id)` with **no select_related/prefetch_related**. The `InvoiceDocumentDetailSerializer` (`apps/invoicing/serializers.py:198-229`) nests `contact = ContactListSerializer` (1 extra query), `lines = InvoiceLineSerializer(many=True)` (1 query) where **every line** walks `account.code` + `account.name` + `tax_code.code` (`serializers.py:97-99` — 2 FK queries per line). A 5-line invoice detail = **14 queries where 3 would do** (1 doc+contact, 1 lines+accounts+tax_codes, 0). **8 call sites** serialise this: the detail GET (`views.py:296`), create/PATCH/approve/send/convert/void responses, `_get_pdf_context` (`document_service.py:1091` — the PDF renders the lines too).
2. **`apps/journal/services/journal_service.py:130-143`** — `get_entry` returns `JournalEntry.objects.get(...)` plain. The `JournalEntryDetailSerializer` (`apps/journal/serializers.py:90-113`) nests `lines = JournalLineSerializer(many=True)` where every line walks `account.code` + `account.name` (`serializers.py:16-17` — 1 FK query per line), plus `get_source_document` (a conditional single `InvoiceDocument.objects.get` — bounded, not N). A 5-line entry detail = **7-8 queries where 2-3 would do**. 3 call sites (detail GET `views.py:154`, create `:129`, reversal `:185`). This is the deferred register's "the journal detail N+1" — now sized precisely.
3. **`apps/banking/services/payment_service.py:285-295`** — `PaymentService.get` returns `Payment.objects.get(...)` plain. The `PaymentSerializer` (`apps/banking/serializers/payment.py:21-22`) walks `contact.name` + `bank_account.account_name` → **2 fixed extra queries** on every serialisation (the detail GET `views.py:352-364` — which also calls `get_allocations`, a separate bounded query — plus the create/void/make/receive responses).

**Consumer sweep (verified this session):** the three service methods' consumers all serialise the related objects (detail responses, PDF context, email/send payloads) — the prefetch is used, not wasted, on the dominant paths. The two status-only consumers (`send_invoicenow` :1202, `get_invoicenow_status` :1281 via `get_document`) pay ONE extra bounded query each — accepted, documented here. **RLS note (verified):** every evaluation point runs inside the request under the tenant context — prefetching moves the queries INTO the request, never out of it. **Ordering note (verified):** the `Prefetch("lines", queryset=...select_related(...))` carries NO `order_by` — the related manager's default order is preserved, so the serialized line order (and the response bytes) cannot change.

**Fix (the P28 pattern applied at the detail seam):**
- `get_document` → `.select_related("contact").prefetch_related(Prefetch("lines", queryset=InvoiceLine.objects.select_related("account", "tax_code")))`
- `get_entry` → `.prefetch_related(Prefetch("lines", queryset=JournalLine.objects.select_related("account")))`
- `PaymentService.get` → `.select_related("contact", "bank_account")`

### Medium

**CFG-P29-M2 — the per-glob coverage ratchet drift (the same class as P28's CFG-M2: "a ratchet nobody bumps is a rubber stamp") + the missing `src/shared/**` tier.**
Measured this session (the `json-summary` aggregation over `coverage/coverage-summary.json`, weighted by covered/total counts — the same numbers the vitest per-glob thresholds gate) vs the configured floors in `apps/web/vitest.config.ts:59-110`:

| Glob | Configured (stmts/funcs/branch/lines) | Measured | Drift |
|---|---|---|---|
| `src/lib/**` | 71/52/74/73 | 73.80/54.65/78.29/75.80 | 2-4 pts |
| `src/hooks/**` | 52/47/**36**/52 | 55.89/47.34/**51.16**/55.63 | **branches 15 pts** |
| `src/app/**` | 73/64/71/73 | 75.51/65.67/73.21/76.30 | 2-3 pts |
| `src/components/**` | 82/74/68/83 | 83.28/76.24/69.27/84.34 | 1-2 pts |
| `src/providers/**` | 61/60/58/60 | 63.11/63.64/58.54/62.11 | 1-2 pts |
| `src/shared/**` | **NO TIER AT ALL** | 73.39/62.50/76.47/73.00 | ungated (whole-suite only) |

The per-glob tiers still hold their P20-measured values (set in the P20/FE-M5 + P18/CFG-L2 + P13/M-4 commits) — the P28 sprint raised only the whole-suite floor and registered this follow-up. The `src/shared/**` tier (80/109 statements — the shared money-formatting/date primitives) has never had its own gate: the P20 tier set covered lib/hooks/app/components/providers and missed it (the same blind-spot class the P20 audit itself fixed for app+providers). Fix: raise the five tiers to the measured floors and ADD the shared tier (73/62/76/73) — a REAL gate at today's level, raised over time, never lowered.

### Low

**DOC-P29-L1 — the docs truths roll forward with the sprint** (the standing DOC-L pattern): README badge/counts + the P29 milestone, CLAUDE 2.29.0 → 2.30.0, AGENTS header + the P29 lessons, SKILL 2.15.0 → 2.16.0, PAD 3.18.0 → 3.19.0, DEPLOYMENT header re-verification, the API guide (no API contract changes — the response bytes are pinned byte-identical; the re-verification noted), ci.yml counts, `.env.example`s re-verified (no new env vars expected).

## 3. The execution plan (phases, TDD)

### Phase 1 — RED: the query-count regression specs

NEW `apps/backend/tests/integration/test_detail_query_counts_p29.py` — one test class per surface, reusing the `pushdown_fx`-style fixtures (the `test_organisation`/`test_user`/`test_accounts`/`test_tax_codes`/`test_fiscal_period`/`auth_client` conventions) and `django.test.utils.CaptureQueriesContext`:

| Task | Test (RED first) |
|---|---|
| T1 | Per surface, GET the detail URL under the capture context with a document/entry carrying ≥3 lines, then assert: (a) the number of SELECT queries touching the surface's related tables (`coa"."account` for account walks, `gst"."tax_code` for tax walks, `invoicing"."contact`/`banking"."bank_account` for the payment detail) is **bounded and independent of the line count** (documents: ≤1 account-touching + ≤1 tax-code-touching SELECT — RED now: 3+ of each on a 3-line document; journal: ≤1 account-touching SELECT — RED now: 3+ on a 3-line entry; payments: ≤1 contact + ≤1 bank_account SELECT — RED now: 1 each but via per-row walks... measured RED: the queries exist as separate per-line SELECTs); (b) the response counter-pin — the detail payload carries the same line count, account codes and totals (the fix must not change the bytes). URL anchors (verified): `/api/v1/<org>/invoicing/documents/<id>/`, `/api/v1/<org>/journal/entries/<id>/`, `/api/v1/<org>/banking/payments/<id>/`. |

### Phase 2 — GREEN: the fixes

| Task | Fix | Verification |
|---|---|---|
| T2 | `document_service.get_document` gains `.select_related("contact")` + `prefetch_related(Prefetch("lines", queryset=InvoiceLine.objects.select_related("account", "tax_code")))`; the docstring records the bounded-query contract. | T1 documents GREEN · the invoicing suites green · the PDF/e2e flows green |
| T3 | `journal_service.get_entry` gains `.prefetch_related(Prefetch("lines", queryset=JournalLine.objects.select_related("account")))`. | T1 journal GREEN · the journal suites green |
| T4 | `payment_service.PaymentService.get` gains `.select_related("contact", "bank_account")`. | T1 payments GREEN · the banking suites green |
| T5 | The full backend suite — every existing pin (the P24/P25/P26/P28 envelope + query-level contracts, the service tests, the RLS gates) holds. | `pytest` **1025 passed / 0 failed / 5 skipped** (the query-count specs replace nothing; +3 new) |
| T6 | The per-glob ratchet raise: `apps/web/vitest.config.ts` — lib → 73/54/78/75, hooks → 55/47/51/55, app → 75/65/73/76, components → 83/76/69/84, providers → 63/63/58/62 (statements/functions/branches/lines), + the NEW `src/shared/**` tier at 73/62/76/73. | `npm run test:coverage` **exit 0** at the raised floors |

### Phase 3 — the full gate matrix + the screenshots

1. The complete gate set on the remediated tree: backend `pytest` **1025+3P/0F/5S** · vitest **698/698 (85 files)** · `test:coverage` green at the RAISED per-glob ratchets · `tsc` 0 · whole-tree `eslint` 0E/0W · live `test:e2e:full` **43/43** (both backends restarted on the remediated code first) · `rls_smoke` **13/13** · `mobile-nav-audit.js` **17/17** (the twenty-seventh settlement) · the `translate` probe re-PASS · `npm audit` **0** (dev+prod) · `build:server` green + `prod-csp-smoke.js` 5/5.
2. Screenshots: 8 DOM-verified captures (`docs/screenshots/184-191_*_session55.png`, md5-unique + non-blank pixel-verified, the session-53 capture conventions) — the three detail surfaces (an invoice detail with lines, a journal entry detail, a payment detail with allocations), the list surfaces, the mobile drawer closed/open, the dashboard.
3. The `.env.example` truth verification (the config-readers sweep re-run; no new env vars expected).

### Phase 4 — the docs truth pass

| Doc | Update |
|---|---|
| README.md | the badge/test arithmetic (backend 1028, e2e 43), the status-table rows, the P29 milestone section |
| CLAUDE.md | version 2.29.0 → 2.30.0, the status block, the P29 milestone block |
| AGENTS.md | the header gate row, the P29 lessons ("a detail page costs one detail per line — close the N+1 at the service seam, the same seam as the list push-down") |
| ledgersg_SKILL.md | the quick-ref numbers, version 2.15.0 → 2.16.0 |
| Project_Architecture_Document.md | the lint/test count rows, version 3.18.0 → 3.19.0 |
| docs/DEPLOYMENT.md | the header re-verification line (session 55 / P29); re-validate the fresh-host walkthrough against the current tree |
| API_CLI_Usage_Guide.md | re-verify the documented contracts against the live stack (the response bytes pinned byte-identical — no version bump; the re-verification noted) |
| .github/workflows/ci.yml | the header comment counts |
| `.env.example` ×3 | re-verified truthful (no changes expected) |

## 4. Deferred register (updated, carried forward)

**Fixed this sprint (removed from the register):** the detail-view N+1 on all three surfaces (BE-P29-H1 — subsumes the registered "journal detail N+1"); the per-glob coverage-tier drift (CFG-P29-M2 — the P28 follow-up); the `src/shared/**` tier gap.

**Still deferred (with rationale, unchanged unless noted):**
- **The `/accounts/search/` limit-contract migration** — unchanged (verified again this session: the frontend never calls the endpoint; a backend-only contract nicety).
- **The capped-default flip** — unchanged.
- **The ruff mechanical batch** (928 production findings re-measured this session; `make lint` convenience only, NOT a CI gate — the safety/bandit CI comment documents the registered debt): the 615 "mechanical" findings (W293/I001/F401) sit beside 26 F405 star-import usages that make blind `--fix` unsafe — keep deferred to a dedicated, reviewed sprint.
- **The audit-log INSERT policy** (DDL); **BE-L3 config-class locking**; **BE-L4 Peppol log-state locking**; **CSV errors[] raw strings**; **dead-letter design; UEN checksum; NULL-context SELECT tradeoff; H-05b models; PaymentsTab prefill; TanStack incompatibility; the membership-cache window; the P20-era FE-M2/M3 designs; CI hardening; the version-story reconciliation** — the P21/P23/P24/P25/P26/P27/P28 deferred registers carry forward unchanged.

## 5. Acceptance criteria

- The query-count pins (all executed): a detail request on each of the three surfaces issues a bounded, line-count-independent set of SELECTs — never a per-line FK walk; the response bytes stay identical (the existing contract suites green, the e2e 43/43).
- The backend suite green (1025+3P/0F/5S); no frontend component change; the one web config change (the per-glob ratchet) verified by `test:coverage` at the raised floors.
- `skills/` untouched by code checks; `git status` shows only the intended files.
- Plan + report saved under `docs/` in the `REMEDIATION_*_P29*` convention; the session log `docs/session_56.md`; the worklog updated.

## 6. Open decisions (resolved with judgment)

- **The detail-seam, not the view:** the fix lands in the three service `get_*` methods (the same seam P28 fixed at the list level) — uniform, tested once per service, and every serialising consumer benefits. The two status-only consumers pay one bounded extra query each (documented in §2); the alternative (per-view prefetching) duplicates the optimisation at 11 call sites and re-introduces the drift class.
- **No `order_by` on the prefetch querysets:** the related manager's default order is the current contract (pinned by the existing suites); adding one would change response bytes. The `select_related` JOINs change only the row travel.
- **The per-glob floors round DOWN to the integer below the measured value** (the P28 whole-suite convention — the ratchet sits at the floor, never above it; a rounding-up gate could red on run-to-run noise).
- **The `src/shared/**` tier is added, not deferred:** it is measured (73.39/62.50/76.47/73.00 — above every current tier floor), additive, and the same blind-spot class the P20 sprint closed for app+providers; deferring it would repeat the P28 lesson (a tier nobody adds is a tier nobody gates).
- **No new e2e spec:** the N+1 is invisible to the browser (the response bytes are the contract, already pinned by the e2e and the contract suites); the query-level truth needs the backend capture-context specs, not a UI walk (the P28 open decision, re-applied).
