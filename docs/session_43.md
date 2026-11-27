I'll continue with the ledgersg multi-phase task. Let me set up the task tracking and start by refreshing the workspace.
There's an existing workspace with a `ledgersg` repo and a `pg` directory from prior work. Let me inspect the state.
工作区已更新（至 `67512bf1`，仅 session_41.md 有变更）。现在让我阅读核心文档。
The core docs have very long lines (Read truncates at 2000 chars/line). Let me wrap them into readable temp copies and read fully.
The Read output is capped by size. Let me read the wrapped docs in chunks.
Now let me read AGENTS.md (the key conventions doc) in chunks.
AGENTS.md 已完全读取。现在开始读取会话/修复文档（当前状态）。
Session 40/41 read — P20 was completed and pushed; the suggested next step is a P21 cycle. Now the P20 plan/report to mirror conventions.
P20 report read. Now the worklog tail, skills catalog, Tailwind validation report, and PG setup script.
现在让我检查一下环境状态（PG、Redis、venv、node_modules）——沙箱可能在会话期间被回收了。
The environment is fully alive (PG 17, Redis, backend :8000/:8001, frontend :3000 — the session-40 stack survived). Let me verify DB state and backend health, then read the skills catalog and Tailwind report.
`test_ledgersg_dev` is missing (will recreate per the documented recipe). Now reading the skills catalog and Tailwind validation report.
Let me extract the specific skill entries I need from the catalog.
Now let me review the remaining core docs (README, PAD, ledgersg_SKILL) — checking their section structure first.
我现在已经完全理解了该项目。让我更新一下待办事项并复现基准门（baseline gates）。
Test DB exists with schema loaded (38 tables). Now the backend baseline.
Backend baseline reproduced exactly: 950P/0F/5S. Now frontend gates.
所有静态基准线已完全重现（950P · 627/627 · tsc 0 · eslint 0E/0W）。现在进行动态基准线测试 —— 让我检查一下 `gate scripts` 和 `live stack` 的健康状况。
Mobile-nav 17/17 — twelfth consecutive live settlement, no Tailwind v4 bug. Now the full e2e suite.
e2e 40/40 green. Now rls_smoke on the :8001 instance and prod-CSP smoke.
rls_smoke 13/13. Now build:server + prod-CSP smoke (the last baseline gates).
All 8 documented P20 baseline gates reproduced exactly. Now launching the P21 audit (the repo's three-parallel-audit pattern).
P20 diff confirmed (8 commits). Launching the three parallel deep audits (Mode C) now.
All three audits complete: **0 Critical / 2 High / 20 Medium / 15 Low / 13 Informational**. Per the repo's audit discipline, I must hand-verify every High finding in source before planning. Let me verify now.
Both High findings confirmed in source. Now verifying the remaining frontend Medium anchors.
All FE anchors verified. Now the backend Medium anchors.
All backend anchors verified. Now the Peppol delivery path (for BE-M4) and the envelope sites + frontend consumers.
BE-M4 路径现在已明确（在 DELIVERED 处标记 `invoicenow_sent_at`）。接下来是信封（envelope）站点及其前端消费者。
The RLS isolation test reads `.get("data", [])` against a `{results}` endpoint — a vacuous assertion (real finding). Now let me check the docs/session numbering and screenshots convention for the new deliverables.
Now verifying the last set of anchors before writing the plan.
All anchors verified. Now writing the validated P21 remediation plan.
Plan saved. Now validating the remaining anchors (test assertion shapes + date defaults) before execution.
All anchors validated. Starting **Phase 1 (backend, TDD)** — first, studying the P20 test conventions to mirror.
Now I have all conventions. Writing the P21 RED test file (Phase 1, TDD).
现在让我运行 RED 测试——它们应该在修复前失败（验证每个失败都是契约，而不是设置）。
RED tests fail as expected. Fixing the fixture setup errors (missing PAYMENT sequences) and verifying each failure is the real contract.
所有 18 个 RED 失败均为正确的契约失败。现在进入 **GREEN 阶段**。让我先研究一下具体的修复位置。
Now checking the 400-raising convention used elsewhere, then applying all backend fixes.
Applying the GREEN fixes. **Fix 1: the envelope unification (7 sites).**
Now the GST envelope sites.
**Fix 2: bank-account locking (BE-P21-M1).**
`get()` is also used by read-only views — locking there would break outside transactions. Reverting and using a private locked getter for the mutation paths instead.
**Fix 3+4: dashboard invalidation on void/create_entry + the on_commit cache truth.** Let me view the current helper implementations.
The on_commit move changes semantics for two existing truth tests — I'll update them to the new contract with `django_capture_on_commit_callbacks(execute=True)`. Applying the helper changes now.
Now `create_entry` in journal_service: the dashboard invalidation (M2) + moving the account_balance deletes to on_commit (M3).
The P20 balance-cache test asserts inline deletion — must update it to the new on_commit contract.
Now updating the two dashboard truth tests to the on_commit contract.
**Fix 5: the invoicenow_sent_at evidence stamp (BE-M4).**
Now updating the old-shape test assertions to the unified contract, and removing the redundant Decimal import.
Now updating all the old-shape test assertions to the unified envelope.
Now the vacuous RLS isolation test fix.
Now running the P21 test file plus the updated suites — GREEN check.
The fixture invoice becomes PAID (not voidable). Fixing to a partial allocation (PARTIALLY_PAID — voidable).
找到了——`patch` 上下文在回调执行前退出，所以真正的 `method` 运行了（spy 已失效）。正在将 `patch` 重构以包裹 `capture` 块。
The final cache.get assertion would fail under the pure mock (it doesn't delete the real key) — removing it; the spy count is the contract.
All P21 tests GREEN. Now the full backend suite for regressions.
Backend suite: **969P/0F/5S** (+19 P21 tests, zero regressions). Now ruff parity on touched files.
Cleaning up my new lint findings.
Lint parity achieved (touched files at/below base; new P21 file clean). Final backend verification run.
**第一阶段已完成 (969P/0F/5S)。** 现在进行第二阶段 —— 前端。首先研究现有的测试规范。
Let me read the P20 a11y sweep test file directly for its loader-test conventions.
现在正在编写 P21 前端 RED 测试。首先，让我查看一下需要修复的 loader 块。
Now writing the P21 frontend RED test file.
Now fixing the test file with the correct prop shapes.
FE-M1 因设置错误而失败（缺少 `useImportBankTransactions` mock）。正在修复 mock。
All 8 RED for the right reasons. Now the date-helper tests and envelope consumer updates.
Now the GREEN fixes. **FE-H1 + H2 + M1:**
**FE-M4 + M5:** payment-card keyboard contract + reconcile aria-pressed.
**FE-M2: the loader live regions** — applying to all remaining sites.
**FE-M3: the date helpers** in shared/format.ts.
Now wiring the consumers of the date helpers.
Now the FE-L batch. Checking ContactPicker and the L3 sites.
Now the frontend envelope consumers.
Now updating the consumer test mocks to the new envelope and adding the token compile gate.
All P21 frontend tests GREEN. Now the full vitest suite for regressions.
The L2 fix intentionally changes the combobox's accessible name to the visible "Customer" label — updating the existing test query.
vitest 641/641 (75 files). Now tsc + eslint.
641/641 with coverage exit 0. The earlier single failure was a flake — let me confirm stability with one more full run.
Stable. Checking e2e specs for envelope dependencies.
The e2e helpers must read the new envelope — updating all org-list casts across e2e specs.
**Phase 3 — cross-cutting.** First the bootstrap script simplification.
The backend on :8000 must serve the new envelope code. Checking reload state.
Both backends run `--noreload` with stale (pre-P21) code — restarting them per the stale-server lesson.
Envelope live-verified on :8000. Now the live e2e suite against the remediated stack.
Login rate-limit accumulation (the documented flake class) — flushing Redis and re-running.
The 500 was my own missing trailing slash. Testing properly and checking the p10 failure cause.
The full-suite run used the correct URL (npm script inline override); my isolated rerun used a wrong env override. Re-running the full suite after a Redis flush.
The FE-L2 rename affects an e2e query — updating the spec's accessible-name locator.
e2e 40/40 green. Now the remaining live gates on the remediated stack.
All gates green. Now the docs truth pass (Phase 3). Starting with README.
Applying the API guide updates.
Now DEPLOYMENT.md counts.
Now the README updates (badge, status table, P21 milestone, test section).
Now CLAUDE.md — the status header, P21 milestone, and the misattributed P18/P19 block.
Now AGENTS.md, ledgersg_SKILL.md, PAD, and ci.yml.
Docs updated. Now the session-42 screenshots. Studying the session-40 capture script to mirror.
Shot 131: the `networkidle` wait consumes the delay before capture. Fixing the wait strategy for the delayed shot.
All 8 captures verified. Now the pixel non-blank verification (repo convention).
All captures verified. Now writing the P21 report, session log, and worklog entry.
All deliverables written. Now the pre-commit verification (placeholder scan + change inventory).
Pre-commit scans clean. Final consolidated gate run before committing.
All gates green. Now the conventional commit series.
All 7 commits on main, tree clean. Now the push via the SSH wrapper (per the runbook).
The wrapper's default remote is stale (ely-beauty) — I'll pass `--remote` explicitly. No `ssh` binary → deploying the paramiko shim per the runbook. Setting up the key and shim.
Dry-run clean — fast-forward `67512bf1..6e2c0336`. Real push now.
P21 周期已完全交付并推送。**远程 `main` 分支 @ `6e2c033` == 本地 HEAD，密钥已销毁，代码树整洁。**

**执行摘要（全部经过实测验证）：**
- **基线完全复现**（950P · 627/627 · tsc 0 · eslint 0E/0W · e2e 40/40 · rls 13/13 · 移动端导航 17/17 — 第 12 次运行确认无 Tailwind v4 bug · prod-CSP 5/5）
- **审计**：3 个并行深度审计 → 0 严重 / 2 高 / 20 中 / 15 低；每个 High 级别问题均已在源码中手动验证
- **已修复 (TDD, 33 个 RED-first 测试)**：列表包络统一（每个列表端点都为 `{results, count}` — 分页的前提条件 + 修复了无效的 RLS 断言）、InvoiceNow `invoicenow_sent_at` 证据戳、`on_commit` 缓存真实性（包括作废/手动条目失效）、银行账户默认标志锁定、`ValidateBalanceView` 400s，以及完整的银行 a11y 批次
- **最终门禁**：后端 **969P/0F/5S** · vitest **641/641** · e2e **40/40** · rls 13/13 · 移动端导航 17/17 (第 13 次) · prod-CSP 5/5 · 8 个 DOM 验证的截图 (128-135)
- **文档**：API 指南 3.2.0，包含 P21 附录，完成了 DEPLOYMENT/README/CLAUDE/AGENTS/PAD/SKILL 的全面梳理，`.env.example` 已验证符合实际情况

关键工件：[P21 plan](/home/z/my-project/ledgersg/docs/REMEDIATION_PLAN_2026-11-27_P21.md) · [P21 report](/home/z/my-project/ledgersg/docs/REMEDIATION_2026-11-27_P21_REPORT.md) · [session log](/home/z/my-project/ledgersg/docs/session_42.md) · [worklog](/home/z/my-project/ledgersg/worklog.md)

建议的下一步：进行 P22 周期以实现**列表分页**（其前提条件现已完成 — `LedgerView` 行实现是第一个目标）以及 ruff 机械化批次（936 个生产环境发现）。
