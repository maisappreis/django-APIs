from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.shortcuts import get_object_or_404

from .models import PostBatch
from .operations import (
    create_post_drafts_from_generation_result,
    ensure_ai_image_quota,
    get_user_brands,
    mark_batch_completed,
    mark_batch_failed,
    mark_batch_pending_review,
    mark_post_completed,
    record_ai_image_usage,
    update_batch_progress,
)
from .services import (
    generate_post_batch_draft_content,
    render_approved_post_image,
)


def run_post_generation_job(user_id, brand_id, batch_id, data):
    close_old_connections()

    try:
        user = get_user_model().objects.get(id=user_id)
        batch = PostBatch.objects.get(id=batch_id, user_id=user_id)
        brand = get_object_or_404(get_user_brands(user), id=brand_id)

        update_batch_progress(batch, 10)
        result = generate_post_batch_draft_content(data)
        update_batch_progress(batch, 70)

        create_post_drafts_from_generation_result(
            user=user,
            brand=brand,
            batch=batch,
            data=data,
            result=result,
        )

        mark_batch_pending_review(batch, result["strategy_summary"])
    except Exception as error:
        try:
            batch = PostBatch.objects.get(id=batch_id, user_id=user_id)
            mark_batch_failed(batch, error)
        except PostBatch.DoesNotExist:
            pass
    finally:
        close_old_connections()


def run_post_image_generation_job(user_id, batch_id):
    close_old_connections()

    try:
        user = get_user_model().objects.get(id=user_id)
        batch = PostBatch.objects.get(id=batch_id, user_id=user_id)
        posts = list(
            batch.posts.select_related("brand")
            .filter(user_id=user_id)
            .order_by("scheduled_date", "post_order", "created_at")
        )
        total_posts = len(posts)

        update_batch_progress(batch, 5)

        if total_posts == 0:
            raise ValueError("No posts found for image generation.")

        for index, post in enumerate(posts):
            if batch.image_source == "ai":
                ensure_ai_image_quota(user, 1)

            render_approved_post_image(
                post,
                use_existing_base=batch.image_source == "user",
            )
            mark_post_completed(post)

            if batch.image_source == "ai":
                record_ai_image_usage(user, quantity=1, batch=batch)

            update_batch_progress(
                batch,
                5 + int((index + 1) / total_posts * 90),
            )

        mark_batch_completed(batch, batch.strategy_summary)
    except Exception as error:
        try:
            batch = PostBatch.objects.get(id=batch_id, user_id=user_id)
            mark_batch_failed(batch, error)
        except PostBatch.DoesNotExist:
            pass
    finally:
        close_old_connections()
