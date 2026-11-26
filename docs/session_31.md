我将首先加载工作区状态，并按照您的运行指令（六阶段工作流：分析 → 规划 → 验证 → 实施 → 验证 → 交付）来建立任务计划。
工作区已重置。正在先通过 HTTPS 克隆仓库（SSH 推送稍后进行）：
仓库已克隆。正在读取核心文档 —— 先检查文件大小，以便完整阅读它们：
AGENTS.md 很大 —— 正在分块读取：
AGENTS.md fully read. Now reading CLAUDE.md, Project_Architecture_Document.md, and ledgersg_SKILL.md:
已内化核心文档。现在开始读取 README（状态部分）和会话/审计/修复文档：
关键发现：`partial_p14_remediation_changes.txt` 记录了提交至错误路径的 P14 修复，且 session_29 揭示了提交 `2bcb43f0` 损坏了 `payment.py`（模型被序列化器代码覆盖）。现在正在检查 4 个 "update session log" 提交以及代码库的实际当前状态：
The repair work described in session_29's second half was never actually committed — only session log docs were. The codebase should still be in the corrupted state from `2bcb43f0`. Verifying:
Corruption confirmed. Now reading the P13 report, both independent audits, and the P14 plan:
我现在已经掌握了完整的信息。让我更新一下进度，并验证来自 `2bcb43f0` 的确切损坏情况 —— 检查该错误提交之前 `payment.py` 的内容，以及正确的文件布局：
Now mapping the full damage. Comparing the corrupted `payment.py` with the real banking serializer, and checking what the correctly-placed modified files reference:
The corrupted payment.py = the real serializer + the stranded H-2 fix. Now checking what the misplaced tests import and what the correctly-placed modified files reference:
Full damage map established. Now checking whether the backend boots (the documented circular import), and the remaining service diffs:
Circular import confirmed (`models/__init__.py:22` → corrupted `payment.py` → imports back from `apps.core.models`). Reading the misplaced P14 fix modules:
Good — the stranded fixes are quality work needing relocation. Now reading operational docs: skills catalog, PG setup script, rootless-postgresql skill, and Tailwind V4 report:
SSH 流程已理解。现在开始环境设置 —— 首先使用仓库的脚本进行 PostgreSQL 设置：
PG 17 已启动。正在创建 LedgerSG 角色和数据库，然后加载 schema。首先检查 session_29 中提到的扩展固定（extension-pinning）问题：
身份验证挂起 —— psql 正在提示输入密码。使用 socket（信任认证）代替：
Schema 已成功加载。正在针对预期验证 RLS 状态（应仍为 pre-§17 = P14 H-6 差距）：
H-6 gap confirmed (5 tables with org_id lack RLS). Now checking Redis setup procedure from DEPLOYMENT.md:
Redis 已启动。正在并行构建后端 venv 和前端 node_modules：
Chromium installed. Now reproducing the corruption evidence — the backend boot failure (documented in session_29, never landed as a fix):
Corruption confirmed live on `main`. Running frontend baseline to confirm it's healthy:
前端基线全部通过（tsc 0, vitest 530/530, eslint 9 已记录）。正在检查 playwright config，然后编写 P15 计划：
Playwright config 已完善。正在检查剩余的基础设施——worklog 尾部、已提交的脚本以及 e2e bootstrap 差距：
在计划之前 —— 正在根据权威来源验证 IRAS GST 注册号格式（M-form regex 中的开放设计决策）：
导航占据了大部分页面。让我查询 OECD TIN 指南和一个具体的格式来源：
OECD guide confirms ASGD = ANNNNNNNC (9 chars). Verifying with one more source since 10-char M-forms also appear in the wild:
已收集真实世界的证据（M90356174N = M+8 位数字+字母，10 个字符；OECD ANNNNNNNC = 9 个字符）。两种 M-form 长度均存在。正在检查提交的 P14 测试对 M-form 的期望：
Both M-forms must validate (matches test expectations and evidence). Now checking package.json scripts, then writing the P15 plan:
All infrastructure verified. Now writing the comprehensive P15 remediation plan:
Now validating the plan against the codebase before execution — diffing the misplaced files against their canonical targets:
已确认两个搁浅修复方案均为精细插入。现在开始检查视图连线缺口（`override_reason`、`related_document_id`）：
Plan validated against the codebase — all targets confirmed. Updating todos and starting Phase 0 (tree repair):
**Phase 0.1** — Restoring the real Payment model:
**Phase 0.2** — Porting the stranded H-2 serializer fix into the canonical payment serializer:
**阶段 0.3–0.6** — 搬迁搁置的模块（period_lock、validators，包含 M-form 修复），并将 C-1 和 C-2 修复内容移植到规范服务中：
Creating `apps/core/validators.py` with the M-form regex fix (both OECD 9-char and real-world 10-char forms):
Now porting the C-1 fix into the canonical organisation service:
Now porting the C-2 + H-05b fixes into the canonical return service (4 surgical insertions):
Now the notes persistence (4th insertion) after the status update:
**Phase 0.7** — Fixing the committed RED test's ValidationError import, then deleting the misplaced files and checking the backend boots:
Backend boots (only the documented W001). Fixing the test-side ValidationError import:
Now running the interim full backend suite to map the honest RED state (per plan 0.9):
Excellent progress — C-2 (filed immutability) and H-1/H-2 (allocation) tests are GREEN after the ports. 34 remaining failures map to Phase-1 scope. Diagnosing the first groups:
Three diagnoses confirmed. Fixing the production ordering bug first (unknown-box validation must precede the override-reason gate):
现在正在修复 RLS 一致性测试的两个测试端 bug（Django-infra 扫描 + 递归 spy）：
Fixing both test-side bugs — the sweep (intersect with tenant tables) and rewriting the recursion-prone spy as a seed-wrapper probe:
C-1 mechanism + tieout ordering fixed. The 2 remaining RLS failures are the honest RED for §17. Diagnosing the period-lock fixture errors:
Fixture bug: the conftest already creates a FY2024 starting 2024-01-01. Checking the conftest fixtures and the approve-path requirements:
正在修复 fixture 以复用 conftest 中现有的 FY2024/1月：
H-3 guard works (journal + void refusals pass). The approve-path tests need the canonical approve method — checking it:
The fixture invoice needs document lines (session-29's lesson). Checking the InvoiceLine model:
The fixture's return dict lacks the `tax_codes` key — adding it:
All 4 period-lock tests GREEN — H-3 fully proven. Diagnosing the input-validation group:
修复测试类（django_db 标记 + 根据 session_29 的分析，将错误的序列化器目标更改为 GSTRegistrationSerializer）：
现在实现 M-1 接入（RED 测试已存在）。首先是 serializers：
现在进行 ContactService._validate_uen 的委托：
现在正在修复输入验证测试文件（`django_db` 标记 + `serializer` 目标）：
M-1 GREEN (23 passed). The 6 remaining are the honest RED for M-4. Implementing the line schema (GREEN):
Now the view forwarding (lines already present; adding `related_document_id`):
M-4 + H-4 + H-5 all GREEN (38 passed). Diagnosing the viewer gates (M-5):
实现 M-5 —— 共享权限辅助程序 + 四条路径的连接：
Two test-side bugs (missing doc sequence + serializer requirements). Checking ContactCreateSerializer requirements:
测试的纯组织需要植入 CoA（联系人服务会解析 AR/AP 控制账户）+ 发送测试所需的文档序列。正在修复辅助程序：
M-5 GREEN。现在开始进行 H-04b (NRIC 掩码) + H-05b (序列化器暴露) 的诊断：
Implementing H-04b masking in the serializers + the echo guard:
Removing the accidental duplicate import, adding override_reason to the file serializer, and fixing the tests' org context:
通过适当的 fixture bank GL 和 org context 修复这两个 create-path 测试：
Adding `override_reason` to GSTReturnFileSerializer and wiring the view:
H-04b + H-05b GREEN (9/9). Now X-1 — the hardened XML parser:
lxml doesn't expose flags — implementing the policy constant design (session-29's lesson) + the hardened parser:
Cleaning up my sloppy CreditNote block:
Now updating the config-gate test to assert the policy constant (lxml can't be introspected):
X-1 已通过。现在进行 P11 测试更新（H-4 合约变更影响）：
Updating the P11 tests to the new H-4 contract:
所有 P11 测试已更新并变绿。进行完整的中间套件检查：
The 4 remaining failures are test fixtures using invalid GST/UEN formats (the old lax contract). Updating them to real formats:
Only §17 remains. Studying the schema's RLS section structure before writing §17:
现在编写 §17 —— RLS 补全补丁（幂等，v1.2.0）：
将 §17 应用到两个实时数据库并运行一致性门控：
The pin IS live — psycopg returns proconfig as an array, not a dict (session-29's exact finding). Fixing the test normalization:
Removing a nonsense line I generated:
**Backend FULLY GREEN: 828 passed / 0 failed / 5 skipped.** Checking M-10's test status before committing:
M-10 has no committed test — writing the RED test first (TDD):
RED 已确认。正在实施 GREEN 去重：
831 通过。现在进行 H-8 — 通过包管理器进行依赖升级：
后端已基于升级后的依赖环境变绿。正在更新 pyproject 清单：
现在进行前端升级（next, zod）：
0 vulnerabilities. Verifying the dev tree wasn't pruned (session-29's trap) — running the full frontend gates:
陷阱已确认 — 正在恢复完整的开发树：
All frontend gates green on Next 16.4.6 + zod 4.6.7. Now H-9 — the Docker key + service.py gates:
H-9 已确认。正在检查现有的 `settings-gate` 测试约定（生产模式）：
正在编写 H-9 RED 测试（service.py 门禁），遵循 settings-gates 约定：
RED 状态已确认（3 个新失败）。正在实现 service.py 的门控机制：
现在进行 Dockerfile 密钥生成修复：
H-9 已完成。现在进行 F-A —— e2e 引导程序的修复：
Wiring 已确认。正在应用 F-A 修复 — ensureDemoActivity 会创建返回：
接下来是 e2e 合约修复 (F-B)。检查 p11 CN 创建和 p10 UEN：
Applying the p11 CN contract fix (related_document_id + cap headroom):
现在处理 p10 UEN 修复 (F-B d)：
现在 F-B(a) —— 单次运行刷新（single-flight refresh）。正在读取当前的 `api-client` 刷新逻辑：
正在检查 `api-client` 的测试约定，然后编写 `RED` 单次执行（single-flight）测试：
RED 已确认。正在实现单次请求（single-flight）修复：
The single-flight works (one refresh logged) but my test's mock logic is off. Checking hasSessionEvidence:
修复方案非常有效 —— 我测试的 mock 计数器有误。正在使用已验证的模式重写该测试：
我的调用编号计算有误 —— 重试占用了第 3-4 次调用，因此“稍后的 401”是第 5 次调用：
单次运行 GREEN。正在检查针对 C-1/H-7 实时验证的 rls_smoke 脚本（计划 1.7）：
Applying the four session-29 smoke fixes (UEN/GST generators, bank GL, approve path, gl_account field):
Running the complete backend gate, then committing Phase 0+1:
Lint parity: 180→181 (1 new finding). Finding and fixing it:
重要提示 — F811 揭示了我重复定义了一个现有的序列化器（即“第二次定义静默胜出”的反模式）。正在检查：
The existing serializer at line 112 must be upgraded in place — removing my duplicate and merging the M-4 bounds into the canonical one:
Lint parity improved (27→25). Suite green at 834. Committing Phase 0+1 as logical conventional commits:
6 commits landed. Phase 2 — the live gate. Checking the daemonize script and the ledgersg_app role setup:
正在启动守护进程化的开发栈（通过 :8000 端口的超级用户后端 + 通过 :3000 端口的前端）：
Stack live. Running the C-1/H-7 live proof — the full walk as `ledgersg_app` on :8001:
C-1 已通过线上验证（201 as app role！）。诊断 403 联系人：
找到了——§17c 的角色策略阻止了中间件在上下文之前的角色读取（`select_related` 连接被过滤）。正在将 role 修改为 NULL 上下文的 SELECT（与 17b 记录的折中方案相同）：
联系已修复。银行账户步骤返回了非 JSON 格式内容 —— 正在检查端点和响应：
URL 为 `bank-accounts/`，而非 `accounts/`。正在修复 smoke script：
**13/13 个步骤已按 `ledgersg_app` 验证通过** — C-1/H-7 已实时验证。现在进行跨租户隔离的实时断言：
0/0 是一个弱证明 —— 使用一个包含实际数据的组织重新进行：
应用角色在无上下文的情况下无法看到任何联系人（默认关闭）。正在使用超级用户获取组织 ID 以进行探测：
RLS 已完全实时验证（上下文中：仅限 own-org；无上下文：对所有人 fail-closed；审计：append-only）。正在提交策略优化，然后引导演示并为实时 e2e 做准备：
Banking 单独测试通过 — full-suite 竞态条件。正在检查 helper：
Line 70 is the login — a rate-limit artifact (the register throttle is 5/hour and I've been running registrations). Flushing the dev cache and re-running:
**LIVE E2E: 40P/0F/0S — fully green!** Now the GST live spot-proof and the mobile-nav probe:
The probe needs authentication first (session-29's finding — login page has no aside). Fixing the script:
P13 已知的时间细微差别——可见性转换在滑出过程中保持抽屉可见（session-29 在更长的等待时间下已验证过）。正在修复探测等待：
**17/17 mobile-nav checks PASS — the nav works, no Tailwind v4 bug** (settled live for this session). Now the screenshots:
Two h1s per page (logo + title) — my `.first()` grabbed the logo. Fixing to use the page title h1:
All 8 captured. Verifying pixel dims + uniqueness per the repo convention:
根据视觉检查范围，从视觉上确认导航界面（移动端导航已打开）：
Screenshots verified. Running the final frontend gates (full vitest + coverage + default e2e):
覆盖率检查通过 (532/532，两个棘轮值均显示绿色)。默认 e2e（无后端环境变量）：
All gates green. Now the .env.example truth pass:
Templates are current — one stale count in the web template. Fixing, then committing the screenshots + scripts:
接下来是文档。首先检查 `DEPLOYMENT.md` 中需要更新的内容：
正在将 P15 更新应用到 DEPLOYMENT.md：
DEPLOYMENT.md 已完成。现在进行 API_CLI_Usage_Guide.md 的对齐：
API guide done. Now the status docs truth pass (README, CLAUDE, PAD, AGENTS, SKILL):
Lessons added. Now writing the P15 report:
接下来是 session log 和 worklog：
文档提交与安全检查：
The pyproject pin updates missed the H-8 commit — committing now:
10 个干净的提交，代码树干净。正在设置 SSH 推送 —— 密钥文件、SSH 二进制文件检查、paramiko 垫片：
正在部署 paramiko ssh shim（根据 runbook 附录 A 的设计）：
试运行通过（快进 10 个提交）。执行正式推送：
该 shim 在二进制 pack 数据上进行文本模式读取（导致代理字符错误）。正在将桥接切换为二进制模式：
**Push successful — remote verified at `5af9b51d` == local HEAD.** Cleaning up (key shred, daemon teardown, remote verification):
密钥已按设计销毁——包装器自身的推送后验证（"remote verified: refs/heads/main @ 5af9b51 == local HEAD"）是权威的检查。通过 HTTPS 进行独立确认：
全部完成。最终验证：远程 `main` 分支位于 `5af9b51d` == 本地 HEAD，代码树整洁，密钥已销毁。

## 会话总结

**发现**：来自被中断的 session-29 的提交 `2bcb43f0` 破坏了 `main` —— 真正的 `Payment` 模型被序列化代码覆盖（后端甚至无法运行 `manage.py check`），而 P14 修复程序被遗留在错误的路径上。

**已交付（P15 冲刺，10 次提交，已推送）**：
- **代码树修复** —— 模型已恢复，所有滞留的修复已迁移；修复了 RED 测试套件中的 5 个测试端 bug
- **P14 已完成** —— FILED 返回不可变性 (409)，GST 周期锁定，关联+限制的贷记单，分配限制 + 分期付款，输入验证器（研究了 M-form：接受两种记录的长度），行项 400s，NRIC 掩码，Viewer 只读，XXE 加固，税务代码去重
- **Schema v1.2.0 §17** —— 每个租户表均启用 RLS，仅追加审计日志，已固定 `search_path`
- **运行时角色关卡实时验证** —— 完整入驻路径为 `ledgersg_app`：**13/13 个冒烟测试步骤通过**（组织创建返回 201，扭转了审计的 500 报错），故障关闭隔离
- **安全升级** —— Django 6.0.10, DRF 3.18.3, Next 16.4.6, zod 4.6.7：**零已知建议**；Docker 密钥加固
- **单次运行刷新**（轮转竞争导致会话中断）
- **移动端导航：17/17 实时检查 —— 正常工作，无 Tailwind v4 bug**

**最终关卡**：后端 **834P/0F/5S** · vitest **532/532** · 实时 e2e **40P/0F** · 覆盖率/eslint/构建通过（绿色） · 8 张已验证的截图。

关键文件：[P15 计划](/home/z/my-project/ledgersg/docs/REMEDIATION_PLAN_2026-11-26_P15.md) · [P15 报告](/home/z/my-project/ledgersg/docs/REMEDIATION_2026-11-26_P15_REPORT.md) · [DEPLOYMENT.md](/home/z/my-project/ledgersg/docs/DEPLOYMENT.md) · [工作日志](/home/z/my-project/ledgersg/worklog.md) · [截图](/home/z/my-project/ledgersg/docs/screenshots/)。

**下一步建议**：P16 事项（UEN 校验和、H-3 DB 触发层、H-05b 附件模型）已在报告的递延登记册中登记。
