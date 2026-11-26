Session 30 — the P15 sprint (tree repair, P14 completion, the runtime-role gate).
Workspace reset again: fresh clone of main at 4ad18d2e, all docs re-read
(AGENTS, CLAUDE, README, PAD, ledgersg_SKILL, session_28/29, both independent
audits, the P13 report, the P14 plan, partial_p14_remediation_changes.txt).
The damage map: 2bcb43f0 destroyed the Payment model (serializer code in the
models package — circular import, manage.py check fails), four P14 modules
stranded at wrong paths, the P14 tests RED at the correct location. The
interrupted repair session's narrative (session_29's second half) confirmed
the diagnoses but committed nothing.
Environment rebuilt: PG 17 rootless via setup_pg_z.sh (ledgersg SUPERUSER +
both DBs, schema v1.1.0 loaded), Redis 8 from debs, venv + npm ci +
chromium-1208. Frontend baseline green (tsc 0, vitest 530/530, eslint 9);
backend could not boot — the corruption reproduced live.
The P15 plan written and validated against every target file (the misplaced
vs canonical diffs; the committed tests' import expectations; the M-form
question researched: OECD TIN guide ANNNNNNNC 9-char vs real-world 10-char
M90356174N — accept both).
Phase 0 executed: Payment model restored from 2bcb43f0~1; the H-2 serializer
fix ported; period_lock moved; validators moved with the M-form regex fix;
the C-1 set_config block and the C-2/H-05b fix blocks ported into the
canonical services; the misplaced files deleted; five test-side bugs in the
never-run RED suite fixed (the ValidationError import, the duplicate
fiscal-year fixture, the state-machine approve tests, the line-less posting
fixtures, the recursing cursor spy rewritten as a seed-wrapper probe).
Phase 1 executed: the f5 tie-out ordering fix (box names before the reason
gate); M-4's line schema MERGED into the existing InvoiceLineCreateSerializer
(F811 caught my duplicate — the second definition would have silently won);
M-1 wired into the org + GST-registration + contact serializers (the fixtures
with invalid M-form numbers fixed to real formats); M-5's viewer gates (the
shared require_permission helper + the org fixture's CoA seed); M-10's band
dedupe (RED first); H-04b masking + masked-echo rejection; H-05b's
override_reason through the serializer + view; X-1's hardened parser with the
policy-constant design (lxml flags are write-only); schema §17 written
(v1.2.0) and applied to both DBs — the conformance tests green after the
sweep-intersection + proconfig-normalization fixes.
H-8: django 6.0.10, DRF 3.18.3, lxml 6.1.3, weasyprint 70 (pyproject updated
through the manager); next 16.4.6 + zod 4.6.7 + the audit-fix transitives —
npm audit 0 vulnerabilities; the npm audit fix --omit=dev dev-tree-pruning
trap hit and reversed (plain npm install restores vitest/playwright).
H-9: the service.py key gate + env ALLOWED_HOSTS (the reload base-then-service
ordering lesson) + the Dockerfile's strong per-boot key.
The dev stack daemonized (backend :8000, app-role backend :8001, frontend
:3000). The live runtime-role gate: rls_smoke 403'd on contact creation —
§17c's org-scoped-only role policy hid the Owner role from the middleware's
PRE-CONTEXT role attach; the NULL-context role SELECT is the documented
tradeoff. After the refinement + the smoke's URL/generator fixes:
13/13 steps green as ledgersg_app — org creation 201 (the C-1 inversion
proven live). The psql isolation probes: with context only the context org's
rows; no context zero rows (fail-closed); the audit log append-only.
F-A + F-B: the e2e bootstrap creates the F5 return; the p11 CN carries
related_document_id with cap-headroom invoice reuse; the p10 real-ACRA UEN;
the single-flight refresh (RED first — my mock's call-numbering was wrong,
the debug trace proved the fix worked, the test rewritten).
The full verification gate: backend 834P/0F/5S (invariants 34P, security
72P/3S), vitest 532/532, coverage green at both ratchets, tsc 0, eslint 9,
build:server green, e2e default 11P+29 gated, live e2e:full 40P/0F/0S (one
mid-run throttle artifact — the documented Redis flush restored it), the GST
live proof 9.00, the mobile-nav probe 17/17 (the login-page aside fix + the
transition-aware close wait), 8 screenshots captured + verified.
The docs truth pass: DEPLOYMENT.md (the P15 revision, v1.2.0, the §7 counts,
the rls_smoke verification step in §12.3), the API guide v2.7.0 (the P14/P15
contract addendum), README (badge 1406, the P15 milestone), CLAUDE 2.18.0,
PAD 3.10.0 (the honest RLS claim), AGENTS (the P15 patterns), ledgersg_SKILL
2.4.0 (lessons 59-63). The P15 report + this session log + the worklog.
9 conventional commits on main; hygiene gate; the SSH push via the wrapper.
