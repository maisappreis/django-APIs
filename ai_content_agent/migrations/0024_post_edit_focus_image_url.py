from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai_content_agent", "0023_post_edit_reference_image_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="edit_focus_image_url",
            field=models.CharField(blank=True, max_length=500),
        ),
    ]
