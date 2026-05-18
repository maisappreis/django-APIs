from pathlib import Path
from PIL import Image


LOGO_MARGIN_RATIO = 0.04
LOGO_MAX_WIDTH_RATIO = 0.11


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
