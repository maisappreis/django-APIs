from django.conf import settings
from django.db import models


class Plan(models.Model):
    class Tier(models.TextChoices):
        FREE = "free", "Free"
        PLUS = "plus", "Plus"
        PRO = "pro", "Pro"

    name = models.CharField(max_length=120)
    tier = models.CharField(max_length=20, choices=Tier.choices)
    price_brl_cents = models.PositiveIntegerField(default=0)
    price_usd_cents = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.get_tier_display()}"
    

class Subscription(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Ativo"
        TRIALING = "trialing", "Teste"
        PAST_DUE = "past_due", "Pagamento pendente"
        CANCELED = "canceled", "Cancelado"
        EXPIRED = "expired", "Expirado"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    valid_until = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)