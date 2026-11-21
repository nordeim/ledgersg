"""
Audit Context Middleware

Captures request metadata (IP address, user agent, request path) and makes it
available to the audit trigger system via SET LOCAL session variables.
"""

import logging

from django.db import connection, transaction
from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)


class AuditContextMiddleware:
    """
    Middleware that captures audit-related request metadata.

    Sets session variables that the audit.log_change() trigger can read.
    Must be placed AFTER TenantContextMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Only capture for API requests
        if not request.path.startswith("/api/"):
            return self.get_response(request)

        # Extract request metadata
        ip_address = self._get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]  # Limit length
        request_path = request.path[:500]

        # C-03: SET LOCAL is transaction-scoped. For org-scoped URLs the
        # TenantContextMiddleware has already opened the request transaction
        # (we run inside it — atomic() here degrades to a savepoint). For
        # every other API path no transaction is open yet, so we open one
        # here to carry the audit context for the duration of the request.
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("SET LOCAL app.client_ip = %s", [ip_address])
                    cursor.execute("SET LOCAL app.user_agent = %s", [user_agent])
                    cursor.execute("SET LOCAL app.request_path = %s", [request_path])

                # Proceed with the request
                return self.get_response(request)
        except Exception:
            # Audit metadata must not break the request, but a failure to
            # set it is a real defect (audit rows lose their context) —
            # log it rather than silently swallowing (L-04 discipline).
            logger.warning(
                "audit_context: failed to set audit session variables",
                exc_info=True,
            )
            raise

    def _get_client_ip(self, request: HttpRequest) -> str:
        """
        Get the client IP address from the request.

        Checks X-Forwarded-For header first (for proxies), then REMOTE_ADDR.

        NOTE (audit M-14): X-Forwarded-For is client-controlled unless a
        trusted proxy count is pinned; audit IPs are best-effort until the
        deployment defines a trusted proxy configuration.
        """
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            # Get the first IP in the chain (client IP)
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR", "")

        # Limit length and validate
        ip = ip[:45]  # IPv6 max length

        # Basic validation - return empty if invalid
        if not ip or " " in ip:
            return ""

        return ip
