from pathlib import Path
from PIL import Image, ImageDraw
from ai_content_agent.helpers import _hex_to_rgba, _paste_logo
from ai_content_agent.templates.text_block import draw_title_subtitle_block


def apply_template_corners(
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
