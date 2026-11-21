"""
Authentication service for LedgerSG.

Handles user registration, login, and token management.
"""

from datetime import timedelta

from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.models import AppUser
from common.exceptions import ValidationError


def register_user(email: str, password: str, full_name: str, phone: str = "") -> AppUser:
    """
    Register a new user.

    Args:
        email: User email address
        password: User password (min 12 chars)
        full_name: User full name
        phone: Optional phone number

    Returns:
        Created AppUser instance

    Raises:
        ValidationError: If email already exists or password invalid
    """
    # Check if email exists
    if AppUser.objects.filter(email=email.lower()).exists():
        raise ValidationError("Email already registered.")

    # Create user
    with transaction.atomic():
        user = AppUser.objects.create_user(
            email=email.lower(),
            password=password,
            full_name=full_name,
        )
        if phone:
            user.phone = phone
            user.save()

    return user


def login_user(email: str, password: str) -> tuple[AppUser, dict]:
    """
    Authenticate user and generate JWT tokens.

    Args:
        email: User email address
        password: User password

    Returns:
        Tuple of (user, token_dict)

    Raises:
        ValidationError: If credentials invalid
    """
    # Authenticate
    user = authenticate(email=email.lower(), password=password)

    if not user:
        raise ValidationError("Invalid email or password.")

    if not user.is_active:
        raise ValidationError("Account is disabled.")

    # Generate tokens
    tokens = generate_tokens(user)

    return user, tokens


def generate_tokens(user: AppUser) -> dict:
    """
    Generate JWT tokens for user.

    Args:
        user: AppUser instance

    Returns:
        Dict with access, refresh tokens and expiry
    """
    from apps.core.models import UserOrganisation

    refresh = RefreshToken.for_user(user)

    # Add default_org_id claim to token
    user_org = UserOrganisation.objects.filter(user=user, is_default=True).first()
    if user_org:
        refresh["default_org_id"] = str(user_org.org_id)
        refresh["default_org_name"] = user_org.org.name
    else:
        # Fallback to first accepted org
        user_org = UserOrganisation.objects.filter(user=user, accepted_at__isnull=False).first()
        if user_org:
            refresh["default_org_id"] = str(user_org.org_id)
            refresh["default_org_name"] = user_org.org.name

    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "access_expires": timezone.now() + timedelta(minutes=15),
    }


def refresh_access_token(refresh_token: str) -> dict:
    """
    Refresh access token using refresh token — WITH ROTATION (H-05).

    The old implementation echoed the same refresh token back, leaving a
    stolen token replayable for its full 7-day lifetime. Now every refresh
    mints a NEW refresh token and blacklists the predecessor, matching
    ROTATE_REFRESH_TOKENS / BLACKLIST_AFTER_ROTATION semantics.

    Args:
        refresh_token: Refresh token string

    Returns:
        Dict with new access token, new refresh token, aware expiry

    Raises:
        ValidationError: If token invalid or blacklisted
    """
    from django.conf import settings as django_settings

    try:
        refresh = RefreshToken(refresh_token)
    except Exception as e:
        raise ValidationError(f"Invalid refresh token: {str(e)}") from e

    # Reject already-blacklisted tokens (logout / password change / reuse)
    try:
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

        if BlacklistedToken.objects.filter(token__jti=refresh["jti"]).exists():
            raise ValidationError("Refresh token has been revoked.")
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f"Invalid refresh token: {str(e)}") from e

    try:
        # Preserve the org context claims across rotation
        default_org_id = refresh.get("default_org_id")
        default_org_name = refresh.get("default_org_name")

        # Blacklist the predecessor, then mint the successor
        try:
            refresh.blacklist()
        except AttributeError:
            # token_blacklist app not available — fail closed rather than
            # silently skipping revocation
            raise ValidationError("Token revocation is not available.") from None

        new_refresh = RefreshToken()
        new_refresh["user_id"] = refresh["user_id"]
        if default_org_id:
            new_refresh["default_org_id"] = default_org_id
        if default_org_name:
            new_refresh["default_org_name"] = default_org_name

        access_lifetime = django_settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"]
        return {
            "access": str(new_refresh.access_token),
            "refresh": str(new_refresh),
            "access_expires": timezone.now() + access_lifetime,
        }
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f"Invalid refresh token: {str(e)}") from e


def change_password(user: AppUser, old_password: str, new_password: str) -> None:
    """
    Change user password.

    Revokes every outstanding refresh token for the user (H-05): a password
    change after a suspected compromise must not leave the attacker's
    sessions valid for up to 7 days.

    Args:
        user: AppUser instance
        old_password: Current password
        new_password: New password

    Raises:
        ValidationError: If old password incorrect or new password invalid
    """
    # Verify old password
    if not user.check_password(old_password):
        raise ValidationError("Current password is incorrect.")

    # Set new password
    user.set_password(new_password)
    user.save()

    # Revoke all outstanding refresh tokens for this user
    _blacklist_all_user_tokens(user)


def get_user_organisations(user: AppUser):
    """
    Get organisations the user belongs to.

    Args:
        user: AppUser instance

    Returns:
        QuerySet of UserOrganisation
    """
    from apps.core.models import UserOrganisation

    return (
        UserOrganisation.objects.filter(
            user=user,
            accepted_at__isnull=False,
        )
        .select_related("org", "role")
        .order_by("-is_default", "org__name")
    )


def logout_user(refresh_token: str) -> None:
    """
    Blacklist refresh token on logout (H-05).

    With the token_blacklist app installed (schema §15b) this now actually
    revokes the token. Failures are logged rather than silently swallowed:
    a logout that does not revoke is a security defect, not a no-op.

    Args:
        refresh_token: Refresh token string
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
    except Exception as e:
        # Token may already be blacklisted or invalid — that is acceptable
        # for logout idempotency, but it must be visible, not silent (L-04).
        logger.warning("logout_user: could not blacklist token: %s", e)


def _blacklist_all_user_tokens(user: AppUser) -> int:
    """
    Blacklist every outstanding refresh token for a user.

    Used by change_password to revoke all sessions after a credential
    change. Returns the number of tokens revoked.
    """
    from rest_framework_simplejwt.token_blacklist.models import (
        BlacklistedToken,
        OutstandingToken,
    )

    revoked = 0
    for outstanding in OutstandingToken.objects.filter(user=user):
        _, created = BlacklistedToken.objects.get_or_create(token=outstanding)
        if created:
            revoked += 1
    return revoked
