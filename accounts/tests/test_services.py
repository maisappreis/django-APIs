from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings

from accounts.models import Plan, Subscription
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
from accounts.tests.factories import create_plan, create_subscription, create_user


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
