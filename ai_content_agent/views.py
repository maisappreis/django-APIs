from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse
import httpx

from .models import Brand, GenerationStatus, PostGeneration, PostGenerationBatch
from .serializers import (
    BrandVisualIdentityInputSerializer,
    BrandVisualIdentityOutputSerializer,
    PostGenerationBatchOutputSerializer,
    PostGenerationDefaultsSerializer,
    PostGenerationInputSerializer,
    PostImageRenderInputSerializer,
)
from .services import (
    analyze_brand_visual_identity,
    generate_post_batch_content,
    rerender_post_image,
)
from .storage import (
    is_firebase_storage_enabled,
    upload_brand_reference_file,
    upload_generated_post_file,
    upload_logo_file,
)


DEFAULT_FORM_VALUES = {
    "business_name": "",
    "niche": "",
    "logo_url": "",
    "text_color": "#FFFFFF",
    "text_font": "",
    "color_palette": {
        "primary_color": "#006C44",
        "secondary_color": "#1FD794",
        "tertiary_color": "#98C8B6",
    },
    "logo_position": "bottom_right",
}


def get_or_create_brand(user, business_name, niche):
    brand = (
        Brand.objects.filter(
            user=user,
            business_name=business_name,
            niche=niche,
        )
        .order_by("-updated_at")
        .first()
    )

    if brand:
        return brand

    return Brand.objects.create(
        user=user,
        business_name=business_name,
        niche=niche,
    )


def apply_brand_defaults(data, brand, request_data):
    fields = [
        "primary_color",
        "secondary_color",
        "tertiary_color",
        "text_color",
        "text_font",
        "logo_position",
    ]

    for field in fields:
        if field not in request_data:
            data[field] = getattr(brand, field)

    data["brand_visual_identity"] = brand.visual_identity_prompt

    return data


def serialize_brand(brand):
    return {
        "id": brand.id,
        "business_name": brand.business_name,
        "niche": brand.niche,
        "visual_identity_summary": brand.visual_identity_summary,
        "visual_identity_prompt": brand.visual_identity_prompt,
        "reference_image_1_url": (
            brand.reference_image_1_url
            or (brand.reference_image_1.url if brand.reference_image_1 else "")
        ),
        "reference_image_2_url": (
            brand.reference_image_2_url
            or (brand.reference_image_2.url if brand.reference_image_2 else "")
        ),
        "logo_url": brand.logo_url,
        "primary_color": brand.primary_color,
        "secondary_color": brand.secondary_color,
        "tertiary_color": brand.tertiary_color,
        "text_color": brand.text_color,
        "text_font": brand.text_font,
        "logo_position": brand.logo_position,
    }


def get_available_post_dates(user, quantity):
    current_date = timezone.localdate()
    occupied_dates = set(
        PostGeneration.objects.filter(
            user=user,
            scheduled_date__gte=current_date,
        )
        .exclude(scheduled_date__isnull=True)
        .values_list("scheduled_date", flat=True)
    )
    available_dates = []

    while len(available_dates) < quantity:
        if current_date not in occupied_dates:
            available_dates.append(current_date)
            occupied_dates.add(current_date)

        current_date += timedelta(days=1)

    return available_dates


def get_defaults_from_batch(batch):
    if not batch:
        return DEFAULT_FORM_VALUES

    logo_url = batch.logo_url or (batch.logo.url if batch.logo else "")

    return {
        "business_name": batch.business_name,
        "niche": batch.niche,
        "logo_url": logo_url,
        "text_color": batch.text_color,
        "text_font": batch.text_font,
        "color_palette": {
            "primary_color": batch.primary_color,
            "secondary_color": batch.secondary_color,
            "tertiary_color": batch.tertiary_color,
        },
        "logo_position": batch.logo_position,
    }


def get_defaults_from_brand(brand):
    if not brand:
        return DEFAULT_FORM_VALUES

    return {
        "business_name": brand.business_name,
        "niche": brand.niche,
        "logo_url": brand.logo_url,
        "text_color": brand.text_color,
        "text_font": brand.text_font,
        "color_palette": {
            "primary_color": brand.primary_color,
            "secondary_color": brand.secondary_color,
            "tertiary_color": brand.tertiary_color,
        },
        "logo_position": brand.logo_position,
    }


def serialize_post_generation(post_generation):
    return {
        "id": post_generation.id,
        "brand_id": post_generation.brand_id,
        "date": post_generation.scheduled_date,
        "caption": post_generation.caption,
        "hashtags": post_generation.hashtags,
        "image_prompt": post_generation.image_prompt,
        "base_image_url": post_generation.base_image_url,
        "image_text": post_generation.image_text,
        "image_url": post_generation.image_url,
        "template": post_generation.template,
        "primary_color": post_generation.primary_color,
        "secondary_color": post_generation.secondary_color,
        "tertiary_color": post_generation.tertiary_color,
        "text_color": post_generation.text_color,
        "text_font": post_generation.text_font,
        "logo_position": post_generation.logo_position,
    }


def get_download_filename(post_generation):
    parsed_url = urlparse(post_generation.image_url)
    extension = Path(parsed_url.path).suffix or ".png"
    return f"post-{post_generation.id}{extension}"


class PostGenerationDefaultsAPIView(APIView):
    def get(self, request):
        latest_brand = (
            Brand.objects.filter(user=request.user)
            .order_by("-updated_at")
            .first()
        )

        if latest_brand:
            serializer = PostGenerationDefaultsSerializer(
                get_defaults_from_brand(latest_brand)
            )

            return Response(serializer.data)

        latest_batch = (
            PostGenerationBatch.objects.filter(user=request.user)
            .order_by("-created_at")
            .first()
        )
        serializer = PostGenerationDefaultsSerializer(
            get_defaults_from_batch(latest_batch)
        )

        return Response(serializer.data)


class BrandListAPIView(APIView):
    def get(self, request):
        brands = Brand.objects.filter(user=request.user).order_by(
            "-updated_at"
        )
        serializer = BrandVisualIdentityOutputSerializer(
            [serialize_brand(brand) for brand in brands],
            many=True,
        )

        return Response(serializer.data)


class BrandVisualIdentityAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        input_serializer = BrandVisualIdentityInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data

        brand = get_or_create_brand(
            user=request.user,
            business_name=data["business_name"],
            niche=data["niche"],
        )
        brand.reference_image_1 = data["reference_image_1"]

        if data.get("reference_image_2"):
            brand.reference_image_2 = data["reference_image_2"]

        brand.save()

        if is_firebase_storage_enabled():
            if brand.reference_image_1:
                brand.reference_image_1_url = upload_brand_reference_file(
                    local_path=brand.reference_image_1.path,
                    user_id=request.user.id,
                    brand_id=brand.id,
                    index=1,
                )

            if brand.reference_image_2:
                brand.reference_image_2_url = upload_brand_reference_file(
                    local_path=brand.reference_image_2.path,
                    user_id=request.user.id,
                    brand_id=brand.id,
                    index=2,
                )

            brand.save(
                update_fields=[
                    "reference_image_1_url",
                    "reference_image_2_url",
                    "updated_at",
                ]
            )

        try:
            brand = analyze_brand_visual_identity(brand)
        except Exception as error:
            response_data = {
                "detail": "Erro ao captar identidade visual da marca.",
            }

            if settings.DEBUG:
                response_data["error"] = str(error)

            return Response(
                response_data,
                status=status.HTTP_502_BAD_GATEWAY,
            )

        output_serializer = BrandVisualIdentityOutputSerializer(
            serialize_brand(brand)
        )

        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class CalendarPostsAPIView(APIView):
    def get(self, request):
        start_date = timezone.localdate()

        posts = (
            PostGeneration.objects.filter(
                user=request.user,
                scheduled_date__gte=start_date,
            )
            .exclude(scheduled_date__isnull=True)
            .order_by("scheduled_date", "post_order", "created_at")
        )

        return Response(
            {
                "start": start_date,
                "posts": [
                    serialize_post_generation(post_generation)
                    for post_generation in posts
                ],
            }
        )


class GeneratePostContentAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        input_serializer = PostGenerationInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        data = input_serializer.validated_data
        brand = get_or_create_brand(
            user=request.user,
            business_name=data["business_name"],
            niche=data["niche"],
        )
        data = apply_brand_defaults(data, brand, request.data)

        batch = PostGenerationBatch.objects.create(
            brand=brand,
            user=request.user,
            business_name=data["business_name"],
            niche=data["niche"],
            objective=data["objective"],
            tone=data["tone"],
            theme=data["theme"],
            quantity=data["quantity"],
            logo=data.get("logo"),
            use_templates=data["use_templates"],
            primary_color=data["primary_color"],
            secondary_color=data["secondary_color"],
            tertiary_color=data["tertiary_color"],
            text_color=data["text_color"],
            text_font=data["text_font"],
            logo_position=data["logo_position"],
        )

        if batch.logo:
            data["logo"] = batch.logo.path
            brand.logo_url = batch.logo.url

            if is_firebase_storage_enabled():
                batch.logo_url = upload_logo_file(
                    local_path=batch.logo.path,
                    user_id=request.user.id,
                )
                brand.logo_url = batch.logo_url
                batch.save(update_fields=["logo_url"])

            brand.save(update_fields=["logo_url", "updated_at"])

        try:
            result = generate_post_batch_content(data)
            saved_posts = []
            available_dates = get_available_post_dates(
                request.user,
                len(result["posts"]),
            )

            for index, post_data in enumerate(result["posts"]):
                scheduled_date = available_dates[index]
                post_generation = PostGeneration.objects.create(
                    batch=batch,
                    brand=brand,
                    user=request.user,
                    business_name=data["business_name"],
                    niche=data["niche"],
                    objective=data["objective"],
                    tone=data["tone"],
                    theme=post_data["idea"]["theme"],
                    caption=post_data["caption"],
                    hashtags=post_data["hashtags"],
                    image_prompt=post_data["image_prompt"],
                    image_text=post_data["image_text"],
                    base_image_url=post_data["base_image_url"],
                    image_url=post_data["image_url"],
                    template=post_data["template"],
                    primary_color=post_data["primary_color"],
                    secondary_color=post_data["secondary_color"],
                    tertiary_color=post_data["tertiary_color"],
                    text_color=post_data["text_color"],
                    text_font=post_data["text_font"],
                    logo_position=post_data["logo_position"],
                    post_order=post_data["order"],
                    scheduled_date=scheduled_date,
                    idea=post_data["idea"],
                    status=GenerationStatus.COMPLETED,
                )

                if is_firebase_storage_enabled():
                    post_generation.base_image_url = upload_generated_post_file(
                        local_path=post_data["base_absolute_path"],
                        user_id=request.user.id,
                        post_id=post_generation.id,
                        kind="base",
                    )
                    post_generation.image_url = upload_generated_post_file(
                        local_path=post_data["final_absolute_path"],
                        user_id=request.user.id,
                        post_id=post_generation.id,
                        kind="final",
                    )
                    post_generation.save(
                        update_fields=[
                            "base_image_url",
                            "image_url",
                        ]
                    )

                saved_posts.append(serialize_post_generation(post_generation))

            batch.strategy_summary = result["strategy_summary"]
            batch.status = GenerationStatus.COMPLETED
            batch.save()

            output_serializer = PostGenerationBatchOutputSerializer(
                {
                    "batch_id": batch.id,
                    "quantity": batch.quantity,
                    "strategy_summary": batch.strategy_summary,
                    "posts": saved_posts,
                }
            )

            return Response(
                output_serializer.data,
                status=status.HTTP_201_CREATED,
            )

        except Exception as error:
            batch.status = GenerationStatus.FAILED
            batch.error_message = str(error)
            batch.save()

            response_data = {
                "detail": "Erro ao gerar conteúdo do post.",
            }

            if settings.DEBUG:
                response_data["error"] = str(error)

            return Response(
                response_data,
                status=status.HTTP_502_BAD_GATEWAY,
            )


class RerenderPostImageAPIView(APIView):
    def patch(self, request, post_id):
        post_generation = get_object_or_404(
            PostGeneration.objects.select_related("batch"),
            id=post_id,
            user=request.user,
        )
        input_serializer = PostImageRenderInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        visual_settings = {
            "image_text": post_generation.image_text,
            "template": post_generation.template or "none",
            "primary_color": post_generation.primary_color,
            "secondary_color": post_generation.secondary_color,
            "tertiary_color": post_generation.tertiary_color,
            "text_color": post_generation.text_color,
            "text_font": post_generation.text_font,
            "logo_position": post_generation.logo_position,
            **input_serializer.validated_data,
        }

        try:
            rerendered_post = rerender_post_image(
                post=post_generation,
                visual_settings=visual_settings,
            )
        except Exception as error:
            response_data = {
                "detail": "Erro ao renderizar imagem do post.",
            }

            if settings.DEBUG:
                response_data["error"] = str(error)

            return Response(
                response_data,
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(serialize_post_generation(rerendered_post))


class DownloadPostImageAPIView(APIView):
    def get(self, request, post_id):
        post_generation = get_object_or_404(
            PostGeneration,
            id=post_id,
            user=request.user,
        )
        filename = get_download_filename(post_generation)

        if post_generation.image_url.startswith(settings.MEDIA_URL):
            relative_path = post_generation.image_url.removeprefix(
                settings.MEDIA_URL
            )
            image_path = Path(settings.MEDIA_ROOT) / relative_path

            if not image_path.exists():
                return Response(
                    {"detail": "Imagem do post não encontrada."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            return FileResponse(
                image_path.open("rb"),
                as_attachment=True,
                filename=filename,
                content_type="image/png",
            )

        try:
            image_response = httpx.get(post_generation.image_url, timeout=30)
            image_response.raise_for_status()
        except httpx.HTTPError:
            return Response(
                {"detail": "Não foi possível baixar a imagem do post."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        response = HttpResponse(
            image_response.content,
            content_type=image_response.headers.get(
                "content-type",
                "image/png",
            ),
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response
