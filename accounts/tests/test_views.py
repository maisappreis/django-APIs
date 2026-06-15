from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Plan, Subscription
from accounts.tests.factories import create_plan, create_subscription, create_user


@override_settings(
    STRIPE_SECRET_KEY="sk_test",
    STRIPE_WEBHOOK_SECRET="whsec_test",
    STRIPE_CHECKOUT_SUCCESS_URL="https://example.com/success",
    STRIPE_CHECKOUT_CANCEL_URL="https://example.com/cancel",
)
class AccountViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_view_creates_user_and_subscription(self):
        create_plan()

        response = self.client.post(
            reverse("register"),
            {
                "email": "user@test.com",
                "password": "strong-password",
                "first_name": "Test",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"]["email"], "user@test.com")
        self.assertTrue(
            Subscription.objects.filter(user__email="user@test.com").exists(),
        )

    def test_profile_view_returns_and_updates_authenticated_user(self):
        user = create_user(email="user@test.com")
        create_subscription(user=user)
        self.client.force_authenticate(user=user)

        get_response = self.client.get(reverse("profile"))
        patch_response = self.client.patch(
            reverse("profile"),
            {
                "email": "updated@test.com",
                "first_name": "Updated",
            },
            format="json",
        )

        user.refresh_from_db()
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        self.assertEqual(get_response.data["user"]["email"], "user@test.com")
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(user.email, "updated@test.com")
        self.assertEqual(user.username, "updated@test.com")

    @override_settings(STRIPE_SECRET_KEY="")
    def test_checkout_returns_503_when_stripe_key_is_missing(self):
        create_plan(tier=Plan.Tier.PLUS, stripe_price_id="price_plus")
        user = create_user()
        self.client.force_authenticate(user=user)

        response = self.client.post(
            reverse("subscription-checkout"),
            {
                "product": "axis",
                "plan": Plan.Tier.PLUS,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @patch("accounts.views.get_stripe_module", return_value=None)
    def test_checkout_returns_503_when_stripe_module_is_missing(self, _stripe):
        create_plan(tier=Plan.Tier.PLUS, stripe_price_id="price_plus")
        user = create_user()
        self.client.force_authenticate(user=user)

        response = self.client.post(
            reverse("subscription-checkout"),
            {
                "product": "axis",
                "plan": Plan.Tier.PLUS,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @patch("accounts.views.create_checkout_session")
    @patch("accounts.views.get_stripe_module")
    def test_checkout_returns_checkout_url(
        self,
        get_stripe_module,
        create_checkout_session,
    ):
        create_plan(tier=Plan.Tier.PLUS, stripe_price_id="price_plus")
        user = create_user()
        self.client.force_authenticate(user=user)
        get_stripe_module.return_value = Mock()
        create_checkout_session.return_value = SimpleNamespace(
            url="https://checkout.test/session",
        )

        response = self.client.post(
            reverse("subscription-checkout"),
            {
                "product": "axis",
                "plan": Plan.Tier.PLUS,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["checkout_url"],
            "https://checkout.test/session",
        )

    @override_settings(STRIPE_SECRET_KEY="")
    def test_cancel_returns_503_when_stripe_key_is_missing(self):
        user = create_user()
        self.client.force_authenticate(user=user)

        response = self.client.post(reverse("subscription-cancel"))

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @patch("accounts.views.get_stripe_module", return_value=None)
    def test_cancel_returns_503_when_stripe_module_is_missing(self, _stripe):
        user = create_user()
        self.client.force_authenticate(user=user)

        response = self.client.post(reverse("subscription-cancel"))

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @patch("accounts.views.get_stripe_module", return_value=Mock())
    def test_cancel_returns_404_when_user_has_no_subscription(self, _stripe):
        user = create_user()
        self.client.force_authenticate(user=user)

        response = self.client.post(reverse("subscription-cancel"))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("accounts.views.get_stripe_module", return_value=Mock())
    def test_cancel_rejects_subscription_without_stripe_id(self, _stripe):
        user = create_user()
        create_subscription(user=user)
        self.client.force_authenticate(user=user)

        response = self.client.post(reverse("subscription-cancel"))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("accounts.views.get_stripe_module", return_value=Mock())
    def test_cancel_rejects_already_canceled_subscription(self, _stripe):
        user = create_user()
        create_subscription(
            user=user,
            status=Subscription.Status.CANCELED,
            stripe_subscription_id="sub_123",
        )
        self.client.force_authenticate(user=user)

        response = self.client.post(reverse("subscription-cancel"))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("accounts.views.cancel_subscription_at_period_end")
    @patch("accounts.views.get_stripe_module", return_value=Mock())
    def test_cancel_success_returns_updated_subscription(self, _stripe, cancel_service):
        user = create_user()
        subscription = create_subscription(
            user=user,
            stripe_subscription_id="sub_123",
        )
        subscription.cancel_at_period_end = True
        cancel_service.return_value = subscription
        self.client.force_authenticate(user=user)

        response = self.client.post(reverse("subscription-cancel"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["subscription"]["cancel_at_period_end"])

    @override_settings(STRIPE_SECRET_KEY="", STRIPE_WEBHOOK_SECRET="")
    def test_webhook_returns_503_when_stripe_is_not_configured(self):
        response = self.client.post(
            reverse("stripe-webhook"),
            data=b"{}",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @patch("accounts.views.get_stripe_module", return_value=None)
    def test_webhook_returns_503_when_stripe_module_is_missing(self, _stripe):
        response = self.client.post(
            reverse("stripe-webhook"),
            data=b"{}",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @patch("accounts.views.get_stripe_module")
    def test_webhook_returns_400_when_payload_is_invalid(self, get_stripe_module):
        stripe = Mock()
        stripe.Webhook.construct_event.side_effect = ValueError
        stripe.error.SignatureVerificationError = Exception
        get_stripe_module.return_value = stripe

        response = self.client.post(
            reverse("stripe-webhook"),
            data=b"invalid",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig_test",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("accounts.views.get_stripe_module")
    def test_webhook_returns_400_when_signature_is_invalid(self, get_stripe_module):
        class FakeSignatureVerificationError(Exception):
            pass

        stripe = Mock()
        stripe.Webhook.construct_event.side_effect = FakeSignatureVerificationError
        stripe.error.SignatureVerificationError = FakeSignatureVerificationError
        get_stripe_module.return_value = stripe

        response = self.client.post(
            reverse("stripe-webhook"),
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig_test",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("accounts.views.handle_stripe_event")
    @patch("accounts.views.get_stripe_module")
    def test_webhook_constructs_and_handles_event(self, get_stripe_module, handler):
        stripe = Mock()
        stripe.Webhook.construct_event.return_value = {
            "type": "invoice.payment_failed",
            "data": {
                "object": {
                    "subscription": "sub_123",
                },
            },
        }
        stripe.error.SignatureVerificationError = Exception
        get_stripe_module.return_value = stripe

        response = self.client.post(
            reverse("stripe-webhook"),
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig_test",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        stripe.Webhook.construct_event.assert_called_once()
        handler.assert_called_once_with(stripe.Webhook.construct_event.return_value)
