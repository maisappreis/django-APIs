from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
import httpx

from .models import Post
from .operations import (
    apply_brand_defaults,
    build_post_visual_settings,
    create_post_batch,
    create_posts_from_generation_result,
    get_brand_by_id_for_user,
    get_brand_for_user,
    get_future_scheduled_posts,
    get_or_create_brand,
    get_user_brands,
    mark_batch_completed,
    mark_batch_failed,
    prepare_post_download,
    save_brand_reference_images,
    sync_brand_logo,
    update_brand_manual_identity,
)
from .presenters import (
    get_defaults_from_brand,
    serialize_brand,
    serialize_post_generation,
)
from .serializers import (
    BrandInputSerializer,
    BrandOutputSerializer,
    ContentAgentBootstrapSerializer,
    PostBatchOutputSerializer,
    PostGenerationInputSerializer,
    PostImageRenderInputSerializer,
)
from .services import (
    analyze_brand_visual_identity,
    generate_post_batch_content,
    rerender_post_image,
)


class ContentAgentBootstrapAPIView(APIView):
    def get(self, request):
        brands = get_user_brands(request.user)
        default_brand = brands.first()
        brand_count = brands.count()
        data = {
            "brand": {
                "has_brand": brand_count > 0,
                "default_brand_id": default_brand.id if default_brand else None,
                "brand_count": brand_count,
            },
            "defaults": get_defaults_from_brand(default_brand),
        }
        serializer = ContentAgentBootstrapSerializer(data)

        return Response(serializer.data)


class BrandListAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        brands = get_user_brands(request.user)
        serializer = BrandOutputSerializer(
            [serialize_brand(brand) for brand in brands],
            many=True,
        )

        return Response(serializer.data)

    @extend_schema(
        summary="Cria uma marca",
        description=(
            "Cria ou reutiliza uma marca do usuario autenticado.\n\n"
            "Campos obrigatorios: `business_name`, `niche`, "
            "`primary_color`, `secondary_color`, `tertiary_color`, "
            "`text_color`, `text_font`.\n\n"
            "Campos opcionais na criacao: `reference_image_1`, "
            "`reference_image_2`, `logo_position`.\n\n"
            "Campos que nao devem ser enviados na criacao: "
            "`visual_identity_summary`, `visual_identity_prompt`, "
            "`reference_image_1_url`, `reference_image_2_url`, `logo_url`.\n\n"
            "Quando `reference_image_1` ou `reference_image_2` forem "
            "enviadas, a API salva as referencias e tenta capturar a "
            "identidade visual por IA."
        ),
        request=BrandInputSerializer,
        responses={status.HTTP_201_CREATED: BrandOutputSerializer},
    )
    def post(self, request):
        input_serializer = BrandInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data

        brand = get_or_create_brand(
            user=request.user,
            business_name=data["business_name"],
            niche=data["niche"],
        )
        brand = update_brand_manual_identity(brand, data)

        if data.get("reference_image_1") or data.get("reference_image_2"):
            brand = save_brand_reference_images(brand, data, request.user)

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

        output_serializer = BrandOutputSerializer(
            serialize_brand(brand)
        )

        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class CalendarPostsAPIView(APIView):
    def get(self, request):
        start_date, posts = get_future_scheduled_posts(request.user)

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
        brand = get_brand_by_id_for_user(
            request.user,
            data.get("brand_id"),
        ) or get_brand_for_user(
            user=request.user,
            business_name=data["business_name"],
            niche=data["niche"],
        )

        if not brand:
            return Response(
                {
                    "detail": (
                        "Voce precisa cadastrar uma marca antes de gerar "
                        "conteudo."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = apply_brand_defaults(data, brand, request.data)

        batch = create_post_batch(request.user, brand, data)
        sync_brand_logo(brand, data, request.user)

        try:
            result = generate_post_batch_content(data)
            saved_posts = create_posts_from_generation_result(
                user=request.user,
                brand=brand,
                batch=batch,
                data=data,
                result=result,
            )

            mark_batch_completed(batch, result["strategy_summary"])

            output_serializer = PostBatchOutputSerializer(
                {
                    "batch_id": batch.id,
                    "quantity": batch.quantity,
                    "strategy_summary": batch.strategy_summary,
                    "posts": [
                        serialize_post_generation(post)
                        for post in saved_posts
                    ],
                }
            )

            return Response(
                output_serializer.data,
                status=status.HTTP_201_CREATED,
            )

        except Exception as error:
            mark_batch_failed(batch, error)

            response_data = {
                "detail": "Erro ao gerar conteudo do post.",
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
            Post.objects.select_related("batch", "brand"),
            id=post_id,
            user=request.user,
        )
        input_serializer = PostImageRenderInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        visual_settings = build_post_visual_settings(
            post_generation,
            input_serializer.validated_data,
        )

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
            Post,
            id=post_id,
            user=request.user,
        )

        try:
            download = prepare_post_download(post_generation)
        except FileNotFoundError:
            return Response(
                {"detail": "Imagem do post nao encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except httpx.HTTPError:
            return Response(
                {"detail": "Nao foi possivel baixar a imagem do post."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if download["local_path"]:
            return FileResponse(
                download["local_path"].open("rb"),
                as_attachment=True,
                filename=download["filename"],
                content_type=download["content_type"],
            )

        response = HttpResponse(
            download["content"],
            content_type=download["content_type"],
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{download["filename"]}"'
        )

        return response
