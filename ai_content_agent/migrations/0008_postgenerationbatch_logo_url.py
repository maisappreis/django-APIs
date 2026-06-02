from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai_content_agent", "0007_post_visual_settings_and_batch_logo"),
    ]

    operations = [
        migrations.AddField(
            model_name="postgenerationbatch",
            name="logo_url",
            field=models.CharField(blank=True, max_length=500),
        ),
    ]
