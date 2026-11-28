I'll continue the task from where we left off. This is a re-sent instruction with document references updated to session_58/P30/session_59, which means the P30 remediation round was already completed by a previous session — so this round's plan should be **P31**. Let me start by checking the workspace state.
The repo exists. Let me check its git status and pull the latest changes.
Workspace refreshed — pulled in `docs/session_59.md`. Let me set up the task plan and then read the key documents.
These are large files. Let me read the persisted outputs in sections.
Let me read the remaining key sections of AGENTS.md and CLAUDE.md efficiently.
Now let me read the CLAUDE.md briefing's key sections (commands and current state).
P30 complete and pushed. This session will produce **P31**. Let me read the P30 plan/report for conventions, plus worklog tail.
Now let me check the worklog tail and the README status table.
Now I have full context: **session 60 → P31 sprint**. The P30 report's suggested next: the ruff semantic batch (B904 ×66), the tests/-tree lint batch (379), or the audit-log INSERT policy. Let me check the environment state first (the sandbox recycles processes between sessions).
PG, Redis, and next dev survived; the backends are down and the venv isn't at `/opt/venv`. Let me find the actual venv location and the setup scripts.
Found the venv at `apps/backend/.venv`. Let me verify it and check the PG databases.
Environment intact: PG 17 with both DBs, venv with Django 6.0.10 + ruff 0.15.2, Redis, next dev. Backends :8000/:8001 are down (session 58 noted this sandbox reaps backgrounded processes — per-gate start→gate→teardown helpers were used). Let me check the helper scripts from session 58.
The daemonize helper exists. Now let me reproduce the backend baseline — the strongest alignment check.
Backend baseline exact: **1030P/0F/5S**. Now the web gates.
Static web gates green. Now let me check the live-gate requirements and how to start the backends.
Environment configured. Let me start the backend on :8000 using the daemonize helper and verify it survives.
Backend survived. Let me start the :8001 RLS instance too, then run the live e2e suite.
There's a SyntaxWarning at `contact_service.py:284` that P30 claimed to have fixed. Let me investigate.
The file shows `^\\d{10}$` (escaped) but a warning fired. Let me check whether the log is stale or there's another `\d` elsewhere.
Line 284 doesn't contain `\d` — the warning text doesn't match current source. Let me verify by compiling fresh and checking the log's boot count.
The file compiles clean — the warning in the log was from a pre-P30 boot (appended log). False alarm. Now let me start the :8001 instance and run the live gates.
Both backends and web server up. Now the live e2e suite — the longest gate.
e2e **43/43**. Now the RLS smoke, mobile-nav audit, and translate probe.
Mobile-nav 17/17 (thirtieth settlement) + translate probe PASS. Now build:server and prod-CSP smoke to complete the baseline.
The CSP smoke failed with MODULE_NOT_FOUND. Let me check what the script expects.
The script spawns its own server on :3111 — my manual server was wrong. Let me run it exactly per its usage.
All 11 documented gates reproduced exactly. Let me verify the P30 ruff ratchet state too.
**Full baseline reproduced — the P30 state holds exactly.** Now the audit phase. Let me first re-verify the P30 slice, then survey the registered deferred candidates (B904 ×66, tests-tree 379, audit-log INSERT policy).
P30 slice verified. Now let me survey the B904 batch — the registered next sprint candidate.
B904: 66 findings across 21 files, document_service.py holding 12. Let me examine representative examples to understand the fix shapes.
Now let me survey the other registered candidates: the tests/-tree batch and check remaining query-walk surfaces one seam deeper.
Tests-tree: 379 findings (221 in the same mechanical classes P30 closed on production). Now let me examine the audit-log INSERT policy — the third registered candidate.
Let me check existing exception-chaining conventions in the codebase to establish the right pattern.
The codebase already has the convention: `from exc` by default, `from None` for deliberate noise. Let me examine the existing exemplars to fix the convention precisely.
Let me check the git history of these two divergent exemplars to understand the original decisions.
The convention history is clear. Now let me do the fresh "one seam deeper" audit sweep — verifying the registered F821 tests-tree findings and hunting for any new issue class.
F821s confirmed as string-annotation nits. Since P31 will be the exception-chaining sprint, let me sweep the companion surfaces: the S110 try-except-pass sites and broad catches.
S110 sites confirmed as registered fail-closed designs. Now let me classify all 66 B904 sites to build the review matrix for the plan.
Let me examine the remaining ambiguous sites to complete the classification.
Classification complete: 62 `from exc` + 4 `from None` (where the message already embeds the original error string). Let me validate the RED-spec design against the actual seams.
All three RED seams validated. Let me confirm `ResourceNotFound` rendering is unaffected by chaining.
The audit is complete: 0 Critical / 1 High / 2 Medium / 1 Low. Now let me write the validated P31 remediation plan.
Plan saved. Now Phase 1 — RED. Let me check the P30 spec conventions and the conftest fixtures first.
Let me verify the service method signatures for the RED spec.
All signatures verified. Writing the RED spec.
**RED confirmed — all 4 fail for exactly the right reasons.** Now Phase 2 GREEN. Let me check what ruff's B904 autofix produces before deciding on the approach.
No autofix available — all 66 fixes are manual (the "reviewed sprint"). Let me write a precise script that applies the classified fixes with a string-aware statement-end scanner.
All 66 applied. Now verify: B904 → 0, no new findings, files compile.
Total is 217, not the expected 211 — my edits introduced 6 new findings. Let me identify them.
My `from exc` suffix pushed 6 lines over the E501 limit. Let me wrap those lines properly.
**277 → 211, B904 at 0** — exactly as planned. Now the GREEN check on the spec.
**GREEN 4/4.** Now T5 — the tests-tree mechanical closure. First the F401 review (the class needing care).
All 66 F401s are models/stdlib/test-helpers — no import-is-the-side-effect class (no factory/registration modules). The full-suite run will prove it. Phase A: whitespace first.
Pure whitespace confirmed. Phase B: import sorting.
All 66 fixed safely. The full-suite run is the real proof. Let me run it.
Suite green: **1034P/0F/5S** (+4). But 3 mechanical findings reappeared (the P30 re-sort lesson). Let me close them.
157 remaining vs the predicted 158 — let me verify the exact class composition for the honest count.
Tests tree: mechanical classes at 0, total 157 (one F811 rode along with the import cleanup — honest note for the report). Now T7 — the unified ratchet.
The P30 lesson: Makefile edits must preserve TABs. Let me check the raw bytes and edit with a tab-safe method.
Unified ratchet green. Now the ci.yml step.
Now Phase 3 — restart both backends on the remediated code (the `--noreload` lesson), then run the full matrix.
All live gates green. Now build:server + prod-CSP smoke.
Now the live contract re-verification — the not-found 404 and typed-400 bodies.
The 404 body is exactly the documented contract. My allocate URL was wrong — the route needs a payment UUID. Let me redo.
Live contracts verified byte-stable. Now the screenshots — let me review the session-57 capture conventions.
I have the conventions. Writing the session-59 capture script (shots 200-207).
All 8 captures OK. Now the pixel verification.
All 8 pixel-verified. Now the `.env.example` truth sweep.
Env examples verified truthful. Now the docs truth pass — starting with README.
Let me check the README's Previous Milestones section for a P30 entry needing a P31 sibling.
I need to restructure: P31 becomes the Latest Milestone, P30 moves to Previous. Let me fix this properly.
Structure fixed. Let me check the other "Latest Milestones" section and any B904 references in README.
README done. Now CLAUDE.md.
Now AGENTS.md — the header truth block and the P31 lessons.
Now SKILL and PAD docs.
Now DEPLOYMENT.md.
Now the API guide re-verification note.
Docs updated. Now the P31 report.
Now the session log and worklog entry.
Worklog done. Now the final verification pass before committing.
All intended files, skills untouched. Final gate run on the exact final tree.
**Final tree verified: 1034P/0F/5S, unified ratchet 0, production 211, tests 157.** Now the atomic commits.
All 5 commits on main, tree clean. Now the SSH wrapper push — reading the instructions first.
The wrapper procedure is clear. Let me check the wrapper's default remote, then set up the key outside the repo.
Dry-run authenticated — fast-forward `933af819..2370f7c4` negotiated. Real push now.
All done. Let me finalize the task list.
The **P31 sprint** is complete and pushed to `main @ 2370f7c4` — all gates green, verified end to end.

## What was delivered

**Baselines first.** All 11 documented gates reproduced exactly before any change (backend 1030P/0F/5S, vitest 698/698, tsc/eslint 0, e2e 43/43 first-run, rls 13/13, mobile-nav 17/17, translate probe PASS, npm audit 0, build + prod-CSP 5/5, lint-mechanical 0, ruff count 277 exact). The **mobile navigation menu works as expected — no TailwindCSS v4 bug** (settled for the 30th/31st times, probe-evidenced).

**The audit** found 1 High / 2 Medium / 1 Low, all TDD-fixed:
- **The B904 exception-chaining closure (headline):** the registered 66 raise-inside-except sites — the P30 report's own suggested next sprint — now chain explicitly: **62 `from exc`** (lookup misses, IntegrityError races, password propagation, parse translations, Celery retries) + **4 `from None`** (messages already embedding the original error string). Response bytes byte-identical, pinned by 4 new `__cause__`/`__suppress_context__` gates + live re-verification.
- **The tests-tree mechanical extension:** 221 findings closed (W293 ×99, I001 ×60, F401 ×66 all reviewed) — production ruff 277 → 211, tests 379 → 157.
- **The unified closed-class ratchet:** `make lint-mechanical` + the CI step now gate all closed classes over production + tests.

**Final gates:** backend **1034P/0F/5S** (+4) · vitest 698/698 · e2e 43/43 · rls 13/13 · mobile-nav 17/17 · prod-CSP 5/5 · 8 pixel-verified screenshots (200-207) · `.env.example` truthful · full docs truth pass (README badge 1775, CLAUDE 2.32.0, AGENTS +2 lessons, SKILL 2.18.0, PAD 3.21.0, DEPLOYMENT, API guide).

Key deliverables: [P31 plan](/home/z/my-project/ledgersg/docs/REMEDIATION_PLAN_2026-11-28_P31.md) · [P31 report](/home/z/my-project/ledgersg/docs/REMEDIATION_2026-11-28_P31_REPORT.md) · [session log](/home/z/my-project/ledgersg/docs/session_60.md) · [worklog](/home/z/my-project/ledgersg/worklog.md) · [README](/home/z/my-project/ledgersg/README.md)

**Suggested next:** the UP typing batch (×109 — needs the mypy-gate conversation), the tests-tree residual (157, incl. the F811 fixture class), the E501/format axis (80 files), or the audit-log INSERT policy (DDL) — all registered with rationale.
