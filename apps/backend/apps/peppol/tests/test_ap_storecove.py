"""
TDD Tests for Phase 3: Storecove Adapter

Tests the Storecove Access Point adapter implementation.
Uses unittest.mock to mock HTTP requests.
"""

import pytest
from unittest.mock import Mock, patch


class TestStorecoveAdapter:
    """Tests for StorecoveAdapter class."""

    def test_storecove_adapter_inherits_base(self):
        """Test that StorecoveAdapter inherits from APAdapterBase."""
        from apps.peppol.services.ap_storecove_adapter import StorecoveAdapter
        from apps.peppol.services.ap_adapter_base import APAdapterBase

        assert issubclass(StorecoveAdapter, APAdapterBase)

    def test_storecove_adapter_init(self):
        """Test StorecoveAdapter initialization with credentials."""
        from apps.peppol.services.ap_storecove_adapter import StorecoveAdapter

        adapter = StorecoveAdapter(
            api_key="test-api-key", client_id="test-client-id", base_url="https://api.storecove.com"
        )

        assert adapter.api_key == "test-api-key"
        assert adapter.client_id == "test-client-id"
        assert adapter.base_url == "https://api.storecove.com"

    @patch("apps.peppol.services.ap_storecove_adapter.requests.Session")
    def test_storecove_authenticate_success(self, mock_session_class):
        """Test successful authentication with Storecove API."""
        from apps.peppol.services.ap_storecove_adapter import StorecoveAdapter

        # Mock successful response
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        adapter = StorecoveAdapter(
            api_key="valid-key", client_id="client-123", base_url="https://api.storecove.com"
        )

        result = adapter.authenticate()

        assert result is True

    @patch("apps.peppol.services.ap_storecove_adapter.requests.Session")
    def test_storecove_authenticate_failure(self, mock_session_class):
        """Test authentication failure with invalid credentials."""
        from apps.peppol.services.ap_storecove_adapter import StorecoveAdapter

        # Mock 401 response
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 401
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        adapter = StorecoveAdapter(
            api_key="invalid-key", client_id="client-123", base_url="https://api.storecove.com"
        )

        result = adapter.authenticate()

        assert result is False

    @patch("apps.peppol.services.ap_storecove_adapter.requests.Session")
    def test_storecove_send_invoice_success(self, mock_session_class):
        """Test successful invoice transmission."""
        from apps.peppol.services.ap_storecove_adapter import StorecoveAdapter
        from apps.peppol.services.ap_adapter_base import TransmissionStatus

        # Mock successful response
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "msg-abc-123",
            "status": "accepted",
            "tracking_id": "track-456",
        }
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        adapter = StorecoveAdapter(
            api_key="valid-key", client_id="client-123", base_url="https://api.storecove.com"
        )

        xml_payload = '<?xml version="1.0"?><Invoice>...</Invoice>'
        peppol_id = "0195:202312345A"

        result = adapter.send_invoice(xml_payload, peppol_id)

        assert result.success is True
        assert result.message_id == "msg-abc-123"
        assert result.status == TransmissionStatus.DELIVERED
        assert result.error_code is None

    @patch("apps.peppol.services.ap_storecove_adapter.requests.Session")
    def test_storecove_send_invoice_failure(self, mock_session_class):
        """Test failed invoice transmission."""
        from apps.peppol.services.ap_storecove_adapter import StorecoveAdapter
        from apps.peppol.services.ap_adapter_base import TransmissionStatus

        # Mock error response
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "validation_failed",
            "message": "Invalid XML format",
        }
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        adapter = StorecoveAdapter(
            api_key="valid-key", client_id="client-123", base_url="https://api.storecove.com"
        )

        xml_payload = '<?xml version="1.0"?><Invoice>...</Invoice>'
        peppol_id = "0195:202312345A"

        result = adapter.send_invoice(xml_payload, peppol_id)

        assert result.success is False
        assert result.message_id is None
        assert result.status == TransmissionStatus.FAILED
        assert result.error_code == "VALIDATION_ERROR"

    @patch("apps.peppol.services.ap_storecove_adapter.requests.Session")
    def test_storecove_check_status_delivered(self, mock_session_class):
        """Test status check for delivered message."""
        from apps.peppol.services.ap_storecove_adapter import StorecoveAdapter
        from apps.peppol.services.ap_adapter_base import TransmissionStatus

        # Mock delivered response
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "msg-abc-123",
            "status": "delivered",
            "delivered_at": "2026-03-09T10:00:00Z",
        }
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        adapter = StorecoveAdapter(
            api_key="valid-key", client_id="client-123", base_url="https://api.storecove.com"
        )

        result = adapter.check_status("msg-abc-123")

        assert result.success is True
        assert result.status == TransmissionStatus.DELIVERED

    @patch("apps.peppol.services.ap_storecove_adapter.requests.Session")
    def test_storecove_validate_connection(self, mock_session_class):
        """Test connection validation."""
        from apps.peppol.services.ap_storecove_adapter import StorecoveAdapter

        # Mock successful ping
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        adapter = StorecoveAdapter(
            api_key="valid-key", client_id="client-123", base_url="https://api.storecove.com"
        )

        result = adapter.validate_connection()

        assert result is True
