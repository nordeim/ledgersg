# LedgerSG — Remediation Report (P11 Sprint: Accounting Truth & Config Honesty)

**Date:** 2026-11-23 (session 23 — continued across a context outage; session 22
carries the raw in-flight log of the first half)
**Base commit:** `1b3e267d` (main — post-P10)
**Plan:** `docs/REMEDIATION_PLAN_2026-11-23_P11.md`
**Source audit:** post-P10 audit re-verified in source with line numbers before
planning (scanner pass per `skills/skills-catalog.md` — all hits in the
documented FP classes — plus three parallel deep-audit agents); every
Critical/High finding hand-verified against the working tree, with two
runtime reproductions (the production cache-backend boot crash; the
`DEBUG=true, DEBUG_TOOLBAR=false` startup ImportError) before execution.
The live API gate then exercised the full accounting path end to end against
the running servers, and the live e2e phase surfaced two more infrastructure
truths (the register throttle literal; the consumed-fixture re-run class).
**Method:** TDD (RED → GREEN → full gate). Every production-code fix has a
regression test that failed for the documented reason before the fix and
passes after.
**Session incidents (recovered, zero loss):** the first half of the sprint
was cut by a context-window outage mid-Task-1 (the workspace, databases,
Redis, dev servers and the saved plan all persisted; the in-flight test
fixture patch was completed on resume). All code commits were made on
resume; nothing was pushed before the final gate.

---

## 1. Verification Ledger (executed evidence)

| Gate | Result |
|---|---|
| Backend `pytest --reuse-db --no-migrations -q` | **735 passed, 0 failed, 5 skipped** (687 P10 baseline + 48 new) |
| `pytest tests/invariants -q` | 27 passed (schema conformance + capacity + balance) |
| `pytest tests/security -q` | 66 passed, 3 skipped (RLS, tokens, cookies, posture gates — +11 including the register-knob posture tests) |
| Frontend `npx tsc --noEmit` | 0 errors |
| Frontend `npx vitest run` | **511/511 passed** (505 P10 baseline + 6 new) |
| `npm run test:coverage` | green at the honest measured-floor ratchet |
| `npm run build:server` | green — the only build mode |
| `npm run test:e2e` (no backend) | **11 passed, 23 gated with reasons** |
| `npm run test:e2e:full` (live stack) | **33 passed, 1 data-conditional skip, 0 failed** (34 specs: 11 always + 23 backend-gated — the 3 new P11 specs included) |
| Live API accounting gate | login → contact PATCH (gst_reg_number persists) → invoice DRAFT→APPROVED (journal posted) → credit note APPROVED (REVERSED journal) → F5 computed (boxes net credit notes) → dashboard `gst_payable = 315.0000` matching F5 Box 8 |
| Screenshots | 7 new (59–65_session23), content-verified (pixel-ratio + DOM-truth assertions per surface) |
| Production posture gates | base `REGISTER_RATELIMIT_IP` stays 5/hour (asserted); base login/refresh knobs unchanged (asserted) |
| CI YAML | parses; coverage step present; no dead steps; no `|| true` on safety |

## 2. What Was Fixed

### The planned register (Tasks 1–15)

| # | Finding | Fix | Evidence |
|---|---|---|---|
| C-1 | Credit notes posted INVOICE-direction GL entries — a credit note DEBITED the customer's AR (books overstated receivables on every credit note since the posting engine shipped) | `journal_service.post_invoice` flips line direction by document type (credit notes credit AR, debit revenue/GST) | 8 integration tests (RED: 5 for the documented reasons) + the live-gate ledger proof (entry 4: AR credit 817.50 / revenue debit 750 / GST debit 67.50) |
| C-2 | Production settings crashed at first cache touch — `django_redis` is a dev extra, never in the production dependency set; plus LOGGING mutated the shared base dict | Builtin `RedisCache`; copy-on-write LOGGING; `LOG_DIR` env knob with the file-handler path derived from it | Settings-gate tests (RED: import + cache round-trip failed) + the live boot reproduction (previously: `ModuleNotFoundError` → now: boots and round-trips) |
| H-1 + M-3/M-4 | The contacts edit dialog prefilled from the LIST row serializer — uen/peppol_id/address/gst_reg_number rendered blank and an unconditional save ERASED the stored values with a success toast (Peppol ID loss breaks InvoiceNow); `gst_reg_number` was undeclared in the update serializer (DRF silently dropped it); the search re-fired per keystroke | Prefill from the DETAIL endpoint (banking-dialog remount pattern); `gst_reg_number` declared on `ContactUpdateSerializer`; the list hook debounces | 9 vitest + 4 backend + the e2e round-trip spec (open → prefill → save → API re-read: uen/gst_reg_number/peppol_id persist) |
| H-2 + M-1 + M-11 | The F5 boxes panel read idealized `box1` keys the backend never sends — every box rendered "—"; the deadlines endpoint's envelope was read wrong; REVIEWED returns were filtered out of the deadline computation | `F5_BOX_LABELS` pasted from the real serializer keys; the deadlines reader consumes the real envelope; the REVIEWED filter includes reviewed returns | Backend deadlines tests + 10 reports vitest (RED re-verified by component revert) + the e2e F5 spec (a monetary value renders) |
| H-3 | The F5 computation counted non-posted documents (quotes are not supplies) and ignored credit notes (they must net) | Posting-type filter + credit-note netting in `calculation_service` | The credit-note integration tests + live: Box 1 = 3500.00 with 750.00 credit notes netting, Box 6 = 315.00 |
| H-4 + M-7 + L-2 | The dashboard GST payable was hardcoded to 0.00; the revenue chart fed `parseFloat("SGD x.xx")` → NaN → 0; six "S$ SGD" double prefixes | `calculate_gst_liability` re-sourced from document lines (delegates to the F5 computation — single statutory truth); the chart takes the raw value; single currency prefixes | Backend + 6 vitest (RED for the documented reasons) + the e2e dashboard spec |
| H-5 | `config/urls.py` gated debug_toolbar on `DEBUG` while INSTALLED_APPS gated on `DEBUG_TOOLBAR` — `DEBUG=true, DEBUG_TOOLBAR=false` crashed startup (ImportError) | One gate: INSTALLED_APPS is the single knob; urls.py derives from the registry | Settings-gate tests + the live reproduction (previously: RuntimeError at boot → now: serves) |
| M-2 | Bank-account PATCH without an id in the path raised 500 | The view resolves the id from the path (404 on missing) | Backend test (RED: 500) |
| M-5 | The organisation PATCH accepted anything (no serializer) — garbage `entity_type`/`base_currency` hit the model raw; the settings PATCH passed no instance | Typed `OrganisationDetailUpdateSerializer` (choice fields, tz length, GST consistency) + instance binding on both PATCH paths | 9 backend tests (RED: 500s) |
| M-6 | Garbage path UUIDs (`/documents/not-a-uuid/`) raised `ValueError` 500s inside view bodies | `<uuid:>` converters at the routing layer across the four url modules; views unwrap the UUID objects (no double-wrap) | The sweep test (RED: the documented 500s) |
| M-8 | The audit trigger's INSERT never read the middleware's `app.client_ip/user_agent/request_path` (NULL on every row); LOGIN/LOGOUT in the CHECK vocabulary but never emitted | The trigger reads the variables; the auth views emit LOGIN/LOGOUT; the model column nullability aligned | Trigger + emission tests (RED); the schema function reloaded into both local DBs |
| M-9..M-14 + L-7 | CI never ran coverage (the "tests pass" step was misleading), carried dead steps, and `dev`-flagged steps ran on every PR; devDependencies sat in the production dependency list; `uv.lock` untracked-by-convention; Makefile lies | Coverage step added, dead steps removed, `npm ci` install split devDeps, `.gitignore` + Makefile truth | CI YAML parses; `npm ci` + coverage + build all green locally through the validation chain |
| H-6 + H-7 + M-12 | The backend Dockerfile pip-installed unpinned at build and had no CMD (the container slept); compose passed credentials the images never see; migrate ran at boot (migrations are permanently disabled here) | Pinned installs, gunicorn CMD, compose credential wiring, migrate removed | Static validation (files linted against the repo's own contracts); no image built in this environment — DEPLOYMENT.md marks it accordingly |
| M-15 | The production CSP carried `unsafe-eval`/`unsafe-inline` unconditionally | unsafe-* dev-only; `connect-src` derives from `NEXT_PUBLIC_API_URL` | next.config.ts + the documented posture |
| M-16 + L-5 | Tracked log files, a broken symlink and stale root scripts | Removed (no code references; GEMINI.md kept — a real SSOT doc) | Gates green after removal |
| L-1/L-3/L-4/L-6/L-9 | Row actions ignored permissions (client-side); `date.today()` at 10 sites (UTC containers); the ledger hid one side of reversal pairs; a dead ValidationError branch; the UEN TOCTOU window | `hasPermission` gates on contacts/banking/reports actions; `timezone.localdate()`; the reversal filter dropped; the dead branch removed; IntegrityError → the same clean 400 | Full-suite green + targeted tests; eslint parity maintained |

### The live gate's own findings (Tasks 16–19 — found by running the product)

| Finding | Fix | Evidence |
|---|---|---|
| The register throttle was a hardcoded `5/hour` decorator literal — the 6th `test:e2e:full` run against the same dev server 429'd the self-serve spec (stuck on /register) | The P4/P6 knob pattern: `config.ratelimits.register_ip` + `REGISTER_RATELIMIT_IP` (base 5/hour unchanged, dev 120/hour) | 3 settings-gate tests (RED) + e2e:full green afterwards |
| The banking payment spec consumed its own fixture (the previous run settled the bootstrap-approved invoice) — re-runs starved on a consumed fixture | `ensureOutstandingInvoice`: the spec creates its own invoice per run (unique reference, DRAFT→APPROVED) | e2e:full green on re-run |
| The p10 contacts spec's row regex depended on era-specific fixture names | Generalized: any real row in `contacts-list` (or the truthful empty state) | e2e:full green |
| The failed-login audit test asserted NO LOGIN rows anywhere — the live gate's legitimate demo-user logins into the SHARED dev DB broke it | Scoped to the failing user (matching the positive test's contract) | Full suite green |
| The dev servers spawned within a tool call die at call end (sandbox process cleanup) — the backend "vanished" between steps | The e2e/boot runs start the backend and run the suite in ONE call; documented | e2e:full 33P/1S/0F |

### The live API accounting gate (executed against the running servers)

Login (demo user) → contact PATCH with the truthful full profile
(`gst_reg_number` M90333391K / uen T08LL1234A / peppol 0195:T08LL1234A all
persist — the M-4 proof) → invoice INV-00002 DRAFT→APPROVED (journal posted)
→ credit note CN-00002 APPROVED (**reversed** journal: AR credit 817.50,
revenue debit 750.00, GST debit 67.50 — the C-1 proof) → F5 computed
(Box 1 = 3500.00 net of the credit notes, Box 6 = 315.00 — the H-3 proof) →
dashboard `gst_payable = 315.0000` matching F5 Box 8 (the H-4 proof).
Seven screenshots captured through the real UI
(`docs/screenshots/59-65_*_session23.png`), verified at pixel level
(non-blank, content-rich) and at DOM level (the P11-critical text asserted
per surface: "SGD 315.00", the box labels, the prefilled dialog values, the
CN journal row).

## 3. Deferred Debt Register (explicit — nothing silently dropped)

- The pre-existing frontend eslint register (47 `no-explicit-any` class
  findings) — parity maintained, no new errors introduced.
- The blank-vs-NULL `organisation.uen` modeling decision (P10's registered
  debt, unchanged).
- The Docker path: statically validated only — no image built/booted in this
  environment (DEPLOYMENT.md marks it).
- The two tracked local dev `.env` files inherited from early repo history
  (unchanged; `.env.example` re-audited 1:1 this sprint).
- Unallocated credit notes do not reduce the document-based outstanding
  receivables figure (they net in the ledger and F5; allocation-based
  settlement of receivables remains the P5 allocation model).

## 4. How to Verify (reproduction commands)

```bash
# backend gate
cd apps/backend && pytest --reuse-db --no-migrations -q      # 735P/0F/5S
pytest tests/security -q                                     # 66P/3S

# frontend gates
cd apps/web && npm run typecheck && npm test                 # 0 errors; 511/511
npm run test:coverage && npm run build:server                # green; green

# e2e (no backend) + live gate
npm run test:e2e                                             # 11P + 23 gated
# with the dev stack up and bootstrapped (DEPLOYMENT.md §9):
npm run test:e2e:full                                        # 33P/1S/0F

# production settings boot (C-2)
DJANGO_SETTINGS_MODULE=config.settings.production SECRET_KEY=x LOG_DIR=/tmp \
  python -c "import django; django.setup(); from django.core.cache import cache; cache.set('k','v'); print(cache.get('k'))"

# the credit-note reversal (C-1) — approve an invoice and a credit note, then:
psql ... -c "SELECT entry_number, source_type, a.code, l.debit, l.credit
FROM journal.entry e JOIN journal.line l ON l.entry_id=e.id
JOIN coa.account a ON a.id=l.account_id ORDER BY e.created_at DESC, l.line_number;"
```

## 5. Commits

Conventional commits on `main`, 17 total this sprint (Tasks 1–15 code
commits, the live-gate commit, the screenshots commit, the docs commit, the
worklog commit), pushed via `docs/ssh_git_wrapper_v3.py` with remote-ref
verification. See `git log 1b3e267d..HEAD` for the full set.
