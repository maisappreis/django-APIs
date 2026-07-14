from pathlib import Path

from django.conf import settings
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps


LOGO_MARGIN_RATIO = 0.04
LOGO_MAX_WIDTH_RATIO = 0.11
TEXT_MAX_WIDTH_RATIO = 0.82
TEXT_FONT_SIZE_RATIO = 0.075
IMAGE_QUALITY_ENHANCE_COLOR_FACTOR = 1.12
IMAGE_QUALITY_ENHANCE_CONTRAST_FACTOR = 1.08
IMAGE_QUALITY_ENHANCE_BRIGHTNESS_FACTOR = 1.03
IMAGE_QUALITY_ENHANCE_SHARPNESS_FACTOR = 1.10
IMAGE_QUALITY_ENHANCE_AUTOCONTRAST_CUTOFF = 1
IMAGE_QUALITY_ENHANCE_TEMPERATURE_FACTOR = 1.0
DEFAULT_IMAGE_QUALITY_SETTINGS = {
    "color_factor": IMAGE_QUALITY_ENHANCE_COLOR_FACTOR,
    "contrast_factor": IMAGE_QUALITY_ENHANCE_CONTRAST_FACTOR,
    "brightness_factor": IMAGE_QUALITY_ENHANCE_BRIGHTNESS_FACTOR,
    "sharpness_factor": IMAGE_QUALITY_ENHANCE_SHARPNESS_FACTOR,
    "autocontrast_cutoff": IMAGE_QUALITY_ENHANCE_AUTOCONTRAST_CUTOFF,
    "temperature_factor": IMAGE_QUALITY_ENHANCE_TEMPERATURE_FACTOR,
}

FONT_FILES_BY_NAME = {
    "dancingscript": (
        "DancingScript-SemiBold.ttf",
    ),
    "inter": (
        "Inter-Regular.ttf",
    ),
    "montserrat": (
        "Montserrat-Medium.ttf",
    ),
    "playfairdisplay": (
        "PlayfairDisplay-Medium.ttf",
    ),
    "poppins": (
        "Poppins-Regular.ttf",
    ),


    "playfair": (
        "PlayfairDisplay-Bold.ttf",
        "PlayfairDisplay-Regular.ttf",
    ),
    "roboto": (
        "Roboto-Bold.ttf",
        "Roboto-Regular.ttf",
    ),
    "opensans": (
        "OpenSans-Bold.ttf",
        "OpenSans-Regular.ttf",
    ),
    "lato": (
        "Lato-Bold.ttf",
        "Lato-Regular.ttf",
    ),
    "segoe": (
        "segoeuib.ttf",
        "segoeui.ttf",
    ),
    "trebuchet": (
        "trebucbd.ttf",
        "trebuc.ttf",
    ),
    "arial": (
        "arialbd.ttf",
        "arial.ttf",
        "Arial.ttf",
    ), 
}

FONT_SEARCH_DIRS = (
    Path(__file__).resolve().parent / "fonts",
    Path("C:/Windows/Fonts"),
)

FALLBACK_FONT_FILES = (
    "arialbd.ttf",
    "Arial.ttf",
    "arial.ttf",
    "segoeuib.ttf",
    "segoeui.ttf",
    "trebucbd.ttf",
    "trebuc.ttf",
)


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


def get_image_quality_settings(overrides=None):
    return {
        **DEFAULT_IMAGE_QUALITY_SETTINGS,
        **(overrides or {}),
    }


def enhance_post_image_quality(image_path, quality_settings=None):
    image_path = Path(image_path)
    quality_settings = get_image_quality_settings(quality_settings)

    with Image.open(image_path) as source_image:
        alpha_channel = None
        if source_image.mode in ("RGBA", "LA"):
            alpha_channel = source_image.convert("RGBA").getchannel("A")

        image = source_image.convert("RGB")
        image = ImageOps.autocontrast(
            image,
            cutoff=quality_settings["autocontrast_cutoff"],
        )
        image = ImageEnhance.Color(image).enhance(
            quality_settings["color_factor"],
        )
        image = ImageEnhance.Contrast(image).enhance(
            quality_settings["contrast_factor"],
        )
        image = ImageEnhance.Brightness(image).enhance(
            quality_settings["brightness_factor"],
        )
        image = _apply_temperature(
            image,
            quality_settings["temperature_factor"],
        )
        image = ImageEnhance.Sharpness(image).enhance(
            quality_settings["sharpness_factor"],
        )

        if alpha_channel:
            image = image.convert("RGBA")
            image.putalpha(alpha_channel)

        image.save(image_path, format="PNG")

    return image_path


def _apply_temperature(image, temperature_factor):
    if temperature_factor == 1:
        return image

    shift = temperature_factor - 1
    red_factor = 1 + shift * 0.35
    green_factor = 1 - shift * 0.20
    blue_factor = 1 + shift * 0.18

    red, green, blue = image.split()

    return Image.merge(
        "RGB",
        (
            red.point(lambda value: _clamp_channel(value * red_factor)),
            green.point(lambda value: _clamp_channel(value * green_factor)),
            blue.point(lambda value: _clamp_channel(value * blue_factor)),
        ),
    )


def _clamp_channel(value):
    return max(0, min(255, int(value)))


def apply_center_text_to_image(
    image_path,
    text,
    text_font=None,
    text_color="#FFFFFF",
):
    if not text:
        return image_path

    image_path = Path(image_path)

    with Image.open(image_path).convert("RGBA") as base_image:
        draw = ImageDraw.Draw(base_image)
        font = _get_center_text_font(base_image.width, text_font)
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
            fill=_hex_to_rgba(text_color),
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


def _hex_to_rgba(hex_color, alpha=255):
    hex_color = (hex_color or "#FFFFFF").lstrip("#")

    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
        alpha,
    )


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


def _get_center_text_font(base_width, text_font=None):
    font_size = int(base_width * TEXT_FONT_SIZE_RATIO)

    return _get_text_font(font_size, text_font)


def _get_text_font(font_size, text_font=None):
    font_key = _get_font_key(text_font)

    for font_path in _get_font_candidate_paths(font_key):
        try:
            return ImageFont.truetype(str(font_path), font_size)
        except OSError:
            continue

    return ImageFont.load_default()


def _get_font_candidate_paths(font_key):
    font_files = (
        *FONT_FILES_BY_NAME.get(font_key, ()),
        *FALLBACK_FONT_FILES,
    )

    for font_file in font_files:
        font_path = Path(font_file)

        if font_path.is_absolute():
            yield font_path
            continue

        for font_dir in _get_font_search_dirs():
            yield font_dir / font_file


def _get_font_search_dirs():
    configured_dir = getattr(settings, "CONTENT_AGENT_FONT_DIR", "")

    if configured_dir:
        yield Path(configured_dir)

    yield from FONT_SEARCH_DIRS


def _get_font_key(text_font):
    normalized_font = _normalize_font_name(text_font)

    if normalized_font in FONT_FILES_BY_NAME:
        return normalized_font

    for font_key in FONT_FILES_BY_NAME:
        if font_key in normalized_font:
            return font_key

    return normalized_font


def _normalize_font_name(text_font):
    if not text_font:
        return ""

    font_name = str(text_font).split(",")[0].strip().strip("'\"")

    return "".join(
        character.lower()
        for character in font_name
        if character.isalnum()
    )


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
