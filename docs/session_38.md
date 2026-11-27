# Session 38 — the P19 sprint log (the remove_line truth gap, the modal semantics debt, the ContactPicker & the route guard)

Continuation of the standing task cycle on the carried-forward
workspace: `git pull` brought in the owner's `docs/session_37.md` (the
P18 session's raw transcript — the sprint had already completed and
pushed; this session is the fresh P19 cycle the log's closing
recommendation named).

The environment audit: PG 17, Redis and the double-forked dev stack
(:8000 dev + :8001 rls) all alive from the prior session; the demo
substrate intact (user, org, 2 contacts, CoA seeded — the documented
`demo1234pass` password). The baselines reproduced exactly before any
change: **backend 914P/0F/5S · vitest 601/601 · tsc 0 · eslint
0E/5W · mobile-nav 17/17** (the ninth live settlement of "no Tailwind
v4 bug").

Three parallel deep audits (Mode C) scoped to the P18 diff + the
carried deferred register → **0 Critical / 3 High / 16 Medium / 22
Low**; every High hand-verified in source. The headline finding: the
P18 commit `51bd46c6` claimed "add_line/remove_line lock the document"
— **only `add_line` got the lock**, and the RED run then exposed that
`remove_line` had never worked at all (an `invoice=` filter against a
`document` FK — FieldError on every call, untyped 500, zero test
coverage). The two frontend Highs: the four hand-rolled banking
"modals" (no focus trap, no Escape, no dialog semantics — violating
the repo's own ui/dialog discipline) and the mouse-only transaction
row (keyboard users could not reach Reconcile — WCAG 2.1.1 Level A).
The plan saved and anchor-validated, then executed TDD.

Phase 1 (backend, every fix RED first): the remove_line truth-gap fix
(atomic + lock + re-check + the real FK) · the unallocate lock
re-order (payment→allocation→document — the AB-BA deadlock inversion)
· the archive-gate cache bypass · the create_entry account locks
(sorted pre-lock — the user line order itself was a deadlock risk) ·
the return-periods savepoint (the P18 catch without one poisoned
ATOMIC_REQUESTS) · the status-task full tenant-context wrap · the
journal-list prefetch (31→2 queries) · the five uuid route islands ·
the serializer-tolerance alignment (0.001→0.0001, the P13 trigger
boundary) · the display_money finite gate · two RED-run discoveries
recorded: BE-L1 (NULL transmitted_at) is impossible (NOT NULL +
auto_now_add) — invalidated; two first-cut probes were vacuous and
rebuilt → **backend 937P/0F/5S (+23 P19 tests)**.

Phase 2 (frontend, vitest RED first): the four banking modals → Radix
Dialog (accessible names, bounded height, the five unlabeled internal
X buttons removed) · the transaction-row button (aria-expanded +
keyboard) · **the ContactPicker WAI-ARIA 1.0 combobox — the deferred
register's oldest item, carried since P16** (activedescendant roving,
full keyboard contract, options on mousedown) · **the in-app
unsaved-work route guard — the register's #2 item** (a document-capture
click interceptor + confirm dialog while the invoice store is dirty) ·
the UEN edit-path regex · the PAID badge unified on bg-success ·
scope="col" on the money tables · the line-editor row-context labels
· the aria batch (back links, payment-form labels, role="alert") ·
the GST checkbox dead-token fix · the contrast gate's color-warning ·
the five eslint warnings (4 fixed + 1 documented TanStack disable) →
**vitest 619/619 (72 files) and eslint 0E/0W — better than parity**.

Phase 3 (cross-cutting): the enforced CSP now reports to the backend's
tested endpoint (production violations were invisible) · the CSV size
cap + row ceiling (worker OOM by one oversized statement) · the compose
beat service removed (its scheduler tables are an intentional §15c
omission — a deterministic crash-loop on the documented Docker route)
· the PG_BASE fresh-host completion · the e2e password fallback fixed
(8 chars could never log in) · uuid dep dropped · ALLOWED_HOSTS via
decouple · the ci-summary gate includes security-scan · the P18 report
erratum.

The full gate matrix, all executed green: backend **937P/0F/5S** ·
vitest **619/619** · tsc 0 · eslint **0 errors/0 warnings** ·
**e2e:full 40/40** (five spec locators honestly adapted to the new
modal/a11y contracts; one real discovery — the import dialog's
unnamed bank-account select) · **rls_smoke 13/13 as `ledgersg_app`**
(the :8001 instance re-daemonized on the remediated code) ·
**mobile-nav 17/17** · **prod-CSP 5/5**.

The deliverables: 8 DOM-verified screenshots
(`docs/screenshots/112-119_*_session38.png`, md5-unique, non-blank
pixel-verified — the P19 proofs: the Radix receive dialog, the
keyboard-expanded row, the combobox with its active option, the
route-guard dialog, the unified PAID badge); the P19 report; this log;
the worklog entry; the conventional commits and the SSH-wrapper push
to main.
