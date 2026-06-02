from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai_content_agent", "0005_postgenerationbatch_form_defaults"),
    ]

    operations = [
        migrations.AddField(
            model_name="postgeneration",
            name="base_image_url",
            field=models.CharField(blank=True, max_length=500),
        ),
    ]
