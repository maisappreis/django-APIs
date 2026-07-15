from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai_content_agent", "0026_post_edit_image_url_db_defaults"),
    ]

    operations = [
        migrations.AddField(
            model_name="brand",
            name="visual_identity_status",
            field=models.CharField(
                choices=[
                    ("idle", "Idle"),
                    ("pending", "Pending"),
                    ("completed", "Completed"),
                    ("failed", "Failed"),
                ],
                default="idle",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="brand",
            name="visual_identity_error",
            field=models.TextField(blank=True),
        ),
    ]
