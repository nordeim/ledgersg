我将首先建立任务计划，并检查本地工作区状态。
The workspace exists with the repo already cloned. Let me refresh it with `git pull` and check status.
Pull brought in `docs/session_49.md`. Now let me survey the repo structure and doc sizes to plan my reading.
Session 49 confirms P25 was delivered and pushed. Now let me read the core documents. Starting with the P25 plan/report and worklog tail, plus the architecture doc.
P25 context is clear. Now let me read the core root docs — CLAUDE.md and the architecture document fully.
The persisted nesting is inefficient. Let me read the key sections of CLAUDE.md directly with targeted offsets.
Now let me read the DEPLOYMENT.md and the git-push wrapper instructions, plus check the environment state.
I have the full push procedure. Note the wrapper's default remote is stale (`ely-beauty`) — I'll pass `--remote git@github.com:nordeim/ledgersg.git` explicitly. Now let me check the environment state and the PG setup script.
Excellent — the full stack survived: PG 17, Redis, backends on :8000/:8001, Next.js on :3000, and the `bin/ssh` shim. Let me verify the database state and env configuration.
Environment is fully live (49 journal lines, 13 APPROVED docs, 3 orgs). Let me update my todos and review the skills catalog + recent P25 changes.
Now let me consult the skills catalog and review the key skills for this session's audit.
The relevant skills are confirmed (same set as P25: tdd, nextjs16-tailwind4, tailwind-patterns, agent-browser, rootless-postgresql, code-review, debugging-and-error-recovery). Now let me audit the P25 code changes in detail.
The P25 frontend changes look clean. Now the bootstrap script — the P25 headline change.
P25 切片审查完成。现在让我定位具体的 gate 命令并开始运行 baseline。
All gate commands identified. Now let me run the baseline gates — starting with the backend suite.
Backend: 1009P/0F/5S — exact match. Now the frontend gates.
All static gates exact: vitest 664/664, tsc 0, eslint 0, npm audit 0 critical. Now the named focus — the mobile-nav live audit.
17/17 on the mobile-nav audit. Now the dedicated live probe for the Tailwind v4 `translate` property bug (the P23 class of defect).
The toggle locator didn't match. Let me find the actual toggle button in the source.
**移动端导航结论（第20次确定）：按预期工作——没有剩余的 TailwindCSS v4 bug。** 中间过渡示例位于 `translate: -40.9622%`，`transitionProperty` 包含独立的 `translate` 属性，Escape 键正常关闭。现在开始 e2e 全面测试。
RLS 13/13. Now the last live gate — build:server + prod-CSP smoke.
**All 9 baseline gates green and exact.** Now let me audit the next-sprint candidate surfaces — the frontend list pages that still fetch unbounded sets (the P25 deferred register's "frontend pagination wiring").
The audit confirms: all four list pages consume unbounded sets. Let me read the full clients to size the pagination wiring work.
Let me read the backend list views to understand the contract for these surfaces.
The audit picture is forming. Let me check the remaining consumers — ContactPicker, quotes page, and the Peppol transmission-log view (the other deferred item).
The transmission log is API-only (no frontend consumer) — a clean backend scope. Let me check the data volumes and e2e spec sensitivity before finalizing the plan.
Let me examine the Peppol model, quotes client, and e2e helpers to complete the design picture.
The banking specs are testid-based and volume-safe. Let me survey the existing frontend test files to plan the RED tests.
让我检查一下银行业务页面结构和联系人选择器测试，以完善设计。
I have the complete audit picture. Let me update todos and write the P26 remediation plan.
计划已保存。现在让我对照代码库验证其余的锚点，然后再执行。
所有锚点已验证。现在进入第一阶段 —— RED。让我研究一下 P25 后端测试文件的结构，并编写 P26 后端 RED 测试。
Now I'll write the backend RED test file for the Peppol transmission-log contract.
The FK requires real documents. Let me fix the fixture to create a real document via the service (the P25 pattern).
The other org needs its own CoA. Let me check how test_accounts seeds accounts and mirror it minimally.
那个修改太草率了——让我重新调整 fixture 的结构，使其更整洁。
**Backend RED confirmed: 7 failed (the missing contract), 5 passed (the pins).** Let me verify one failure reason is exactly right.
后端 RED 状态正好因预期的原因被确认。现在进入前端 hook 的 RED 测试阶段 —— 首先是 `use-invoices.test.tsx`。
Now the `use-contacts.test.tsx` RED spec.
**Hook RED confirmed: 10 failed (new contracts), 38 passed (pins).** Now the page/component RED tests. Let me check the existing test structures first.
Now let me add the RED page/component tests to all five spec files.
Mock leakage from my new test broke the deactivate test. Let me check the file's mock reset pattern and fix.
现有的测试使用了 `mockReturnValueOnce` —— 我之前的测试使用的是粘性 `mockReturnValue`。让我来修复这个问题。
联系人现已正常显示为 RED。让我检查一下 `contact-picker` 测试，看是否需要进行 `envelope-shape` 的验证。
The picker test passed trivially — the one-shot mock got consumed then the sticky array took over on re-render. Let me make it a sticky override (the file's beforeEach resets it per test).
**RED phase complete across all tiers.** Now the e2e RED spec (T4). Let me check the invoices.spec.ts API conventions.
The hook TS errors are the expected RED. The `sr` typing needs fixing in my test code.
All remaining tsc errors are the expected RED. **Now Phase 2 — GREEN.** Starting with the backend (T5).
Now the Peppol view rewrite.
**Backend GREEN: 12/12.** Now the frontend GREEN — `use-invoices.ts` page param first.
Now the invoices-client.tsx rewiring.
I need the count-based empty branch (the P25 pattern) — let me fix that.
`navigation` 角色已通过——只是总结文本的匹配失败了。我来检查一下现有的 `table-pagination` 测试是如何匹配它的。
My test assertions used row counts, but the summary is page math (`end = min(offset+limit, count)`). Let me study the ledger beyond-end test and fix my assertions.
Now I'll fix my test assertions to the page-math semantics (mirroring the ledger patterns).
The userEvent + fake timers combo hangs. Let me rewrite with fireEvent.
The mock must switch at offset ≥ 40 with two Next clicks (the ledger pattern exactly). Fixing.
**Invoices GREEN: 12/12.** Now the contacts surface (T7).
Expected: the old mocks are array-shaped. Updating the test factory to the envelope and adapting the picker.
The picker's old tests mock the bare array. Updating their beforeEach to the envelope.
Picker 12/12. Now the banking surface (T8) — the hooks first.
Now the payment-list and transaction-list components.
The old tests assert the retired count lines. Updating them to the evolved contract.
The first script died before writing — the count-25 edit never landed. Applying it now.
**Banking GREEN: 61/61.** Now the quotes page (T9).
**Quotes GREEN: 5/5.** Now the full frontend suite to catch any remaining ripple.
The remaining 6 failures are all bare-array `useContacts` mocks in other test files. Updating them to the envelope.
双重调用源自我在 effect 中进行的 offset-reset（React 在从 effect 中退出前可能会多渲染一次）。修复方法：将 reset 操作批量处理到 debounce 超时和 filter click handler 中——不再使用单独的 effect。
Same pattern fix for the invoices page (batch the reset into the debounce tick).
**Full vitest suite GREEN: 686/686 (80 files, +22).** Now tsc + eslint.
Declaration order — `setOffset` is used before it's declared. Moving the state up.
All static gates green. Now the full backend suite and the live e2e run.
后端：1021P/0F/5S (+12)。`:8000/:8001` 上的 `--noreload` 后端必须重启才能加载新代码（P24 课程）。
Let me verify the 8001 RLS instance is configured correctly (how it runs as ledgersg_app).
All live probes green. Now the full e2e suite with the new P26 spec.
**E2E GREEN: 43/43** (42 + the new P26 spec). Let me verify the fodder stocking and idempotency.
Fodder stocked correctly (6 drafts, 21 > 20, idempotent). Now the remaining gates: coverage, mobile-nav, prod-CSP, npm audit.
**All 10 gates green on the remediated tree.** Now the fresh-DB proof (Phase 3.2) — the acceptance test for the new spec's self-sufficiency.
Fresh bootstrap: 36 lines / 12 APPROVED (the P25 guarantees hold). Now the critical acceptance — the FIRST e2e run on the fresh DB.
**THE FRESH-DB PROOF: 43/43, 0 skipped, on the FIRST run.** Let me verify the self-stocked fodder on the fresh org.
The proof is complete — fodder self-stocked (13 + 8 drafts = 21 > 20). Now the screenshots. Let me check the session-48 capture script as the model.
All 8 captures OK with DOM truths. Now the non-blank pixel verification per repo convention.
All captures verified (0.35–0.62 non-uniform). Now the `.env.example` truth verification.
`.env.example`s verified truthful — no changes needed. Now the docs truth pass. Let me locate the exact spots in README.
Now the docs truth pass — starting with README (badge, counts, the P26 milestone).
Now CLAUDE.md — version bump, status header, and the P26 milestone.
The embedded double quotes broke the string. Retrying with proper quoting.
Now AGENTS.md — the header gate row and the P26 lessons.
Now the P26 lessons section (appended after the P25 lessons).
Now ledgersg_SKILL.md, PAD, and ci.yml.
Now the API guide — version bump and the P26 addendum.
Docs truth pass complete. Now the P26 report.
Now the session log and the worklog entry.
Now the pre-commit verification — git status, placeholder scan, and the final arithmetic check.
All checks pass. Now the atomic conventional commits.
所有 5 个提交已完成，工作区干净。现在通过 SSH 包装器进行推送 —— 首先进行 shim 和 paramiko 检查。
Dry-run authenticated — remote at `334c2f0e`, fast-forward to `245d9460` negotiated. Now the real push.
P26 冲刺周期已全部完成并推送。以下是完整概览：

## 会话 50 — P26 冲刺：已交付，所有关卡绿灯，已推送至 `main` @ `245d946`（已远程验证）

**首先验证了理解：** 执行 `git pull` 至 `334c2f0e`，环境从上次会话中完好保留（PG 17 / Redis / 技术栈 — 已重新探测），并对照代码树重新阅读了所有核心文档。**基线重现了 9/9 个已记录的关卡，完全一致** — 这是自 P24 规范落地以来的首次完全重现。

**特别关注 — 移动端导航结论：按预期工作；无残留的 TailwindCSS v4 错误**（第 20 次判定：航班中样本在 `translate` 时为 `-40.9622%`，`transitionProperty` 包含了独立的 `translate` 属性，Escape 键将其关闭）。

**审计（模式 C）：0 严重 / 0 高危 / 4 中危 / 2 低危** — 四个未分页的前端界面 + Peppol 传输日志（最后一个未绑定边界的后端列表）。已通过 [P26 计划](/home/z/my-project/ledgersg/docs/REMEDIATION_PLAN_2026-11-28_P26.md)交付，并在执行前进行了锚点验证。

**已交付（TDD，先红后绿）：** invoices/contacts/payments/transactions/quotes 上的服务端分页（大小为 20，共享 `TablePagination`，每个 hook 的 queryKey 页面身份）；invoices 搜索已迁移至服务端；`useContacts` 返回 envelope；Peppol 日志使用 `id` 平局决胜（tiebreaker）+ 单查询计数器加入了 `?limit=&offset=` 协议（未分页字节完全一致）。

**验证：** 后端 **1021P/0F/5S** · vitest **686/686 (80 个文件)** · 覆盖率绿灯（棘轮指标*提高*） · tsc/eslint 0 · e2e **43/43** · rls 13/13 · mobile-nav 17/17 · prod-CSP 5/5 · 审计 0 严重 · **全新数据库证明：一次引导 → 首次运行 = 43/43，0 跳过**（新规范自备其测试数据）。8 张经像素验证的屏幕截图（160-167）。`.env.example` 已重新验证，确保真实。通过 5 次常规提交 + SSH 包装器推送完成了文档一致性检查（README 1750, CLAUDE 2.27.0, AGENTS 课程, SKILL 2.13.0, PAD 3.16.0, [DEPLOYMENT](/home/z/my-project/ledgersg/docs/DEPLOYMENT.md), [API guide 3.5.0](/home/z/my-project/ledgersg/API_CLI_Usage_Guide.md), [worklog](/home/z/my-project/ledgersg/worklog.md)） — 进行了空运行（dry-run），远程引用（remote ref）已验证等于 HEAD，密钥已销毁。

**建议的下一步：** 针对五个服务驱动列表的 SQL 级下推（push-down），`/accounts/search/` 的限制协议迁移，或专项依赖冲刺（17 个 dev-tier 发现）。
