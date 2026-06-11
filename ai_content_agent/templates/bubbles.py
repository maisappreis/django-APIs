from pathlib import Path
from PIL import Image, ImageDraw
from ai_content_agent.helpers import _hex_to_rgba, _paste_logo
from ai_content_agent.templates.text_block import draw_title_subtitle_block


def apply_template_bubbles(
    image_path,
    title="",
    subtitle="",
    logo_file=None,
    logo_position="bottom_right",
    primary_color=None,
    secondary_color=None,
    text_color=None,
    title_font=None,
    subtitle_font=None,
):
    image_path = Path(image_path)

    with Image.open(image_path).convert("RGBA") as base_image:
        width, height = base_image.size

        bubbles_layer = Image.new("RGBA", base_image.size, (0, 0, 0, 0))
        bubbles_draw = ImageDraw.Draw(bubbles_layer)

        large_circle_diameter = int(width * 0.62)
        small_circle_diameter = int(width * 0.42)

        offset_x = int(width * 0.08)
        offset_y = int(height * 0.08)

        bubbles_draw.ellipse(
            [
                offset_x - large_circle_diameter // 2,
                offset_y - large_circle_diameter // 2,
                offset_x + large_circle_diameter // 2,
                offset_y + large_circle_diameter // 2,
            ],
            fill=_hex_to_rgba(primary_color, alpha=125),
        )

        bubbles_draw.ellipse(
            [
                width - offset_x - small_circle_diameter // 2,
                height - offset_y - small_circle_diameter // 2,
                width - offset_x + small_circle_diameter // 2,
                height - offset_y + small_circle_diameter // 2,
            ],
            fill=_hex_to_rgba(secondary_color, alpha=115),
        )

        base_image = Image.alpha_composite(base_image, bubbles_layer)

        draw = ImageDraw.Draw(base_image)
        draw_title_subtitle_block(
            draw=draw,
            width=width,
            height=height,
            title=title,
            subtitle=subtitle,
            title_font=title_font,
            subtitle_font=subtitle_font,
            text_color=text_color,
            max_width=int(width * 0.72),
            horizontal_align="center",
        )

        if logo_file:
            base_image = _paste_logo(base_image, logo_file, logo_position)

        base_image.convert("RGB").save(image_path, format="PNG")

    return image_path
