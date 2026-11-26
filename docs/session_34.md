# Session 34 — the P17 sprint (2026-11-27)

The raw session log. Executed across two context windows (the sprint was
planned and half-executed in the first; the second window completed
Phase 2, the docs truth pass, the live gates, the screenshots and the
push — the workspace, PG, Redis, the double-forked dev stack and the plan
all persisted across the outage, zero loss).

## Window 1 — the environment, the audit, the plan, Phase 1, most of Phase 2

The workspace had been reset. Cloning the repo fresh (main, clean at
`e9b2626d`). The five core docs digested (AGENTS/CLAUDE/README/PAD/SKILL)
via parallel Explore agents; the recent session docs read directly
(session_31/32/33, the P16 plan + report, the worklog tail).

The session_29 `payment.py`/serializer regression check via git history:
the P15 tree repair reverted the corrupted `2bcb43f0` overwrite, the
Payment model intact, `ALLOCATABLE_STATUSES` present in both the wire
serializer and the allocate endpoint — no surviving regression; the P16
header claims matched the tree.

Environment rebuilt from scratch: PostgreSQL 17 rootless via
`docs/setup_pg_z.sh`, both databases created + schema-loaded (v1.2.0),
`ledgersg_app` at the documented dev password, Redis 8 rootless, backend
venv + web node_modules installed. Every documented baseline reproduced
green: backend **860P/0F/5S** (invariants 34P, security 76P/3S), vitest
554/554, tsc 0, `eslint src` 9 (the whole-tree 11 delta = the `e2e/` pair).

The dev stack started (double-fork daemons) + Playwright chromium
installed. The mobile-nav live probe: **17/17 PASS at 375/800/1280** —
no TailwindCSS v4 bug (settled live on the fresh clone, consistent with
P12/P13/P15/P16). The demo bootstrap through the documented §9 path
surfaced a real docs defect: the DEPLOYMENT.md GST example
`M90345678` fails the P15 honest validator (missing the check letter) —
registered as DOC-H1.

Three parallel deep audits (backend concurrency/contracts, frontend
tokens/hooks/shell/env, cross-cutting docs truth) + lead hand-verification
of every Critical/High in source. The P17 plan written and validated
against the tree: `docs/REMEDIATION_PLAN_2026-11-27_P17.md`.

Phase 1 executed TDD (each: RED → GREEN → suite): the double-reversal
guard + row lock (BE-H1), the double-void row lock (BE-H2), the Celery
tenant context + on-commit dispatch via the new `common/tenant_context.py`
(BE-H3, with a real RLS-enforced probe as `ledgersg_app` after a vacuous
first test was caught — the test connection ran as superuser), the
400-contract sweep (BE-M1/M2/M3/M5/M6/L2), the settings gates (BE-L3/L4),
the 6-dp exchange rate (BE-L1), the query-count-gated `select_related`
batch (BE-M7), the negative-membership cache fix (BE-M4). The schema
gained §15c (the Django framework tables — the fresh-host pytest
transactional-teardown gap) and the version bumped to v1.2.1.
**Backend 882P/0F/5S.**

Phase 2 executed TDD: the `--color-success` token + design-token gates
(FE-M1), the proxy nonce orchestration tests (FE-M3), the dead CSP
origins (FE-L1), the unsaved-changes guard hook (FE-M4), the redirect
carry (FE-L5), the shared `uenSchema` across all three surfaces (FE-L6),
the six lint errors cleared to whole-tree 0 errors / 5 parity warnings
(FE-M2), the dead-utility sweep (FE-L2). **vitest 576/576.**

## Window 2 — completion: FE-L3/L4, the gates, the docs truth pass, the live gates, the shots, the push

Resuming: workspace intact, all P17 changes uncommitted on main; the
double-forked stack still alive (PG, Redis, runserver, next dev). FE-L2
verified complete. FE-L3 executed: `useComplianceAlerts` and `useCurrentOrg`
were already deleted; the invoice-store slimmed to exactly the
`hasUnsavedChanges` contract (tsc 0). FE-L4 executed RED → GREEN: the
org-selector as a real Radix-contract menu (aria state, `menuitemradio`,
Escape/outside-click, arrow-key roving with wrap, focus return) —
6/6 tests, the mobile-nav suite untouched (18/18 in the layout family).

The backend restarted on the remediated code. The suite runner
investigation: `manage.py test` prompts against the dev DB (wrong runner
+ the `DB_NAME` override documented) — the canonical `pytest
--reuse-db --no-migrations` with `DB_NAME=test_ledgersg_dev` runs green
in 19s: **882P/0F/5S**. vitest full: **582/582** (69 files). eslint whole
tree: **0 errors / 5 warnings** (two self-introduced warnings fixed — the
unused import + the unused selector). `build:server` green.

Phase 3 — the docs truth pass: DEPLOYMENT.md (header, §4 counts + the
§15c upgrade path, §7 counts + the runner note, §9 GST `M9034567K` +
`related_document_id` + vitest 582, §11 token/`ORG_ID`/Bearer flow, §13
v1.2.1); README (badge 1504, status table, P16+P17 milestone blocks,
env tables, dead refs, issues URL, footer, the dashboard endpoint in the
diagram); AGENTS/CLAUDE/PAD/SKILL normalized to P17 (the SKILL's false
env-tracking claim inverted; the PAD's absolute path retired); the API
guide P17 addendum + v2.8.0; the LICENSE (AGPL-3.0, structure-verified);
ci.yml (DATABASE_URL no-op removed + the lint gate at `--max-warnings 5`);
the tracked `database_connection_status.txt` untracked; the three
repo-root scripts given the self-resolving playwright require; the root +
web `.env.example` reader maps corrected.

Phase 4 — the live gates, all green on the remediated tree: the demo
bootstrap through the **fixed** §9 flow (register 201, org 201 with
`M9034567K` — DOC-H1 validated live); e2e default **11P/29 skip**;
e2e:full **40/40** (the first fresh-DB run self-bootstraps — one
interaction, then 40/40 on the consecutive run); the §11 checklist
commands executed verbatim (200/400/200/200/200/200); **rls_smoke 13/13
as `ledgersg_app`**; **mobile-nav 17/17**; **prod-CSP smoke 5/5**.

The screenshots: `scripts/capture-screenshots-session34.js` — 8
DOM-verified, md5-unique captures (`docs/screenshots/96-103_*_session34.png`)
including the two P17 surfaces: the open org-selector menu
(`role="menu"` + `menuitemradio` + `aria-expanded`) and the Payments tab
showing **2 live `text-success` elements** (the FE-M1 token — pre-P17
those classes compiled to no CSS). Pixel-sanity verified (99%+ non-white,
the Illuminated-Carbon dark shell).

The P17 report (`docs/REMEDIATION_2026-11-27_P17_REPORT.md`), this log,
and the worklog entry written; the conventional commits made on `main`
and pushed via `docs/ssh_git_wrapper_v3.py` with remote-ref verification.
