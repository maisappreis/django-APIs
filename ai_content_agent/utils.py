from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


LOGO_MARGIN_RATIO = 0.04
LOGO_MAX_WIDTH_RATIO = 0.11
TEXT_MAX_WIDTH_RATIO = 0.82
TEXT_FONT_SIZE_RATIO = 0.075


def apply_logo_to_image(image_path, logo_file, position="bottom_right"):
    image_path = Path(image_path)

    with Image.open(image_path).convert("RGBA") as base_image:
        with Image.open(logo_file).convert("RGBA") as logo_image:
            logo_image = _resize_logo(logo_image, base_image.width)
            coordinates = _get_logo_coordinates(
                base_image=base_image,
                logo_image=logo_image,
                position=position,
            )

            base_image.alpha_composite(logo_image, coordinates)
            base_image.convert("RGB").save(image_path, format="PNG")

    return image_path


def apply_center_text_to_image(image_path, text):
    if not text:
        return image_path

    image_path = Path(image_path)

    with Image.open(image_path).convert("RGBA") as base_image:
        draw = ImageDraw.Draw(base_image)
        font = _get_center_text_font(base_image.width)
        lines = _wrap_text(
            text=text,
            font=font,
            max_width=int(base_image.width * TEXT_MAX_WIDTH_RATIO),
            draw=draw,
        )
        text_block = "\n".join(lines)
        text_bbox = draw.multiline_textbbox(
            (0, 0),
            text_block,
            font=font,
            spacing=10,
        )
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        coordinates = (
            (base_image.width - text_width) // 2,
            (base_image.height - text_height) // 2,
        )

        draw.multiline_text(
            coordinates,
            text_block,
            font=font,
            fill=(255, 255, 255, 255),
            anchor=None,
            align="center",
            spacing=10,
        )
        base_image.convert("RGB").save(image_path, format="PNG")

    return image_path


def _resize_logo(logo_image, base_width):
    max_logo_width = int(base_width * LOGO_MAX_WIDTH_RATIO)

    if logo_image.width <= max_logo_width:
        return logo_image

    ratio = max_logo_width / logo_image.width
    new_size = (
        max_logo_width,
        int(logo_image.height * ratio),
    )

    return logo_image.resize(new_size, Image.LANCZOS)


def _get_logo_coordinates(base_image, logo_image, position):
    margin = int(base_image.width * LOGO_MARGIN_RATIO)

    positions = {
        "top_left": (
            margin,
            margin,
        ),
        "top_right": (
            base_image.width - logo_image.width - margin,
            margin,
        ),
        "bottom_left": (
            margin,
            base_image.height - logo_image.height - margin,
        ),
        "bottom_right": (
            base_image.width - logo_image.width - margin,
            base_image.height - logo_image.height - margin,
        ),
        "top_center": (
            (base_image.width - logo_image.width) // 2,
            margin,
        ),
        "bottom_center": (
            (base_image.width - logo_image.width) // 2,
            base_image.height - logo_image.height - margin,
        ),
    }

    return positions.get(position, positions["bottom_right"])


def _get_center_text_font(base_width):
    font_size = int(base_width * TEXT_FONT_SIZE_RATIO)

    for font_path in (
        "C:/Windows/Fonts/PlayfairDisplay-Bold.ttf",
        "C:/Windows/Fonts/Montserrat-Bold.ttf",
        "C:/Windows/Fonts/Poppins-Bold.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/trebucbd.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/Arial.ttf",
    ):
        try:
            return ImageFont.truetype(font_path, font_size)
        except OSError:
            continue

    return ImageFont.load_default()


def _wrap_text(text, font, max_width, draw):
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        candidate = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), candidate, font=font)
        candidate_width = bbox[2] - bbox[0]

        if candidate_width <= max_width:
            current_line = candidate
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines
