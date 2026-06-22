from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image
from rest_framework.serializers import ValidationError

from ai_content_agent.serializers import (
    MAX_BRAND_LOGO_SIZE,
    validate_brand_logo,
)


def get_logo_file(image_format, content_type, extension):
    content = BytesIO()
    Image.new("RGB", (2, 2), "blue").save(content, format=image_format)

    return SimpleUploadedFile(
        f"logo.{extension}",
        content.getvalue(),
        content_type=content_type,
    )


class BrandLogoValidationTest(SimpleTestCase):
    def test_accepts_png_jpeg_and_webp(self):
        files = (
            get_logo_file("PNG", "image/png", "png"),
            get_logo_file("JPEG", "image/jpeg", "jpg"),
            get_logo_file("WEBP", "image/webp", "webp"),
        )

        for logo in files:
            with self.subTest(logo=logo.name):
                self.assertIs(validate_brand_logo(logo), logo)

    def test_rejects_logo_larger_than_3_mb(self):
        logo = SimpleUploadedFile(
            "logo.png",
            b"x" * (MAX_BRAND_LOGO_SIZE + 1),
            content_type="image/png",
        )

        with self.assertRaisesMessage(ValidationError, "no máximo 3 MB"):
            validate_brand_logo(logo)

    def test_rejects_gif_even_when_it_is_a_valid_image(self):
        logo = get_logo_file("GIF", "image/gif", "gif")

        with self.assertRaisesMessage(
            ValidationError,
            "formatos PNG, JPEG ou WebP",
        ):
            validate_brand_logo(logo)

    def test_rejects_content_that_is_not_an_image(self):
        logo = SimpleUploadedFile(
            "logo.png",
            b"not-an-image",
            content_type="image/png",
        )

        with self.assertRaisesMessage(ValidationError, "imagem válida"):
            validate_brand_logo(logo)
