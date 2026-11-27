"""
P18 schema-source gates — §15c completion (v1.2.2).

BE-L1: §15c (v1.2.1) shipped django_content_type / auth_permission /
    django_migrations but intentionally omitted django_session and
    django_admin_log. The API never touches sessions (JWT + refresh
    cookies), so the flush path is fine — but the P17 ENABLE_ADMIN
    opt-in (the documented ops escape hatch; dev default TRUE) mounts
    an admin whose login + LogEntry writes hit exactly those tables.
    On a schema-only fresh host the opt-in 500s. §15c must cover the
    full ENABLE_ADMIN surface.

The honest gate is SOURCE-level (the SQL-First mandate): the schema
file is the single source of truth for what a documented fresh-host
load creates. A live-DB check would pass vacuously on environments
that ever ran `manage.py migrate` (the legacy leftovers).
"""

from pathlib import Path

import pytest

SCHEMA = (
    Path(__file__).resolve().parents[2]
    / "database_schema.sql"
)


def _section(sql: str, start: str, end: str) -> str:
    begin = sql.index(start)
    finish = sql.index(end, begin)
    return sql[begin:finish]


@pytest.fixture(scope="module")
def schema_sql() -> str:
    return SCHEMA.read_text()


class TestFrameworkTablesGateP18:
    def test_section_15c_creates_the_admin_optin_tables(self, schema_sql):
        """django_session + django_admin_log must exist in §15c — the
        ENABLE_ADMIN opt-in needs both (login writes sessions; admin
        actions write LogEntry)."""
        section = _section(
            schema_sql,
            "§15c  DJANGO FRAMEWORK TABLES",
            "§16  MONETARY CAPACITY WIDENING",
        )
        assert (
            "CREATE TABLE IF NOT EXISTS public.django_session" in section
        ), "§15c must create public.django_session (the ENABLE_ADMIN login path)"
        assert (
            "CREATE TABLE IF NOT EXISTS public.django_admin_log" in section
        ), "§15c must create public.django_admin_log (admin LogEntry writes)"

    def test_schema_version_bumped_to_v1_2_2(self, schema_sql):
        """The version header must reflect the §15c completion (the
        upgrade ladder in DEPLOYMENT.md §13 keys off it)."""
        assert "Version:    1.2.2" in schema_sql, (
            "the schema header must carry v1.2.2 after the §15c completion"
        )

    def test_v1_2_2_changelog_entry_exists(self, schema_sql):
        assert "v1.2.2 (2026-11-27)" in schema_sql, (
            "the VERSION CHANGELOG must document the v1.2.2 §15c completion"
        )

    def test_admin_optin_tables_are_idempotent(self, schema_sql):
        """The §13 upgrade path re-runs the schema on existing databases —
        every §15c statement must be IF NOT EXISTS."""
        section = _section(
            schema_sql,
            "§15c  DJANGO FRAMEWORK TABLES",
            "§16  MONETARY CAPACITY WIDENING",
        )
        for table in ("django_session", "django_admin_log"):
            assert f"CREATE TABLE IF NOT EXISTS public.{table}" in section

    def test_admin_optin_tables_granted_to_app_role(self, schema_sql):
        """ledgersg_app (the runtime role) needs full CRUD on the session
        table and INSERT/SELECT on the admin log — same posture as the
        rest of §15c."""
        section = _section(
            schema_sql,
            "§15c  DJANGO FRAMEWORK TABLES",
            "§16  MONETARY CAPACITY WIDENING",
        )
        for table in ("public.django_session", "public.django_admin_log"):
            assert table in section, f"{table} must appear in the §15c GRANTs"
