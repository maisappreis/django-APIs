from django.db import migrations


def set_image_quality_settings_db_default(apps, schema_editor):
    Post = apps.get_model("ai_content_agent", "Post")
    Post.objects.filter(image_quality_settings__isnull=True).update(
        image_quality_settings={},
    )

    if schema_editor.connection.vendor != "postgresql":
        return

    schema_editor.execute(
        """
        ALTER TABLE ai_content_agent_post
        ALTER COLUMN image_quality_settings SET DEFAULT '{}'::jsonb
        """
    )


def drop_image_quality_settings_db_default(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    schema_editor.execute(
        """
        ALTER TABLE ai_content_agent_post
        ALTER COLUMN image_quality_settings DROP DEFAULT
        """
    )


class Migration(migrations.Migration):

    dependencies = [
        ("ai_content_agent", "0024_post_edit_focus_image_url"),
    ]

    operations = [
        migrations.RunPython(
            set_image_quality_settings_db_default,
            drop_image_quality_settings_db_default,
        ),
    ]
