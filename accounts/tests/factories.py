from django.contrib.auth.models import User

from accounts.models import Plan, Subscription


def create_plan(
    tier=Plan.Tier.FREE,
    stripe_price_id="",
    stripe_price_id_brl=None,
    stripe_price_id_usd=None,
    is_active=True,
):
    return Plan.objects.create(
        name=f"{tier.title()} plan",
        tier=tier,
        stripe_price_id_brl=(
            stripe_price_id
            if stripe_price_id_brl is None
            else stripe_price_id_brl
        ),
        stripe_price_id_usd=(
            stripe_price_id
            if stripe_price_id_usd is None
            else stripe_price_id_usd
        ),
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
