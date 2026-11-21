"""
HttpOnly refresh-token cookie helpers (P4/E-1).

Session persistence design: the login/register/refresh responses return the
token pair in the body (API clients) AND set the refresh token as an HttpOnly
cookie (browser clients). The browser replays the cookie on
`POST /api/v1/auth/refresh/` via `credentials: "include"` — the frontend
never handles the refresh token in JavaScript, honouring the repo's
zero-JWT-exposure mandate.

Cookie contract:
- name:   refresh_token
- path:   /api/v1/auth/  — the browser never sends it to data endpoints
- HttpOnly, SameSite=Lax (localhost:3000 -> localhost:8000 is same-site;
  cross-site topologies need None+Secure — see docs/DEPLOYMENT.md §9)
- Secure  = not DEBUG
- max_age = SIMPLE_JWT REFRESH_TOKEN_LIFETIME (7 days)
"""

from django.conf import settings

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth/"


def set_refresh_cookie(response, refresh_token: str) -> None:
    """Attach the (rotated) refresh token as an HttpOnly auth-path cookie."""
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=int(
            settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()
        ),
        httponly=True,
        samesite="Lax",
        secure=not settings.DEBUG,
        path=REFRESH_COOKIE_PATH,
    )


def delete_refresh_cookie(response) -> None:
    """Expire the refresh cookie (logout / password change / refresh failure)."""
    response.delete_cookie(
        REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        samesite="Lax",
    )


def get_refresh_cookie(request) -> str | None:
    """The refresh token from the request cookie, if the browser sent one."""
    return request.COOKIES.get(REFRESH_COOKIE_NAME)
