Let me read the key documentation files systematically. I'll start with the most important sections.
I have a clear picture from session_35.md — that documents the completed P17 sprint. Now let me set up the task plan and continue with the remaining reviews.
Now let me validate the codebase state and environment (sandbox recycling kills processes but keeps files).
Environment is alive (PG 17, Redis, backend on :8000, next dev). Let me verify health and venv state, then reproduce the documented baselines.
Environment fully intact — `ledgersg_app` uses the schema placeholder password as documented in the P17 report. Now let me reproduce the documented baseline gates.
All baselines reproduce exactly (882P/5S, vitest 582/582, tsc 0, eslint 0E/5W). Now the mobile-nav live probe and the skills catalog review.
Mobile nav: 17/17 PASS — the documented "no Tailwind v4 bug" verdict re-settled live. Now let me review the audit-relevant skills the user named, then check recent changes.
All baselines green and the named mobile-nav focus settled. Now launching the three parallel deep audits (the repo's established pattern), scoped to the P17 diff plus the deferred register.
Three audits complete: 0 Critical / 3 High / 20 Medium / 20 Low. Per audit discipline, let me hand-verify every High and the key Mediums in source before planning.
All High findings verified in source. Let me gather the remaining facts for the plan (globals.css tokens, npm availability, button hover tokens).
Registry reachable; all facts gathered. Now writing the P18 remediation plan following the repo's convention.
Plan saved. Now the validation pass — verifying every plan anchor against the tree before executing.
All plan anchors verified against the tree. Now executing **Phase 1 — BE-H1 (statutory-record locking)**, TDD: RED first.
Now writing the BE-H1 RED tests (the P17 test conventions — spy probe + sequential pin).
RED confirmed for both lock probes. Fixing the FK hack in the review test (`reviewed_by` must be a real user):
Now the GREEN fix for BE-H1 — reading the full service context first:
BE-H1 GREEN (4/4). Now **BE-M2 — unallocate/unreconcile locks**. Reading the full methods first:
Now adding the BE-M2 RED tests to the P18 test file:
Missing the fixture import (the P17 pattern imports it explicitly):
RED confirmed for both BE-M2 probes. Now the GREEN fixes:
I need to preserve the `ResourceNotFound` contract and avoid double-locking via select_related:
Now the unreconcile lock fix:
BE-M2 GREEN (6/6). Now the invoicing batch — BE-M4/M5/M6. Reading the current code:
Proper RED (only the lock probe). Now the BE-M4 GREEN fix:
BE-M4 GREEN. Now **BE-M5 + BE-M6** RED tests:
Now the BE-M5 GREEN fix — restructure `add_line` with lock + atomic + typed IntegrityError (scripted re-indent for reliability):
The anchor must match post-re-indent spacing (12 spaces). Fixing:
BE-M5 GREEN. Now **BE-M6** — locking the original in the credit-note cap check:
The lock must hold through the cap read — wrapping the entire validation body:
Now moving the validation call inside `create_document`'s atomic block:
BE-M6 GREEN (19/19 with regressions). Now **BE-M3 — header/archived account posting gate**:
Proper RED (DID NOT RAISE). GREEN fix — the account gate in `create_entry`:
Now the `archive_account` lock (BE-M3's second half):
BE-M3 GREEN. Now **BE-M1 — the three Peppol task bodies**. Reading them:
Writing the BE-M1/L3/M7 RED tests (new file, P17 conventions):
The on-commit test needs pytest-django's `django_capture_on_commit_callbacks` (the TestCase outer transaction otherwise defers callbacks forever). Rewriting that class:
All proper RED. Now the GREEN fixes for the three task bodies:
Now the email task's permanent-failure classification (BE-L3):
All Celery tests GREEN (9/9). Now the remaining backend L batch — BE-L2/L5/L6/L4:
Now writing the L-batch RED tests (BE-L2/L5/L6/L4):
4 RED confirmed. Applying the four GREEN fixes:
All Phase 1 backend fixes GREEN. Running the full backend suite for regressions:
5 failures — pre-existing tests pinning the old contracts. Examining each:
All 5 pin the old (broken) contracts. Updating them to the new contracts with documentation:
**Backend fully green: 909P/0F/5S (+27 P18 tests)**. Now Phase 2 — schema §15c completion (v1.2.2):
Writing the §15c gate test (RED), then the schema change:
All 5 RED. Now the schema §15c completion — checking FK conventions first:
Now applying the schema §15c completion (v1.2.2):
Now reloading the schema into both local DBs (idempotent) and running the gate tests:
The reload exposed a real problem — `django_admin_log` didn't get created. Investigating:
The full-file run must have aborted before §15c. Re-running with errors visible:
Index names can't be schema-qualified in `CREATE INDEX`. Fixing:
**Backend: 914P/0F/5S.** Now Phase 3 — the frontend batch. Checking the existing test conventions:
The pairing tests pass suspiciously fast — the grep isn't finding anything. Debugging:
Found it — the path resolves one level short (`src/src`). Fixing the test:
The wash forms (`bg-alert/10`) need exclusion — only opaque backgrounds carry the pairing contract:
The variant-merged and decorative cases need exclusion — only explicit foreground classes flag:
Proper RED — exactly the 10 offender lines. Applying all frontend GREEN fixes:
The offender is a CSS comment. Restricting the sweep to code files:
FE-H1/M2/M3 GREEN. Now **FE-M1 — nested Escape**:
Proper RED. The GREEN fix — drawer Escape defers to the open org menu:
FE-M1 GREEN (19/19). Now **FE-L3 + FE-M4**:
Proper RED. GREEN fix — reset the flag on success:
FE-L3 GREEN. Now **FE-M4 — actually sharing the uenSchema**:
FE-M4 GREEN. Now **FE-L1 — the tw-animate-css fix (the real Tailwind v4 class)**. Installing the v4-native package:
Compiling the RED test into the design-token gate:
RED confirmed (9 tests). GREEN — the import in globals.css:
Classic trap — `it` inside the callback is the test function, not the name. Fixing:
All Phase 3 fixes GREEN. Running the full vitest suite for regressions:
The empty-UEN case — the form must keep the old empty-is-valid semantics:
**vitest 601/601 (70 files, +19 P18 tests)**. Now Phase 4 — configs. Measuring hooks coverage for the honest floor:
Ratchet green. Now CFG-L3 (@types/uuid) and CFG-L1 (the CI e2e job):
`uuid@13` ships its own types — `@types/uuid` (stalled at v11) is the mismatch. Removing it:
Now the CI e2e job (CFG-L1). Reading the current CI file:
CI valid. Running the remaining frontend gates (eslint + build):
All code gates at parity. Now **Phase 5 — the docs truth pass**, starting with the `.env.example` files (the user's named deliverable):
Now the DEPLOYMENT.md truth pass — reading the sections with the findings:
Now DOC-M9 (setup_pg_z.sh parametrization) and DOC-L1 (§11 login probe):
Now the README batch:
Now the remaining doc files (CLAUDE, SKILL, PAD, Makefile, AGENTS):
Now adding the P18 addendum to the API guide:
Now restarting the backend on the remediated code and re-bootstrapping the demo substrate (the schema reload wiped it):
Demo substrate bootstrapped (user + org). Now the live e2e gate — first run self-bootstraps the activity:
The backend died mid-run. Investigating:

所有 P18 修改都完好地保留在工作区中。现在让我调查一下后端崩溃的问题——检查一下后端日志。
后端已于 07:54 重启并提供了健康检查服务。让我看看 07:54 之后发生了什么——即 e2e 门禁运行本身——并检查当前的端口状态。
后端日志在第 50 行（健康检查为 200）后突然结束，没有关闭回溯信息 —— 听起来很像是被 OOM 终止了。让我确认一下，并检查最后一次 e2e 运行状态。
最后一次 e2e 运行失败，有 26 个测试失败——全部是后端崩溃导致的连锁反应（无 OOM 日志条目，但运行中途后端停止了响应）。我的调查结论是：后端进程静默终止了。让我检查一下内存压力（可能的原因），然后重启它并重新运行 gate。
The plan is intact and memory is the likely culprit: 4.1GB total, **no swap**, next-dev already eats ~900MB — during the e2e run with parallel Chromium workers the OOM killer reaped the backend. Let me see the plan's tail (verification/commit phases) and the worklog to pin down exactly what remains.
我现在已经掌握了全貌。Phase 1–5 已完成；**Phase 6 仍未完成**：完整的 live gate 重新运行、截图、报告文档以及 commit/push。让我检查一下交付物的当前状态（截图脚本、报告、session_36 文档）以及 playwright config 的内存配置。
Playwright 已经在 live 时设为 `workers: 1` 了，所以问题不在这里。让我检查一下仓库中用于后端长期运行的既定守护进程模式（`scripts/daemonize.py`）以及 e2e gate 脚本。
The daemonizer is the repo's established pattern — the backend must have been started without it (hence mid-run death when the tool-call timeout hit). Let me check the e2e script names and start the backend properly.
现在让我通过 `daemonize` 模式重启后端（使其在工具调用中得以存活），并检查其环境设置。
后端 `.env` 已就绪。现在通过 `daemonize` 模式重启后端：
Backend is daemonized (PID 426) and healthy. Let me set up the remaining-work TODO list, then verify the demo substrate before running the gates.
psql 卡在密码提示符上了。让我检查一下 rls_smoke.py 所使用的连接模式（已确立的模式）：
rls_smoke 需要在 :8001 上运行一个独立的 `ledgersg_app` 后端。现在让我使用 .env 凭证来验证基底：
尽管健康检查显示正常，但 `core.users` 却丢失了——健康检查只运行了 `SELECT 1`。让我检查一下 schema 的状态：
`core` schema 存在且有 10 张表，但 `core.users` 缺失。让我列出其中实际包含的内容：
尽管设置了超时，查询还是莫名其妙地挂起了。让我用更严格的限制重试一下：
表使用的是 SQL-First 蛇形命名法（`app_user`，`organisation`）——我之前的查询有误，DB 是正常的。现在正在检查 demo 基板：
演示基础数据为空——第一轮 e2e 运行（后端崩溃的那次）可能清除了它，或者自建（self-bootstrap）过程在中途失败了。让我检查一下 e2e 测试是如何自建数据的：
e2e 测试需要一个已存在的演示用户 (`demo@ledgersg.sg`/`demo1234`)。我来检查一下 `auth.spec.ts` 是否自行引导了它：
规范需要预先存在的演示用户。会话日志显示基础数据已引导——让我找一下 DEPLOYMENT.md 中的引导约定：
后端日志中没有发现 `register POST` 请求 —— 基础数据（substrate）的引导可能是通过脚本执行的，或者尚未提交。让我搜索一下引导脚本：
引导脚本已存在。让我检查一下它的上次运行结果，并查明为什么数据库（DB）是空的：
谜团已解：注册在 05:58 成功，但随后的 schema v1.2.2 重载清空了数据行；会话结束后的重新引导从未实际写入后端（07:54 重启后的日志中没有请求）。现在正在针对健康（已守护进程化）的后端执行引导：
Substrate verified: 1 user, 1 org, 102 CoA accounts seeded. The backend is now properly daemonized (survives tool calls — that was the earlier failure mode). Now let me verify the frontend dev server and launch the full e2e gate detached:
两个服务器都运行正常。正在后台启动完整的 e2e 测试：
E2e 已启动。在它运行的同时，让我来编写 session-36 的截图脚本（基于既定惯例的 session34 模式）。首先，让我研究一下 session34 的捕获脚本，以遵循其结构：
运行静默终止了——日志为空，且没有 playwright 进程。让我直接运行它来诊断：
运行正常，但测试 6（银行支付结算）很快失败 —— 可能是全新的 DB 缺少 bootstrap 活动依赖。让我检查一下 banking.spec 的具体需求：
该测试依赖于 `ensureOutstandingInvoice` 辅助函数。让我阅读一下它，看看它是为什么会快速失败：
Root cause identified: banking test 6 needs a **contact** to exist, but on a fresh DB the contact is only bootstrapped by the p11 spec (which runs alphabetically *after* banking). The documented fix: bootstrap the activity first (p11's `ensureDemoActivity` is idempotent), then the full suite goes green. Also, the earlier nohup death shows I must use the repo's `daemonize.py` for process survival. Launching the combined run (p11 bootstrap → full gate):
已后台运行（PID 1494）。在等待期间，让我研究一下 session34 的截图脚本，以构建 session36 的对应脚本：
现在让我检查一下这三个 P18 contrast-fixed surfaces，以构建准确的 DOM truths 用于截图：
Now checking the Radix dialog's animate classes (the FE-L1 restoration surface):
Dialog surface confirmed. Let me check the e2e run progress, then write the session36 capture script:
p11 bootstrap 已完成，完整套件正在运行（测试 12+）。测试 13 (void flow) 显示为跳过 —— 让我检查一下它的跳过条件：
空白跳过（void skip）表明文档状态发生了变化。让我检查一下组合运行中 p11 bootstrap 阶段的输出：
The p11 `ensureDemoActivity` **reuses** an existing contact (DEPLOYMENT.md §9 step 3 must be done outside the specs). My bootstrap only did steps 1–2. Let me read the exact step-3 contract:
现在情况清楚了：联系人必须在 spec 之外存在（步骤 3）。让我终止当前注定失败的运行，检查联系人创建约定，创建联系人，并重新干净地开始：
只有 `name` 是必需的。现在：终止那个注定失败的运行，创建联系人，并重新开始：
Contact created. Restarting the full e2e gate with the complete substrate in place:
运行正在进行中 (PID 3121)。在它执行期间，让我来编写 session-36 的截图捕获脚本，遵循 session34 的约定：
在 e2e 运行期间，让我检查一下 untracked files (P18 新增内容)，并准备 rls_smoke 的先决条件：
已找到占位符密码。现在让我检查一下 e2e 进度和 mobile-nav probe script 的调用情况：
测试已通过 30/40。在等待完成的同时，让我研究一下 P17 报告的结构，以便对其进行仿照：
测试 34 (p11 dashboard GST) 失败。让我看看失败详情：
37 个通过，3 个失败 —— 全部在 p11 的 `ensureDemoActivity` 中：与 PATCH 的联系人往返失败。P18 没有直接修改联系人更新，所以让我手动复现这个 PATCH 以查看真正的错误：
重复的 UEN —— 另一个联系人已经拥有 `T08LL1234A`。让我列出所有联系人：
p10 在不带 UEN 的情况下创建了 "E2E Picked Customer"，但现在它携带了该 UEN —— 这意味着测试 32 的 PATCH 可能是在后续步骤中成功并失败的。让我检查一下所有三个错误：
所有三个都在 PATCH 处失败了，但 E2E Picked 不知为何得到了 UEN。让我查找所有 UEN `T08LL1234A` 的写入者：
只有 p11 会写入那个 UEN。让我检查一下 contacts 的 `created_at/updated_at` 以重建时间线：
已重构时间线：被终止的运行顺序 patch 了 "E2E Picked Customer"（当时是唯一联系人的 `contacts[0]`），在我的联系人生成之前 —— 导致后续运行将 `Demo Trading` 选为 `contacts[0]` 并触发重复项守卫（duplicate guard）。手术式修复：将 `E2E Picked` 的 profile 字段还原为其 `p10` 初始状态，然后重新运行：
让我验证一下 duplicate guard 是否排除了自身（重新运行幂等性）：
Guard 是自排除且幂等的。正在重新运行完整的 e2e gate：
在程序运行的同时，让我先起草报告。首先轮询运行进度：
**e2e:full 40/40 GREEN.** 现在按顺序执行剩余的门控。先从后端 pytest 测试套件开始（已记录的调用方式）：
Backend 914P/0F/5S。接下来是 invariants + security 子集以及 frontend gates：
tsc 0 + eslint 0E/5W。现在进行生产环境构建（同时服务于 CSP 冒烟测试）：
构建成功。现在将 rls_smoke 后端启动为 `:8001` 上的 `ledgersg_app`（已守护进程化），并检查 prod-CSP 冒烟测试的需求：
rls_smoke 13/13. 现在进行 mobile-nav 探测，并检查 prod-CSP 冒烟测试的需求：
mobile-nav 17/17 — 判定结果在 P18 上保持有效。现在进行 prod-CSP 冒烟测试：
prod-CSP 5/5 — **所有门禁均通过**。现在正在捕获 session-36 的截图：
已捕获全部 8 张截图，且已通过 DOM 验证并确认 md5 唯一。让我对两张核心的 P18 捕获图（PAID 徽章 + 动画对话框）进行视觉确认：
当前会话中无法使用 Vision——但 DOM 探针已经通过编程方式验证了表面（badge 计数、animation-name）。让我来运行所需的像素级非空白验证：
所有截图均已验证为非空白。现在开始编写文档。首先，让我研究一下 session_35 的规范：
现在我来检查一下 P17 条目的 worklog 格式：
现在，让我收集报告所需的准确 diff 统计数据，以验证 P18 变更清单：
所有锚点已验证。现在正在编写 P18 报告：
现在正在编写 session_36.md（存储库的 raw-transcript 风格）：
现在是 worklog 条目。让我看看 P17 条目的结尾部分以参考其结构：
现在开始追加 P18 工作日志条目：
工作日志已更新。让我检查一下是否有陈旧的 gate-count 引用（window-1 文档在最终数据出来之前就已经通过了）：
README 和 CLAUDE.md 仍然包含 P17 时期的统计数据。让我查看并更新每一处：
P17 的部分属于历史记录，但 README 的计数表和“当前里程碑”的声明需要 P18 的数据。让我检查一下 README 的里程碑结构和当前状态声明：
README 的 P18 章节在 window-1 中已经存在，并附带了正确的数据。过期的部分是 test-suite 表格和预期的输出注释。让我也检查一下 CLAUDE.md 的结构：
CLAUDE.md 已完全更新至 P18。仅 README 的 current-state 表需要修复：
README 已修复。快速检查 DEPLOYMENT.md 中过期的统计数据：
所有文档现已一致。让我研究一下 P17 的提交系列，以便在 P18 中模仿其主题粒度：
让我检查一下 P18 测试文件的覆盖率，以便按主题对提交进行分组：
让我检查一下那三个修改过的预存测试文件，以便将它们放入正确的提交中：
清晰的分组。在提交之前，让我先研究一下 SSH wrapper 的流程（以便正确规划推送）：
流程已明确。让我检查一下 `ssh` 二进制文件的可用性以及 wrapper 的远程默认配置：
No `ssh` binary — I need the paramiko shim (Appendix A). Let me check the ssh-venv that exists from a prior session and read the shim:
ssh-venv 中已包含 paramiko。我来查找一下实际的 Appendix A shim 代码：
`bin/ssh` 的 shim 已经存在。让我验证一下它是否有效：
shim 运行正常。现在让我来配置 git 并对新文档进行一次最终的占位符检查：
身份配置已就绪，占位符已清理完毕。让我获取完整的文件清单以规划提交（commit）：
Full inventory confirmed. Now executing the 10-commit conventional series (mirroring the P17 pattern), all on main:
`test_query_params_p7.py`（BE-L2 合约的测试侧）之前被遗漏了——现将其作为后续提交：
Working tree clean — 11 commits on main. All gates were executed green this session (only docs changed after). Now the SSH push per the wrapper runbook: key to a 0600 temp file (never inside the repo), shim on PATH, dry-run first:
试运行（Dry-run）通过——身份验证正常，基于 base commit `56f8f835` 干净地执行快进（fast-forward）式更新。正在执行正式推送：
**推送已验证：远程 `refs/heads/main` @ d2c2a08f == 本地 HEAD。** 正在按照 runbook 销毁操作员密钥并进行最终验证：
所有事项均已核实并完成。最终待办事项状态：
P18 冲刺已完成并交付。本次会话从上一个窗口中断的地方继续——当时开发后端在 `e2e` 运行中途意外终止。

**中断的调查（根本原因已解决）：** 后端与工具调用绑定，而非通过 `scripts/daemonize.py` 守护进程化——它在运行中途因调用超时而终止（日志在健康检查处停止，导致 26 个规格的级联故障）。现已进行守护进程化并重新运行；8000 和 8001 端口均已存活。

**此后解决的实时 e2e 问题：** 架构重新加载清空了演示底层（demo substrate）；发现引导程序（bootstrap）需要 `DEPLOYMENT` §9 第 1-3 步（包括联系人，这是 p11 辅助程序复用而非创建的内容）；之前被中断的运行导致演示 UEN 滞留在错误的联系人上，从而触发重复防护（duplicate guard）——已进行精细化重置，经验证该防护是自排除的（幂等重新运行）。

**最终门禁矩阵（全部实际执行，全部通过）：** 后端 **914P/0F/5S**（不变性 34P，安全性 83P/3S）· vitest **601/601** · tsc 0 · eslint **0E/5W** · build:server 正常（绿色）· **e2e:full 40/40** · **rls_smoke 13/13（以 `ledgersg_app` 身份）** · **mobile-nav 17/17**（无 Tailwind v4 mobile-nav 错误——已第 7 次确认）· **prod-CSP 5/5** · schema **v1.2.2**。

**交付物：** 8 张经过 DOM 验证的截图（`104-111_*_session36.png`——已配对的 PAID 徽章、设置徽章，以及计算样式为 `animation: enter 0.2s` 的已恢复动画对话框）、P18 报告、`session_36.md`、工作日志条目，以及在窗口 1 中传递的 `.env.example`/文档核对更新。

**已推送：** 11 个符合惯例的提交（`a5d186ac..d2c2a08f`），通过 `ssh_git_wrapper_v3.py` 推送至 `main` 分支——远程引用已由包装器和 GitHub API 验证为 `d2c2a08f`，两个临时密钥均已销毁。工作树干净，与源同步。

建议的下一步：启动一个新的审计会话（P19）以处理延期登记册——最大的项目是 `ContactPicker` WAI-ARIA 组合框（combobox）、应用内的未保存工作路由守卫（unsaved-work route guard）以及后端列表分页（list pagination）。
