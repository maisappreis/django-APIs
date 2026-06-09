from datetime import datetime

from django.utils import timezone

try:
    from accounts.models import Plan, Subscription
except ImportError:  # pragma: no cover
    Plan = None
    Subscription = None


AI_IMAGE_MONTHLY_LIMITS = {
    "free": 2,
    "plus": 30,
    "pro": 50,
}

PLAN_RULES = {
    "free": {
        "max_brands": 1,
        "can_capture_visual_identity": False,
    },
    "plus": {
        "max_brands": 1,
        "can_capture_visual_identity": True,
    },
    "pro": {
        "max_brands": 3,
        "can_capture_visual_identity": True,
    },
}


def get_user_plan_tier(user):
    if not getattr(user, "is_authenticated", False):
        return "free"

    try:
        subscription = user.subscription
    except Exception:
        return "free"

    active_statuses = {
        getattr(Subscription.Status, "ACTIVE", "active"),
        getattr(Subscription.Status, "TRIALING", "trialing"),
    }

    if subscription.status not in active_statuses:
        return "free"

    return subscription.plan.tier or "free"


def get_ai_image_monthly_limit(user):
    return AI_IMAGE_MONTHLY_LIMITS.get(get_user_plan_tier(user), 2)


def get_plan_rules(user):
    return PLAN_RULES.get(get_user_plan_tier(user), PLAN_RULES["free"])


def get_max_brands(user):
    return get_plan_rules(user)["max_brands"]


def can_capture_visual_identity(user):
    return get_plan_rules(user)["can_capture_visual_identity"]


def get_current_month_range():
    now = timezone.localtime()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if start.month == 12:
        next_month = datetime(start.year + 1, 1, 1)
    else:
        next_month = datetime(start.year, start.month + 1, 1)

    end = timezone.make_aware(next_month, start.tzinfo)

    return start, end
