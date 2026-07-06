from pathlib import Path

from PIL import Image, ImageDraw

from ai_content_agent.helpers import _hex_to_rgba, _paste_logo
from ai_content_agent.templates.editorial_split import _wrap_text_breaking_long_words
from ai_content_agent.utils import _get_text_font


TITLE_FONT_SIZE_RATIO = 0.058
SUBTITLE_FONT_SIZE_RATIO = 0.034
KICKER_FONT_SIZE_RATIO = 0.022


def apply_template_luxury_minimal(
    image_path,
    title="",
    subtitle="",
    logo_file=None,
    logo_position="top_right",
    primary_color=None,
    secondary_color=None,
    text_color=None,
    title_font=None,
    subtitle_font=None,
):
    image_path = Path(image_path)

    with Image.open(image_path).convert("RGBA") as base_image:
        width, height = base_image.size
        base_image = Image.alpha_composite(
            base_image,
            _build_luxury_overlay(width, height),
        )

        draw = ImageDraw.Draw(base_image)
        margin = int(width * 0.075)
        text_width = int(width * 0.58)
        text_x = margin
        text_y = height - int(height * 0.285)

        _draw_corner_marks(
            draw=draw,
            width=width,
            height=height,
            color=secondary_color or primary_color,
        )
        _draw_text_block(
            draw=draw,
            title=title,
            subtitle=subtitle,
            x=text_x,
            y=text_y,
            max_width=text_width,
            width=width,
            height=height,
            primary_color=primary_color,
            secondary_color=secondary_color or primary_color,
            text_color=text_color,
            title_font=title_font,
            subtitle_font=subtitle_font,
        )

        if logo_file:
            base_image = _paste_logo(base_image, logo_file, logo_position)

        base_image.convert("RGB").save(image_path, format="PNG")

    return image_path


def _build_luxury_overlay(width, height):
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for y in range(height):
        progress = y / max(1, height - 1)
        alpha = int(135 * progress ** 1.7)
        draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))

    for x in range(width):
        progress = 1 - x / max(1, width - 1)
        alpha = int(70 * progress ** 2)
        draw.line([(x, 0), (x, height)], fill=(0, 0, 0, alpha))

    return overlay


def _draw_corner_marks(draw, width, height, color):
    margin = int(width * 0.06)
    length = int(width * 0.14)
    stroke = max(1, int(width * 0.003))
    bottom = height - margin
    right = width - margin

    draw.line(
        [(margin, margin), (margin + length, margin)],
        fill=_hex_to_rgba(color, alpha=210),
        width=stroke,
    )
    draw.line(
        [(margin, margin), (margin, margin + length)],
        fill=_hex_to_rgba(color, alpha=210),
        width=stroke,
    )
    draw.line(
        [(right - length, bottom), (right, bottom)],
        fill=_hex_to_rgba(color, alpha=190),
        width=stroke,
    )
    draw.line(
        [(right, bottom - length), (right, bottom)],
        fill=_hex_to_rgba(color, alpha=190),
        width=stroke,
    )


def _draw_text_block(
    draw,
    title,
    subtitle,
    x,
    y,
    max_width,
    width,
    height,
    primary_color,
    secondary_color,
    text_color,
    title_font,
    subtitle_font,
):
    kicker_font = _get_text_font(int(width * KICKER_FONT_SIZE_RATIO), subtitle_font)
    title_font_file, title_lines = _get_wrapped_font(
        draw=draw,
        text=(title or "").strip().upper(),
        max_width=max_width,
        initial_size=int(width * TITLE_FONT_SIZE_RATIO),
        min_size=int(width * 0.042),
        text_font=title_font,
        max_lines=2,
    )
    subtitle_font_file = _get_text_font(
        int(width * SUBTITLE_FONT_SIZE_RATIO),
        subtitle_font,
    )
    subtitle_lines = _wrap_text_breaking_long_words(
        (subtitle or "").strip(),
        subtitle_font_file,
        max_width,
        draw,
    )[:2]
    line_gap = max(5, int(height * 0.01))
    padding_x = int(width * 0.035)
    padding_y = int(height * 0.026)
    panel_width = max_width + padding_x * 2
    panel_height = _get_panel_height(
        draw=draw,
        title_lines=title_lines,
        subtitle_lines=subtitle_lines,
        title_font=title_font_file,
        subtitle_font=subtitle_font_file,
        height=height,
        padding_y=padding_y,
        line_gap=line_gap,
    )

    draw.rectangle(
        [
            (x - padding_x, y - padding_y),
            (x - padding_x + panel_width, y - padding_y + panel_height),
        ],
        fill=_hex_to_rgba(primary_color, alpha=165),
    )

    draw.line(
        [(x, y), (x + int(max_width * 0.22), y)],
        fill=_hex_to_rgba(secondary_color, alpha=255),
        width=max(2, int(width * 0.004)),
    )

    current_y = y + int(height * 0.023)
    draw.text(
        (x, current_y),
        "LUXURY EDIT",
        font=kicker_font,
        fill=_hex_to_rgba(secondary_color, alpha=240),
    )
    current_y += int(height * 0.038)

    for line in title_lines:
        draw.text(
            (x, current_y),
            line,
            font=title_font_file,
            fill=_hex_to_rgba(text_color, alpha=255),
        )
        bbox = draw.textbbox((0, 0), line, font=title_font_file)
        current_y += bbox[3] - bbox[1] + line_gap

    if title_lines and subtitle_lines:
        current_y += int(height * 0.006)

    for line in subtitle_lines:
        draw.text(
            (x, current_y),
            line,
            font=subtitle_font_file,
            fill=_hex_to_rgba(text_color, alpha=230),
        )
        bbox = draw.textbbox((0, 0), line, font=subtitle_font_file)
        current_y += bbox[3] - bbox[1] + line_gap


def _get_panel_height(
    draw,
    title_lines,
    subtitle_lines,
    title_font,
    subtitle_font,
    height,
    padding_y,
    line_gap,
):
    content_height = int(height * 0.023) + int(height * 0.038)
    content_height += _get_lines_height(draw, title_lines, title_font, line_gap)

    if title_lines and subtitle_lines:
        content_height += int(height * 0.006)

    content_height += _get_lines_height(draw, subtitle_lines, subtitle_font, line_gap)

    return content_height + padding_y * 2


def _get_lines_height(draw, lines, font, line_gap):
    if not lines:
        return 0

    heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        heights.append(bbox[3] - bbox[1])

    return sum(heights) + line_gap * (len(lines) - 1)


def _get_wrapped_font(
    draw,
    text,
    max_width,
    initial_size,
    min_size,
    text_font,
    max_lines,
):
    font_size = initial_size

    while font_size >= min_size:
        font = _get_text_font(font_size, text_font)
        lines = _wrap_text_breaking_long_words(text, font, max_width, draw)[
            :max_lines
        ]
        widest_line = max(
            (_get_text_width(draw, line, font) for line in lines),
            default=0,
        )

        if widest_line <= max_width:
            return font, lines

        font_size -= 2

    font = _get_text_font(min_size, text_font)
    return font, _wrap_text_breaking_long_words(
        text,
        font,
        max_width,
        draw,
    )[:max_lines]


def _get_text_width(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]
