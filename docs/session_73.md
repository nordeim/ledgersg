我将按指令顺序执行这套完整的代码审计与修复任务。首先创建任务清单，然后刷新工作区。
工作区已更新至最新提交 `a7ce0c10`（包含 `docs/session_71.md`）。现在阅读核心文档。
文档较大，我读取保存的完整内容关键部分。
现在阅读 session 日志与 P36 修复文档。
核心修复历史已掌握。现在快速掌握 README / PAD / SKILL 的当前锚点与项目结构。
核心文档阅读完成。现在验证环境状态（PG/Redis/venv/node_modules）。
venv 与 node_modules 存活，但 PG/Redis 需要检查。查看 rootless PostgreSQL 配置。
psql 挂起（可能在等待密码）。检查后端 .env 配置与连接方式。
PG 17 运行正常（45 张表）。验证数据库 schema 与 demo substrate 规模。
环境存活验证完成：PG 17（45 表，demo substrate：149 orgs / 45 entries / 1710 accounts / 37 documents）+ Redis 8 均正常。快速确认 setup 脚本与 skill 的一致性，然后复现基线。
环境与 repo 契约一致。现在标记 PostgreSQL 任务完成，并复现 P36 基线门禁（后端测试套件）。
后端基线精确复现：**1114P/0F/5S**。现在运行 web 静态门禁。
所有静态门禁精确复现。现在在同一次调用中运行实时门禁（e2e / rls_smoke / mobile-nav / translate probe）。
rls_smoke 13/13 与 e2e 43/43 通过，但 mobile-nav audit 与 translate probe 报错。查看这两个脚本的依赖。
这两个探针需要前端 dev server（:3000）。参考上一会话的捕获脚本确认启动方式。
**全部 P36 门禁精确复现**：rls 13/13 · mobile-nav **17/17（第 42 次判定，无 Tailwind v4 bug）** · translate probe PASS · e2e 43/43。现在验证测试套件配置并审计 P36 代码切片。
Vitest + Playwright 配置已就地验证。现在源码复核 P36 切片。
P36 切片源码复核通过。现在进行 P37 审计——先查注册的延后项详情，再进行新发现挖掘。
查看近期提交历史与变更文件，聚焦“近期变更”审计。
现在进行 P37 新发现挖掘。系统性探测几个假设轴：e2e substrate 积累、UEN 校验、unitCode 真值、credit-note BillingReference。
发现两个候选轴。深入检查：mapper 的 unit_code 供源、credit note 与原始发票的关联字段。
DB 层有 `related_document_id`（P14/H-4 强制 IRAS 规则）。检查 credit-note XML 是否发出该引用（BillingReference）。
确认 mapper 未发出原始发票引用。检查 generator 的 credit-note 输出结构与 XSD 是否声明 BillingReference。
Generator 确认无 BillingReference。现在通过网络检索确认 EN 16931 / Peppol PINT 对 credit note 引用原始发票的强制性规则。
多个来源确认 IRAS 要求与 Peppol PINT 结构。获取 PINT credit note 规范确认 BillingReference 的基数。
发现候选 H1 已确认（EN 16931 规则校准：BR-CO-24 是行费用规则，实际结构是 BG-3/BT-25）。检查 credit note PDF 模板与 XSD 是否携带原始发票引用。
PDF 模板同样无原始发票引用。检查 model 字段定义与 API 序列化。
模型与序列化器都携带 `related_document`，但 XML 与 PDF 均未发出。继续第二轴扫描：credit note 的调整原因（IRAS 要求描述调整内容）。
获取 IRAS InvoiceNow e-Tax 指南确认 credit note 经 InvoiceNow 提交时的原始发票引用要求。
权威来源已充分（IRAS §11.6 + Peppol PINT 语法 + repo 自身 P14/H-4）。现在写实时探针复现发现：demo credit note 的 XML 无 BillingReference。
探针确认：BillingReference=0，原始发票号在 XML 中出现 0 次。查看干净输出与 PDF 生成上下文。
H1 发现已完全复现。现在检查修复设计约束：XSD 结构、现有 fixtures 的影响范围、API 文档现状。
查看 .sch 规则结构与现有 credit-note 合成 fixtures，评估新规则的影响范围。
DB 契约无懈可击（service 层无条件强制）。检查 PDF 上下文构造，完成审计证据链。
审计证据链完整。检查 XSD 组件现状（Note / DocumentReference 是否已声明）。
设计约束已明确。检查现有 specs 的验证调用方式与 transmission service 的 credit-note 路径，完成影响范围评估。
影响范围明确：3 个合成 fixture 需补 `billing_reference`。检查传输服务调用 mapper 的位置以确认查询边界。
审计完成：**0 严重 / 1 高 / 1 低**。现在编写 P37 修复计划。
计划已保存。现在执行前进行计划对齐验证：确认现有 fixtures 的影响与 XML 字节断言的波及范围。
Mock 约定明确。全面搜索 `validate_credit_note_xml` 的测试调用点，确保 fixture 影响清单完整。
计划验证完成：fixture 影响精确限定为 4 处，均为 containment 断言无字节风险。查看 P8 PDF 测试模式后开始 Phase 1 RED。
P8 模式清晰。现在编写 Phase 1 的两个 RED specs。
修正 PDF 测试：直接用 `render_to_string`（基树上可用），确保 RED 原因正确（模板内容缺失而非辅助方法不存在）。
Now writing the second RED spec (note emission):
PDF 测试出现 ERROR（fixture 不可用）。检查错误详情。
fixture 在 `tests/integration/conftest.py`。将 PDF 测试类移至 `tests/integration/test_credit_note_pdf_p37.py`（P8 先例的位置）。
提取逻辑出错导致类嵌套。直接重写集成测试文件。
RED 确认：14 failed / 6 passed。检查 `test_mapper_omits_reference` 失败原因（应为 mock 字段问题）。
经典的类作用域问题。修复 mock：类创建后再设置参数化属性。
RED 阶段完成。现在进入 Phase 2 GREEN：T3 mapper 修复。
**Phase 1 RED 完成：13 failed / 7 designed controls。** Phase 2 GREEN — T3 mapper：
我误删了 P36 的 tax_currency 行。立即恢复。
tax_currency 已恢复。现在添加 `_map_billing_reference` 辅助方法：
T4：generator 修复（BillingReference + cbc:Note 发出）。
现在编辑 generator：两条路径的 cbc:Note + credit-note 路径的 BillingReference。
现在添加 `_create_billing_reference` 辅助方法。查看 `_create_payment_terms` 的位置以保持风格一致：
T5：更新 XSDs。先看 CAC XSD 的声明模式：
现在更新 CreditNote XSD（BillingReference + Note）与 Invoice XSD（Note）：
T6：Schematron 添加 PINT-SG-REFERENCE 模式（BR-SG-07）：
T7：PDF 模板 + 上下文。先改模板（引用块 + 标题）：
现在更新 `_get_pdf_context`（credit-note 门控的 related_document 上下文项）：
T8：fixtures 真值修正（4 处合成 mapped-data 补 billing_reference）：
Mock 缺 `notes` 属性。修复两个 spec 的 mock 并诊断其余失败：
两个根因明确：identity 断言应比较 id；note spec 的 credit-note payload 需补 billing_reference。修复：
模板日期渲染是本地化格式。将模板改为确定性 ISO 格式（`|date:"Y-m-d"`）：
**20 个 P37 门禁全部 GREEN。** T9：运行完整后端套件（期望 1114 + 20 = 1134）：
按 P36 惯例修复 mock（补齐 mapper 的真实读取字段）：
**后端套件 1134P/0F/5S — 精确 +20，所有既有 pin 保持。** 现在验证 lint 真值：
production ruff 148 → 150（+2）。定位新增项：
mapper 文件 7→8（我的 `Dict[str, Any] | None` 注解）。找另一个 +1：
两个新增项均为 UP006（新方法的 `Dict` 注解）。按 P36 惯例（新代码必须干净），改用小写 `dict`：
Lint 真值恢复（148/73 精确）。Phase 3：完整门禁矩阵。先跑后端全套 + web 门禁：
现在，在同一个调用中运行实时门禁（e2e / rls / mobile-nav / translate / build:CSP / prod-CSP）：
全部实时门禁通过（rls 13/13 · mobile-nav 17/17 第43次判定 · translate PASS · e2e 43/43）。现在 build:server + prod-CSP + 实时契约复核：
契约 1-4 全部通过。修复探针脚本的 `document_id` → `id` 错误，并检查 build/CSP 输出：
build:server 与 prod-CSP 5/5 通过。`.env.example` 真值扫描 + npm audit：
现在处理截图。查看 session-70 捕获脚本约定：
编写 session-72 截图脚本（248-255，沿用约定）：
8/8 捕获正常。现在像素验证：
**Phase 3 完成**（全矩阵绿 + 契约通过 + 8/8 像素验证）。进入 Phase 4 文档真值校验。先写 P37 报告：
现在更新 README（徽章 1855→1875 + P37 里程碑）：
现在为 AGENTS.md 添加 P37 经验教训，并更新 DEPLOYMENT.md：
现在，API_CLI_Usage_Guide.md（v3.9.0 → v3.10.0，credit-note 引用契约）：
接下来是工作日志条目：
文档真值校验完成。最终提交前验证：完整变更集 + 门禁复跑：
最终树验证通过。占位符扫描 + 查看 SSH wrapper 推送说明：
按 repo 惯例进行 3 次提交（fix / screenshots / docs）：
3 次提交完成，工作树干净。现在通过 SSH wrapper 推送：
shim 已就位且系统 python 有 paramiko。验证密钥并执行 dry-run：
Dry-run 通过（`a7ce0c10..49d90ab0` 干净 fast-forward）。执行真实推送：
**P37 Sprint 已交付并推送到 `main` 分支**（commit `49d90ab0`，远程已验证 `refs/heads/main == local HEAD`，密钥已销毁）。

## 本次会话完成的工作

**环境与基线**：工作区拉取至 `a7ce0c10`；沙箱回收后 PG 17 + Redis 8 依然存活（端到端验证：45 表、demo substrate 149 orgs / 37 documents）。全部 P36 门禁精确复现：backend **1114P/0F/5S** · vitest 698/698 · tsc/eslint 0 · e2e 43/43 · rls 13/13 · **mobile-nav 17/17 + translate probe PASS（第 42/43 次判定 — 正常工作，无 Tailwind v4 bug）** · ruff 148/73。Vitest + Playwright 配置已就地验证。

**审计（0 严重 / 1 高 / 1 低，均已在生产环境复现）**：
- **H1 — credit-note 原始发票引用缺口**：DB 层自 P14 起强制 `related_document_id`（IRAS 规则），但实时探针证实生成的 XML **零 BillingReference、零原始发票号出现**，PDF 亦无引用块且标题泄漏原始枚举值
- **L1 — cbc:Note 缺口**：mapper 丢弃 notes 字段（BR-111-GST-SG 期望原因备注）

**已交付（TDD，13 RED → GREEN，+20 门禁）**：BillingReference 贯穿所有层（mapper `_map_billing_reference` → generator UBL 位置发出 → CAC/CreditNote XSD 声明 → **BR-SG-07** Schematron 存在性下限 → PDF "Original Invoice" 块 + "CREDIT NOTE" 标题）；受守卫的 cbc:Note 发出（notes 空文档字节稳定）。

**已验证**：backend **1134P/0F/5S** · 完整 web 矩阵绿 · 实时契约复核（真实 demo credit note CN-00001 携带 INV-00001 · 2026-01-01 引用并验证通过；剥除引用的对照失败且 BR-SG-07 命名；发票字节与 P36 一致）· 8 张像素验证截图 (248-255) · `.env.example` 真实 · 完整文档校验（README 徽章 1875，CLAUDE 2.38.0，API 指南 v3.10.0，新增 1 条 AGENTS 经验教训）。

关键交付物：[P37 计划](/home/z/my-project/ledgersg/docs/REMEDIATION_PLAN_2026-11-28_P37.md) · [P37 报告](/home/z/my-project/ledgersg/docs/REMEDIATION_2026-11-28_P37_REPORT.md) · [会话日志](/home/z/my-project/ledgersg/docs/session_72.md) · [工作日志](/home/z/my-project/ledgersg/worklog.md)

**建议下一步**：已登记的候选 — UP 类型化批处理（受 mypy 限制）、E501 + 格式轴、BR-CO-11/12/18、N818 重命名，或新登记的 `unit_code` 建模缺口。
