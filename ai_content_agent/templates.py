from pathlib import Path

from PIL import Image, ImageDraw
from .helpers import _hex_to_rgba, _paste_logo_on_top_right
from .utils import _get_center_text_font, _wrap_text


def apply_template_rectangle(
    image_path,
    text,
    logo_file=None,
    primary_color=None,
    text_color=None,
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


def apply_template_bubbles(
    image_path,
    text,
    logo_file=None,
    primary_color=None,
    secondary_color=None,
    text_color=None,
):
    image_path = Path(image_path)

    with Image.open(image_path).convert("RGBA") as base_image:
        width, height = base_image.size

        overlay = Image.new("RGBA", base_image.size, (0, 0, 0, 45))
        base_image = Image.alpha_composite(base_image, overlay)

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
        font = _get_center_text_font(width)
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
            base_image = _paste_logo_on_top_right(base_image, logo_file)

        base_image.convert("RGB").save(image_path, format="PNG")

    return image_path


def apply_template_frame(
    image_path,
    text,
    logo_file=None,
    primary_color=None,
    tertiary_color=None,
    text_color=None,
):
    image_path = Path(image_path)

    with Image.open(image_path).convert("RGBA") as base_image:
        width, height = base_image.size

        overlay = Image.new("RGBA", base_image.size, (0, 0, 0, 55))
        base_image = Image.alpha_composite(base_image, overlay)

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
        font = _get_center_text_font(width)
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
            base_image = _paste_logo_on_top_right(base_image, logo_file)

        base_image.convert("RGB").save(image_path, format="PNG")

    return image_path


def apply_template_circle(
    image_path,
    text,
    logo_file=None,
    secondary_color=None,
    text_color=None,
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
        font = _get_center_text_font(width)
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
            base_image = _paste_logo_on_top_right(base_image, logo_file)

        base_image.convert("RGB").save(image_path, format="PNG")

    return image_path


def apply_template_triangle(
    image_path,
    text,
    logo_file=None,
    secondary_color=None,
    tertiary_color=None,
    text_color=None,
):
    image_path = Path(image_path)

    with Image.open(image_path).convert("RGBA") as base_image:
        width, height = base_image.size

        overlay = Image.new("RGBA", base_image.size, (0, 0, 0, 45))
        base_image = Image.alpha_composite(base_image, overlay)

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
        font = _get_center_text_font(width)
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
        text_y = int(height * 0.44) - text_height // 2

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
