"""
Custom authentication classes for LedgerSG API.
"""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import exceptions


class CORSJWTAuthentication(JWTAuthentication):
    """
    JWT Authentication that skips authentication for OPTIONS requests.

    This allows CORS preflight requests to pass through without auth tokens,
    while maintaining authentication for actual data requests.

    CORS preflight requests (OPTIONS method) are sent by browsers before
    the actual request to check if CORS is allowed. These requests never
    include authentication tokens by design, so we need to skip JWT
    authentication for OPTIONS requests.

    Usage:
            REST_FRAMEWORK = {
                    'DEFAULT_AUTHENTICATION_CLASSES': [
                            'apps.core.authentication.CORSJWTAuthentication',
                    ],
            }
    """

    def authenticate(self, request):
        """
        Authenticate the request, but skip OPTIONS (CORS preflight).

        For OPTIONS requests, return None to indicate "no authentication required".
        For all other requests, use standard JWT authentication.

        Returns:
                None for OPTIONS requests
                Tuple (user, token) for authenticated requests
                Raises AuthenticationFailed for unauthenticated non-OPTIONS requests
        """
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            # Return None to indicate "no authentication provided"
            # This allows the request to proceed to permission checks
            return None

        # Apply normal JWT authentication for all other methods
        return super().authenticate(request)
