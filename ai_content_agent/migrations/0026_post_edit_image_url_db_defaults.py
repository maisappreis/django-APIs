from django.db import migrations


def set_edit_image_url_db_defaults(apps, schema_editor):
    Post = apps.get_model("ai_content_agent", "Post")
    Post.objects.filter(edit_reference_image_url__isnull=True).update(
        edit_reference_image_url="",
    )
    Post.objects.filter(edit_focus_image_url__isnull=True).update(
        edit_focus_image_url="",
    )

    if schema_editor.connection.vendor != "postgresql":
        return

    schema_editor.execute(
        """
        ALTER TABLE ai_content_agent_post
        ALTER COLUMN edit_reference_image_url SET DEFAULT '',
        ALTER COLUMN edit_focus_image_url SET DEFAULT ''
        """
    )


def drop_edit_image_url_db_defaults(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    schema_editor.execute(
        """
        ALTER TABLE ai_content_agent_post
        ALTER COLUMN edit_reference_image_url DROP DEFAULT,
        ALTER COLUMN edit_focus_image_url DROP DEFAULT
        """
    )


class Migration(migrations.Migration):

    dependencies = [
        ("ai_content_agent", "0025_post_image_quality_settings_db_default"),
    ]

    operations = [
        migrations.RunPython(
            set_edit_image_url_db_defaults,
            drop_edit_image_url_db_defaults,
        ),
    ]
