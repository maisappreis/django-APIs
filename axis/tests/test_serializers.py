from django.test import TestCase

from axis.models import ContactMessage
from axis.serializers import ContactMessageSerializer
from axis.tests.factories import create_contact_message


class ContactMessageSerializerTest(TestCase):
    def test_serializes_contact_message(self):
        contact_message = create_contact_message(
            email="client@example.com",
            message="Quero saber mais sobre o Axis.",
        )

        data = ContactMessageSerializer(contact_message).data

        self.assertEqual(data["id"], contact_message.id)
        self.assertEqual(data["email"], "client@example.com")
        self.assertEqual(data["message"], "Quero saber mais sobre o Axis.")
        self.assertEqual(data["source"], "axis")
        self.assertIn("created_at", data)

    def test_accepts_valid_contact_message_and_ignores_read_only_source(self):
        serializer = ContactMessageSerializer(data={
            "email": "client@example.com",
            "message": "Mensagem valida para contato.",
            "source": "malicious-source",
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        contact_message = serializer.save(source="axis")

        self.assertEqual(contact_message.source, "axis")
        self.assertEqual(ContactMessage.objects.count(), 1)

    def test_rejects_short_trimmed_message(self):
        serializer = ContactMessageSerializer(data={
            "email": "client@example.com",
            "message": " curto ",
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("message", serializer.errors)

    def test_rejects_invalid_email(self):
        serializer = ContactMessageSerializer(data={
            "email": "not-an-email",
            "message": "Mensagem valida para contato.",
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)
