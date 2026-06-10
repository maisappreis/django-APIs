from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai_content_agent", "0013_postbatch_image_source_usageevent"),
    ]

    operations = [
        migrations.AddField(
            model_name="postbatch",
            name="image_format",
            field=models.CharField(
                default="square",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="post",
            name="image_format",
            field=models.CharField(
                default="square",
                max_length=20,
            ),
        ),
    ]
