我将首先设置工作空间并克隆仓库，然后系统地处理这个多阶段任务。
Repo cloned successfully on `main`. Let me set up a task plan and start reading the key documents.
Now let me read the core documentation files. Starting with the smaller key docs.
Now let me read AGENTS.md and ledgersg_SKILL.md.
Now let me read ledgersg_SKILL.md and the session documents.
Let me read the original skill file directly in manageable chunks.
Core docs read. Now the session documents.
I have a good picture of P6. Let me read the rest of the worklog and the skills catalog + PG setup docs.
Now let me read the skills catalog, PG setup script, and SSH wrapper documentation.
The wrapper needs a `--remote` override for ledgersg. Now let me validate understanding against the codebase structure.
The codebase matches the documented state: reports/quotes remain template shells (P7 candidates). Now let me set up PostgreSQL.
Fresh environment. Let me install rootless PostgreSQL using the repo script.
TCP connection hung awaiting password. Let me use socket + PGPASSWORD properly.
Role and DBs exist. Now load the schema with the password set.
Schema v1.1.0 verified (47 NUMERIC(19,4) columns, seeded SR rate history, 30+2 tables). Now Redis.
Need liblzf (as noted in worklog). Let me download it.
Redis is up (PONG). Now backend venv + frontend deps.
Check passes (1 known W001). Now reproduce the documented P6 baselines.
150 failures — environment issue. Let me diagnose.
The reaper killed Redis between invocations (documented lesson). Let me create a resilient helper script.
Backend baseline reproduced exactly: **588 passed, 5 skipped**. Now frontend baselines.
All P6 baselines reproduced exactly (588P/5S backend, 383/383 vitest, 0 typecheck errors, 9+11 e2e). Now the audit phase.
Scanner output matches the documented FP profile. Let me analyze criticals scoped to `apps/` (excluding `skills/`).
Let me verify these criticals are the documented false-positive classes.
Scanner criticals confirmed as documented false-positive classes (hardcoded schema names, docstrings, test fixtures). Now the focused manual audit of recent P6 changes.
让我检查一下 OVERDUE 状态是如何与分配（allocations）交互的——这可能是一个类似 F-4 的死胡同。
Two dashboard services exist. Let me check which one is live and find the payables gap.
The live dashboard is `apps/reporting` (frontend calls `/reports/dashboard/metrics/`); the core one is a duplicate surface. Let me audit the live reporting service closely.
Let me review the remaining P6 backend surfaces — unallocate, payment JE, and the ledger view.
Confirmed a real crash path (payment on bank account without gl_account). Let me dispatch parallel audit agents for breadth while I review configs.
Outstanding audit results. Let me verify the highest-severity findings myself before planning.
All key findings verified. Let me check the remaining artifacts I need to plan around: DEPLOYMENT.md, .env.example, shadowed urls.
Let me verify the dead-code claims before finalizing the plan.
All verification complete. Now let me write the P7 remediation plan.
Plan saved. Now validating the plan's assumptions against the codebase before executing.
All plan assumptions validated. Now executing the plan — starting with Task 1 (F-2): status-transition authorization. Let me study the test patterns first.
Now writing the RED tests for Task 1. Let me check the invoice workflow test structure first.
Test fixture field name issue. Let me check the model fields.
RED confirmed — but my "without permission" tests must use a limited member, not the owner client. Let me fix the test harness.
Now the GREEN phase. Let me view the current view code and implement the fix.
Now update the serializer to a ChoiceField and check the ValidationError import:
The handler works in isolation but returns None in the request path. Let me debug empirically.
**Root cause found** — a new pre-existing bug: `base.py` uses the wrong DRF settings key (`DEFAULT_EXCEPTION_HANDLER` instead of `EXCEPTION_HANDLER`), so the custom exception handler has NEVER been active; in-view permission raises produce 500s, not 403s. Let me fix it.
Now let me add a settings-gate regression test for the handler resolution, then rerun the Task 1 tests.
Task 1 GREEN including the F-19 root-cause fix. Let me run the full suite for regressions (the handler activation changes 500→4xx mappings).
**595 passed, 0 failed** — no regressions. Let me commit Task 1 and set up the SSH push infrastructure for the incremental safeguard.
Task 1 pushed. Now Task 2 (F-3): org create phantom address — RED test first.
RED confirmed (500 TypeError). GREEN — remove the phantom field:
Task 2 GREEN. Now Task 3 (F-4): fiscal routes — RED first.
Now harden the close views (CanManageOrg + timezone-aware datetimes) and delete the shadowed module:
600 passed. Committing Tasks 2+3 and pushing.
The deletion landed in the F-3 commit (noted for the session log). Now Task 4 (F-5): payment fail-closed. RED first.
The schema enforces NOT NULL — the defect is at bank-account creation (raw IntegrityError 500), not the payment path. Let me verify and adjust the tests to the real contract.
Serializer requires it; only the service path is fail-open. Let me update the tests to the real contract and fix both seams.
RED for the right reasons. GREEN — implement the service validation and payment guard.
Now the payment-path defense-in-depth guard:
604 passed. Committing Task 4, then moving to the frontend tasks.
Now Task 5 (F-7): api-client error envelope. Let me study the current code and write RED vitest tests.
RED confirmed. GREEN — implement the envelope reader:
Task 5 GREEN. Now Task 6 — the void-reason dialog (the Critical F-1 fix). Let me study the current detail client.
Radix dialog is available. Let me write the RED tests for the void dialog first.
Now let me add the void-dialog RED tests to this file and check the hook's current invalidations:
4 RED as expected. GREEN — first the Shadcn dialog + textarea primitives (radix already a dependency):
Now wire the void dialog into the detail client (including the no-org guard from Task 9 and the F-12 catch fix — doing them together since I'm rewriting this file's interaction logic):
Now add the dialog itself at the end of the component (before the closing div):
Now the F-8 ledger invalidation and F-6 hook type fix in use-invoices.ts:
The mutation is called with `(reason, {onSuccess})` — the assertion expects a single arg. Fixing the test:
All green. Now the backend half of Task 7 (F-6): send-view recipient normalization. RED first.
3 RED. GREEN — normalize and validate in the send view:
Now add the InvoiceSendSerializer to serializers.py:
ListField rejects strings before validate_to runs. Need a custom field:
Task 7 complete. Now Task 8 (F-9): payables PARTIALLY_PAID — RED first.
The existing test's docstring claims PARTIALLY_PAID is included — the code never did. RED test:
Task 8 GREEN (41 reporting tests pass). Now Task 9: no-org states + GST flag + shell.
Now the GST flag fix and shell fixes:
Now the shell fixes (nav id, Demo User placeholders, dead New Invoice button):
Now let me add the RED→GREEN vitest tests for the no-org states and run the full frontend gates:
Now the same for settings, plus the InvoiceNow/PDF wiring (Task 12). Let me check the settings test and add the no-org case:
Settings GREEN. Now Task 12: dead-code pass + wire PDF/InvoiceNow buttons.
Now wire the PDF download and InvoiceNow send into the detail page:
397/397 pass but 2 typecheck errors (the known type-green lesson). Fixing imports:
Shell lint findings are pre-existing (parity). Fixing the one new finding — unused import:
All frontend gates green (397/397). Updating .env.example for the deleted server client:
Frontend batch pushed. Now Task 10: settings PATCH validation + permissions.
5 RED. GREEN — typed serializers + CanManageOrg on both views:
Now the serializer and the Peppol view:
The serializer file lacks its import. Fixing:
The two tests encoded the audited insecure behavior. But GET should stay member-accessible — let me gate only PATCH via get_permissions:
616 passed. Now Task 11 (F-11): malformed query params → 400. RED tests first:
6 RED + sanity GREEN. Now the shared helper and view patches:
Ruff improved (119→117), suite 623P. Now Task 13: permission classes + a11y.
624 passed. Now the ledger-table a11y (aria-sort + scope):
Now the e2e additions — void dialog + error message display:
Default e2e green (9 passed + 12 gated). Committing the backend batch (Tasks 10, 11, 13) and the a11y/e2e batch:
All remediation tasks committed and pushed. Now the final verification gates — live stack for e2e:full + screenshots.
All gates green. Now the live phase — one invocation (reaper-proof). Let me check the existing bootstrap/screenshot scripts:
No surviving scripts (fresh workspace). Let me write the bootstrap and screenshot scripts fresh, per the documented contracts.
Bootstrap failed on the revenue account lookup. Let me debug against a live backend:
The bootstrap picks the wrong history row. Fix: resolve via `?effective_on=` (the P2 feature):
18/21 e2e passed, 3 failed on a missing "New Invoice" link — likely my shell change interacting with the spec. Let me diagnose:
The invoices page + my new shell link both match → strict-mode collision. Let me verify and fix the spec to disambiguate:
**e2e:full 21/21 passed + 6/6 screenshots captured.** Let me visually verify the key shots:
All shots verified (1440×900, dark-theme profile, unique). Now the documentation phase — starting with README:
Now the DEPLOYMENT.md rewrite as a detailed fresh-host step-by-step guide:
Now the P7 report, session log, and worklog:
The F-9 payables fix rode the frontend batch commit (git add -A). Let me correct the report's commit list to match reality:

All 8 remediation code commits are pushed. What remains: the documentation batch (in progress), the P7 report (untracked), screenshots, the e2e spec fix, and the worklog/session log. Let me check what's missing.
很好 —— 计划已被跟踪（已提交），截图 35-40 和 P7 报告处于待处理状态。让我检查一下会话日志编号、`worklog` 状态以及测试套件 `config` 变更，以明确具体还剩哪些工作。
我来通过检查之前的会话日志是如何引用它们的截图文件名的，来确认截图/会话命名的约定。
我现在已经掌握了全貌。P7 会话的截图命名为 `session14`，其日志将保存为 `session_15.md`（已确立的惯例：截图使用 N，日志使用 N+1）。让我来制定剩余的工作计划。
未提交的 spec 修复正是使 e2e:full 变为绿色的 strict-mode disambiguation。然而，P7 的提交记录中并没有涉及 vitest/playwright 的配置文件 —— 让我检查一下这些配置的当前状态以及 P7 计划中关于测试套件任务的内容。
配置已通过文档化的项目/覆盖率设置建立。现在我来阅读 P7 计划和 P7 报告，以检查报告的 commit-list 修正状态（这是中断前正在进行的任务）。
P7 报告已存在且内容完整。提交列表中需要根据实际情况进行修正（第 10 项列出了一个不存在的独立 F-9 提交）。让我验证一下 F-9 和 urls.py 删除操作的实际提交归属。
Confirmed: F-9 rode commit `8a5e94a6` (frontend batch via `git add -A`), and the urls.py deletion rode `f56c5ffa` — the report's §5 item 10 lists a commit that doesn't exist and needs correcting. Let me now review the uncommitted doc changes for completeness.
DEPLOYMENT.md 的重写非常详尽。我来检查一下剩余的文档差异。
README diff is complete and matches the evidence. Let me check the remaining doc diffs (AGENTS, CLAUDE, PAD, ledgersg_SKILL).
文档 diff 已完成。让我看看 ledgersg_SKILL.md 的 diff（被截断了），然后验证 frontend gates。
All doc updates are complete and internally consistent. Now let me re-verify the frontend gates on the current working tree (these need no PG/Redis).
类型检查 0 错误，vitest 398/398 —— 与报告完全一致。现在执行默认的 e2e 套件（无后端；Playwright 会自动启动开发服务器）。
Default e2e: 9 passed + 12 gated skips — all three frontend gates match the report on the current tree. Backend is unchanged since commit `c9e42840` (zero backend diffs in the working tree), so the verified 624P/5S stands. Now let me study the session-log and worklog formats before writing them.
现在让我研究一下会话日志格式 (session_14.md)，以便在写入 session_15.md 之前参考它。
The formats are clear. Now let me get precise commit stats for the report's traceability annotations.
现在我已经掌握了所有确切的事实。让我来纠正报告的第 5 节（提交列表），以使其符合实际情况。
报告已修正。接下来是 P7 会话日志 —— `docs/session_15.md`，遵循既定的叙事风格。
现在是工作日志条目——按时间倒序置于顶部，与 P6 条目结构保持一致。
Worklog entry in place. Now let me review the SSH wrapper skill doc before committing and pushing.
The wrapper needs a `--remote` override for ledgersg and the paramiko shim on PATH. Let me verify the shim and key (fingerprint only, never printing the private key).
Shim and key are ready. Now the three final commits, in the order the corrected report §5 documents them.
所有三个提交都在 `main` 分支上，工作区是干净的。在推送前进行快速安全性和内容检查。
The grep matches are just the wrapper's validation constant and docs mentioning the delimiter — no key material. Now the push: shim on PATH, dry-run first, then the real push with the ledgersg remote override.
Dry-run green — the push will carry `c9e42840..3e928e83`. Executing the real push now.
Push succeeded — wrapper verified remote `main` at `3e928e8` == local HEAD. One independent remote check via the shim, then shred the operator key per the runbook.
Key 文件仍然存在（chain 在 shred 之前已停止）。shim 需要 `-i` 参数 —— 让我显式设置 `GIT_SSH_COMMAND`，进行验证，然后进行 shred。
The shred script had a bug (`getsize(f)` instead of `getsize(p)`). Let me re-run the verification and the fixed shred.
Remote and local match exactly — `3e928e83` on `main`, fully synced. Now shredding the operator key.
The P7 sprint is now fully complete. Resuming from the interrupted report correction, I finished the documentation phase and shipped everything:

**What was completed this session**
- **Corrected the P7 report** (`docs/REMEDIATION_2026-11-22_P7_REPORT.md` §5) to match the actual commit graph — F-9/F-6-backend/.env.example traced to the frontend batch commit, the urls.py deletion to F-3
- **Re-verified gates on the final tree**: typecheck 0 errors, vitest 398/398, e2e default 9+12 gated — identical to pre-interruption; backend unchanged since `c9e42840` (624P/5S)
- **Created** `docs/session_15.md` (P7 session log) and **prepended the Session 14 entry** to `worklog.md`
- **3 final commits** (spec fix, docs truth pass, worklog/report/screenshots), pushed via the SSH wrapper
- **Remote verified**: `main` @ `3e928e83` == local HEAD; deploy key shredded

Final state: 12 P7 commits on `main`, all gates green (backend 624P/0F/5S, vitest 398/398, e2e:full 21/21), 6 screenshots, DEPLOYMENT.md fresh-host guide, `.env.example` tracked.

Suggested next steps: the report §3 registers the P8 candidate (real reports/quotes pages) plus deferred items (B6 list envelopes, invoice edit flow, ledger pagination) — ready whenever you want to start the next sprint.
