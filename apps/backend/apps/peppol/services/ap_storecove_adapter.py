"""
Storecove Access Point Adapter for Peppol/InvoiceNow integration.

Implements the APAdapterBase interface for Storecove API integration.
Storecove is an IMDA-accredited Peppol Access Point provider.

API Documentation:
- Base URL: https://api.storecove.com/api/v2
- Authentication: API Key in Authorization header
- Endpoints:
  - POST /document_submissions - Submit invoice
  - GET /document_submissions/{id} - Check status
"""

import requests
from typing import Dict, Any, Optional
from apps.peppol.services.ap_adapter_base import (
    APAdapterBase,
    TransmissionResult,
    TransmissionStatus,
)


class StorecoveAdapter(APAdapterBase):
    """
    Storecove Access Point adapter for Peppol transmission.

    Implements the APAdapterBase interface to integrate with Storecove's
    REST API for sending and tracking Peppol invoices.

    Attributes:
        api_key: Storecove API key for authentication
        client_id: Storecove client identifier
        base_url: Storecove API base URL
        session: requests.Session for HTTP calls

    Example:
        adapter = StorecoveAdapter(
            api_key="your-api-key",
            client_id="your-client-id",
            base_url="https://api.storecove.com"
        )

        # Authenticate
        if adapter.authenticate():
            # Send invoice
            result = adapter.send_invoice(xml_payload, "0195:202312345A")
            if result.success:
                print(f"Message ID: {result.message_id}")
    """

    def __init__(self, api_key: str, client_id: str, base_url: str = "https://api.storecove.com"):
        """
        Initialize Storecove adapter with credentials.

        Args:
            api_key: Storecove API key
            client_id: Storecove client ID
            base_url: Storecove API base URL (defaults to production)
        """
        self.api_key = api_key
        self.client_id = client_id
        self.base_url = base_url.rstrip("/")  # Remove trailing slash
        self.session = requests.Session()

        # Set default headers
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def authenticate(self) -> bool:
        """
        Validate API credentials by making a test request.

        Makes a lightweight GET request to validate the API key
        is valid and the endpoint is reachable.

        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Make a lightweight request to validate credentials
            # Using a health check or status endpoint if available
            response = self.session.get(f"{self.base_url}/api/v2/", timeout=10)

            # 200 or 404 means the API is reachable and auth worked
            # (404 is expected if root endpoint doesn't exist)
            if response.status_code == 200:
                return True
            elif response.status_code == 404:
                # API is reachable, auth likely valid
                return True
            elif response.status_code == 401:
                # Authentication failed
                return False
            else:
                # Other errors - API might be down
                return False

        except requests.exceptions.RequestException:
            # Network errors or timeouts
            return False

    def send_invoice(self, xml_payload: str, peppol_id: str) -> TransmissionResult:
        """
        Send invoice XML to Peppol network via Storecove API.

        Posts the XML invoice to Storecove's document_submissions
        endpoint. The XML should be a valid UBL 2.1 PINT-SG invoice.

        Args:
            xml_payload: Complete UBL 2.1 XML invoice as string
            peppol_id: Recipient's Peppol participant ID (e.g., "0195:202312345A")

        Returns:
            TransmissionResult with status and message_id

        Raises:
            No exceptions raised - all errors returned in TransmissionResult
        """
        try:
            # Prepare Storecove API payload
            payload = self._prepare_payload(xml_payload, peppol_id)

            # Send to Storecove
            response = self.session.post(
                f"{self.base_url}/api/v2/document_submissions", json=payload, timeout=30
            )

            # Parse response
            return self._parse_send_response(response)

        except requests.exceptions.Timeout:
            return TransmissionResult.failure(
                error_code="TIMEOUT",
                error_message="Request timed out after 30 seconds",
                status=TransmissionStatus.FAILED,
            )
        except requests.exceptions.RequestException as e:
            return TransmissionResult.failure(
                error_code="NETWORK_ERROR",
                error_message=f"Network error: {str(e)}",
                status=TransmissionStatus.FAILED,
            )

    def check_status(self, message_id: str) -> TransmissionResult:
        """
        Check transmission status for a previously sent message.

        Polls the Storecove API to get the current status of a
        document submission.

        Args:
            message_id: The Peppol message ID returned by send_invoice()

        Returns:
            TransmissionResult with current status
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/v2/document_submissions/{message_id}", timeout=10
            )

            return self._parse_status_response(response, message_id)

        except requests.exceptions.Timeout:
            return TransmissionResult.failure(
                error_code="TIMEOUT",
                error_message="Status check timed out",
                status=TransmissionStatus.FAILED,
            )
        except requests.exceptions.RequestException as e:
            return TransmissionResult.failure(
                error_code="NETWORK_ERROR",
                error_message=f"Network error checking status: {str(e)}",
                status=TransmissionStatus.FAILED,
            )

    def validate_connection(self) -> bool:
        """
        Validate API connectivity and configuration.

        Makes a lightweight request to verify the Storecove API
        endpoint is reachable and responding.

        Returns:
            True if API is reachable and responding, False otherwise
        """
        try:
            response = self.session.get(f"{self.base_url}/api/v2/", timeout=5)

            # Consider 2xx or 404 as success (API is reachable)
            return response.status_code < 500

        except requests.exceptions.RequestException:
            return False

    def _prepare_payload(self, xml_payload: str, peppol_id: str) -> Dict[str, Any]:
        """
        Prepare Storecove API payload.

        Formats the XML payload according to Storecove API specification.
        Storecove accepts JSON with embedded XML.

        Args:
            xml_payload: UBL 2.1 XML invoice
            peppol_id: Recipient Peppol participant ID

        Returns:
            Dictionary ready for JSON serialization
        """
        return {
            "document": {
                "type": "Invoice",
                "format": "UBL",
                "content": xml_payload,
                "encoding": "UTF-8",
            },
            "recipient": {
                "scheme": "0195",  # Peppol party ID scheme
                "id": peppol_id.replace("0195:", "")
                if peppol_id.startswith("0195:")
                else peppol_id,
            },
            "sender": {"client_id": self.client_id},
        }

    def _parse_send_response(self, response: requests.Response) -> TransmissionResult:
        """
        Parse Storecove API response for document submission.

        Args:
            response: requests.Response from POST /document_submissions

        Returns:
            TransmissionResult with parsed status
        """
        try:
            data = response.json()
        except ValueError:
            data = {}

        if response.status_code == 201:
            # Success - document accepted
            message_id = data.get("id") or data.get("message_id")
            return TransmissionResult.success(message_id=message_id, raw_response=data)
        elif response.status_code == 400:
            # Bad request - validation error
            error_msg = data.get("message", "Invalid request")
            return TransmissionResult.failure(
                error_code="VALIDATION_ERROR",
                error_message=error_msg,
                status=TransmissionStatus.FAILED,
                raw_response=data,
            )
        elif response.status_code == 401:
            # Authentication error
            return TransmissionResult.failure(
                error_code="AUTH_ERROR",
                error_message="Authentication failed - invalid API key",
                status=TransmissionStatus.FAILED,
                raw_response=data,
            )
        elif response.status_code == 422:
            # Unprocessable - Peppol validation error
            error_msg = data.get("message", "Peppol validation failed")
            return TransmissionResult.failure(
                error_code="PEPPOL_VALIDATION_ERROR",
                error_message=error_msg,
                status=TransmissionStatus.REJECTED,
                raw_response=data,
            )
        elif response.status_code == 429:
            # Rate limited
            return TransmissionResult.failure(
                error_code="RATE_LIMITED",
                error_message="Rate limit exceeded - retry later",
                status=TransmissionStatus.FAILED,
                raw_response=data,
            )
        else:
            # Server error or other
            return TransmissionResult.failure(
                error_code=f"HTTP_{response.status_code}",
                error_message=f"API error: {response.status_code}",
                status=TransmissionStatus.FAILED,
                raw_response=data,
            )

    def _parse_status_response(
        self, response: requests.Response, message_id: str
    ) -> TransmissionResult:
        """
        Parse Storecove status check response.

        Args:
            response: requests.Response from GET /document_submissions/{id}
            message_id: The message ID being checked

        Returns:
            TransmissionResult with current status
        """
        try:
            data = response.json()
        except ValueError:
            data = {}

        if response.status_code == 200:
            status = data.get("status", "").lower()

            if status == "delivered":
                return TransmissionResult.success(message_id=message_id, raw_response=data)
            elif status in ["failed", "rejected"]:
                return TransmissionResult.failure(
                    error_code="DELIVERY_FAILED",
                    error_message=data.get("error_message", "Delivery failed"),
                    status=TransmissionStatus.REJECTED,
                    raw_response=data,
                )
            else:
                # Still processing (pending, transmitting, etc.)
                return TransmissionResult(
                    success=False,
                    message_id=message_id,
                    status=TransmissionStatus.TRANSMITTING,
                    raw_response=data,
                )
        elif response.status_code == 404:
            return TransmissionResult.failure(
                error_code="NOT_FOUND",
                error_message=f"Message {message_id} not found",
                status=TransmissionStatus.FAILED,
                raw_response=data,
            )
        else:
            return TransmissionResult.failure(
                error_code=f"HTTP_{response.status_code}",
                error_message=f"Status check failed: {response.status_code}",
                status=TransmissionStatus.FAILED,
                raw_response=data,
            )
