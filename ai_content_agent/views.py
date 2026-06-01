from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from .models import GenerationStatus, PostGeneration, PostGenerationBatch
from .serializers import (
    PostGenerationBatchOutputSerializer,
    PostGenerationInputSerializer,
)
from .services import generate_post_batch_content


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
            use_templates=data["use_templates"],
        )

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
                    image_url=post_data["image_url"],
                    template=post_data["template"],
                    post_order=post_data["order"],
                    scheduled_date=scheduled_date,
                    idea=post_data["idea"],
                    status=PostGeneration.Status.COMPLETED,
                )
                saved_posts.append(
                    {
                        "id": post_generation.id,
                        "date": post_generation.scheduled_date,
                        "caption": post_generation.caption,
                        "hashtags": post_generation.hashtags,
                        "image_prompt": post_generation.image_prompt,
                        "image_text": post_generation.image_text,
                        "image_url": post_generation.image_url,
                        "template": post_generation.template,
                    }
                )

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
