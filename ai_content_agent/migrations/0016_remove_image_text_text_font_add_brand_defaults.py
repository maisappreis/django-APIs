from django.db import migrations, models

import ai_content_agent.defaults


class Migration(migrations.Migration):

    dependencies = [
        ("ai_content_agent", "0015_post_title_subtitle_fonts"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="brand",
            name="text_font",
        ),
        migrations.AddField(
            model_name="brand",
            name="title_font",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="brand",
            name="subtitle_font",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="brand",
            name="image_format",
            field=models.CharField(
                default=ai_content_agent.defaults.DEFAULT_IMAGE_FORMAT,
                max_length=20,
            ),
        ),
        migrations.RemoveField(
            model_name="post",
            name="image_text",
        ),
        migrations.RemoveField(
            model_name="post",
            name="text_font",
        ),
    ]
