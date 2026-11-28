"""Server-side list pagination (P24/BE-M1).

Every list endpoint returns the FULL matching set — the payload grows
without bound (the ledger endpoint returns the org's entire journal-line
history in one response). The additive contract this module implements:

- `?limit=N&offset=M` paginates: the response gains `next`/`previous`
  (absolute URLs carrying limit+offset+the caller's filters, DRF-style)
  and `count` reads as the TOTAL matching rows (which equals
  ``len(results)`` only in the unpaginated mode — the semantic is
  documented in the API guide).
- With `limit` ABSENT the response stays byte-identical
  `{results, count}` — every existing consumer (the e2e specs, the
  bootstrap script, rls_smoke, the frontend hooks) keeps working.

Typed 400s follow the P7/F-11 garbage-param convention: limit must be
an integer in [1, 1000] (explicit beats silent clamping — a caller's
paging bug must surface, not silently clamp), offset a non-negative
integer capped at the Postgres bigint bound (2**63 - 1 — P25/BE-M2:
an offset above int8 cannot round-trip through OFFSET, so it is
garbage at the parse layer, never a DataError 500 at the SQL layer).
P25/BE-L4: `offset` requires `limit` — a well-formed offset without a
limit is a caller paging bug (the pre-P25 behaviour silently returned
the FULL set with the offset unused); it surfaces as the typed 400.
Postgres tie order is not stable across executions, so
paginated surfaces need a deterministic total order (the schema's
UNIQUE keys carry the ledger, entries and documents; the contacts and
payments `id` tiebreakers landed with this module).
"""

from rest_framework.pagination import (
    CursorPagination as _CursorPagination,
)
from rest_framework.pagination import (
    PageNumberPagination,
)
from rest_framework.request import Request
from rest_framework.response import Response

from common.exceptions import ValidationError
from common.query_params import parse_int_param

# ---------------------------------------------------------------------------
# The dormant DRF page-number classes (pre-P24 legacy, kept verbatim):
# `DEFAULT_PAGINATION_CLASS` in config/settings/base.py imports
# `StandardPagination` by string path, and the DRF system check accesses
# the setting at every boot — the module must keep defining it. No
# LedgerSG view paginates through DRF's generics (every list is a raw
# APIView returning the explicit {results, count} envelope), so these
# classes stay dormant; the live pagination is the limit/offset contract
# below (P24/BE-M1).
# ---------------------------------------------------------------------------


class StandardPagination(PageNumberPagination):
    """
    Standard page-number pagination for most endpoints.

    Supports configurable page_size via query parameter.
    """

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200
    page_query_param = "page"


class LargeResultPagination(PageNumberPagination):
    """
    Pagination for endpoints that return large results.

    e.g., journal entries, audit logs
    """

    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 500
    page_query_param = "page"


class CursorPagination(_CursorPagination):
    """
    Cursor-based pagination for large datasets.

    Use for: journal entries, audit logs, invoice lines
    Provides consistent performance regardless of dataset size.
    """

    page_size = 100
    cursor_query_param = "cursor"
    ordering = "-created_at"


class SmallResultPagination(PageNumberPagination):
    """
    Pagination for endpoints with small result sets.

    e.g., dropdown options, settings
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
    page_query_param = "page"

#: The documented max page size — a typed 400 above it.
MAX_PAGE_LIMIT = 1000

#: The offset ceiling — the Postgres bigint bound (int8 parity). An
#: offset above it cannot survive the SQL `OFFSET` clause (DataError:
#: bigint out of range), so it is rejected at the parse layer with the
#: typed 400 (P25/BE-M2).
MAX_PAGE_OFFSET = 2**63 - 1


def parse_limit_offset(request: Request) -> tuple[int | None, int]:
    """Parse the `limit`/`offset` query params.

    Returns ``(limit, offset)`` — ``limit`` is None when the param is
    absent (the unpaginated back-compat mode). Garbage or out-of-range
    values raise the typed ValidationError that wrap_response maps to
    the 400 error envelope. ``offset`` without ``limit`` is the typed
    400 (P25/BE-L4 — the offset is meaningless unpaginated; the
    pre-P25 behaviour silently ignored it and returned the full set).
    """
    raw_limit = request.query_params.get("limit")
    raw_offset = request.query_params.get("offset")

    limit: int | None = None
    if raw_limit is not None and raw_limit != "":
        limit = parse_int_param(raw_limit, "limit")
        if limit < 1 or limit > MAX_PAGE_LIMIT:
            raise ValidationError(
                f"Invalid 'limit' — must be between 1 and {MAX_PAGE_LIMIT}, "
                f"got {raw_limit}."
            )

    offset = 0
    if raw_offset is not None and raw_offset != "":
        if limit is None:
            raise ValidationError(
                "Invalid 'offset' — 'limit' is required when 'offset' is "
                "present (the unpaginated response returns the full set; "
                "an offset alone is a paging bug, not a page request)."
            )
        offset = parse_int_param(
            raw_offset, "offset", min_value=0, max_value=MAX_PAGE_OFFSET
        )

    return limit, offset


def page_envelope(
    request: Request,
    limit: int,
    offset: int,
    results: list,
    total: int,
    extra: dict | None = None,
) -> Response:
    """The paginated response: `{results, count, next, previous}`.

    DRF LimitOffset semantics: `next` while offset+limit < total (the
    URL carries the caller's filters — paging within a filtered set
    must not widen it), `previous` when offset > 0, clamped at 0.

    P26/BE-M4: `extra` merges additional envelope keys AFTER the
    standard four (e.g. the Peppol transmission log's status counters)
    — additive; every existing caller is byte-identical without it.
    """
    next_url = (
        _page_url(request, limit, offset + limit)
        if offset + limit < total
        else None
    )
    previous_url = (
        _page_url(request, limit, max(0, offset - limit)) if offset > 0 else None
    )
    payload: dict = {
        "results": results,
        "count": total,
        "next": next_url,
        "previous": previous_url,
    }
    if extra:
        payload.update(extra)
    return Response(payload)


def _page_url(request: Request, limit: int, offset: int) -> str:
    """The absolute page URL: the caller's filters survive (paging within
    a filtered set must not widen it), with limit/offset rewritten."""
    query = request.query_params.copy()
    query["limit"] = str(limit)
    query["offset"] = str(offset)
    return request.build_absolute_uri(f"{request.path}?{query.urlencode()}")
