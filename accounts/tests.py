from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APIClient

from django.contrib.auth.tokens import default_token_generator

from accounts.serializers import (
    CustomTokenObtainPairSerializer,
    PasswordResetConfirmSerializer,
)


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


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    PASSWORD_RESET_CONFIRM_URL="http://localhost:3000/axis/reset-password",
)
class PasswordResetTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_request_returns_generic_response_when_email_does_not_exist(self):
        response = self.client.post(
            reverse("password-reset"),
            {"email": "missing@test.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def test_request_sends_reset_email_when_user_exists(self):
        User.objects.create_user(
            username="user@test.com",
            email="user@test.com",
            password="old-password",
        )

        response = self.client.post(
            reverse("password-reset"),
            {"email": "user@test.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("uid=", mail.outbox[0].body)
        self.assertIn("token=", mail.outbox[0].body)
        self.assertIn("http://localhost:3000/axis/reset-password", mail.outbox[0].body)

    def test_confirm_resets_user_password(self):
        user = User.objects.create_user(
            username="user@test.com",
            email="user@test.com",
            password="old-password",
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        response = self.client.post(
            reverse("password-reset-confirm"),
            {
                "uid": uid,
                "token": token,
                "password": "NewStrongPassword123!",
            },
            format="json",
        )

        user.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(user.check_password("NewStrongPassword123!"))

    def test_confirm_rejects_invalid_token(self):
        user = User.objects.create_user(
            username="user@test.com",
            email="user@test.com",
            password="old-password",
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        serializer = PasswordResetConfirmSerializer(data={
            "uid": uid,
            "token": "invalid-token",
            "password": "NewStrongPassword123!",
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("token", serializer.errors)

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
