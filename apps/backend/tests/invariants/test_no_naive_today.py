"""
Timezone-aware date gate (P13/B-6).

`TIME_ZONE` is Asia/Singapore but containers run UTC: between 00:00 and
08:00 SGT the UTC date is a day behind, so any production call to
`date.today()` computes the wrong statutory date (F5 deadlines, aged
as-at defaults, converted-invoice posting dates, overdue counts). The
P11/L-3 sweep fixed the posting service but 8 production sites remained.

This gate walks the production source tree and fails on any
`date.today()` (or `datetime.today()`/`datetime.now()` naive variants)
outside the explicitly allowed files below.
"""

from pathlib import Path

# Files allowed to keep naive-today calls (none today — the list exists so
# a future justified exception is deliberate, not silent).
ALLOWED: dict[str, set[int]] = {}

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SCAN_DIRS = ["apps", "common", "config"]
NAIVE_PATTERNS = ("date.today()", "datetime.today()", "datetime.now()")


def test_no_naive_today_in_production_code():
    offenders = []
    for scan_dir in SCAN_DIRS:
        for path in (BACKEND_ROOT / scan_dir).rglob("*.py"):
            rel = str(path.relative_to(BACKEND_ROOT))
            if "tests" in path.parts or path.name.startswith("test_"):
                continue
            allowed_lines = ALLOWED.get(rel, set())
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if lineno in allowed_lines:
                    continue
                # commented-out code is not a call
                if line.lstrip().startswith("#"):
                    continue
                for pattern in NAIVE_PATTERNS:
                    if pattern in line:
                        offenders.append(f"{rel}:{lineno}: {line.strip()}")

    assert not offenders, (
        "Naive 'today' calls in production code — use timezone.localdate() "
        "(TIME_ZONE=Asia/Singapore vs UTC containers; P13/B-6):\n  "
        + "\n  ".join(offenders)
    )
