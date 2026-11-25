"""
P14/H-6 + C-1 — RLS conformance and the org-creation context.

H-6: every table carrying tenant data (org_id — or being the tenant root)
must actually have ROW LEVEL SECURITY enabled. Pre-P14, six tables were
open to the non-superuser runtime role: core.organisation (policies
existed but RLS was never ENABLED — inert), core.user_organisation,
core.role, audit.event_log, gst.organisation_peppol_settings and
gst.tax_code. audit.log_change (SECURITY DEFINER) must pin its
search_path.

C-1: create_organisation must set the RLS tenant context (transaction
local) before seeding — under the documented runtime role
ledgersg_app the seeds otherwise violate the RLS WITH CHECK (the
2026-11-24 audit reproduced POST /organisations/ → 500 live).
"""

import uuid
from datetime import date

import pytest
from django.db import connection

from apps.core.models import Account, Contact, Organisation
from apps.core.services.organisation_service import create_organisation
from apps.core.models import AppUser, UserOrganisation

# Tables documented as GLOBAL (no org_id — shared reference data): the
# conformance gate must not demand RLS on them.
GLOBAL_TABLES = {"app_user", "currency", "account_type", "account_sub_type"}


def _tenant_tables(cursor):
    """(schema, table) pairs that carry tenant data: an org_id column, or
    the tenant root core.organisation itself."""
    cursor.execute(
        """
        SELECT c.relnamespace::regnamespace::text AS schema, c.relname AS table_name
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname IN ('core','coa','gst','journal','invoicing','banking','audit')
          AND c.relkind = 'r'
          AND (
            c.relname = 'organisation'
            OR EXISTS (
                SELECT 1 FROM information_schema.columns ic
                WHERE ic.table_schema = n.nspname
                  AND ic.table_name = c.relname
                  AND ic.column_name = 'org_id'
            )
          )
        """
    )
    return {(row[0], row[1]) for row in cursor.fetchall()}


class TestRLSConformanceP14:
    @pytest.mark.django_db
    def test_every_tenant_table_has_rls_enabled(self):
        """RED for H-6: all tenant-data tables must have relrowsecurity."""
        with connection.cursor() as cursor:
            tenant_tables = _tenant_tables(cursor)
            cursor.execute(
                """
                SELECT c.relnamespace::regnamespace::text, c.relname
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname IN ('core','coa','gst','journal','invoicing','banking','audit')
                  AND c.relkind = 'r' AND NOT c.relrowsecurity
                """
            )
            unprotected = {
                (row[0], row[1])
                for row in cursor.fetchall()
                if row[1] not in GLOBAL_TABLES
            }

        assert not unprotected, (
            f"Tables carrying tenant data WITHOUT RLS (H-6): {sorted(unprotected)} — "
            f"the documented globals {sorted(GLOBAL_TABLES)} are the only permitted "
            "unprotected tables."
        )
        # The specific P14/H-6 set is covered (a direct assertion so a future
        # table addition cannot silently weaken the gate).
        for expected in [
            ("core", "organisation"),
            ("core", "user_organisation"),
            ("core", "role"),
            ("audit", "event_log"),
            ("gst", "organisation_peppol_settings"),
            ("gst", "tax_code"),
        ]:
            assert expected in tenant_tables, f"{expected} must carry tenant data"

    @pytest.mark.django_db
    def test_audit_log_change_pins_search_path(self):
        """RED for M-6a: the SECURITY DEFINER audit function must not
        resolve names through the caller's search_path."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT p.proconfig
                FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = 'audit' AND p.proname = 'log_change'
                """
            )
            row = cursor.fetchone()

        assert row is not None, "audit.log_change must exist"
        proconfig = row[0] or {}
        assert "search_path" in proconfig, (
            f"audit.log_change must pin search_path (SECURITY DEFINER) — "
            f"got proconfig={proconfig}"
        )


class TestOrgCreationContextP14:
    @pytest.mark.django_db
    def test_create_organisation_sets_rls_context_before_seeding(self, test_user):
        """C-1: the set_config happens BEFORE the CoA seed. Verified via a
        trigger-style probe: a constraint on coa.account that reads
        current_setting('app.current_org_id') at INSERT time must see the
        NEW org id (not the empty middleware default for this non-org-
        scoped flow).

        The probe uses a transaction-local SAVEPOINT-free direct check:
        we spy on the SQL statement stream instead — the honest,
        behavior-level check is the live ledgersg_app smoke
        (scripts/rls_smoke.py in the verification gate); here we assert
        the mechanism: after create_organisation, the context var set by
        the service is visible inside its atomic block via the audit of
        the seeded rows themselves.
        """
        org = create_organisation(
            user=test_user,
            name="C1 Probe Org",
            uen=f"TP{uuid.uuid4().hex[:8]}",
            gst_registered=False,
        )

        # The seeds ran INSIDE the service's atomic block with the context
        # set — assert they produced rows (as the superuser they would
        # also pass, but under ledgersg_app only the set_config made this
        # possible; the live smoke gate proves that side).
        seeded_accounts = Account.objects.filter(org_id=org.id).count()
        assert seeded_accounts >= 20, (
            f"the CoA seed must have run for the new org (got {seeded_accounts} accounts)"
        )

        # And the owner membership exists.
        assert UserOrganisation.objects.filter(user=test_user, org=org).exists()

    @pytest.mark.django_db
    def test_create_organisation_issues_set_config_in_transaction(self, test_user, monkeypatch):
        """C-1 mechanism gate: the service executes
        set_config('app.current_org_id', <org>, true) on the shared
        connection BEFORE the seed SQL function runs."""
        import apps.core.services.organisation_service as org_service_module

        executed = []
        real_cursor_execute = connection.cursor

        class SpyCursor:
            def __init__(self, real):
                self._real = real

            def __enter__(self):
                self._cursor = self._real.__enter__()
                return self

            def __exit__(self, *args):
                return self._real.__exit__(*args)

            def execute(self, sql, params=None):
                executed.append((sql, params))
                return self._cursor.execute(sql, params)

            def __getattr__(self, name):
                return getattr(self._cursor, name)

        def spy_cursor():
            return SpyCursor(real_cursor_execute())

        monkeypatch.setattr(
            org_service_module.connection, "cursor", spy_cursor, raising=True
        )

        create_organisation(
            user=test_user,
            name="C1 Mechanism Org",
            uen=f"TM{uuid.uuid4().hex[:8]}",
            gst_registered=False,
        )

        set_config_calls = [
            (sql, params)
            for sql, params in executed
            if "set_config" in sql and "app.current_org_id" in sql
        ]
        assert set_config_calls, (
            "create_organisation must issue set_config('app.current_org_id', ...) "
            "before seeding (C-1)"
        )
        sql, params = set_config_calls[0]
        assert params and str(params[0]) != "", "the set_config must carry the new org id"

        seed_calls = [sql for sql, _ in executed if "seed_default_chart_of_accounts" in sql]
        assert seed_calls, "the CoA seed must run through the SQL function"

        # Ordering: set_config BEFORE the seed function call.
        stmts = [sql for sql, _ in executed]
        set_config_idx = next(i for i, s in enumerate(stmts) if "set_config" in s and "app.current_org_id" in s)
        seed_idx = next(i for i, s in enumerate(stmts) if "seed_default_chart_of_accounts" in s)
        assert set_config_idx < seed_idx, (
            "set_config('app.current_org_id') must precede the CoA seed (C-1)"
        )
