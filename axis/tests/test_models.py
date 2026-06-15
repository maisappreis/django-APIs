from django.test import TestCase

from axis.tests.factories import create_contact_message


class ContactMessageModelTest(TestCase):
    def test_string_representation_contains_email_and_created_date(self):
        contact_message = create_contact_message(email="client@example.com")

        representation = str(contact_message)

        self.assertIn("client@example.com", representation)
        self.assertIn(contact_message.created_at.strftime("%Y-%m-%d %H:%M"), representation)

    def test_defaults_source_to_axis_and_unread(self):
        contact_message = create_contact_message(source="axis")

        self.assertEqual(contact_message.source, "axis")
        self.assertFalse(contact_message.is_read)
