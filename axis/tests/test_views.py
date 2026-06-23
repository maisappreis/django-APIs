from unittest.mock import patch

from django.urls import reverse
from django.core import mail
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from axis.models import ContactMessage


class ContactAPIViewTest(APITestCase):
    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="Axis <sender@gmail.com>",
        CONTACT_NOTIFICATION_EMAIL="owner@gmail.com",
    )
    def test_contact_endpoint_creates_axis_message(self):
        response = self.client.post(
            reverse("axis-contact"),
            {
                "email": "client@example.com",
                "message": "Gostaria de receber mais informacoes sobre o Axis.",
                "source": "ignored",
            },
            format="json",
        )

        contact_message = ContactMessage.objects.get()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["detail"], "Mensagem recebida com sucesso.")
        self.assertEqual(contact_message.email, "client@example.com")
        self.assertEqual(contact_message.source, "axis")
        self.assertFalse(contact_message.is_read)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["owner@gmail.com"])
        self.assertEqual(mail.outbox[0].reply_to, ["client@example.com"])
        self.assertIn(contact_message.message, mail.outbox[0].body)

    @override_settings(CONTACT_NOTIFICATION_EMAIL="owner@gmail.com")
    @patch("axis.emails.send_contact_notification", side_effect=RuntimeError("SMTP down"))
    def test_contact_is_preserved_when_notification_fails(self, _send):
        response = self.client.post(
            reverse("axis-contact"),
            {
                "email": "client@example.com",
                "message": "Esta mensagem precisa continuar salva.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ContactMessage.objects.count(), 1)

    def test_contact_endpoint_returns_400_for_invalid_payload(self):
        response = self.client.post(
            reverse("axis-contact"),
            {
                "email": "client@example.com",
                "message": "curto",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("message", response.data)

    @override_settings(CONTACT_NOTIFICATION_EMAIL="")
    def test_contact_ignores_expired_or_invalid_bearer_token(self):
        response = self.client.post(
            reverse("axis-contact"),
            {
                "email": "client@example.com",
                "message": "Mensagem enviada com um token antigo no navegador.",
            },
            format="json",
            HTTP_AUTHORIZATION="Bearer expired-token",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ContactMessage.objects.count(), 1)
