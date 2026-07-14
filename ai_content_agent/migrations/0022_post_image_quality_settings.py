from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai_content_agent", "0021_post_image_edit_mode"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="image_quality_settings",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
