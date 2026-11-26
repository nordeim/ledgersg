"""
Asynchronous tasks for Invoicing module.
"""

import logging
from uuid import UUID
from celery import shared_task

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

from apps.core.models import Organisation, InvoiceDocument
from apps.invoicing.services import DocumentService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_invoice_email_task(
    self, org_id: str, document_id: str, recipients: list, cc: list | None = None, bcc: list | None = None
):
    """
    Background task to generate PDF and send invoice via email.

    P8/G-6: cc/bcc travel with the send contract — they were validated by
    the API since P7 but silently dropped here.

    P17/BE-H3: a Celery worker has no middleware — every tenant-table
    SELECT policy is `org_id = core.current_org_id()` and the GUC is NULL
    on a worker, so without opening the tenant context here the task
    sees zero rows and retries to death while the API already answered
    `{"sent": true}` (dev/test never see it: eager mode runs inside the
    request transaction where the middleware set the GUC).
    """
    from common.tenant_context import tenant_context

    try:
        with tenant_context(org_id):
            return _send_invoice_email(org_id, document_id, recipients, cc, bcc)
    except Exception as exc:
        logger.error(f"Error sending invoice email {document_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)


def _send_invoice_email(org_id, document_id, recipients, cc=None, bcc=None):
    """The send itself, executed under the org's RLS context."""
    org = Organisation.objects.get(id=org_id)
    document = InvoiceDocument.objects.get(id=document_id, org_id=org_id)
    contact = document.contact

    context = {
        "org_name": org.name,
        "contact_name": contact.name,
        "document_number": document.document_number,
        "total_amount": document.total_incl,
        "currency": org.base_currency,
        "due_date": document.due_date,
    }

    subject = f"Invoice {document.document_number} from {org.name}"
    text_content = render_to_string("invoicing/email/invoice_email.txt", context)
    html_content = render_to_string("invoicing/email/invoice_email.html", context)

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
        cc=cc or [],
        bcc=bcc or [],
    )
    email.attach_alternative(html_content, "text/html")

    # Attach PDF
    pdf_stream = DocumentService.generate_pdf(UUID(org_id), UUID(document_id))
    email.attach(
        f"{document.document_number}.pdf",
        pdf_stream.getvalue(),
        "application/pdf"
    )

    email.send()
    logger.info(f"Successfully sent invoice {document_id} to {recipients}")

    return {"status": "sent", "document_id": document_id}
