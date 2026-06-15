from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from axis.models import ContactMessage


class ContactAPIViewTest(APITestCase):
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
