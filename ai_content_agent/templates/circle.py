from pathlib import Path
from PIL import Image, ImageDraw
from ai_content_agent.helpers import _hex_to_rgba, _paste_logo
from ai_content_agent.utils import _get_center_text_font, _wrap_text


def apply_template_circle(
    image_path,
    text,
    logo_file=None,
    logo_position="bottom_right",
    secondary_color=None,
    text_color=None,
    text_font=None,
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
        font = _get_center_text_font(width, text_font)
        max_text_width = int(width * 0.38)
        lines = _wrap_text(
            text=text,
            font=font,
            max_width=max_text_width,
            draw=draw,
        )
        text_block = "\n".join(lines)

        bbox = draw.multiline_textbbox(
            (0, 0),
            text_block,
            font=font,
            spacing=10,
            align="right",
        )
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        right_margin = int(width * 0.08)
        text_x = width - right_margin - text_width
        text_y = (height - text_height) // 2 + int(height * 0.08)

        draw.multiline_text(
            (text_x, text_y),
            text_block,
            font=font,
            fill=_hex_to_rgba(text_color, alpha=255),
            align="right",
            spacing=10,
        )

        if logo_file:
            base_image = _paste_logo(base_image, logo_file, logo_position)

        base_image.convert("RGB").save(image_path, format="PNG")

    return image_path