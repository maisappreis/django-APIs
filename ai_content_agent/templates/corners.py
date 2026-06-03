from pathlib import Path
from PIL import Image, ImageDraw
from ai_content_agent.helpers import _hex_to_rgba, _paste_logo
from ai_content_agent.utils import _get_center_text_font, _wrap_text


def apply_template_corners(
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

        corners_layer = Image.new("RGBA", base_image.size, (0, 0, 0, 0))
        corners_draw = ImageDraw.Draw(corners_layer)

        triangle_size = int(width * 0.34)
        alpha = 153

        corners_draw.polygon(
            [
                (0, 0),
                (triangle_size, 0),
                (0, triangle_size),
            ],
            fill=_hex_to_rgba(primary_color, alpha=alpha),
        )
        corners_draw.polygon(
            [
                (width, height),
                (width - triangle_size, height),
                (width, height - triangle_size),
            ],
            fill=_hex_to_rgba(secondary_color, alpha=alpha),
        )

        base_image = Image.alpha_composite(base_image, corners_layer)

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