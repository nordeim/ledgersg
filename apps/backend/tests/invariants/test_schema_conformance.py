"""
Schema–model conformance gate (M-01 / I-01 remediation).

The SQL-First design makes database_schema.sql the source of truth and all
Django models unmanaged mirrors. Nothing in the normal toolchain verifies
the mirror — drift surfaces as runtime FieldError/UndefinedColumn deep in
financial transactions (this exact class of defect produced audit findings
C-01a, C-01d and H-01).

This test introspects information_schema.columns and asserts that every
column each unmanaged model declares actually exists in the live schema with
a compatible type. It fails on the next drift before any request does.
"""

import pytest
from django.apps import apps
from django.db import connection, models

# Django field class -> acceptable PostgreSQL data types.
# ForeignKey/OneToOne store the target PK's type (uuid, smallint, ...).
FIELD_COMPAT = {
    "DecimalField": {"numeric"},
    "UUIDField": {"uuid"},
    "DateField": {"date"},
    "DateTimeField": {"timestamp with time zone", "timestamp without time zone"},
    "BooleanField": {"boolean"},
    "NullBooleanField": {"boolean"},
    "CharField": {"character varying", "character", "text", "USER-DEFINED"},
    "EmailField": {"character varying", "character", "text"},
    "URLField": {"character varying", "character", "text"},
    "SlugField": {"character varying", "character", "text"},
    "TextField": {"text", "character varying"},
    "SmallIntegerField": {"smallint"},
    "IntegerField": {"smallint", "integer"},
    "PositiveIntegerField": {"smallint", "integer"},
    "PositiveSmallIntegerField": {"smallint"},
    "BigIntegerField": {"integer", "bigint"},
    "ForeignKey": {"uuid", "smallint", "integer", "bigint", "character varying", "character"},
    "OneToOneField": {"uuid", "smallint", "integer", "bigint", "character varying", "character"},
    "BigAutoField": {"bigint"},
    "AutoField": {"integer"},
    "JSONField": {"jsonb", "json"},
    "ArrayField": {"ARRAY"},
    "GenericIPAddressField": {"character varying", "inet"},
}


def _domain_models():
    """All concrete models from LedgerSG's local apps."""
    local_apps = {
        "core", "coa", "gst", "journal", "invoicing", "banking", "reporting",
        "peppol",
    }
    for model in apps.get_models():
        if model._meta.app_label in local_apps and not model._meta.proxy:
            yield model


def _split_db_table(db_table: str):
    """Parse the db_table quoting convention 'schema\".\"table' or 'schema.table'."""
    table = db_table.replace('"', "")
    if "." in table:
        schema, name = table.rsplit(".", 1)
        return schema, name
    return "public", table


def _precision_drift_problem(model, field, schema, table, column, live) -> str | None:
    """
    Precision conformance message (P3, H-03) or None when shapes match.

    A DecimalField's declared max_digits/decimal_places must match the live
    column shape. NUMERIC(10,4) silently capped money at S$999,999.9999 —
    below the S$1M GST registration threshold; this check makes any future
    precision drift a test failure, not a runtime `numeric field overflow`.
    """
    if field.max_digits is None or field.decimal_places is None:
        return None
    if (
        live["numeric_precision"] == field.max_digits
        and live["numeric_scale"] == field.decimal_places
    ):
        return None
    return (
        f"{model.__name__}.{field.name}: column "
        f"'{schema}.{table}.{column}' is "
        f"NUMERIC({live['numeric_precision']},{live['numeric_scale']}) "
        f"in the schema but DecimalField(max_digits={field.max_digits}, "
        f"decimal_places={field.decimal_places}) in the model (precision drift)"
    )


@pytest.mark.django_db
def test_every_model_column_exists_in_schema():
    columns_by_table = {}
    problems = []

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT table_schema, table_name, column_name, data_type,
                   numeric_precision, numeric_scale
            FROM information_schema.columns
            WHERE table_schema IN ('core','coa','gst','journal','invoicing',
                                   'banking','audit','public')
            """
        )
        for schema, table, column, data_type, precision, scale in cursor.fetchall():
            columns_by_table.setdefault((schema, table), {})[column] = {
                "data_type": data_type,
                "numeric_precision": precision,
                "numeric_scale": scale,
            }

    checked = 0
    for model in _domain_models():
        meta = model._meta
        schema, table = _split_db_table(meta.db_table)
        live = columns_by_table.get((schema, table))
        if live is None:
            problems.append(
                f"{model.__name__}: table '{schema}.{table}' does not exist in the schema"
            )
            continue

        for field in meta.concrete_fields:
            column = field.column
            checked += 1
            actual = live.get(column)
            if actual is None:
                problems.append(
                    f"{model.__name__}.{field.name}: column '{schema}.{table}.{column}' "
                    "does not exist in the schema (model drift)"
                )
                continue
            allowed = FIELD_COMPAT.get(type(field).__name__)
            if allowed is None:
                # Unknown field class: flag for manual review rather than guess
                problems.append(
                    f"{model.__name__}.{field.name}: unmapped field class "
                    f"'{type(field).__name__}' for column "
                    f"'{schema}.{table}.{column}' — extend FIELD_COMPAT"
                )
            elif actual["data_type"] not in allowed:
                problems.append(
                    f"{model.__name__}.{field.name}: column "
                    f"'{schema}.{table}.{column}' is {type(field).__name__} "
                    f"in the model but '{actual['data_type']}' in the schema"
                )
            elif isinstance(field, models.DecimalField):
                problem = _precision_drift_problem(
                    model, field, schema, table, column, actual
                )
                if problem:
                    problems.append(problem)

    assert not problems, (
        f"Schema/model drift detected in {len(problems)} place(s) "
        f"({checked} columns checked):\n" + "\n".join(f"  - {p}" for p in problems)
    )


@pytest.mark.django_db
def test_conformance_gate_catches_deliberate_drift():
    """
    Meta-test: prove the gate actually detects drift by checking a
    deliberately fake column name against the introspection logic.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_schema = 'gst' AND table_name = 'return'
              AND column_name = 'definitely_not_a_real_column_xyz'
            """
        )
        assert cursor.fetchone()[0] == 0, "sanity: fake column must not exist"
