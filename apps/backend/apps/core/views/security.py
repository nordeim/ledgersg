"""
Security-related views for CSP violation reporting (SEC-003).

This module provides endpoints for monitoring Content Security Policy violations
reported by browsers. Violations are logged for security analysis.

Reference: REMEDIATION_PLAN.md - Phase 1, Step 1.3
"""

import logging
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([AllowAny])  # Allow anonymous CSP reports from browsers
@csrf_exempt
@require_POST
def csp_report_view(request: Request) -> HttpResponse:
    """
    Handle CSP violation reports from browsers.

    Browsers send violation reports to this endpoint when CSP policies are violated.
    Reports are logged for security monitoring and analysis.

    Args:
        request: Django REST Framework request containing CSP violation data

    Returns:
        HttpResponse: 204 No Content (standard CSP report response)

    Security Notes:
        - Endpoint is CSRF-exempt (browsers don't send CSRF tokens with CSP reports)
        - Returns 204 even on error (fail silently for security)
        - Logs violations for monitoring and analysis

    Example CSP Report Payload:
        {
            "csp-report": {
                "document-uri": "http://example.com/",
                "referrer": "",
                "violated-directive": "script-src",
                "effective-directive": "script-src",
                "original-policy": "default-src 'self'",
                "blocked-uri": "http://evil.com/script.js",
                "status-code": 200
            }
        }
    """
    try:
        violation_data = request.data

        logger.warning(
            "CSP Violation Detected",
            extra={
                "violation": violation_data,
                "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                "ip_address": request.META.get("REMOTE_ADDR", ""),
                "path": request.META.get("PATH_INFO", ""),
            },
        )

    except Exception as e:
        logger.error(f"Error processing CSP report: {e}")

    return HttpResponse(status=204)
