The workspace exists. Let me refresh it with git pull and check the current state.
已拉取最新代码（已添加 session_4.md）。现在让我制定任务计划并阅读核心文档。
Let me read the remaining core docs (README, architecture doc, skill file).
Now reading session_4.md (the new file from the pull) and the P1 remediation plan/report.
session_4.md 记录了 P1 sprint（已推送至 be3fefee）。现在让我阅读 P1 计划和报告，以了解延迟的债务登记。
Now let me examine the current codebase structure and test configurations (key new requirement: vitest + playwright suites).
Now let me check the environment state (PG/Redis may need restart after sandbox recycle) and set up services.
Services are running. Let me verify the DB state and run the backend test baseline to confirm reproducibility.
Schema counts differ between DBs (23 vs 35). Let me investigate the schema list in both databases.
Both DBs correctly loaded (test DB has extra Django tables from `--reuse-db` runs — expected). Now running the backend baseline to confirm the documented green state (499P/0F/5S).
Backend baseline confirmed: 499 passed / 0 failed / 5 skipped — matches documented state exactly. Now the frontend suite.
Both suites reproduce documented state. Marking env/validation todos complete and moving to the audit phase.
Let me examine the audit skill used in prior sessions and its runner.
Scanner reports 21 "criticals" — session 3 verified these as false positives. Let me confirm they're the same set, then focus the real audit on recent changes.
Same 21 scanner findings as session 3. Let me re-verify the two in production code paths (not test files).
Both are docstring false positives (confirmed). Now the real audit — reviewing the recent P1 sprint diffs.
Now let me review the P0 plan's deferred register to scope the P2 candidates.
现在让我检查 P2 审计的关键候选对象——H-04（GST 税率历史）和测试套件状态。首先从税率解析代码开始。
H-04 confirmed: `get_tax_code_by_code()` has no `effective_from` ordering — arbitrary rate returned when history exists. Let me check how document lines resolve rates.
`add_line` snapshots the rate from the passed tax_code_id without date-effectiveness validation — H-04 confirmed. Now let me check the e2e/vitest infrastructure state.
Chromium v1208 installed — matching playwright 1.58.2. Continuing the audit: checking the gst views caller and other rate-resolution paths.
More defects found in the GST calculate endpoint (silent 9% fallback = fail-open). Let me check the seed rate history and how `.first()` misbehaves.
Rate history confirmed: SR has 3 rows (0.07/0.08/0.09). Let me verify what `.first()` actually returns via the Django ORM.
**H-04 reproduced live**: service returns 0.07 (2007 row) instead of 0.09. Let me check the tax-code list endpoint to understand caller exposure.
`list_tax_codes` also returns all 3 SR rows unordered by date. Let me check the GST calculation serializer contract and existing tests.
The iras-info endpoint serves a static 9% while DB resolution returns 7% — inconsistent. Let me check how the frontend selects tax codes.
Frontend hardcodes 9% (correct); backend resolves 7% — contract drift confirmed. Now verifying the `.env.example` files against what the code actually reads.
7 of 9 web env-example vars are dead — the header claim is false. Now let me run the current playwright e2e suite to capture its RED state (audit evidence).
The headless shell variant is missing. Installing it.
Chromium e2e: 5 passed, 1 failed — the axe accessibility scan finds real violations. Let me see them.
`/` redirects to `/dashboard` → auth guard → `/login`. The axe scan actually scanned the login page. Let me check its structure.
Login page uses `<div>` (no `<main>`) and h3 only — a11y defect confirmed. Let me check the typecheck/lint state of the web app.
25 pre-existing type errors in test files — the typecheck gate is red with no `typecheck` script even defined. Let me check eslint too.
The audit is complete. Now validating the remediation-plan assumptions against the codebase before writing it.
`box_mapping` isn't a model field — the create-tax-code path may pass an invalid kwarg. Let me verify this live.
Defect B-7 confirmed: custom tax-code creation always 500s. Let me check the root conftest fixtures needed for the plan's tests.
All assumptions validated. Now writing the P2 remediation plan (following the P1 naming/structure convention).
Plan saved. Now validating it against the codebase (per the mandated plan→validate→execute sequence).
All plan assumptions validated. Let me record the validation refinements in the plan, then begin execution.
Plan validated. Now executing the remediation with TDD — starting with Task 1 (playwright config) and Task 2's RED test.
Syntax error — I forgot to close the `projects` array. Fixing.
Task 1 verified: default 6 chromium tests; opt-in 30 across 5 projects. Now Task 2 — writing the RED vitest test for login a11y first.
Tests fail on the missing AuthProvider context. Let me check how existing tests handle providers.
Updating the test with the repo's established mocking pattern so RED fails for the right reason.
RED confirmed for the right reasons (no main, no h1, only h3). Now GREEN — implementing the login page fix.
Vitest GREEN. Now the independent e2e axe verification (self-managed dev server).
A stale dev server (from before the fix) is being reused. Killing it so playwright starts a fresh one.
The fix is live (main + h1 present) — but the Next.js dev-tools overlay is now flagged. Let me see the exact remaining violations.
Only one real violation left: color-contrast on the terms paragraph. Let me check the theme's muted color values.
`text-secondary` (#A0A0A0) gives 7.22:1 (AAA) vs muted's 3.29:1. Fixing the paragraph surgically.
Zero violations. Running the full e2e suite now (clean server lifecycle).
Root cause found: the test races the auth redirect (`/` → `/dashboard` → guard returns null → `/login`). Axe scans the empty shell mid-redirect. Fixing the test to wait for navigation to settle — the zero-violations assertion stays strict.
E2E GREEN: 6/6. Running full vitest to confirm no regressions, then moving to Task 3.
Vitest 324/324 (321 + 3 new). Task 2 done. Now Task 3 — RED test for the custom tax-code creation bug.
RED confirmed with the exact audited TypeError. Now GREEN — fixing the view.
The TypeError is fixed; now the DB's `chk_io_flag` CHECK rejects the row. Let me check the constraint definition.
The service must satisfy the DB's io-flag contract. Fixing `create_tax_code` with a compliant default.
Task 3 GREEN (3/3). Now Task 4 — checking fixtures needed for the add_line effectiveness test.
Writing the Task 4 RED test file (rate-effectiveness by date).
RED confirmed: 12/12. Now GREEN — implementing the service-layer effectiveness resolution.
The two-branch query has a bug (NULL effective_from rows skip the effective_to check). Rewriting as a single correct query.
Now updating `list_tax_codes` with the `effective_on` filter and deterministic ordering.
Now the serializer and views.
`tax_code_id` is a UUIDField but the view treats it as a code — the path never worked at all. Fixing the serializer with a canonical `tax_code` field plus a CharField alias.
Now the calculate view (fail-closed, date-aware) and the list view (`effective_on` param).
Let me check `wrap_response`'s response shape to align my test assertions.
`wrap_response` doesn't nest data — fixing my test assertions to match the actual response shape.
Now the `add_line` effectiveness validation, and checking the views' imports.
Now wiring the `effective_on` query param into the list view, then the `add_line` validation.
Now the `add_line` effectiveness validation in the document service.
Two fixes: the view's `UUID(org_id)` crashes on already-UUID kwargs (this path was double-broken), and my test used an invalid document type.
Now fixing my test's document type (should be `SALES_INVOICE`).
The view's function-local `from decimal import Decimal` (in the else branch) unbinds `Decimal` for the if-branch — the path was triple-broken. Fixing with a module-level import.
Cleaning up the leftover blank lines from import removal.
The TenantModel requires an org — system rows must come from the schema seed. Checking if the test DB has them.
The test DB already has system SR history rows — so `effective_on` must resolve per-code (org-preferred), and the shadow test should use the existing system rows. Fixing both.
The ordering test needs to reflect the actual contract: org rows first (newest→oldest), then system rows. Updating the assertion.
Task 4 GREEN: 12/12. Now the full backend suite regression check.
Full suite green: 514 passed (+15 new). Now Task 5 — the truthful web `.env.example`. Reading the current one fully first.
Task 5 done. Now Task 6 — enumerating the exact tsc errors to fix.
Mechanical fixes: `jest.Mock` → vitest `Mock` casts and missing imports. Let me script the type-alias fixes first.
25 → 13. Now the fixture fixes. Inspecting each location.
These tests verify zod defaults — the fixture deliberately omits fields. The type annotation is wrong (output type instead of input type). Checking the schema.
`calculateFromLines` reads only input fields — the parameter type should be `InvoiceLineInput[]`. Fixing the signature and the tests.
The right split: schema-input type for the default-tests; complete payloads for the mutation tests (production types stay strict).
8 left — the payment/account sites differ, and `InvoiceLineInput` isn't the form-state type. Checking the exact sites and the line schema.
Typecheck: 0 errors. Adding the `typecheck` script and verifying runtime didn't break.
Vitest 324/324 maintained. Verifying the typecheck script and lint on touched files.
My new/rewritten files are lint-clean. Verifying the `any` errors are pre-existing (not on my edited lines).
All lint findings confirmed pre-existing (in an untouched file). Now the backend gates: ruff on touched files + `manage.py check`.
Zero new findings in production files (19 = 19 pre-existing). Fixing the one unused import in my new test file.
New files lint-clean. Running the complete P2 verification gate now.
Full gate GREEN. Now the docs alignment — checking current README testing sections.
Updating README.md with the P2 state.
Now CLAUDE.md status updates.
Now AGENTS.md — appending the session-5 lessons.
Now writing the P2 remediation report (verification ledger).
P2 report saved. Now refreshing `ledgersg_SKILL.md` per the distill skills — reading their protocols first.
Now reading the current ledgersg_SKILL.md to apply the update protocol.
Applying the skill-update protocol: version bump, project_state, new anti-patterns/debug rows/lessons.
Finishing the skill update: frontmatter description, lessons, and quick-reference.
Skill refreshed (v1.2.0). Now Task 8 — screenshots. Starting both dev servers.
Servers up. Checking the demo user exists, then capturing screenshots.
All unique and valid. Visually verifying the key captures (login with a11y fix + dashboard).
Programmatic verification passed (unique hashes, correct dimensions, non-blank). Cleaning up the scratch capture script and writing the session log.
Now updating worklog.md with the session 5 record.
Worklog updated. Now the commit sequence per the P2 plan. Checking the full change set.
Cleaning scratch artifacts and checking gitignore coverage for playwright outputs.
Adding the playwright artifact dirs to the web .gitignore (part of B-1 hygiene).
Committing in the plan's logical groups. First, splitting the two mixed gst files for atomic B-7/B-3 commits.
B-7 committed (3/3 green in that state). Restoring the full versions for the B-3 commit.
`package.json` was missed (a failed pathspec aborted its git add). Amending the B-5 commit.
The amend landed on the wrong commit (worklog instead of B-5). Fixing the history properly.
8 atomic commits, clean tree. Final verification gate on the committed state before push.
All green on the committed state. Now the SSH push — reading the wrapper skill.
The venv has paramiko and the session-3 shim is intact. Deploying the key securely (outside the repo) and running the fingerprint check.
Dry-run clean (fast-forward 4acece81..33548dce). Executing the real push.
All work is complete and pushed. Final summary:

## Session 5 — P2 Sprint complete

**Pushed:** 8 conventional commits to `main` (`4acece81..33548dce`), remote ref verified, key shredded.

**Audit** (repo skills, recent changes focus) found 7 real issues; headline: GST rate resolution returned the **2007 7% row** for SR instead of 9% (live-verified), `POST /gst/tax-codes/` always 500'd, and both frontend suites were red-by-default.

**Remediation (TDD, all RED→GREEN):**
- **H-04**: rate-by-effective-date everywhere, fail-closed (unknown code → 404, stale code on `add_line` → 400) — 12 new tests
- **B-7**: custom tax-code creation works again — 3 new tests
- **B-1/B-2**: playwright green-by-default (chromium; `PLAYWRIGHT_PROJECTS=all` opt-in); login page a11y fixed + deterministic axe scan
- **B-5**: `npm run typecheck` gate added, 25 type errors repaired
- **B-4**: truthful `apps/web/.env.example`

**Final gate (executed):** backend **514P/0F/5S** · vitest **324/324** · typecheck **0 errors** · e2e **6/6** · invariants 15P · security 32P/3S.

**Delivered:** [P2 plan](/home/z/my-project/ledgersg/docs/REMEDIATION_PLAN_2026-11-21_P2.md) · [P2 report](/home/z/my-project/ledgersg/docs/REMEDIATION_2026-11-21_P2_REPORT.md) · [session_5.md](/home/z/my-project/ledgersg/docs/session_5.md) · [worklog.md](/home/z/my-project/ledgersg/worklog.md) · refreshed [ledgersg_SKILL.md](/home/z/my-project/ledgersg/ledgersg_SKILL.md) (v1.2.0) · 5 new screenshots in docs/screenshots/

**Suggested next:** H-03 numeric widening (now the top compliance risk), then wiring the invoice form's tax-code dropdown to `?effective_on=<document date>`.
