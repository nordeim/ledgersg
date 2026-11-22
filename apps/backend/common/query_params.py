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


def parse_int_param(value: str, param: str) -> int:
    """Parse an integer query param; 400 with the param name on garbage."""
    try:
        return int(value)
    except (ValueError, TypeError) as err:
        raise ValidationError(
            f"Invalid '{param}' — expected an integer, got '{value}'."
        ) from err
