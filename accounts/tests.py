from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APIClient
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth.tokens import default_token_generator

from accounts.models import Plan, Subscription
from accounts.serializers import (
    CheckoutSessionSerializer,
    CustomTokenObtainPairSerializer,
    PasswordResetConfirmSerializer,
    RegisterSerializer,
    UserUpdateSerializer,
)
from accounts.services import (
    cancel_subscription_at_period_end,
    create_checkout_session,
    get_current_period_end,
    handle_checkout_completed,
    handle_invoice_payment_failed,
    handle_stripe_event,
    handle_subscription_updated,
    map_stripe_subscription_status,
    retrieve_stripe_subscription,
    stripe_object_to_dict,
    sync_subscription_from_stripe,
)


def create_plan(tier=Plan.Tier.FREE, stripe_price_id="", is_active=True):
    return Plan.objects.create(
        name=f"{tier.title()} plan",
        tier=tier,
        stripe_price_id=stripe_price_id,
        is_active=is_active,
    )


def create_user(email="user@test.com", password="strong-password"):
    return User.objects.create_user(
        username=email,
        email=email,
        password=password,
    )


def create_subscription(user=None, plan=None, **kwargs):
    user = user or create_user()
    plan = plan or create_plan()
    return Subscription.objects.create(
        user=user,
        plan=plan,
        status=kwargs.pop("status", Subscription.Status.ACTIVE),
        **kwargs,
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
    STRIPE_SECRET_KEY="sk_test",
    STRIPE_CHECKOUT_SUCCESS_URL="https://example.com/success",
    STRIPE_CHECKOUT_CANCEL_URL="https://example.com/cancel",
)
class AccountServiceTest(TestCase):
    def test_stripe_object_to_dict_supports_dict_and_stripe_like_objects(self):
        self.assertEqual(stripe_object_to_dict({"id": "sub_1"}), {"id": "sub_1"})

        stripe_object = SimpleNamespace(
            to_dict_recursive=lambda: {"id": "sub_2"},
        )

        self.assertEqual(stripe_object_to_dict(stripe_object), {"id": "sub_2"})

        legacy_stripe_object = SimpleNamespace(
            _to_dict_recursive=lambda: {"id": "sub_3"},
        )

        self.assertEqual(
            stripe_object_to_dict(legacy_stripe_object),
            {"id": "sub_3"},
        )

    def test_map_stripe_subscription_status_maps_known_and_unknown_statuses(self):
        self.assertEqual(
            map_stripe_subscription_status("active"),
            Subscription.Status.ACTIVE,
        )
        self.assertEqual(
            map_stripe_subscription_status("incomplete_expired"),
            Subscription.Status.EXPIRED,
        )
        self.assertEqual(
            map_stripe_subscription_status("unknown"),
            Subscription.Status.PAST_DUE,
        )

    def test_get_current_period_end_reads_subscription_or_item_period(self):
        self.assertEqual(
            get_current_period_end({"current_period_end": 123}),
            123,
        )
        self.assertEqual(
            get_current_period_end({
                "items": {
                    "data": [
                        {"current_period_end": 456},
                    ],
                },
            }),
            456,
        )
        self.assertIsNone(get_current_period_end({"items": {"data": []}}))

    def test_sync_subscription_from_stripe_updates_local_subscription(self):
        subscription = create_subscription()

        sync_subscription_from_stripe(subscription, {
            "id": "sub_123",
            "customer": "cus_123",
            "status": "trialing",
            "cancel_at_period_end": True,
            "canceled_at": 1700000000,
            "current_period_end": 1700086400,
        })

        subscription.refresh_from_db()
        self.assertEqual(subscription.status, Subscription.Status.TRIALING)
        self.assertEqual(subscription.stripe_customer_id, "cus_123")
        self.assertEqual(subscription.stripe_subscription_id, "sub_123")
        self.assertTrue(subscription.cancel_at_period_end)
        self.assertIsNotNone(subscription.canceled_at)
        self.assertEqual(subscription.valid_until.isoformat(), "2023-11-15")

    @patch("accounts.services.get_stripe_module", return_value=None)
    def test_retrieve_stripe_subscription_returns_none_without_id_or_stripe(
        self,
        get_stripe_module,
    ):
        self.assertIsNone(retrieve_stripe_subscription(""))
        self.assertIsNone(retrieve_stripe_subscription("sub_123"))
        get_stripe_module.assert_called_once()

    @patch("accounts.services.get_stripe_module")
    def test_retrieve_stripe_subscription_returns_subscription_dict(
        self,
        get_stripe_module,
    ):
        stripe = Mock()
        stripe.Subscription.retrieve.return_value = SimpleNamespace(
            to_dict_recursive=lambda: {"id": "sub_123"},
        )
        get_stripe_module.return_value = stripe

        self.assertEqual(
            retrieve_stripe_subscription("sub_123"),
            {"id": "sub_123"},
        )

    @patch("accounts.services.get_stripe_module")
    def test_retrieve_stripe_subscription_returns_none_on_stripe_error(
        self,
        get_stripe_module,
    ):
        class FakeStripeError(Exception):
            pass

        stripe = Mock()
        stripe.error.StripeError = FakeStripeError
        stripe.Subscription.retrieve.side_effect = FakeStripeError()
        get_stripe_module.return_value = stripe

        self.assertIsNone(retrieve_stripe_subscription("sub_123"))

    @patch("accounts.services.get_stripe_module", return_value=None)
    def test_create_checkout_session_raises_when_stripe_is_missing(self, _stripe):
        user = create_user()
        plan = create_plan(tier=Plan.Tier.PLUS, stripe_price_id="price_plus")

        with self.assertRaises(RuntimeError):
            create_checkout_session(user, plan, "axis")

    @patch("accounts.services.get_stripe_module")
    def test_create_checkout_session_sends_metadata_to_stripe(self, get_stripe_module):
        user = create_user()
        plan = create_plan(tier=Plan.Tier.PLUS, stripe_price_id="price_plus")
        stripe = Mock()
        stripe.checkout.Session.create.return_value = SimpleNamespace(
            url="https://checkout.test/session",
        )
        get_stripe_module.return_value = stripe

        session = create_checkout_session(user, plan, "axis")

        self.assertEqual(session.url, "https://checkout.test/session")
        stripe.checkout.Session.create.assert_called_once()
        call_kwargs = stripe.checkout.Session.create.call_args.kwargs
        self.assertEqual(call_kwargs["customer_email"], user.email)
        self.assertEqual(call_kwargs["line_items"][0]["price"], "price_plus")
        self.assertEqual(call_kwargs["metadata"]["user_id"], str(user.id))
        self.assertEqual(call_kwargs["metadata"]["plan_tier"], Plan.Tier.PLUS)
        self.assertEqual(call_kwargs["metadata"]["product"], "axis")

    @patch("accounts.services.get_stripe_module", return_value=None)
    def test_cancel_subscription_raises_when_stripe_is_missing(self, _stripe):
        subscription = create_subscription(stripe_subscription_id="sub_123")

        with self.assertRaises(RuntimeError):
            cancel_subscription_at_period_end(subscription)

    @patch("accounts.services.get_stripe_module")
    def test_cancel_subscription_at_period_end_syncs_returned_subscription(
        self,
        get_stripe_module,
    ):
        subscription = create_subscription(stripe_subscription_id="sub_123")
        stripe = Mock()
        stripe.Subscription.modify.return_value = {
            "id": "sub_123",
            "customer": "cus_123",
            "status": "active",
            "cancel_at_period_end": True,
        }
        get_stripe_module.return_value = stripe

        cancel_subscription_at_period_end(subscription)

        subscription.refresh_from_db()
        stripe.Subscription.modify.assert_called_once_with(
            "sub_123",
            cancel_at_period_end=True,
        )
        self.assertTrue(subscription.cancel_at_period_end)
        self.assertEqual(subscription.stripe_customer_id, "cus_123")

    @patch("accounts.services.retrieve_stripe_subscription", return_value=None)
    def test_handle_checkout_completed_updates_subscription(self, _retrieve):
        free_plan = create_plan()
        plus_plan = create_plan(tier=Plan.Tier.PLUS, stripe_price_id="price_plus")
        user = create_user()
        create_subscription(user=user, plan=free_plan)

        handle_checkout_completed({
            "metadata": {
                "user_id": str(user.id),
                "plan_tier": Plan.Tier.PLUS,
            },
            "customer": "cus_123",
            "subscription": "sub_123",
        })

        subscription = user.subscription
        subscription.refresh_from_db()
        self.assertEqual(subscription.plan, plus_plan)
        self.assertEqual(subscription.stripe_customer_id, "cus_123")
        self.assertEqual(subscription.stripe_subscription_id, "sub_123")

    def test_handle_checkout_completed_ignores_missing_metadata_or_objects(self):
        handle_checkout_completed({"metadata": {}})
        handle_checkout_completed({
            "metadata": {
                "user_id": "999",
                "plan_tier": Plan.Tier.PLUS,
            },
        })

        self.assertEqual(Subscription.objects.count(), 0)

    @patch("accounts.services.retrieve_stripe_subscription")
    def test_handle_checkout_completed_syncs_retrieved_subscription(self, retrieve):
        create_plan()
        plus_plan = create_plan(tier=Plan.Tier.PLUS, stripe_price_id="price_plus")
        user = create_user()
        subscription = create_subscription(user=user)
        retrieve.return_value = {
            "id": "sub_123",
            "customer": "cus_123",
            "status": "active",
            "metadata": {
                "user_id": str(user.id),
                "plan_tier": Plan.Tier.PLUS,
            },
        }

        handle_checkout_completed({
            "metadata": {
                "user_id": str(user.id),
                "plan_tier": Plan.Tier.PLUS,
            },
            "subscription": "sub_123",
        })

        subscription.refresh_from_db()
        self.assertEqual(subscription.plan, plus_plan)
        self.assertEqual(subscription.status, Subscription.Status.ACTIVE)

    def test_handle_subscription_updated_finds_subscription_and_updates_plan(self):
        free_plan = create_plan()
        pro_plan = create_plan(tier=Plan.Tier.PRO, stripe_price_id="price_pro")
        subscription = create_subscription(
            plan=free_plan,
            stripe_subscription_id="sub_123",
        )

        handle_subscription_updated({
            "id": "sub_123",
            "customer": "cus_123",
            "status": "active",
            "metadata": {
                "plan_tier": Plan.Tier.PRO,
            },
        })

        subscription.refresh_from_db()
        self.assertEqual(subscription.plan, pro_plan)
        self.assertEqual(subscription.status, Subscription.Status.ACTIVE)

    def test_handle_subscription_updated_can_find_subscription_by_user_id(self):
        user = create_user()
        subscription = create_subscription(user=user)

        handle_subscription_updated({
            "id": "sub_123",
            "customer": "cus_123",
            "status": "active",
            "metadata": {
                "user_id": str(user.id),
            },
        })

        subscription.refresh_from_db()
        self.assertEqual(subscription.stripe_subscription_id, "sub_123")
        self.assertEqual(subscription.stripe_customer_id, "cus_123")

    def test_handle_subscription_updated_ignores_unknown_subscription(self):
        handle_subscription_updated({
            "id": "sub_missing",
            "status": "active",
            "metadata": {},
        })

        self.assertEqual(Subscription.objects.count(), 0)

    def test_handle_invoice_payment_failed_marks_subscription_past_due(self):
        subscription = create_subscription(
            stripe_subscription_id="sub_123",
            status=Subscription.Status.ACTIVE,
        )

        handle_invoice_payment_failed({"subscription": "sub_123"})

        subscription.refresh_from_db()
        self.assertEqual(subscription.status, Subscription.Status.PAST_DUE)

    def test_handle_invoice_payment_failed_ignores_missing_subscription_id(self):
        handle_invoice_payment_failed({})

        self.assertEqual(Subscription.objects.count(), 0)

    @patch("accounts.services.handle_checkout_completed")
    def test_handle_stripe_event_dispatches_checkout_completed(self, handler):
        handle_stripe_event({
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_123",
                },
            },
        })

        handler.assert_called_once_with({"id": "cs_123"})

    @patch("accounts.services.handle_subscription_updated")
    def test_handle_stripe_event_dispatches_subscription_updated(self, handler):
        handle_stripe_event({
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_123",
                },
            },
        })

        handler.assert_called_once_with({"id": "sub_123"})

    @patch("accounts.services.handle_invoice_payment_failed")
    def test_handle_stripe_event_dispatches_invoice_payment_failed(self, handler):
        handle_stripe_event({
            "type": "invoice.payment_failed",
            "data": {
                "object": {
                    "subscription": "sub_123",
                },
            },
        })

        handler.assert_called_once_with({"subscription": "sub_123"})


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
