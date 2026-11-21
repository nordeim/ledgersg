"""
Refresh-cookie session persistence tests (P4/E-1).

The P3 register documented that every full page reload dropped the session:
the backend returns the token pair in the login body and sets no cookie, the
frontend discards the refresh token, and `tryRefreshToken` posts an empty
body the body-based refresh endpoint 400s. This sprint closes the loop with
an HttpOnly refresh cookie (the design the api-client header always claimed):

- login and register set the cookie alongside the body tokens
- refresh accepts the cookie when the body has no token (and rotates it)
- logout accepts the cookie, blacklists it, and expires the cookie
- change_password expires the cookie (all refresh tokens are revoked)

Cookie contract: HttpOnly, SameSite=Lax, Path=/api/v1/auth/, Secure=!DEBUG,
7-day max_age (REFRESH_TOKEN_LIFETIME).

The client-side evidence gate (P4/E-1 refinement, discovered in the e2e run):
refreshing on EVERY 401 turned an anonymous failure (bad login credentials)
into a pointless refresh POST that flooded the refresh rate limit and
swallowed the caller's error. The fix: a second, non-secret `session_hint`
marker cookie — JS-readable (NOT HttpOnly, path=/) so the api-client can see
"a session exists, attempt the refresh"; deleted on logout / password change
/ a failed cookie-refresh so dead evidence cannot linger.
"""

import pytest
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.services import auth_service

COOKIE_NAME = "refresh_token"
HINT_COOKIE_NAME = "session_hint"
LOGIN_URL = "/api/v1/auth/login/"
REGISTER_URL = "/api/v1/auth/register/"
REFRESH_URL = "/api/v1/auth/refresh/"
LOGOUT_URL = "/api/v1/auth/logout/"


def _login(api_client, test_user):
    """Login through the public endpoint (the conftest fixture password)."""
    return api_client.post(
        LOGIN_URL,
        {"email": test_user.email, "password": "testpassword123"},
        format="json",
    )


def _cookie_attrs(response):
    morsel = response.cookies[COOKIE_NAME]
    return {
        "value": morsel.value,
        "httponly": bool(morsel["httponly"]),
        "path": morsel["path"],
        "samesite": morsel["samesite"] or "",
        "secure": bool(morsel["secure"]),
        "max-age": morsel["max-age"],
    }


def _assert_refresh_cookie_contract(response):
    """The cookie must be HttpOnly, auth-path-scoped, SameSite=Lax, 7-day."""
    assert COOKIE_NAME in response.cookies, "login must set the refresh cookie"
    attrs = _cookie_attrs(response)
    assert attrs["httponly"] is True, "refresh cookie must be HttpOnly"
    assert attrs["path"] == "/api/v1/auth/", (
        "refresh cookie must be scoped to the auth endpoints only, got "
        f"{attrs['path']!r}"
    )
    assert attrs["samesite"].lower() == "lax", f"SameSite must be Lax, got {attrs['samesite']!r}"
    assert attrs["secure"] == (not settings.DEBUG), (
        "Secure flag must be tied to !DEBUG"
    )
    expected_seconds = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
    assert attrs["max-age"] == expected_seconds, (
        f"cookie max-age must match REFRESH_TOKEN_LIFETIME ({expected_seconds}s), "
        f"got {attrs['max-age']!r}"
    )


@pytest.mark.django_db
def test_login_sets_httponly_refresh_cookie(api_client, test_user):
    """RED for E-1: the login response must carry the HttpOnly refresh cookie."""
    response = _login(api_client, test_user)
    assert response.status_code == 200
    _assert_refresh_cookie_contract(response)


@pytest.mark.django_db
def test_register_sets_httponly_refresh_cookie(db, api_client):
    """RED for E-1: registration must set the same cookie (new-session UX)."""
    response = api_client.post(
        REGISTER_URL,
        {
            "email": "cookie-reg@ledgersg.sg",
            # min_length=12 + Django validate_password: pass the validator
            "password": "wqj2cFp8mZtR4aKy",
            "full_name": "Cookie Reg",
        },
        format="json",
    )
    assert response.status_code in (201, 200), response.data
    _assert_refresh_cookie_contract(response)


@pytest.mark.django_db
def test_refresh_with_cookie_and_no_body_returns_tokens(api_client, test_user):
    """RED for E-1: refresh must accept the cookie when the body is empty.

    This is the exact production path of the remediated client: the browser
    replays the HttpOnly cookie via credentials:'include' with no body.
    """
    login_response = _login(api_client, test_user)
    cookie_value = login_response.cookies[COOKIE_NAME].value

    api_client.cookies[COOKIE_NAME] = cookie_value
    response = api_client.post(REFRESH_URL, {}, format="json")

    assert response.status_code == 200, response.data
    assert "access" in response.data["tokens"], "rotated pair must be in the body"


@pytest.mark.django_db
def test_refresh_rotation_blacklists_the_cookie_value(api_client, test_user):
    """RED for E-1: rotating via the cookie must kill the old cookie value.

    Rotation semantics must be identical to the body path (H-05): the cookie
    used for a refresh is blacklisted; the response sets the NEW rotated
    cookie.
    """
    login_response = _login(api_client, test_user)
    old_cookie = login_response.cookies[COOKIE_NAME].value

    api_client.cookies[COOKIE_NAME] = old_cookie
    first = api_client.post(REFRESH_URL, {}, format="json")
    assert first.status_code == 200
    new_cookie = first.cookies[COOKIE_NAME].value
    assert new_cookie != old_cookie, "the refresh response must rotate the cookie"

    # The OLD cookie value is dead (blacklisted by rotation).
    api_client.cookies[COOKIE_NAME] = old_cookie
    replay = api_client.post(REFRESH_URL, {}, format="json")
    assert replay.status_code == 401, "a replayed rotated cookie must be rejected"

    # The NEW cookie value works (proves the rotation was persisted).
    api_client.cookies[COOKIE_NAME] = new_cookie
    second = api_client.post(REFRESH_URL, {}, format="json")
    assert second.status_code == 200


@pytest.mark.django_db
def test_body_refresh_still_works(api_client, test_user):
    """Backward compatibility: the documented body refresh path is unchanged."""
    login_response = _login(api_client, test_user)
    body_refresh = login_response.data["tokens"]["refresh"]

    response = api_client.post(REFRESH_URL, {"refresh": body_refresh}, format="json")
    assert response.status_code == 200
    assert response.data["tokens"]["refresh"] != body_refresh


@pytest.mark.django_db
def test_logout_with_cookie_blacklists_and_expires(api_client, test_user):
    """RED for E-1: logout must accept the cookie, blacklist it, and delete it."""
    login_response = _login(api_client, test_user)
    cookie_value = login_response.cookies[COOKIE_NAME].value

    # logout_view is IsAuthenticated — carry the login access token
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {login_response.data['tokens']['access']}"
    )
    api_client.cookies[COOKIE_NAME] = cookie_value
    response = api_client.post(LOGOUT_URL, {}, format="json")
    assert response.status_code == 200
    api_client.credentials()

    # The cookie is expired client-side…
    assert COOKIE_NAME in response.cookies, "logout must delete the refresh cookie"
    expired = _cookie_attrs(response)
    assert expired["max-age"] == 0 or expired["value"] == "", (
        "logout response must expire the refresh cookie"
    )

    # …and blacklisted server-side (the old value cannot refresh anymore).
    api_client.cookies[COOKIE_NAME] = cookie_value
    replay = api_client.post(REFRESH_URL, {}, format="json")
    assert replay.status_code == 401


@pytest.mark.django_db
def test_change_password_expires_the_refresh_cookie(api_client, test_user):
    """RED for E-1: password change revokes all refresh tokens; the cookie must die too."""
    login_response = _login(api_client, test_user)
    cookie_value = login_response.cookies[COOKIE_NAME].value

    access_token = login_response.data["tokens"]["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
    response = api_client.post(
        "/api/v1/auth/change-password/",
        {
            "old_password": "testpassword123",
            "new_password": "wqj2cFp8mZtR4aKy",
        },
        format="json",
    )
    assert response.status_code == 200, response.data
    api_client.credentials()

    assert COOKIE_NAME in response.cookies, (
        "change_password must expire the refresh cookie (all sessions revoked)"
    )
    expired = _cookie_attrs(response)
    assert expired["max-age"] == 0 or expired["value"] == ""

    # And the old cookie value is revoked server-side.
    api_client.cookies[COOKIE_NAME] = cookie_value
    replay = api_client.post(REFRESH_URL, {}, format="json")
    assert replay.status_code == 401


@pytest.mark.django_db
def test_logout_with_body_token_unchanged(auth_client, test_user):
    """Backward compatibility: body logout still blacklists (existing contract)."""
    refresh = RefreshToken.for_user(test_user)
    response = auth_client.post(LOGOUT_URL, {"refresh": str(refresh)}, format="json")
    assert response.status_code == 200

    from common.exceptions import ValidationError as LedgerSGValidationError

    with pytest.raises(LedgerSGValidationError):
        auth_service.refresh_access_token(str(refresh))


# --- The client-side evidence gate: the session_hint marker cookie (P4/E-1
# refinement). Refreshing on EVERY 401 made an anonymous failure (bad login
# credentials) trigger a pointless refresh POST — flooding the refresh rate
# limit and swallowing the login form's error. The hint cookie is the
# browser-readable evidence that a session exists. ---


def _hint_attrs(response):
    morsel = response.cookies[HINT_COOKIE_NAME]
    return {
        "value": morsel.value,
        "httponly": bool(morsel["httponly"]),
        "path": morsel["path"],
        "samesite": morsel["samesite"] or "",
        "secure": bool(morsel["secure"]),
        "max-age": morsel["max-age"],
    }


def _assert_hint_cookie_contract(response):
    """The hint must be JS-readable, page-wide, Lax, and live as long as the
    refresh token — a marker only, no secret material."""
    assert HINT_COOKIE_NAME in response.cookies, (
        "the session_hint marker cookie must be set alongside the refresh cookie"
    )
    attrs = _hint_attrs(response)
    assert attrs["httponly"] is False, (
        "the hint must NOT be HttpOnly — it is the JavaScript-side evidence gate"
    )
    assert attrs["path"] == "/", (
        f"the hint must be readable on every page (path=/), got {attrs['path']!r}"
    )
    assert attrs["samesite"].lower() == "lax", f"SameSite must be Lax, got {attrs['samesite']!r}"
    assert attrs["secure"] == (not settings.DEBUG)
    expected_seconds = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
    assert attrs["max-age"] == expected_seconds, (
        f"hint max-age must match REFRESH_TOKEN_LIFETIME ({expected_seconds}s), "
        f"got {attrs['max-age']!r}"
    )


@pytest.mark.django_db
def test_login_sets_js_readable_session_hint(api_client, test_user):
    """RED: login must set the evidence marker with the hint contract."""
    response = _login(api_client, test_user)
    assert response.status_code == 200
    _assert_hint_cookie_contract(response)


@pytest.mark.django_db
def test_refresh_success_renews_the_session_hint(api_client, test_user):
    """RED: a successful (rotating) refresh must renew the evidence marker."""
    login_response = _login(api_client, test_user)
    api_client.cookies[COOKIE_NAME] = login_response.cookies[COOKIE_NAME].value

    response = api_client.post(REFRESH_URL, {}, format="json")
    assert response.status_code == 200
    _assert_hint_cookie_contract(response)


@pytest.mark.django_db
def test_logout_deletes_the_session_hint(api_client, test_user):
    """RED: logout must expire the hint with the refresh cookie."""
    login_response = _login(api_client, test_user)
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {login_response.data['tokens']['access']}"
    )
    api_client.cookies[COOKIE_NAME] = login_response.cookies[COOKIE_NAME].value

    response = api_client.post(LOGOUT_URL, {}, format="json")
    assert response.status_code == 200
    api_client.credentials()

    assert HINT_COOKIE_NAME in response.cookies, "logout must expire the hint"
    expired = _hint_attrs(response)
    assert expired["max-age"] in ("0", 0) or expired["value"] == "", (
        "the logout response must expire the session_hint cookie"
    )


@pytest.mark.django_db
def test_change_password_deletes_the_session_hint(api_client, test_user):
    """RED: password change revokes every session — the hint must die too."""
    login_response = _login(api_client, test_user)
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {login_response.data['tokens']['access']}"
    )
    api_client.cookies[COOKIE_NAME] = login_response.cookies[COOKIE_NAME].value

    response = api_client.post(
        "/api/v1/auth/change-password/",
        {
            "old_password": "testpassword123",
            "new_password": "wqj2cFp8mZtR4aKy",
        },
        format="json",
    )
    assert response.status_code == 200, response.data
    api_client.credentials()

    assert HINT_COOKIE_NAME in response.cookies, (
        "change_password must expire the session_hint cookie"
    )
    expired = _hint_attrs(response)
    assert expired["max-age"] in ("0", 0) or expired["value"] == ""


@pytest.mark.django_db
def test_refresh_failure_with_cookie_expires_stale_evidence(api_client, test_user):
    """RED: a dead refresh cookie must not leave stale evidence behind — the
    401 response expires BOTH cookies so the browser stops carrying them."""
    api_client.cookies[COOKIE_NAME] = "not-a-valid-refresh-token"

    response = api_client.post(REFRESH_URL, {}, format="json")
    assert response.status_code == 401, "an invalid cookie must be rejected"

    for name, label in (
        (COOKIE_NAME, "refresh cookie"),
        (HINT_COOKIE_NAME, "session_hint marker"),
    ):
        assert name in response.cookies, (
            f"a failed cookie-refresh must expire the {label} (dead evidence)"
        )
        morsel = response.cookies[name]
        assert morsel["max-age"] in ("0", 0) or morsel.value == ""


@pytest.mark.django_db
def test_refresh_failure_with_body_does_not_touch_cookies(api_client, test_user):
    """A failed BODY refresh (API-client path) must not send Set-Cookie
    headers — the API client never carried browser evidence."""
    response = api_client.post(REFRESH_URL, {"refresh": "not-a-valid-token"}, format="json")
    assert response.status_code == 401

    assert COOKIE_NAME not in response.cookies, (
        "the body path must not set or expire browser cookies"
    )
    assert HINT_COOKIE_NAME not in response.cookies
