from pathlib import Path
from PIL import Image, ImageDraw
from ai_content_agent.helpers import _hex_to_rgba, _paste_logo
from ai_content_agent.utils import _get_center_text_font, _wrap_text


def apply_template_frame(
    image_path,
    text,
    logo_file=None,
    logo_position="bottom_right",
    primary_color=None,
    tertiary_color=None,
    text_color=None,
    text_font=None,
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
        font = _get_center_text_font(width, text_font)
        lines = _wrap_text(
            text=text,
            font=font,
            max_width=int(width * 0.66),
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