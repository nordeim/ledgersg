"""
TDD Tests for Phase 3: Access Point Adapter Base

Tests the abstract base class interface for AP providers.
"""

import pytest
from abc import ABC
from typing import Dict, Any


class TestAPAdapterBase:
    """Tests for APAdapterBase abstract class."""

    def test_adapter_base_is_abstract(self):
        """Test that APAdapterBase cannot be instantiated directly."""
        # Import will fail initially - that's expected in RED phase
        from apps.peppol.services.ap_adapter_base import APAdapterBase

        # Should raise TypeError when trying to instantiate abstract class
        with pytest.raises(TypeError):
            APAdapterBase()

    def test_adapter_base_requires_authenticate(self):
        """Test that concrete class must implement authenticate method."""
        from apps.peppol.services.ap_adapter_base import APAdapterBase

        # Create a concrete class that doesn't implement authenticate
        class IncompleteAdapter(APAdapterBase):
            def send_invoice(self, xml_payload: str, peppol_id: str):
                pass

            def check_status(self, message_id: str):
                pass

            def validate_connection(self) -> bool:
                pass

        # Should raise TypeError when trying to instantiate
        with pytest.raises(TypeError) as exc_info:
            IncompleteAdapter()

        assert "authenticate" in str(exc_info.value)

    def test_adapter_base_requires_send_invoice(self):
        """Test that concrete class must implement send_invoice method."""
        from apps.peppol.services.ap_adapter_base import APAdapterBase

        class IncompleteAdapter(APAdapterBase):
            def authenticate(self) -> bool:
                pass

            def check_status(self, message_id: str):
                pass

            def validate_connection(self) -> bool:
                pass

        with pytest.raises(TypeError) as exc_info:
            IncompleteAdapter()

        assert "send_invoice" in str(exc_info.value)

    def test_adapter_base_requires_check_status(self):
        """Test that concrete class must implement check_status method."""
        from apps.peppol.services.ap_adapter_base import APAdapterBase

        class IncompleteAdapter(APAdapterBase):
            def authenticate(self) -> bool:
                pass

            def send_invoice(self, xml_payload: str, peppol_id: str):
                pass

            def validate_connection(self) -> bool:
                pass

        with pytest.raises(TypeError) as exc_info:
            IncompleteAdapter()

        assert "check_status" in str(exc_info.value)

    def test_adapter_base_requires_validate_connection(self):
        """Test that concrete class must implement validate_connection method."""
        from apps.peppol.services.ap_adapter_base import APAdapterBase

        class IncompleteAdapter(APAdapterBase):
            def authenticate(self) -> bool:
                pass

            def send_invoice(self, xml_payload: str, peppol_id: str):
                pass

            def check_status(self, message_id: str):
                pass

        with pytest.raises(TypeError) as exc_info:
            IncompleteAdapter()

        assert "validate_connection" in str(exc_info.value)


class TestTransmissionResult:
    """Tests for TransmissionResult dataclass."""

    def test_transmission_result_dataclass_exists(self):
        """Test that TransmissionResult dataclass can be imported."""
        from apps.peppol.services.ap_adapter_base import TransmissionResult

        assert TransmissionResult is not None

    def test_transmission_result_has_required_fields(self):
        """Test TransmissionResult has all required fields."""
        from apps.peppol.services.ap_adapter_base import TransmissionResult, TransmissionStatus

        result = TransmissionResult(
            success=True,
            message_id="msg-123",
            status=TransmissionStatus.DELIVERED,
            error_code=None,
            error_message=None,
            raw_response={"status": "ok"},
        )

        assert result.success is True
        assert result.message_id == "msg-123"
        assert result.status == TransmissionStatus.DELIVERED
        assert result.error_code is None
        assert result.error_message is None
        assert result.raw_response == {"status": "ok"}

    def test_transmission_result_success_factory(self):
        """Test TransmissionResult can be created for success case."""
        from apps.peppol.services.ap_adapter_base import TransmissionResult, TransmissionStatus

        result = TransmissionResult.success(
            message_id="msg-456", raw_response={"id": "msg-456", "status": "delivered"}
        )

        assert result.success is True
        assert result.message_id == "msg-456"
        assert result.status == TransmissionStatus.DELIVERED
        assert result.error_code is None
        assert result.error_message is None

    def test_transmission_result_failure_factory(self):
        """Test TransmissionResult can be created for failure case."""
        from apps.peppol.services.ap_adapter_base import TransmissionResult, TransmissionStatus

        result = TransmissionResult.failure(
            error_code="AUTH_ERROR",
            error_message="Invalid API key",
            raw_response={"error": "authentication_failed"},
        )

        assert result.success is False
        assert result.message_id is None
        assert result.status == TransmissionStatus.FAILED
        assert result.error_code == "AUTH_ERROR"
        assert result.error_message == "Invalid API key"


class TestTransmissionStatus:
    """Tests for TransmissionStatus enum."""

    def test_transmission_status_enum_exists(self):
        """Test that TransmissionStatus enum can be imported."""
        from apps.peppol.services.ap_adapter_base import TransmissionStatus

        assert TransmissionStatus is not None

    def test_transmission_status_has_all_values(self):
        """Test TransmissionStatus has all required values."""
        from apps.peppol.services.ap_adapter_base import TransmissionStatus

        assert TransmissionStatus.PENDING.value == "PENDING"
        assert TransmissionStatus.TRANSMITTING.value == "TRANSMITTING"
        assert TransmissionStatus.DELIVERED.value == "DELIVERED"
        assert TransmissionStatus.FAILED.value == "FAILED"
        assert TransmissionStatus.REJECTED.value == "REJECTED"
