import shutil
import tempfile
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings

from accounts.models import Plan
from ai_content_agent.models import GenerationStatus, Post, UsageEvent
from ai_content_agent.operations import (
    apply_brand_defaults,
    build_post_visual_settings,
    create_post_batch,
    create_posts_from_generation_result,
    delete_post_generation,
    ensure_ai_image_quota,
    ensure_brand_quota,
    ensure_visual_identity_capture_allowed,
    get_future_scheduled_posts,
    get_brand_by_id_for_user,
    get_monthly_ai_image_usage,
    get_or_create_brand,
    mark_batch_completed,
    mark_batch_failed,
    mark_batch_pending,
    mark_batch_pending_review,
    mark_post_completed,
    prepare_post_download,
    record_ai_image_usage,
    save_brand_reference_images,
    sync_brand_logo,
    update_batch_progress,
    update_brand_manual_identity,
    update_post_draft_prompts,
)
from ai_content_agent.services import (
    _clean_hex_color,
    _get_template_color_kwargs,
    analyze_brand_visual_identity,
    build_post_draft_content,
    create_final_image_from_base,
    generate_post_batch_content,
    generate_post_batch_draft_content,
    generate_post_image_files,
    get_final_image_subtitle,
    get_final_image_title,
    get_image_work_path,
    get_local_media_path,
    get_logo_position_for_template,
    get_post_image_files,
    get_post_logo_file,
    get_remote_image_work_path,
    get_template_name_for_post,
    prepare_uploaded_post_image_files,
    render_image_file,
    rerender_post_image,
    save_uploaded_post_image_file,
)
from ai_content_agent.tests.factories import (
    create_batch,
    create_brand,
    create_post,
    create_subscription,
    create_user,
)


def get_uploaded_image(name="image.gif"):
    return SimpleUploadedFile(
        name,
        (
            b"GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xff\xff\xff,\x00\x00\x00\x00\x01\x00\x01\x00"
            b"\x00\x02\x02D\x01\x00;"
        ),
        content_type="image/gif",
    )


def get_visual_data(**overrides):
    data = {
        "quantity": 2,
        "business_name": "Brand",
        "niche": "Fitness",
        "objective": "Sell",
        "tone": "Friendly",
        "theme": "Summer",
        "template": "rectangle",
        "use_templates": True,
        "logo_position": "bottom_right",
        "primary_color": "#111111",
        "secondary_color": "#222222",
        "tertiary_color": "#333333",
        "text_color": "#FFFFFF",
        "title_font": "inter",
        "subtitle_font": "inter",
        "image_format": "square",
    }
    data.update(overrides)
    return data


def get_post_result(**overrides):
    data = {
        "order": 1,
        "idea": {"title": "Idea"},
        "caption": "Caption",
        "hashtags": ["#tag"],
        "image_prompt": "Prompt",
        "image_title": "TITLE",
        "image_subtitle": "SUBTITLE",
        "base_image_url": "/media/generated_posts/base.png",
        "image_url": "/media/generated_posts/final.png",
        "base_absolute_path": "/tmp/base.png",
        "final_absolute_path": "/tmp/final.png",
        "template": "none",
        "primary_color": "#111111",
        "secondary_color": "#222222",
        "tertiary_color": "#333333",
        "text_color": "#FFFFFF",
        "title_font": "inter",
        "subtitle_font": "inter",
        "logo_position": "bottom_right",
    }
    data.update(overrides)
    return data


class OperationsTest(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.media_root, ignore_errors=True)

    def test_get_or_create_brand_reuses_latest_matching_brand(self):
        user = create_user()
        existing = create_brand(user=user, business_name="Brand", niche="Fitness")

        brand = get_or_create_brand(user, "Brand", "Fitness")
        new_brand = get_or_create_brand(user, "New", "Food")

        self.assertEqual(brand, existing)
        self.assertEqual(new_brand.business_name, "New")
        self.assertEqual(get_brand_by_id_for_user(user, ""), None)
        self.assertEqual(get_brand_by_id_for_user(user, existing.id), existing)

    def test_get_future_scheduled_posts_filters_by_date_range(self):
        user = create_user()
        brand = create_brand(user=user)
        inside = create_post(
            user=user,
            brand=brand,
            scheduled_date=date(2026, 6, 20),
            status=GenerationStatus.COMPLETED,
        )
        create_post(
            user=user,
            brand=brand,
            scheduled_date=date(2026, 7, 20),
            status=GenerationStatus.COMPLETED,
        )
        create_post(
            user=user,
            brand=brand,
            scheduled_date=date(2026, 6, 20),
            status=GenerationStatus.PENDING,
        )

        start_date, posts = get_future_scheduled_posts(
            user,
            start_date=date(2026, 6, 14),
            end_date=date(2026, 7, 17),
        )

        self.assertEqual(start_date, date(2026, 6, 14))
        self.assertEqual(list(posts), [inside])

    def test_brand_quota_and_visual_identity_rules(self):
        user = create_user()
        brand = create_brand(user=user, business_name="Brand", niche="Fitness")

        self.assertEqual(ensure_brand_quota(user, "Brand", "Fitness"), brand)

        with self.assertRaises(ValueError):
            ensure_brand_quota(user, "Other", "Food")

        with self.assertRaises(ValueError):
            ensure_visual_identity_capture_allowed(user)

        plus_user = create_user()
        create_subscription(plus_user, tier=Plan.Tier.PLUS)
        self.assertIsNone(ensure_visual_identity_capture_allowed(plus_user))

    def test_update_brand_manual_identity_and_apply_defaults(self):
        brand = create_brand()

        update_brand_manual_identity(brand, {
            "business_name": "Updated",
            "primary_color": "#ABCDEF",
            "content_language": "en-US",
        })
        data = {}
        apply_brand_defaults(data, brand, request_data={"primary_color": "#000000"})

        brand.refresh_from_db()
        self.assertEqual(brand.business_name, "Updated")
        self.assertEqual(brand.primary_color, "#ABCDEF")
        self.assertEqual(brand.content_language, "en-US")
        self.assertNotIn("primary_color", data)
        self.assertEqual(data["secondary_color"], brand.secondary_color)
        self.assertEqual(data["brand_visual_identity"], brand.visual_identity_prompt)
        self.assertEqual(data["content_language"], "en-US")

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="firebase")
    @patch("ai_content_agent.operations.upload_brand_reference_file")
    def test_save_brand_reference_images_uploads_to_firebase(self, upload_reference):
        upload_reference.side_effect = [
            "https://cdn.test/ref1.gif",
            "https://cdn.test/ref2.gif",
        ]
        user = create_user()
        brand = create_brand(user=user)

        with override_settings(MEDIA_ROOT=self.media_root):
            save_brand_reference_images(
                brand,
                {
                    "reference_image_1": get_uploaded_image("ref1.gif"),
                    "reference_image_2": get_uploaded_image("ref2.gif"),
                },
                user,
            )

        brand.refresh_from_db()
        self.assertEqual(brand.reference_image_1_url, "https://cdn.test/ref1.gif")
        self.assertEqual(brand.reference_image_2_url, "https://cdn.test/ref2.gif")
        self.assertEqual(upload_reference.call_count, 2)

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="firebase")
    @patch("ai_content_agent.operations.delete_firebase_file")
    @patch("ai_content_agent.operations.upload_brand_reference_file")
    def test_reference_upload_failure_preserves_previous_urls(
        self, upload_reference, delete_file
    ):
        user = create_user()
        brand = create_brand(
            user=user,
            reference_image_1_url="https://cdn.test/old-1.png",
            reference_image_2_url="https://cdn.test/old-2.png",
        )
        upload_reference.side_effect = [
            "https://cdn.test/new-1.png",
            RuntimeError("upload failed"),
        ]

        with override_settings(MEDIA_ROOT=self.media_root):
            with self.assertRaisesMessage(RuntimeError, "upload failed"):
                save_brand_reference_images(
                    brand,
                    {
                        "reference_image_1": get_uploaded_image("ref1.gif"),
                        "reference_image_2": get_uploaded_image("ref2.gif"),
                    },
                    user,
                )

        brand.refresh_from_db()
        self.assertEqual(
            brand.reference_image_1_url,
            "https://cdn.test/old-1.png",
        )
        self.assertEqual(
            brand.reference_image_2_url,
            "https://cdn.test/old-2.png",
        )
        delete_file.assert_called_once_with("https://cdn.test/new-1.png")

    def test_create_batch_usage_quota_progress_and_markers(self):
        user = create_user()
        brand = create_brand(user=user)
        batch = create_post_batch(user, brand, get_visual_data(quantity=3))

        self.assertEqual(batch.quantity, 3)
        self.assertEqual(get_monthly_ai_image_usage(user)["used"], 0)
        self.assertEqual(ensure_ai_image_quota(user, 1)["remaining"], 2)
        with self.assertRaises(ValueError):
            ensure_ai_image_quota(user, 3)

        self.assertIsNone(record_ai_image_usage(user, quantity=0))
        event = record_ai_image_usage(user, quantity=1, batch=batch)
        self.assertEqual(event.kind, UsageEvent.Kind.AI_POST_IMAGE)

        update_batch_progress(batch, 150)
        batch.refresh_from_db()
        self.assertEqual(batch.progress, 100)

        mark_batch_pending(batch)
        batch.refresh_from_db()
        self.assertEqual(batch.status, GenerationStatus.PENDING)
        self.assertEqual(batch.progress, 0)

        mark_batch_pending_review(batch, "Review")
        batch.refresh_from_db()
        self.assertEqual(batch.status, GenerationStatus.PENDING_REVIEW)
        self.assertEqual(batch.strategy_summary, "Review")

        mark_batch_completed(batch, "Done")
        batch.refresh_from_db()
        self.assertEqual(batch.status, GenerationStatus.COMPLETED)

        mark_batch_failed(batch, RuntimeError("boom"))
        batch.refresh_from_db()
        self.assertEqual(batch.status, GenerationStatus.FAILED)
        self.assertEqual(batch.error_message, "boom")

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="local")
    def test_sync_brand_logo_reuses_existing_logo_when_no_upload(self):
        user = create_user()
        brand = create_brand(user=user)
        with override_settings(MEDIA_ROOT=self.media_root):
            brand.logo = get_uploaded_image("logo.gif")
            brand.save()
            data = {}
            sync_brand_logo(brand, data, user)

        self.assertTrue(data["logo"].endswith("logo.gif"))

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="firebase")
    @patch("ai_content_agent.operations.upload_logo_file", return_value="https://cdn.test/logo.gif")
    def test_sync_brand_logo_uploads_new_logo(self, upload_logo_file):
        user = create_user()
        brand = create_brand(user=user)
        data = {"logo": get_uploaded_image("logo.gif")}

        with override_settings(MEDIA_ROOT=self.media_root):
            sync_brand_logo(brand, data, user)

        brand.refresh_from_db()
        self.assertEqual(brand.logo_url, "https://cdn.test/logo.gif")
        upload_logo_file.assert_called_once()

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="firebase")
    @patch("ai_content_agent.operations.delete_replaced_firebase_file")
    @patch(
        "ai_content_agent.operations.upload_logo_file",
        side_effect=RuntimeError("upload failed"),
    )
    def test_logo_upload_failure_preserves_previous_url(
        self, _upload_logo_file, delete_replaced
    ):
        user = create_user()
        brand = create_brand(
            user=user,
            logo_url="https://cdn.test/old-logo.png",
        )

        with override_settings(MEDIA_ROOT=self.media_root):
            with self.assertRaisesMessage(RuntimeError, "upload failed"):
                sync_brand_logo(
                    brand,
                    {"logo": get_uploaded_image("logo.gif")},
                    user,
                )

        brand.refresh_from_db()
        self.assertEqual(brand.logo_url, "https://cdn.test/old-logo.png")
        delete_replaced.assert_not_called()

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="firebase")
    @patch("ai_content_agent.operations.upload_logo_file")
    @patch("ai_content_agent.firebase_cleanup.delete_firebase_file")
    def test_sync_brand_logo_does_not_delete_shared_legacy_logo(
        self,
        delete_file,
        upload_logo_file,
    ):
        user = create_user()
        legacy_url = "https://cdn.test/users/1/brand/logo.png"
        brand = create_brand(user=user, logo_url=legacy_url)
        create_brand(
            user=user,
            business_name="Second brand",
            logo_url=legacy_url,
        )
        upload_logo_file.return_value = (
            f"https://cdn.test/users/{user.id}/brands/{brand.id}/logo.gif"
        )

        with override_settings(MEDIA_ROOT=self.media_root):
            sync_brand_logo(
                brand,
                {"logo": get_uploaded_image("logo.gif")},
                user,
            )

        delete_file.assert_not_called()
        upload_logo_file.assert_called_once_with(
            local_path=upload_logo_file.call_args.kwargs["local_path"],
            user_id=user.id,
            brand_id=brand.id,
        )

    @patch("ai_content_agent.signals.delete_firebase_file")
    def test_deleting_brand_removes_persistent_assets(self, delete_file):
        brand = create_brand(
            logo_url="https://cdn.test/logo.png",
            reference_image_1_url="https://cdn.test/ref1.png",
            reference_image_2_url="https://cdn.test/ref2.png",
        )

        brand.delete()

        self.assertEqual(delete_file.call_count, 3)

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="firebase")
    @patch("ai_content_agent.operations.upload_generated_post_file")
    def test_create_posts_from_generation_result_uploads_generated_files(self, upload_file):
        upload_file.side_effect = [
            "https://cdn.test/base.png",
            "https://cdn.test/final.png",
        ]
        user = create_user()
        brand = create_brand(user=user)
        batch = create_batch(user=user, brand=brand)

        posts = create_posts_from_generation_result(
            user,
            brand,
            batch,
            data={},
            result={"posts": [get_post_result(order=1)]},
        )

        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].status, GenerationStatus.COMPLETED)
        self.assertEqual(posts[0].base_image_url, "https://cdn.test/base.png")
        self.assertEqual(posts[0].image_url, "https://cdn.test/final.png")

    def test_update_prompts_and_post_marker(self):
        user = create_user()
        brand = create_brand(user=user)
        batch = create_batch(user=user, brand=brand)
        post = create_post(
            user=user,
            brand=brand,
            batch=batch,
            status=GenerationStatus.PENDING_REVIEW,
        )
        ignored_post = create_post(
            user=user,
            brand=brand,
            batch=batch,
            status=GenerationStatus.COMPLETED,
        )

        update_post_draft_prompts(batch, [
            {"id": post.id, "image_prompt": "Reviewed prompt"},
            {"id": ignored_post.id, "image_prompt": "Should not change"},
            {"id": 999, "image_prompt": "Missing"},
        ])
        mark_post_completed(post)

        post.refresh_from_db()
        ignored_post.refresh_from_db()
        self.assertEqual(post.image_prompt, "Reviewed prompt")
        self.assertEqual(post.status, GenerationStatus.COMPLETED)
        self.assertEqual(ignored_post.image_prompt, "Prompt")

    def test_build_post_visual_settings_can_remove_text(self):
        post = create_post(image_title="Old", image_subtitle="Sub")

        settings = build_post_visual_settings(
            post,
            {
                "has_text_image": False,
                "primary_color": "#000000",
            },
        )

        self.assertEqual(settings["image_title"], "")
        self.assertEqual(settings["image_subtitle"], "")
        self.assertEqual(settings["primary_color"], "#000000")

    def test_prepare_post_download_local_and_remote(self):
        media_root = Path(self.media_root)
        local_file = media_root / "generated_posts" / "final.png"
        local_file.parent.mkdir(parents=True)
        local_file.write_bytes(b"image")
        local_post = create_post(image_url="/media/generated_posts/final.png")

        with override_settings(MEDIA_ROOT=self.media_root):
            local_download = prepare_post_download(local_post)

        self.assertEqual(local_download["local_path"], local_file)
        self.assertEqual(local_download["content_type"], "image/png")

        remote_response = Mock()
        remote_response.content = b"remote"
        remote_response.headers = {"content-type": "image/jpeg"}
        remote_post = create_post(image_url="https://cdn.test/final.jpg")
        with patch("ai_content_agent.operations.httpx.get", return_value=remote_response):
            remote_download = prepare_post_download(remote_post)

        remote_response.raise_for_status.assert_called_once()
        self.assertEqual(remote_download["content"], b"remote")
        self.assertEqual(remote_download["content_type"], "image/jpeg")

    def test_prepare_post_download_raises_when_local_file_missing(self):
        post = create_post(image_url="/media/generated_posts/missing.png")

        with override_settings(MEDIA_ROOT=self.media_root):
            with self.assertRaises(FileNotFoundError):
                prepare_post_download(post)

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="firebase")
    @patch("ai_content_agent.operations.delete_firebase_file")
    def test_delete_post_generation_collects_storage_errors(self, delete_firebase_file):
        delete_firebase_file.side_effect = [False, True]
        post = create_post(
            base_image_url="https://cdn.test/base.png",
            image_url="https://cdn.test/final.png",
        )

        errors = delete_post_generation(post)

        self.assertEqual(len(errors), 1)
        self.assertFalse(Post.objects.filter(id=post.id).exists())


class ServicesTest(SimpleTestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.media_root, ignore_errors=True)

    def test_template_and_text_helpers(self):
        self.assertEqual(get_logo_position_for_template("none", "top_left"), "top_left")
        self.assertEqual(get_logo_position_for_template("rectangle", "top_left"), "top_right")
        self.assertEqual(get_logo_position_for_template("none", ""), "")
        self.assertEqual(get_template_name_for_post(get_visual_data(quantity=1), 1), "rectangle")
        self.assertEqual(
            get_template_name_for_post(get_visual_data(quantity=2, use_templates=False), 2),
            "none",
        )
        self.assertEqual(
            _get_template_color_kwargs(
                "rectangle",
                {"primary_color": "#111111", "text_color": "#FFFFFF"},
            ),
            {"primary_color": "#111111", "text_color": "#FFFFFF"},
        )
        self.assertEqual(get_final_image_title({"has_text_image": False}, {"image_title": "AI"}), "")
        self.assertEqual(get_final_image_title({"image_title": "User"}, {"image_title": "AI"}), "User")
        self.assertEqual(get_final_image_subtitle({}, {"image_subtitle": "AI"}), "AI")
        self.assertEqual(_clean_hex_color("#abc123", "#000000"), "#ABC123")
        self.assertEqual(_clean_hex_color("bad", "#000000"), "#000000")

    @override_settings(CONTENT_AGENT_USE_MOCK_IMAGES=True)
    @patch("ai_content_agent.services.mock_generate_image_files", return_value={"base": {}, "final": {}})
    def test_generate_post_image_files_uses_mock_when_enabled(self, mock_files):
        self.assertEqual(generate_post_image_files({"image_prompt": "Prompt"}), {"base": {}, "final": {}})
        mock_files.assert_called_once()

    @override_settings(CONTENT_AGENT_USE_MOCK_IMAGES=False)
    @patch("ai_content_agent.services.generate_image_files", return_value={"base": {}, "final": {}})
    def test_generate_post_image_files_uses_ai_client_when_mock_disabled(self, generate):
        generate_post_image_files({"image_prompt": "Prompt"}, image_format="portrait")

        generate.assert_called_once_with(
            "Prompt",
            image_format="portrait",
            content_language="pt-BR",
        )

    def test_uploaded_image_file_helpers(self):
        with override_settings(MEDIA_ROOT=self.media_root):
            image_files = prepare_uploaded_post_image_files([get_uploaded_image()])

        self.assertEqual(len(image_files), 1)
        self.assertTrue(Path(image_files[0]["base"]["absolute_path"]).exists())
        self.assertTrue(Path(image_files[0]["final"]["absolute_path"]).exists())

    @patch("ai_content_agent.services.save_uploaded_post_image_file", return_value="uploaded")
    @patch("ai_content_agent.services.generate_post_image_files", return_value="generated")
    def test_get_post_image_files_chooses_prepared_user_or_generated(
        self,
        generate,
        save_uploaded,
    ):
        self.assertEqual(
            get_post_image_files({"image_files": ["prepared"]}, {}, 1),
            "prepared",
        )
        self.assertEqual(
            get_post_image_files({"my_images_or_ai": "user", "images": ["upload"]}, {}, 1),
            "uploaded",
        )
        self.assertEqual(get_post_image_files({"image_format": "portrait"}, {}, 1), "generated")
        save_uploaded.assert_called_once_with("upload")
        generate.assert_called_once_with(
            {},
            image_format="portrait",
            content_language="pt-BR",
        )

    @patch("ai_content_agent.services.apply_logo_to_image")
    @patch("ai_content_agent.services.apply_center_text_to_image")
    def test_render_image_file_without_template_applies_text_and_logo(self, apply_text, apply_logo):
        render_image_file(
            image_path="/tmp/final.png",
            template_name="none",
            image_title="TITLE",
            image_subtitle="SUBTITLE",
            logo_file="/tmp/logo.png",
            logo_position="bottom_left",
        )

        apply_text.assert_called_once()
        apply_logo.assert_called_once_with(
            image_path="/tmp/final.png",
            logo_file="/tmp/logo.png",
            position="bottom_left",
        )

    def test_render_image_file_with_template_calls_renderer(self):
        renderer = Mock()

        with patch.dict("ai_content_agent.services.TEMPLATE_RENDERERS", {"rectangle": renderer}):
            render_image_file(
                image_path="/tmp/final.png",
                template_name="rectangle",
                image_title="TITLE",
                logo_position="bottom_right",
                primary_color="#111111",
                text_color="#FFFFFF",
            )

        renderer.assert_called_once()
        self.assertEqual(renderer.call_args.kwargs["logo_position"], "top_right")
        self.assertEqual(renderer.call_args.kwargs["primary_color"], "#111111")

    def test_build_post_draft_content_uses_visual_defaults(self):
        draft = build_post_draft_content(
            get_visual_data(quantity=1),
            {"title": "Idea"},
            get_post_result(),
            1,
        )

        self.assertEqual(draft["template"], "rectangle")
        self.assertEqual(draft["base_image_url"], "")
        self.assertEqual(draft["image_title"], "TITLE")

    def test_local_and_remote_image_work_paths(self):
        local_path = Path(self.media_root) / "generated_posts" / "base.png"
        local_path.parent.mkdir(parents=True)
        local_path.write_bytes(b"base")

        with override_settings(MEDIA_ROOT=self.media_root):
            self.assertEqual(
                get_local_media_path("/media/generated_posts/base.png"),
                local_path,
            )
            self.assertEqual(
                get_image_work_path("/media/generated_posts/base.png"),
                local_path,
            )
            with self.assertRaises(ValueError):
                get_local_media_path("https://cdn.test/base.png")

        response = Mock(content=b"remote")
        with override_settings(MEDIA_ROOT=self.media_root):
            with patch("ai_content_agent.services.httpx.get", return_value=response):
                remote_path = get_remote_image_work_path("https://cdn.test/base.png")

        response.raise_for_status.assert_called_once()
        self.assertTrue(remote_path.exists())
        self.assertEqual(remote_path.read_bytes(), b"remote")

    @patch("ai_content_agent.services.uuid4", return_value="fixed-id")
    def test_create_final_image_from_base_copies_existing_base(self, _uuid):
        base_path = Path(self.media_root) / "generated_posts" / "base.png"
        base_path.parent.mkdir(parents=True)
        base_path.write_bytes(b"base")

        with override_settings(MEDIA_ROOT=self.media_root):
            final_data = create_final_image_from_base("/media/generated_posts/base.png")

        self.assertEqual(final_data["image_path"], "generated_posts/final-fixed-id.png")
        self.assertTrue(Path(final_data["absolute_path"]).exists())

    def test_create_final_image_from_base_raises_when_missing(self):
        with override_settings(MEDIA_ROOT=self.media_root):
            with self.assertRaises(ValueError):
                create_final_image_from_base("/media/generated_posts/missing.png")

    def test_get_post_logo_file_returns_logo_path_or_none(self):
        post = SimpleNamespace(brand=None)
        self.assertIsNone(get_post_logo_file(post))

        logo = SimpleNamespace(path="/tmp/logo.png")
        post = SimpleNamespace(brand=SimpleNamespace(logo=logo))
        self.assertEqual(get_post_logo_file(post), "/tmp/logo.png")

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="firebase")
    @patch("ai_content_agent.services.get_remote_image_work_path")
    def test_get_post_logo_file_downloads_persistent_logo(self, get_work_path):
        get_work_path.return_value = Path("/tmp/remote-logo.png")
        post = SimpleNamespace(
            brand=SimpleNamespace(
                logo=None,
                logo_url="https://cdn.test/users/1/brands/2/logo.png",
            )
        )

        self.assertEqual(
            get_post_logo_file(post),
            str(Path("/tmp/remote-logo.png")),
        )
        get_work_path.assert_called_once_with(
            post.brand.logo_url,
            asset_group="logos",
        )

    @override_settings(CONTENT_AGENT_USE_MOCK_CONTENT=False)
    @patch("ai_content_agent.services.build_posts_from_plan_prompt", return_value="content prompt")
    @patch("ai_content_agent.services.build_post_plan_prompt", return_value="plan prompt")
    @patch("ai_content_agent.services.generate_structured_content")
    def test_generate_post_batch_draft_content_uses_ai_clients(
        self,
        generate_structured_content,
        build_plan_prompt,
        build_content_prompt,
    ):
        generate_structured_content.side_effect = [
            {
                "strategy_summary": "Strategy",
                "posts": [{"title": "Idea"}],
            },
            {
                "posts": [get_post_result(order=1)],
            },
        ]

        result = generate_post_batch_draft_content(get_visual_data(quantity=1))

        self.assertEqual(result["strategy_summary"], "Strategy")
        self.assertEqual(result["posts"][0]["order"], 1)
        build_plan_prompt.assert_called_once()
        build_content_prompt.assert_called_once()

    @override_settings(CONTENT_AGENT_USE_MOCK_CONTENT=False)
    @patch("ai_content_agent.services.generate_structured_content")
    def test_generate_post_batch_draft_content_validates_counts_and_order(self, generate):
        idea = {
            "title": "Idea",
            "theme": "Summer",
            "objective": "Sell",
            "format": "educativo",
            "angle": "Angle",
            "visual_direction": "Visual",
        }
        generate.return_value = {"strategy_summary": "Strategy", "posts": []}

        with self.assertRaises(ValueError):
            generate_post_batch_draft_content(get_visual_data(quantity=1))

        generate.side_effect = [
            {"strategy_summary": "Strategy", "posts": [idea]},
            {"posts": []},
        ]
        with self.assertRaises(ValueError):
            generate_post_batch_draft_content(get_visual_data(quantity=1))

        generate.side_effect = [
            {"strategy_summary": "Strategy", "posts": [idea]},
            {"posts": [get_post_result(order=2)]},
        ]
        with self.assertRaises(ValueError):
            generate_post_batch_draft_content(get_visual_data(quantity=1))

    @patch("ai_content_agent.services.render_post_content", return_value={"order": 1})
    @patch("ai_content_agent.services.generate_post_batch_draft_content")
    def test_generate_post_batch_content_renders_each_draft(self, draft_content, render):
        draft_content.return_value = {
            "quantity": 1,
            "strategy_summary": "Strategy",
            "posts": [
                {
                    "order": 1,
                    "idea": {"title": "Idea"},
                }
            ],
        }

        result = generate_post_batch_content(get_visual_data(quantity=1))

        self.assertEqual(result["posts"], [{"order": 1}])
        render.assert_called_once()


class DatabaseServicesTest(TestCase):
    @patch("ai_content_agent.services.generate_brand_visual_identity")
    def test_analyze_brand_visual_identity_updates_brand_with_clean_colors(self, generate):
        brand = create_brand()
        brand.reference_image_1 = "content_agent/brand_references/ref.png"
        generate.return_value = {
            "visual_identity_summary": "Summary",
            "visual_identity_prompt": "Prompt",
            "primary_color": "#abc123",
            "secondary_color": "bad",
            "tertiary_color": "#123456",
            "text_color": "#ffffff",
            "title_font": "Very Long Font Name",
            "subtitle_font": "Subtitle Font",
        }

        analyzed = analyze_brand_visual_identity(brand)

        self.assertEqual(analyzed.visual_identity_summary, "Summary")
        self.assertEqual(analyzed.primary_color, "#ABC123")
        self.assertEqual(analyzed.secondary_color, "#222222")

    def test_analyze_brand_visual_identity_requires_reference_image(self):
        with self.assertRaises(ValueError):
            analyze_brand_visual_identity(create_brand())

    @override_settings(CONTENT_AGENT_STORAGE_BACKEND="firebase")
    @patch("ai_content_agent.services.upload_generated_post_file")
    @patch("ai_content_agent.services.render_image_file")
    @patch("ai_content_agent.services.create_final_image_from_base")
    def test_rerender_post_image_uploads_when_firebase_enabled(
        self,
        create_final,
        render,
        upload,
    ):
        post = create_post()
        create_final.return_value = {
            "absolute_path": "/tmp/final.png",
            "image_url": "/media/generated_posts/final.png",
        }
        upload.return_value = "https://cdn.test/final.png"

        rerendered = rerender_post_image(
            post,
            {
                "template": "none",
                "image_title": "New",
                "image_subtitle": "",
                "primary_color": "#000000",
                "secondary_color": "#111111",
                "tertiary_color": "#222222",
                "text_color": "#FFFFFF",
                "title_font": "",
                "subtitle_font": "",
                "logo_position": "",
            },
        )

        self.assertEqual(rerendered.image_title, "New")
        self.assertEqual(rerendered.image_url, "https://cdn.test/final.png")
        render.assert_called_once()
        upload.assert_called_once()


class JobsTest(TestCase):
    def test_generate_post_review_batch_updates_progress_and_marks_review(self):
        user = create_user()
        brand = create_brand(user=user)
        batch = create_batch(user=user, brand=brand)
        result = {
            "strategy_summary": "Strategy",
            "posts": [get_post_result(order=1)],
        }

        with patch("ai_content_agent.jobs.generate_post_batch_draft_content", return_value=result):
            with patch("ai_content_agent.jobs.create_post_drafts_from_generation_result") as create_drafts:
                from ai_content_agent.jobs import generate_post_review_batch

                generate_post_review_batch(user, brand, batch, get_visual_data(quantity=1))

        batch.refresh_from_db()
        self.assertEqual(batch.status, GenerationStatus.PENDING_REVIEW)
        self.assertEqual(batch.progress, 100)
        create_drafts.assert_called_once()

    @patch("ai_content_agent.jobs.render_approved_post_image")
    @patch("ai_content_agent.jobs.create_post_drafts_from_generation_result")
    @patch("ai_content_agent.jobs.generate_post_batch_draft_content")
    def test_user_images_skip_prompt_review_and_complete_batch(
        self, generate_draft, create_drafts, render_image
    ):
        user = create_user()
        brand = create_brand(user=user)
        batch = create_batch(user=user, brand=brand, image_source="user")
        post = create_post(
            user=user,
            brand=brand,
            batch=batch,
            status=GenerationStatus.PENDING_REVIEW,
        )
        result = {
            "strategy_summary": "Strategy",
            "posts": [get_post_result(order=1)],
        }
        generate_draft.return_value = result
        create_drafts.return_value = [post]

        from ai_content_agent.jobs import generate_post_review_batch

        generate_post_review_batch(user, brand, batch, get_visual_data(quantity=1))

        batch.refresh_from_db()
        post.refresh_from_db()
        self.assertEqual(result["posts"][0]["image_prompt"], "")
        self.assertEqual(batch.status, GenerationStatus.COMPLETED)
        self.assertEqual(post.status, GenerationStatus.COMPLETED)
        render_image.assert_called_once_with(post, use_existing_base=True)

    @patch("ai_content_agent.jobs.generate_post_review_batch")
    def test_run_post_generation_job_success_and_failure(self, generate_review):
        user = create_user()
        brand = create_brand(user=user)
        batch = create_batch(user=user, brand=brand)

        from ai_content_agent.jobs import run_post_generation_job

        run_post_generation_job(user.id, brand.id, batch.id, {})
        generate_review.assert_called_once()

        generate_review.side_effect = RuntimeError("boom")
        run_post_generation_job(user.id, brand.id, batch.id, {})
        batch.refresh_from_db()
        self.assertEqual(batch.status, GenerationStatus.FAILED)
        self.assertEqual(batch.error_message, "boom")

        run_post_generation_job(user.id, brand.id, 999, {})

    @patch("ai_content_agent.jobs.render_approved_post_image")
    def test_run_post_image_generation_job_completes_ai_batch(self, render):
        user = create_user()
        brand = create_brand(user=user)
        batch = create_batch(
            user=user,
            brand=brand,
            image_source="ai",
            strategy_summary="Strategy",
        )
        post = create_post(
            user=user,
            brand=brand,
            batch=batch,
            status=GenerationStatus.PENDING,
        )

        from ai_content_agent.jobs import run_post_image_generation_job

        run_post_image_generation_job(user.id, batch.id)

        post.refresh_from_db()
        batch.refresh_from_db()
        self.assertEqual(post.status, GenerationStatus.COMPLETED)
        self.assertEqual(batch.status, GenerationStatus.COMPLETED)
        self.assertEqual(batch.progress, 100)
        self.assertEqual(UsageEvent.objects.filter(user=user).count(), 1)
        render.assert_called_once_with(post, use_existing_base=False)

    @patch("ai_content_agent.jobs.render_approved_post_image")
    def test_run_post_image_generation_job_uses_existing_base_for_user_batch(self, render):
        user = create_user()
        brand = create_brand(user=user)
        batch = create_batch(user=user, brand=brand, image_source="user")
        post = create_post(user=user, brand=brand, batch=batch)

        from ai_content_agent.jobs import run_post_image_generation_job

        run_post_image_generation_job(user.id, batch.id)

        render.assert_called_once_with(post, use_existing_base=True)

    def test_run_post_image_generation_job_marks_failed_when_no_posts(self):
        user = create_user()
        brand = create_brand(user=user)
        batch = create_batch(user=user, brand=brand)

        from ai_content_agent.jobs import run_post_image_generation_job

        run_post_image_generation_job(user.id, batch.id)

        batch.refresh_from_db()
        self.assertEqual(batch.status, GenerationStatus.FAILED)
        self.assertIn("No posts found", batch.error_message)

        run_post_image_generation_job(user.id, 999)
