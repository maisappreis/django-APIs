from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageOps

from ai_content_agent.helpers import _hex_to_rgba, _paste_logo
from ai_content_agent.templates.editorial_split import _wrap_text_breaking_long_words
from ai_content_agent.utils import _get_text_font


TITLE_FONT_SIZE_RATIO = 0.038
SUBTITLE_FONT_SIZE_RATIO = 0.021
SIDE_LABEL_FONT_SIZE_RATIO = 0.014


def apply_template_editorial_stack(
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
        canvas = Image.new("RGBA", source_image.size, (248, 248, 245, 255))
        draw = ImageDraw.Draw(canvas)

        frame_margin = int(width * 0.075)
        photo_box = (
            frame_margin,
            int(height * 0.18),
            width - frame_margin,
            height - int(height * 0.075),
        )
        card_width = int(width * 0.36)
        card_height = int(height * 0.30)
        card_x = (width - card_width) // 2
        card_y = int(height * 0.065)

        _paste_color_photo(canvas, source_image, photo_box)
        _draw_editorial_marks(
            draw=draw,
            width=width,
            height=height,
            card_x=card_x,
            card_y=card_y,
            card_width=card_width,
            primary_color=primary_color,
            secondary_color=secondary_color,
        )
        _draw_text_card(
            draw=draw,
            title=title,
            subtitle=subtitle,
            x=card_x,
            y=card_y,
            width=card_width,
            height=card_height,
            canvas_width=width,
            canvas_height=height,
            primary_color=primary_color,
            text_color=text_color,
            title_font=title_font,
            subtitle_font=subtitle_font,
        )
        _draw_side_label(
            draw=draw,
            x=card_x + card_width + int(width * 0.028),
            y=card_y + int(height * 0.015),
            canvas_width=width,
            text_color="#222222",
            subtitle_font=subtitle_font,
        )

        if logo_file:
            canvas = _paste_logo(canvas, logo_file, logo_position)

        canvas.convert("RGB").save(image_path, format="PNG")

    return image_path


def _paste_color_photo(canvas, source_image, photo_box):
    x1, y1, x2, y2 = photo_box
    photo_width = x2 - x1
    photo_height = y2 - y1
    resampling = getattr(Image, "Resampling", Image).LANCZOS

    photo = ImageOps.fit(
        source_image.convert("RGB"),
        (photo_width, photo_height),
        method=resampling,
    )
    photo = ImageEnhance.Contrast(photo).enhance(1.08)
    photo = ImageEnhance.Color(photo).enhance(1.05)
    canvas.alpha_composite(photo.convert("RGBA"), (x1, y1))


def _draw_editorial_marks(
    draw,
    width,
    height,
    card_x,
    card_y,
    card_width,
    primary_color,
    secondary_color,
):
    stroke = max(3, int(width * 0.006))
    line_y = card_y + int(height * 0.145)
    left_start = int(width * 0.075)
    left_end = card_x - int(width * 0.025)
    right_start = card_x + card_width + int(width * 0.025)
    right_end = width - int(width * 0.075)

    draw.line(
        [(left_start, line_y), (left_end, line_y)],
        fill=_hex_to_rgba(primary_color or "#111111", alpha=255),
        width=stroke,
    )
    draw.line(
        [(right_start, line_y), (right_end, line_y)],
        fill=_hex_to_rgba(secondary_color or primary_color, alpha=255),
        width=stroke,
    )
    draw.rectangle(
        [
            (card_x - int(width * 0.018), card_y + int(height * 0.02)),
            (card_x + int(width * 0.018), card_y + int(height * 0.06)),
        ],
        fill=_hex_to_rgba(secondary_color or primary_color, alpha=255),
    )


def _draw_text_card(
    draw,
    title,
    subtitle,
    x,
    y,
    width,
    height,
    canvas_width,
    canvas_height,
    primary_color,
    text_color,
    title_font,
    subtitle_font,
):
    draw.rectangle(
        [(x, y), (x + width, y + height)],
        fill=_hex_to_rgba(primary_color or "#111111", alpha=238),
    )

    padding_x = int(canvas_width * 0.035)
    content_width = width - padding_x * 2
    current_y = y + int(canvas_height * 0.068)
    title_font_file, title_lines = _get_wrapped_font(
        draw=draw,
        text=(title or "").strip().upper(),
        max_width=content_width,
        initial_size=int(canvas_width * TITLE_FONT_SIZE_RATIO),
        min_size=int(canvas_width * 0.028),
        text_font=title_font,
        max_lines=2,
    )
    subtitle_font_file = _get_text_font(
        int(canvas_width * SUBTITLE_FONT_SIZE_RATIO),
        subtitle_font,
    )
    subtitle_lines = _wrap_text_breaking_long_words(
        (subtitle or "").strip(),
        subtitle_font_file,
        content_width,
        draw,
    )[:3]
    line_gap = max(4, int(canvas_height * 0.007))

    for line in title_lines:
        draw.text(
            (x + padding_x, current_y),
            line,
            font=title_font_file,
            fill=_hex_to_rgba(text_color or "#FFFFFF", alpha=255),
        )
        bbox = draw.textbbox((0, 0), line, font=title_font_file)
        current_y += bbox[3] - bbox[1] + line_gap

    if title_lines and subtitle_lines:
        current_y += int(canvas_height * 0.012)
        draw.line(
            [
                (x + padding_x, current_y),
                (x + padding_x + int(content_width * 0.28), current_y),
            ],
            fill=_hex_to_rgba(text_color or "#FFFFFF", alpha=180),
            width=max(1, int(canvas_width * 0.003)),
        )
        current_y += int(canvas_height * 0.018)

    for line in subtitle_lines:
        draw.text(
            (x + padding_x, current_y),
            line,
            font=subtitle_font_file,
            fill=_hex_to_rgba(text_color or "#FFFFFF", alpha=230),
        )
        bbox = draw.textbbox((0, 0), line, font=subtitle_font_file)
        current_y += bbox[3] - bbox[1] + line_gap


def _draw_side_label(draw, x, y, canvas_width, text_color, subtitle_font):
    font = _get_text_font(
        int(canvas_width * SIDE_LABEL_FONT_SIZE_RATIO),
        subtitle_font,
    )
    label = "NOTE"
    spacing = max(9, int(canvas_width * 0.012))
    current_y = y

    for character in label:
        if character == " ":
            current_y += spacing
            continue

        draw.text(
            (x, current_y),
            character,
            font=font,
            fill=_hex_to_rgba(text_color, alpha=255),
        )
        current_y += spacing


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
