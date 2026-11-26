# LedgerSG — Remediation Report (P15 Sprint: Tree Repair, P14 Completion & the Runtime-Role Gate)

**Date:** 2026-11-26 (session 30)
**Base commit:** `4ad18d2e` (main — post-P13, post the two independent audits, post the corrupted `2bcb43f0` and the four session-log commits)
**Plan:** `docs/REMEDIATION_PLAN_2026-11-26_P15.md` (validated against the codebase before execution)
**Source inputs:** the P14 plan (`docs/REMEDIATION_PLAN_2026-11-25_P14.md` — partially executed by the interrupted session-29 then committed to WRONG PATHS), both independent audits (`docs/Code_Review_Audit_2026-11-24_independent_{1,2}.md`), the P13 report, and the two halves of `docs/session_29.md` (the P14 execution + the interrupted repair session's diagnoses).
**Method:** TDD (RED → GREEN → full gate) where implementations were missing; the committed RED P14 tests were diagnosed per-failure (implementation gap vs test-side bug — five test-side defects fixed, every one the interrupted session had diagnosed). Lint parity on touched files; conventional commits on `main`; `skills/` excluded from all checks/tests/compilation.

---

## 1. Verification Ledger (executed evidence)

| Gate | Result |
|---|---|
| Backend `pytest --reuse-db --no-migrations -q` | **834 passed, 0 failed, 5 skipped** (839 collected; 750 P13 baseline + 84 new P14/P15 tests) |
| `pytest tests/invariants -q` | **34 passed** (incl. the filed-return immutability + GST-lock + allocation-contract + F5 tie-out gates) |
| `pytest tests/security -q` | **72 passed, 3 skipped** (incl. the 3 new service-key gates + the RLS conformance + org-creation context gates) |
| `manage.py check` (testing settings) | 0 errors, 1 issue — the documented `django_ratelimit.W001` |
| **The runtime-role gate (C-1/H-7)** | `scripts/rls_smoke.py --base http://127.0.0.1:8001` against a `DB_USER=ledgersg_app` runserver: **13/13 steps green** — register → **create organisation 201 (the C-1 inversion — the audit's live 500)** → org list → contact → invoice → approve (journal posts under RLS) → bank account → payment+allocation → F5 return + compute |
| RLS live assertions (psql as `ledgersg_app`) | With org context: only the context org's rows visible (1 org, its contacts); **no context: 0 contacts, 0 journal entries (fail-closed)**; `audit.event_log` DELETE denied at the permission layer (append-only) |
| Frontend `npx tsc --noEmit` | 0 errors |
| Frontend `npx vitest run` | **532/532 passed** (61 files; 530 baseline + 2 single-flight refresh tests) |
| `npm run test:coverage` | green at both ratchets (whole-suite + `src/lib/**` per-glob) |
| `npx eslint src` | **9 findings** (the documented deferred register; no new — the F811 duplicate-serializer catch among them, fixed) |
| `npm run build:server` | green (Next 16.4.6) |
| `npm run test:e2e` (no backend) | 11 passed + 29 gated with reasons (40 specs) |
| `npm run test:e2e:full` (live stack, demo trio) | **40 passed, 0 failed, 0 skipped** |
| GST live spot-proof | `POST /gst/calculate/` 100.05 × 0.09 → `"gst_amount": "9.00"` (the P13 IRAS 2dp contract intact) |
| Mobile-nav live probe | **17/17 checks** at 375/800/1280 (toggle, closed-drawer visibility:hidden, open visible, overlay, X hit-target, transition-aware close, no overflow, no console errors, tablet/desktop sticky, the v4 space-y trap sweep clean) — **the navigation works; no TailwindCSS v4 bug exists** (the P12/P13 verdicts re-settled live) |
| Dependency audits | `pip-audit`: the upgraded set clean; `npm audit --omit=dev`: **0 vulnerabilities** (was 1 critical + 5 high + 2 moderate) |
| Screenshots | 8 new (`docs/screenshots/80-87_*_session30.png`) — pixel-verified (1280×800 / 375×812, md5-unique, content-rich) with DOM truths asserted per surface |
| Ruff parity (touched files) | 180 → 179 findings on the touched set (no new debt; 2 pre-existing cleared; the F811 dup-serializer finding fixed) |

## 2. What Was Done

### Phase 0 — the tree repair (R-0, the headline)

`2bcb43f0` ("partial p14 changes") had overwritten the real `Payment` MODEL
with the payment SERIALIZER (a circular import — `manage.py check` failed;
reproduced live at session start) and stranded four P14 modules at
`apps/backend/` root while their consumers imported the canonical paths.

- `apps/core/models/payment.py` restored from `2bcb43f0~1`
- the H-2 `ALLOCATABLE_STATUSES` fix ported into the canonical serializer
- `gst/period_lock.py` → `apps/gst/services/period_lock.py` (byte-identical)
- `gst/validators.py` → `apps/core/validators.py` with the M-form regex
  corrected to `^M\d{7,8}[A-Z]$` (both documented lengths — see §4)
- the C-1 `set_config` block ported into the canonical organisation service
- the C-2 FILED-immutability + H-05b override-reason fixes ported into the
  canonical return service (4 surgical insertions)
- the four misplaced files deleted
- five test-side defects in the never-run RED suite fixed (DRF-vs-LedgerSG
  ValidationError import; the duplicate-fiscal-year fixture; the
  state-machine-skipping approve tests; line-less posting fixtures; the
  recursing cursor spy → rewritten as a seed-wrapper probe)

### Phase 1 — the P14 completion

| # | Finding(s) | Fix | Evidence |
|---|---|---|---|
| 1 | C-2 | FILED/AMENDED returns refuse recompute — **even with `force=true`** (typed 409; corrections go through `/amend/`) | 5 RED→GREEN tests + the tie-out ordering fix (unknown-box validation precedes the reason gate) |
| 2 | H-1, H-2 | `allocate()` locks the row (`select_for_update`) and caps at the outstanding balance; the serializer's allocation-eligible set is APPROVED/SENT/PARTIALLY_PAID/OVERDUE | the committed contract tests green (over-allocation 400, VOID/DRAFT refused, the full instalment cycle → PAID) |
| 3 | H-3 | the derived GST lock (`assert_not_gst_locked`) wired into approve/void/manual-journal/payment-void | 4 RED→GREEN tests (filed-period refusals + the after-period control) |
| 4 | H-4 | credit notes REQUIRE `related_document_id` (same contact, same direction, non-VOID original, cumulative cap ≤ the original total incl. GST); the serializer + view forward it | the committed guard tests green; the P11 posting/dashboard tests updated to the linked-CN contract (8 tests) |
| 5 | H-5 | the GST-registration guard (rate>0 lines require `gst_registered` + the registration window) — already correctly placed by the interrupted session; verified green | the committed guard tests (9) green |
| 6 | H-6 + M-6a + M-7c | schema **v1.2.0 §17**: ENABLE+FORCE RLS on the six remaining tenant tables; `audit.log_change` pins `search_path = pg_catalog, audit, public`; the event log is append-only (UPDATE/DELETE refused); the Peppol-key comment is honest | the conformance tests green; both DBs patched in place; the §17c NULL-context refinement after the live smoke exposed the pre-context role read |
| 7 | C-1 + H-7 | org creation sets the RLS context before seeding; the runtime-role smoke script fixed (real UEN/GST generators, `is_bank` GL, canonical approve, `bank-accounts/` URL) | **13/13 live steps as `ledgersg_app`** + the psql isolation probes |
| 8 | M-4 | the line-item schema (bounded quantity/unit_price, required lines min 1) — merged into the EXISTING `InvoiceLineCreateSerializer` (the F811 duplicate catch); a missing `lines` key is a 400 (was KeyError 500) | 7 RED→GREEN tests |
| 9 | M-1 | honest validators wired into the org-create + GST-registration serializers + `ContactService._validate_uen`; the invalid `^\d{10}$` branch gone; both M-form lengths + the UEN form accepted | the table-driven tests (23 parametrised cases) + the serializer contract tests |
| 10 | X-1 | the shared hardened lxml parser; `_HARDENED_PARSER_FLAGS` is the introspectable policy constant | 5 tests (XXE file/URL, the entity bomb, valid-UBL control, the config gate) |
| 11 | H-05b | box overrides REQUIRE `override_reason` (≥10 chars); reason + computed-vs-filed deltas persist into notes; the wire serializer + view carry the field | 5 tests |
| 12 | H-04b | NRIC `paynow_id` masked on read (`S*****67D`); masked echoes rejected on both write paths (PDPA) | 4 tests (round-trip, echo, fresh, mobile control) |
| 13 | M-5 | the Viewer role is read-only: contact create/patch/delete + document send require `can_create_invoices` (shared module helper) | 6 tests (Viewer 403s, Manager 201, read control) |
| 14 | M-10 | `list_tax_codes` dedupes org bands over identical system bands (per code+effective_from+effective_to; history intact) | 3 RED→GREEN tests |
| 15 | H-8 | django 6.0.10, DRF 3.18.3, lxml 6.1.3, weasyprint 70.0; next 16.4.6, zod 4.6.7 + audit-fix transitives — **0 known advisories on both production sets** | full gates re-run on the upgraded tree |
| 16 | H-9 | `service.py` enforces the production key gate + env `ALLOWED_HOSTS`; the Dockerfile generates a strong per-boot key | 3 settings-gate tests |
| 17 | F-A | `ensureDemoActivity` CREATES the F5 return on a fresh DB | the live e2e bootstrap |

### Phase 2 — the live gate (F-B)

- **Single-flight refresh** (F-B a): concurrent 401s share ONE refresh call
  (the backend rotates + blacklists the refresh token; the second parallel
  refresh got 401 and its failure path killed the session with a hard
  redirect — the live suite caught it mid-run). 2 RED→GREEN vitest tests;
  the live session specs green.
- **e2e contracts** (F-B b/c/d): the p11 credit note carries
  `related_document_id`; the invoice-reuse logic requires cap headroom; the
  p10 registration uses a real ACRA UEN. **Live e2e:full 40P/0F/0S.**

## 3. Environment notes (recorded)

- The sandbox was reset: PG 17 rootless via `docs/setup_pg_z.sh`, Redis
  8.0.2 from debs, the backend venv + `npm ci` + chromium-1208 rebuilt; the
  double-fork daemonizer (`scripts/daemonize.py`) kept the dev stack
  (backend :8000, app-role backend :8001, frontend :3000) alive across tool
  calls for the live gates.
- The one live-e2e failure mid-verification was the register/login throttle
  budget across repeated runs — the documented dev procedure (flush the
  Redis window) restored it; production posture unchanged.

## 4. The M-form GST number (the researched decision)

Primary sources, both documented in the validator docstring: the OECD
"Information on TINs: Singapore" guide (Section II) gives ASGD =
`ANNNNNNNC` (9 chars — M + 7 digits + check letter), while real
IRAS-issued numbers on company statutory documents are M + 8 digits +
check letter (10 chars — e.g. `M90356174N` on FSM Global's forms,
`M90001281J` on SIA's). IRAS's own "Invoicing customers" page shows the
UEN-form example (`123456789A`). Decision: accept the union
(`^M\d{7,8}[A-Z]$` + the UEN form); format-only, no invented checksum
(the official ACRA algorithm is not published — the P16 decision).

## 5. Deferred Debt Register (explicit — nothing silently dropped)

- **UEN checksum** verification (needs the official ACRA algorithm) and
  F-form foreign-company UENs (foreign-company onboarding scope).
- **H-3 DB-trigger layer** (the derived runtime lock shipped; a
  `journal.entry` trigger is the P16 hardening item).
- **H-05b evidence model** (the notes-persisted trail shipped; a dedicated
  attachment model is the P16 design).
- Everything carried forward from the P14 plan §6 and the P13 register:
  audit1 M-2 (threshold monitor), M-3 (alert deadline), M-6b (audit
  coverage expansion), M-8 (trusted-proxy rate-limit key), M-9
  (tax-document PDF template), M-7-full (Peppol key encryption); audit2
  M-01..M-05, M-07 (maker-checker), M-08 (restore drill); B-3, B-4, B-8,
  B-9, B-12, B-15..B-19; the frontend L-batch; the 9 eslint findings
  (unchanged policies); the ruff register.

## 6. How to Verify (reproduction commands)

```bash
# backend gate
cd apps/backend && pytest --reuse-db --no-migrations -q   # 834P/0F/5S
pytest tests/invariants -q                                 # 34P
pytest tests/security -q                                   # 72P/3S

# frontend gates
cd apps/web && npm run typecheck && npm test               # 0; 532/532
npm run test:coverage && npm run build:server               # both green
npx eslint src                                             # 9 findings

# e2e (no backend) + the live gate
npm run test:e2e                                           # 11P + 29 gated
export E2E_API_URL=http://127.0.0.1:8000 \
       E2E_DEMO_EMAIL=demo@ledgersg.sg E2E_DEMO_PASSWORD=demo1234pass
npm run test:e2e:full                                      # 40P/0F/0S

# the runtime-role gate (C-1/H-7) — a second backend as ledgersg_app
DB_USER=ledgersg_app DB_PASSWORD=<its-password> python manage.py runserver :8001
python ../../scripts/rls_smoke.py --base http://127.0.0.1:8001  # 13/13

# the mobile-nav probe (17/17)
NODE_PATH=apps/web/node_modules node scripts/mobile-nav-audit.js
```

## 7. Commits

Conventional commits on `main` (see `git log 4ad18d2e..HEAD`): the tree
repair; the P14 API contracts batch; schema §17 (v1.2.0) + the §17c
refinement; the dependency upgrades; the service-key gate + Docker key +
smoke fixes; the e2e/client batch (bootstrap + contracts + single-flight);
the screenshots + probe scripts; this report + the docs truth pass + the
worklog/session. Pushed via `docs/ssh_git_wrapper_v3.py --remote
git@github.com:nordeim/ledgersg.git` with remote-ref verification.
