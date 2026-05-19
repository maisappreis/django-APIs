from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings

from .models import PostGeneration
from .serializers import (
    PostGenerationInputSerializer,
    PostGenerationOutputSerializer,
)
from .services import generate_post_content


class GeneratePostContentAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        input_serializer = PostGenerationInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        data = input_serializer.validated_data

        post_generation = PostGeneration.objects.create(
            user=request.user,
            business_name=data["business_name"],
            niche=data["niche"],
            objective=data["objective"],
            tone=data["tone"],
            theme=data["theme"],
        )

        try:
            result = generate_post_content(data)

            post_generation.caption = result["caption"]
            post_generation.hashtags = result["hashtags"]
            post_generation.image_prompt = result["image_prompt"]
            post_generation.status = PostGeneration.Status.COMPLETED
            post_generation.save()

            output_serializer = PostGenerationOutputSerializer(result)

            return Response(
                output_serializer.data,
                status=status.HTTP_201_CREATED,
            )

        except Exception as error:
            post_generation.status = PostGeneration.Status.FAILED
            post_generation.error_message = str(error)
            post_generation.save()

            response_data = {
                "detail": "Erro ao gerar conteúdo do post.",
            }

            if settings.DEBUG:
                response_data["error"] = str(error)

            return Response(
                response_data,
                status=status.HTTP_502_BAD_GATEWAY,
            )
