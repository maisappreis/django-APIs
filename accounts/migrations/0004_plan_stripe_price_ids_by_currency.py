from django.db import migrations, models


def copy_existing_price_to_brl(apps, schema_editor):
    Plan = apps.get_model("accounts", "Plan")
    for plan in Plan.objects.exclude(stripe_price_id=""):
        plan.stripe_price_id_brl = plan.stripe_price_id
        plan.save(update_fields=["stripe_price_id_brl"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_subscription_cancel_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="plan",
            name="stripe_price_id_brl",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="plan",
            name="stripe_price_id_usd",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.RunPython(
            copy_existing_price_to_brl,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="plan",
            name="stripe_price_id",
        ),
    ]
