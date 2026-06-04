from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def copy_batch_logo_to_brand(apps, schema_editor):
    Brand = apps.get_model("ai_content_agent", "Brand")
    PostGenerationBatch = apps.get_model(
        "ai_content_agent",
        "PostGenerationBatch",
    )

    for batch in PostGenerationBatch.objects.exclude(brand_id__isnull=True):
        update_fields = []
        brand = Brand.objects.get(id=batch.brand_id)

        if getattr(batch, "logo", None) and not brand.logo:
            brand.logo = batch.logo
            update_fields.append("logo")

        if batch.logo_url and not brand.logo_url:
            brand.logo_url = batch.logo_url
            update_fields.append("logo_url")

        if update_fields:
            brand.save(update_fields=update_fields)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ai_content_agent", "0009_brand_postgeneration_brand_postgenerationbatch_brand_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="brand",
            name="logo",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="content_agent/logos/",
            ),
        ),
        migrations.RunPython(copy_batch_logo_to_brand, noop_reverse),
        migrations.RenameModel(
            old_name="PostGenerationBatch",
            new_name="PostBatch",
        ),
        migrations.RenameModel(
            old_name="PostGeneration",
            new_name="Post",
        ),
        migrations.RemoveField(
            model_name="postbatch",
            name="business_name",
        ),
        migrations.RemoveField(
            model_name="postbatch",
            name="logo",
        ),
        migrations.RemoveField(
            model_name="postbatch",
            name="logo_position",
        ),
        migrations.RemoveField(
            model_name="postbatch",
            name="logo_url",
        ),
        migrations.RemoveField(
            model_name="postbatch",
            name="niche",
        ),
        migrations.RemoveField(
            model_name="postbatch",
            name="primary_color",
        ),
        migrations.RemoveField(
            model_name="postbatch",
            name="secondary_color",
        ),
        migrations.RemoveField(
            model_name="postbatch",
            name="tertiary_color",
        ),
        migrations.RemoveField(
            model_name="postbatch",
            name="text_color",
        ),
        migrations.RemoveField(
            model_name="postbatch",
            name="text_font",
        ),
        migrations.RemoveField(
            model_name="post",
            name="business_name",
        ),
        migrations.RemoveField(
            model_name="post",
            name="niche",
        ),
        migrations.RemoveField(
            model_name="post",
            name="objective",
        ),
        migrations.RemoveField(
            model_name="post",
            name="theme",
        ),
        migrations.RemoveField(
            model_name="post",
            name="tone",
        ),
        migrations.AlterField(
            model_name="postbatch",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="post_batches",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="post",
            name="batch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="posts",
                to="ai_content_agent.postbatch",
            ),
        ),
        migrations.AlterField(
            model_name="post",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="posts",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
