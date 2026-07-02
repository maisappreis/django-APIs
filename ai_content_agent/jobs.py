from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.shortcuts import get_object_or_404

from .models import GenerationStatus, PostBatch
from .operations import (
    create_post_drafts_from_generation_result,
    ensure_ai_image_edit_quota,
    ensure_ai_image_quota,
    ensure_user_image_quota,
    get_user_brands,
    mark_batch_completed,
    mark_batch_failed,
    mark_batch_pending_review,
    mark_post_completed,
    record_ai_image_edit_usage,
    record_ai_image_usage,
    record_user_image_usage,
    update_batch_progress,
)
from .services import (
    build_user_post_image_edit_review_prompt,
    generate_post_batch_draft_content,
    prepare_private_post_source_image_files,
    render_approved_post_image,
)


def generate_post_review_batch(user, brand, batch, data):
    update_batch_progress(batch, 10)
    result = generate_post_batch_draft_content(data)
    update_batch_progress(batch, 70)

    image_edit_mode = data.get("image_edit_mode", "none")
    edit_user_image_with_ai = image_edit_mode != "none"

    if batch.image_source == "user":
        for post_data in result["posts"]:
            if edit_user_image_with_ai:
                post_data["image_prompt"] = build_user_post_image_edit_review_prompt(
                    data,
                    post_data,
                )
            else:
                post_data["image_prompt"] = ""

    posts = create_post_drafts_from_generation_result(
        user=user,
        brand=brand,
        batch=batch,
        data=data,
        result=result,
    )

    if batch.image_source == "user" and not edit_user_image_with_ai:
        total_posts = len(posts)

        for index, post in enumerate(posts):
            ensure_user_image_quota(user, 1)
            render_approved_post_image(post, use_existing_base=True)
            mark_post_completed(post)
            record_user_image_usage(user, quantity=1, batch=batch)
            update_batch_progress(
                batch,
                70 + int((index + 1) / total_posts * 25),
            )

        mark_batch_completed(batch, result["strategy_summary"])
        return batch

    if batch.image_source == "user":
        mark_batch_pending_review(batch, result["strategy_summary"])
        return batch

    mark_batch_pending_review(batch, result["strategy_summary"])
    return batch


def run_post_generation_job(user_id, brand_id, batch_id, data):
    close_old_connections()

    try:
        user = get_user_model().objects.get(id=user_id)
        batch = PostBatch.objects.get(id=batch_id, user_id=user_id)
        brand = get_object_or_404(get_user_brands(user), id=brand_id)
        image_object_paths = data.get("image_object_paths") or []

        if (
            data.get("my_images_or_ai") == "user"
            and image_object_paths
            and not data.get("image_files")
        ):
            data["image_files"] = prepare_private_post_source_image_files(
                user_id,
                image_object_paths,
            )

        generate_post_review_batch(user, brand, batch, data)
        return True
    except Exception as error:
        try:
            batch = PostBatch.objects.get(id=batch_id, user_id=user_id)
            mark_batch_failed(batch, error)
        except PostBatch.DoesNotExist:
            pass
        return False
    finally:
        close_old_connections()


def run_post_image_generation_job(user_id, batch_id):
    close_old_connections()

    try:
        user = get_user_model().objects.get(id=user_id)
        batch = PostBatch.objects.get(id=batch_id, user_id=user_id)
        if batch.status == GenerationStatus.COMPLETED:
            return True

        posts = list(
            batch.posts.select_related("brand")
            .filter(user_id=user_id)
            .exclude(status=GenerationStatus.COMPLETED)
            .order_by("scheduled_date", "post_order", "created_at")
        )
        total_posts = len(posts)

        update_batch_progress(batch, 5)

        if total_posts == 0:
            raise ValueError("No posts found for image generation.")

        for index, post in enumerate(posts):
            user_image_ai_edit = (
                batch.image_source == "user"
                and bool(post.image_prompt)
            )

            if batch.image_source == "ai" or user_image_ai_edit:
                if user_image_ai_edit:
                    ensure_ai_image_edit_quota(user, 1)
                else:
                    ensure_ai_image_quota(user, 1)
            if batch.image_source == "user":
                ensure_user_image_quota(user, 1)

            render_approved_post_image(
                post,
                use_existing_base=batch.image_source == "user",
            )
            mark_post_completed(post)

            if batch.image_source == "ai" or user_image_ai_edit:
                if user_image_ai_edit:
                    record_ai_image_edit_usage(user, quantity=1, batch=batch)
                else:
                    record_ai_image_usage(user, quantity=1, batch=batch)
            if batch.image_source == "user":
                record_user_image_usage(user, quantity=1, batch=batch)

            update_batch_progress(
                batch,
                5 + int((index + 1) / total_posts * 90),
            )

        mark_batch_completed(batch, batch.strategy_summary)
        return True
    except Exception as error:
        try:
            batch = PostBatch.objects.get(id=batch_id, user_id=user_id)
            mark_batch_failed(batch, error)
        except PostBatch.DoesNotExist:
            pass
        return False
    finally:
        close_old_connections()
