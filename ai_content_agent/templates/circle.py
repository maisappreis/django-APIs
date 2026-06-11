from pathlib import Path
from PIL import Image, ImageDraw
from ai_content_agent.helpers import _hex_to_rgba, _paste_logo
from ai_content_agent.templates.text_block import draw_title_subtitle_block


def apply_template_circle(
    image_path,
    title="",
    subtitle="",
    logo_file=None,
    logo_position="bottom_right",
    secondary_color=None,
    text_color=None,
    title_font=None,
    subtitle_font=None,
):
    image_path = Path(image_path)

    with Image.open(image_path).convert("RGBA") as base_image:
        width, height = base_image.size

        overlay_layer = Image.new(
            "RGBA",
            base_image.size,
            _hex_to_rgba(secondary_color, alpha=255),
        )
        mask = Image.new("L", base_image.size, 153)
        mask_draw = ImageDraw.Draw(mask)

        circle_diameter = int(width * 0.82)
        circle_center_x = int(width * 0.42)
        circle_center_y = height // 2
        circle_box = [
            circle_center_x - circle_diameter // 2,
            circle_center_y - circle_diameter // 2,
            circle_center_x + circle_diameter // 2,
            circle_center_y + circle_diameter // 2,
        ]
        mask_draw.ellipse(circle_box, fill=0)
        overlay_layer.putalpha(mask)

        base_image = Image.alpha_composite(base_image, overlay_layer)

        draw = ImageDraw.Draw(base_image)
        max_text_width = int(width * 0.38)
        right_margin = int(width * 0.08)
        draw_title_subtitle_block(
            draw=draw,
            width=width,
            height=height,
            title=title,
            subtitle=subtitle,
            title_font=title_font,
            subtitle_font=subtitle_font,
            text_color=text_color,
            max_width=max_text_width,
            anchor_x=width - right_margin,
            anchor_y=height // 2 + int(height * 0.08),
            horizontal_align="right",
        )

        if logo_file:
            base_image = _paste_logo(base_image, logo_file, logo_position)

        base_image.convert("RGB").save(image_path, format="PNG")

    return image_path
