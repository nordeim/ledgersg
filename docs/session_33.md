The workspace exists with the repo already cloned. Let me check its current state.
工作区位于 `main` 分支，且状态干净。让我先用 `git pull` 拉取最新更改以刷新。
仓库已与远程仓库同步至 commit `d7f7d9b7`。我来为这个多阶段的任务建立任务计划。
文档大小适中。我来阅读它们——首先从描述当前状态的最新会话/修复文档开始。
Session 30/31 (P15 sprint) 已完成并推送。现在让我阅读剩余的关键文档。从 P15 计划/报告和工作日志开始。
Now the worklog and the P15 plan structure:
现在正在阅读核心文档——CLAUDE.md 和架构文档：
已注意到 `CLAUDE.md` 第 6 行与表格中陈旧的计数（750P/530 对比 834P/532）——这是文档核对过程中的一个发现。接下来是架构文档和技能文件：
Now the project SKILL file and session_29:
Now let me check AGENTS.md structure and key sections:
我已掌握完整情况。让我快速浏览一下剩余的会话文档，并检查技能目录：
文档已阅读。现在让我验证环境状态——检查 PG、Redis 和构建产物是否在沙盒重置中幸存下来：
Environment survived — PG 17, Redis, venv, node_modules, and even the dev stack (from session 30) are still running. Let me verify database state and reproduce the documented baselines:
PG is intact (v1.2.0, RLS complete, §17 verified) but `test_ledgersg_dev` is missing. Let me recreate it and load the schema:
The test DB already existed (my earlier listing was misleading). Let me verify both DBs are at v1.2.0 with §17 intact:
Both DBs have 25 RLS-enabled tenant tables (§17 complete). Let me confirm the schema file version and check for the app_organisations data (demo substrate):
Schema v1.2.0 with §17 confirmed; demo data present. Now let me reproduce the documented baselines — backend suite first:
One failure: the RLS app-role test can't authenticate as `ledgersg_app` — the role's password doesn't match what the test expects. Let me check what the test uses:
The test expects the documented dev default password `CHANGE_ME_IN_PRODUCTION`. The previous session's smoke run changed the role password. Let me reset it:
Baseline restored. Now the full backend gate plus frontend gates:
Backend baseline exact match: 834P/0F/5S, invariants 34P, security 72P/3S. Now frontend gates:
All baselines reproduced exactly (834P/0F/5S · tsc 0 · vitest 532/532 · eslint 9). Vitest + Playwright suites are present and configured. Let me verify the test configs and check the skills catalog:
Let me find the specific skills the user mentioned in the catalog:
Let me read the Tailwind V4 validation report and the key skill files for the mobile-nav check:
The report's trap log (space-y rewrite, shadow-scale shift) is the key reference for the mobile-nav check. Now let me audit the recent P15 code changes — the diff from the pre-P15 base:
P15 变更已映射。现在让我先在运行中的开发栈上验证其健康状况，然后运行 `mobile-nav` 实时探针（用户关注的核心点）：
Dev stack is live (backend runserver + next-server 16.4.6). Running the mobile-nav live probe:
17/17 mobile-nav checks pass — the nav works, no Tailwind v4 bug. Let me verify the v4 setup at source level (the report's trap log: legacy config absence, shadow token pin, space-y trap):
v4 setup is clean (CSS-first, no legacy config). The probe checked the nav live; let me extend the space-y trap sweep source-wide (the report's trap 4 — any `space-y-*` container with explicit `mt-*`/`mb-*` child):
The heuristic flags are noise (600-char window spans unrelated siblings) — the live probe settled the nav: clean. The v4 semantics are the *design intent* for this v4-native app. Marking the mobile-nav todo complete; now the systematic audit:
Let me load the key audit skills from the repo (code-review-checklist for the scan structure, tdd for execution):
I have the audit framework. Now launching three parallel deep-audit agents over distinct scopes:
All three audits are complete with substantial findings. Per audit discipline, let me hand-verify every Critical/High finding before planning:
H-1 verified: service.py drops all four critical middleware entries. Now verifying the CSP Critical against actual build artifacts:
C-1 verified: 3 non-nonced inline scripts per page + strict `script-src 'self'` = blocked hydration in production. Now verifying the remaining Highs:
Now verifying the org-creation stale closure (AUDIT-2/H-2):
All Highs verified in source. Two quick spot-checks (discount_pct drop + the .gitignore/backup claim), then I'll write the P16 plan:
所有发现均已验证。现在，在编写计划之前，让我先验证关键的实现站点（计划与代码库对齐）：
**Alert** — the bash output shows a possibly corrupted selector `"aref]"`. This matches the documented P10 tool-display artifact (`[` sequences eaten in bash output). Verifying raw bytes before treating it as real:
False alarm — the Read tool shows the selector is intact (`"a[href], button:not([disabled])"`); it was the documented bash display artifact (P10 lesson 40). All plan targets are now validated. Writing the P16 remediation plan:
Plan saved. Now validating the remaining execution sites before starting (the plan-vs-codebase alignment pass):
All sites validated. Let me confirm the Next 16 proxy.ts convention (for F1) in the installed framework:
The bundled Next 16 guide confirms the proxy.ts + nonce pattern, with a critical caveat: **nonces require dynamic rendering**. Let me read the rest and check this app's rendering mode:
All routes are statically prerendered — the nonce approach requires dynamic rendering (per the Next guide). This is a material design element; let me record it in the plan, then execute:
Now executing **Phase 0 / F1 — the CSP nonce fix**. First, the current next.config.ts in full:
Now implementing F1 with TDD. First the RED test for the CSP strategy module:
RED confirmed. Now the GREEN implementation — the CSP builder module:
Now the proxy itself and the next.config.ts surgery (remove CSP, add allowedDevOrigins):
`isDev` is now unused in next.config.ts — checking and cleaning up, then adding the layout's force-dynamic:
Now the root layout's force-dynamic (nonces require dynamic rendering):
Now run the CSP unit tests (GREEN check) plus typecheck:
CSP builder GREEN (8/8), tsc clean. Now the production smoke gate — the script that would have caught this class of bug:
All routes now dynamic + Proxy registered. Running the production CSP smoke:
Path error — running from the repo root with the documented NODE_PATH convention:
The script needs robust path resolution (spawn cwd vs module resolution). Fixing:
**FE-C1 fixed and verified live: 5/5 smoke checks pass — production hydrates under a nonce CSP.** Now Phase 1 — backend contracts, starting with B14 (the service-path middleware). Reading the existing settings-gate test conventions:
Writing the RED test for B14 (the middleware-presence gate) following the file's conventions:
RED confirmed. Now the GREEN fix — derive service.py's MIDDLEWARE from base:
B14 GREEN. Now B1 — the BulkAllocationSerializer instalment fix. Reading the full serializer:
Let me see how the statuses are defined in payment.py and the service to unify:
Now writing the RED test for B1 — an endpoint-level instalment test. Checking the existing P14 contract test first:
The existing tests cover the service but not the wire serializer. Writing the RED test for the endpoint contract:
RED confirmed (2 genuine failures). Now the GREEN fix on allocation.py:
Now removing the dead `AllocationCreateSerializer` references:
B1 GREEN (17 passed). Now B2+B3+B4 — the payment service fixes. Reading the relevant service sections:
Let me examine the void/unallocate release blocks and the audit trigger coverage before batch-editing:
No lifecycle evidence column exists. Let me check the audit trigger coverage on documents — the event log may be the evidence source:
`trg_audit_document` exists but runtime audit-parsing is fragile. B8 design decision: evidence-based partial restore (`invoicenow_sent_at` → SENT, else APPROVED) with the email-sent residual registered. Writing the RED tests for the payment-service batch (B2/B4/B8/B12/B13):
4 errors — the `payment_fixture` lives in the other module. Fixing by importing the fixture:
6 genuine RED failures. Before the GREEN pass, let me read the void method's reversal-date logic (the localdate test needs the fallback semantics):
The test needs a fiscal period covering today for the localdate assertion. Checking the conftest fixtures:
The test needs a today-period for a clean assertion. Updating the localdate test:
Now the GREEN pass — decimal_utils.py first, then all payment_service.py edits:
Now the payment_service.py batch (lock, money(), localdate, status restore, audit dedup):
Let me check the current state of the allocate method after the partial edit:
The voided check was consumed by my edit — restoring it after the locked read:
Now the remaining payment_service edits — money() for FX paths, localdate, status restoration in both release paths, and the audit dedup:
Now the audit dedup (B13) — removing the manual audit writes where the trigger already covers the row:
Two rows still written — my regex removal missed create_received's block. Checking:
The trigger maps INSERT→'CREATE' — my removal worked; the test vocabulary was wrong. Fixing both test issues:
All 8 payment tests GREEN. Continuing with B4's box-override validation (NaN at the file/amend seams):
The amend path takes no boxes — both seams covered. Now let me batch the remaining backend fixes (B3/B5/B6/B7/B9/B10/B11). First the sites:
All sites confirmed. Writing the batched RED tests for B5/B6/B7/B9/B10/B11:
5 RED failures confirmed. Applying all GREEN fixes:
The python replace silently no-opped (pattern mismatch). Using Edit directly:
The control assertion should expect the raise, not compare:
All 7 GREEN. Now B3 — the atomic create+allocate. Implementing the combined service method:
Now the B3 RED test (allocation failure must roll back the payment), then the B12 remainder (period_lock docstring + payment-void lock test):
B3 GREEN (10/10). Now the B12 remainder — the period_lock docstring + the missing payment-void lock test:
Writing the payment-void lock test (payment created before filing; void after — the fallback path must refuse):
All backend Phase-1 tasks complete. Running the full backend suite for regressions:
These tests asserted the manual rows I intentionally removed (B13). Let me verify the trigger's user attribution path before updating them:
The trigger carries full attribution via the request-context GUCs (P11/M-8). Updating the 2 tests to the trigger contract:
**Backend FULLY GREEN: 860 passed / 0 failed / 5 skipped (+26 new tests).** Now Phase 2 — frontend. Starting with F2 (dashboard queryKey):
The schema matches field-for-field. Checking the existing wrong-key test convention before writing the RED test:
The test file has the exact pattern I need. Adding the F2 RED test:
RED confirmed. The GREEN fix — swap the page's inline query for the hook:
F2 GREEN. Now F3 — the org-creation stale closure. Reading the provider test conventions:
Adding the F3 RED test — `selectOrgById` must select an org absent from the current list:
RED confirmed. Applying the F3 GREEN fix in the provider:
F3 GREEN. Now F4 — the UEN regex. Writing the RED test:
The regex lives on `customerSchema`. Rewriting the test to target it directly:
RED confirmed (T/S-forms rejected). The GREEN fix — mirror the backend's three ACRA patterns:
F4 GREEN. Now F5 — the login open-redirect guard:
Writing the F5 RED test (redirect guard):
The location stub isn't read — the fallback tests pass for the wrong reason. Fixing with history.replaceState:
Correct RED state (2 genuine failures). The GREEN fix:
F5 GREEN. Now F6+F9 — the shell fixes. Reading the current scroll-lock and drawer markup:
Now appending the F6 + F9 RED tests to the shell test file:
RED confirmed. Checking whether setup.ts already polyfills matchMedia (affects test design):
Restructuring the F6 test (stub before render) and applying the shell fixes:
Now the shell.tsx GREEN fixes (breakpoint listener, dialog semantics, broadened trap):
Two test-visible issues: jsdom's `offsetParent` is always null (my visibility filter broke the trap) and the breakpoint fire needs act(). Fixing:
The open drawer now exposes role=dialog — the test must query the new role:
All 12 shell tests GREEN. Now F8 (dead code + single-flight failure test) and F10 (e2e serial contract):
tsc clean. Now the single-flight shared-failure test:
The failure path was already correct — now pinned by test (3/3). Now F10 — the e2e serial contract:
All Phase-2 items landed. Running the full frontend gate:
5 test failures + 4 new lint findings to fix. Starting with the headers-config test (it gated the OLD architecture):
Updating the headers-config test to the P16 single-source architecture:
Now the new-organisation page test:
Now fixing my 2 lint additions (the unused interfaces) and checking the remaining eslint delta:
One new finding is mine (`QueryFunction` unused). Fixing it:
One error still mine — identifying it against the baseline:
Aligning my test with the established (lint-clean) holder pattern:
Let me get a precise per-file comparison:
My test's holder mutation adds a third error of a pre-existing class. Rewriting the probe mutation-free:
Lint parity restored (9 = baseline). Running the complete frontend gate:
All frontend gates green (554/554, coverage 0, eslint parity, tsc 0). Rebuilding production + re-running the CSP smoke with the final code:
Prod smoke 5/5. Now restarting the dev stack with the remediated code (the P13 lesson: next.config changes need a manual restart):
Both daemons up. Running the e2e default suite:
Default e2e green (11P + 29 gated). Now the live full suite:
**Live e2e:full — 40 passed, 0 failed.** Now the mobile-nav probe (my shell.tsx changes touched it) and the rls_smoke:
All live gates green. Now capturing screenshots of the remediated surfaces — adapting the session-30 capture script:
8 screenshots captured and verified. Visually confirming the key P16 surface (the mobile nav dialog):
The repo's DOM-truth verification standard is satisfied (the probe + truths asserted the visuals). Now Phase 3 — the docs truth pass. First, the final gate counts:
Final counts: 860P/0F/5S backend (865 collected), invariants 34P, security 76P/3S, vitest 554/554, total 1454. Executing the docs truth pass with a precise script:
Now the README truth pass (the biggest file — 12 fixes):
Now DEPLOYMENT.md — the §17 upgrade note, stale counts, and the new smoke step:
§17 extraction verified (322 lines to EOF). Adding the production-CSP smoke to the verification sections:
Now the API_CLI_Usage_Guide.md alignment (stale metrics, wrong endpoint, missing endpoints, P16 addendum):
Now the .env.example addition and the hygiene untracking:
Now AGENTS.md — the status header + P16 patterns section:
Adding the P16 lessons to ledgersg_SKILL.md + the project_state:
Now Current_Project_Status.md (the SUPERSEDED banner) and the worklog + session log + P16 report:
Now the session log and worklog:
All docs written. Final pre-commit verification — the complete gate re-run:
All gates green. Organizing the commits:
The hygiene commit re-added two docker logs (`*_new.txt` doesn't match `*_log.txt`). Fixing with an amend:
The amend mixed the docs changes into the hygiene commit. Splitting them properly:
Let me verify exactly which commit carries the deletions (critical for the push):
The hygiene deletions accidentally landed inside the CSP commit (the `git rm --cached` ran before the commit phase). Since nothing is pushed, let me rebuild the stack cleanly:
State reset cleanly. Recommitting in the correct order:
Now the hygiene commit (deletions staged fresh, nothing to swallow them):
18 plan files in subdirectories remain — amending them into the hygiene commit:
One leftover — the old status file. Resolving:
The archived copy lost its banner in the reset dance. Fixing both issues:
11 clean commits, tree clean. Final hygiene gate + the push setup:
The push procedure is clear. Setting up the key + shim (checking for a real ssh binary first):
Dry-run clean (fast-forward of the 11 commits). Executing the real push:
Push verified by the wrapper (remote == local HEAD). One independent confirmation via HTTPS:
**Push confirmed by two independent channels** — remote `main` at `eae32567` == local HEAD. Finalizing:
The P16 sprint is complete and pushed. Here's what happened:

## Session Summary — P16 "Production Truth" Sprint

**The audit** (3 parallel deep agents + my hand-verification of every Critical/High) found the headline issue: **the shipped production app could not hydrate** — the static CSP `script-src 'self'` blocked Next.js's non-nonced inline bootstrap scripts on every page, and the dev-mode test suite structurally couldn't catch it.

**The mobile navigation (your named focus): verified working — no TailwindCSS v4 bug.** The 17/17 live probe passed at 375/800/1280 px (toggle, visibility, overlay, hit-target, transitions, no overflow, no console errors, space-y trap sweep clean). P16 then *improved* it: `role="dialog"` + `aria-modal`, a full focusable-set trap, and scroll-lock release on breakpoint resize.

**Key fixes** (all TDD, RED-first): the nonce-based CSP via `proxy.ts` + a new production smoke gate (5/5); the Docker-path middleware restored; the allocate endpoint's instalment contract; the dashboard invalidation key; org-creation no longer dead-ends; all three ACRA UEN forms accepted; payment locks/atomicity; NaN box-override rejection; plus a full docs truth pass and hygiene cleanup.

**Final gates, all executed green**: backend **860P/0F/5S** · vitest **554/554** · eslint 9 (parity) · live e2e **40/0F** · rls_smoke **13/13** · mobile-nav **17/17** · prod-CSP smoke **5/5**.

**Delivered**: [P16 plan](/home/z/my-project/ledgersg/docs/REMEDIATION_PLAN_2026-11-26_P16.md) · [P16 report](/home/z/my-project/ledgersg/docs/REMEDIATION_2026-11-26_P16_REPORT.md) · [session_32](/home/z/my-project/ledgersg/docs/session_32.md) · [DEPLOYMENT.md](/home/z/my-project/ledgersg/docs/DEPLOYMENT.md) · [API guide](/home/z/my-project/ledgersg/API_CLI_Usage_Guide.md) · [worklog](/home/z/my-project/ledgersg/worklog.md) · screenshots 88-95 in `docs/screenshots/`.

11 conventional commits pushed to `main` via the SSH wrapper — remote verified at `eae32567` == local HEAD, key shredded. The next sprint's first item is registered: the ContactPicker WAI-ARIA combobox.
