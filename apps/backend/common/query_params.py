"""Query-parameter parsing helpers (P7/F-11).

Malformed query params must produce a 400 ValidationError — never an
unhandled ValueError/InvalidOperation 500. Each helper parses or raises
the domain ValidationError that wrap_response maps to 400.
"""

from datetime import datetime
from uuid import UUID

from common.exceptions import ValidationError


def parse_date_param(value: str, param: str) -> datetime:
    """Parse an ISO date query param; 400 with the param name on garbage."""
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except (ValueError, TypeError) as err:
        raise ValidationError(
            f"Invalid '{param}' — expected YYYY-MM-DD, got '{value}'."
        ) from err


def parse_uuid_param(value: str, param: str) -> UUID:
    """Parse a UUID query param; 400 with the param name on garbage."""
    try:
        return UUID(str(value))
    except (ValueError, TypeError, AttributeError) as err:
        raise ValidationError(
            f"Invalid '{param}' — expected a UUID, got '{value}'."
        ) from err


def parse_int_param(
    value: str,
    param: str,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int:
    """Parse an integer query param; 400 with the param name on garbage.

    P8/G-2: `min_value` rejects semantically-invalid integers (e.g. a
    negative slice limit) that parse fine but blow up (or misbehave)
    downstream — an out-of-range int is as malformed as a non-int.
    P25/BE-M2: `max_value` is the upper mirror — a validly-typed but
    astronomically large value (e.g. an offset above the Postgres
    bigint bound) must surface as the typed 400, not as a DataError 500
    at the SQL layer or a silent misbehaviour downstream.
    """
    try:
        parsed = int(value)
    except (ValueError, TypeError) as err:
        raise ValidationError(
            f"Invalid '{param}' — expected an integer, got '{value}'."
        ) from err
    if min_value is not None and parsed < min_value:
        raise ValidationError(
            f"Invalid '{param}' — must be >= {min_value}, got {parsed}."
        )
    if max_value is not None and parsed > max_value:
        raise ValidationError(
            f"Invalid '{param}' — must be <= {max_value}, got {parsed}."
        )
    return parsed
