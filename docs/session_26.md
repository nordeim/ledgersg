远程仓库有了一个新的提交（`ba4357d4 update session log`）。正按照指示拉取：
工作区已更新至 `ba4357d4`。现在正在制定会话计划：
AGENTS.md has been previously reviewed and last touched by my own P11 truth-pass commit. Let me focus on the new/changed docs — `session_24.md` (new from remote), the P11 report, and worklog tail:
session_24.md confirms: P11 sprint fully completed and pushed at `8ec6949b`; the repo is at post-P11 state. Now checking the skills catalog for the Tailwind v4 skill the user highlighted, plus reviewing the core docs' current state:
Now reading the most relevant repo skills for the mobile-nav / Tailwind v4 investigation:
Now examining the actual frontend mobile navigation code in the app:
Now let me examine the app's Tailwind v4 CSS setup — the likely home of the bug:
Clean v4 setup (no legacy config). Now restarting infrastructure (processes don't survive sandbox recycles) while I continue doc review:
Both PG and Redis survived the recycle. Verifying DB state and dependencies:
DBs use schema-qualified apps (core, invoicing, gst, journal, banking, coa, audit) — consistent with the documented architecture. Checking the audit trigger and whether a second DB is expected:
Audit triggers intact. Now completing the doc review (P11 report + worklog tail) while verifying build environments:
All environments persisted. Updating progress and running the baseline gates to confirm post-P11 green state:
Backend at the documented 735P/5S. Now frontend gates:
All baselines hold (backend 735P/5S, tsc 0, vitest 511/511). Now the focused audit — reading the agent-browser skill to drive the live mobile-nav check:
agent-browser 0.43.0 available. Let me check the background-terminals skill for keeping dev servers alive across tool calls:
No `bg_start` tool exposed. Let me test whether a fully-detached process survives across tool calls:
Confirmed: processes die at call end — everything (servers + browser audit) must run within a single call. Finding login credentials for the live check:
Writing the one-call live audit script (servers + browser audit must live in a single tool call):
Core mechanics verified (toggle/open/close/overlay/desktop all correct). But step 4 failed to find the nav link — investigating. Let me look at the screenshots:
I'll verify via DOM truth instead of pixels. Re-running a focused probe on the nav link mismatch:
Mystery solved — the app renders trailing-slash hrefs (`/ledger/`); with the corrected selector the nav **navigates and closes correctly**. The mobile nav core works. Now investigating the real findings — the recharts `width(-1)/height(-1)` warning:
recharts 3.7 — the -1/-1 warning is likely a known mount-time ResizeObserver artifact, but I must verify the chart actually sizes up. Checking the dashboard layout, then live-probing the SVG size at both viewports:
Chart renders correctly at both viewports (422×200 and 293×200) — the -1/-1 is transient recharts-3.x mount noise only. One anomaly remains: the toggle's computed `display:flex` (expected `inline-flex`). Settling it with a class-dump probe, plus verifying a few more v4-specific surfaces:
Key findings crystallizing. My probe-4 shots were self-inflicted (I re-clicked the already-open toggle). Real app truth so far: nav works, but **no Escape-close / focus trap / scroll lock / focus return on the mobile menu** (skill §9.4 mandatory overlay a11y). Now settling the `display:flex` anomaly — checking whether agent-browser's own injected CSS is the culprit, via the compiled stylesheet:
The mystery is settled: only `.inline-flex` and media-gated `.md:hidden` match — and `display:flex` is correct CSS **blockification of an inline-level flex item** (the toggle sits inside the flex header). Zero display bug. The mobile nav works as expected.

Now checking existing Shell tests and the e2e posture before writing the P12 plan:
The navigation e2e spec only covers anonymous routes — no authenticated mobile-nav interaction test exists. Running the remaining audit gates (e2e, coverage, build, lint parity):
ESLint shows 79 problems (36 any + 30 unused-vars + 4 set-state-in-effect) — diverging from the documented P11 parity of 47. Investigating whether the invocation differs or this is a real regression:
P10/P11 parity was scoped to touched files; the full-repo lint debt has drifted to 79 findings vs the documented 47-register. Locating the new-generation react-hooks findings:
The `[m` sequences display as eaten (same known display artifact class as prior session's CI YAML). Verifying the real bytes with python:
Display-layer artifacts can't be trusted for `[m` sequences. Checking the ground truth via git's hash comparison (immune to display mangling):
Git confirms the tree is byte-identical to HEAD — the `[m` was display-layer artifact (known class), the file is valid. The audit is complete. Now checking the API_CLI_Usage_Guide.md (this session's explicit new ask):
The guide is stale (metrics from March, no P11 truths, misleading session-persistence note). Now checking the root layout for the `data-scroll-behavior` fix target:
All audit facts gathered. Writing the P12 remediation plan:
Plan saved. Now executing Task 1 (A-1: mobile-nav overlay a11y) — TDD. First studying test conventions for mocking the auth provider:
Writing the RED test for Task 1 (A-1 mobile-nav overlay a11y):
RED confirmed (6 failed / 1 passed — exactly the documented a11y gaps). Now GREEN — implementing in shell.tsx:
GREEN — 7/7. Full vitest regression check:
Parity holds on touched files. Task 2 — the authenticated mobile-nav e2e spec. Studying the gated-spec convention:
Specs gate cleanly with reasons. Task 3 — lint-debt truth pass. Getting the exact unused-vars list:
31 mechanical findings + shell dead state. Checking the three tricky ones first:
Fix is type-equivalent. Pulling exact lines for all mechanical fixes:
All contexts verified safe. Executing the full batch of mechanical fixes:
Now the banking-client.tsx three fixes:
Badge is used — restoring its import (my edit was too aggressive):
Now payment-card, payment-list, transaction-list:
Now the dashboard apostrophe, invoices-client, loading, reports-client, client-only:
Now invoices-client, the fiscal-card test, new-organisation test, api-client tests:
Now use-toast.ts (type-only fix), middleware.ts (unused param), and shell.tsx dead state:
Now the shell.tsx dead `mounted` state and its effect:
Now the GSTF5Chart CustomTooltip hoist (A-6):
Now Task 4 — the root layout `data-scroll-behavior` attribute:
Now running the full gate chain on the changed files — lint recount, typecheck, full vitest:
79 → 45 findings; all planned classes cleared. Now typecheck + full vitest:
All gates green (tsc 0, vitest 518/518, coverage pass, build pass). Committing the work in logical units:
Both code commits in. Now the live verification phase — checking screenshot naming convention first:
A11y live-verified perfectly. The API-check org extraction failed (wrong shape assumed). Checking the real `/auth/me/` shape:
`/auth/me/` returns the user profile; orgs come from `/auth/organisations/`. Re-running the API-guide live gate with the corrected extraction:
`/auth/organisations/` returns a bare list — fixing extraction and re-running:
All 9 endpoint contracts verified live. Finding the actual dashboard endpoint name:
The dashboard endpoint is `reports/dashboard/metrics/`. Now updating the API guide with verified truths (Task 5):
Now Task 6 — DEPLOYMENT.md validation. Checking which facts drifted:
P12 adds tests — I need the true live e2e counts before patching docs. Running the full live e2e gate now (servers + suite in one call, per the sandbox constraint):
One new spec failed. Reading the error context for the true state at failure:
The failure context shows the menu still open on /dashboard — the link click was swallowed. My a11y changes likely interact with the click path. Re-running the single spec with verbose tracing:
Reproducing with event instrumentation to find what swallows the click:
The app works via DOM clicks and nothing overlays the link — so the failure is in the real-mouse-event path. Checking exactly which assertion failed:
The failure was at the `.click()` call itself (line 65) — a 30s actionability timeout. Re-running just this spec to capture the full failure reason:
**Spec bug, not app bug**: `getByRole('link', {name: 'Ledger'})` also matched the logo ("L LEDGERSG" contains the substring "LEDGER"). Fixing with exact scoping:
**36 passed / 1 skipped / 0 failed** — the live gate is fully green including all 3 new mobile-nav specs. Now patching DEPLOYMENT.md with the truthful P12 numbers:
Now the `.env.example` no-drift check:
Env examples intact — no drift. Now the docs truth pass (Task 8). Checking current doc state for P11 patterns to mirror:
README done. Now CLAUDE.md, SKILL, AGENTS.md, PAD:
Now AGENTS.md — locating the P11 patterns section to add the P12 block:
PAD updated. Verifying the screenshots are content-rich (pixel truth) before the report:
All screenshots verified (correct dimensions, content-rich, unique). Writing the P12 report:
Now the session log and worklog entry:
Now committing the remaining work:
5 commits in. Final pre-push verification (tsc covers e2e specs — they changed since last run):
All clean. Now the SSH push per the runbook:
The runbook is clear — the prior session's shim already exists in `/home/z/my-project/bin`. Verifying it and paramiko:
The dry-run hit a non-fast-forward — the remote moved. Checking:
Local is 5 ahead, 0 behind — the remote should fast-forward. Let me see the full wrapper output:
The wrapper defaults to its baked-in `ely-beauty` remote — the `--remote` flag is mandatory for this repo. Re-running correctly:
Dry-run green — auth verified, clean fast-forward of the 5 commits. Executing the real push:
Push verified (`refs/heads/main @ ee16f68 == local HEAD`), keys shredded, tree clean. Finalizing:
The P12 sprint is complete and pushed. Summary of the session:

## Sprint verdicts (the two focus questions)

1. **The mobile navigation menu works as expected** — verified live, not by inspection: toggle/overlay/open/close/navigate/auto-close/keyboard/desktop-sticky all pass at 375×812, 800×1024 and 1280×800 via agent-browser against the running dev stack, with no console errors and no horizontal overflow.
2. **No TailwindCSS v4 bug exists** — the suspicious `display:flex` on the `md:hidden` toggle was settled by a matched-rule trace through the stylesheets: only `.inline-flex` and the media-gated `.md:hidden` apply, and `flex` is correct CSS **flex-item blockification**. The v4 setup itself is clean (`@import "tailwindcss"` + `@theme`, no legacy config).

## What was remediated (TDD, [plan](/home/z/my-project/ledgersg/docs/REMEDIATION_PLAN_2026-11-23_P12.md))

- **A-1** The open menu now meets the mandatory overlay a11y contract it lacked: Escape closes, body scroll locks, focus moves in on open and returns to the trigger on close, Tab cycles within (7 vitest, 6 RED → 7 GREEN; re-verified live in the browser)
- **A-2** First authenticated mobile-nav e2e coverage (3 gated specs, all green in the live full run)
- **A-3** Lint-debt truth pass: the register had drifted to 79 findings vs the documented 47 — every mechanical class cleared, **79 → 45**, remaining debt truthfully registered
- **A-4/A-5/A-6** `data-scroll-behavior="smooth"` (Next.js warning verified gone), dead state removed, in-render tooltip hoisted
- **A-8/A-9** [API_CLI_Usage_Guide.md](/home/z/my-project/ledgersg/API_CLI_Usage_Guide.md) re-verified live (9/9 endpoint envelopes, journal mount, login contract, credit-note reversal) and rewritten to v2.5.0; DEPLOYMENT counts patched; env examples no-drift

**Final gate (all executed):** backend 735P/0F/5S (unchanged) · vitest 518/518 · typecheck 0 · coverage + build green · live e2e:full **36P/1S/0F** (37 specs) · 6 pixel-verified screenshots · docs truth pass (README P12 milestone, CLAUDE v2.16.0, AGENTS P12 patterns, PAD, SKILL v2.1.0 with lessons 51–54) · [P12 report](/home/z/my-project/ledgersg/docs/REMEDIATION_2026-11-23_P12_REPORT.md), [session 25 log](/home/z/my-project/ledgersg/docs/session_25.md), [worklog](/home/z/my-project/ledgersg/worklog.md).

**Push:** 5 conventional commits on `main` via `docs/ssh_git_wrapper_v3.py` — remote verified at `ee16f687` == local HEAD, keys shredded, tree clean.
