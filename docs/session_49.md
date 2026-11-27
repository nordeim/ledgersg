I'll start by internalizing the operating instructions and setting up the workspace. Let me create a comprehensive TODO plan first.
The workspace doesn't have the ledgersg repo yet. Let me clone it.
Repo cloned successfully. Now let me explore the structure and read the key documents. Given their size (100KB+ each), I'll use a combination of direct reading for critical files and subagents for digesting the large ones.
Now let me read the most recent session docs and check current state. I'll read the critical recent files myself and delegate digesting the huge docs to subagents in parallel.
Now let me read the P24 plan and report, plus the worklog tail to understand the current state.
Now let me read the worklog tail and check git history to understand session numbering conventions.
The last commit added `session_47.md` (a narration log of the P24 run). Now I have the state: P24 delivered, all gates green. Let me digest the large core docs via parallel subagents while I read the operational files myself.
I now have a comprehensive understanding of the project. Let me update the TODO list and read the operational setup files.
The environment is fresh (sandbox recycled) — PG, Redis, venv, node_modules all need rebuilding. Let me read the rootless-postgresql skill and start the setup immediately since it takes time.
Now let me start the environment build. First, PostgreSQL via the repo's setup script:
PG 17 is live. Now create the LedgerSG roles and databases, and load the schema:
The TCP connection needs the password (scram). Let me retry with PGPASSWORD:
Now load the schema into both databases (the schema's DO blocks create `ledgersg_app` etc.):
Schema loaded — 30 domain tables in each DB, all 3 roles present. Now Redis. Let me check DEPLOYMENT.md §5 for the exact procedure:
Now install Redis rootless:
Redis 8.0.2 running. Now backend venv and npm install in parallel:
Both installed. Now configure env files, verify Django check, and install Playwright chromium:
All configured. Django check passes (1 known W001 warning). Now start the dev stack via the daemonizer:
Dev stack is live. Now bootstrap the demo substrate:
Substrate ready. Now reproduce the full 9-gate baseline. Starting with backend pytest and vitest:
Backend 995P/0F/5S, vitest 660/660, tsc 0, eslint 0 — all exact. Now the live e2e gate:
One e2e failure on the P24 ledger pagination spec. Let me investigate:
The spec needs >20 ledger rows on the demo org. Let me check the demo org's journal line count and the spec's preconditions:
The demo org has only 11 journal lines — below the 20-row page size the P24 spec expects. In session 46 the org had 36 lines (accumulated substrate). Let me read the spec to understand its data precondition:
The spec claims "the demo substrate posts 36+ journal lines (the §9 bootstrap)" but a fresh bootstrap yields only 11 — a real gap. Let me verify the bootstrap script's actual output and check git history:
The bootstrap only posts ~11 lines — the P24 spec's "36+ lines" claim only held on session-46's accumulated DB. This is a genuine first-run-truth regression (a P25 finding). Let me identify the 1 skipped spec and complete the remaining baseline gates:
Root cause confirmed: on a fresh DB the demo user has one org; the banking spec (alphabetically first) settles its only invoice to PAID, so the void spec skips, and the P24 pagination spec fails with only 11 lines. The documented 42/42 baseline relied on session-46's accumulated substrate — the §9 bootstrap no longer delivers the first-run truth. Let me complete the remaining baseline gates:
All 9 gates reproduced — 8 exact, with the live e2e exposing the fresh-substrate gap (40P/1F/1S vs documented 42/42). Now the named focus: the mobile-nav live probe. Let me check what the audit script covers and do the live transition probe:
Let me check the actual toggle button's accessible name:
**移动端导航结论：运行正常 — 该界面上已无残留的 TailwindCSS v4 错误**（第17次确认：结束于 -100%/隐藏状态，`transitionProperty` 为 "transform, translate, visibility"，在 -40.96% 处出现运行中期采样，打开状态为 0px/对话框角色，按 Escape 可关闭）。
Now the audit phase. Let me consult the skills catalog and audit the recent P24 changes plus the substrate gap:
The catalog is consulted (tdd, nextjs16-tailwind4, tailwind-patterns, agent-browser, rootless-postgresql are the relevant ones — all with established usage patterns in AGENTS.md lessons). Now let me run a Mode C audit of the recent P24 changes via a subagent while I audit the substrate/e2e contract myself:
Excellent audit — 0 Critical / 2 Medium / 5 Low / 7 Informational, plus my headline finding (fresh-substrate e2e gap). Now let me verify the e2e specs' sensitivity to substrate growth before designing the bootstrap top-up:
The banking spec is self-sufficient (creates its own invoice). So why did the void spec skip? Let me check the demo user's org list — `orgs.results[0]` may not be the demo org:
INV-00002 (banking spec's own) is APPROVED — so the void spec should find it. Let me check why it skipped by re-running just the invoices spec:
The void spec passes now. The skip in the full run needs precise identification — let me re-run the full suite and capture exactly which test skipped:
Now 41P/1F/0S — the skip was transient in the first run. Let me find all conditional skips to understand which one fired:
Only the void spec has conditional skips. Let me examine the current journal entries to understand the line shape for the top-up design:
Each approved invoice posts 3 lines, each settlement 2. Pure bootstrap = 6 lines. Let me check the e2e spec inventory for anything sensitive to substrate growth (F5/GST/dashboard):
p11 has its own idempotent substrate helper on the demo org. Let me check its F5 box assertions and p10's dashboard assertions for value sensitivity:
Let me verify reports.spec.ts fully for value sensitivity:
Structural assertions only — substrate growth is safe. Now let me verify the vitest/playwright configs and the `.env.example` truth (task items):
Both configs are mature — the "add suites under existing configs" interpretation stands. Let me examine the TablePagination component for the L-2/L-3 fixes:
All findings verified in source. Now let me read the pagination module and parse_int_param for the backend fixes:
Let me confirm the transactions URL and check the current git status:
URL is `bank-transactions/`, tree is clean. Let me read the bootstrap script fully to design the top-up in its style:
Now let me check the existing ledger-page test structure to design the frontend RED tests:
I have complete evidence for the plan. Let me write the P25 remediation plan now:
Plan saved. Now Phase 1 — RED. Let me check the P24 test file's imports and conventions first:
Now let me write the P25 backend RED test file. First, verify the banking URL prefix:
Let me fix the confused count assertion in the empty-string test:
Now run the backend RED phase:
The model lives in `apps.core.models`. Fix the import:
Backend RED confirmed: 4 failed (the behavior changes), 10 passed (the pins). Let me verify the ledger huge-offset failure is the documented 500:
`assert 500 == 400` — the M2 500 reproduced. Now the frontend RED. Let me read the existing component test:
Now add the Label-in-Name RED test to the component spec:
Now the ledger-page test extensions. Let me read the rest of that file first:
Now let me add the frontend RED tests — the beyond-end branch, the org-switch pin, the summary-math guard, and the L5 rename:
Now the ledger-page test extensions:
Let me check the userEvent import convention in the repo:
Now run the frontend RED phase:
All three tiers RED for exactly the right reasons. Now Phase 2 — GREEN. First the backend fixes:
Now the pagination module — the offset cap and the offset-requires-limit rule:
Backend GREEN (40/40 across P24+P25). Now the frontend fixes:
Now the ledger-client fixes — the count-based empty state, render-time org reset, and the comment truth:
The `end` needs the same guard — `min(offset+limit, count)` still yields 40. Fix:
有两个测试设计问题：`beyond-end` 测试需要导航到 `offset 40`，而 `org-switch` pin 需要真实的 hook（mock 会导致丢弃的渲染）。让我检查一下 `use-ledger.ts` 的 transport：
The org-switch pin needs the REAL hook (module mocks can't observe discarded renders). Let me rewrite the beyond-end test with a stateful mock and move the org-switch test to its own file with only the transport mocked:
Now create the dedicated org-switch test file with the real hook:
All GREEN. Let me verify the org-switch test is genuinely RED on the old code (TDD honesty check — temporarily restore the useEffect):
The test passes even on the old code — it doesn't distinguish the implementations. Let me debug what URLs actually fire:
Important empirical finding: **the stale fetch does not manifest on React 19 + TanStack v5.90** — even the old useEffect version never fires it (notifyManager batching). The L3 finding downgrades from "bug" to "hardening" — the render-time reset makes the guarantee explicit instead of timing-emergent. Let me restore the fix, clean the debug, and correct the records:
Now update the plan's L3 finding to the honest empirical status:
The plan is now consistent. Now T4 — the bootstrap step 4c fodder top-up:
Let me syntax-check and run the top-up live on the current dev DB:
The top-up didn't fire — 16 lines / 2 approved means the loop didn't create anything. Let me debug:
No fodder documents and the syntax works. Let me debug the functions directly against the live backend:
The API works manually. Let me trace the script execution:
The loop runs but every POST fails — `FODDER_ID` is empty. Let me see the actual error:
The POST requires `tax_code_id` — but step 4a's original invoice (created without it) succeeded. Let me check the original entry's lines and the serializer rule:
Major discovery — the bootstrap's step 4a has been **silently broken all along**: `tax_code_id` is required by the serializer (P14/M-4), so the invoice POST fails and `"invoice OK ()"` prints with an empty ID. The e2e specs masked it by being self-sufficient. Let me check how p11's helper fetches the SR tax code:
Now let me fix the bootstrap script properly — the tax_code_id on all three document-creating steps plus loud failures:
Top-up works: 37 lines, 9 approved invoices. Verify idempotency:
Idempotent ✓. Now restart both `--noreload` backends (the P24 lesson) and run the live probes:
All T7 probes verified. Now the full gate matrix — backend suite first:
Coverage green at the ratchet (78 files, 664 tests). Now the live e2e gate:
42/42. Now the remaining live gates — rls_smoke, mobile-nav, build + prod-CSP, npm audit:
All 9 gates green on the remediated tree. Now **the fresh-DB proof** — the M1 acceptance: drop/recreate the dev DB, restart, bootstrap once, then the first e2e run:
The drop failed — backends were still connected. Let me kill them first, then redo:
Fresh bootstrap: 36 lines, 12 approved invoices, real invoice ID. Fix the Redis flush (needs LD_LIBRARY_PATH), then the first-run proof:
**THE FRESH-DB PROOF: 42/42 passed, 0 skipped, on the FIRST run** — the first-run truth restored. Now the screenshots. Let me check the session-45 capture script conventions:
I have the pattern. Note the session-45 script uses the old `/go to next page/i` locators that my L1 fix renames — I'll patch that script too (keeps it re-runnable). First, let me check the current demo org line count after the fresh e2e run, then write the session-48 script:
Also patch the session-45 script's two locators to the new aria-labels (keeps it re-runnable):
All 8 captures OK with DOM truths. Now the non-blank pixel verification per repo convention:
All captures verified. Let me re-run the mobile-nav and rls gates on the final (fresh-DB) environment state to complete the matrix:
Now the `.env.example` verification (config-readers sweep):
`.env.example`s verified truthful (the one "missing" match is a comment false-positive). Now the docs truth pass. Let me find the exact spots in README:
Now the README truth pass:
Now add the P25 milestone section and update the testing counts:
Now update the README testing-section counts:
README done. Now CLAUDE.md:
The MultiEdit failed on exact matching. Let me use Python for the AGENTS.md header edits:
Now add the P25 lessons section to AGENTS.md. Let me check the P24 lessons format:
Now ledgersg_SKILL.md and PAD:
Now DEPLOYMENT.md:
Now update the API guide — version bump and the P25 addendum:
Now write the P25 report:
Now the session log and the worklog entry:
Fix a typo in the worklog entry:
All intended files only. Pre-commit verification — placeholder scan and final arithmetic check:
Everything verified. Now the atomic conventional commits:
All 5 commits in, tree clean. Now the SSH-wrapper push. Let me read the runbook:
I have the runbook. Let me check the sandbox's ssh availability and prepare the key:
No ssh binary and no paramiko — I'll install paramiko and deploy the Appendix A shim (outside the repo):
Dry-run authenticates and negotiates the fast-forward. Now the real push:
The push is fully verified — remote `main` @ `94af7dc5` == local HEAD, tracking ref synced, key shredded. Let me finalize the TODO list:
The complete P25 remediation cycle is delivered and pushed. Here's the full account:

## Session 48 — P25 Sprint: delivered, all gates green, pushed to `main` @ `94af7dc5` (remote-verified)

**Understanding validated first:** fresh `git clone` to `0def60b5`, full reads of the core docs + the session-46/47 logs + the P24 plan/report, then the **9-gate baseline reproduced before any change** — 8 gates exact (backend 995P/0F/5S · vitest 660/660 · tsc 0 · eslint 0E/0W · rls 13/13 · mobile-nav 17/17 · prod-CSP 5/5 · npm audit 0 critical), but the live e2e gate did **not** reproduce: 40P/1F/1S vs the documented 42/42 — that gap became the sprint's headline. The environment was rebuilt from zero (rootless PG 17 + Redis + venv + npm + chromium, all daemonized).

**The named focus — mobile navigation verdict:** **working as expected; NO remaining TailwindCSS v4 bug.** Live probe: `transitionProperty: "transform, translate, visibility"`, closed `-100%`/hidden, mid-flight sample at `-40.9622%`, open `role=dialog` at `0px`, Escape closes it.

**The headline (root-caused Mode B before fixing):** the §9 bootstrap's invoice/credit-note steps had been **silently broken since P14/M-4** made `tax_code_id` required — POSTs failed behind `|| true` guards ("invoice OK ()"), so a fresh host never stocked the volume the P24 e2e spec documents. Fixed with the SR tax code + loud failures + a count-driven fodder top-up (≥36 lines, ≥4 APPROVED, idempotent). **The proof: fresh DB → one bootstrap → FIRST e2e:full = 42/42, 0 skipped.**

**Also shipped (TDD, RED→GREEN):** the int8 offset cap (was an untyped 500), offset-requires-limit 400 (was silently ignored), the transactions test matrix, WCAG 2.5.3 pagination labels, the beyond-end page keeping its controls, the render-time org-switch reset (with an honest empirical downgrade recorded — the old code's stale fetch never actually fired on React 19 + TanStack 5.90).

**Final gates:** backend **1009P/0F/5S** · vitest **664/664 (78 files)** · coverage green at the ratchet · tsc 0 · eslint 0E/0W · e2e **42/42** (twice) · rls 13/13 · mobile-nav 17/17 · prod-CSP 5/5 · npm audit 0 critical.

**Deliverables:** the [P25 plan](/home/z/my-project/ledgersg/docs/REMEDIATION_PLAN_2026-11-28_P25.md) + [report](/home/z/my-project/ledgersg/docs/REMEDIATION_2026-11-28_P25_REPORT.md) + [session-48 log](/home/z/my-project/ledgersg/docs/session_48.md) + [worklog](/home/z/my-project/ledgersg/worklog.md); 8 DOM-verified screenshots (152-159, the fresh-substrate ledger pair the headline); the docs truth pass (README 1715-badge, CLAUDE 2.26.0, AGENTS + 4 new lessons, SKILL 2.12.0, PAD, [DEPLOYMENT.md](/home/z/my-project/ledgersg/docs/DEPLOYMENT.md) re-verified from zero, [API guide 3.4.0](/home/z/my-project/ledgersg/API_CLI_Usage_Guide.md)); `.env.example`s re-verified truthful. 5 conventional commits pushed via the SSH wrapper (dry-run first, remote ref verified == HEAD, key shredded).

**Suggested next steps:** the frontend pagination wiring for invoices/contacts/payments (the backend contract is ready), the SQL-level push-down through the five service signatures, and the Peppol transmission-log pagination (newly registered).
