from pathlib import Path
from PIL import Image, ImageDraw
from ai_content_agent.helpers import _hex_to_rgba, _paste_logo
from ai_content_agent.utils import _get_center_text_font, _wrap_text


def apply_template_bubbles(
    image_path,
    text,
    logo_file=None,
    logo_position="bottom_right",
    primary_color=None,
    secondary_color=None,
    text_color=None,
    text_font=None,
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
        font = _get_center_text_font(width, text_font)
        lines = _wrap_text(
            text=text,
            font=font,
            max_width=int(width * 0.72),
            draw=draw,
        )
        text_block = "\n".join(lines)

        bbox = draw.multiline_textbbox(
            (0, 0),
            text_block,
            font=font,
            spacing=10,
        )
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        text_x = (width - text_width) // 2
        text_y = (height - text_height) // 2

        draw.multiline_text(
            (text_x, text_y),
            text_block,
            font=font,
            fill=_hex_to_rgba(text_color, alpha=255),
            align="center",
            spacing=10,
        )

        if logo_file:
            base_image = _paste_logo(base_image, logo_file, logo_position)

        base_image.convert("RGB").save(image_path, format="PNG")

    return image_path