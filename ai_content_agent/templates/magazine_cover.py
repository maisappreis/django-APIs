from pathlib import Path

from PIL import Image, ImageDraw

from ai_content_agent.helpers import _hex_to_rgba, _paste_logo
from ai_content_agent.utils import _get_text_font, _wrap_text


TITLE_FONT_SIZE_RATIO = 0.104
SUBTITLE_FONT_SIZE_RATIO = 0.04
KICKER_FONT_SIZE_RATIO = 0.026


def apply_template_magazine_cover(
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
            _build_editorial_overlay(width, height),
        )

        draw = ImageDraw.Draw(base_image)
        margin_x = int(width * 0.075)
        title_anchor_y = int(height * 0.58)
        max_title_width = int(width * 0.79)
        max_subtitle_width = width - margin_x * 2 - int(width * 0.068)

        accent_color = secondary_color or primary_color
        _draw_kicker(
            draw=draw,
            width=width,
            height=height,
            x=margin_x,
            y=int(height * 0.10),
            color=accent_color,
            text_color=text_color,
            subtitle_font=subtitle_font,
        )
        title_bottom = _draw_title(
            draw=draw,
            title=title,
            x=margin_x,
            y=title_anchor_y,
            max_width=max_title_width,
            width=width,
            height=height,
            text_color=text_color,
            title_font=title_font,
        )
        _draw_subtitle_card(
            draw=draw,
            subtitle=subtitle,
            x=margin_x,
            y=title_bottom + int(height * 0.026),
            max_width=max_subtitle_width,
            width=width,
            height=height,
            primary_color=primary_color,
            text_color=text_color,
            subtitle_font=subtitle_font,
        )
        _draw_editorial_rules(
            draw=draw,
            width=width,
            height=height,
            color=accent_color,
        )

        if logo_file:
            base_image = _paste_logo(base_image, logo_file, logo_position)

        base_image.convert("RGB").save(image_path, format="PNG")

    return image_path


def _build_editorial_overlay(width, height):
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for y in range(height):
        strength = int(185 * (y / max(1, height - 1)) ** 1.35)
        draw.line([(0, y), (width, y)], fill=(0, 0, 0, strength))

    side_width = int(width * 0.52)
    for x in range(side_width):
        strength = int(85 * (1 - x / max(1, side_width - 1)))
        draw.line([(x, 0), (x, height)], fill=(0, 0, 0, strength))

    return overlay


def _draw_kicker(
    draw,
    width,
    height,
    x,
    y,
    color,
    text_color,
    subtitle_font,
):
    font = _get_text_font(int(width * KICKER_FONT_SIZE_RATIO), subtitle_font)
    line_width = int(width * 0.16)
    line_y = y + int(height * 0.012)
    draw.line(
        [(x, line_y), (x + line_width, line_y)],
        fill=_hex_to_rgba(color, alpha=255),
        width=max(2, int(width * 0.006)),
    )
    draw.text(
        (x + line_width + int(width * 0.025), y),
        "SPECIAL EDITION",
        font=font,
        fill=_hex_to_rgba(text_color, alpha=235),
    )


def _draw_title(
    draw,
    title,
    x,
    y,
    max_width,
    width,
    height,
    text_color,
    title_font,
):
    title = (title or "").strip()
    if not title:
        return y

    font = _get_text_font(int(width * TITLE_FONT_SIZE_RATIO), title_font)
    lines = _wrap_text(title.upper(), font, max_width, draw)
    line_gap = max(6, int(height * 0.006))

    current_y = y
    for line in lines[:3]:
        shadow_offset = max(2, int(width * 0.006))
        draw.text(
            (x + shadow_offset, current_y + shadow_offset),
            line,
            font=font,
            fill=(0, 0, 0, 150),
        )
        draw.text(
            (x, current_y),
            line,
            font=font,
            fill=_hex_to_rgba(text_color, alpha=255),
        )
        bbox = draw.textbbox((0, 0), line, font=font)
        current_y += bbox[3] - bbox[1] + line_gap

    return current_y


def _draw_subtitle_card(
    draw,
    subtitle,
    x,
    y,
    max_width,
    width,
    height,
    primary_color,
    text_color,
    subtitle_font,
):
    subtitle = (subtitle or "").strip()
    if not subtitle:
        return

    font = _get_text_font(int(width * SUBTITLE_FONT_SIZE_RATIO), subtitle_font)
    lines = _wrap_text(subtitle, font, max_width, draw)[:2]
    line_gap = max(5, int(height * 0.01))
    padding_x = int(width * 0.034)
    padding_y = int(height * 0.022)
    _, text_height = _measure_lines(draw, lines, font, line_gap)
    box_width = width - x * 2
    box = [
        x,
        y,
        x + box_width,
        y + text_height + padding_y * 2,
    ]

    draw.rectangle(
        box,
        fill=_hex_to_rgba(primary_color, alpha=205),
    )

    current_y = y + padding_y
    for line in lines:
        draw.text(
            (x + padding_x, current_y),
            line,
            font=font,
            fill=_hex_to_rgba(text_color, alpha=255),
        )
        bbox = draw.textbbox((0, 0), line, font=font)
        current_y += bbox[3] - bbox[1] + line_gap


def _draw_editorial_rules(draw, width, height, color):
    stroke = max(2, int(width * 0.004))
    left = int(width * 0.075)
    right = width - left
    bottom = height - int(height * 0.055)

    draw.line(
        [(left, bottom), (right, bottom)],
        fill=_hex_to_rgba(color, alpha=220),
        width=stroke,
    )
    draw.line(
        [(left, int(height * 0.18)), (left, int(height * 0.45))],
        fill=_hex_to_rgba(color, alpha=180),
        width=stroke,
    )


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
