import logging

from django.conf import settings
from django.core.mail import EmailMessage


logger = logging.getLogger(__name__)


def send_contact_notification(contact_message):
    recipient = getattr(settings, "CONTACT_NOTIFICATION_EMAIL", "")
    if not recipient:
        return False

    email = EmailMessage(
        subject="Nova mensagem de contato do Axis",
        body=(
            f"Remetente: {contact_message.email}\n"
            f"Data: {contact_message.created_at:%d/%m/%Y %H:%M}\n\n"
            f"{contact_message.message}"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
        reply_to=[contact_message.email],
    )
    email.send(fail_silently=False)
    return True


def notify_contact_safely(contact_message):
    try:
        return send_contact_notification(contact_message)
    except Exception:
        logger.exception(
            "Failed to send notification for contact message %s.",
            contact_message.id,
        )
        return False
