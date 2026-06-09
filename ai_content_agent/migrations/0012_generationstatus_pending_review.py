from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai_content_agent", "0011_postbatch_progress"),
    ]

    operations = [
        migrations.AlterField(
            model_name="postbatch",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("pending_review", "Pending review"),
                    ("completed", "Completed"),
                    ("failed", "Failed"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="post",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("pending_review", "Pending review"),
                    ("completed", "Completed"),
                    ("failed", "Failed"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
    ]
