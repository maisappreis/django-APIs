from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai_content_agent", "0014_postbatch_post_image_format"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="image_title",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="post",
            name="image_subtitle",
            field=models.CharField(blank=True, max_length=180),
        ),
        migrations.AddField(
            model_name="post",
            name="title_font",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="post",
            name="subtitle_font",
            field=models.CharField(blank=True, max_length=80),
        ),
    ]
