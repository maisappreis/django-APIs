from datetime import timedelta

from django.db import migrations, models


def reschedule_duplicate_brand_dates(apps, schema_editor):
    Post = apps.get_model("ai_content_agent", "Post")
    brand_ids = list(
        Post.objects.exclude(brand_id__isnull=True)
        .exclude(scheduled_date__isnull=True)
        .values_list("brand_id", flat=True)
        .distinct()
    )

    for brand_id in brand_ids:
        used_dates = set()
        posts = Post.objects.filter(
            brand_id=brand_id,
            scheduled_date__isnull=False,
        ).order_by("scheduled_date", "created_at", "id")

        for post in posts:
            next_date = post.scheduled_date
            while next_date in used_dates:
                next_date += timedelta(days=1)

            used_dates.add(next_date)
            if next_date != post.scheduled_date:
                Post.objects.filter(id=post.id).update(scheduled_date=next_date)


class Migration(migrations.Migration):
    dependencies = [
        ("ai_content_agent", "0017_brand_content_language"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="post",
            index=models.Index(
                fields=["brand", "scheduled_date", "status"],
                name="ai_content__brand_i_61ef91_idx",
            ),
        ),
        migrations.RunPython(
            reschedule_duplicate_brand_dates,
            migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="post",
            constraint=models.UniqueConstraint(
                fields=("brand", "scheduled_date"),
                name="unique_scheduled_post_per_brand_date",
            ),
        ),
    ]
