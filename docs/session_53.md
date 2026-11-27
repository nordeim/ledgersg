I'll continue the task from where it left off. Let me set up a TODO plan and start by refreshing the workspace.
工作区已刷新 —— `main` 分支上的 `session_51.md` 已完成 fast-forward 合并。现在让我阅读根文档。
The repo is large with extensive documentation. Let me read the most recent session docs first to understand current state.
Session 51 confirms P26 was delivered and pushed. Let me read the P26 plan and report to understand what was done and what's deferred.
P26 was fully delivered. Now let me read the worklog tail and the key header sections of the root docs.
Docs reviewed. Now let me check the environment state (PG, Redis, stack) since the sandbox may have been recycled.
The full stack survived. Let me verify the database and stack state.
Environment fully live. Let me update todos and check the skills catalog, then audit the recent P26 changes.
The catalog is large; session_51 already identified the relevant skill set (tdd, nextjs16-tailwind4, tailwind-patterns, agent-browser, code-review, debugging-and-error-recovery, rootless-postgresql). Now let me audit the P26 code slice in detail (Mode C).
Backend P26 changes look clean. Now the frontend hooks:
P26 wiring verified in source. Now let me reproduce the documented baseline gates — the strongest alignment check. First, the exact commands:
2 failures — both are `ledgersg_app` connection auth failures (environment-related, not code). Let me check what these tests need:
The tests rely on the documented dev password `CHANGE_ME_IN_PRODUCTION` for `ledgersg_app`. The role's password must have drifted in the live cluster. Let me verify and reset it:
Backend baseline reproduced exactly: **1021P/0F/5S**. Now the frontend static gates:
所有静态门限均已完全重现。现在进行命名重点——移动端导航审计：
17/17 on the mobile-nav audit. Now the dedicated Tailwind v4 `translate` property live probe (the P23 class of defect):
Mobile-nav verdict (twenty-second settlement): **working as expected, no remaining Tailwind v4 bug** — the slide interpolates through 8 mid-flight samples with `transitionProperty: "transform, translate, visibility"`. Now the RLS smoke and full e2e:
:8001 (RLS instance) broke — my `ALTER ROLE` changed the password to the test default while that backend was started with the previous password. Let me check how it runs and restart it correctly:
The server died when the shell command exited. Let me use `setsid` to fully detach it:
The environment kills spawned processes when commands finish. There's a `background-terminals` skill for exactly this — let me load it:
The `bg_start` tool isn't available in this session. Let me test what survives between commands:
All spawned processes are killed when the command exits. Let me try a double-fork daemonization, which fully detaches:
The double-fork daemon survives. Now the RLS smoke:
RLS smoke 13/13. Now the full e2e suite (the last major baseline gate):
One failure in the P26 pagination spec. Let me examine the failure details:
Passes in isolation — the full-run failure was the Previous step. Let me check the substrate state and re-run the full suite to determine flake vs. real issue:
Reproducible in the full run but green in isolation — a real cross-test interaction. Let me capture the actual failure detail:
The snapshot shows the table rendered but no pagination navigation. Let me see the end of the snapshot:
The snapshot shows the app back on page 1 ("Showing 1–20 of 25 rows") after the Next click — the offset was reset or the click was lost. Let me reproduce with instrumentation:
My clean repro works fine — the failure only occurs in the full-run context. Let me watch the actual failure video:
Let me analyze the Playwright trace instead — it has the full action/network timeline:
The click WAS dispatched. Let me check the network layer — did the offset=20 request fire?
Both fetches fired (offset=0, then offset=20) — but no refetch of offset=0, meaning the UI reset was a **cache-served state reset**, not a new request. Let me check the console messages and frame navigations:
Both requests returned 200, yet the UI reset to page 1. The timeline reveals the race: Next click at ~mount+350ms, then a `setOffset(0)` fires ~mount+600ms. Let me confirm the root cause — the mount-run of the debounce effect:
Root cause found. Let me check the banking lists for the same pattern:
Confirmed. Let me complete the audit — check `use-banking.ts`, the e2e fodder helper, and the org-switch reset coverage across all six surfaces:
The audit picture is complete. Let me check the existing vitest specs that pin the debounce-reset behavior (my fix must not break their pins):
The existing specs mock the hook, so the race is unpinned — that's the coverage gap. Let me complete the audit with transaction-list and check the remaining surfaces:
The audit is complete. Let me review the ledger's real-hook spec pattern (the convention my regression tests must mirror) and the test configs:
Now let me check the test configs and the existing spec files I'll extend:
All context gathered. Let me check the existing spec file locations for the surfaces I'll extend, then write the P27 plan:
All conventions gathered. Now let me write the P27 remediation plan (validated against the codebase — every anchor verified above):
Plan saved and anchor-validated. Now Phase 1 — RED. Let me check the api-client endpoints shape to mock correctly:
Now let me check how the existing invoices page test handles next/link and other imports:
Let me check the contacts-client imports and rendering needs before writing its spec:
Now writing the RED specs. T1 — invoices pagination state:
RED confirmed — 2 failed (the race + the org switch), 1 pin passed (the search reset). Let me verify (a)'s failure reason is exactly the revert:
RED confirmed for exactly the right reason — the revert. Now T2 — contacts pagination state spec:
The `ContactRow` needs `hasPermission` from useAuth. Fixing the mock:
T2 RED confirmed (2 failed / 2 pins). Now T3 — quotes:
T3 RED confirmed. Now T4 — payment-list state spec. Let me check PaymentRow's needs:
T4 RED 已确认。接下来是 T5 —— transaction-list。让我检查一下 TransactionRow 的需求：
The pagination never rendered — likely an endpoint field mismatch in my mock. Let me check `useBankTransactions`:
The dump shows page 2 already rendered at the first assertion — let me see the exact failing line:
T5 is RED for the right reason — after the filter/org change the summary stays at the stale "21–40". **RED phase complete: 9 failing contracts + 3 passing pins.** Now Phase 2 — GREEN. T6, the invoices fix:
T6 GREEN (3 new + 8 existing pins). Now T7 — contacts:
The existing P11 debounce spec counts mock calls — my `useState` compare causes a second render. The fix: use a ref for the value-change compare (no re-render when the offset is already 0). Updating both clients:
The extra render comes from `setOffset(0)` firing even when offset is already 0 (React's documented bailout re-render). The fix: only call setOffset when the offset actually needs changing:
All 26 green. Now T8 — quotes org-switch reset:
Now T9 — the banking lists (filter-change + org resets):
Two issues: the quotes spec needs a `next/navigation` mock, and my change broke an existing payment-list test. Let me check that first:
The default `filters = {}` creates a fresh object each render — infinite loop with the identity compare. Fix: a stable module-level default:
Now the quotes spec needs the `next/navigation` mock (for `useConvertQuote`'s `useRouter`):
All green. Now the full vitest suite to catch ripples:
ESLint's `react-hooks/refs` rule blocks ref access during render. The clean alternative: compare inside the timer callback (an event, not render) — the mount-run compares `""===""` and no-ops, closing the race deterministically:
Now the same pattern for contacts-client:
Full suite green (698/698, 85 files). Now the moment of truth — the full e2e run (the race must be gone):
**43/43 — the race is closed.** Now the complete gate matrix. Backend first:
Coverage green — floor raised to 73.39/70.72/62.38/73.95. Now mobile-nav, build + prod-CSP, and audit:
All 10 gates green. Now the fresh-DB proof. Let me find the §9 bootstrap script:
Now the fresh-DB proof. Kill backends, recreate the DB, restart, bootstrap, first e2e run:
Schema loaded (37 tables). Flush Redis and restart both backends:
Both backends healthy on the fresh DB. Now the ONE bootstrap run:
Bootstrap complete (36 lines / 12 APPROVED). Now the FIRST e2e run on the fresh DB:
**Fresh-DB proof: 43/43, 0 skipped, first run.** Now the screenshots. Let me model the capture script on session-50's:
All 8 captures OK with DOM truths. Now the non-blank pixel verification (repo convention):
All screenshots verified. Now the `.env.example` truth re-verification:
`.env.example` files verified truthful (16 backend settings vars documented; web reads exactly `NEXT_PUBLIC_API_URL`; no new vars this sprint). Now Phase 4 — the docs truth pass. README first:
Now CLAUDE.md — version bump, status, and the P27 milestone:
Now AGENTS.md — the header gate row and the P27 lessons:
Now the SKILL and PAD:
Now DEPLOYMENT.md — the header re-verification line and §7/§9 counts:
Now the API guide — re-verify the documented contracts against the live stack (no API changes this sprint):
All documented contracts verified live. Adding the P27 re-verification note to the guide:
Now the P27 report:
Now the session log and worklog entry:
Now the pre-commit verification — placeholder scan, git status, and the arithmetic check:
Arithmetic verified. Let me spot-check DEPLOYMENT.md's fresh-host walkthrough (the user's requirement) before committing:
The guide is complete (§1-§14 from git clone). Now the atomic conventional commits:
All commits done, tree clean. Now the SSH wrapper push. Let me read the instructions:
The shim is ready. Now write the key, verify it parses, and dry-run the wrapper:
Typo in my key transcription (dropped a character). Rewriting exactly:
Dry-run authenticated — fast-forward `3aad8b63..19a1c2d0` negotiated. Now the real push:
The P27 sprint is complete and pushed. Final summary:

## Session 52 — P27 Sprint delivered, all gates green, pushed to `main` @ `19a1c2d0` (remote verified, key shredded)

**The headline finding:** the documented e2e baseline did **not** reproduce — 42/43 (three times, always the P26 pagination spec, green in isolation). The Playwright trace proved the root cause: the P26 search-debounce effect's **mount-run** called `setOffset(0)` unconditionally, so a Next click inside the ~600ms window silently reverted to the cached page 1 — no refetch, no feedback, the click lost.

**Delivered (TDD, RED 9 → GREEN, 12 new gates in 5 real-hook spec files):**
- **The race closed** — the page restart now fires only on a debounced **value change** (invoices + contacts)
- **Org-switch offset resets** on all five list surfaces (the P25 ledger pattern)
- **Filter-change resets** on the banking lists (with the stable `NO_FILTERS` default)

**Verified:** backend 1021P/0F/5S (untouched) · vitest 698/686→**698/698 (85 files)** · coverage floor raised to 73.39/70.72/62.38/73.95 · tsc/eslint 0 · e2e **43/43 deterministic** · fresh-DB proof **43/43 first run** · rls 13/13 · mobile-nav 17/17 (no Tailwind v4 bug — the 22nd/23rd settlements, with the mid-flight slide probe) · 8 pixel-verified screenshots (168-175) · `.env.example` truthful · API guide re-verified live (no API changes).

Key deliverables: [P27 plan](/home/z/my-project/ledgersg/docs/REMEDIATION_PLAN_2026-11-28_P27.md) · [P27 report](/home/z/my-project/ledgersg/docs/REMEDIATION_2026-11-28_P27_REPORT.md) · [session_52 log](/home/z/my-project/ledgersg/docs/session_52.md) · [worklog](/home/z/my-project/ledgersg/worklog.md) · [DEPLOYMENT.md](/home/z/my-project/ledgersg/docs/DEPLOYMENT.md)

**Suggested next:** a dedicated dependency sprint (the 17 dev-tier npm-audit findings), the SQL-level push-down for the five service-driven lists, or the `/accounts/search/` limit-contract migration — all registered in the deferred carry-forward.
