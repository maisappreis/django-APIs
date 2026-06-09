from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
import httpx
from threading import Thread

from .models import Post, PostBatch
from .operations import (
    apply_brand_defaults,
    build_post_visual_settings,
    create_post_drafts_from_generation_result,
    create_post_batch,
    get_brand_by_id_for_user,
    get_brand_for_user,
    get_future_scheduled_posts,
    get_or_create_brand,
    get_user_brands,
    mark_batch_completed,
    mark_batch_failed,
    mark_batch_pending,
    mark_batch_pending_review,
    mark_post_completed,
    prepare_post_download,
    save_brand_reference_images,
    sync_brand_logo,
    update_post_draft_prompts,
    update_brand_manual_identity,
    update_batch_progress,
)
from .presenters import (
    serialize_brand,
    serialize_post_batch,
    serialize_post_generation,
)
from .serializers import (
    BrandInputSerializer,
    BrandOutputSerializer,
    BrandPatchSerializer,
    PostBatchOutputSerializer,
    PostGenerationInputSerializer,
    PostImageRenderInputSerializer,
    PostPromptApprovalSerializer,
)
from .services import (
    analyze_brand_visual_identity,
    generate_post_batch_draft_content,
    render_approved_post_image,
    rerender_post_image,
)


def run_post_generation_job(user_id, brand_id, batch_id, data):
    close_old_connections()

    try:
        user = get_user_model().objects.get(id=user_id)
        batch = PostBatch.objects.get(id=batch_id, user_id=user_id)
        brand = get_object_or_404(get_user_brands(user), id=brand_id)

        update_batch_progress(batch, 10)
        result = generate_post_batch_draft_content(data)
        update_batch_progress(batch, 70)

        create_post_drafts_from_generation_result(
            user=user,
            brand=brand,
            batch=batch,
            result=result,
        )

        mark_batch_pending_review(batch, result["strategy_summary"])
    except Exception as error:
        try:
            batch = PostBatch.objects.get(id=batch_id, user_id=user_id)
            mark_batch_failed(batch, error)
        except PostBatch.DoesNotExist:
            pass
    finally:
        close_old_connections()


def run_post_image_generation_job(user_id, batch_id):
    close_old_connections()

    try:
        batch = PostBatch.objects.get(id=batch_id, user_id=user_id)
        posts = list(
            batch.posts.select_related("brand")
            .filter(user_id=user_id)
            .order_by("scheduled_date", "post_order", "created_at")
        )
        total_posts = len(posts)

        update_batch_progress(batch, 5)

        if total_posts == 0:
            raise ValueError("No posts found for image generation.")

        for index, post in enumerate(posts):
            render_approved_post_image(post)
            mark_post_completed(post)
            update_batch_progress(
                batch,
                5 + int((index + 1) / total_posts * 90),
            )

        mark_batch_completed(batch, batch.strategy_summary)
    except Exception as error:
        try:
            batch = PostBatch.objects.get(id=batch_id, user_id=user_id)
            mark_batch_failed(batch, error)
        except PostBatch.DoesNotExist:
            pass
    finally:
        close_old_connections()


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
            "`reference_image_2`, `logo`, `logo_position`.\n\n"
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
        sync_brand_logo(brand, data, request.user)

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


class BrandDetailAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        summary="Edita uma marca",
        description=(
            "Edita parcialmente uma marca do usuario autenticado.\n\n"
            "Campos aceitos: `business_name`, `niche`, `primary_color`, "
            "`secondary_color`, `tertiary_color`, `text_color`, "
            "`text_font`, `logo`, `logo_position`, `reference_image_1` e "
            "`reference_image_2`.\n\n"
            "Quando `reference_image_1` ou `reference_image_2` forem "
            "enviadas, a API salva as referencias e tenta recapturar a "
            "identidade visual por IA."
        ),
        request=BrandPatchSerializer,
        responses={status.HTTP_200_OK: BrandOutputSerializer},
    )
    def patch(self, request, brand_id):
        brand = get_object_or_404(
            get_user_brands(request.user),
            id=brand_id,
        )
        input_serializer = BrandPatchSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data

        brand = update_brand_manual_identity(brand, data)
        sync_brand_logo(brand, data, request.user)

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

        return Response(output_serializer.data)


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
        data["images"] = request.FILES.getlist("images")

        if data["my_images_or_ai"] == "user" and (
            len(data["images"]) != data["quantity"]
        ):
            return Response(
                {
                    "detail": (
                        "Envie exatamente uma imagem para cada post "
                        "solicitado."
                    ),
                    "expected": data["quantity"],
                    "received": len(data["images"]),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        batch = create_post_batch(request.user, brand, data)
        sync_brand_logo(brand, data, request.user)

        update_batch_progress(batch, 5)

        Thread(
            target=run_post_generation_job,
            args=(request.user.id, brand.id, batch.id, data),
            daemon=True,
        ).start()

        return Response(
            {
                "job_id": batch.id,
                "batch_id": batch.id,
                "status": batch.status,
                "progress": batch.progress,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class PostGenerationStatusAPIView(APIView):
    def get(self, request, batch_id):
        batch = get_object_or_404(
            PostBatch.objects.prefetch_related("posts"),
            id=batch_id,
            user=request.user,
        )
        response_data = {
            "job_id": batch.id,
            "batch_id": batch.id,
            "status": batch.status,
            "progress": batch.progress,
            "error_message": batch.error_message,
        }

        if batch.status in {"completed", "pending_review"}:
            response_data.update(serialize_post_batch(batch))

        return Response(response_data)


class PendingReviewPostBatchAPIView(APIView):
    def get(self, request):
        batch = (
            PostBatch.objects.prefetch_related("posts")
            .filter(
                user=request.user,
                status="pending_review",
            )
            .order_by("-created_at")
            .first()
        )

        if not batch:
            return Response({"batch": None})

        return Response({"batch": serialize_post_batch(batch)})


class ApprovePostPromptsAPIView(APIView):
    def post(self, request, batch_id):
        batch = get_object_or_404(
            PostBatch.objects.prefetch_related("posts"),
            id=batch_id,
            user=request.user,
            status="pending_review",
        )
        input_serializer = PostPromptApprovalSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        update_post_draft_prompts(
            batch,
            input_serializer.validated_data["posts"],
        )
        mark_batch_pending(batch)

        Thread(
            target=run_post_image_generation_job,
            args=(request.user.id, batch.id),
            daemon=True,
        ).start()

        return Response(
            {
                "job_id": batch.id,
                "batch_id": batch.id,
                "status": batch.status,
                "progress": batch.progress,
            },
            status=status.HTTP_202_ACCEPTED,
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
