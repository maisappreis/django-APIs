import shutil
import tempfile
from inspect import signature
from pathlib import Path

from django.test import SimpleTestCase
from PIL import Image, ImageDraw, ImageFont

from ai_content_agent.templates.bubbles import apply_template_bubbles
from ai_content_agent.templates.circle import apply_template_circle
from ai_content_agent.templates.corners import apply_template_corners
from ai_content_agent.templates.frame import apply_template_frame
from ai_content_agent.templates.layer import apply_template_layer
from ai_content_agent.templates.rectangle import apply_template_rectangle
from ai_content_agent.templates.stripes import apply_template_stripes
from ai_content_agent.templates.text_block import (
    _get_block_x,
    _get_block_y,
    _measure_lines,
    _measure_text_block,
    draw_title_subtitle_block,
)
from ai_content_agent.templates.text_overlay import (
    TEXT_OVERLAY_PRESETS,
    _get_block_coordinates,
    _measure_lines as overlay_measure_lines,
    _measure_text_block as overlay_measure_text_block,
    apply_template_text_overlay,
)
from ai_content_agent.templates.triangle import apply_template_triangle
from ai_content_agent.templates.vertical_rectangle import (
    apply_template_vertical_rectangle,
)


class TemplateRenderTest(SimpleTestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_image(self, name="base.png", size=(320, 320)):
        image_path = self.temp_dir / name
        Image.new("RGB", size, (32, 48, 64)).save(image_path)
        return image_path

    def create_logo(self):
        logo_path = self.temp_dir / "logo.png"
        Image.new("RGBA", (48, 24), (255, 255, 255, 255)).save(logo_path)
        return logo_path

    def assert_template_saves_png(self, renderer, **kwargs):
        image_path = self.create_image(f"{renderer.__name__}.png")
        call_kwargs = {
            "image_path": image_path,
            "title": "Main Title",
            "subtitle": "Subtitle text",
            "logo_file": self.create_logo(),
            "logo_position": "top_left",
            "primary_color": "#006C44",
            "secondary_color": "#1FD794",
            "tertiary_color": "#98C8B6",
            "text_color": "#FFFFFF",
            **kwargs,
        }
        accepted_kwargs = {
            key: value
            for key, value in call_kwargs.items()
            if key in signature(renderer).parameters
        }

        result = renderer(**accepted_kwargs)

        self.assertEqual(result, image_path)
        with Image.open(image_path) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.size, (320, 320))

    def test_shape_templates_render_and_save_png(self):
        renderers = [
            apply_template_bubbles,
            apply_template_circle,
            apply_template_corners,
            apply_template_frame,
            apply_template_layer,
            apply_template_rectangle,
            apply_template_stripes,
            apply_template_triangle,
            apply_template_vertical_rectangle,
        ]

        for renderer in renderers:
            with self.subTest(renderer=renderer.__name__):
                self.assert_template_saves_png(renderer)

    def test_text_overlay_renders_all_positions_with_box(self):
        for position in TEXT_OVERLAY_PRESETS:
            with self.subTest(position=position):
                self.assert_template_saves_png(
                    apply_template_text_overlay,
                    position=position,
                    show_box=True,
                )

    def test_text_overlay_with_no_text_still_pastes_logo_and_saves(self):
        image_path = self.create_image("overlay-logo-only.png")

        result = apply_template_text_overlay(
            image_path=image_path,
            title="",
            subtitle="",
            logo_file=self.create_logo(),
            logo_position="bottom_right",
        )

        self.assertEqual(result, image_path)
        self.assertTrue(image_path.exists())

    def test_text_overlay_with_no_text_and_no_logo_returns_without_saving_changes(self):
        image_path = self.create_image("overlay-empty.png")

        result = apply_template_text_overlay(
            image_path=image_path,
            title="",
            subtitle="",
            logo_file=None,
        )

        self.assertEqual(result, image_path)


class TextBlockHelperTest(SimpleTestCase):
    def get_draw_and_font(self):
        image = Image.new("RGBA", (240, 240), (0, 0, 0, 0))
        return ImageDraw.Draw(image), ImageFont.load_default()

    def test_text_block_measurement_and_alignment_helpers(self):
        draw, font = self.get_draw_and_font()

        width, height = _measure_lines(draw, ["Title", "Line"], font, line_gap=4)
        block = _measure_text_block(
            draw=draw,
            title_lines=["Title"],
            subtitle_lines=["Subtitle"],
            title_font=font,
            subtitle_font=font,
            line_gap=4,
            section_gap=10,
        )

        self.assertGreater(width, 0)
        self.assertGreater(height, 0)
        self.assertGreater(block["height"], 0)
        self.assertEqual(_get_block_x(100, 20, "left"), 100)
        self.assertEqual(_get_block_x(100, 20, "right"), 80)
        self.assertEqual(_get_block_x(100, 20, "center"), 90)
        self.assertEqual(_get_block_y(100, 20, "top"), 100)
        self.assertEqual(_get_block_y(100, 20, "bottom"), 80)
        self.assertEqual(_get_block_y(100, 20, "center"), 90)

    def test_draw_title_subtitle_block_handles_empty_left_right_and_center(self):
        for horizontal_align in ("left", "center", "right"):
            with self.subTest(horizontal_align=horizontal_align):
                image = Image.new("RGBA", (240, 240), (0, 0, 0, 0))
                draw = ImageDraw.Draw(image)

                draw_title_subtitle_block(
                    draw=draw,
                    width=240,
                    height=240,
                    title="Title",
                    subtitle="Subtitle",
                    text_color="#FFFFFF",
                    anchor_x=120,
                    anchor_y=120,
                    horizontal_align=horizontal_align,
                )

        image = Image.new("RGBA", (240, 240), (0, 0, 0, 0))
        draw_title_subtitle_block(
            draw=ImageDraw.Draw(image),
            width=240,
            height=240,
            title="",
            subtitle="",
        )

    def test_text_overlay_measurement_and_coordinates(self):
        draw, font = self.get_draw_and_font()

        width, height = overlay_measure_lines(draw, ["Title"], font, line_gap=4)
        block = overlay_measure_text_block(
            draw=draw,
            title_lines=["Title"],
            subtitle_lines=["Subtitle"],
            title_font=font,
            subtitle_font=font,
            line_gap=4,
            section_gap=10,
        )

        self.assertGreater(width, 0)
        self.assertGreater(height, 0)
        self.assertGreater(block["height"], 0)

        for position in TEXT_OVERLAY_PRESETS:
            x, y = _get_block_coordinates(
                width=240,
                height=240,
                block_width=80,
                block_height=40,
                position=position,
            )
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
