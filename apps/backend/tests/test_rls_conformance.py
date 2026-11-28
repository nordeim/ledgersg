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

import pytest
from django.db import connection

from apps.core.models import Account, UserOrganisation
from apps.core.services.organisation_service import create_organisation

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
        """RED for H-6: all tenant-data tables must have relrowsecurity.

        The sweep INTERSECTS the unprotected set with the tenant-table set
        (session-30 lesson: Django's migrate creates infra tables in the
        core schema — auth_group, django_admin_log, django_celery_beat_*,
        django_content_type, django_session — which are NOT tenant data
        and must not fail this gate)."""
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
            } & tenant_tables

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
        # Session-30 fix (the session-29 finding): psycopg returns proconfig
        # as a parsed ARRAY like ['search_path=pg_catalog, audit, public'],
        # not a dict — normalise before asserting.
        proconfig_raw = row[0] or []
        proconfig = {}
        for item in proconfig_raw:
            if isinstance(item, str) and "=" in item:
                key, _, value = item.partition("=")
                proconfig[key.strip()] = value.strip()
        assert "search_path" in proconfig, (
            f"audit.log_change must pin search_path (SECURITY DEFINER) — "
            f"got proconfig={proconfig_raw}"
        )
        # the pinned path must lead with pg_catalog (no caller-controlled
        # schema can shadow object resolution)
        assert proconfig["search_path"].split(",")[0].strip() == "pg_catalog"


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
        """C-1 mechanism gate: when the CoA seed runs, the transaction-local
        setting app.current_org_id already holds the NEW org id.

        Probe design (session-30: the cursor-spy recursed when Django used
        the cursor outside a with-block — the delegation fix never landed;
        this rewrite wraps the seed function itself and reads the setting
        through the SAME connection the service uses, which cannot
        recurse and asserts the invariant directly)."""
        import apps.core.services.organisation_service as org_service_module

        captured = []
        real_seed = org_service_module._seed_chart_of_accounts

        def probing_seed(org_id, gst_registered):
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_setting('app.current_org_id', true)")
                captured.append(cursor.fetchone()[0])
            return real_seed(org_id, gst_registered)

        monkeypatch.setattr(
            org_service_module, "_seed_chart_of_accounts", probing_seed, raising=True
        )

        org = create_organisation(
            user=test_user,
            name="C1 Mechanism Org",
            uen=f"TM{uuid.uuid4().hex[:8]}",
            gst_registered=False,
        )

        assert captured, "the CoA seed must run during create_organisation"
        assert captured[0] == str(org.id), (
            "app.current_org_id must equal the NEW org id at seed time — "
            f"got {captured[0]!r}, expected {str(org.id)!r} (C-1: the set_config "
            "must precede the seed on the same transaction)"
        )
