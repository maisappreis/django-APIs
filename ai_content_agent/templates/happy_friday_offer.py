from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageOps

from ai_content_agent.helpers import _hex_to_rgba, _paste_logo
from ai_content_agent.templates.editorial_split import _wrap_text_breaking_long_words
from ai_content_agent.utils import _get_text_font


TITLE_FONT_SIZE_RATIO = 0.045
SUBTITLE_FONT_SIZE_RATIO = 0.033
KICKER_FONT_SIZE_RATIO = 0.017
FOOTER_FONT_SIZE_RATIO = 0.012


def apply_template_happy_friday_offer(
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

    with Image.open(image_path).convert("RGBA") as source_image:
        width, height = source_image.size
        canvas = Image.new("RGBA", source_image.size, (232, 232, 230, 255))
        draw = ImageDraw.Draw(canvas)

        margin_x = int(width * 0.105)
        top_y = int(height * 0.135)
        image_height = int(height * 0.475)
        text_height = int(height * 0.30)
        content_width = width - margin_x * 2
        photo_box = (
            margin_x,
            top_y,
            margin_x + content_width,
            top_y + image_height,
        )
        text_box = (
            margin_x,
            photo_box[3],
            margin_x + content_width,
            photo_box[3] + text_height,
        )

        _paste_offer_photo(canvas, source_image, photo_box)
        _draw_top_tag(
            draw=draw,
            center_x=width // 2,
            y=int(height * 0.09),
            canvas_width=width,
            canvas_height=height,
            primary_color=primary_color,
            text_color=text_color,
            subtitle_font=subtitle_font,
        )
        _draw_text_panel(
            draw=draw,
            title=title,
            subtitle=subtitle,
            box=text_box,
            canvas_width=width,
            canvas_height=height,
            primary_color=primary_color,
            secondary_color=secondary_color,
            title_font=title_font,
            subtitle_font=subtitle_font,
        )
        _draw_outer_shadow(draw, width, height)

        if logo_file:
            canvas = _paste_logo(canvas, logo_file, logo_position)

        canvas.convert("RGB").save(image_path, format="PNG")

    return image_path


def _paste_offer_photo(canvas, source_image, photo_box):
    x1, y1, x2, y2 = photo_box
    photo_width = x2 - x1
    photo_height = y2 - y1
    resampling = getattr(Image, "Resampling", Image).LANCZOS

    photo = ImageOps.fit(
        source_image.convert("RGB"),
        (photo_width, photo_height),
        method=resampling,
        centering=(0.50, 0.28),
    )
    photo = ImageEnhance.Brightness(photo).enhance(1.03)
    photo = ImageEnhance.Contrast(photo).enhance(1.07)
    photo = ImageEnhance.Color(photo).enhance(1.08)
    canvas.alpha_composite(photo.convert("RGBA"), (x1, y1))


def _draw_top_tag(
    draw,
    center_x,
    y,
    canvas_width,
    canvas_height,
    primary_color,
    text_color,
    subtitle_font,
):
    tag_width = int(canvas_width * 0.22)
    tag_height = int(canvas_height * 0.075)
    tag_x = center_x - tag_width // 2
    tag_fill = _hex_to_rgba(primary_color or "#181818", alpha=245)
    tag_text_color = _get_tag_text_color(text_color)
    font = _get_text_font(int(canvas_width * KICKER_FONT_SIZE_RATIO), subtitle_font)

    draw.rectangle(
        [(tag_x, y), (tag_x + tag_width, y + tag_height)],
        fill=tag_fill,
    )
    _draw_centered_text(
        draw=draw,
        text="This Week",
        box=(tag_x, y, tag_x + tag_width, y + tag_height),
        font=font,
        fill=_hex_to_rgba(tag_text_color),
    )


def _draw_text_panel(
    draw,
    title,
    subtitle,
    box,
    canvas_width,
    canvas_height,
    primary_color,
    secondary_color,
    title_font,
    subtitle_font,
):
    x1, y1, x2, y2 = box
    panel_width = x2 - x1
    panel_height = y2 - y1

    draw.rectangle(box, fill=(255, 255, 255, 255))

    title_text = (title or "").strip().upper()
    subtitle_text = (subtitle or "").strip()
    title_font_file, title_lines = _get_wrapped_font(
        draw=draw,
        text=title_text,
        max_width=int(panel_width * 0.78),
        initial_size=int(canvas_width * TITLE_FONT_SIZE_RATIO),
        min_size=int(canvas_width * 0.032),
        text_font=title_font,
        max_lines=2,
    )
    subtitle_font_file = _get_text_font(
        int(canvas_width * SUBTITLE_FONT_SIZE_RATIO),
        subtitle_font,
    )
    footer_font = _get_text_font(
        int(canvas_width * FOOTER_FONT_SIZE_RATIO),
        subtitle_font,
    )
    subtitle_lines = _wrap_text_breaking_long_words(
        subtitle_text,
        subtitle_font_file,
        int(panel_width * 0.70),
        draw,
    )[:1]
    line_gap = max(4, int(canvas_height * 0.008))
    title_block_height = _measure_lines(draw, title_lines, title_font_file, line_gap)
    subtitle_block_height = _measure_lines(
        draw,
        subtitle_lines,
        subtitle_font_file,
        line_gap,
    )
    footer_text = "Link in bio"
    footer_bbox = draw.textbbox((0, 0), footer_text, font=footer_font)
    footer_height = footer_bbox[3] - footer_bbox[1]
    block_height = (
        title_block_height
        + subtitle_block_height
        + footer_height
        + int(panel_height * 0.12)
    )
    current_y = y1 + max(0, (panel_height - block_height) // 2)

    for line in title_lines:
        _draw_centered_text(
            draw=draw,
            text=line,
            box=(x1, current_y, x2, current_y + int(canvas_height * 0.06)),
            font=title_font_file,
            fill=(18, 18, 18, 255),
        )
        bbox = draw.textbbox((0, 0), line, font=title_font_file)
        current_y += bbox[3] - bbox[1] + line_gap

    current_y += int(panel_height * 0.025)

    for line in subtitle_lines:
        _draw_centered_text(
            draw=draw,
            text=line,
            box=(x1, current_y, x2, current_y + int(canvas_height * 0.045)),
            font=subtitle_font_file,
            fill=_hex_to_rgba(secondary_color or primary_color or "#111111"),
        )
        bbox = draw.textbbox((0, 0), line, font=subtitle_font_file)
        current_y += bbox[3] - bbox[1] + line_gap

    current_y += int(panel_height * 0.045)
    _draw_centered_text(
        draw=draw,
        text=footer_text,
        box=(x1, current_y, x2, current_y + footer_height + line_gap),
        font=footer_font,
        fill=(32, 32, 32, 210),
    )


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


def _draw_centered_text(draw, text, box, font, fill):
    x1, y1, x2, y2 = box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = x1 + ((x2 - x1) - text_width) // 2
    y = y1 + ((y2 - y1) - text_height) // 2 - bbox[1]

    draw.text((x, y), text, font=font, fill=fill)


def _measure_lines(draw, lines, font, line_gap):
    if not lines:
        return 0

    heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        heights.append(bbox[3] - bbox[1])

    return sum(heights) + line_gap * (len(lines) - 1)


def _draw_outer_shadow(draw, width, height):
    shadow_color = (175, 175, 170, 120)
    draw.line([(0, height - 1), (width, height - 1)], fill=shadow_color, width=2)
    draw.line([(width - 1, 0), (width - 1, height)], fill=shadow_color, width=2)


def _get_tag_text_color(text_color):
    if not text_color or _is_dark_color(text_color):
        return "#FFFFFF"

    return text_color


def _is_dark_color(hex_color):
    try:
        red, green, blue, _ = _hex_to_rgba(hex_color)
    except (TypeError, ValueError):
        return True

    brightness = (red * 299 + green * 587 + blue * 114) / 1000
    return brightness < 150


def _get_text_width(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]
