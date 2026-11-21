"""
RLS transaction-scoping invariants (C-03 remediation).

Production runs views under ATOMIC_REQUESTS: the request transaction opens
strictly INSIDE the view, AFTER middleware code has run. A `SET LOCAL`
executed directly in middleware therefore lands in its own autocommit
statement and is discarded before any view query — RLS is ineffective.

These tests use TransactionTestCase (no wrapping test transaction — the same
autocommit semantics as production) and assert the session variable is live
*while the view executes*, which is the only place it matters.
"""

import uuid

import pytest
from django.test import RequestFactory, TransactionTestCase
from django.http import HttpResponse
from django.db import connection
from django.utils import timezone

from common.middleware.tenant_context import TenantContextMiddleware
from apps.core.models import Organisation, UserOrganisation, Role, AppUser


def _make_role(org):
    return Role.objects.create(
        org=org,
        name="OWNER",
        can_manage_org=True,
        can_manage_users=True,
        can_manage_coa=True,
        can_create_invoices=True,
        can_approve_invoices=True,
        can_void_invoices=True,
        can_create_journals=True,
        can_manage_banking=True,
        can_file_gst=True,
        can_view_reports=True,
        can_export_data=True,
    )


def _make_org(name):
    return Organisation.objects.create(
        name=name,
        base_currency="SGD",
        gst_registered=False,
        uen=f"T{uuid.uuid4().hex[:10]}",
    )


class TestRLSTransactionScoping(TransactionTestCase):
    """The setting must be live inside the view under autocommit semantics."""

    def setUp(self):
        self.factory = RequestFactory()
        self.org = _make_org("RLS Org A")
        self.role = _make_role(self.org)
        self.user = AppUser.objects.create_user(
            email=f"rls_tx_{uuid.uuid4().hex[:8]}@example.com", password="testpass123"
        )
        UserOrganisation.objects.create(
            user=self.user, org=self.org, role=self.role, accepted_at=timezone.now()
        )
        # Rows created during the test for later cleanup (unmanaged tables are
        # NOT truncated automatically by TransactionTestCase)
        self._orgs = [self.org]
        self._users = [self.user]

    def tearDown(self):
        # Unmanaged models are outside Django's truncation — clean up manually
        # so later test classes do not hit unique constraints on leftovers.
        UserOrganisation.objects.filter(user__in=self._users).delete()
        for org in self._orgs:
            # CASCADE removes roles/contacts; RLS is not active for the
            # superuser-ish test connection (app role bypasses via FORCE off
            # for table owner in test DB)
            Organisation.objects.filter(id=org.id).delete()
        AppUser.objects.filter(id__in=[u.id for u in self._users]).delete()

    def test_set_local_is_live_inside_view_under_autocommit(self):
        """
        RED for C-03: with the middleware fixed, the org session variable
        must be visible to queries made BY THE VIEW (inside the request
        transaction). Under the old code the SET LOCAL was discarded before
        the view ran, so this assertion saw an empty string.
        """
        seen = {}

        def view(request):
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_setting('app.current_org_id', true)")
                seen["org_id"] = cursor.fetchone()[0]
            return HttpResponse("ok")

        request = self.factory.get(f"/api/v1/{self.org.id}/banking/bank-accounts/")
        request.user = self.user

        response = TenantContextMiddleware(view)(request)

        assert response.status_code == 200
        assert seen["org_id"] == str(self.org.id), (
            "app.current_org_id must be set for the duration of the view; "
            f"got {seen['org_id']!r} — SET LOCAL is being executed outside "
            "the request transaction (C-03)"
        )

    def test_unauthenticated_request_fails_closed(self):
        """Unauthenticated org-scoped requests must leave RLS in deny-all mode."""

        class AnonymousUser:
            is_authenticated = False

        seen = {}

        def view(request):
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_setting('app.current_org_id', true)")
                seen["org_id"] = cursor.fetchone()[0]
            return HttpResponse("ok")

        request = self.factory.get(f"/api/v1/{self.org.id}/banking/bank-accounts/")
        request.user = AnonymousUser()

        TenantContextMiddleware(view)(request)

        assert seen["org_id"] in (None, ""), (
            "Unauthenticated requests must not leak an org context; "
            f"got {seen['org_id']!r}"
        )

    def test_cross_org_access_denied(self):
        """A member of org A requesting org B's URL gets 403, not data."""
        org_b = _make_org("RLS Org B")
        role_b = _make_role(org_b)
        user_b = AppUser.objects.create_user(
            email=f"rls_tx_b_{uuid.uuid4().hex[:8]}@example.com", password="testpass123"
        )
        self._orgs.append(org_b)
        self._users.append(user_b)
        UserOrganisation.objects.create(
            user=user_b, org=org_b, role=role_b, accepted_at=timezone.now()
        )

        request = self.factory.get(f"/api/v1/{org_b.id}/banking/bank-accounts/")
        request.user = self.user  # member of org A only

        response = TenantContextMiddleware(lambda r: HttpResponse("ok"))(request)
        assert response.status_code == 403

    def test_rls_actually_filters_rows_for_app_role(self):
        """
        End-to-end RLS from the application role's perspective (C-03
        verification ledger item: "raw cross-tenant SELECT returns no
        foreign rows under autocommit").

        The Django test connection runs as the superuser that loaded the
        schema (superusers always bypass RLS), so this test connects as the
        real application role — ledgersg_app — which the schema's FORCE ROW
        LEVEL SECURITY policies bind. With app.current_org_id set for org A,
        a raw SELECT on a tenant table must return only org A rows, and with
        no context set it must return none.
        """
        import psycopg

        from apps.core.models import Contact
        from django.conf import settings

        org_b = _make_org("RLS Org C")
        self._orgs.append(org_b)
        Contact.objects.create(
            org=self.org, contact_type="CUSTOMER", name="Org A contact"
        )
        Contact.objects.create(
            org=org_b, contact_type="CUSTOMER", name="Org B contact"
        )

        db = settings.DATABASES["default"]
        # The schema (§15) provisions ledgersg_app with a placeholder
        # password; tests rely on the documented dev default.
        conn = psycopg.connect(
            host=db["HOST"],
            port=db["PORT"],
            dbname=db["NAME"],
            user="ledgersg_app",
            password="CHANGE_ME_IN_PRODUCTION",
        )
        try:
            with conn.transaction():
                conn.execute(
                    "SELECT set_config('app.current_org_id', %s, true)",
                    [str(self.org.id)],
                )
                rows = conn.execute("SELECT count(*) FROM invoicing.contact").fetchone()
                assert rows[0] == 1, (
                    "RLS must restrict the app role to the current org's rows; "
                    f"got {rows[0]} rows"
                )
            # Outside the transaction the setting is gone: deny-all
            rows = conn.execute("SELECT count(*) FROM invoicing.contact").fetchone()
            assert rows[0] == 0, (
                "Without an org context the app role must see no tenant rows; "
                f"got {rows[0]} rows"
            )
        finally:
            conn.close()
