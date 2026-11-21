"""
Common view utilities for LedgerSG.

Response wrappers and view helpers used across all apps.
"""

from collections.abc import Callable
from functools import wraps

from rest_framework import status
from rest_framework.response import Response

from common.exceptions import DuplicateResource, ResourceNotFound, ValidationError


def wrap_response(func: Callable) -> Callable:
    """
    Decorator that wraps view methods to handle common exceptions
    and standardize response format.

    Handles:
    - ValidationError -> 400 Bad Request
    - ResourceNotFound -> 404 Not Found
    - DuplicateResource -> 409 Conflict
    - Generic exceptions -> 500 Internal Server Error

    Usage:
    @wrap_response
    def get(self, request, org_id):
        # Your view logic
        return Response(data)
    """
    import logging

    logger = logging.getLogger(__name__)

    @wraps(func)
    def wrapper(*args, **kwargs) -> Response:
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            return Response(
                {
                    "error": {
                        "code": e.code,
                        "message": e.message,
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ResourceNotFound as e:
            return Response(
                {
                    "error": {
                        "code": e.code,
                        "message": e.message,
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except DuplicateResource as e:
            return Response(
                {
                    "error": {
                        "code": e.code,
                        "message": e.message,
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )
        # Unexpected exceptions MUST propagate.
        #
        # Under ATOMIC_REQUESTS = True, Django wraps the view in a transaction.
        # If we convert an exception into a 500 Response here, Django sees a
        # normal return value and COMMITS the partial multi-step state — the
        # exact failure mode audited as C-04. Re-raising lets the atomic
        # wrapper roll everything back; the server error page / DRF exception
        # handler produces the client-facing 500.
        except Exception:
            logger.error(f"View error in {func.__name__}", exc_info=True)
            raise

    return wrapper
