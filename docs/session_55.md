Workspace exists. Let me refresh it with git pull and check the current state.
P27 已完成；新的拉取仅带来了 `docs/session_53.md`。我来建立一个任务计划，并阅读所有关键文档。
session_53 is the transcript of the P27 sprint. Now let me read session_52, the P27 plan/report, and the worklog tail.
P27 的故事已经明确。现在让我查看工作日志的最后部分，并评估环境状态（PG、Redis、stack），因为沙盒可能已被回收。
Environment survived fully: PG 17, Redis, backends on :8000/:8001, next dev on :3000. Let me read the persisted CLAUDE.md and verify DB/backend health.
Only 7 tables in public — unexpected (docs say 37). Let me investigate the schema layout.
Database is fine — tables live in per-app schemas (core/gst/banking/invoicing/coa/journal/audit); Django sees 36 tables. Environment is fully operational with no password drift. Let me review the remaining root docs' key sections.
现在让我查看 AGENTS.md 的头部数据和 P27 代码差异，以开始审计。
Full picture acquired. Now let me reproduce the documented baselines — the strongest alignment check. I'll start the backend suite in the background while auditing the P27 diff.
The P27 diff is consistent. Now let me hunt for the same defect class elsewhere — any remaining debounce+reset patterns P27 might have missed.
Ledger is clean (no search). Let me check the contact-picker and the utils debounce for the same class of issue.
Contact-picker is clean. Let me check the backend baseline result.
nohup 后台任务在 shell 退出时被终止（沙箱回收了进程组）。正在前台运行测试套件并设置适当的超时时间：
Backend baseline reproduced exactly: 1021P/0F/5S (30.15s). Now the frontend gates:
ESLint must run from `apps/web` (config lives there). Let me verify the documented command:
All static gates reproduced (backend 1021P/0F/5S, vitest 698/698, tsc 0, eslint 0E/0W). Now the e2e config check and full run:
e2e 43/43 — the P27 fix holds deterministically. Now rls_smoke, mobile-nav audit, and npm audit:
17/17 mobile-nav audit (24th settlement). Now the dedicated Tailwind v4 `translate` live probe:
Let me check the e2e helpers for the correct login credentials/selectors:
Mobile-nav verdict (24th settlement): working as expected, no Tailwind v4 bug — the slide interpolates through 7 mid-flight samples. Now npm audit:
All 8 baseline gates reproduce exactly. Now the deeper audit for the P28 scope — let me examine the three registered candidates: the 17 dev-tier npm-audit findings, the SQL push-down, and the accounts/search limit contract.
All 17 are dev-tier. Let me check the SQL push-down candidate — the five service-driven lists:
Found the push-down candidate: `len(contacts)` materializes every row for the count. Let me check all five call sites and the page_envelope:
Key discovery: the services return **materialized Python lists** — every paginated request fetches ALL rows, then slices in Python. This is the registered push-down candidate. Let me check the banking services and the accounts/search endpoint:
The accounts/search endpoint requires alignment (count = slice length, not total). Let me dry-run the dependency fix and spot-check the banking hook:
All dev-tier confirmed. Let me check the accounts/search frontend consumer to size candidate C:
Frontend never calls `/accounts/search/` — candidate C is low value. The P28 scope: **SQL push-down (headline) + dev-tier dependency closure**. Let me map all consumers of the four service methods:
Only the views consume these services in production. Let me check how tests use them (list vs queryset semantics):
Tests use `len()` and indexing — both work on querysets. Let me check the serializers for related-field access (N+1 risk) and the payment service queryset:
All four services already carry select_related (P17). Let me do a final consumer sweep, then check the vitest/playwright configs for the test-suite task:
Only the two list call sites consume the list methods. Let me verify the vitest config state (the standing test-suite task item):
Discrepancy: the P27 report claims the coverage floor was raised to 73.39/70.72/62.38/73.95, but the config shows the P20-era 71/60/68/71. Let me check the history:
The config hasn't changed since P20, yet P21–P27 reports claim raised floors. Let me check how coverage actually gates:
Measured coverage (73.39/70.72/62.38/73.95) exceeds config floors (71/68/60/71) — the P21–P27 reports claimed raised floors but never bumped the config. That's a finding. Let me get the per-tier values:
Let me find the existing P24 pagination API tests to mirror their fixtures for the RED specs:
我已获取 `fixture` 模式。让我验证这四个列表表的实际数据库表名，以便进行 SQL 断言：
All audit inputs gathered. Updating todos and writing the validated P28 plan:
Plan saved with every anchor pre-verified. Let me do the final plan-validation pass (the transactions URL + the CaptureQueriesContext import path), then start Phase 1 RED:
All patterns gathered. Writing the RED spec:
RED: 4/4 failed. Verifying the failure reason is exactly the push-down gap:
RED confirmed for exactly the right reason — the unbounded SELECT. Phase 2 GREEN. Let me read the service tails to edit:
Now the GREEN edits — all four services return lazy querysets:
Now the banking services:
Services done. The view edits are minimal — `len(qs)` → `qs.count()` (the slice on a queryset already renders SQL LIMIT/OFFSET):
All six files edited. Now the GREEN verification — run the RED specs:
GREEN 4/4. Now the full backend suite for ripples:
Backend 1025P/0F/5S — all existing pins hold. Now T5, the coverage ratchet raise:
Now T6 — the dependency closure (`npm audit fix`):
0 vulnerabilities across dev+prod. Now the web gate matrix on the bumped tree — coverage with the raised ratchet first:
All web gates green. The e2e needs the backends restarted (they run `--noreload` with pre-fix code). Let me check the daemonize helper:
Both backends healthy on remediated code. Now RLS smoke + the full e2e:
e2e 43/43. Now the mobile-nav re-settlement and the production build + CSP smoke (the toolchain changed):
All gates green. Now the screenshots — let me model on the session-52 capture script:
让我检查一下 `quotes surface` 的 DOM 以进行捕获：
One shot timed out (likely quotes). Let me check the quotes page rendering conditions:
Let me add progress logging to identify the failing shot:
The quotes shot fails — the substrate has 0 quotes right now. Let me check how the e2e P26 spec stocks its fodder:
Patching the capture script with a count-driven quote fodder helper (the P26 convention):
仍然在 179 处失败。让我检查一下 `quotes-client` 实际上是如何查询 API 的：
The quotes page queries `type=SALES_QUOTE`, not `QUOTE`. Let me check the document type choices:
Count is 0 for SALES_QUOTE. Let me check whether my earlier POST created a stray "QUOTE"-typed document:
RLS blocks direct psql. Using the postgres superuser:
The helper queried `document_type=` which the backend silently ignores (it reads `type=`) — so count was 24 and it returned early. Fixing to use the real param and type:
All 8 captures OK. Now the non-blank pixel verification (repo convention):
The glob missed 180-182. Fixing:
All 8 captures verified. Now the `.env.example` truth re-verification:
`.env.example`s verified truthful. Now the API guide live re-verification against the remediated stack (the byte-identical proof):
The beyond-end contract verifies. Let me check a mid-set page and the Peppol log envelope:
All contracts byte-identical. Now the docs truth pass — starting with README:
Updating README — badge, status rows, the P28 milestone, and test counts:
README done. Now CLAUDE.md — version, status, milestone block:
Now the CLAUDE.md milestone block:
Now AGENTS.md — the header gate row and P28 lessons:
Now SKILL, PAD, DEPLOYMENT, API guide, and ci.yml:
Now DEPLOYMENT.md header and counts:
DEPLOYMENT.md done. Now the API guide re-verification note:
Now the P28 report:
Now the session log and worklog entry:
All docs updated. Now the pre-commit verification — placeholder scan, git status, arithmetic:
The PNG "placeholder" hits are binary false-positives. Verifying the new text files are clean:
All clean, `.env.example`s tracked and truthful. Now the atomic conventional commits:
All 5 commits done, tree clean. Now the SSH wrapper push — reading the instructions first:
I have the wrapper procedure. Let me check the ssh binary, the wrapper, and the remote:
A real `ssh` binary exists; the wrapper needs the `--remote` override (its default is stale). Writing the key and verifying it parses:
Key parses (ed25519). Dry-run with the remote override:
No system ssh — but `/home/z/my-project/bin/ssh` exists (the prior session's shim). Let me verify it:
The shim and paramiko are ready. Running the dry-run with the shim on PATH:
Dry-run authenticated — fast-forward `ad8b3b47..dfcde539` negotiated. The real push:
Push verified — remote `main @ dfcde53 == local HEAD`, key shredded, no residue. Final todo update:
The P28 sprint is complete and pushed to `main` @ `dfcde539` (remote ref verified equal to HEAD; the deploy key shredded after use).

## What was delivered

**Understanding & baseline first.** Workspace refreshed to `ad8b3b47`; all core docs re-read and validated against the code. The environment (PG 17, Redis, both backends, next dev) was live with no repair needed, and **all documented gates reproduced exactly** — backend 1021P/0F/5S, vitest 698/698, tsc/eslint 0, e2e 43/43 deterministic, rls 13/13, mobile-nav 17/17.

**The named focus settled (24th/25th times):** the mobile navigation menu **works as expected — no remaining TailwindCSS v4 bug**. A dedicated live `translate` probe sampled 7 mid-flight values through the drawer slide; the transition list carries the standalone `translate` property; Escape closes.

**The audit found 3 real issues, all fixed via TDD:**
- **The SQL push-down (headline):** the four service-driven lists (contacts, documents [invoices + quotes], payments, bank transactions) fetched the **entire table on every page request** and Python-sliced. Now lazy querysets + SQL `COUNT(*)` + SQL `LIMIT/OFFSET`, byte-identical envelopes — pinned by 4 new `CaptureQueriesContext` gates (RED runs proved the unbounded fetch).
- **The honest ratchet:** the coverage config still held P20-era floors while reports claimed raises — now actually written in (71/60/68/71 → 73/62/70/73).
- **The dependency closure:** all 17 dev-tier npm-audit findings closed with in-range bumps; `npm audit` now **0 across dev+prod**.

**Final gates:** backend **1025P/0F/5S** (+4) · vitest 698/698 · coverage green at the raised ratchet · e2e 43/43 · prod-CSP 5/5 · API contracts re-verified live (byte-identical) · 8 pixel-verified screenshots (176-183) · `.env.example`s verified truthful · full docs truth pass (README badge 1766, CLAUDE 2.29.0, AGENTS +3 lessons, SKILL 2.15.0, PAD 3.18.0, DEPLOYMENT, API guide, ci.yml) + [P28 plan](https://github.com/nordeim/ledgersg/blob/main/docs/REMEDIATION_PLAN_2026-11-28_P28.md), report, session log, and worklog — all in 5 atomic conventional commits on `main`.

**Suggested next** (registered in the deferred carry-forward): the per-glob coverage-tier raise, the `/accounts/search/` limit-contract migration (no frontend consumer today), or the ruff mechanical batch (936 production findings).
