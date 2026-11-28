I'll start by setting up the workspace and understanding the project. Let me begin with checking the current state and cloning the repository.
Repo cloned. This is a large, complex task. Let me set up a comprehensive TODO list first:
Now let me review the project structure and core documentation. The docs are large, so I'll read them systematically:
Now let me check the current worklog tail and git state to understand where things stand:
P37 已交付。现在让我查看核心文档。由于文档篇幅较大，我将有策略地阅读其中的关键部分：
Core docs reviewed. Now let me check the skills catalog and set up the environment:
Now let me check the environment state (PG/Redis/venv/node_modules):
Environment fully reset — PG, Redis, venv, node_modules all need provisioning. Let me start with PostgreSQL:
PG 17 is running. Now create the ledgersg roles/databases and load the schema:
The 45-table count refers to the test DB after pytest fixtures; dev DB has 37 — consistent with historical plans (37/45). Now Redis:
Redis 8 running. Now the backend venv:
Backend venv 已准备就绪 (Django 6.0.10)。接下来安装 web `node_modules`：
Environment is provisioned. Now let me check backend env config and run the baseline backend suite:
Now let me run the backend baseline test suite to confirm the state:
Backend baseline reproduced exactly: **1134P/0F/5S** — matches the P37 documented state. Now the web static gates:
All static gates green. Now backend lint truth:
Lint truth verified: production 148 / tests 73 exact — matches documented state. Now let me check the dev server startup conventions and the live-gate scripts:
Now start the full dev stack with tool-call survival (the repo's daemonize approach):
Dev stack is live (8000: 401, 8001: 401, 3000: 307 — all expected). Now bootstrap the demo substrate:
RLS smoke: **13/13 green**. Now the named focus — the mobile navigation menu audit:
Mobile nav: **17/17 passed** (44th settlement) + translate probe **PASS** — no Tailwind v4 bug. Now the full live e2e suite:
**e2e:full 43/43 passed.** Let me complete the gate matrix with npm audit, build:server and prod-CSP smoke:
Test suite configs verified in place. Now build:server + prod-CSP smoke:
**Complete baseline gate matrix verified — all gates match the documented P37 state exactly.** Let me update the todos and start the audit phase:
Now the audit phase. First, let me review the P37 diff (the recent code changes):
The generator's P37 slice is well-formed. Let me verify the XSD element ordering matches the generator emission order:
The P37 slice audits clean. Let me examine the mobile nav component itself (the named focus) and the Tailwind-V4 report:
Mobile nav verified working (44th settlement). Now let me hunt for fresh audit findings — probing the transmission service path and other presentation layers:
Potential finding at line 175 — the invoice fetch is not org-scoped. Let me check the calling view and how other services scope:
A potential finding emerges: `send_invoicenow` refuses credit notes, yet P34-P37 built the full credit-note transmission pipeline. Let me check the auto-transmit path:
This looks like a significant finding — the credit-note transmission pipeline (P34-P37) may be unreachable. Let me verify against the deferred register and test files:
The P34 plan fixed the pipeline dispatch but never revisited the workflow gates. Let me check the frontend surface and the auto-transmit path to complete the evidence:
**Finding confirmed at three layers**: the UI shows "Send via InvoiceNow" for APPROVED credit notes, but the backend refuses them. Let me reproduce it live on the demo stack:
**H1 finding fully reproduced live.** Let me continue the audit sweep — I noticed a suspicious `ln:` naming in the api-client earlier. Let me check:
The api-client is clean (earlier match was a substring false-alarm). Let me audit the new P37 specs for quality:
Found a second finding: the P37 spec hardcodes an absolute sandbox path while P35/P36 use relative paths. Let me check the PDF spec too:
Only one file affected. Now let me check the docs the user asked me to validate (DEPLOYMENT.md, API_CLI_Usage_Guide.md) for alignment with the current state:
The API guide is changelog-style with addenda — clear update path. Let me finish the audit with the send-invoicenow view permission check (P9 hinted at it):
View layer is clean. Let me consult the repo's code-review and TDD skills per the user's instruction before finalizing the plan:
Let me review the auto-transmit internals before writing the plan:
The audit is complete. Let me check the session log numbering convention before writing the plan:
Now let me study the test conventions for the wiring specs before writing the plan:
I have all the audit evidence needed. Now let me write the comprehensive P38 remediation plan:
Fixing a garbled line in the plan:
Plan saved. Now **Phase 0: validate the plan against the codebase** — checking for any existing tests that pin the current refusal behavior:
Two refusal sites found. Let me examine the second one (the email gate at line 1165):
A sibling surface with the same defect class — the email gate. Let me check the UI affordance and test coverage for it:
The email gate is a sibling surface but the UI doesn't advertise it — no broken promise. I'll register it as a new deferred item and keep the sprint focused. Updating the plan:
Continuing plan validation — checking remaining tests that could break:
All existing tests are compatible with the plan. Let me verify the fixtures my new spec will need:
Fixtures verified. **Plan validated against the codebase — aligned.** Now executing Phase 1 (TDD RED) — writing the new spec:
Now run the spec — expecting the RED gates to fail for exactly the right reason:
RED confirmed for gates (i)/(ii). The approval test needs the org's Chart of Accounts (the P14 posting requirement) — let me check how sibling specs set it up:
The approval test needs a service-created document with real lines. Let me fix the spec's fixture:
**Phase 1 RED complete** — all 3 headline gates fail for exactly the right reasons (the "Only SALES_INVOICE" refusal; no log row on approval). The draft/peppol/config controls will green when the type gate widens (gate ordering). Now **Phase 2 GREEN** — the fixes:
Now the L1 fix — the P37 spec's absolute path:
**GREEN — all 19 gates pass.** Now the full backend suite (T5):
These 2 failures are environmental (the `ledgersg_app` role's password), not from my change. Let me check what password these RLS tests expect:
The tests rely on the schema's documented dev default password. Let me restore it and restart the :8001 RLS instance accordingly:
**Backend suite: 1143P/0F/5S — exactly +9.** Now verify lint truth:
Lint truth exact (148/73, mechanical exit 0). Now Phase 3 — restart the dev backend on remediated code and run the live gates:
**Full gate matrix green.** Now the live contract re-verification — the CN-00001 probe on remediated code:
The type gate now passes (the error moved to the config gate). The demo org lacks Peppol settings — let me check `is_configured` and configure it for the live proof:
The Redis daemon died between tool calls (the documented sandbox behavior). Let me restart it via the repo's daemonizer:
Redis is alive — the refusal is likely IPv6 `localhost` (::1) vs my IPv4-only bind. Let me verify:
`localhost` resolves to ::1 but Redis binds only IPv4. Rebind Redis to both loopbacks:
The transport is **pyamqp (RabbitMQ)** — the server never picked up the Redis broker/eager config. Let me check the celery app config:
**Root cause found — a real codebase bug**: `config/__init__.py` never imports the Celery app, so `@shared_task` binds to Celery's default app (amqp://localhost:5672, eager=False) in web processes. Let me verify:
The bug is proven. But the test suite passes — something imports config.celery under pytest. Let me find what:
No file in the backend imports config.celery — the wiring bug is total in web processes. Let me check how the docs start the worker (the `-A config` resolution):
The worker finds `config.celery.app` via Celery's `-A` fallback, but the **web process (gunicorn/wsgi) never imports it** — the canonical Celery+Django wiring bug. This is a second HIGH finding. Let me read the task body to understand the eager-mode impact of the fix:
Testing settings confirmed. This live-verification discovery is exactly what Phase 3 is for. Let me update the plan with the new H2 finding:
Now update the plan's findings, tasks, and acceptance criteria sections for H2:
Plan updated. Now write the T1b RED spec for the Celery wiring:
**T1b RED confirmed** — the default app with `broker_url: None` and eager=False. Now the T2b fix:
**Backend suite: 1146P/0F/5S — exactly +12.** Restart the backend and re-run the live contract verification:
**Live contract re-verification PASSES: 200/QUEUED with a real log id** (the log shows FAILED — the eager inline run against the demo's unreachable Storecove endpoint, the registered unverifiable adapter item). Now re-run all live gates on the fully remediated tree:
`make lint-mechanical` failed — let me get the details:
All gates green. Now npm audit + the screenshots. Let me check the session-72 capture script convention:
Now let me write the session-74 capture script (256-263), featuring the P38 surface — the credit-note detail page:
The credit note isn't on page 1. Let me make the capture deterministic — resolve the credit note id via the API first, then navigate directly:
All 8 captures OK. Now the pixel-verification script (the session convention):
All pixel-verified. Let me visually confirm the P38 feature capture — the credit note detail page:
The P38 feature surface confirmed: **"Send via InvoiceNow" renders on the APPROVED credit note** — now honest post-P38. Now Phase 4 — the docs truth pass. Starting with README:
Now updating README (badge, status rows, P38 milestone):
Now the README test-count rows further down:
README done. Now CLAUDE.md:
Now insert the P38 milestone block into CLAUDE.md:
CLAUDE.md done. Now AGENTS.md — the header gate row + the P38 lesson:
Now ledgersg_SKILL.md:
Now the Project_Architecture_Document.md:
PAD done. Now DEPLOYMENT.md — this session provisioned the environment from scratch through the guide's own steps (a real verification):
Let me verify §5 (Redis) and §10 (Celery) for drift against what I actually did:
Found drift in §7 (stale count). Updating §7 and §10:
Now API_CLI_Usage_Guide.md — version bump + the P38 addendum:
Now add the P38 addendum after the P37 one:
Let me check the CI workflow for header counts:
Now the worklog entry — let me check its structure:
Now the P38 report:
Now the session log:
Let me fix a typo in the report and run the final placeholder scan:
The edit merged two table rows. Fixing:
Now the final placeholder scan and change-set review:
Change set is clean (only legitimate historical quote references). Final gate re-run, then the SSH wrapper setup for the push:
I have the full procedure. First, the commits (the repo's 3-commit convention):
All 3 commits made. Now the SSH wrapper push setup:
Now materialize the key and run the wrapper dry-run:
Dry-run clean (`dd5caff6..2f9f43da` fast-forward). Real push:
**P38 Sprint delivered and pushed to `main`** (commit `2f9f43da`, remote ref verified, key shredded). The working tree is clean.

## What this session delivered

**Environment (provisioned from scratch — the sandbox was wiped)**: rootless PG 17 via `docs/setup_pg_z.sh` + `skills/rootless-postgresql` (both DBs + the v1.2.2 schema), Redis 8, the backend venv, the web tree + Playwright, the demo substrate, and the daemonized dev stack. DEPLOYMENT.md §1–§9 was walked end-to-end on a fresh host.

**Baseline**: every documented P37 gate reproduced exactly (backend 1134P/0F/5S · vitest 698/698 · e2e 43/43 · RLS 13/13 · **mobile-nav 17/17 + translate probe PASS — no Tailwind v4 bug, the 44th/45th settlements**). Vitest + Playwright configs verified in place and current.

**Audit (0 Critical / 2 High / 1 Low)** — and the second High was caught by the plan's own live re-verification step:
- **H1**: both InvoiceNow workflow gates refused credit notes (the pre-P34 P9/C-3 gate + the invoice-only auto-transmit) while the UI rendered "Send via InvoiceNow" on APPROVED credit notes — reproduced live on CN-00001 (400).
- **H2**: `config/__init__.py` never imported the Celery app — every WSGI-process dispatch hit Celery's default amqp broker and 500'd on the first real send (the tests never saw it; every one mocks `.delay`).
- **L1**: the P37 spec's absolute sandbox path.

**Remediation (TDD — 6 RED gates + 6 designed controls, +12)**: gates widened to `{SALES_INVOICE, SALES_CREDIT_NOTE}` (quotes/inbound types still refused), the canonical Celery app import wired in, the path fixed. Final gate: **backend 1146P/0F/5S**, the full web matrix green, ruff 148/73 unchanged, and the live proof: **`POST /documents/{CN-00001}/send-invoicenow/` → 200/QUEUED** with a pollable log row.

Deliverables: [P38 plan](/home/z/my-project/ledgersg/docs/REMEDIATION_PLAN_2026-11-28_P38.md) · [P38 report](/home/z/my-project/ledgersg/docs/REMEDIATION_2026-11-28_P38_REPORT.md) · [session log](/home/z/my-project/ledgersg/docs/session_74.md) · [screenshots 256-263](/home/z/my-project/ledgersg/docs/screenshots/257_credit_note_detail_session74.png) · docs updated across README/CLAUDE/AGENTS/SKILL/PAD/DEPLOYMENT/API guide v3.11.0/ci.yml/worklog.

**Suggested next**: the newly registered emailed-PDF gate for credit notes, or the standing register (UP batch, E501/format axis, BR-CO-11/12/18, `unit_code` modeling).
