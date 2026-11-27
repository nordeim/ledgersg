我将首先建立任务计划，并检查本地工作区状态。
工作区已存在且仓库已克隆。执行 `git pull` 以刷新——`session_51.md` 已完成 fast-forward 至 `3aad8b63`。环境在沙箱回收后完整保留：PG 17、Redis、:8000/:8001/:3000 上的技术栈——但 `ledgersg_app` 的密码发生了偏移（2 个 RLS pytest 门限失败）；在执行 `ALTER ROLE` 回到记录的默认值并重启 8001（分离的守护进程——此沙箱会清理同进程组的子进程）后，后端测试套件完全复现：1021P/0F/5S。
静态门限完全复现：vitest 686/686（80 个文件）、tsc 0、eslint 0E/0W、npm audit 0 critical。现在开始进行指定的关注点——移动端导航。
**移动端导航结论（第 22 次确定）：按预期工作——没有剩余的 TailwindCSS v4 bug。** 审计 17/17；专用 `translate` 探针：8 个中间飞行样本，`transitionProperty` 中包含 `translate` 属性，Escape 键将其关闭。
RLS smoke 测试 13/13（绿色）。现在进行实时 e2e——记录的门限为 43/43。
**e2e 复现为 42/43，三次运行结果相同**——P26 分页规范在 "Showing 21–N" 处失败，但在隔离测试中通过。这不是 flake（不稳定）：Pull the trace。
追踪证据：Next 点击已分发；offset=20 请求已触发并返回 200；然后 UI 返回到 "Showing 1–20"，且没有第三个请求——这是缓存服务的还原特征。时序：点击落在 mount+350ms，在防抖动效果的 MOUNT-run 窗口内（其计时器主体在 ~300ms 时无条件调用 setOffset(0)，在 StrictMode 下翻倍）。审核结论：FE-H1——竞态条件；加上银行列表上缺失的组织切换和过滤器更改偏移重置（P25 分类账模式从未应用到这五个界面）。
P27 计划已保存并根据代码库进行了锚定验证。RED 阶段：5 个新的 real-hook 传输模拟规范文件——9 个失败，完全符合预期的原因，3 个反向固定（counter-pins）通过。
GREEN 阶段：针对 VALUE CHANGE 的值比较修复（计时器回调内部的 `lastDebounced` ref——linter 拒绝了渲染时间 ref 的读取，`react-hooks/refs`；且现有测试套件捕获了未设防的 `setOffset(0)` 双重渲染以及 absent-prop `filters = {}` 的无限循环）。迭代：ref 守卫 → lint 干净的计时器回调比较 → NO_FILTERS 稳定默认值。
完全 vitest 698/698（85 个文件），tsc 0，eslint 0E/0W。现在是见证时刻——完整的 e2e 测试。
**e2e 43/43——确定性。** 竞态窗口在结构上已关闭。后端测试套件未更改（1021P/0F/5S，重新验证）。覆盖率下限提高到 73.39/70.72/62.38/73.95。mobile-nav 17/17（第 23 次），translate 探测重新通过，build:server 绿色，prod-CSP 5/5，rls_smoke 13/13，audit 0 critical。
全新数据库证明：drop/recreate → schema 加载（37 张表）→ 后端重启 → Redis 刷新 → 一次引导（36 行 / 12 APPROVED）→ **首次 e2e 运行 = 43/43，0 跳过。**
捕获了 8 张屏幕截图（168-175），DOM 真理已验证——标题 169：第 2 页在旧竞态窗口之后保持了 1.5s。像素验证非空白。`.env.example` 重新验证真实（没有新的环境变量）。API 指南契约在修复后的技术栈上重新进行实时验证（分页 envelope、类型化的 400、Peppol 计数器）——没有 API 变化，版本保持 3.5.0。
文档事实传递：README 徽章 1762 + P27 里程碑，CLAUDE 2.28.0，AGENTS 标头 + 4 个新课程，SKILL 2.14.0，PAD 3.17.0，DEPLOYMENT 标头 + §7 计数，ci.yml，P27 报告。
现在进行提交前验证：占位符扫描、git status、算术检查，然后是通过 SSH 包装器进行的原子常规提交。
P27 冲刺已全部完成并推送。以下是完整概览：

## 会话 52 — P27 冲刺：已交付，所有关卡绿灯，已推送至 `main`（已远程验证）

**首先验证了理解：** 执行 `git pull` 至 `3aad8b63`；所有核心文档在代码树中重新阅读。基线复现了 9/10 个记录的关卡——并且**实时 e2e 复现为 42/43（三次）**，这是本次冲刺的头条发现。环境修复：`ledgersg_app` 密码漂移（ALTER 回到记录的默认值；8001 通过分离守护程序重启）。

**指定的关注点——移动端导航结论：按预期工作；无剩余的 TailwindCSS v4 错误**（第 22 次确定：8 个中间飞行 `translate` 样本，`transitionProperty` 携带独立的属性，Escape 键关闭）。

**根本原因隔离（追踪驱动）：** P26 搜索防抖动效果的 MOUNT-run 无条件调用了 `setOffset(0)`——在 ~600ms 窗口内的下一次点击静默恢复到缓存的第 1 页：已分发点击，offset=20 请求已应答 200，UI 返回 "Showing 1–20" 且没有第三个请求（缓存服务的还原——对 URL 计数不可见，对 mocked hooks 不可见）。隔离测试在时机上通过；完整运行在确定性地失败。

**已交付（TDD，red→green，5 个新规范文件中的 12 个新关卡）：** 分页重启现在仅在实际的 VALUE CHANGE（invoices + contacts）、ORG SWITCH（所有五个界面—— P25/FE-L3 模式）或 FILTER CHANGE（银行列表，具有稳定的 `NO_FILTERS` 默认值）时触发——绝不在计时器的 mount-run 上。两个迭代阶段的教训：linter 拒绝了渲染时间 ref 的读取（`react-hooks/refs`），现有测试套件捕获了未设防的重置双重渲染以及 absent-prop 的恒等循环。

**验证：** 后端 **1021P/0F/5S**（未触动，重新验证）· vitest **698/698（85 个文件）** · 覆盖率下限提高到 **73.39/70.72/62.38/73.95** · tsc/eslint 0 · e2e **43/43——确定性** · rls 13/13 · mobile-nav 17/17 · prod-CSP 5/5 · audit 0 critical · **全新数据库证明：一次引导 → 首次运行 = 43/43，0 跳过**。8 张像素验证的屏幕截图（168-175——标题：第 2 页保持在旧竞态窗口之后）。`.env.example` 真实；API 指南契约重新实时验证（无 API 变化）。通过常规提交 + SSH 包装器推送完成了文档事实传递（README 1762，CLAUDE 2.28.0，AGENTS 课程，SKILL 2.14.0，PAD 3.17.0，DEPLOYMENT，API 指南）——进行 dry-run，远程引用验证等于 HEAD，密钥销毁。

**建议的下一步：** 针对 SQL 级下推的冲刺，`/accounts/search/` 限制协议迁移，或专门的依赖冲刺（17 个开发层级发现）。
