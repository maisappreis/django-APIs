from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ai_content_agent", "0018_post_brand_calendar_constraints"),
    ]

    operations = [
        migrations.AlterField(
            model_name="usageevent",
            name="kind",
            field=models.CharField(
                choices=[
                    ("ai_post_image", "AI post image"),
                    ("user_post_image", "User post image"),
                ],
                max_length=40,
            ),
        ),
    ]
