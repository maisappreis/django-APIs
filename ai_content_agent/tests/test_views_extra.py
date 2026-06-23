import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

import httpx
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from accounts.models import Plan
from ai_content_agent.models import GenerationStatus, UsageEvent
from ai_content_agent.tests.factories import (
    create_batch,
    create_brand,
    create_post,
    create_subscription,
    create_user,
)
from ai_content_agent.tests.test_operations_services_jobs import get_uploaded_image


class ContentAgentViewExtraTest(APITestCase):
    def setUp(self):
        self.user = create_user()
        self.brand = create_brand(user=self.user)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def get_generation_payload(self, **overrides):
        payload = {
            "brand_id": self.brand.id,
            "business_name": self.brand.business_name,
            "niche": self.brand.niche,
            "objective": "Attract leads",
            "tone": "Friendly",
            "theme": "Summer",
            "quantity": "1",
            "my_images_or_ai": "ai",
            "primary_color": "#111111",
            "secondary_color": "#222222",
            "tertiary_color": "#333333",
            "text_color": "#FFFFFF",
            "title_font": "inter",
            "subtitle_font": "inter",
            "logo_position": "bottom_right",
            "image_format": "square",
        }
        payload.update(overrides)
        return payload

    def test_brand_list_returns_user_brands(self):
        response = self.client.get(reverse("brand-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.brand.id)

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="firebase")
    @patch("ai_content_agent.views.generate_brand_reference_upload_url")
    def test_sign_brand_reference_upload(self, generate_upload_url):
        generate_upload_url.return_value = {
            "upload_url": "https://storage.test/signed",
            "object_path": "users/1/pending/brand-references/ref.png",
            "expires_in": 600,
            "upload_headers": {"Content-Type": "image/png"},
        }

        response = self.client.post(
            reverse("brand-reference-upload-sign"),
            {
                "filename": "reference.png",
                "content_type": "image/png",
                "size": 1024,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, generate_upload_url.return_value)
        generate_upload_url.assert_called_once_with(
            user_id=self.user.id,
            content_type="image/png",
        )

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="firebase")
    @patch("ai_content_agent.views.generate_brand_reference_upload_url")
    def test_sign_brand_reference_upload_accepts_jpg_alias(
        self,
        generate_upload_url,
    ):
        generate_upload_url.return_value = {
            "upload_url": "https://storage.test/signed",
            "object_path": "users/1/pending/brand-references/ref.jpg",
            "expires_in": 600,
            "upload_headers": {"Content-Type": "image/jpg"},
        }

        response = self.client.post(
            reverse("brand-reference-upload-sign"),
            {
                "filename": "reference.jpg",
                "content_type": "image/jpg",
                "size": 1024,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        generate_upload_url.assert_called_once_with(
            user_id=self.user.id,
            content_type="image/jpg",
        )

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="firebase")
    @patch("ai_content_agent.views.generate_brand_reference_upload_url")
    def test_sign_brand_reference_upload_rejects_invalid_metadata(
        self,
        generate_upload_url,
    ):
        response = self.client.post(
            reverse("brand-reference-upload-sign"),
            {
                "filename": "reference.svg",
                "content_type": "image/svg+xml",
                "size": 10 * 1024 * 1024 + 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("content_type", response.data)
        self.assertIn("size", response.data)
        generate_upload_url.assert_not_called()

    def test_sign_brand_reference_upload_requires_authentication(self):
        anonymous_client = APIClient()

        response = anonymous_client.post(
            reverse("brand-reference-upload-sign"),
            {
                "filename": "reference.png",
                "content_type": "image/png",
                "size": 1024,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="local")
    @patch("ai_content_agent.views.generate_brand_reference_upload_url")
    def test_sign_brand_reference_upload_requires_firebase(
        self,
        generate_upload_url,
    ):
        response = self.client.post(
            reverse("brand-reference-upload-sign"),
            {
                "filename": "reference.png",
                "content_type": "image/png",
                "size": 1024,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
        generate_upload_url.assert_not_called()

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="firebase")
    @patch("ai_content_agent.views.generate_post_source_upload_url")
    def test_sign_post_source_upload(self, generate_upload_url):
        generate_upload_url.return_value = {
            "upload_url": "https://storage.test/signed",
            "object_path": "users/1/pending/post-source-images/ref.png",
            "expires_in": 600,
            "upload_headers": {"Content-Type": "image/png"},
        }

        response = self.client.post(
            reverse("post-source-upload-sign"),
            {
                "filename": "post.png",
                "content_type": "image/png",
                "size": 1024,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        generate_upload_url.assert_called_once_with(self.user.id, "image/png")

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="firebase")
    @patch("ai_content_agent.views.analyze_brand_visual_identity")
    @patch("ai_content_agent.views.delete_replaced_firebase_file")
    @patch("ai_content_agent.views.finalize_brand_reference_upload")
    def test_complete_brand_reference_upload_associates_private_object(
        self, finalize_upload, delete_replaced_file, analyze_visual_identity
    ):
        create_subscription(self.user, tier=Plan.Tier.PLUS)
        finalize_upload.return_value = {
            "object_path": "users/1/brands/1/references/ref.png",
            "storage_url": "https://storage.googleapis.com/bucket/ref.png",
            "content_type": "image/png",
            "size": 1024,
        }
        pending_path = (
            f"users/{self.user.id}/pending/brand-references/"
            "00000000-0000-0000-0000-000000000000.png"
        )

        response = self.client.post(
            reverse("brand-reference-upload-complete"),
            {
                "brand_id": self.brand.id,
                "slot": 1,
                "object_path": pending_path,
                "analyze": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.brand.refresh_from_db()
        self.assertEqual(
            self.brand.reference_image_1_url,
            "https://storage.googleapis.com/bucket/ref.png",
        )
        finalize_upload.assert_called_once_with(
            user_id=self.user.id,
            brand_id=self.brand.id,
            slot=1,
            object_path=pending_path,
        )
        delete_replaced_file.assert_called_once_with(
            "", "https://storage.googleapis.com/bucket/ref.png"
        )
        analyze_visual_identity.assert_called_once()

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="firebase")
    @patch("ai_content_agent.views.finalize_brand_reference_upload")
    def test_complete_brand_reference_upload_rejects_another_users_brand(
        self, finalize_upload
    ):
        create_subscription(self.user, tier=Plan.Tier.PLUS)
        another_brand = create_brand()

        response = self.client.post(
            reverse("brand-reference-upload-complete"),
            {
                "brand_id": another_brand.id,
                "slot": 1,
                "object_path": (
                    f"users/{self.user.id}/pending/brand-references/"
                    "00000000-0000-0000-0000-000000000000.png"
                ),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        finalize_upload.assert_not_called()

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="firebase")
    @patch(
        "ai_content_agent.views.finalize_brand_reference_upload",
        side_effect=ValueError("O arquivo enviado não é uma imagem válida."),
    )
    def test_complete_brand_reference_upload_rejects_invalid_image(
        self, _finalize_upload
    ):
        create_subscription(self.user, tier=Plan.Tier.PLUS)

        response = self.client.post(
            reverse("brand-reference-upload-complete"),
            {
                "brand_id": self.brand.id,
                "slot": 1,
                "object_path": (
                    f"users/{self.user.id}/pending/brand-references/"
                    "00000000-0000-0000-0000-000000000000.png"
                ),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="local", DEBUG=True)
    @patch("ai_content_agent.views.analyze_brand_visual_identity")
    def test_brand_create_returns_502_when_visual_identity_analysis_fails(self, analyze):
        self.brand.delete()
        create_subscription(self.user, tier=Plan.Tier.PLUS)
        analyze.side_effect = RuntimeError("ai failed")

        response = self.client.post(
            reverse("brand-list"),
            {
                "business_name": "Reference Brand",
                "niche": "Food",
                "primary_color": "#111111",
                "secondary_color": "#222222",
                "tertiary_color": "#333333",
                "text_color": "#FFFFFF",
                "title_font": "inter",
                "subtitle_font": "inter",
                "logo_position": "bottom_right",
                "image_format": "square",
                "reference_image_1": get_uploaded_image("reference.gif"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn("error", response.data)

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="local", DEBUG=True)
    @patch("ai_content_agent.views.analyze_brand_visual_identity")
    def test_brand_patch_returns_502_when_visual_identity_analysis_fails(self, analyze):
        create_subscription(self.user, tier=Plan.Tier.PLUS)
        analyze.side_effect = RuntimeError("ai failed")

        response = self.client.patch(
            reverse("brand-detail", kwargs={"brand_id": self.brand.id}),
            {
                "reference_image_1": get_uploaded_image("reference.gif"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn("error", response.data)

    @patch("ai_content_agent.views.get_future_scheduled_posts")
    def test_calendar_returns_start_and_posts(self, get_future_posts):
        post = create_post(user=self.user, brand=self.brand)
        get_future_posts.return_value = (date(2026, 6, 14), [post])

        response = self.client.get(
            reverse("calendar-posts"),
            {
                "start_date": "2026-06-14",
                "end_date": "2026-07-17",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        get_future_posts.assert_called_once_with(
            self.user,
            start_date=date(2026, 6, 14),
            end_date=date(2026, 7, 17),
        )
        self.assertEqual(response.data["start"], date(2026, 6, 14))
        self.assertEqual(response.data["posts"][0]["id"], post.id)

    def test_calendar_rejects_invalid_date_range(self):
        response = self.client.get(
            reverse("calendar-posts"),
            {
                "start_date": "2026-07-17",
                "end_date": "2026-06-14",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(CONTENT_AGENT_MAINTENANCE_TOKEN="secret-token")
    @patch("ai_content_agent.views.cleanup_post_images_outside_retention_window")
    def test_firebase_cleanup_maintenance_requires_token(self, cleanup):
        response = self.client.get(reverse("firebase-cleanup-maintenance"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        cleanup.assert_not_called()

    @override_settings(CONTENT_AGENT_MAINTENANCE_TOKEN="secret-token")
    @patch("ai_content_agent.views.cleanup_post_images_outside_retention_window")
    def test_firebase_cleanup_maintenance_runs_with_bearer_token(self, cleanup):
        cleanup.return_value = 3

        response = self.client.get(
            reverse("firebase-cleanup-maintenance"),
            HTTP_AUTHORIZATION="Bearer secret-token",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ok")
        self.assertEqual(response.data["cleaned_posts"], 3)
        cleanup.assert_called_once_with()

    def test_generate_posts_returns_400_when_brand_is_missing(self):
        response = self.client.post(
            reverse("generate-post-content"),
            self.get_generation_payload(brand_id=999, business_name="Missing"),
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("ai_content_agent.views.prepare_uploaded_post_image_files")
    @patch("ai_content_agent.views.generate_post_review_batch")
    def test_generate_posts_with_user_images_prepares_images_and_returns_batch(
        self,
        generate_review,
        prepare_images,
    ):
        batch = create_batch(
            user=self.user,
            brand=self.brand,
            status=GenerationStatus.PENDING_REVIEW,
            progress=100,
            image_source="user",
        )
        create_post(
            user=self.user,
            brand=self.brand,
            batch=batch,
            status=GenerationStatus.PENDING_REVIEW,
        )
        generate_review.return_value = batch
        prepare_images.return_value = [{"base": {}, "final": {}}]

        response = self.client.post(
            reverse("generate-post-content"),
            self.get_generation_payload(
                my_images_or_ai="user",
                images=[get_uploaded_image("post.gif")],
            ),
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        prepare_images.assert_called_once()
        generate_review.assert_called_once()

    @patch("ai_content_agent.views.prepare_private_post_source_image_files")
    @patch("ai_content_agent.views.generate_post_review_batch")
    def test_generate_posts_consumes_private_source_paths(
        self, generate_review, prepare_private_images
    ):
        batch = create_batch(
            user=self.user,
            brand=self.brand,
            status=GenerationStatus.PENDING_REVIEW,
            progress=100,
            image_source="user",
        )
        create_post(
            user=self.user,
            brand=self.brand,
            batch=batch,
            status=GenerationStatus.PENDING_REVIEW,
        )
        generate_review.return_value = batch
        prepare_private_images.return_value = [{"base": {}, "final": {}}]
        object_path = (
            f"users/{self.user.id}/pending/post-source-images/"
            "00000000-0000-0000-0000-000000000000.png"
        )

        response = self.client.post(
            reverse("generate-post-content"),
            self.get_generation_payload(
                my_images_or_ai="user",
                image_object_paths=[object_path],
            ),
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        prepare_private_images.assert_called_once_with(
            self.user.id,
            [object_path],
        )
        generate_review.assert_called_once()

    @override_settings(DEBUG=True)
    @patch("ai_content_agent.views.generate_post_review_batch")
    def test_generate_posts_marks_batch_failed_when_generation_raises(self, generate_review):
        generate_review.side_effect = RuntimeError("generation failed")

        response = self.client.post(
            reverse("generate-post-content"),
            self.get_generation_payload(),
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn("error", response.data)

    def test_generation_status_includes_batch_when_completed(self):
        batch = create_batch(
            user=self.user,
            brand=self.brand,
            status=GenerationStatus.COMPLETED,
            progress=100,
        )
        create_post(user=self.user, brand=self.brand, batch=batch)

        response = self.client.get(
            reverse("post-generation-status", kwargs={"batch_id": batch.id}),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["batch_id"], batch.id)
        self.assertIn("posts", response.data)

    def test_pending_review_returns_empty_payload_when_no_posts(self):
        response = self.client.get(reverse("pending-review-post-batch"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["batch"])
        self.assertEqual(response.data["posts"], [])

    @patch("ai_content_agent.views.enqueue_post_image_generation")
    def test_approve_prompts_returns_403_when_ai_quota_is_exceeded(self, enqueue):
        batch = create_batch(
            user=self.user,
            brand=self.brand,
            status=GenerationStatus.PENDING_REVIEW,
            image_source="ai",
        )
        post = create_post(
            user=self.user,
            brand=self.brand,
            batch=batch,
            status=GenerationStatus.PENDING_REVIEW,
        )
        UsageEvent.objects.create(
            user=self.user,
            kind=UsageEvent.Kind.AI_POST_IMAGE,
            quantity=2,
        )

        response = self.client.post(
            reverse("approve-post-prompts", kwargs={"batch_id": batch.id}),
            {
                "posts": [
                    {
                        "id": post.id,
                        "image_prompt": "Reviewed",
                    }
                ]
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        enqueue.assert_not_called()

    @patch("ai_content_agent.views.rerender_post_image")
    def test_rerender_post_returns_updated_post(self, rerender):
        post = create_post(user=self.user, brand=self.brand)
        post.image_title = "New"
        rerender.return_value = post

        response = self.client.patch(
            reverse("rerender-post-image", kwargs={"post_id": post.id}),
            {
                "image_title": "New",
                "template": "none",
                "primary_color": "#111111",
                "secondary_color": "#222222",
                "tertiary_color": "#333333",
                "text_color": "#FFFFFF",
                "logo_position": "bottom_right",
                "has_text_image": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["image_title"], "New")
        rerender.assert_called_once()

    @override_settings(DEBUG=True)
    @patch("ai_content_agent.views.rerender_post_image", side_effect=RuntimeError("render failed"))
    def test_rerender_post_returns_502_when_render_fails(self, _rerender):
        post = create_post(user=self.user, brand=self.brand)

        response = self.client.patch(
            reverse("rerender-post-image", kwargs={"post_id": post.id}),
            {
                "template": "none",
                "primary_color": "#111111",
                "secondary_color": "#222222",
                "tertiary_color": "#333333",
                "text_color": "#FFFFFF",
                "logo_position": "bottom_right",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn("error", response.data)

    @patch("ai_content_agent.views.prepare_post_download")
    def test_download_post_returns_remote_content_response(self, prepare_download):
        post = create_post(user=self.user, brand=self.brand)
        prepare_download.return_value = {
            "filename": "post.png",
            "local_path": None,
            "content": b"image",
            "content_type": "image/png",
        }

        response = self.client.get(
            reverse("download-post-image", kwargs={"post_id": post.id}),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, b"image")
        self.assertEqual(
            response["Content-Disposition"],
            'attachment; filename="post.png"',
        )

    @patch("ai_content_agent.views.prepare_post_download")
    def test_download_post_returns_local_file_response(self, prepare_download):
        post = create_post(user=self.user, brand=self.brand)
        temp_dir = tempfile.mkdtemp()
        local_path = Path(temp_dir) / "post.png"
        local_path.write_bytes(b"image")
        prepare_download.return_value = {
            "filename": "post.png",
            "local_path": local_path,
            "content": None,
            "content_type": "image/png",
        }

        response = self.client.get(
            reverse("download-post-image", kwargs={"post_id": post.id}),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "image/png")

    @patch("ai_content_agent.views.prepare_post_download", side_effect=FileNotFoundError)
    def test_download_post_returns_404_when_file_is_missing(self, _prepare):
        post = create_post(user=self.user, brand=self.brand)

        response = self.client.get(
            reverse("download-post-image", kwargs={"post_id": post.id}),
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("ai_content_agent.views.prepare_post_download", side_effect=httpx.HTTPError("nope"))
    def test_download_post_returns_502_when_remote_download_fails(self, _prepare):
        post = create_post(user=self.user, brand=self.brand)

        response = self.client.get(
            reverse("download-post-image", kwargs={"post_id": post.id}),
        )

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
