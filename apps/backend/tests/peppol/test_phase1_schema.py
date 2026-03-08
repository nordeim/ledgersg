"""
TDD Tests for Phase 1: Database Schema
Tests SQL schema changes for InvoiceNow foundation.
"""

import pytest
from django.db import connection


@pytest.mark.django_db
def test_peppol_transmission_log_has_xml_payload_hash():
    """Test that xml_payload_hash column exists in peppol_transmission_log."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'gst'
            AND table_name = 'peppol_transmission_log'
            AND column_name = 'xml_payload_hash'
        """)
        result = cursor.fetchone()
        assert result is not None


@pytest.mark.django_db
def test_peppol_transmission_log_has_access_point_provider():
    """Test that access_point_provider column exists."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'gst'
            AND table_name = 'peppol_transmission_log'
            AND column_name = 'access_point_provider'
        """)
        result = cursor.fetchone()
        assert result is not None


@pytest.mark.django_db
def test_peppol_transmission_log_has_mlr_fields():
    """Test that MLR tracking columns exist."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'gst'
            AND table_name = 'peppol_transmission_log'
            AND column_name IN ('mlr_status', 'mlr_received_at')
        """)
        results = cursor.fetchall()
        assert len(results) == 2


@pytest.mark.django_db
def test_peppol_transmission_log_has_iras_submission_id():
    """Test that iras_submission_id column exists for 5th corner."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'gst'
            AND table_name = 'peppol_transmission_log'
            AND column_name = 'iras_submission_id'
        """)
        result = cursor.fetchone()
        assert result is not None


@pytest.mark.django_db
def test_organisation_peppol_settings_table_exists():
    """Test that organisation_peppol_settings table was created."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'gst'
                AND table_name = 'organisation_peppol_settings'
            )
        """)
        result = cursor.fetchone()
        assert result[0] is True


@pytest.mark.django_db
def test_organisation_has_access_point_fields():
    """Test that Organisation has new Peppol fields."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'core'
            AND table_name = 'organisation'
            AND column_name IN (
                'access_point_provider',
                'access_point_api_url',
                'access_point_api_key',
                'access_point_client_id',
                'auto_transmit',
                'transmission_retry_attempts'
            )
        """)
        results = cursor.fetchall()
        assert len(results) == 6
