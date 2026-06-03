from pathlib import Path
from PIL import Image, ImageDraw
from ai_content_agent.helpers import _hex_to_rgba, _paste_logo
from ai_content_agent.utils import _get_center_text_font, _wrap_text


def apply_template_vertical_rectangle(
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

        rectangle_layer = Image.new("RGBA", base_image.size, (0, 0, 0, 0))
        rectangle_draw = ImageDraw.Draw(rectangle_layer)

        rectangle_width = int(width * 0.13)
        accent_width = int(width * 0.035)
        accent_gap = int(width * 0.035)
        rectangle_left = width - rectangle_width
        accent_right = rectangle_left - accent_gap
        accent_left = accent_right - accent_width

        rectangle_draw.rectangle(
            [(accent_left, 0), (accent_right, height)],
            fill=_hex_to_rgba(secondary_color, alpha=135),
        )
        rectangle_draw.rectangle(
            [(rectangle_left, 0), (width, height)],
            fill=_hex_to_rgba(secondary_color, alpha=155),
        )
        base_image = Image.alpha_composite(base_image, rectangle_layer)

        draw = ImageDraw.Draw(base_image)
        font = _get_center_text_font(width, text_font)
        left_margin = int(width * 0.08)
        max_text_width = int(width * 0.58)
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
        )
        text_height = bbox[3] - bbox[1]

        text_x = left_margin
        text_y = (height - text_height) // 2

        draw.multiline_text(
            (text_x, text_y),
            text_block,
            font=font,
            fill=_hex_to_rgba(text_color, alpha=255),
            align="left",
            spacing=10,
        )

        if logo_file:
            base_image = _paste_logo(base_image, logo_file, logo_position)

        base_image.convert("RGB").save(image_path, format="PNG")

    return image_path