"""
Token lifecycle security tests (H-05 core remediation).

Guards:
- refresh_access_token must ROTATE: return a new refresh token and blacklist
  the predecessor (previously it returned the same token, unrotated)
- logout must blacklist the refresh token (previously a no-op except: pass
  because token_blacklist was not installed)
- change_password must revoke outstanding refresh tokens
"""

import pytest


@pytest.mark.django_db
def test_refresh_rotates_the_refresh_token(test_user):
    """RED for H-05: refresh must mint a NEW refresh token, not echo the old one."""
    from rest_framework_simplejwt.tokens import RefreshToken

    from apps.core.services import auth_service

    old_refresh = RefreshToken.for_user(test_user)

    tokens = auth_service.refresh_access_token(str(old_refresh))

    assert "access" in tokens and "refresh" in tokens
    assert tokens["refresh"] != str(old_refresh), (
        "Refresh token must be rotated on use (ROTATE_REFRESH_TOKENS semantics)"
    )


@pytest.mark.django_db
def test_blacklisted_refresh_token_is_rejected(test_user):
    """RED for H-05: after rotation the old refresh token must be unusable."""
    from rest_framework_simplejwt.tokens import RefreshToken

    from apps.core.services import auth_service
    from common.exceptions import ValidationError as LedgerSGValidationError

    old_refresh = RefreshToken.for_user(test_user)
    auth_service.refresh_access_token(str(old_refresh))

    with pytest.raises(LedgerSGValidationError):
        auth_service.refresh_access_token(str(old_refresh))


@pytest.mark.django_db
def test_logout_blacklists_refresh_token(test_user):
    """RED for H-05: logout must make the refresh token unusable."""
    from rest_framework_simplejwt.tokens import RefreshToken

    from apps.core.services import auth_service
    from common.exceptions import ValidationError as LedgerSGValidationError

    refresh = RefreshToken.for_user(test_user)
    auth_service.logout_user(str(refresh))

    with pytest.raises(LedgerSGValidationError):
        auth_service.refresh_access_token(str(refresh))


@pytest.mark.django_db
def test_change_password_revokes_refresh_tokens(test_user):
    """RED for H-05: a password change must revoke existing sessions."""
    from rest_framework_simplejwt.tokens import RefreshToken

    from apps.core.services import auth_service
    from common.exceptions import ValidationError as LedgerSGValidationError

    refresh = RefreshToken.for_user(test_user)

    auth_service.change_password(
        test_user, "testpassword123", "new-secure-password-456"
    )

    with pytest.raises(LedgerSGValidationError):
        auth_service.refresh_access_token(str(refresh))


@pytest.mark.django_db
def test_refresh_expiry_uses_timezone_aware_datetime(test_user):
    """L-05: access_expires must be timezone-aware (USE_TZ = True)."""
    from rest_framework_simplejwt.tokens import RefreshToken

    from apps.core.services import auth_service

    refresh = RefreshToken.for_user(test_user)
    tokens = auth_service.refresh_access_token(str(refresh))

    expires = tokens["access_expires"]
    assert expires.tzinfo is not None, (
        f"access_expires must be timezone-aware, got naive {expires!r}"
    )
