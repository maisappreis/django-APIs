from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai_content_agent", "0022_post_image_quality_settings"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="edit_reference_image_url",
            field=models.CharField(blank=True, max_length=500),
        ),
    ]
