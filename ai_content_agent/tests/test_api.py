import shutil
import tempfile
from datetime import date
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from PIL import Image

from accounts.models import Plan, Subscription

from ..models import Brand, GenerationStatus, Post, PostBatch, UsageEvent
from ..operations import (
    create_post_drafts_from_generation_result,
    delete_post_generation,
    get_available_post_dates,
)
from ..serializers import PostImageRenderInputSerializer
from ..services import (
    generate_post_batch_draft_content,
    render_approved_post_image,
    render_post_content,
    rerender_post_image,
)
from ..utils import _get_font_key, _get_font_candidate_paths


TODAY = "2026-06-11"


def get_test_image(name="logo.gif"):
    return SimpleUploadedFile(
        name,
        (
            b"GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xff\xff\xff,\x00\x00\x00\x00\x01\x00\x01\x00"
            b"\x00\x02\x02D\x01\x00;"
        ),
        content_type="image/gif",
    )


def get_test_logo_png():
    content = BytesIO()
    Image.new("RGBA", (2, 2), "blue").save(content, format="PNG")

    return SimpleUploadedFile(
        "logo.png",
        content.getvalue(),
        content_type="image/png",
    )


class BrandPatchAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="brand-owner",
            password="password",
        )
        self.other_user = User.objects.create_user(
            username="other-user",
            password="password",
        )
        self.brand = Brand.objects.create(
            user=self.user,
            business_name="Old Brand",
            niche="Old niche",
            primary_color="#111111",
            secondary_color="#222222",
            tertiary_color="#333333",
            text_color="#FFFFFF",
            title_font="inter",
            subtitle_font="inter",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_patch_brand_updates_partial_fields(self):
        url = reverse("brand-detail", kwargs={"brand_id": self.brand.id})

        response = self.client.patch(
            url,
            {
                "business_name": "New Brand",
                "primary_color": "#006C44",
                "title_font": "montserrat",
                "subtitle_font": "montserrat",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.brand.refresh_from_db()
        self.assertEqual(self.brand.business_name, "New Brand")
        self.assertEqual(self.brand.niche, "Old niche")
        self.assertEqual(self.brand.primary_color, "#006C44")
        self.assertEqual(self.brand.title_font, "montserrat")
        self.assertEqual(self.brand.subtitle_font, "montserrat")
        self.assertEqual(response.data["business_name"], "New Brand")

    def test_patch_brand_does_not_update_other_users_brand(self):
        self.client.force_authenticate(user=self.other_user)
        url = reverse("brand-detail", kwargs={"brand_id": self.brand.id})

        response = self.client.patch(
            url,
            {"business_name": "Forbidden Brand"},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        self.brand.refresh_from_db()
        self.assertEqual(self.brand.business_name, "Old Brand")

    def test_free_plan_blocks_visual_identity_capture_on_patch(self):
        url = reverse("brand-detail", kwargs={"brand_id": self.brand.id})

        response = self.client.patch(
            url,
            {
                "reference_image_1": get_test_image("reference.gif"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("identidade visual", response.data["detail"])

    def test_patch_brand_rejects_gif_logo(self):
        response = self.client.patch(
            reverse("brand-detail", kwargs={"brand_id": self.brand.id}),
            {"logo": get_test_image("logo.gif")},
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("logo", response.data)
        self.assertIn(
            "PNG, JPEG ou WebP",
            str(response.data["logo"]),
        )


class BrandCreateAPITestCase(APITestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.user = User.objects.create_user(
            username="brand-creator",
            password="password",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        shutil.rmtree(self.media_root, ignore_errors=True)

    def create_subscription(self, tier):
        plan = Plan.objects.create(
            name=tier.title(),
            tier=tier,
            is_active=True,
        )
        return Subscription.objects.create(
            user=self.user,
            plan=plan,
            status=Subscription.Status.ACTIVE,
        )

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="firebase")
    @patch("ai_content_agent.operations.upload_logo_file")
    def test_post_brand_with_logo_uploads_to_firebase_and_saves_url(
        self,
        upload_logo_file,
    ):
        firebase_url = "https://storage.example.com/users/1/brand/logo.png"
        upload_logo_file.return_value = firebase_url

        with override_settings(MEDIA_ROOT=self.media_root):
            response = self.client.post(
                reverse("brand-list"),
                {
                    "business_name": "Logo Brand",
                    "niche": "Fitness",
                    "primary_color": "#111111",
                    "secondary_color": "#222222",
                    "tertiary_color": "#333333",
                    "text_color": "#FFFFFF",
                    "title_font": "inter",
            "subtitle_font": "inter",
                    "logo": get_test_logo_png(),
                    "logo_position": "bottom_right",
                },
                format="multipart",
            )

        self.assertEqual(response.status_code, 201)
        brand = Brand.objects.get(user=self.user, business_name="Logo Brand")
        self.assertFalse(brand.logo)
        self.assertEqual(brand.logo_url, firebase_url)
        self.assertEqual(response.data["logo_url"], firebase_url)
        upload_logo_file.assert_called_once_with(
            local_path=upload_logo_file.call_args.kwargs["local_path"],
            user_id=self.user.id,
            brand_id=brand.id,
        )

    def test_post_brand_without_logo_keeps_logo_url_blank(self):
        response = self.client.post(
            reverse("brand-list"),
            {
                "business_name": "No Logo Brand",
                "niche": "Food",
                "primary_color": "#111111",
                "secondary_color": "#222222",
                "tertiary_color": "#333333",
                "text_color": "#FFFFFF",
                "title_font": "inter",
            "subtitle_font": "inter",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        brand = Brand.objects.get(user=self.user, business_name="No Logo Brand")
        self.assertFalse(brand.logo)
        self.assertEqual(brand.logo_url, "")
        self.assertEqual(brand.title_font, "inter")
        self.assertEqual(brand.subtitle_font, "inter")
        self.assertEqual(response.data["title_font"], "inter")
        self.assertEqual(response.data["subtitle_font"], "inter")

    def test_free_plan_blocks_second_brand(self):
        Brand.objects.create(
            user=self.user,
            business_name="Existing Brand",
            niche="Fitness",
        )

        response = self.client.post(
            reverse("brand-list"),
            {
                "business_name": "Second Brand",
                "niche": "Food",
                "primary_color": "#111111",
                "secondary_color": "#222222",
                "tertiary_color": "#333333",
                "text_color": "#FFFFFF",
                "title_font": "inter",
            "subtitle_font": "inter",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("Limite de marcas", response.data["detail"])

    def test_free_plan_blocks_visual_identity_capture_on_create(self):
        response = self.client.post(
            reverse("brand-list"),
            {
                "business_name": "Reference Brand",
                "niche": "Fitness",
                "primary_color": "#111111",
                "secondary_color": "#222222",
                "tertiary_color": "#333333",
                "text_color": "#FFFFFF",
                "title_font": "inter",
            "subtitle_font": "inter",
                "reference_image_1": get_test_image("reference.gif"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("identidade visual", response.data["detail"])

    def test_pro_plan_allows_three_brands_and_blocks_fourth(self):
        self.create_subscription(Plan.Tier.PRO)

        for index in range(3):
            Brand.objects.create(
                user=self.user,
                business_name=f"Brand {index}",
                niche="Fitness",
            )

        response = self.client.post(
            reverse("brand-list"),
            {
                "business_name": "Fourth Brand",
                "niche": "Food",
                "primary_color": "#111111",
                "secondary_color": "#222222",
                "tertiary_color": "#333333",
                "text_color": "#FFFFFF",
                "title_font": "inter",
            "subtitle_font": "inter",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("3 marca(s)", response.data["detail"])


class PostImageTextTestCase(SimpleTestCase):
    def get_base_data(self, **overrides):
        return {
            "quantity": 1,
            "template": "none",
            "use_templates": False,
            "logo_position": "bottom_right",
            "primary_color": "#111111",
            "secondary_color": "#222222",
            "tertiary_color": "#333333",
            "text_color": "#FFFFFF",
            "title_font": "inter",
            "subtitle_font": "inter",
            **overrides,
        }

    def get_result(self):
        return {
            "caption": "Caption",
            "hashtags": ["#tag"],
            "image_prompt": "Image prompt",
            "image_title": "AI TEXT",
            "image_subtitle": "AI SUBTITLE",
        }

    @patch("ai_content_agent.services.render_image_file")
    @patch("ai_content_agent.services.generate_post_image_files")
    def test_render_post_content_uses_blank_image_title_when_disabled(
        self,
        generate_post_image_files,
        render_image_file,
    ):
        generate_post_image_files.return_value = {
            "base": {
                "image_url": "/media/base.png",
                "absolute_path": "/tmp/base.png",
            },
            "final": {
                "image_url": "/media/final.png",
                "absolute_path": "/tmp/final.png",
            },
        }

        post_data = render_post_content(
            data=self.get_base_data(has_text_image=False),
            idea={"title": "Idea"},
            result=self.get_result(),
            index=1,
        )

        self.assertEqual(post_data["image_title"], "")
        self.assertEqual(render_image_file.call_args.kwargs["image_title"], "")

    @patch("ai_content_agent.services.render_image_file")
    @patch("ai_content_agent.services.generate_post_image_files")
    def test_render_post_content_uses_user_image_title_when_provided(
        self,
        generate_post_image_files,
        render_image_file,
    ):
        generate_post_image_files.return_value = {
            "base": {
                "image_url": "/media/base.png",
                "absolute_path": "/tmp/base.png",
            },
            "final": {
                "image_url": "/media/final.png",
                "absolute_path": "/tmp/final.png",
            },
        }

        post_data = render_post_content(
            data=self.get_base_data(image_title="USER TEXT"),
            idea={"title": "Idea"},
            result=self.get_result(),
            index=1,
        )

        self.assertEqual(post_data["image_title"], "USER TEXT")
        self.assertEqual(
            render_image_file.call_args.kwargs["image_title"],
            "USER TEXT",
        )

    @patch("ai_content_agent.services.apply_center_text_to_image")
    def test_render_image_file_joins_title_and_subtitle_with_hyphen(
        self,
        apply_center_text_to_image,
    ):
        from ..services import render_image_file

        render_image_file(
            image_path="/tmp/final.png",
            template_name="none",
            image_title="TITLE",
            image_subtitle="SUBTITLE",
            title_font="inter",
        )

        self.assertEqual(
            apply_center_text_to_image.call_args.kwargs["text"],
            "TITLE: SUBTITLE",
        )


class PostDraftGenerationTestCase(SimpleTestCase):
    def get_base_data(self):
        return {
            "quantity": 1,
            "business_name": "Draft Brand",
            "niche": "Fitness",
            "objective": "Attract leads",
            "tone": "Friendly",
            "theme": "Summer",
            "template": "none",
            "use_templates": False,
            "logo_position": "bottom_right",
            "primary_color": "#111111",
            "secondary_color": "#222222",
            "tertiary_color": "#333333",
            "text_color": "#FFFFFF",
            "title_font": "inter",
            "subtitle_font": "inter",
        }

    @override_settings(CONTENT_AGENT_USE_MOCK_CONTENT=True)
    @patch("ai_content_agent.services.render_post_content")
    @patch("ai_content_agent.services.generate_post_image_files")
    def test_draft_generation_does_not_render_or_generate_images(
        self,
        generate_post_image_files,
        render_post_content_mock,
    ):
        result = generate_post_batch_draft_content(self.get_base_data())

        self.assertEqual(result["quantity"], 1)
        self.assertEqual(result["posts"][0]["image_url"], "")
        self.assertEqual(result["posts"][0]["base_image_url"], "")
        self.assertTrue(result["posts"][0]["image_prompt"])
        generate_post_image_files.assert_not_called()
        render_post_content_mock.assert_not_called()


class PostDraftOperationTestCase(TestCase):
    def test_create_post_drafts_marks_posts_as_pending_review(self):
        user = User.objects.create_user(
            username="draft-owner",
            password="password",
        )
        brand = Brand.objects.create(
            user=user,
            business_name="Draft Brand",
            niche="Fitness",
        )
        batch = PostBatch.objects.create(
            user=user,
            brand=brand,
            objective="Attract leads",
            tone="Friendly",
            theme="Summer",
            quantity=1,
        )
        result = {
            "posts": [
                {
                    "order": 1,
                    "idea": {"title": "Idea"},
                    "template": "none",
                    "primary_color": "#111111",
                    "secondary_color": "#222222",
                    "tertiary_color": "#333333",
                    "text_color": "#FFFFFF",
                    "title_font": "inter",
            "subtitle_font": "inter",
                    "logo_position": "",
                    "caption": "Caption",
                    "hashtags": ["#tag"],
                    "image_prompt": "Prompt to review",
                    "image_title": "TEXT",
                    "image_subtitle": "SUBTITLE",
                }
            ],
        }

        posts = create_post_drafts_from_generation_result(
            user=user,
            brand=brand,
            batch=batch,
            result=result,
        )

        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].status, GenerationStatus.PENDING_REVIEW)
        self.assertEqual(posts[0].image_url, "")
        self.assertEqual(posts[0].image_prompt, "Prompt to review")

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="local")
    def test_create_post_drafts_stores_uploaded_base_image(self):
        user = User.objects.create_user(
            username="draft-image-owner",
            password="password",
        )
        brand = Brand.objects.create(
            user=user,
            business_name="Draft Brand",
            niche="Fitness",
        )
        batch = PostBatch.objects.create(
            user=user,
            brand=brand,
            objective="Attract leads",
            tone="Friendly",
            theme="Summer",
            quantity=1,
            image_source="user",
        )
        result = {
            "posts": [
                {
                    "order": 1,
                    "idea": {"title": "Idea"},
                    "template": "none",
                    "primary_color": "#111111",
                    "secondary_color": "#222222",
                    "tertiary_color": "#333333",
                    "text_color": "#FFFFFF",
                    "title_font": "inter",
            "subtitle_font": "inter",
                    "logo_position": "",
                    "caption": "Caption",
                    "hashtags": ["#tag"],
                    "image_prompt": "Prompt to review",
                    "image_title": "TEXT",
                    "image_subtitle": "SUBTITLE",
                }
            ],
        }

        posts = create_post_drafts_from_generation_result(
            user=user,
            brand=brand,
            batch=batch,
            result=result,
            data={
                "image_files": [
                    {
                        "base": {
                            "image_url": "/media/generated_posts/uploads/user-base.png",
                            "absolute_path": "/tmp/user-base.png",
                        },
                        "final": {
                            "image_url": "/media/generated_posts/final.png",
                            "absolute_path": "/tmp/final.png",
                        },
                    }
                ],
            },
        )

        self.assertEqual(
            posts[0].base_image_url,
            "/media/generated_posts/uploads/user-base.png",
        )
        self.assertEqual(posts[0].image_url, "")


class PostSchedulingTestCase(TestCase):
    @patch("ai_content_agent.operations.timezone.localdate")
    def test_different_brands_can_use_the_same_date(self, localdate):
        localdate.return_value = date(2026, 6, 11)
        user = User.objects.create_user(
            username="multi-brand-schedule-owner",
            password="password",
        )
        first_brand = Brand.objects.create(
            user=user,
            business_name="First Brand",
            niche="Fitness",
        )
        second_brand = Brand.objects.create(
            user=user,
            business_name="Second Brand",
            niche="Food",
        )
        Post.objects.create(
            user=user,
            brand=first_brand,
            scheduled_date=date(2026, 6, 11),
            status=GenerationStatus.COMPLETED,
        )

        self.assertEqual(
            get_available_post_dates(user, second_brand, 1),
            [date(2026, 6, 11)],
        )

    @patch("ai_content_agent.operations.timezone.localdate")
    def test_all_scheduled_brand_posts_block_available_dates(
        self,
        localdate,
    ):
        localdate.return_value = date(2026, 6, 11)
        user = User.objects.create_user(
            username="schedule-owner",
            password="password",
        )
        brand = Brand.objects.create(
            user=user,
            business_name="Schedule Brand",
            niche="Fitness",
        )
        Post.objects.create(
            user=user,
            brand=brand,
            scheduled_date=date(2026, 6, 11),
            status=GenerationStatus.COMPLETED,
        )
        Post.objects.create(
            user=user,
            brand=brand,
            scheduled_date=date(2026, 6, 12),
            status=GenerationStatus.PENDING_REVIEW,
        )
        Post.objects.create(
            user=user,
            brand=brand,
            scheduled_date=date(2026, 6, 13),
            status=GenerationStatus.PENDING,
        )

        self.assertEqual(
            get_available_post_dates(user, brand, 3),
            [
                date(2026, 6, 14),
                date(2026, 6, 15),
                date(2026, 6, 16),
            ],
        )

    @patch("ai_content_agent.operations.timezone.localdate")
    def test_deleted_completed_post_date_becomes_available(self, localdate):
        localdate.return_value = date(2026, 6, 11)
        user = User.objects.create_user(
            username="delete-schedule-owner",
            password="password",
        )
        brand = Brand.objects.create(
            user=user,
            business_name="Delete Schedule Brand",
            niche="Fitness",
        )
        post = Post.objects.create(
            user=user,
            brand=brand,
            scheduled_date=date(2026, 6, 11),
            status=GenerationStatus.COMPLETED,
        )

        delete_post_generation(post)

        self.assertEqual(
            get_available_post_dates(user, brand, 2),
            [
                date(2026, 6, 11),
                date(2026, 6, 12),
            ],
        )


class TextFontResolutionTestCase(SimpleTestCase):
    def test_resolves_frontend_font_values_to_backend_keys(self):
        self.assertEqual(_get_font_key("montserrat"), "montserrat")
        self.assertEqual(_get_font_key("Montserrat, sans-serif"), "montserrat")
        self.assertEqual(_get_font_key("Montserrat Bold"), "montserrat")
        self.assertEqual(_get_font_key("Playfair Display"), "playfairdisplay")
        self.assertEqual(_get_font_key("Poppins"), "poppins")

    @override_settings(CONTENT_AGENT_FONT_DIR="/app/fonts")
    def test_prefers_configured_font_directory(self):
        candidates = list(_get_font_candidate_paths("montserrat"))

        self.assertEqual(
            str(candidates[0]).replace("\\", "/"),
            "/app/fonts/Montserrat-Medium.ttf",
        )


class PostImageRenderInputSerializerTestCase(SimpleTestCase):
    def test_accepts_has_text_image_and_blank_logo_position(self):
        serializer = PostImageRenderInputSerializer(data={
            "has_text_image": "no",
            "image_title": "",
                "image_subtitle": "",
            "template": "none",
            "title_font": "inter",
            "subtitle_font": "inter",
            "text_color": "#FFFFFF",
            "primary_color": "#111111",
            "secondary_color": "#222222",
            "tertiary_color": "#333333",
            "logo_position": "",
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertFalse(serializer.validated_data["has_text_image"])
        self.assertEqual(serializer.validated_data["logo_position"], "")


class PostGenerationInputSerializerTestCase(SimpleTestCase):
    def test_accepts_blank_logo_position_to_generate_post_without_logo(self):
        from ..serializers import PostGenerationInputSerializer

        serializer = PostGenerationInputSerializer(data={
            "brand_id": 1,
            "business_name": "Brand",
            "niche": "Fitness",
            "objective": "Attract leads",
            "tone": "Friendly",
            "theme": "Summer",
            "logo_position": "",
            "image_format": "portrait",
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["logo_position"], "")
        self.assertEqual(serializer.validated_data["image_format"], "portrait")


class RerenderPostImageTestCase(TestCase):
    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="local")
    @patch("ai_content_agent.services.render_image_file")
    @patch("ai_content_agent.services.create_final_image_from_base")
    def test_blank_logo_position_removes_brand_logo_from_post(
        self,
        create_final_image_from_base,
        render_image_file,
    ):
        user = User.objects.create_user(
            username="post-editor",
            password="password",
        )
        brand = Brand.objects.create(
            user=user,
            business_name="Logo Brand",
            niche="Fitness",
            logo="content_agent/logos/logo.png",
        )
        post = Post.objects.create(
            brand=brand,
            user=user,
            base_image_url="/media/base.png",
            image_url="/media/final.png",
            image_title="Old text",
            template="none",
            logo_position="bottom_right",
        )
        create_final_image_from_base.return_value = {
            "absolute_path": "/tmp/new-final.png",
            "image_url": "/media/new-final.png",
        }

        rerendered_post = rerender_post_image(
            post,
            {
                "image_title": "",
                "image_subtitle": "",
                "template": "none",
                "primary_color": "#111111",
                "secondary_color": "#222222",
                "tertiary_color": "#333333",
                "text_color": "#FFFFFF",
                "title_font": "inter",
            "subtitle_font": "inter",
                "logo_position": "",
            },
        )

        self.assertEqual(rerendered_post.image_title, "")
        self.assertEqual(rerendered_post.logo_position, "")
        self.assertEqual(render_image_file.call_args.kwargs["logo_file"], None)


class ApprovedPostImageRenderTestCase(TestCase):
    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="local")
    @patch("ai_content_agent.services.render_image_file")
    @patch("ai_content_agent.services.generate_post_image_files")
    def test_render_approved_post_image_uses_reviewed_prompt(
        self,
        generate_post_image_files,
        render_image_file,
    ):
        user = User.objects.create_user(
            username="image-owner",
            password="password",
        )
        brand = Brand.objects.create(
            user=user,
            business_name="Image Brand",
            niche="Fitness",
        )
        post = Post.objects.create(
            brand=brand,
            user=user,
            image_prompt="Reviewed prompt",
            image_title="TEXT",
            template="none",
            primary_color="#111111",
            secondary_color="#222222",
            tertiary_color="#333333",
            text_color="#FFFFFF",
            title_font="inter",
            subtitle_font="inter",
            logo_position="",
            image_format="portrait",
            status=GenerationStatus.PENDING_REVIEW,
        )
        generate_post_image_files.return_value = {
            "base": {
                "image_url": "/media/base.png",
                "absolute_path": "/tmp/base.png",
            },
            "final": {
                "image_url": "/media/final.png",
                "absolute_path": "/tmp/final.png",
            },
        }

        rendered_post = render_approved_post_image(post)

        generate_post_image_files.assert_called_once_with({
            "image_prompt": "Reviewed prompt",
        }, image_format="portrait", content_language="pt-BR")
        render_image_file.assert_called_once()
        self.assertEqual(rendered_post.base_image_url, "/media/base.png")
        self.assertEqual(rendered_post.image_url, "/media/final.png")

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="local")
    @patch("ai_content_agent.services.render_image_file")
    @patch("ai_content_agent.services.create_final_image_from_base")
    @patch("ai_content_agent.services.generate_post_image_files")
    def test_render_approved_post_image_uses_uploaded_base_without_generation(
        self,
        generate_post_image_files,
        create_final_image_from_base,
        render_image_file,
    ):
        user = User.objects.create_user(
            username="uploaded-image-owner",
            password="password",
        )
        brand = Brand.objects.create(
            user=user,
            business_name="Image Brand",
            niche="Fitness",
        )
        post = Post.objects.create(
            brand=brand,
            user=user,
            base_image_url="/media/generated_posts/uploads/user-base.png",
            image_prompt="",
            image_title="TEXT",
            template="none",
            primary_color="#111111",
            secondary_color="#222222",
            tertiary_color="#333333",
            text_color="#FFFFFF",
            title_font="inter",
            subtitle_font="inter",
            logo_position="",
            image_format="portrait",
            status=GenerationStatus.PENDING_REVIEW,
        )
        create_final_image_from_base.return_value = {
            "absolute_path": "/tmp/final.png",
            "image_url": "/media/generated_posts/final.png",
        }

        rendered_post = render_approved_post_image(
            post,
            use_existing_base=True,
        )

        generate_post_image_files.assert_not_called()
        create_final_image_from_base.assert_called_once_with(
            "/media/generated_posts/uploads/user-base.png",
        )
        render_image_file.assert_called_once()
        self.assertEqual(
            rendered_post.base_image_url,
            "/media/generated_posts/uploads/user-base.png",
        )
        self.assertEqual(
            rendered_post.image_url,
            "/media/generated_posts/final.png",
        )

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="local")
    @patch("ai_content_agent.services.render_image_file")
    @patch("ai_content_agent.services.get_image_work_path")
    @patch("ai_content_agent.services.edit_user_post_image_files")
    def test_render_approved_post_image_edits_uploaded_base_when_prompt_exists(
        self,
        edit_user_post_image_files,
        get_image_work_path,
        render_image_file,
    ):
        user = User.objects.create_user(
            username="edited-upload-owner",
            password="password",
        )
        brand = Brand.objects.create(
            user=user,
            business_name="Image Brand",
            niche="Fitness",
            content_language="en-US",
        )
        post = Post.objects.create(
            brand=brand,
            user=user,
            base_image_url="/media/generated_posts/uploads/user-base.png",
            image_prompt="Edit prompt",
            image_title="TEXT",
            template="none",
            primary_color="#111111",
            secondary_color="#222222",
            tertiary_color="#333333",
            text_color="#FFFFFF",
            title_font="inter",
            subtitle_font="inter",
            logo_position="",
            image_format="portrait",
            status=GenerationStatus.PENDING_REVIEW,
        )
        get_image_work_path.return_value = Path("/tmp/source.png")
        edit_user_post_image_files.return_value = {
            "base": {
                "image_url": "/media/generated_posts/edited-base.png",
                "absolute_path": "/tmp/edited-base.png",
            },
            "final": {
                "image_url": "/media/generated_posts/edited-final.png",
                "absolute_path": "/tmp/edited-final.png",
            },
        }

        rendered_post = render_approved_post_image(
            post,
            use_existing_base=True,
        )

        edit_user_post_image_files.assert_called_once_with(
            Path("/tmp/source.png"),
            "Edit prompt",
            image_format="portrait",
            content_language="en-US",
        )
        render_image_file.assert_called_once()
        self.assertEqual(
            rendered_post.base_image_url,
            "/media/generated_posts/edited-base.png",
        )
        self.assertEqual(
            rendered_post.image_url,
            "/media/generated_posts/edited-final.png",
        )


class PostUserImagesTestCase(SimpleTestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.media_root, ignore_errors=True)

    def get_base_data(self, **overrides):
        return {
            "quantity": 1,
            "template": "none",
            "use_templates": False,
            "logo_position": "bottom_right",
            "primary_color": "#111111",
            "secondary_color": "#222222",
            "tertiary_color": "#333333",
            "text_color": "#FFFFFF",
            "title_font": "inter",
            "subtitle_font": "inter",
            "my_images_or_ai": "user",
            "images": [get_test_image("post.gif")],
            **overrides,
        }

    def get_result(self):
        return {
            "caption": "Caption",
            "hashtags": ["#tag"],
            "image_prompt": "Image prompt",
            "image_title": "AI TEXT",
            "image_subtitle": "AI SUBTITLE",
        }

    @override_settings(MEDIA_ROOT="")
    @patch("ai_content_agent.services.render_image_file")
    def test_render_post_content_uses_uploaded_image_as_base(
        self,
        render_image_file,
    ):
        with override_settings(MEDIA_ROOT=self.media_root):
            post_data = render_post_content(
                data=self.get_base_data(),
                idea={"title": "Idea"},
                result=self.get_result(),
                index=1,
            )

        self.assertIn("/media/generated_posts/uploads/user-base-", post_data["base_image_url"])
        self.assertIn("/media/generated_posts/final-", post_data["image_url"])
        self.assertTrue(post_data["base_absolute_path"].endswith(".gif"))
        render_image_file.assert_called_once()


class GeneratePostContentAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="post-creator",
            password="password",
        )
        self.brand = Brand.objects.create(
            user=self.user,
            business_name="Post Brand",
            niche="Fitness",
            primary_color="#111111",
            secondary_color="#222222",
            tertiary_color="#333333",
            text_color="#FFFFFF",
            title_font="inter",
            subtitle_font="inter",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def create_subscription(self, tier):
        plan = Plan.objects.create(
            tier=tier,
            name=tier.title(),
            price_brl_cents=1000,
            price_usd_cents=200,
        )
        return Subscription.objects.create(
            user=self.user,
            plan=plan,
            status=Subscription.Status.ACTIVE,
        )

    def test_generate_posts_rejects_more_than_seven_posts_per_batch(self):
        response = self.client.post(
            reverse("generate-post-content"),
            {
                "brand_id": self.brand.id,
                "business_name": self.brand.business_name,
                "niche": self.brand.niche,
                "objective": "Attract leads",
                "tone": "Friendly",
                "theme": "Summer",
                "quantity": "8",
                "my_images_or_ai": "ai",
                "primary_color": "#111111",
                "secondary_color": "#222222",
                "tertiary_color": "#333333",
                "text_color": "#FFFFFF",
                "title_font": "inter",
                "subtitle_font": "inter",
                "logo_position": "bottom_right",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("quantity", response.data)

    def test_generate_posts_rejects_multiple_posts_for_free_plan(self):
        response = self.client.post(
            reverse("generate-post-content"),
            {
                "brand_id": self.brand.id,
                "business_name": self.brand.business_name,
                "niche": self.brand.niche,
                "objective": "Attract leads",
                "tone": "Friendly",
                "theme": "Summer",
                "quantity": "2",
                "my_images_or_ai": "ai",
                "primary_color": "#111111",
                "secondary_color": "#222222",
                "tertiary_color": "#333333",
                "text_color": "#FFFFFF",
                "title_font": "inter",
                "subtitle_font": "inter",
                "logo_position": "bottom_right",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("posts por geracao", response.data["detail"])

    def test_generate_posts_requires_one_user_image_per_post(self):
        self.create_subscription(Plan.Tier.PLUS)

        response = self.client.post(
            reverse("generate-post-content"),
            {
                "brand_id": self.brand.id,
                "business_name": self.brand.business_name,
                "niche": self.brand.niche,
                "objective": "Attract leads",
                "tone": "Friendly",
                "theme": "Summer",
                "quantity": "2",
                "my_images_or_ai": "user",
                "primary_color": "#111111",
                "secondary_color": "#222222",
                "tertiary_color": "#333333",
                "text_color": "#FFFFFF",
                "title_font": "inter",
            "subtitle_font": "inter",
                "logo_position": "bottom_right",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["expected"], 2)
        self.assertEqual(response.data["received"], 0)

    def test_usage_endpoint_returns_monthly_ai_image_usage(self):
        UsageEvent.objects.create(
            user=self.user,
            kind=UsageEvent.Kind.AI_POST_IMAGE,
            quantity=1,
        )
        UsageEvent.objects.create(
            user=self.user,
            kind=UsageEvent.Kind.USER_POST_IMAGE,
            quantity=2,
        )
        UsageEvent.objects.create(
            user=self.user,
            kind=UsageEvent.Kind.AI_IMAGE_EDIT,
            quantity=1,
        )

        response = self.client.get(reverse("content-agent-usage"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["ai_images"]["used"], 1)
        self.assertEqual(response.data["ai_images"]["limit"], 3)
        self.assertEqual(response.data["ai_images"]["remaining"], 2)
        self.assertEqual(response.data["user_images"]["used"], 2)
        self.assertEqual(response.data["user_images"]["limit"], 5)
        self.assertEqual(response.data["user_images"]["remaining"], 3)
        self.assertEqual(response.data["ai_image_edits"]["used"], 1)
        self.assertEqual(response.data["ai_image_edits"]["limit"], 3)
        self.assertEqual(response.data["ai_image_edits"]["remaining"], 2)

    def test_generate_posts_blocks_ai_images_when_monthly_quota_is_exceeded(self):
        self.create_subscription(Plan.Tier.PLUS)
        UsageEvent.objects.create(
            user=self.user,
            kind=UsageEvent.Kind.AI_POST_IMAGE,
            quantity=14,
        )

        response = self.client.post(
            reverse("generate-post-content"),
            {
                "brand_id": self.brand.id,
                "business_name": self.brand.business_name,
                "niche": self.brand.niche,
                "objective": "Attract leads",
                "tone": "Friendly",
                "theme": "Summer",
                "quantity": "2",
                "my_images_or_ai": "ai",
                "primary_color": "#111111",
                "secondary_color": "#222222",
                "tertiary_color": "#333333",
                "text_color": "#FFFFFF",
                "title_font": "inter",
            "subtitle_font": "inter",
                "logo_position": "bottom_right",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("Limite mensal", response.data["detail"])

    def test_generate_posts_blocks_user_images_when_monthly_quota_is_exceeded(self):
        self.create_subscription(Plan.Tier.PLUS)
        UsageEvent.objects.create(
            user=self.user,
            kind=UsageEvent.Kind.USER_POST_IMAGE,
            quantity=29,
        )

        response = self.client.post(
            reverse("generate-post-content"),
            {
                "brand_id": self.brand.id,
                "business_name": self.brand.business_name,
                "niche": self.brand.niche,
                "objective": "Attract leads",
                "tone": "Friendly",
                "theme": "Summer",
                "quantity": "2",
                "my_images_or_ai": "user",
                "images": [
                    get_test_image("post-1.gif"),
                    get_test_image("post-2.gif"),
                ],
                "primary_color": "#111111",
                "secondary_color": "#222222",
                "tertiary_color": "#333333",
                "text_color": "#FFFFFF",
                "title_font": "inter",
                "subtitle_font": "inter",
                "logo_position": "bottom_right",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("imagens proprias", response.data["detail"])

    @override_settings(CONTENT_AGENT_USE_MOCK_CONTENT=True)
    @patch("ai_content_agent.views.enqueue_post_image_generation")
    def test_generate_posts_returns_review_batch_without_starting_job(
        self,
        enqueue_job,
    ):
        existing_batch = PostBatch.objects.create(
            user=self.user,
            brand=self.brand,
            objective="Attract leads",
            tone="Friendly",
            theme="Existing",
            quantity=1,
            status=GenerationStatus.PENDING_REVIEW,
            progress=100,
        )
        existing_post = Post.objects.create(
            batch=existing_batch,
            brand=self.brand,
            user=self.user,
            caption="Existing caption",
            hashtags=["#tag"],
            image_prompt="Existing prompt",
            image_title="TEXT",
            template="none",
            status=GenerationStatus.PENDING_REVIEW,
            scheduled_date="2026-06-09",
        )

        response = self.client.post(
            reverse("generate-post-content"),
            {
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
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], GenerationStatus.PENDING_REVIEW)
        self.assertEqual(response.data["progress"], 100)
        self.assertEqual(response.data["quantity"], 1)
        self.assertEqual(len(response.data["posts"]), 2)
        self.assertEqual(response.data["posts"][0]["id"], existing_post.id)
        self.assertEqual(
            response.data["posts"][0]["batch_id"],
            existing_batch.id,
        )
        self.assertTrue(response.data["posts"][1]["image_prompt"])
        self.assertEqual(
            response.data["posts"][1]["batch_id"],
            response.data["batch_id"],
        )
        enqueue_job.assert_not_called()

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="local")
    @patch("ai_content_agent.views.enqueue_post_image_generation")
    def test_approve_post_prompts_updates_prompts_and_starts_image_jobs(
        self,
        enqueue_job,
    ):
        batch = PostBatch.objects.create(
            user=self.user,
            brand=self.brand,
            objective="Attract leads",
            tone="Friendly",
            theme="Summer",
            quantity=1,
            status=GenerationStatus.PENDING_REVIEW,
            progress=100,
        )
        other_batch = PostBatch.objects.create(
            user=self.user,
            brand=self.brand,
            objective="Attract leads",
            tone="Friendly",
            theme="Winter",
            quantity=1,
            status=GenerationStatus.PENDING_REVIEW,
            progress=100,
        )
        post = Post.objects.create(
            batch=batch,
            brand=self.brand,
            user=self.user,
            caption="Caption",
            hashtags=["#tag"],
            image_prompt="Old prompt",
            image_title="TEXT",
            template="none",
            primary_color="#111111",
            secondary_color="#222222",
            tertiary_color="#333333",
            text_color="#FFFFFF",
            title_font="inter",
            subtitle_font="inter",
            logo_position="",
            status=GenerationStatus.PENDING_REVIEW,
            scheduled_date="2026-06-09",
        )
        other_post = Post.objects.create(
            batch=other_batch,
            brand=self.brand,
            user=self.user,
            caption="Other caption",
            hashtags=["#tag"],
            image_prompt="Other old prompt",
            image_title="TEXT",
            template="none",
            primary_color="#111111",
            secondary_color="#222222",
            tertiary_color="#333333",
            text_color="#FFFFFF",
            title_font="inter",
            subtitle_font="inter",
            logo_position="",
            status=GenerationStatus.PENDING_REVIEW,
            scheduled_date="2026-06-10",
        )
        response = self.client.post(
            reverse("approve-post-prompts", kwargs={"batch_id": batch.id}),
            {
                "posts": [
                    {
                        "id": post.id,
                        "image_prompt": "Reviewed prompt",
                    },
                    {
                        "id": other_post.id,
                        "image_prompt": "Other reviewed prompt",
                    }
                ]
            },
            format="json",
        )

        post.refresh_from_db()
        other_post.refresh_from_db()
        batch.refresh_from_db()
        other_batch.refresh_from_db()

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["status"], GenerationStatus.PENDING)
        self.assertEqual(post.image_prompt, "Reviewed prompt")
        self.assertEqual(other_post.image_prompt, "Other reviewed prompt")
        self.assertEqual(batch.status, GenerationStatus.PENDING)
        self.assertEqual(other_batch.status, GenerationStatus.PENDING)
        self.assertEqual(len(response.data["jobs"]), 2)
        self.assertEqual(enqueue_job.call_count, 2)
        enqueue_job.assert_any_call(self.user.id, batch.id)
        enqueue_job.assert_any_call(self.user.id, other_batch.id)

    def test_pending_review_endpoint_returns_all_pending_review_posts(self):
        batch = PostBatch.objects.create(
            user=self.user,
            brand=self.brand,
            objective="Attract leads",
            tone="Friendly",
            theme="Summer",
            quantity=1,
            status=GenerationStatus.PENDING_REVIEW,
            progress=100,
            strategy_summary="Review this batch",
        )
        other_batch = PostBatch.objects.create(
            user=self.user,
            brand=self.brand,
            objective="Attract leads",
            tone="Friendly",
            theme="Winter",
            quantity=1,
            status=GenerationStatus.PENDING_REVIEW,
            progress=100,
            strategy_summary="Review this other batch",
        )
        post = Post.objects.create(
            batch=batch,
            brand=self.brand,
            user=self.user,
            caption="Caption",
            hashtags=["#tag"],
            image_prompt="Prompt to review",
            image_title="TEXT",
            template="none",
            status=GenerationStatus.PENDING_REVIEW,
            scheduled_date="2026-06-09",
        )
        other_post = Post.objects.create(
            batch=other_batch,
            brand=self.brand,
            user=self.user,
            caption="Other caption",
            hashtags=["#tag"],
            image_prompt="Other prompt to review",
            image_title="TEXT",
            template="none",
            status=GenerationStatus.PENDING_REVIEW,
            scheduled_date="2026-06-10",
        )

        response = self.client.get(reverse("pending-review-post-batch"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["batch"]["quantity"], 2)
        self.assertEqual(len(response.data["batch"]["posts"]), 2)
        self.assertEqual(response.data["batch"]["posts"][0]["id"], post.id)
        self.assertEqual(
            response.data["batch"]["posts"][0]["batch_id"],
            batch.id,
        )
        self.assertEqual(
            response.data["batch"]["posts"][1]["id"],
            other_post.id,
        )
        self.assertEqual(
            response.data["batch"]["posts"][1]["batch_id"],
            other_batch.id,
        )
        self.assertEqual(
            response.data["batch"]["posts"][0]["image_prompt"],
            "Prompt to review",
        )


class DeletePostAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="delete-owner",
            password="password",
        )
        self.other_user = User.objects.create_user(
            username="delete-other",
            password="password",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_delete_post_removes_only_users_post(self):
        post = Post.objects.create(
            user=self.user,
            caption="Post to delete",
            image_url="/media/final.png",
        )

        response = self.client.delete(
            reverse("delete-post", kwargs={"post_id": post.id})
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Post.objects.filter(id=post.id).exists())

    def test_delete_post_does_not_remove_other_users_post(self):
        post = Post.objects.create(
            user=self.other_user,
            caption="Other user post",
            image_url="/media/final.png",
        )

        response = self.client.delete(
            reverse("delete-post", kwargs={"post_id": post.id})
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Post.objects.filter(id=post.id).exists())

    @override_settings(
        CONTENT_AGENT_STORAGE_BACKEND="firebase",
        FIREBASE_STORAGE_BUCKET="bucket",
    )
    @patch("ai_content_agent.firebase_cleanup.delete_public_file")
    def test_delete_post_removes_firebase_images(self, delete_public_file):
        post = Post.objects.create(
            user=self.user,
            caption="Firebase post",
            base_image_url="https://storage.googleapis.com/bucket/users/1/posts/1/base.png",
            image_url="https://storage.googleapis.com/bucket/users/1/posts/1/final.png",
        )

        response = self.client.delete(
            reverse("delete-post", kwargs={"post_id": post.id})
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Post.objects.filter(id=post.id).exists())
        self.assertEqual(delete_public_file.call_count, 2)
