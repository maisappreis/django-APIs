from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Plan, Subscription
from accounts.serializers import (
    CheckoutSessionSerializer,
    CustomTokenObtainPairSerializer,
    PasswordResetConfirmSerializer,
    RegisterSerializer,
    UserUpdateSerializer,
)
from accounts.tests.factories import create_plan, create_user


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


class AccountSerializerTest(TestCase):
    def test_register_normalizes_email_and_creates_free_subscription(self):
        free_plan = create_plan()
        serializer = RegisterSerializer(data={
            "email": " NewUser@Test.COM ",
            "password": "strong-password",
            "first_name": "New",
            "last_name": "User",
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()

        self.assertEqual(user.email, "newuser@test.com")
        self.assertEqual(user.username, "newuser@test.com")
        self.assertEqual(user.subscription.plan, free_plan)
        self.assertEqual(user.subscription.status, Subscription.Status.ACTIVE)

    def test_register_rejects_duplicate_email_case_insensitively(self):
        create_plan()
        create_user(email="user@test.com")

        serializer = RegisterSerializer(data={
            "email": " USER@test.com ",
            "password": "strong-password",
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_register_rejects_inactive_selected_plan(self):
        serializer = RegisterSerializer(data={
            "email": "user@test.com",
            "password": "strong-password",
            "plan_tier": Plan.Tier.PRO,
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("plan_tier", serializer.errors)

    def test_checkout_defaults_to_plus_plan_and_stores_selected_plan(self):
        plus_plan = create_plan(
            tier=Plan.Tier.PLUS,
            stripe_price_id="price_plus",
        )
        serializer = CheckoutSessionSerializer(data={
            "product": "axis",
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["plan_tier"], Plan.Tier.PLUS)
        self.assertEqual(serializer.plan, plus_plan)
        self.assertEqual(serializer.product, "axis")
        self.assertEqual(serializer.currency, Plan.Currency.BRL)

    def test_checkout_selects_usd_price(self):
        plus_plan = create_plan(
            tier=Plan.Tier.PLUS,
            stripe_price_id_brl="price_plus_brl",
            stripe_price_id_usd="price_plus_usd",
        )
        serializer = CheckoutSessionSerializer(data={
            "product": "axis",
            "plan_tier": Plan.Tier.PLUS,
            "currency": Plan.Currency.USD,
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.plan, plus_plan)
        self.assertEqual(serializer.currency, Plan.Currency.USD)

    def test_checkout_rejects_plan_without_price_for_selected_currency(self):
        create_plan(
            tier=Plan.Tier.PRO,
            stripe_price_id_brl="price_pro_brl",
            stripe_price_id_usd="",
        )
        serializer = CheckoutSessionSerializer(data={
            "product": "axis",
            "plan_tier": Plan.Tier.PRO,
            "currency": Plan.Currency.USD,
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    def test_checkout_rejects_plan_without_stripe_price_id(self):
        create_plan(tier=Plan.Tier.PRO)
        serializer = CheckoutSessionSerializer(data={
            "product": "axis",
            "plan": Plan.Tier.PRO,
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    def test_checkout_rejects_missing_active_plan(self):
        serializer = CheckoutSessionSerializer(data={
            "product": "axis",
            "plan": Plan.Tier.PRO,
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    def test_user_update_normalizes_email_and_updates_username(self):
        user = create_user(email="old@test.com")
        serializer = UserUpdateSerializer(
            user,
            data={
                "email": " New@Test.COM ",
                "first_name": "Maisa",
                "last_name": "Preis",
            },
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_user = serializer.save()

        self.assertEqual(updated_user.email, "new@test.com")
        self.assertEqual(updated_user.username, "new@test.com")
        self.assertEqual(updated_user.first_name, "Maisa")
        self.assertEqual(updated_user.last_name, "Preis")

    def test_user_update_rejects_email_used_by_another_user(self):
        user = create_user(email="old@test.com")
        create_user(email="taken@test.com")
        serializer = UserUpdateSerializer(
            user,
            data={"email": " taken@test.com "},
            partial=True,
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_token_serializer_requires_email_or_username(self):
        serializer = CustomTokenObtainPairSerializer(data={
            "password": "strong-password",
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_password_reset_confirm_rejects_invalid_uid(self):
        serializer = PasswordResetConfirmSerializer(data={
            "uid": "invalid",
            "token": "invalid-token",
            "password": "NewStrongPassword123!",
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("token", serializer.errors)


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
