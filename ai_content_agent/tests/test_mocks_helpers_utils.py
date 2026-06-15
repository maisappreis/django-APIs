import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings
from PIL import Image, ImageDraw, ImageFont

from ai_content_agent.helpers import _hex_to_rgba as helper_hex_to_rgba
from ai_content_agent.helpers import _paste_logo
from ai_content_agent.mocks import (
    _build_generated_image_data,
    _mock_hashtag,
    _mock_image_title,
    _mock_post_format,
    mock_generate_batch_content,
    mock_generate_image_files,
    mock_generate_post_plan,
)
from ai_content_agent.utils import (
    _get_font_candidate_paths,
    _get_font_key,
    _get_logo_coordinates,
    _hex_to_rgba,
    _normalize_font_name,
    _resize_logo,
    _wrap_text,
    apply_center_text_to_image,
    apply_logo_to_image,
)


class MocksTest(SimpleTestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.media_root, ignore_errors=True)

    @override_settings(MEDIA_ROOT="/tmp/media", MEDIA_URL="/media/")
    def test_build_generated_image_data_normalizes_path(self):
        data = _build_generated_image_data(Path("generated_posts") / "file.png")

        self.assertEqual(data["image_path"], "generated_posts/file.png")
        self.assertEqual(data["image_url"], "/media/generated_posts/file.png")
        self.assertTrue(data["absolute_path"].endswith("generated_posts\\file.png") or data["absolute_path"].endswith("generated_posts/file.png"))

    def test_mock_post_plan_and_content_are_deterministic(self):
        data = {
            "quantity": 2,
            "business_name": "Brand",
            "niche": "Dental Clinic",
            "objective": "Sell",
            "tone": "Friendly",
            "theme": "Summer",
        }
        plan = mock_generate_post_plan(data)
        content = mock_generate_batch_content(data, plan["posts"])

        self.assertEqual(len(plan["posts"]), 2)
        self.assertEqual(plan["posts"][0]["format"], "educativo")
        self.assertEqual(content["posts"][0]["order"], 1)
        self.assertIn("#dentalclinic", content["posts"][0]["hashtags"])
        self.assertEqual(_mock_post_format(8), "educativo")
        self.assertEqual(_mock_image_title(8), "COMECE HOJE")
        self.assertEqual(_mock_hashtag("!!!"), "#conteudo")

    @override_settings(MEDIA_URL="/media/")
    @patch("ai_content_agent.mocks.copyfile")
    @patch("ai_content_agent.mocks.uuid4")
    def test_mock_generate_image_files_copies_base_and_final(self, uuid4_mock, copyfile):
        uuid4_mock.return_value = "fixed-id"

        with override_settings(MEDIA_ROOT=self.media_root):
            result = mock_generate_image_files()

        self.assertIn("base-fixed-id.png", result["base"]["image_path"])
        self.assertIn("final-fixed-id.png", result["final"]["image_path"])
        self.assertEqual(copyfile.call_count, 2)


class HelpersAndUtilsTest(SimpleTestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_image(self, name, size=(100, 100), color=(10, 20, 30, 255)):
        path = self.temp_dir / name
        Image.new("RGBA", size, color).save(path)
        return path

    def test_hex_to_rgba_helpers(self):
        self.assertEqual(helper_hex_to_rgba("#112233", alpha=128), (17, 34, 51, 128))
        self.assertEqual(_hex_to_rgba("#FFFFFF"), (255, 255, 255, 255))
        self.assertEqual(_hex_to_rgba(None), (255, 255, 255, 255))

    def test_logo_coordinates_cover_known_and_default_positions(self):
        base = Image.new("RGBA", (100, 80))
        logo = Image.new("RGBA", (10, 8))

        self.assertEqual(_get_logo_coordinates(base, logo, "top_left"), (4, 4))
        self.assertEqual(_get_logo_coordinates(base, logo, "top_center"), (45, 4))
        self.assertEqual(_get_logo_coordinates(base, logo, "bottom_center"), (45, 68))
        self.assertEqual(_get_logo_coordinates(base, logo, "unknown"), (86, 68))

    def test_resize_logo_only_shrinks_large_logo(self):
        small_logo = Image.new("RGBA", (5, 5))
        large_logo = Image.new("RGBA", (100, 50))

        self.assertIs(_resize_logo(small_logo, base_width=100), small_logo)
        resized = _resize_logo(large_logo, base_width=100)

        self.assertEqual(resized.width, 11)
        self.assertEqual(resized.height, 5)

    def test_font_helpers_normalize_and_find_candidates(self):
        self.assertEqual(_normalize_font_name("'Montserrat', sans-serif"), "montserrat")
        self.assertEqual(_get_font_key("Playfair Display"), "playfairdisplay")

        candidates = list(_get_font_candidate_paths("inter"))

        self.assertTrue(any(path.name == "Inter-Regular.ttf" for path in candidates))

    def test_wrap_text_breaks_long_line(self):
        image = Image.new("RGBA", (100, 100))
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()

        lines = _wrap_text("one two three four", font, max_width=30, draw=draw)

        self.assertGreater(len(lines), 1)

    def test_apply_center_text_to_image_returns_early_without_text(self):
        image_path = self.create_image("center.png")

        self.assertEqual(apply_center_text_to_image(image_path, ""), image_path)

    def test_apply_center_text_to_image_writes_text(self):
        image_path = self.create_image("text.png")

        result = apply_center_text_to_image(
            image_path,
            "Hello world",
            text_color="#FFFFFF",
        )

        self.assertEqual(result, image_path)
        self.assertTrue(image_path.exists())

    def test_apply_logo_to_image_and_paste_logo(self):
        image_path = self.create_image("base.png", size=(120, 120))
        logo_path = self.create_image("logo.png", size=(20, 20), color=(255, 0, 0, 255))

        self.assertEqual(apply_logo_to_image(image_path, logo_path), image_path)

        base_image = Image.new("RGBA", (120, 120), (0, 0, 0, 255))
        pasted = _paste_logo(base_image, logo_path, "top_left")

        self.assertEqual(pasted.size, (120, 120))
