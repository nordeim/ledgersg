我将从上次会话中断的地方继续。让我首先验证一下工作区和环境状态，因为在会话之间沙箱可能会被回收（进程被终止，文件被保留）。
环境实际上还在运行（PG 17、Redis、后端运行在 ：8000 以及 `next dev` 都处于活跃状态 —— 后端已于 00:43 重启并带有 `--noreload` 参数，很可能是在程序意外中断后）。让我检查一下 Git 状态，并查看会话/修复文档，看看上一次会话具体停止在了哪里。
Git 状态是干净的 —— 上一个会话已经提交了所有内容 (P18 报告、session-36 日志、工作日志、截图，以及最后一个测试侧的修复 `d2c2a08f`)。注意：`docs/session_37.md` 还不存在 —— 这是我将在本次会话中创建的日志。让我阅读一下关键文档，以精确验证项目的当前状态。
太好了——session 36 的日志显示上一次会话实际上已经完成了一切：完整的门禁矩阵已全部通过（backend 914P/0F/5S，vitest 601/601，e2e:full 40/40，rls_smoke 13/13，mobile-nav 17/17，prod-CSP 5/5），已捕获 8 张截图，更新了工作日志，并执行了 “SSH-wrapper 推送到 main” 分支。让我验证一下该推送是否真正同步到了 GitHub 的远端仓库（local-origin ref 可能已经过期）。
远程仓库有一个本地缺失的 commit（`99786f6a`）—— session-36 的推送已经同步（之前远程处于 `d2c2a08f`），但有人在此之后推送了一个新的 commit。让我通过 `git pull` 拉取并检查一下。
仓库所有者推送了 `docs/session_37.md` (190行) —— 我需要审查的新会话日志。我来阅读一下。
这理清了整体情况：`session_37.md` 是**已完成 P18 冲刺的原始记录**（由仓库所有者推送），而不仅仅是中断点。P18 冲刺已完全完成并推送（在 `a5d186ac..d2c2a08f` 之间有 11 个提交，远程已验证）。中断的“后端在运行中死亡”问题已得到解决（根本原因：与工具调用绑定的重启，而非 `scripts/daemonize.py` 守护进程）。日志建议的下一步：针对**延迟登记册（deferred register）进行一次全新的 P19 审计冲刺**（ContactPicker WAI-ARIA 组合框、未保存工作路由守卫、后端列表分页）。

因此，本次会话（session 38）是完整的 P19 周期：审查 → 验证状态 → 审计 → 计划 → TDD 执行 → 门禁 → 截图 → 文档 → 工作日志 → 提交 → 推送。让我来设置待办事项列表并开始。
P18 报告的 §4 延迟登记册是 P19 的待办事项。现在让我审查核心文档（刷新我的理解）和工作日志尾部。让我先检查一下文档大小。
P18 工作日志条目已完成并保持一致。现在让我来审查核心文档——从 `CLAUDE.md`（项目智能体契约）开始，然后是其他文档的关键部分。
`CLAUDE.md` 已完全符合 P18 标准（前端 v0.3.4，后端 v0.6.4，数据库 v1.2.2，所有门禁已记录）。让我从核心文档中提取关键的操作规范（gate 命令、提交/推送约定），然后验证环境。
文档审查确认 P18 状态一致。我来从 Makefile 和 AGENTS.md 中拉取规范的 gate 命令，然后验证环境。
已确认规范的门禁命令。现在让我来验证实时环境和演示基板。
后端运行正常，前端响应正常。我来通过登录端点验证一下 demo 基板（用户 + 组织）。
登录失败——演示基板（demo substrate）可能缺失。让我检查一下 `bootstrap` 脚本和实际的路由。
演示密码是 `demo1234pass`（12+ 个字符以满足注册最低限制），而不是 `demo1234`。让我重试登录并检查基板状态。
登录正常 —— substrate 已存在（用户创建于 08:50，即上一个会话的最终 bootstrap）。让我获取 token 并验证 org/contacts。
连续两次快速登录导致触发频率限制。让我改用脚本方式，只进行一次登录并保存 token。
现在登录返回空响应。让我检查一下实际的 HTTP 状态和后端健康状况。
Login works now (HTTP 200), but I see TWO backend processes (PID 426 from 00:43 and PID 7324 from 01:02). Let me inspect both.
All services verified: dev backend :8000, rls_smoke backend :8001 (as `ledgersg_app`, still alive from the P18 gate run), PG, Redis, next dev :3000. Let me finish the substrate check and then reproduce the documented baselines.
联系人调用返回为空。让我检查一下原始响应，以了解具体情况。
URL 是基于 org-scoped 的：`/api/v1/<org_id>/invoicing/contacts/`。JWT 显示默认的 org-id 为 `21b691c1-738d-4469-96b1-0dbaa97f11bc`。让我确认一下基板（substrate）。
基板已完全验证（用户、组织、2 个联系人、CoA 账户）。环境验证完成。现在让我重现已记录的基线——首先从后端测试套件开始。
后端测试数据库为 `test_ledgersg_dev`（由 `DB_NAME=ledgersg_dev` 自动派生）。让我来运行后端基准测试（每次一个检查点——已知内存紧张是导致之前后端崩溃的原因）。
后端基线已完全复现：**914 passed, 5 skipped**。接下来是前端门控。
所有静态前端基线已复现。现在进行移动端导航检测——用户明确关注的重点（第 8 次实机确认）。
Mobile-nav 17/17 已通过 — 第 8 次现场确认，确认不存在 Tailwind v4 导航错误。所有基准线均已完全复现。现在进入 B 阶段：审计。让我先界定 P18 差异（diff）的范围，然后启动三次并行深度审计。
现在，让我按照仓库既定的模式，启动三项并行的深度审计（Mode C）——后端、前端和横切领域——每项审计都针对 P18 diff 以及 P19 候选范围的延迟登记册（deferred register）。
三项审计已全部完成。综合统计：**0 个严重 / 3 个高危 / 16 个中危 / 22 个低危**。主要发现是 P18 中的一个真实差距：`remove_line` 尽管在提交信息中声称已锁定，但从未被锁定。在制定计划之前，我先在源码中人工核实每一个高危发现（审计准则）。
源码中的所有 3 个高优先级问题均已确认。现在让我研究一下 P18 计划的结构，以便完全参照其编写 P19 计划。
在制定计划之前，让我先抽查一下 Medium 发现结果中的关键锚点。
所有锚点已验证。现在我已经掌握了撰写 P19 计划所需的一切信息。让我开始编写（遵循仓库的 `REMEDIATION_PLAN_YYYY-MM-DD_PXX.md` 命名惯例）。
计划已保存。现在进行执行前的验证——验证剩余尚未直接确认的锚点。
所有锚点已验证 —— 计划与树结构完全一致。现在进入第一阶段（后端，TDD）。让我先研究一下 P18 并发测试文件，以模仿其约定。
P18 测试约定已明确（spy-probe + sequential contracts）。我来检查一下 Celery context test 和 API contract test patterns，然后编写 P19 RED 文件。
在编写 RED 测试之前，让我先阅读一下 `create_return_periods` 和 GST 模型。
已确认约束。让我检查一下进行测试所需的其余 `service signatures`。
现在我将编写 P19 后端 RED 测试文件。
财政年度为 2024 年 1 月。让我修复测试日期和签名。
现在让我运行 P19 测试文件，以确认正确的 RED 状态（因契约断言而失败，而非设置错误）。
4 个测试结果符合预期地显示为红色（RED）。另外 4 个测试需要修复设置 —— 并且 remove_line 测试暴露了更多问题：该服务的 `InvoiceLine.objects.get(id=line_id, invoice=document)` 使用了一个不存在的 `invoice` 字段（模型字段为 `document`），这意味着 remove_line 本身就是损坏的（FieldError → 500）。让我检查一下 peppol log 表中有哪些时间戳可用。
从 RED 尝试中得出的重要发现：(1) `transmitted_at` 为 `NOT NULL DEFAULT NOW()` + `auto_now_add=True` —— **NULL-PENDING 行不可能存在，因此审计的 BE-L1 发现无效**（已在源码中验证）；(2) `savepoint_state` 在 Django 6 中是一个整型 (int)；(3) 竞争探测 (race probe) 必须位于 `select_for_update` 的接缝处（即锁重新读取的地方），而不是在行获取 (line fetch) 时。让我来修复这些测试。
让我将共享的 fixture 移动到模块级别，并检查剩余的失败详情。
一个测试意外通过了（预修复）。我来调试一下深度探测。
`savepoint_state` 是一个单调递增计数器，而不是深度表——它无法检测到块退出。让我用一个跟踪 `tenant_context` 进入/退出的 wrapper 来替换这个探针。
8 项测试已全部正确处于 RED 状态。接下来我将对剩余的后端任务（uuid 路由、序列化器容差、display_money、查询次数）进行第二个 RED 测试文件测试。
`create-serializer` 测试空洞地通过了——可能是由于其他原因导致验证失败。让我来检查一下。
所有后端 RED 测试已就绪（共 18 个）。现在开始 GREEN 修复。让我读取完整的 `unallocate` 方法以及剩余的修复目标。
所有目标已读取。现在开始应用 GREEN 修复 —— 从 BE-H1 (`remove_line`) 开始，即标题修复。
现在进行 BE-M3（取消分配锁重排序）和 BE-M5（peppol 任务全包装）。
现在进行剩余的后端修复工作 —— 批量应用。
`create_entry` 锁引入了新的死锁风险（两个并发条目以相反顺序锁定账户）。让我添加一个确定性的预锁定阶段。
现在进行 display_money 有限值检查、suggest_matches select_related，以及 amend_return 原子操作换行。
所有后端修复已应用。正在运行 P19 后端测试套件以准备进行 GREEN（测试通过）。
16/20 通过。让我检查一下剩余的 4 个。
有三个测试框架修复：将 `list_entries` 移入查询计数上下文，修复 `BankAccount` 导入，使 `_FakeManager` 可迭代，并移除单事务模拟中的 savepoint-rollback 痕迹。
全部 20 个 P19 后端测试均已通过。现在运行完整测试套件以进行回归检查。
后端已通过：**934P/0F/5S**（+20，无回归）。现在进行第二阶段——前端。让我来调研一下前端测试的约定和组件。
让我读取一下我需要修改的组件。
现在让我来应用 FE-H1（banking modals → Radix Dialog）、FE-H2（transaction row button）和 FE-M1（UEN edit regex）。首先检查 UEN regex 的导出。
让我先检查一下现有的 `banking-client` 测试工具，以便为 modal 测试参照其结构。
现在开始编写前端 RED 测试文件（基于 `banking-client-transactions` harness 模式）。
全部 6 个测试均呈红色。现在应用 GREEN 修复。首先检查现有的表单测试是否固定了内部的 X 按钮。
现有的测试已固定在页脚的 Cancel —— 可以安全地移除未命名的 header X。正在应用 FE-H1 修复。
现在进行 FE-H2 —— 交易行头部按钮。
进度 —— H2 Enter/Space 已通过。其余问题属于测试精度相关的问题。让我检查一下标签页结构。
找到两个 “Import Statement” 按钮（一个位于 client header，一个位于 transaction-list）。正在修复测试选择器（test selectors）。
Radix 1.1.15 完全没有设置 `aria-modal`（role="dialog" + focus trap 才是它的契约）。让我为对话框添加可访问名称（accessible names），并正确地固定该契约。
6 个测试全部通过。现在移除表单中多余的未标记的 X 按钮（对话框现在提供了一个已标记的关闭按钮）。
所有 X 按钮均已移除。让我对 `banking` 测试目录进行回归检查。
两个测试需要更新以适配新的（正确的）模态框行为。让我来读取一下它们。
所有 133 个 banking 测试均已通过。现在开始应用快速修复批次（M1, M4, M5, L3, L5）。
现在开始 M5 (scope="col") 和 L3 (back-link labels)。
现在进行 FE-L1（发票行网格 ARIA）和 FE-L4（支付表单标签）。
现有的测试锁定了旧的标签。正在将它们更新为新的行上下文名称。
发票测试已全部通过。现在处理 FE-L4（支付表单字段标签 + 错误提示）。
FE-L4 已完成。现在处理 FE-L7 —— 那 5 个 eslint 警告。
**eslint 0E/0W** —— 保持完全一致。现在处理 FE-L8（两个 UEN 编辑面上的 UEN 编辑验证）。
全部通过。接下来是关键的部分——FE-M2，即 ContactPicker WAI-ARIA combobox（自 P16 以来就推迟的项目）。
正在向现有的 `contact-picker` 测试文件中添加 P19 键盘契约测试 (RED)。
正确的 RED。现在开始实现完整的 WAI-ARIA combobox。
旧测试固定的一个行为需要更新（选项现在基于 `mousedown` 进行选择——正确的 `pre-blur` 模式）。
FE-M2 已完成（9/9 通过）。现在进行 FE-M3 —— 应用内未保存工作路由守卫。
所有 5 个 route-guard 测试均已通过。现在将 guard 挂载到 invoice 表单中。
等等——我把 JSX 插入到了函数体中。测试竟然通过了，这很可疑。让我核实一下实际落盘的内容。
该元素虽然会被解析，但永远不会渲染——必须将其放置在返回的 JSX 内部。让我来妥善修复这个问题。
第二阶段完成。现在进入第三阶段——横向工作。首先从 X-M1（CSP report-uri）开始。
CSP 测试已通过。现在进行 X-M2 —— CSV 大小限制。让我检查一下导入签名和现有测试。
将 CSV cap 的 RED 测试添加到 P19 合约文件中，然后进行修复。
正确显示红色（失败）。正在应用 CSV 上限修复。
CSV cap 已通过。现在开始处理剩余的跨领域批次。
Compose 有效。现在处理 X-M4 (PG_BASE)、X-L2 (e2e 密码)、X-L4 (ALLOWED_HOSTS)、X-L5 (CI 校验)。
现在处理 X-L3（移除未使用的 uuid 依赖）以及 X-L1 勘误表。
所有 Phase 3 修复已应用。现在开始完整的 gate matrix。先从 Backend 开始。
两个测试适配：表单测试需要 `mousedown`，并且身份验证测试的 `router` mock 必须是 `stable` 的。
Vitest 619/619，tsc 0 —— 但 eslint 检测到 2 个新错误。让我检查一下。
所有静态检查均已通过 (619/619, tsc 0, eslint 0E/0W)。现在进行实时检查——首先在修复后的代码上重启后端（根据 P13/P18 的经验，使用 daemonize.py）。
后端已重启并搭载修复后的代码，基板完好。正在运行实时端到端（e2e）门控。
2 个 e2e 失败 —— 可能是我的 modal/form 修改产生的下游影响。让我检查一下。
该 spec 定位了旧的 `div.fixed.inset-0` 覆盖层 —— 现已变更为 Radix Dialog。我来调整一下 spec，并同时检查 invoice 相关的 spec。
该测试用例（spec）定位了旧的 `div.cursor-pointer` 扩展器——现在已改为按钮。正在修复。
对话已打开，但组合框弹出窗口未显示选项。让我通过完整的银行业务规范运行来重新生成新的上下文。
检测结果显示该选择项正常打开，共有 8 个选项。让我完全复现该规范的精确操作序列。
导入表单中的 bank-account 选择框没有 accessible name（与 FE-L4 属于同类缺陷）。正在添加该标签。
现在发现了一个已命名且可见的组合框。正在重新运行失败的测试用例。
HEADER 按钮的名称现在包含了 "Unreconciled" 徽章 —— 修复了匹配歧义。
确认按钮超出了视口（view port）范围——高内容的对话需要设置 `max-h` 并启用内部滚动。正在修复 `DialogContent` 的封装器。
银行测试规范已全部通过。完整 e2e 门禁运行：
**e2e:full 40/40 已通过。** 现在在 :8001 端口重启 rls_smoke 后端（修复后的代码，以 `ledgersg_app` 身份）并运行剩余的实时门禁。
**完整门禁矩阵已全部通过**：后端 937P/0F/5S · vitest 619/619 · tsc 0 · eslint 0E/0W · e2e 40/40 · rls_smoke 13/13 · mobile-nav 17/17 · prod-CSP 5/5。现在开始 session-38 的截图。
现在正在编写 session-38 截图捕获脚本（P19 验证界面）。
4 个 P19 验证界面已通过。116/117 因页面真值（page-truth）断言失败——让我来调试一下这些 h1 检查。
探针测试通过了，但脚本却失败了——让我给脚本添加真值调试。
找到了——我的脚本在所有选择器上都使用了 `.first()`，但第一个 `h1` 是 "LEDGERSG" logo。正在修复为针对 `h1` 使用页面级最后一次（page-last）的约定。
已全部捕获 8 个。正在对截图进行像素级非空白验证（仓库约定）。
让我对这两个最重要的 P19 证明捕获进行视觉确认。
本次会话中无法使用视觉功能——DOM probes 加上像素检查是既定的验证依据（P18 先例）。现在开始文档编写：P19 报告、session log、worklog。
现在是 session_38.md 日志和工作日志条目。
现在进行文档核对更新——即核心文档中的门禁计数。
正在更新核心文档中的 P19 状态和统计数据。
现在开始处理 API 指南 P19 的附录。
文档已更新。接下来进行提交系列——首先进行完整变更清单的登记。
现在是前端批次（第 4 次提交）。
所有 8 个提交已完成，工作区已清理。现在通过 SSH wrapper 进行推送。让我研究一下运行手册和 wrapper。
在推送前，先对新增/修改的文档进行占位符扫描。
清理（匹配项为历史 `worklog` 说明）。现在通过 SSH wrapper 进行推送 —— 密钥存放在仓库外的 `/tmp` 中，先进行 `dry-run`。
远端有新的提交——让我通过 HTTPS 拉取并检查一下变动。
真奇怪 —— 实际的远程仓库仍停留在我的基准提交上。让我检查一下 wrapper 的推送机制。
直接试运行（dry-run）成功且顺利完成了 fast-forward。让我重新运行封装好的试运行，看看第一次失败是否是暂时性的。
Dry-run 现在通过了——第一次失败是暂时的。现在开始进行真正的推送。
**推送已验证：远程 main @ 39596a8f == 本地 HEAD。** 根据操作手册销毁操作员密钥并进行最终验证。
P19 冲刺已完成并交付。本次会话从 P18 中断的地方继续：拉取了所有者的 `session_37.md` 日志（确认 P18 已推送），复现了所有基线，运行了三项深度审计（0 个严重 / 3 个高 / 16 个中 / 22 个低），然后端到端地执行了新的周期。

**核心发现：** P18 的提交声称 `remove_line` 已被锁定——但实际上从未有过锁，而且它其实从未生效过（每次调用都会出现 FieldError → 500）。连同另外两个高优先级问题：四个手动编写的银行模态框（没有焦点捕获/Escape/对话框语义）以及仅支持鼠标的事务行（导致键盘用户无法访问 Reconcile）。

**已修复（TDD，先 RED 后 GREEN）：** 锁定/事务完成（死锁重新排序、归档缓存绕过、已排序账户锁、保存点、完整的租户上下文）、uuid 路由孤岛、日志预取 + 容差、CSV 上限、CSP report-uri、组合节拍移除、PG_BASE 修复——外加那两个遗留的延迟事项：**ContactPicker WAI-ARIA 组合框**和**应用内未保存工作路由守卫**（自 P16 以来一直处于延迟状态）。

**最终门禁（全部通过）：** 后端 937P/0F/5S · vitest 619/619 · tsc 0 · eslint 0E/0W · e2e 40/40 · rls_smoke 13/13 · mobile-nav 17/17（第 9 次无 Tailwind-v4-bug 的裁定） · prod-CSP 5/5。通过 8 个 DOM 验证的截图进行了记录，更新了文档，并分 8 次常规提交推送——远程验证为 `39596a8f`，密钥已销毁。

关键工件：[P19 计划](/home/z/my-project/ledgersg/docs/REMEDIATION_PLAN_2026-11-27_P19.md) · [P19 报告](/home/z/my-project/ledgersg/docs/REMEDIATION_2026-11-27_P19_REPORT.md) · [会话日志](/home/z/my-project/ledgersg/docs/session_38.md) · [工作日志](/home/z/my-project/ledgersg/worklog.md)

建议的下一步：进行一次 P20 审计会话，处理剩余的待办事项——列表分页 + `{data}/{results}` 信封统一（其先决条件）、ruff 机械批处理以及审计日志 INSERT 策略设计。
