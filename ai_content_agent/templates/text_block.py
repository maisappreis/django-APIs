from ai_content_agent.helpers import _hex_to_rgba
from ai_content_agent.utils import _get_text_font, _wrap_text


TITLE_FONT_SIZE_RATIO = 0.074
SUBTITLE_FONT_SIZE_RATIO = 0.039


def draw_title_subtitle_block(
    draw,
    width,
    height,
    title="",
    subtitle="",
    title_font=None,
    subtitle_font=None,
    text_color="#FFFFFF",
    max_width=None,
    anchor_x=None,
    anchor_y=None,
    horizontal_align="center",
    vertical_anchor="center",
):
    title = (title or "").strip()
    subtitle = (subtitle or "").strip()

    if not title and not subtitle:
        return

    title_font_file = _get_text_font(
        int(width * TITLE_FONT_SIZE_RATIO),
        title_font,
    )
    subtitle_font_file = _get_text_font(
        int(width * SUBTITLE_FONT_SIZE_RATIO),
        subtitle_font,
    )
    max_width = max_width or int(width * 0.72)
    title_lines = (
        _wrap_text(title, title_font_file, max_width, draw)
        if title
        else []
    )
    subtitle_lines = (
        _wrap_text(subtitle, subtitle_font_file, max_width, draw)
        if subtitle
        else []
    )
    line_gap = max(6, int(height * 0.012))
    section_gap = max(10, int(height * 0.018))
    block = _measure_text_block(
        draw=draw,
        title_lines=title_lines,
        subtitle_lines=subtitle_lines,
        title_font=title_font_file,
        subtitle_font=subtitle_font_file,
        line_gap=line_gap,
        section_gap=section_gap,
    )
    block_x = _get_block_x(
        anchor_x=anchor_x if anchor_x is not None else width // 2,
        block_width=block["width"],
        horizontal_align=horizontal_align,
    )
    block_y = _get_block_y(
        anchor_y=anchor_y if anchor_y is not None else height // 2,
        block_height=block["height"],
        vertical_anchor=vertical_anchor,
    )

    _draw_text_lines(
        draw=draw,
        lines=title_lines,
        font=title_font_file,
        color=text_color,
        block_x=block_x,
        block_y=block_y,
        block_width=block["width"],
        horizontal_align=horizontal_align,
        line_gap=line_gap,
    )

    subtitle_y = block_y + block["title_height"]
    if title_lines and subtitle_lines:
        subtitle_y += section_gap

    _draw_text_lines(
        draw=draw,
        lines=subtitle_lines,
        font=subtitle_font_file,
        color=text_color,
        block_x=block_x,
        block_y=subtitle_y,
        block_width=block["width"],
        horizontal_align=horizontal_align,
        line_gap=line_gap,
    )


def _measure_text_block(
    draw,
    title_lines,
    subtitle_lines,
    title_font,
    subtitle_font,
    line_gap,
    section_gap,
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
        total_height += section_gap

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


def _get_block_x(anchor_x, block_width, horizontal_align):
    if horizontal_align == "left":
        return anchor_x

    if horizontal_align == "right":
        return anchor_x - block_width

    return anchor_x - block_width // 2


def _get_block_y(anchor_y, block_height, vertical_anchor):
    if vertical_anchor == "top":
        return anchor_y

    if vertical_anchor == "bottom":
        return anchor_y - block_height

    return anchor_y - block_height // 2


def _draw_text_lines(
    draw,
    lines,
    font,
    color,
    block_x,
    block_y,
    block_width,
    horizontal_align,
    line_gap,
):
    current_y = block_y

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        line_height = bbox[3] - bbox[1]

        if horizontal_align == "center":
            line_x = block_x + (block_width - line_width) // 2
        elif horizontal_align == "right":
            line_x = block_x + block_width - line_width
        else:
            line_x = block_x

        draw.text(
            (line_x, current_y),
            line,
            font=font,
            fill=_hex_to_rgba(color, alpha=255),
        )
        current_y += line_height + line_gap
