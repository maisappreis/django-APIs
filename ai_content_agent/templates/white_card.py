from pathlib import Path

from PIL import Image, ImageDraw

from ai_content_agent.helpers import _hex_to_rgba, _paste_logo
from ai_content_agent.utils import _get_text_font, _wrap_text


WHITE_CARD_PRESETS = {
    "bottom_right": ("right", "bottom"),
    "bottom_left": ("left", "bottom"),
    "top_right": ("right", "top"),
    "top_left": ("left", "top"),
}

TITLE_FONT_SIZE_RATIO = 0.082
SUBTITLE_FONT_SIZE_RATIO = 0.041
MAX_WIDTH_RATIO = 0.38
EDGE_MARGIN_RATIO = 0.04
PADDING_X_RATIO = 0.025
PADDING_Y_RATIO = 0.025
TEXT_GAP_RATIO = 0.025
TITLE_SEPARATOR_GAP_RATIO = 0.035
SEPARATOR_HEIGHT_RATIO = 0.004


def apply_template_white_card_bottom_right(
    image_path,
    title="",
    subtitle="",
    logo_file=None,
    logo_position="bottom_right",
    primary_color="#000000",
    title_font=None,
    subtitle_font=None,
):
    return _apply_white_card_template(
        image_path=image_path,
        title=title,
        subtitle=subtitle,
        logo_file=logo_file,
        logo_position=logo_position,
        primary_color=primary_color,
        title_font=title_font,
        subtitle_font=subtitle_font,
        preset="bottom_right",
    )


def apply_template_white_card_bottom_left(
    image_path,
    title="",
    subtitle="",
    logo_file=None,
    logo_position="bottom_right",
    primary_color="#000000",
    title_font=None,
    subtitle_font=None,
):
    return _apply_white_card_template(
        image_path=image_path,
        title=title,
        subtitle=subtitle,
        logo_file=logo_file,
        logo_position=logo_position,
        primary_color=primary_color,
        title_font=title_font,
        subtitle_font=subtitle_font,
        preset="bottom_left",
    )


def apply_template_white_card_top_right(
    image_path,
    title="",
    subtitle="",
    logo_file=None,
    logo_position="bottom_right",
    primary_color="#000000",
    title_font=None,
    subtitle_font=None,
):
    return _apply_white_card_template(
        image_path=image_path,
        title=title,
        subtitle=subtitle,
        logo_file=logo_file,
        logo_position=logo_position,
        primary_color=primary_color,
        title_font=title_font,
        subtitle_font=subtitle_font,
        preset="top_right",
    )


def apply_template_white_card_top_left(
    image_path,
    title="",
    subtitle="",
    logo_file=None,
    logo_position="bottom_right",
    primary_color="#000000",
    title_font=None,
    subtitle_font=None,
):
    return _apply_white_card_template(
        image_path=image_path,
        title=title,
        subtitle=subtitle,
        logo_file=logo_file,
        logo_position=logo_position,
        primary_color=primary_color,
        title_font=title_font,
        subtitle_font=subtitle_font,
        preset="top_left",
    )


def _apply_white_card_template(
    image_path,
    title="",
    subtitle="",
    logo_file=None,
    logo_position="bottom_right",
    primary_color="#000000",
    title_font=None,
    subtitle_font=None,
    preset="bottom_right",
):
    title = (title or "").strip()
    subtitle = (subtitle or "").strip()
    image_path = Path(image_path)

    with Image.open(image_path).convert("RGBA") as base_image:
        if not title and not subtitle:
            if logo_file:
                base_image = _paste_logo(base_image, logo_file, logo_position)
                base_image.convert("RGB").save(image_path, format="PNG")

            return image_path

        draw = ImageDraw.Draw(base_image)
        width, height = base_image.size
        title_font_file = _get_text_font(
            int(width * TITLE_FONT_SIZE_RATIO),
            title_font,
        )
        subtitle_font_file = _get_text_font(
            int(width * SUBTITLE_FONT_SIZE_RATIO),
            subtitle_font,
        )
        padding_x = int(width * PADDING_X_RATIO)
        padding_y = int(height * PADDING_Y_RATIO)
        max_text_width = int(width * MAX_WIDTH_RATIO)
        title_lines = (
            _wrap_text(title, title_font_file, max_text_width, draw)
            if title
            else []
        )
        subtitle_lines = (
            _wrap_text(
                subtitle.upper(),
                subtitle_font_file,
                max_text_width,
                draw,
            )
            if subtitle
            else []
        )
        line_gap = max(2, int(height * 0.006))
        title_separator_gap = max(8, int(height * TITLE_SEPARATOR_GAP_RATIO))
        section_gap = max(5, int(height * TEXT_GAP_RATIO))
        separator_height = max(1, int(height * SEPARATOR_HEIGHT_RATIO))
        block = _measure_block(
            draw=draw,
            title_lines=title_lines,
            subtitle_lines=subtitle_lines,
            title_font=title_font_file,
            subtitle_font=subtitle_font_file,
            line_gap=line_gap,
            title_separator_gap=title_separator_gap,
            section_gap=section_gap,
            separator_height=separator_height,
        )
        card_width = block["width"] + padding_x * 2
        card_height = block["height"] + padding_y * 2
        card_x, card_y = _get_card_coordinates(
            image_width=width,
            image_height=height,
            card_width=card_width,
            card_height=card_height,
            preset=preset,
        )

        draw.rectangle(
            [
                (card_x, card_y),
                (card_x + card_width, card_y + card_height),
            ],
            fill=_hex_to_rgba("#FFFFFF", alpha=245),
        )
        text_x = card_x + padding_x + block["width"]
        text_y = card_y + padding_y
        _draw_lines(
            draw=draw,
            lines=title_lines,
            font=title_font_file,
            color="#000000",
            right_x=text_x,
            start_y=text_y,
            line_gap=line_gap,
        )

        subtitle_y = text_y + block["title_height"]
        if title_lines and subtitle_lines:
            separator_y = subtitle_y + title_separator_gap
            draw.rectangle(
                [
                    (text_x - block["width"], separator_y),
                    (text_x, separator_y + separator_height),
                ],
                fill=_hex_to_rgba(primary_color, alpha=255),
            )
            subtitle_y = separator_y + separator_height + section_gap

        _draw_lines(
            draw=draw,
            lines=subtitle_lines,
            font=subtitle_font_file,
            color="#000000",
            right_x=text_x,
            start_y=subtitle_y,
            line_gap=line_gap,
        )

        if logo_file:
            base_image = _paste_logo(base_image, logo_file, logo_position)

        base_image.convert("RGB").save(image_path, format="PNG")

    return image_path


def _measure_block(
    draw,
    title_lines,
    subtitle_lines,
    title_font,
    subtitle_font,
    line_gap,
    title_separator_gap,
    section_gap,
    separator_height,
):
    title_width, title_height = _measure_lines(
        draw,
        title_lines,
        title_font,
        line_gap,
    )
    subtitle_width, subtitle_height = _measure_lines(
        draw,
        subtitle_lines,
        subtitle_font,
        line_gap,
    )
    total_height = title_height + subtitle_height

    if title_lines and subtitle_lines:
        total_height += title_separator_gap + section_gap + separator_height

    return {
        "width": max(title_width, subtitle_width),
        "height": total_height,
        "title_height": title_height,
    }


def _measure_lines(draw, lines, font, line_gap):
    if not lines:
        return 0, 0

    widths = []
    heights = []

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])

    return max(widths), sum(heights) + line_gap * (len(lines) - 1)


def _get_card_coordinates(
    image_width,
    image_height,
    card_width,
    card_height,
    preset,
):
    horizontal_align, vertical_align = WHITE_CARD_PRESETS[preset]
    margin = int(image_width * EDGE_MARGIN_RATIO)

    x_positions = {
        "left": 0,
        "right": image_width - card_width,
    }
    y_positions = {
        "top": margin,
        "bottom": image_height - card_height - margin,
    }

    return x_positions[horizontal_align], y_positions[vertical_align]


def _draw_lines(draw, lines, font, color, right_x, start_y, line_gap):
    current_y = start_y

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        line_height = bbox[3] - bbox[1]
        draw.text(
            (right_x - line_width, current_y),
            line,
            font=font,
            fill=_hex_to_rgba(color, alpha=255),
        )
        current_y += line_height + line_gap
