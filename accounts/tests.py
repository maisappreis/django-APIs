from django.contrib.auth.models import User
from django.test import TestCase

from accounts.serializers import CustomTokenObtainPairSerializer


class CustomTokenObtainPairSerializerTest(TestCase):
    def test_accepts_email_as_login_identifier(self):
        email = "user@test.com"
        User.objects.create_user(
            username=email,
            email=email,
            password="strong-password",
        )

        serializer = CustomTokenObtainPairSerializer(data={
            "email": email,
            "password": "strong-password",
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIn("access", serializer.validated_data)
        self.assertEqual(serializer.validated_data["user"]["email"], email)

    def test_keeps_accepting_username_as_login_identifier(self):
        email = "legacy@test.com"
        User.objects.create_user(
            username=email,
            email=email,
            password="strong-password",
        )

        serializer = CustomTokenObtainPairSerializer(data={
            "username": email,
            "password": "strong-password",
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIn("access", serializer.validated_data)
        self.assertEqual(serializer.validated_data["user"]["email"], email)
