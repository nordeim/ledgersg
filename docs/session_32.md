# Session 32 — the P16 sprint (production truth: CSP hydration, the service-path middleware, the deferred-contract sweep)

Workspace refreshed: `git pull` to `d7f7d9b7` (the P15 tree + the session-31
log). Core docs re-read in full (AGENTS structure + P15 patterns, CLAUDE,
PAD, ledgersg_SKILL, README status sections), the session chain read
(session_29/30/31, the P14/P15 plans + reports, the worklog tail), and the
understanding validated against the tree: the environment had SURVIVED
(PG 17 with schema v1.2.0 + §17 RLS on all 25 tenant tables, Redis, the
venv, node_modules, even the session-30 dev daemons) — only the test DB
needed its role password restored to the documented dev default (an
environmental artifact of the session-30 smoke, not a code defect) and
the baselines reproduced exactly: 834P/0F/5S (invariants 34, security
72P/3S), tsc 0, vitest 532/532, eslint 9.
The audit: three parallel deep agents (backend P15-diff + services;
frontend api-client/shell/hooks/configs; cross-cutting status-claims)
plus lead hand-verification of every Critical/High in source and BUILD
ARTIFACTS. The headline: the production CSP `script-src 'self'` blocked
Next's non-nonced inline bootstrap scripts on every prerendered page —
the shipped production app could not hydrate, and no test could see it
(every suite runs against `next dev`, whose CSP allows unsafe-inline).
Two more Highs per side: service.py's from-scratch MIDDLEWARE had
dropped the tenant/audit/CSP/WhiteNoise middleware (the Docker API path
would 403 every org request); the dedicated allocate endpoint still
demanded APPROVED-only (the P14 instalment fix missed the wire
serializer); the dashboard query key was inverted (all 10 invalidations
no-ops); org creation dead-ended on a stale closure; the frontend UEN
regex rejected the LLP form the backend accepts. A display artifact was
caught and dismissed per the P10/M-11 lesson (bash ate `[h` in
`a[href]`; the Read tool showed the bytes intact).
The mobile-nav focus settled FIRST (before any code change): the 17/17
live probe at 375/800/1280 — toggle, closed-drawer visibility:hidden,
overlay, X hit-target, transition-aware close, no overflow, no console
errors, sticky tablet/desktop, the v4 space-y trap sweep clean. The
navigation works; no Tailwind v4 bug (P12/P13/P15 verdicts re-settled).
The P16 plan written and validated against every target file (the
nonce-requires-dynamic-rendering caveat found in the BUNDLED Next 16
guide — all 15 routes were static shells; force-dynamic is the
documented trade), then executed TDD:
Phase 0: `src/lib/csp.ts` (the testable builder) + `src/proxy.ts` (the
per-request nonce, request AND response headers) + force-dynamic in the
root layout + the CSP REMOVED from next.config (single source — the
P13/H-1 trap) + `scripts/prod-csp-smoke.js` (build standalone, boot,
assert nonce + hydration + zero violations). 8 builder tests + the
revised headers-config gate + **the smoke 5/5**.
Phase 1 (backend, all RED first): the middleware derivation + the
four-module settings gate; the shared ALLOCATABLE_STATUSES on the wire
serializer (+ the dead AllocationCreateSerializer deleted); the payment
row lock; NaN/Infinity rejection at money() AND both box-override seams
(+ the three FX quantize paths to money()); the line-total NUMERIC(19,4)
bound; atomic create+allocate (one service method, both views);
discount_pct forwarded; system tax-code rows read-only; the return-row
locks; the CSV bytes-once decode; the normalized-UEN write-back; the
SENT restoration on allocation release (evidence-based — the
invoicenow_sent_at case; the email residual registered); localdate();
the audit dedup (the trigger is the truth — and its INSERT→'CREATE'
vocabulary taught the test); the period_lock docstring corrected + the
advertised payment-void lock test WRITTEN. Test-side lessons en route:
the p14 fixture import, PaymentAllocation's related-name, the
FiscalYear/FiscalPeriod field names (is_closed vs is_open), the trigger
action vocabulary, the filing_due_date NOT NULL. **860P/0F/5S.**
Phase 2 (frontend, RED first): the dashboard consumes useDashboardMetrics
(the orgId-first key — one line deleted the dead hook AND fixed the
invalidations); the provider's selectOrgById (no list-state read) wired
into the create flow; the three ACRA forms mirrored in the shared schema
(+ the dead isValidUEN deleted); the open-redirect guard; the drawer
closes at the md crossing (the matchMedia-mocking lesson: stub BEFORE
render); the broadened focus trap + role=dialog/aria-modal; the dead
code swept (ClientOnly, createQueryHooks, the unused interfaces, the
QueryFunction import); the e2e serial contract in the config; the
single-flight shared-FAILURE test (the implementation was already
correct — now pinned). Two test-suite updates were contract corrections,
not deletions: the headers-config CSP tests rewritten for the
single-source architecture; the org-page test's assertion moved to
selectOrgById. **554/554, tsc 0, eslint 9 (exact parity — the immutability
probe was rewritten mutation-free to keep it).**
The docs truth pass: every stale claim fixed across CLAUDE/README/PAD/
SKILL/AGENTS/ci.yml (the counts to 860/554/1454, the five dep versions,
Redis required, the clone URL, the env table, the §4b cross-ref, the
roadmap zombie); DEPLOYMENT.md gained the §17 upgrade note (the sed
extraction verified against the schema) + the smoke step; the API guide
gained the P16 addendum + the corrected route + four documented
endpoints; the SKILL got lessons 64-69; AGENTS got the P16 patterns;
Current_Project_Status.md archived with a SUPERSEDED banner; 7 tracked
logs + 49 backup/plan files untracked per the .gitignore's intent.
The full verification gate, all executed: backend 860P/0F/5S (invariants
34, security 76P/3S) · vitest 554/554 · coverage green · eslint 9 ·
build:server green (all routes dynamic + the proxy registered) · **the
prod-CSP smoke 5/5** · e2e default 11P+29 gated · **live e2e:full
40P/0F/0S** · **rls_smoke 13/13 as ledgersg_app** (on the daemonized
app-role backend) · **mobile-nav 17/17 on the remediated tree** · 8
screenshots (88-95_session32, DOM-verified incl. the new role=dialog
truth, md5-unique).
Conventional commits on main; the hygiene sweep; the SSH push via the
wrapper (paramiko shim, binary-mode bridge — the session-31 lesson);
key shredded after push.
