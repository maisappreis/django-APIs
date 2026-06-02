from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta

from .models import GenerationStatus, PostGeneration, PostGenerationBatch
from .serializers import (
    PostGenerationBatchOutputSerializer,
    PostGenerationDefaultsSerializer,
    PostGenerationInputSerializer,
    PostImageRenderInputSerializer,
)
from .services import generate_post_batch_content, rerender_post_image
from .storage import (
    is_firebase_storage_enabled,
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


def serialize_post_generation(post_generation):
    return {
        "id": post_generation.id,
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


class PostGenerationDefaultsAPIView(APIView):
    def get(self, request):
        latest_batch = (
            PostGenerationBatch.objects.filter(user=request.user)
            .order_by("-created_at")
            .first()
        )
        serializer = PostGenerationDefaultsSerializer(
            get_defaults_from_batch(latest_batch)
        )

        return Response(serializer.data)


class GeneratePostContentAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        input_serializer = PostGenerationInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        data = input_serializer.validated_data

        batch = PostGenerationBatch.objects.create(
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

            if is_firebase_storage_enabled():
                batch.logo_url = upload_logo_file(
                    local_path=batch.logo.path,
                    user_id=request.user.id,
                )
                batch.save(update_fields=["logo_url"])

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
                    status=PostGeneration.Status.COMPLETED,
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
