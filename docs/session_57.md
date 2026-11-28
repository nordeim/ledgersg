工作区已刷新 — P28 已由 session-54 完成，且 session_55 刚刚添加。本次会话将生成 **P29**。我来制定任务计划。
现在让我阅读核心文档。AGENTS.md 的篇幅最大（1974 行）——我将阅读其页眉和页脚（最近的经验教训），以及完整的 CLAUDE.md 和其他文档。
Let me read the AGENTS.md tail (recent sprint lessons) and worklog tail to complete my picture.
文档读取已完成。现在让我阅读 P28 计划的延期登记册（P29 候选方案），并检查环境状态（沙箱可能已被回收）。
环境已完全保留 — PG 17、Redis、两个后端 (:8000/:8001) 以及 `next dev` (:3000) 均在运行中。让我验证一下健康状况，并检查正在运行的代码是否为 P28-current。
全部状态正常。现在让我阅读 `skills` 目录以选择合适的审计技能，然后复现文档中记录的基线。
Skills confirmed available. Now let me reproduce all documented baselines — the strongest alignment check. Starting with the backend suite:
Backend baseline exactly reproduced: 1025P/0F/5S. Now the web gates:
Static gates green. Now the live e2e suite (43/43 expected, ~2.3m):
e2e 43/43 deterministic. Now the RLS smoke and mobile-nav audit:
Scripts live at repo root. Running them from there:
All 9 documented gates reproduce exactly. The mobile-nav focus is settled (26th settlement): working, no Tailwind v4 bug. Updating todos and moving to the audit phase.
Let me examine the full current view code for the pagination paths:
P28 slice verified consistent. Now the vitest/playwright config state (the standing test-suite task) and the per-glob coverage numbers (the P29 candidate):
The vitest/playwright suites are fully in place. Now let me measure the per-glob coverage numbers (the P29 candidate #1) and check the playwright config:
The whole-suite floor matches exactly (73.39/70.72/62.38/73.95). Now let me compute the exact per-glob aggregates from the JSON summary:
Key findings emerging: the per-glob tiers still sit at P20 values (hooks branches: 36 configured vs 51.16 measured — a 15-point rubber stamp), and `src/shared/**` has **no tier gate at all**. Let me check the ruff register and hunt for other findings:
Ruff 显示 1310 个检测结果（包含测试文件）。让我检查一下 ruff 是否在任何地方被用作校验门槛，并查看 CI 工作流：
Ruff 是一个 `make lint` 便利工具，而非 CI 门禁（已登记的债务）。让我检查一下 CI 门禁和已登记的 N+1 候选问题：
Detail N+1 is real but bounded (single-entry surfaces). Now let me hunt for the same class at LIST scale — serializers with nested `source=` access whose querysets lack select_related:
The invoice document detail has the same N+1 class (8 serializer call sites, 2 FKs per line). Let me sweep all detail services systematically:
The detail-N+1 class is confirmed across three surfaces. Let me check the remaining registered candidates — `/accounts/search/` and the capped-default flip:
GST/COA lists are bounded domains without pagination contracts — by design. Let me verify the playwright config and check a few more detail surfaces:
status_history is timestamp-synthesized (no queries). The audit picture is complete. Let me check for existing tests that pin query counts on these surfaces (blast radius), and the InvoiceLine/JournalLine model relations:
所有模型关系（FKs）已验证。我来检查一下 `get_document`/`get_entry`/`PaymentService.get` 的所有使用者，以了解其影响范围：
The consumer map is complete. Let me read the P28 spec to mirror its conventions for the RED specs:
我已获取 P28 规范模式。我来验证一下 RED 规范的详细端点 URL：
All anchors verified. The audit is complete — now writing the validated P29 plan:
Plan saved. Now Phase 1 — RED. Let me check the conftest fixtures first:
Journal entries need ≥2 lines. Let me verify the Account/TaxCode table anchors for the query filter:
The allocation serializer also walks `document` per row — another N+1 in the payment detail view. Let me check `get_allocations`:
`get_allocations` 已经对 document 进行了 select_related——payment N+1 为 contact+bank_account（已修复）。现在让我检查一下 RED spec 的 fixtures：
Now writing the RED spec:
Now the RED run — the specs must fail for exactly the right reason (the per-line walks):
Fixture date misalignment — let me check the fiscal period fixture's date range:
文档和支付对于完全正确的原因显示为 RED（3 次账户遍历；单表支付获取）。日志 URL 返回 404 —— 让我检查一下实际的前缀：
RED 已确认 — 所有 3 个规范都因完全正确的原因失败（3 次账户遍历、3 次账户遍历、单表支付获取）。现在进入第二阶段 — GREEN。让我读取这三个服务方法：
The journal list already prefetches plain `lines` — let me check whether its list serializer walks account per line (a potential list-scale N+1 P28 missed):
List surface is clean (no account walks). Now the GREEN edits — all three service seams:
Now the journal service:
Now the payment service:
Now the GREEN verification:
GREEN 3/3. Now the full backend suite for ripples:
Backend 1028P/0F/5S (+3), every pin holds. Now T6 — the per-glob ratchet raise:
Coverage exit 0 at the raised floors. Now Phase 3 — restart the backends on remediated code and run the full matrix:
Both backends healthy on remediated code. Now the live gates — RLS smoke + full e2e:
All 11 gates green on the remediated tree. Now the screenshots — let me review the session-53 capture script to model on:
现在让我检查一下 P29 截图相关的详情页面存在哪些前端路由：
Now writing the session-55 capture script:
All 8 captures OK. Now the non-blank pixel verification:
All 8 pixel-verified. Now the `.env.example` truth verification (the config-readers sweep):
`.env.example`s verified truthful. Now the live API contract re-verification (the byte-identical proof on the detail endpoints):
All contracts verified live. Now the docs truth pass — starting with README:
Now updating README — badge, status rows, P29 milestone, counts:
The Backend row still says 1025 — fixing:
README done. Now CLAUDE.md — version bump + status + P29 milestone:
CLAUDE.md 已完成。接下来是 AGENTS.md —— 头部准入行 + P29 教训：
Now the P29 lessons section in AGENTS.md (before the P28 lessons):
接下来是 SKILL、PAD、DEPLOYMENT、API guide 和 ci.yml：
Now PAD, DEPLOYMENT, and ci.yml:
Now the DEPLOYMENT.md header re-verification:
Now the API guide re-verification note:
One unclosed paren — fixing the balance:
All docs updated. Now the P29 report:
Now the session log and worklog entry:
Now the pre-commit verification — placeholder scan, git status, arithmetic:
All TODO hits are pre-existing historical references. Now the atomic conventional commits:
所有 5 个提交已完成，工作区干净。现在进行 SSH 封装推送 —— 首先先阅读说明：
Dry-run authenticated — fast-forward `6f398bf3..49e5c3c0` negotiated. Now the real push:
P29 sprint 已完成并已推送 —— 远程 `main @ 49e5c3c0` 已验证与本地 HEAD 一致，部署密钥已销毁，无残留。

## 已交付内容

**基准线优先。** 工作区已刷新至 `6f398bf3`；所有 9 个已记录的测试关卡均已完全复现（后端 1025P/0F/5S，vitest 698/698，tsc/eslint 0，e2e 43/43 首次运行即确定性通过，rls 13/13，mobile-nav 17/17，translate 探测通过 PASS，npm audit 0）。环境（PG 17，Redis，双后端，next dev）运行正常，无需修复。

**核心关注点已解决（第 26/27 次）：** 移动端导航菜单**按预期工作 —— 没有残留的 TailwindCSS v4 bug**（7 个飞行中的 translate 采样，独立的属性存在于 transition 列表中，Escape 键可关闭）。

**审计发现了 3 个实际问题，均已通过 TDD 修复：**
- **详情视图 N+1（核心重点）：** 三个详情接合点（文档、日志条目、支付）获取其行数据时使用了普通的 `.get()`，而序列化器在每行中遍历 FKs —— 一个 5 行的发票详情在需要 3 个查询的地方却消耗了 14 个查询（包括 PDF 上下文在内的 8 个调用点）。现在：contact 使用 `select_related`，lines 在一个 JOIN 查询中携带 account + tax_code 进行预取，支付时 JOIN 其相关行 —— **字节完全一致的负载**，由 3 个新的查询计数门控固定（RED 运行证明了遍历的存在）。
- **每个 glob 的覆盖率的 ratification 检查：** 五个层级仍持有 P20 的值（hooks 分支比实际值低了 **15 个百分点**）—— 全部提升至测量底线，外加新的 `src/shared/**` 层级（此前完全未进行门控）。
- 验证了 vitest + playwright 测试套件的完整性和即时性（698 + 43 个规范）；本次 sprint 在其中增加了 3 个后端门控。

**最终测试关卡：** 后端 **1028P/0F/5S** (+3) · vitest 698/698 · 提升后的每个 glob ratchets 下覆盖率为绿色 · e2e 43/43 · prod-CSP 5/5 · 字节完全一致的详情契约已实时重新验证 · 8 张像素验证截图 (184-191) · `.env.example` 验证无误 · 完整的文档真实性检查（README 徽章 1769，CLAUDE 2.30.0，AGENTS +3 课，SKILL 2.16.0，PAD 3.19.0，DEPLOYMENT，API 指南，ci.yml）—— 包含在 `main` 分支上的 5 个原子提交中。

**建议的下一步**（已在注册表中）：`/accounts/search/` 限制契约迁移、ruff 机械批处理（936 个发现 —— 需要经过审查的 sprint）或审计日志 INSERT 策略。
