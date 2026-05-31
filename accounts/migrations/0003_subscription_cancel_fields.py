from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_plan_stripe_price_id_subscription_stripe_customer_id_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscription",
            name="cancel_at_period_end",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="subscription",
            name="canceled_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
