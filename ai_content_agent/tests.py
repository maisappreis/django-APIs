import shutil
import tempfile
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from .models import Brand
from .services import render_post_content


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
            text_font="inter",
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
                "text_font": "montserrat",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.brand.refresh_from_db()
        self.assertEqual(self.brand.business_name, "New Brand")
        self.assertEqual(self.brand.niche, "Old niche")
        self.assertEqual(self.brand.primary_color, "#006C44")
        self.assertEqual(self.brand.text_font, "montserrat")
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

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="firebase")
    @patch("ai_content_agent.operations.upload_logo_file")
    def test_post_brand_with_logo_uploads_to_firebase_and_saves_url(
        self,
        upload_logo_file,
    ):
        firebase_url = "https://storage.example.com/users/1/brand/logo.gif"
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
                    "text_font": "inter",
                    "logo": get_test_image(),
                    "logo_position": "bottom_right",
                },
                format="multipart",
            )

        self.assertEqual(response.status_code, 201)
        brand = Brand.objects.get(user=self.user, business_name="Logo Brand")
        self.assertTrue(brand.logo)
        self.assertEqual(brand.logo_url, firebase_url)
        self.assertEqual(response.data["logo_url"], firebase_url)
        upload_logo_file.assert_called_once()

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
                "text_font": "inter",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        brand = Brand.objects.get(user=self.user, business_name="No Logo Brand")
        self.assertFalse(brand.logo)
        self.assertEqual(brand.logo_url, "")


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
            "text_font": "inter",
            **overrides,
        }

    def get_result(self):
        return {
            "caption": "Caption",
            "hashtags": ["#tag"],
            "image_prompt": "Image prompt",
            "image_text": "AI TEXT",
        }

    @patch("ai_content_agent.services.render_image_file")
    @patch("ai_content_agent.services.generate_post_image_files")
    def test_render_post_content_uses_blank_image_text_when_disabled(
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

        self.assertEqual(post_data["image_text"], "")
        self.assertEqual(render_image_file.call_args.kwargs["image_text"], "")

    @patch("ai_content_agent.services.render_image_file")
    @patch("ai_content_agent.services.generate_post_image_files")
    def test_render_post_content_uses_user_image_text_when_provided(
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
            data=self.get_base_data(image_text="USER TEXT"),
            idea={"title": "Idea"},
            result=self.get_result(),
            index=1,
        )

        self.assertEqual(post_data["image_text"], "USER TEXT")
        self.assertEqual(
            render_image_file.call_args.kwargs["image_text"],
            "USER TEXT",
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
            "text_font": "inter",
            "my_images_or_ai": "user",
            "images": [get_test_image("post.gif")],
            **overrides,
        }

    def get_result(self):
        return {
            "caption": "Caption",
            "hashtags": ["#tag"],
            "image_prompt": "Image prompt",
            "image_text": "AI TEXT",
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
            text_font="inter",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_generate_posts_requires_one_user_image_per_post(self):
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
                "text_font": "inter",
                "logo_position": "bottom_right",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["expected"], 2)
        self.assertEqual(response.data["received"], 0)
