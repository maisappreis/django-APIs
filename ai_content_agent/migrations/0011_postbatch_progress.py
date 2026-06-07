from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ai_content_agent", "0010_rename_post_models_and_reduce_batch_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="postbatch",
            name="progress",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
