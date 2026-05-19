from pathlib import Path

from PIL import Image, ImageDraw
from .helpers import _hex_to_rgba, _paste_logo_on_top_right
from .utils import _get_center_text_font, _wrap_text


def apply_template_rectangle(
    image_path,
    text,
    logo_file=None,
    *,
    primary_color,
    text_color,
):
    image_path = Path(image_path)

    with Image.open(image_path).convert("RGBA") as base_image:
        width, height = base_image.size

        overlay = Image.new("RGBA", base_image.size, (0, 0, 0, 70))
        base_image = Image.alpha_composite(base_image, overlay)

        banner_height = int(height * 0.24)
        banner_y = height - banner_height

        banner_layer = Image.new("RGBA", base_image.size, (0, 0, 0, 0))
        banner_draw = ImageDraw.Draw(banner_layer)
        banner_draw.rectangle(
            [(0, banner_y), (width, height)],
            fill=_hex_to_rgba(primary_color, alpha=90),
        )
        base_image = Image.alpha_composite(base_image, banner_layer)

        draw = ImageDraw.Draw(base_image)
        font = _get_center_text_font(width)
        lines = _wrap_text(
            text=text,
            font=font,
            max_width=int(width * 0.82),
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
        text_y = banner_y + (banner_height - text_height) // 2 - int(height * 0.025)

        draw.multiline_text(
            (text_x, text_y),
            text_block,
            font=font,
            fill=_hex_to_rgba(text_color, alpha=255),
            align="center",
            spacing=10,
        )

        if logo_file:
            base_image = _paste_logo_on_top_right(base_image, logo_file)

        base_image.convert("RGB").save(image_path, format="PNG")

    return image_path
