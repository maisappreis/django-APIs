from datetime import date, datetime
from io import BytesIO
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image

from accounts.models import Plan, Subscription
from ai_content_agent.models import GenerationStatus
from ai_content_agent.firebase_cleanup import (
    cleanup_post_images_outside_retention_window,
    cleanup_replaced_brand_files,
    delete_replaced_firebase_file,
    get_post_image_retention_range,
    is_firebase_public_url,
)
from ai_content_agent.presenters import (
    get_download_filename,
    serialize_brand,
    serialize_post_batch,
    serialize_post_generation,
)
from ai_content_agent.rules import (
    can_capture_visual_identity,
    get_ai_image_monthly_limit,
    get_current_month_range,
    get_max_brands,
    get_user_image_monthly_limit,
    get_user_plan_tier,
)
from ai_content_agent.storage import (
    consume_post_source_upload,
    delete_public_file,
    finalize_brand_reference_upload,
    generate_brand_reference_upload_url,
    generate_private_read_url,
    generate_post_source_upload_url,
    get_object_path_from_public_url,
    get_public_url,
    get_storage_backend,
    is_firebase_storage_enabled,
    upload_brand_reference_file,
    upload_generated_post_file,
    upload_local_file,
    upload_private_local_file,
    upload_logo_file,
)
from ai_content_agent.tests.factories import (
    create_batch,
    create_brand,
    create_post,
    create_subscription,
    create_user,
)


class RulesTest(TestCase):
    def test_unauthenticated_or_without_subscription_uses_free_plan(self):
        anonymous = Mock(is_authenticated=False)
        user = create_user()

        self.assertEqual(get_user_plan_tier(anonymous), "free")
        self.assertEqual(get_user_plan_tier(user), "free")
        self.assertEqual(get_ai_image_monthly_limit(user), 3)
        self.assertEqual(get_user_image_monthly_limit(user), 10)
        self.assertEqual(get_max_brands(user), 1)
        self.assertFalse(can_capture_visual_identity(user))

    def test_active_subscription_uses_plan_rules(self):
        user = create_user()
        create_subscription(user, tier=Plan.Tier.PRO)

        self.assertEqual(get_user_plan_tier(user), Plan.Tier.PRO)
        self.assertEqual(get_ai_image_monthly_limit(user), 60)
        self.assertEqual(get_user_image_monthly_limit(user), 60)
        self.assertEqual(get_max_brands(user), 3)
        self.assertTrue(can_capture_visual_identity(user))

    def test_inactive_subscription_falls_back_to_free(self):
        user = create_user()
        create_subscription(
            user,
            tier=Plan.Tier.PRO,
            status=Subscription.Status.CANCELED,
        )

        self.assertEqual(get_user_plan_tier(user), "free")

    @patch("ai_content_agent.rules.timezone.localtime")
    def test_current_month_range_handles_december_rollover(self, localtime):
        localtime.return_value = timezone.make_aware(datetime(2026, 12, 15, 10))

        start, end = get_current_month_range()

        self.assertEqual(start.month, 12)
        self.assertEqual(start.day, 1)
        self.assertEqual(end.year, 2027)
        self.assertEqual(end.month, 1)
        self.assertEqual(end.day, 1)


class PresentersTest(TestCase):
    def test_serialize_brand_uses_stored_urls(self):
        brand = create_brand(
            logo_url="https://cdn.test/logo.png",
            reference_image_1_url="https://cdn.test/ref1.png",
        )

        data = serialize_brand(brand)

        self.assertEqual(data["id"], brand.id)
        self.assertEqual(data["logo_url"], "https://cdn.test/logo.png")
        self.assertEqual(
            data["reference_image_1_url"],
            "https://cdn.test/ref1.png",
        )
        self.assertEqual(data["business_name"], "Test Brand")

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="firebase")
    @patch("ai_content_agent.presenters.generate_brand_reference_read_url")
    def test_serialize_brand_signs_private_reference(self, generate_read_url):
        generate_read_url.side_effect = lambda value: (
            "https://storage.test/signed" if value else value
        )
        brand = create_brand(
            reference_image_1_url="gs://bucket/users/1/reference.png"
        )

        data = serialize_brand(brand)

        self.assertEqual(
            data["reference_image_1_url"],
            "https://storage.test/signed",
        )
        generate_read_url.assert_any_call(
            "gs://bucket/users/1/reference.png"
        )

    def test_serialize_post_generation_and_batch_orders_posts(self):
        user = create_user()
        brand = create_brand(user=user)
        batch = create_batch(user=user, brand=brand, quantity=2)
        later_post = create_post(
            user=user,
            brand=brand,
            batch=batch,
            post_order=2,
            status=GenerationStatus.COMPLETED,
        )
        earlier_post = create_post(
            user=user,
            brand=brand,
            batch=batch,
            post_order=1,
            status=GenerationStatus.COMPLETED,
        )

        post_data = serialize_post_generation(earlier_post)
        batch_data = serialize_post_batch(batch)

        self.assertEqual(post_data["id"], earlier_post.id)
        self.assertEqual(post_data["batch_id"], batch.id)
        self.assertEqual(batch_data["batch_id"], batch.id)
        self.assertEqual(batch_data["posts"][0]["id"], earlier_post.id)
        self.assertEqual(batch_data["posts"][1]["id"], later_post.id)

    @patch("ai_content_agent.presenters.generate_private_read_url")
    def test_serialize_post_generation_signs_private_images(self, generate_read_url):
        generate_read_url.side_effect = lambda value: f"signed:{value}"
        post = create_post(
            base_image_url="gs://bucket/users/1/posts/1/base.png",
            image_url="gs://bucket/users/1/posts/1/final.png",
        )

        data = serialize_post_generation(post)

        self.assertEqual(
            data["base_image_url"],
            "signed:gs://bucket/users/1/posts/1/base.png",
        )
        self.assertEqual(
            data["image_url"],
            "signed:gs://bucket/users/1/posts/1/final.png",
        )

    def test_get_download_filename_uses_url_extension_or_png_default(self):
        post = create_post(image_url="https://cdn.test/final.jpg?token=1")
        png_post = create_post(image_url="https://cdn.test/final")

        self.assertEqual(get_download_filename(post), f"post-{post.id}.jpg")
        self.assertEqual(get_download_filename(png_post), f"post-{png_post.id}.png")


class StorageTest(TestCase):
    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="local")
    def test_local_backend_disables_firebase_uploads_and_deletes(self):
        self.assertEqual(get_storage_backend(), "local")
        self.assertFalse(is_firebase_storage_enabled())
        self.assertIsNone(upload_local_file("/tmp/file.png", "object.png"))
        self.assertFalse(delete_public_file("https://example.com/file.png"))

    @override_settings(
        CONTENT_AGENT_STORAGE_BACKEND="firebase",
        FIREBASE_PUBLIC_BASE_URL="https://cdn.test",
        FIREBASE_STORAGE_BUCKET="bucket-name",
    )
    def test_public_url_prefers_configured_base_url(self):
        self.assertTrue(is_firebase_storage_enabled())
        self.assertEqual(
            get_public_url("users/1/file.png"),
            "https://cdn.test/users/1/file.png",
        )

    @override_settings(
        CONTENT_AGENT_STORAGE_BACKEND="firebase",
        FIREBASE_PUBLIC_BASE_URL="",
        FIREBASE_STORAGE_BUCKET="bucket-name",
    )
    def test_public_url_falls_back_to_storage_googleapis(self):
        self.assertEqual(
            get_public_url("users/1/file.png"),
            "https://storage.googleapis.com/bucket-name/users/1/file.png",
        )

    @override_settings(
        FIREBASE_PUBLIC_BASE_URL="https://cdn.test",
        FIREBASE_STORAGE_BUCKET="bucket-name",
    )
    def test_object_path_from_public_url_handles_base_url_and_bucket_url(self):
        self.assertEqual(get_object_path_from_public_url(""), "")
        self.assertEqual(
            get_object_path_from_public_url("https://cdn.test/users/1/file.png"),
            "users/1/file.png",
        )
        self.assertEqual(
            get_object_path_from_public_url(
                "https://storage.googleapis.com/bucket-name/users/1/file.png",
            ),
            "users/1/file.png",
        )
        self.assertEqual(
            get_object_path_from_public_url(
                "gs://bucket-name/users/1/private.png"
            ),
            "users/1/private.png",
        )

    @patch("ai_content_agent.storage.upload_private_local_file")
    @patch("ai_content_agent.storage.upload_local_file")
    def test_upload_helpers_build_expected_object_paths(
        self,
        upload_local_file_mock,
        upload_private_local_file_mock,
    ):
        upload_local_file_mock.return_value = "https://cdn.test/file.png"
        upload_private_local_file_mock.return_value = "gs://bucket-name/file.png"

        self.assertEqual(
            upload_generated_post_file("/tmp/source.jpg", 1, post_id=2, kind="base"),
            "gs://bucket-name/file.png",
        )
        self.assertEqual(
            upload_logo_file("/tmp/logo.svg", 1, 3),
            "https://cdn.test/file.png",
        )
        self.assertEqual(
            upload_brand_reference_file("/tmp/ref.webp", 1, 3, 2),
            "https://cdn.test/file.png",
        )

        generated_path = upload_private_local_file_mock.call_args.kwargs["object_path"]
        logo_path = upload_local_file_mock.call_args_list[0].kwargs["object_path"]
        reference_path = upload_local_file_mock.call_args_list[1].kwargs["object_path"]
        self.assertTrue(generated_path.startswith("users/1/posts/2/base-"))
        self.assertTrue(logo_path.startswith("users/1/brands/3/logo-"))
        self.assertTrue(logo_path.endswith(".svg"))
        self.assertTrue(
            reference_path.startswith(
                "users/1/brands/3/references/reference-2-"
            )
        )
        self.assertTrue(reference_path.endswith(".webp"))

    @override_settings(
        CONTENT_AGENT_STORAGE_BACKEND="firebase",
        FIREBASE_STORAGE_BUCKET="bucket-name",
    )
    @patch("ai_content_agent.storage.get_firebase_bucket")
    def test_private_upload_and_read_never_make_object_public(self, get_bucket):
        bucket = Mock()
        blob = bucket.blob.return_value
        blob.generate_signed_url.return_value = "https://storage.test/signed"
        get_bucket.return_value = bucket

        stored_url = upload_private_local_file(
            "/tmp/post.png",
            "users/1/posts/2/final.png",
        )
        read_url = generate_private_read_url(stored_url)

        self.assertEqual(
            stored_url,
            "gs://bucket-name/users/1/posts/2/final.png",
        )
        self.assertEqual(read_url, "https://storage.test/signed")
        blob.make_public.assert_not_called()
        blob.generate_signed_url.assert_called_once()

    @override_settings(FIREBASE_SIGNED_UPLOAD_EXPIRATION_SECONDS=300)
    @patch("ai_content_agent.storage.get_firebase_bucket")
    def test_generate_brand_reference_upload_url_is_private_and_temporary(
        self,
        get_firebase_bucket,
    ):
        bucket = Mock()
        blob = bucket.blob.return_value
        blob.generate_signed_url.return_value = "https://storage.test/signed"
        get_firebase_bucket.return_value = bucket

        result = generate_brand_reference_upload_url(7, "image/webp")

        object_path = bucket.blob.call_args.args[0]
        self.assertTrue(
            object_path.startswith(
                "users/7/pending/brand-references/",
            )
        )
        self.assertTrue(object_path.endswith(".webp"))
        blob.generate_signed_url.assert_called_once()
        signed_url_kwargs = blob.generate_signed_url.call_args.kwargs
        self.assertEqual(signed_url_kwargs["version"], "v4")
        self.assertEqual(signed_url_kwargs["method"], "PUT")
        self.assertEqual(
            signed_url_kwargs["content_type"],
            "image/webp",
        )
        blob.make_public.assert_not_called()
        self.assertEqual(result["upload_url"], "https://storage.test/signed")
        self.assertEqual(result["object_path"], object_path)
        self.assertEqual(result["expires_in"], 300)
        self.assertEqual(
            result["upload_headers"],
            {"Content-Type": "image/webp"},
        )

    @patch("ai_content_agent.storage.get_firebase_bucket")
    def test_generate_brand_reference_upload_url_accepts_jpg_alias(
        self,
        get_firebase_bucket,
    ):
        bucket = Mock()
        blob = bucket.blob.return_value
        blob.generate_signed_url.return_value = "https://storage.test/signed"
        get_firebase_bucket.return_value = bucket

        result = generate_brand_reference_upload_url(7, "image/jpg")

        self.assertTrue(result["object_path"].endswith(".jpg"))
        self.assertEqual(
            result["upload_headers"],
            {"Content-Type": "image/jpg"},
        )

    @patch("ai_content_agent.storage.get_firebase_bucket")
    def test_post_source_upload_is_signed_and_consumed_privately(
        self, get_firebase_bucket
    ):
        image_data = BytesIO()
        Image.new("RGB", (2, 2), "red").save(image_data, format="PNG")
        content = image_data.getvalue()
        bucket = Mock()
        blob = bucket.blob.return_value
        blob.generate_signed_url.return_value = "https://storage.test/signed"
        blob.size = len(content)
        blob.content_type = "image/png"
        blob.download_as_bytes.return_value = content
        get_firebase_bucket.return_value = bucket

        signed = generate_post_source_upload_url(7, "image/png")
        consumed = consume_post_source_upload(7, signed["object_path"])

        self.assertTrue(
            signed["object_path"].startswith(
                "users/7/pending/post-source-images/"
            )
        )
        self.assertEqual(consumed["content"], content)
        blob.delete.assert_called_once_with()

    @override_settings(
        FIREBASE_STORAGE_BUCKET="bucket-name",
        FIREBASE_PUBLIC_BASE_URL="",
    )
    @patch("ai_content_agent.storage.get_firebase_bucket")
    def test_finalize_brand_reference_upload_validates_and_moves_image(
        self, get_firebase_bucket
    ):
        image_data = BytesIO()
        Image.new("RGB", (2, 2), "red").save(image_data, format="PNG")
        content = image_data.getvalue()
        bucket = Mock()
        pending_blob = bucket.blob.return_value
        pending_blob.size = len(content)
        pending_blob.content_type = "image/png"
        pending_blob.download_as_bytes.return_value = content
        get_firebase_bucket.return_value = bucket
        pending_path = (
            "users/7/pending/brand-references/"
            "00000000-0000-0000-0000-000000000000.png"
        )

        result = finalize_brand_reference_upload(7, 3, 2, pending_path)

        self.assertTrue(
            result["object_path"].startswith(
                "users/7/brands/3/references/reference-2-"
            )
        )
        self.assertTrue(result["object_path"].endswith(".png"))
        bucket.copy_blob.assert_called_once_with(
            pending_blob, bucket, result["object_path"]
        )
        pending_blob.delete.assert_called_once_with()
        self.assertEqual(result["content_type"], "image/png")
        self.assertEqual(result["size"], len(content))
        self.assertEqual(
            result["storage_url"],
            f"gs://bucket-name/{result['object_path']}",
        )

    @patch("ai_content_agent.storage.get_firebase_bucket")
    def test_finalize_brand_reference_upload_rejects_another_users_path(
        self, get_firebase_bucket
    ):
        with self.assertRaisesMessage(ValueError, "Caminho de upload inválido"):
            finalize_brand_reference_upload(
                7,
                3,
                1,
                (
                    "users/8/pending/brand-references/"
                    "00000000-0000-0000-0000-000000000000.png"
                ),
            )

        get_firebase_bucket.assert_not_called()

    @override_settings(
        CONTENT_AGENT_STORAGE_BACKEND="firebase",
        FIREBASE_PUBLIC_BASE_URL="https://cdn.test",
    )
    @patch("ai_content_agent.storage.get_firebase_bucket")
    def test_delete_public_file_deletes_blob(self, get_firebase_bucket):
        bucket = Mock()
        blob = bucket.blob.return_value
        get_firebase_bucket.return_value = bucket

        self.assertTrue(delete_public_file("https://storage.googleapis.com/b/users/1/a.png"))
        blob.delete.assert_called_once()


class FirebaseCleanupTest(TestCase):
    @override_settings(
        CONTENT_AGENT_STORAGE_BACKEND="firebase",
        FIREBASE_PUBLIC_BASE_URL="https://cdn.test",
    )
    @patch("ai_content_agent.firebase_cleanup.delete_public_file")
    def test_cleanup_replaced_brand_files_deletes_only_replaced_slots(self, delete_file):
        brand = create_brand(
            logo_url="https://cdn.test/logo.png",
            reference_image_1_url="https://cdn.test/ref1.png",
            reference_image_2_url="https://cdn.test/ref2.png",
        )
        delete_file.return_value = True

        deleted = cleanup_replaced_brand_files(
            brand,
            next_logo=True,
            next_reference_indexes=[2],
        )

        self.assertEqual(deleted, ["https://cdn.test/logo.png", "https://cdn.test/ref2.png"])
        self.assertEqual(delete_file.call_count, 2)

    @override_settings(
        CONTENT_AGENT_STORAGE_BACKEND="firebase",
        FIREBASE_PUBLIC_BASE_URL="https://cdn.test",
    )
    @patch("ai_content_agent.firebase_cleanup.delete_public_file")
    def test_delete_replaced_firebase_file_skips_same_url(self, delete_file):
        self.assertFalse(
            delete_replaced_firebase_file(
                "https://cdn.test/final.png",
                "https://cdn.test/final.png",
            )
        )

        delete_file.assert_not_called()

    @override_settings(
        FIREBASE_PUBLIC_BASE_URL="https://cdn.test",
        FIREBASE_STORAGE_BUCKET="bucket-name",
    )
    def test_is_firebase_public_url_ignores_local_media_urls(self):
        self.assertTrue(is_firebase_public_url("https://cdn.test/users/1/file.png"))
        self.assertTrue(
            is_firebase_public_url(
                "https://storage.googleapis.com/bucket-name/users/1/file.png"
            )
        )
        self.assertFalse(is_firebase_public_url("/media/generated_posts/final.png"))

    def test_post_image_retention_range_uses_30_days_before_and_after(self):
        start_date, end_date = get_post_image_retention_range(date(2026, 6, 17))

        self.assertEqual(start_date, date(2026, 5, 18))
        self.assertEqual(end_date, date(2026, 7, 17))

    @override_settings(
        CONTENT_AGENT_STORAGE_BACKEND="firebase",
        FIREBASE_PUBLIC_BASE_URL="https://cdn.test",
    )
    @patch("ai_content_agent.firebase_cleanup.delete_public_file")
    def test_cleanup_post_images_outside_retention_window_keeps_text_history(self, delete_file):
        user = create_user()
        inside = create_post(
            user=user,
            scheduled_date=date(2026, 6, 20),
            status=GenerationStatus.COMPLETED,
            base_image_url="https://cdn.test/base-inside.png",
            image_url="https://cdn.test/final-inside.png",
        )
        outside = create_post(
            user=user,
            scheduled_date=date(2026, 8, 1),
            status=GenerationStatus.COMPLETED,
            caption="Keep this caption",
            base_image_url="https://cdn.test/base-outside.png",
            image_url="https://cdn.test/final-outside.png",
        )
        delete_file.return_value = True

        cleaned_count = cleanup_post_images_outside_retention_window(
            reference_date=date(2026, 6, 17)
        )

        self.assertEqual(cleaned_count, 1)
        outside.refresh_from_db()
        inside.refresh_from_db()
        self.assertEqual(outside.caption, "Keep this caption")
        self.assertEqual(outside.base_image_url, "")
        self.assertEqual(outside.image_url, "")
        self.assertEqual(inside.base_image_url, "https://cdn.test/base-inside.png")
        self.assertEqual(inside.image_url, "https://cdn.test/final-inside.png")
        self.assertEqual(delete_file.call_count, 2)
