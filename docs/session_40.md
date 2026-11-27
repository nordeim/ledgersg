# Session 40 — the P20 sprint log (the void/transition lock completion, the CSV transaction poisoning, the e2e first-run truth & the test-config ratchet)

The standing task cycle on a freshly-recycled workspace: the clone was
fresh (`git clone` — the sandbox had been reset), so the environment
was rebuilt from the docs: rootless PG 17 via `docs/setup_pg_z.sh`
(per `skills/rootless-postgresql`), the `ledgersg` role + both
databases, the schema v1.2.2 loaded, Redis 8 extracted rootless on
:6379, the backend venv installed, both `.env` files copied from the
verified examples, the dev stack daemonized on :8000 + :3000, and the
demo substrate bootstrapped through the public API.

The baselines reproduced exactly before any change: **backend 937P/0F/5S
· vitest 619/619 · tsc 0 · eslint 0E/0W · mobile-nav 17/17** (the tenth
live settlement of "no Tailwind v4 bug") · prod-CSP 5/5 · rls_smoke
13/13. One REAL finding surfaced during the baseline: the first full
e2e run against the fresh DB failed exactly one spec
(`banking.spec.ts:151`, "record payment settles an invoice") and the
second run passed 40/40 — a flake, root-caused by the audit below to a
spec-order dependency by construction, not timing.

Three parallel deep audits (Mode C) scoped to the P19 diff + the
deferred register → **0 Critical / 6 High / 23 Medium / 17 Low**; every
High hand-verified in source. The headline findings: `void()` recomputes
and saves the affected documents WITHOUT the document row lock (the
odd one out — allocate/unallocate both hold it; a concurrently-committed
allocation is silently lost from `amount_paid`), the CSV import loop has
no savepoint (one DB-level row error — a NUMERIC(19,4) overflow —
poisons the transaction and 500s the whole import, the per-row
`errors[]` contract never delivered), and `transition_status()` still
carries the unlocked gate + stale full-row save that P19/BE-H1 fixed
for `remove_line`. The frontend Highs: the invoice form's Notes/Terms
textareas have no accessible names, and the two icon-only back links on
/invoices/new + /quotes/new have empty accessible names. The
cross-cutting High: the first-run e2e flake (banking runs 2nd, its
helper requires a contact, the only contact-creating spec runs 7th —
red run 1 / green run 2 by construction, while DEPLOYMENT §9 documents
a fresh DB as self-bootstrapping).

The plan saved (`docs/REMEDIATION_PLAN_2026-11-27_P20.md`) and
anchor-validated, then executed TDD.

Phase 1 (backend, every fix RED first): the `void()` document locks
(sorted pre-lock; the interleaving probe pins that T2's committed
allocation survives) · the CSV savepoint + the `1E15` magnitude bound
(the poison row lands in `errors[]`, the surrounding rows import) ·
`transition_status()` locked + post-lock re-validation +
`update_fields` (the stale SENT write refused; the racing totals
survive) · the `allocate()` sorted document pre-lock · the
`create_entry` balance-cache invalidation · the Decimal import / the
positive-amount guard / the unreconcile org filter → **backend
950P/0F/5S (+13 P20 tests)**.

Phase 2 (frontend, vitest RED first): the Notes/Terms label
association · the named back links · the ContactPicker blur dismissal
(rAF-deferred, mousedown still wins) · the gst-f5-chart ARIA row ·
`formatDateOnly` with `timeZone: "UTC"` · the brand `<h1>` → `<p>` ·
the loading live regions · **the config ratchet (the owner's named
task): the coverage surface expanded to `src/app/**` +
`src/providers/**` with per-glob floors, the whole-suite floor RAISED
62/51/52/63 → 71/60/68/71, the `__tests__` helper excluded; playwright
gained `retain-on-failure` traces + the en-SG/Asia-Singapore
locale/timezone pins; `test:all` now runs the coverage** → **vitest
627/627 (73 files) and the ratchet green at the raised floor**.

Phase 3 (cross-cutting): the banking helper is contact-self-sufficient
(a fresh DB's first run is green — the flake closed at the point of
consumption) · `scripts/bootstrap_demo_substrate_session40.sh` genuinely
mirrors §9 steps 1-5 (idempotent, double-run verified) and DEPLOYMENT
§9's false self-bootstrap claim corrected · the DEPLOYMENT §3 lifecycle
parametrized to `$PG_BASE` · the stale counts refreshed in
DEPLOYMENT/AGENTS/PAD/ci.yml · the four wrong API-guide routes corrected
with errata + the metrics row · the backend `.env.example` gained the
decouple search-path caveat.

The full gate matrix, all executed green on the remediated tree:
backend **950P/0F/5S** · vitest **627/627** · tsc 0 · eslint **0E/0W** ·
coverage **green at the RAISED ratchet** · **e2e:full 40/40** ·
**rls_smoke 13/13 as `ledgersg_app`** · **mobile-nav 17/17** (the
eleventh settlement) · **prod-CSP 5/5** · build:server green.

The deliverables: 8 DOM-verified screenshots
(`docs/screenshots/120-127_*_session40.png`, md5-unique, non-blank
pixel-verified — the P20 proofs: the Notes/Terms label association, the
named back link, the combobox blur dismissal `true → false`, the
single-h1 dashboard with the brand as `<p>`, the chart's valid ARIA
row); the P20 report; this log; the worklog entry; the docs truth pass;
the conventional commits and the SSH-wrapper push to main.
