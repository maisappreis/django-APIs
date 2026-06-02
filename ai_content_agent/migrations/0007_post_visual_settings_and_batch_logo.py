from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai_content_agent", "0006_postgeneration_base_image_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="postgenerationbatch",
            name="logo",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="content_agent/logos/",
            ),
        ),
        migrations.AddField(
            model_name="postgeneration",
            name="logo_position",
            field=models.CharField(default="bottom_right", max_length=20),
        ),
        migrations.AddField(
            model_name="postgeneration",
            name="primary_color",
            field=models.CharField(default="#006C44", max_length=7),
        ),
        migrations.AddField(
            model_name="postgeneration",
            name="secondary_color",
            field=models.CharField(default="#1FD794", max_length=7),
        ),
        migrations.AddField(
            model_name="postgeneration",
            name="tertiary_color",
            field=models.CharField(default="#98C8B6", max_length=7),
        ),
        migrations.AddField(
            model_name="postgeneration",
            name="text_color",
            field=models.CharField(default="#FFFFFF", max_length=7),
        ),
        migrations.AddField(
            model_name="postgeneration",
            name="text_font",
            field=models.CharField(blank=True, max_length=80),
        ),
    ]
