from pathlib import Path
from PIL import Image, ImageDraw
from ai_content_agent.helpers import _hex_to_rgba, _paste_logo
from ai_content_agent.templates.text_block import draw_title_subtitle_block


def apply_template_triangle(
    image_path,
    title="",
    subtitle="",
    logo_file=None,
    logo_position="bottom_right",
    secondary_color=None,
    tertiary_color=None,
    text_color=None,
    title_font=None,
    subtitle_font=None,
):
    image_path = Path(image_path)

    with Image.open(image_path).convert("RGBA") as base_image:
        width, height = base_image.size

        triangle_layer = Image.new("RGBA", base_image.size, (0, 0, 0, 0))
        triangle_draw = ImageDraw.Draw(triangle_layer)

        triangle_height = int(height * 0.24)
        triangle_peak_x = int(width * 0.68)
        triangle_peak_y = height - triangle_height
        top_triangle_height = int(height * 0.14)
        top_triangle_peak_x = int(width * 0.32)
        top_triangle_peak_y = top_triangle_height

        triangle_draw.polygon(
            [
                (0, height),
                (width, height),
                (triangle_peak_x, triangle_peak_y),
            ],
            fill=_hex_to_rgba(secondary_color, alpha=130),
        )
        triangle_draw.polygon(
            [
                (0, 0),
                (width, 0),
                (top_triangle_peak_x, top_triangle_peak_y),
            ],
            fill=_hex_to_rgba(tertiary_color, alpha=130),
        )
        base_image = Image.alpha_composite(base_image, triangle_layer)

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
            anchor_y=int(height * 0.44),
            horizontal_align="center",
        )

        if logo_file:
            base_image = _paste_logo(base_image, logo_file, logo_position)

        base_image.convert("RGB").save(image_path, format="PNG")

    return image_path
