from django.contrib import admin
from rest_framework.authtoken.models import Token
from .models import Plan, Subscription


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ('key', 'user', 'created')


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "tier",
        "price_brl_cents",
        "price_usd_cents",
        "stripe_price_id",
        "is_active",
    )
    list_filter = ("tier", "is_active")
    search_fields = ("name", "tier", "stripe_price_id")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "plan",
        "status",
        "valid_until",
        "stripe_customer_id",
        "stripe_subscription_id",
        "created_at",
    )
    list_filter = ("status", "plan")
    search_fields = (
        "user__username",
        "user__email",
        "plan__name",
        "stripe_customer_id",
        "stripe_subscription_id",
    )
