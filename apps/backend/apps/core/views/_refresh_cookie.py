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

The client-side evidence gate (P4/E-1 refinement): a second, NON-secret
`session_hint` marker cookie travels with the refresh cookie. It is
deliberately JS-readable (NOT HttpOnly, path=/) so the api-client can tell
"attempt the refresh — a session exists" from "this 401 is anonymous —
propagate it to the caller" without touching the HttpOnly token itself.
Refreshing on every 401 turned bad login credentials into a pointless
refresh POST that flooded the refresh rate limit and swallowed the caller's
error; the hint gate closes that. It dies wherever the refresh cookie dies
(logout / password change / failed cookie-refresh).
"""

from django.conf import settings

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth/"
SESSION_HINT_COOKIE_NAME = "session_hint"


def _refresh_lifetime_seconds() -> int:
    return int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())


def set_refresh_cookie(response, refresh_token: str) -> None:
    """Attach the (rotated) refresh token as an HttpOnly auth-path cookie."""
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=_refresh_lifetime_seconds(),
        httponly=True,
        samesite="Lax",
        secure=not settings.DEBUG,
        path=REFRESH_COOKIE_PATH,
    )


def set_session_hint(response) -> None:
    """Attach the JS-readable, non-secret session-evidence marker."""
    response.set_cookie(
        SESSION_HINT_COOKIE_NAME,
        "1",  # marker only — no secret material
        max_age=_refresh_lifetime_seconds(),
        httponly=False,  # intentionally JS-readable — the client's evidence gate
        samesite="Lax",
        secure=not settings.DEBUG,
        path="/",
    )


def delete_refresh_cookie(response) -> None:
    """Expire the refresh cookie (logout / password change / refresh failure)."""
    response.delete_cookie(
        REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        samesite="Lax",
    )


def delete_session_hint(response) -> None:
    """Expire the evidence marker (dead evidence must not linger)."""
    response.delete_cookie(
        SESSION_HINT_COOKIE_NAME,
        path="/",
        samesite="Lax",
    )


def set_session_cookies(response, refresh_token: str) -> None:
    """Set the full browser session evidence: HttpOnly token + hint marker."""
    set_refresh_cookie(response, refresh_token)
    set_session_hint(response)


def delete_session_cookies(response) -> None:
    """Expire both cookies (logout / password change / failed cookie-refresh)."""
    delete_refresh_cookie(response)
    delete_session_hint(response)


def get_refresh_cookie(request) -> str | None:
    """The refresh token from the request cookie, if the browser sent one."""
    return request.COOKIES.get(REFRESH_COOKIE_NAME)
