from datetime import datetime, timezone
from django.conf import settings
from .models import Plan, Subscription
from .urls_utils import localize_frontend_url


def stripe_object_to_dict(stripe_object):
    if isinstance(stripe_object, dict):
        return stripe_object

    if hasattr(stripe_object, "to_dict_recursive"):
        return stripe_object.to_dict_recursive()

    return stripe_object._to_dict_recursive()


def get_stripe_module():
    try:
        import stripe
    except ImportError:
        return None

    stripe.api_key = settings.STRIPE_SECRET_KEY

    return stripe


def map_stripe_subscription_status(stripe_status):
    status_map = {
        "active": Subscription.Status.ACTIVE,
        "trialing": Subscription.Status.TRIALING,
        "past_due": Subscription.Status.PAST_DUE,
        "canceled": Subscription.Status.CANCELED,
        "unpaid": Subscription.Status.PAST_DUE,
        "incomplete_expired": Subscription.Status.EXPIRED,
    }

    return status_map.get(stripe_status, Subscription.Status.PAST_DUE)


def get_current_period_end(stripe_subscription):
    period_end = stripe_subscription.get("current_period_end")
    if period_end:
        return period_end

    items = stripe_subscription.get("items") or {}
    for item in items.get("data") or []:
        period_end = item.get("current_period_end")
        if period_end:
            return period_end

    return None


def sync_subscription_from_stripe(subscription, stripe_subscription):
    subscription.status = map_stripe_subscription_status(
        stripe_subscription.get("status"),
    )
    subscription.stripe_customer_id = stripe_subscription.get("customer") or ""
    subscription.stripe_subscription_id = stripe_subscription.get("id") or ""
    subscription.cancel_at_period_end = bool(
        stripe_subscription.get("cancel_at_period_end"),
    )

    canceled_at = stripe_subscription.get("canceled_at")
    subscription.canceled_at = (
        datetime.fromtimestamp(canceled_at, tz=timezone.utc)
        if canceled_at
        else None
    )

    period_end = get_current_period_end(stripe_subscription)
    if period_end:
        subscription.valid_until = datetime.fromtimestamp(
            period_end,
            tz=timezone.utc,
        ).date()

    subscription.save()


def retrieve_stripe_subscription(subscription_id):
    if not subscription_id:
        return None

    stripe = get_stripe_module()
    if not stripe:
        return None

    try:
        return stripe_object_to_dict(stripe.Subscription.retrieve(subscription_id))
    except stripe.error.StripeError:
        return None


def create_checkout_session(
    user,
    plan,
    product,
    currency=Plan.Currency.BRL,
    locale="pt",
):
    stripe = get_stripe_module()
    if not stripe:
        raise RuntimeError("Biblioteca stripe nao instalada.")

    return stripe.checkout.Session.create(
        mode="subscription",
        customer_email=user.email,
        line_items=[
            {
                "price": plan.get_stripe_price_id(currency),
                "quantity": 1,
            }
        ],
        success_url=localize_frontend_url(
            f"{settings.FRONTEND_URL.rstrip('/')}/billing/success/",
            locale,
            "",
        ),
        cancel_url=localize_frontend_url(
            f"{settings.FRONTEND_URL.rstrip('/')}/billing/cancel/",
            locale,
            "",
        ),
        metadata={
            "user_id": str(user.id),
            "plan_tier": plan.tier,
            "product": product,
            "currency": currency,
            "locale": locale,
        },
        subscription_data={
            "metadata": {
                "user_id": str(user.id),
                "plan_tier": plan.tier,
                "product": product,
                "currency": currency,
                "locale": locale,
            },
        },
    )


def cancel_subscription_at_period_end(subscription):
    stripe = get_stripe_module()
    if not stripe:
        raise RuntimeError("Biblioteca stripe nao instalada.")

    stripe_subscription = stripe.Subscription.modify(
        subscription.stripe_subscription_id,
        cancel_at_period_end=True,
    )
    stripe_subscription = stripe_object_to_dict(stripe_subscription)
    sync_subscription_from_stripe(subscription, stripe_subscription)

    return subscription


def handle_checkout_completed(session):
    user_id = session.get("metadata", {}).get("user_id")
    plan_tier = session.get("metadata", {}).get("plan_tier")

    if not user_id or not plan_tier:
        return

    try:
        plan = Plan.objects.get(tier=plan_tier, is_active=True)
        subscription = Subscription.objects.get(user_id=user_id)
    except (Plan.DoesNotExist, Subscription.DoesNotExist):
        return

    subscription.plan = plan
    subscription.status = Subscription.Status.ACTIVE
    subscription.stripe_customer_id = session.get("customer") or ""
    subscription.stripe_subscription_id = session.get("subscription") or ""

    stripe_subscription = retrieve_stripe_subscription(
        subscription.stripe_subscription_id,
    )
    if stripe_subscription:
        sync_subscription_from_stripe(subscription, stripe_subscription)
    else:
        subscription.save()


def handle_subscription_updated(stripe_subscription):
    subscription_id = stripe_subscription.get("id")
    metadata = stripe_subscription.get("metadata", {})
    user_id = metadata.get("user_id")
    plan_tier = metadata.get("plan_tier")

    subscription = None

    if subscription_id:
        subscription = Subscription.objects.filter(
            stripe_subscription_id=subscription_id,
        ).first()

    if not subscription and user_id:
        subscription = Subscription.objects.filter(user_id=user_id).first()

    if not subscription:
        return

    if plan_tier:
        plan = Plan.objects.filter(tier=plan_tier, is_active=True).first()
        if plan:
            subscription.plan = plan

    sync_subscription_from_stripe(subscription, stripe_subscription)


def handle_invoice_payment_failed(invoice):
    subscription_id = invoice.get("subscription")

    if not subscription_id:
        return

    Subscription.objects.filter(
        stripe_subscription_id=subscription_id,
    ).update(status=Subscription.Status.PAST_DUE)


def handle_stripe_event(event):
    stripe_object = stripe_object_to_dict(event["data"]["object"])

    if event["type"] == "checkout.session.completed":
        handle_checkout_completed(stripe_object)
    elif event["type"] in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        handle_subscription_updated(stripe_object)
    elif event["type"] == "invoice.payment_failed":
        handle_invoice_payment_failed(stripe_object)
