"""
Celery Tasks for InvoiceNow/Peppol async transmission.

Provides async task execution for Peppol invoice transmission,
enabling non-blocking approval workflows and retry logic.
"""

import logging
from datetime import datetime
from celery import shared_task
from typing import Optional

# Configure module logger
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def transmit_peppol_invoice_task(self, transmission_log_id: str, org_id: str) -> dict:
    """
    Async task to transmit invoice via Peppol.

    Called when an invoice is approved and auto-transmit is enabled.
    Executes the transmission workflow asynchronously with retry support.

    Args:
        transmission_log_id: UUID of the transmission log entry
        org_id: UUID of the organization

    Returns:
        Dict with transmission result:
        {
            "success": bool,
            "message_id": str or None,
            "status": str,
            "error": str or None
        }

    Raises:
        self.retry: On retryable errors (network, timeout, rate limit)

    Example:
        # Queue for async execution
        task = transmit_peppol_invoice_task.delay(
            "550e8400-e29b-41d4-a716-446655440000",
            "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        )

        # Get result
        result = task.get(timeout=30)
    """
    from apps.peppol.services.transmission_service import TransmissionService

    logger.info(
        f"Starting Peppol transmission task for log {transmission_log_id}, "
        f"attempt {self.request.retries + 1}"
    )

    try:
        # Execute transmission against the pre-created log (P5/C-2: the old
        # call passed the LOG id to transmit_invoice(), which expects an
        # INVOICE id — the auto-transmit path could never succeed).
        service = TransmissionService()
        log = service.execute_transmission_for_log(transmission_log_id)

        # Prepare result
        result = {
            "success": log.status == "DELIVERED",
            "message_id": str(log.peppol_message_id) if log.peppol_message_id else None,
            "status": log.status,
            "error": log.error_message if log.status == "FAILED" else None,
        }

        if log.status == "DELIVERED":
            logger.info(f"Peppol transmission successful: message_id={log.peppol_message_id}")
        elif log.status == "FAILED":
            logger.error(f"Peppol transmission failed: {log.error_code} - {log.error_message}")

            # Determine if retryable
            retryable_errors = ["TIMEOUT", "NETWORK_ERROR", "RATE_LIMITED"]
            if log.error_code in retryable_errors and self.request.retries < self.max_retries:
                countdown = 60 * (2**self.request.retries)  # Exponential backoff
                logger.info(f"Retrying transmission in {countdown} seconds")
                raise self.retry(countdown=countdown)

        return result

    except Exception as exc:
        logger.exception(f"Peppol transmission task failed: {exc}")

        # Retry on exception
        if self.request.retries < self.max_retries:
            countdown = 60 * (2**self.request.retries)
            logger.info(f"Retrying due to exception in {countdown} seconds")
            raise self.retry(exc=exc, countdown=countdown)

        # Max retries exceeded
        return {"success": False, "message_id": None, "status": "FAILED", "error": str(exc)}


@shared_task(bind=True, max_retries=3)
def retry_failed_transmission_task(self, transmission_log_id: str) -> dict:
    """
    Async task to retry a failed Peppol transmission.

    Manually triggered for failed transmissions. Increments attempt
    counter and re-executes the transmission workflow.

    Args:
        transmission_log_id: UUID of the failed transmission log

    Returns:
        Dict with retry result

    Raises:
        self.retry: On retryable errors
        ValueError: If max retries exceeded

    Example:
        # Retry a failed transmission
        task = retry_failed_transmission_task.delay(
            "550e8400-e29b-41d4-a716-446655440000"
        )
    """
    from apps.peppol.services.transmission_service import TransmissionService

    logger.info(
        f"Retrying Peppol transmission {transmission_log_id}, attempt {self.request.retries + 1}"
    )

    try:
        service = TransmissionService()
        log = service.retry_transmission(transmission_log_id)

        result = {
            "success": log.status == "DELIVERED",
            "message_id": str(log.peppol_message_id) if log.peppol_message_id else None,
            "status": log.status,
            "attempt_number": log.attempt_number,
            "error": log.error_message if log.status == "FAILED" else None,
        }

        if log.status == "DELIVERED":
            logger.info(f"Retry successful: message_id={log.peppol_message_id}")
        elif log.status == "FAILED":
            logger.error(f"Retry failed: {log.error_message}")

            # Retry if applicable
            retryable_errors = ["TIMEOUT", "NETWORK_ERROR", "RATE_LIMITED"]
            if log.error_code in retryable_errors and self.request.retries < self.max_retries:
                countdown = 60 * (2**self.request.retries)
                raise self.retry(countdown=countdown)

        return result

    except ValueError as e:
        # Non-retryable error (max retries exceeded)
        logger.error(f"Retry not possible: {e}")
        return {"success": False, "message_id": None, "status": "FAILED", "error": str(e)}

    except Exception as exc:
        logger.exception(f"Retry task failed: {exc}")

        if self.request.retries < self.max_retries:
            countdown = 60 * (2**self.request.retries)
            raise self.retry(exc=exc, countdown=countdown)

        return {"success": False, "message_id": None, "status": "FAILED", "error": str(exc)}


@shared_task
def check_transmission_status_task(message_id: str) -> Optional[dict]:
    """
    Check status of an in-flight Peppol transmission.

    Polls the Access Point for the current status of a message and updates
    the matching PeppolTransmissionLog with the result. Used for status
    monitoring and notifications.

    Args:
        message_id: Peppol message ID from transmission

    Returns:
        Dict with status information or None if no log matches the message id:
        {
            "message_id": str,
            "status": str,
            "delivered_at": str or None,
            "error": str or None
        }

    Example:
        # Check status
        result = check_transmission_status_task.delay("msg-abc-123").get()
    """
    from apps.peppol.models import PeppolTransmissionLog
    from apps.peppol.services.transmission_service import TransmissionService

    logger.info(f"Checking status for Peppol message {message_id}")

    log = (
        PeppolTransmissionLog.objects.filter(peppol_message_id=message_id)
        .order_by("-response_at", "-transmitted_at", "-id")
        .first()
    )
    if log is None:
        logger.warning(f"No transmission log found for message {message_id}")
        return None

    try:
        service = TransmissionService()
        adapter = service.get_adapter_for_org(str(log.org_id))
        result = adapter.check_status(message_id)
    except Exception as exc:
        logger.exception(f"Status check for message {message_id} failed: {exc}")
        return {
            "message_id": message_id,
            "status": log.status,
            "delivered_at": None,
            "error": str(exc),
        }

    if result.success:
        log.status = "DELIVERED"
        log.error_code = ""
        log.error_message = ""
    else:
        log.status = result.status.value
        log.error_code = result.error_code or ""
        log.error_message = result.error_message or ""
    log.response_at = datetime.now()
    log.save()

    return {
        "message_id": message_id,
        "status": log.status,
        "delivered_at": log.response_at.isoformat() if log.response_at else None,
        "error": log.error_message or None,
    }


@shared_task
def cleanup_old_transmission_logs_task(days: int = 90) -> int:
    """
    Clean up stale in-flight transmission logs.

    Retention-safe cleanup (P5/C-2): DELIVERED and REJECTED logs are the
    delivery evidence for IRAS's 5-year record-retention requirement
    (database_schema.sql: "IRAS requires 5-year record retention") and are
    NEVER deleted here. Only non-final logs (PENDING / TRANSMITTING /
    FAILED) older than the horizon are removed — stale in-flight rows with
    no audit value that would otherwise accumulate forever.

    Args:
        days: Age (in days) beyond which stale non-final logs are removed
            (default: 90)

    Returns:
        Number of stale logs deleted

    Example:
        # Cleanup stale in-flight logs older than 90 days
        deleted_count = cleanup_old_transmission_logs_task.delay(90).get()
    """
    from datetime import datetime, timedelta
    from apps.peppol.models import PeppolTransmissionLog

    cutoff_date = datetime.now() - timedelta(days=days)

    stale_logs = PeppolTransmissionLog.objects.filter(
        transmitted_at__lt=cutoff_date,
        status__in=["PENDING", "TRANSMITTING", "FAILED"],
    )

    count = stale_logs.count()
    stale_logs.delete()

    logger.info(f"Cleaned up {count} stale non-final transmission logs")

    return count
