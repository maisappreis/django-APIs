from django.contrib import admin
from rest_framework.authtoken.models import Token
from .models import Plan, Subscription
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

admin.site.unregister(User)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "id",
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
    )

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
        "cancel_at_period_end",
        "canceled_at",
        "stripe_customer_id",
        "stripe_subscription_id",
        "created_at",
    )
    list_filter = ("status", "plan", "cancel_at_period_end")
    search_fields = (
        "user__username",
        "user__email",
        "plan__name",
        "stripe_customer_id",
        "stripe_subscription_id",
    )
