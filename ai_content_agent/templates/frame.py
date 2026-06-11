from pathlib import Path
from PIL import Image, ImageDraw
from ai_content_agent.helpers import _hex_to_rgba, _paste_logo
from ai_content_agent.templates.text_block import draw_title_subtitle_block


def apply_template_frame(
    image_path,
    title="",
    subtitle="",
    logo_file=None,
    logo_position="bottom_right",
    primary_color=None,
    tertiary_color=None,
    text_color=None,
    title_font=None,
    subtitle_font=None,
):
    image_path = Path(image_path)

    with Image.open(image_path).convert("RGBA") as base_image:
        width, height = base_image.size

        frame_layer = Image.new("RGBA", base_image.size, (0, 0, 0, 0))
        frame_draw = ImageDraw.Draw(frame_layer)

        outer_margin = int(width * 0.09)
        inner_gap = int(width * 0.045)
        outer_stroke = max(6, int(width * 0.014))
        inner_stroke = max(4, int(width * 0.008))

        outer_box = [
            outer_margin,
            outer_margin,
            width - outer_margin,
            height - outer_margin,
        ]
        inner_box = [
            outer_margin + inner_gap,
            outer_margin + inner_gap,
            width - outer_margin - inner_gap,
            height - outer_margin - inner_gap,
        ]

        frame_draw.rectangle(
            outer_box,
            outline=_hex_to_rgba(primary_color, alpha=185),
            width=outer_stroke,
        )
        frame_draw.rectangle(
            inner_box,
            outline=_hex_to_rgba(tertiary_color, alpha=185),
            width=inner_stroke,
        )

        base_image = Image.alpha_composite(base_image, frame_layer)

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
            max_width=int(width * 0.66),
            horizontal_align="center",
        )

        if logo_file:
            base_image = _paste_logo(base_image, logo_file, logo_position)

        base_image.convert("RGB").save(image_path, format="PNG")

    return image_path
