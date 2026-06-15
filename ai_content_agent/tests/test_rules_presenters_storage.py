from datetime import datetime
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import Plan, Subscription
from ai_content_agent.models import GenerationStatus
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
    get_user_plan_tier,
)
from ai_content_agent.storage import (
    delete_public_file,
    get_object_path_from_public_url,
    get_public_url,
    get_storage_backend,
    is_firebase_storage_enabled,
    upload_brand_reference_file,
    upload_generated_post_file,
    upload_local_file,
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
        self.assertEqual(get_ai_image_monthly_limit(user), 2)
        self.assertEqual(get_max_brands(user), 1)
        self.assertFalse(can_capture_visual_identity(user))

    def test_active_subscription_uses_plan_rules(self):
        user = create_user()
        create_subscription(user, tier=Plan.Tier.PRO)

        self.assertEqual(get_user_plan_tier(user), Plan.Tier.PRO)
        self.assertEqual(get_ai_image_monthly_limit(user), 50)
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

    @patch("ai_content_agent.storage.upload_local_file")
    def test_upload_helpers_build_expected_object_paths(self, upload_local_file_mock):
        upload_local_file_mock.return_value = "https://cdn.test/file.png"

        self.assertEqual(
            upload_generated_post_file("/tmp/source.jpg", 1, post_id=2, kind="base"),
            "https://cdn.test/file.png",
        )
        self.assertEqual(upload_logo_file("/tmp/logo.svg", 1), "https://cdn.test/file.png")
        self.assertEqual(
            upload_brand_reference_file("/tmp/ref.webp", 1, 3, 2),
            "https://cdn.test/file.png",
        )

        generated_path = upload_local_file_mock.call_args_list[0].kwargs["object_path"]
        logo_path = upload_local_file_mock.call_args_list[1].kwargs["object_path"]
        reference_path = upload_local_file_mock.call_args_list[2].kwargs["object_path"]
        self.assertTrue(generated_path.startswith("users/1/posts/2/base-"))
        self.assertEqual(logo_path, "users/1/brand/logo.svg")
        self.assertEqual(
            reference_path,
            "users/1/brands/3/references/reference-2.webp",
        )

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="firebase")
    @patch("ai_content_agent.storage.get_firebase_bucket")
    def test_delete_public_file_deletes_blob(self, get_firebase_bucket):
        bucket = Mock()
        blob = bucket.blob.return_value
        get_firebase_bucket.return_value = bucket

        self.assertTrue(delete_public_file("https://storage.googleapis.com/b/users/1/a.png"))
        blob.delete.assert_called_once()
