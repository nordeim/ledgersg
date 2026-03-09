"""
Abstract Base Class for Access Point Adapters.

Provides the interface that all AP providers (Storecove, etc.) must implement
for Peppol/InvoiceNow transmission.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from enum import Enum


class TransmissionStatus(Enum):
    """
    Transmission status values for Peppol messages.

    These map to the status values stored in PeppolTransmissionLog.
    """

    PENDING = "PENDING"
    TRANSMITTING = "TRANSMITTING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


@dataclass
class TransmissionResult:
    """
    Result of a transmission attempt.

    Provides standardized response format across all AP providers.

    Attributes:
        success: Whether the transmission was successful
        message_id: Peppol message ID from AP (None if failed)
        status: Current transmission status
        error_code: Error code from AP or validation (None if success)
        error_message: Detailed error message (None if success)
        raw_response: Raw API response data for debugging
    """

    success: bool
    message_id: Optional[str] = None
    status: TransmissionStatus = field(default=TransmissionStatus.PENDING)
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None

    @classmethod
    def success(
        cls, message_id: str, raw_response: Optional[Dict[str, Any]] = None
    ) -> "TransmissionResult":
        """
        Factory method for successful transmission results.

        Args:
            message_id: The Peppol message ID from AP
            raw_response: Raw API response data

        Returns:
            TransmissionResult with success=True, status=DELIVERED
        """
        return cls(
            success=True,
            message_id=message_id,
            status=TransmissionStatus.DELIVERED,
            error_code=None,
            error_message=None,
            raw_response=raw_response,
        )

    @classmethod
    def failure(
        cls,
        error_code: str,
        error_message: str,
        status: TransmissionStatus = TransmissionStatus.FAILED,
        raw_response: Optional[Dict[str, Any]] = None,
    ) -> "TransmissionResult":
        """
        Factory method for failed transmission results.

        Args:
            error_code: Error code from AP or validation
            error_message: Detailed error message
            status: Transmission status (FAILED or REJECTED)
            raw_response: Raw API response data

        Returns:
            TransmissionResult with success=False
        """
        return cls(
            success=False,
            message_id=None,
            status=status,
            error_code=error_code,
            error_message=error_message,
            raw_response=raw_response,
        )


class APAdapterBase(ABC):
    """
    Abstract base class for Access Point adapters.

    All AP providers (Storecove, etc.) must inherit from this class
    and implement all abstract methods.

    Usage:
        class StorecoveAdapter(APAdapterBase):
            def authenticate(self) -> bool:
                # Implementation...
                pass

            def send_invoice(self, xml_payload: str, peppol_id: str) -> TransmissionResult:
                # Implementation...
                pass

            def check_status(self, message_id: str) -> TransmissionResult:
                # Implementation...
                pass

            def validate_connection(self) -> bool:
                # Implementation...
                pass
    """

    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the AP provider.

        Validates API credentials by making a lightweight test request
        to the AP provider's authentication endpoint.

        Returns:
            True if authentication successful, False otherwise
        """
        pass

    @abstractmethod
    def send_invoice(self, xml_payload: str, peppol_id: str) -> TransmissionResult:
        """
        Send invoice XML to Peppol network via AP provider.

        This is the main method for transmitting invoices. The adapter
        handles the API-specific payload formatting and response parsing.

        Args:
            xml_payload: Complete UBL 2.1 XML invoice as string
            peppol_id: Recipient's Peppol participant ID

        Returns:
            TransmissionResult with status and message_id (if successful)
        """
        pass

    @abstractmethod
    def check_status(self, message_id: str) -> TransmissionResult:
        """
        Check transmission status for a previously sent message.

        Used to poll for delivery status or handle async callbacks.

        Args:
            message_id: The Peppol message ID returned by send_invoice()

        Returns:
            TransmissionResult with current status
        """
        pass

    @abstractmethod
    def validate_connection(self) -> bool:
        """
        Validate API connectivity and configuration.

        Makes a lightweight request to verify the AP endpoint is
        reachable and responding correctly.

        Returns:
            True if API is reachable and responding, False otherwise
        """
        pass
