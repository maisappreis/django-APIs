from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ai_content_agent", "0016_remove_image_text_text_font_add_brand_defaults"),
    ]

    operations = [
        migrations.AddField(
            model_name="brand",
            name="content_language",
            field=models.CharField(
                choices=[
                    ("pt-BR", "Português (Brasil)"),
                    ("en-US", "English (United States)"),
                ],
                default="pt-BR",
                max_length=5,
            ),
        ),
    ]
