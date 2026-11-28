我将开始执行这套完整的工作指令。首先建立任务清单，然后逐步推进。
工作区已刷新到最新（`7322b224`，含 session_67.md）。现在开始阅读核心文档：
仓库是 monorepo 结构：`apps/backend`（Django）+ `apps/web`（Next.js）。现在阅读核心文档：
文档很大，读取关键部分：
现在读取会话历史文档（session_67 是最新的）：
P34 上下文已完全掌握。现在检查环境状态（PG/Redis/服务器是否存活）：
环境大部分存活：PG 17 + Redis + web dev server 都在运行，backend :8000 已死（沙箱回收后台进程的已知行为）。验证数据库状态：
数据库结构完整（documents 在 `invoicing.document`，53 orgs 是多次 e2e 运行累积的正常状态）。现在读取 skills 目录与关键辅助文档：
Tailwind v4 报告与 PG 设置脚本已读。现在启动 backend 并复现基线（关键教训：后台进程会在调用间被回收，需在同一调用内完成）：
后端基线精确复现：**1073P/0F/5S**。现在运行 web 静态门控：
所有静态门控精确复现（1073P · 698/698 · tsc 0 · eslint 0 · lint-mechanical 0 · ruff 148/73）。现在查 e2e 所需的环境变量与运行方式：
上会话的编排脚本可直接复用。运行 live gates 基线：
**全部基线门控精确复现 — P34 状态完全成立**（含 mobile-nav 17/17 第 38 次判定 + translate probe PASS，无 Tailwind v4 bug）。现在进入审计阶段（Mode C），先验证 P34 修复切片：
P34 切片在源码中成立。现在审计 P35 候选 — 首先是登记在册的头号候选（Schematron 轴）：
Schematron 轴已定位：`_validate_schematron` 占位符从未被调用，`schematron_errors` 恒为空，`.sch` 文件存在但 queryBinding="xslt2"。检查 lxml 的 isoschematron 能力与 transmission service 对验证结果的使用：
**审计发现（已复现）**：repo 的 `PINT-UBL-validation.sch` 使用了错误的命名空间（`dml` 而非 ISO 标准的 `dsdl`）+ `queryBinding="xslt2"`（lxml 只支持 XSLT 1.0 skeleton）——该文件根本无法被解析；且 `_validate_schematron` 占位符从未被调用，`schematron_errors` 恒为空。用正确命名空间 + `xslt` binding 验证可行（no-ID → False, with-ID → True）。

继续审计 generator 与 transmission service 的完整流程：
Generator 全貌已掌握。现在检查既有验证测试与 mapper，以及 web 测试套件配置（standing task）：
审计发现持续累积：`test_validate_returns_schematron_errors` 是一个恒真测试（`assert hasattr(...) or True`）。现在验证 web 测试套件配置（standing task）：
配置验证完毕（在位且最新）。现在检查一个潜在新发现 — transmission service 的 `"; ".join(errors)` 与真实 dict 形状的兼容性：
**第二个真实发现已确认**：transmission 测试完全 mock 验证服务，且 mock 形状是字符串列表（`"errors": ["Invalid tax category"]`），而真实验证器返回 dict 列表（`{"message":..., "line":..., "column":...}`）— `"; ".join(list_of_dicts)` 会抛 TypeError，导致 schema 无效文档走 INTERNAL_ERROR 而非预期的 VALIDATION_ERROR。继续检查 .sch 的其他消费者：
三个发现全部活体复现。快速 sanity check（带行的有效文档应通过 — 确认 P34 状态无回归）：
审计完成。决定性证据：**篡改 currencyID 的文档（USD 文档内一个 SGD 金额）当前通过验证 is_valid=True** — 跨元素业务规则缺口实锤。汇总 P35 发现：0 Critical / 2 High（Schematron 轴三重缺陷 + transmission 失败路径 TypeError 崩溃）。

按指令咨询 repo skills 后制定计划：
现在编写 P35 修复计划（沿用 repo 命名约定）：
计划已保存。现在对照代码库验证计划（执行前的对齐检查）：
既有 fixture 通过 generator 单一 `currency` 参数保证一致性（P33 真理）。现在原型验证计划中的 XPath 规则在实际 generator 输出上的行为（计划验证的关键步骤）：
`matches()` 是 XPath 2.0 函数，XSLT 1.0 不支持。改用 XPath 1.0 等价表达式（translate 技巧）：
**原型规则集全部按预期工作**（8/8 场景验证通过，含位置信息的 SVRL 提取）。计划已对照代码库验证。现在检查测试 conftest 约定后开始 Phase 1 RED：
现在编写 Phase 1 RED 规格（两个新 spec 文件）：
RED 确认：14 failed + 2 designed controls pass。验证失败原因是否精确命中缺陷：
RED 失败原因全部精确命名缺陷（SchematronParseError · dml/dsdl 命名空间 · is_valid=True 缺口 · TypeError join 崩溃）。**Phase 1 完成：14 RED + 2 controls = 16 新门控**。

现在 Phase 2 GREEN — T3 重写 .sch（用已验证的原型）：
现在进行 T4 — 将 `_validate_schematron` 集成到验证服务中：
验证编辑后的文件完整性：
T1 规格 10/10 通过。现在进行 T5 — transmission service 的形状容忍格式化器：
主测试通过。控制测试需设置 mock adapter（验证 seam 之后的步骤不是被测点）：
T2 规格 6/6 通过。现在 T6 — 强化恒真测试：
现在 T7 — 运行完整的后端测试套件：
**后端套件：1089P/0F/5S — 精确 +16 门控，既有 pin 全部保持**。现在检查 lint 真理：
生产计数 148→150，我的编辑引入了 2 个新发现。定位并修复：
新增的 2 个发现是我在 327 行引入的 `List[Dict[str, Any]]`（UP006 ×2）。用现代化注解修复：
**Lint 真理恢复：148/73 精确，全套件 1089P/0F/5S 保持**。Phase 2 GREEN 完成。现在 Phase 3 — 修复后树上的完整门控矩阵。先跑 web 静态门控，再跑 live gates：
Live gates 全绿（rls 13/13 · mobile-nav 17/17 第 39 次判定 · translate PASS · e2e 43/43）。现在 build:server + prod-CSP 冒烟：
prod-CSP 5/5 通过。现在做 live API 契约复验（真实 demo 文档 + 业务规则层开启）。参考上会话的探针脚本：
**LIVE 契约复验 PASS**：真实发票 INV-00006 (SGD) 业务规则层开启后仍 is_valid=True 字节稳定；篡改控制触发 BR-SG-06；真实 credit note 干净通过。

现在截图（232-239）。查看上会话截图脚本约定：
编写 session-68 截图脚本（232-239，沿用 repo 约定）：
8/8 截图捕获成功（DOM truths 全过，md5 唯一）。现在像素验证：
8/8 像素验证通过（variance 438–936）。目视抽查一张确认：
当前模型无法直接查看图像 — DOM truths + 像素方差是 repo 既定的验证标准（session_66 已确立），8/8 全部通过。现在验证 `.env.example`：
`.env.example` 已在位且详尽。做 config-readers 扫描确认 P35 未引入新环境变量：
变更集精确符合预期。现在进入 Phase 4 — 文档 truth pass。先看 README 的当前状态：
更新 README（badge、状态行、里程碑、测试计数）：
README 结构正确。现在更新 CLAUDE.md：
修复一个笔误（UML→UBL），然后更新 AGENTS.md：
MultiEdit 因第二个 edit 的 old_str 错误而整体未应用。分开重做：
第一个编辑已应用（头部已是 session 68 / P35）。现在追加两个 P35 lessons 到尾部：
更新 SKILL 与 PAD：
SKILL 与 PAD 更新完成。现在更新 DEPLOYMENT.md 头部与 ci.yml：
现在更新 API_CLI_Usage_Guide.md：
现在编写 P35 报告：
现在编写 session log 与 worklog 更新：
所有文档已更新。最终验证变更集：
变更集精确符合预期。提交前做最终全套件验证：
最终验证全绿（1089P · lint 0 · 148/73 · .sch 编译正常）。现在按 repo 约定提交（3 个 commit），先读 SSH wrapper 使用说明：
Wrapper 默认远程是 ely-beauty，需传 `--remote` 指向 ledgersg。现在按约定提交：
3 个 commit 已完成。现在设置 SSH 密钥并通过 wrapper 推送：
Dry-run 绿色（干净 fast-forward）。执行真实推送：
**P35 Sprint 已交付 — Peppol 业务规则真实度 + 传输失败路径真实度，已推送到 `main` 分支，提交 ID 为 `42aeb76e`。**

工作区已拉取到 `7322b224`；环境在沙盒回收后依然存活并进行了端到端验证（PG 17 + 两个数据库 + v1.2.2 模式，Redis 8，venv，:3000 端口上的 Web 开发服务器）。在进行任何更改之前，所有记录的基线都已完全重现：后端 **1073P/0F/5S**，vitest **698/698**，tsc/eslint 0，e2e **43/43**，rls **13/13**，移动端导航 **17/17 + 转换探针 PASS — 运行正常，无 Tailwind v4 bug**（第 38/39 次判定）。

审计发现了两个高危缺陷，均已在生产环境复现：业务规则验证层**端到端完全是装饰性的**（`.sch` 无法解析 — 一个 `dml`→`dsdl` 命名空间拼写错误 + 不支持的 `xslt2` 绑定；`_validate_schematron` 是一个从未被调用的占位符；一个带有金额 `currencyID` 被篡改为 SGD 的 USD 单据验证顺利通过），并且传输失败路径**在真实验证器的字典格式上崩溃**（`"; ".join` → TypeError → INTERNAL_ERROR，而不是携带真实消息的 VALIDATION_ERROR）。

已全部通过 TDD 修复（14 个 RED → GREEN，新增 16 个门控）：在两个验证路径上连接了带有故障关闭（fail-closed）姿态的 5 规则 XPath 1.0 Schematron 集（**BR-SG-06 金额与 `currencyID` 的一致性扫描在验证层中锁定了 P33 真实度**），以及形状容错的错误连接 + 一个带有无验证模拟的真实失败路径规范。后端 **1089P/0F/5S** · ruff **148/73**（保持不变）· 已在现场真实演示单据上验证 — 两种类型在开启该层的情况下均验证通过，字节保持稳定；被篡改的对照单据因指明了 BR-SG-06 而失败。8 张经像素验证的屏幕截图（232-239），`.env.example` 真实，完整的文档真实度检查（CLAUDE 2.36.0，API 指南 v3.8.0，新增 2 个 AGENTS 经验教训）。推送已通过 SSH 包装器验证（远程 == HEAD @ `42aeb76e`），密钥已销毁。

关键交付物：[P35 计划](/home/z/my-project/ledgersg/docs/REMEDIATION_PLAN_2026-11-28_P35.md) · [P35 报告](/home/z/my-project/ledgersg/docs/REMEDIATION_2026-11-28_P35_REPORT.md) · [会话日志](/home/z/my-project/ledgersg/docs/session_68.md) · [工作日志](/home/z/my-project/ledgersg/worklog.md) · [README](/home/z/my-project/ledgersg/README.md) · [部署](/home/z/my-project/ledgersg/docs/DEPLOYMENT.md) · [API 指南](/home/z/my-project/ledgersg/API_CLI_Usage_Guide.md)

**建议下一步：** 已注册的候选方案 — Schematron **算术**轴（针对 `NUMERIC(19,4)` 的 BR-CO-10..17 规则，需要 XPath 精度对话）、UP 类型定义批次（×105，受限于 mypy 门控对话），或 E501 + `make format` 轴。
