from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
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
    get_future_scheduled_posts,
    get_latest_batch,
    get_latest_brand,
    get_or_create_brand,
    get_user_brands,
    mark_batch_completed,
    mark_batch_failed,
    prepare_post_download,
    save_brand_reference_images,
    sync_brand_logo,
)
from .presenters import (
    get_defaults_from_batch,
    get_defaults_from_brand,
    serialize_brand,
    serialize_post_generation,
)
from .serializers import (
    BrandVisualIdentityInputSerializer,
    BrandVisualIdentityOutputSerializer,
    PostBatchOutputSerializer,
    PostGenerationDefaultsSerializer,
    PostGenerationInputSerializer,
    PostImageRenderInputSerializer,
)
from .services import (
    analyze_brand_visual_identity,
    generate_post_batch_content,
    rerender_post_image,
)


class PostDefaultsAPIView(APIView):
    def get(self, request):
        latest_brand = get_latest_brand(request.user)

        if latest_brand:
            serializer = PostGenerationDefaultsSerializer(
                get_defaults_from_brand(latest_brand)
            )

            return Response(serializer.data)

        latest_batch = get_latest_batch(request.user)
        serializer = PostGenerationDefaultsSerializer(
            get_defaults_from_batch(latest_batch)
        )

        return Response(serializer.data)


class BrandListAPIView(APIView):
    def get(self, request):
        brands = get_user_brands(request.user)
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

        output_serializer = BrandVisualIdentityOutputSerializer(
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
        brand = get_or_create_brand(
            user=request.user,
            business_name=data["business_name"],
            niche=data["niche"],
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
