"""
Authentication views for LedgerSG.
"""

from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.permissions import IsAuthenticatedOrOptions
from apps.core.serializers.auth import (
    ChangePasswordSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserProfileSerializer,
)
from apps.core.services import auth_service
from apps.core.views._refresh_cookie import (
    delete_session_cookies,
    get_refresh_cookie,
    set_session_cookies,
)
from common.exceptions import ValidationError


@api_view(["POST"])
@permission_classes([AllowAny])
@ratelimit(key="ip", rate="5/hour", block=True)
def register_view(request: Request) -> Response:
    """
    Register a new user.

    POST /api/v1/auth/register/
    Rate limit: 5 registrations per hour per IP.
    """
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        user = auth_service.register_user(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            full_name=serializer.validated_data["full_name"],
        )

        # Generate tokens
        tokens = auth_service.generate_tokens(user)

        response = Response(
            {
                "user": UserProfileSerializer(user).data,
                "tokens": tokens,
            },
            status=status.HTTP_201_CREATED,
        )
        # Browser session persistence: HttpOnly refresh cookie + the
        # JS-readable session_hint evidence marker (P4/E-1)
        set_session_cookies(response, tokens["refresh"])
        return response

    except ValidationError as e:
        return Response(
            {"error": {"code": e.code, "message": e.message}}, status=status.HTTP_400_BAD_REQUEST
        )


def _emit_auth_audit(user, action: str, request: Request) -> None:
    """P11/M-8: emit the curated LOGIN/LOGOUT audit row.

    LOGIN/LOGOUT have been in the event_log CHECK vocabulary since the
    schema shipped but no code ever emitted them. The row carries the
    request context (ip / user agent / path) directly — these are
    org-independent auth events (org_id is the user's default org when
    one exists, NULL for pre-org logins).
    """
    from apps.core.models import AuditEventLog, UserOrganisation

    membership = UserOrganisation.objects.filter(
        user=user, is_default=True
    ).select_related("org").first()

    try:
        AuditEventLog.objects.create(
            org=membership.org if membership else None,
            user=user,
            action=action,
            entity_schema="core",
            entity_table="app_user",
            entity_id=user.id,
            new_data={"email": user.email},
            ip_address=request.META.get("REMOTE_ADDR") or None,
            user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:500],
            request_path=request.path[:500],
        )
    except Exception:
        # Audit emission must not break the auth flow — but losing the row
        # is a real defect, so log it (the L-04 discipline).
        import logging

        logging.getLogger(__name__).warning(
            "audit emission failed for %s user=%s", action, user.id,
            exc_info=True,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
@ratelimit(key="ip", rate="config.ratelimits.login_ip", block=True)
@ratelimit(key="user_or_ip", rate="config.ratelimits.login_user", block=True)
def login_view(request: Request) -> Response:
    """
    Login user and return JWT tokens.

    POST /api/v1/auth/login/
    Rate limits (settings knobs, P4): LOGIN_RATELIMIT_IP (default 10/min
    per IP; 60/min in the development settings for the e2e budget) and
    LOGIN_RATELIMIT_USER (default 30/min per user_or_ip). Resolved lazily
    per request by django-ratelimit's dotted-path loader.
    """
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        user, tokens = auth_service.login_user(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )

        # P11/M-8: the login event lands in the immutable audit trail.
        _emit_auth_audit(user, "LOGIN", request)

        response = Response(
            {
                "user": UserProfileSerializer(user).data,
                "tokens": tokens,
            }
        )
        # Browser session persistence: HttpOnly refresh cookie + the
        # JS-readable session_hint evidence marker (P4/E-1)
        set_session_cookies(response, tokens["refresh"])
        return response

    except ValidationError as e:
        return Response(
            {"error": {"code": e.code, "message": e.message}}, status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(["POST"])
@permission_classes([AllowAny])
@ratelimit(key="ip", rate="config.ratelimits.refresh_ip", block=True)
def refresh_view(request: Request) -> Response:
    """
    Refresh access token.

    POST /api/v1/auth/refresh/
    Rate limit: 20/min per IP (settings knob REFRESH_RATELIMIT_IP —
    P6/E-1; development raises the budget for the local e2e suite).

    Token sources (P4/E-1): the request body `refresh` field (API clients,
    unchanged contract) OR the HttpOnly `refresh_token` cookie the browser
    replays via credentials:"include" (browser clients — cross-reload
    session persistence). Rotation is identical on both paths: the used
    token is blacklisted and the response sets the new rotated pair (body
    and cookie).

    On a failed COOKIE-path refresh the 401 expires both cookies: the
    browser must stop carrying dead session evidence (the JS-side hint
    gate would otherwise keep attempting refreshes against a dead token).
    A failed BODY-path refresh (API clients) sends no Set-Cookie headers.
    """
    body_token = request.data.get("refresh")
    refresh_token = body_token or get_refresh_cookie(request)

    if not refresh_token:
        return Response(
            {"error": {"code": "missing_token", "message": "Refresh token is required"}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        tokens = auth_service.refresh_access_token(refresh_token)
        response = Response({"tokens": tokens})
        set_session_cookies(response, tokens["refresh"])
        return response

    except ValidationError as e:
        response = Response(
            {"error": {"code": e.code, "message": e.message}}, status=status.HTTP_401_UNAUTHORIZED
        )
        if not body_token:
            # The cookie was the credential that just failed — expire the
            # dead evidence so the browser drops it (P4/E-1 refinement).
            delete_session_cookies(response)
        return response


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request: Request) -> Response:
    """
    Logout user (blacklist refresh token).

    POST /api/v1/auth/logout/

    Token sources (P4/E-1): body `refresh` field or the HttpOnly refresh
    cookie — whichever is present is blacklisted, and the cookie is expired.
    """
    refresh_token = request.data.get("refresh") or get_refresh_cookie(request)

    if refresh_token:
        auth_service.logout_user(refresh_token)

    # P11/M-8: the logout event lands in the immutable audit trail.
    _emit_auth_audit(request.user, "LOGOUT", request)

    response = Response({"message": "Logged out successfully"})
    delete_session_cookies(response)
    return response


@api_view(["GET", "PATCH", "OPTIONS"])  # Added OPTIONS for CORS preflight
@permission_classes([IsAuthenticatedOrOptions])  # Allow OPTIONS without auth
def me_view(request: Request) -> Response:
    """
    Get or update current user profile.

    GET /api/v1/auth/me/
    PATCH /api/v1/auth/me/
    OPTIONS /api/v1/auth/me/  # CORS preflight
    """
    # Handle OPTIONS preflight request
    if request.method == "OPTIONS":
        return Response(status=200)

    if request.method == "GET":
        return Response(UserProfileSerializer(request.user).data)

    # PATCH - update profile
    serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()

    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password_view(request: Request) -> Response:
    """
    Change user password.

    POST /api/v1/auth/change-password/
    """
    serializer = ChangePasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        auth_service.change_password(
            user=request.user,
            old_password=serializer.validated_data["old_password"],
            new_password=serializer.validated_data["new_password"],
        )

        # Every outstanding refresh token was revoked server-side — the
        # browser's refresh cookie (and the session_hint evidence marker)
        # must die with them (P4/E-1).
        response = Response({"message": "Password changed successfully"})
        delete_session_cookies(response)
        return response

    except ValidationError as e:
        return Response(
            {"error": {"code": e.code, "message": e.message}}, status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_organisations_view(request: Request) -> Response:
    """
    Get current user's organisations.

    GET /api/v1/auth/organisations/
    """
    memberships = auth_service.get_user_organisations(request.user)

    data = []
    for membership in memberships:
        data.append(
            {
                "id": str(membership.id),  # Membership ID
                "org": {
                    "id": str(membership.org.id),
                    "name": membership.org.name,
                    "legal_name": membership.org.legal_name,
                    "uen": membership.org.uen,
                    "entity_type": membership.org.entity_type,
                    "gst_registered": membership.org.gst_registered,
                    "gst_reg_number": membership.org.gst_reg_number,
                    "gst_reg_date": membership.org.gst_reg_date,
                    "gst_scheme": membership.org.gst_scheme,
                    "gst_filing_frequency": membership.org.gst_filing_frequency,
                    "peppol_participant_id": membership.org.peppol_participant_id,
                    "invoicenow_enabled": membership.org.invoicenow_enabled,
                    "fy_start_month": membership.org.fy_start_month,
                    "base_currency": membership.org.base_currency,
                    "timezone": membership.org.timezone,
                    "is_active": membership.org.is_active,
                },
                "role": {
                    "id": str(membership.role.id),
                    "name": membership.role.name,
                    "can_manage_org": membership.role.can_manage_org,
                    "can_manage_users": membership.role.can_manage_users,
                    "can_manage_coa": membership.role.can_manage_coa,
                    "can_create_invoices": membership.role.can_create_invoices,
                    "can_approve_invoices": membership.role.can_approve_invoices,
                    "can_void_invoices": membership.role.can_void_invoices,
                    "can_create_journals": membership.role.can_create_journals,
                    "can_manage_banking": membership.role.can_manage_banking,
                    "can_file_gst": membership.role.can_file_gst,
                    "can_view_reports": membership.role.can_view_reports,
                    "can_export_data": membership.role.can_export_data,
                },
                "is_default": membership.is_default,
            }
        )

    return Response(data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_default_org_view(request: Request) -> Response:
    """
    Set user's default organisation.

    POST /api/v1/auth/set-default-org/
    Body: { "org_id": "uuid" }
    """
    from apps.core.models import UserOrganisation

    org_id = request.data.get("org_id")
    if not org_id:
        return Response(
            {"error": {"code": "missing_org_id", "message": "org_id is required"}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Verify user belongs to this org
    try:
        user_org = UserOrganisation.objects.get(
            user=request.user, org_id=org_id, accepted_at__isnull=False
        )
    except UserOrganisation.DoesNotExist:
        return Response(
            {
                "error": {
                    "code": "unauthorized",
                    "message": "You do not have access to this organisation",
                }
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    # Clear existing default
    UserOrganisation.objects.filter(user=request.user, is_default=True).update(is_default=False)

    # Set new default
    user_org.is_default = True
    user_org.save(update_fields=["is_default"])

    return Response(
        {
            "message": "Default organisation updated",
            "default_org": {
                "id": str(user_org.org.id),
                "name": user_org.org.name,
            },
        }
    )
