from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
import httpx
from threading import Thread

from .jobs import generate_post_review_batch, run_post_image_generation_job
from .models import GenerationStatus, Post, PostBatch
from .operations import (
    apply_brand_defaults,
    build_post_visual_settings,
    create_post_batch,
    delete_post_generation,
    ensure_brand_quota,
    ensure_ai_image_quota,
    ensure_visual_identity_capture_allowed,
    get_brand_by_id_for_user,
    get_brand_for_user,
    get_future_scheduled_posts,
    get_monthly_ai_image_usage,
    get_or_create_brand,
    get_user_brands,
    mark_batch_pending,
    mark_batch_failed,
    prepare_post_download,
    save_brand_reference_images,
    sync_brand_logo,
    update_brand_manual_identity,
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
    prepare_uploaded_post_image_files,
    rerender_post_image,
)


def get_pending_review_posts_for_user(user):
    return (
        Post.objects.select_related("batch", "brand")
        .filter(
            user=user,
            status=GenerationStatus.PENDING_REVIEW,
            batch__status=GenerationStatus.PENDING_REVIEW,
        )
        .order_by(
            "scheduled_date",
            "post_order",
            "created_at",
        )
    )


def serialize_pending_review_posts_for_user(user):
    return [
        serialize_post_generation(post)
        for post in get_pending_review_posts_for_user(user)
    ]


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
            "`text_color`, `title_font`, `subtitle_font`, `image_format`.\n\n"
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

        try:
            ensure_brand_quota(
                user=request.user,
                business_name=data["business_name"],
                niche=data["niche"],
            )
        except ValueError as error:
            return Response(
                {"detail": str(error)},
                status=status.HTTP_403_FORBIDDEN,
            )

        if data.get("reference_image_1") or data.get("reference_image_2"):
            try:
                ensure_visual_identity_capture_allowed(request.user)
            except ValueError as error:
                return Response(
                    {"detail": str(error)},
                    status=status.HTTP_403_FORBIDDEN,
                )

        brand = get_or_create_brand(
            user=request.user,
            business_name=data["business_name"],
            niche=data["niche"],
        )
        brand = update_brand_manual_identity(brand, data)
        sync_brand_logo(brand, data, request.user)

        if data.get("reference_image_1") or data.get("reference_image_2"):
            try:
                ensure_visual_identity_capture_allowed(request.user)
            except ValueError as error:
                return Response(
                    {"detail": str(error)},
                    status=status.HTTP_403_FORBIDDEN,
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
            "`title_font`, `subtitle_font`, `image_format`, `logo`, "
            "`logo_position`, `reference_image_1` e `reference_image_2`.\n\n"
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
            try:
                ensure_visual_identity_capture_allowed(request.user)
            except ValueError as error:
                return Response(
                    {"detail": str(error)},
                    status=status.HTTP_403_FORBIDDEN,
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

        if data["my_images_or_ai"] == "ai":
            try:
                ensure_ai_image_quota(request.user, data["quantity"])
            except ValueError as error:
                return Response(
                    {"detail": str(error)},
                    status=status.HTTP_403_FORBIDDEN,
                )
        else:
            data["image_files"] = prepare_uploaded_post_image_files(
                data["images"]
            )

        batch = create_post_batch(request.user, brand, data)
        sync_brand_logo(brand, data, request.user)

        try:
            batch = generate_post_review_batch(
                user=request.user,
                brand=brand,
                batch=batch,
                data=data,
            )
        except Exception as error:
            mark_batch_failed(batch, error)
            response_data = {
                "detail": "Erro ao gerar conteudo para revisao.",
            }

            if settings.DEBUG:
                response_data["error"] = str(error)

            return Response(
                response_data,
                status=status.HTTP_502_BAD_GATEWAY,
            )

        response_data = {
            "job_id": batch.id,
            "status": batch.status,
            "progress": batch.progress,
            **serialize_post_batch(batch),
        }
        response_data["posts"] = serialize_pending_review_posts_for_user(
            request.user
        )

        return Response(response_data, status=status.HTTP_201_CREATED)


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
        posts = list(get_pending_review_posts_for_user(request.user))

        if not posts:
            return Response({"batch": None, "posts": []})

        latest_batch = max(posts, key=lambda post: post.batch.created_at).batch
        serialized_posts = [
            serialize_post_generation(post)
            for post in posts
        ]

        return Response({
            "batch": {
                "batch_id": latest_batch.id,
                "quantity": len(serialized_posts),
                "image_format": latest_batch.image_format,
                "strategy_summary": latest_batch.strategy_summary,
                "posts": serialized_posts,
            },
            "posts": serialized_posts,
        })


class ApprovePostPromptsAPIView(APIView):
    def post(self, request, batch_id):
        anchor_batch = get_object_or_404(
            PostBatch.objects.prefetch_related("posts"),
            id=batch_id,
            user=request.user,
            status=GenerationStatus.PENDING_REVIEW,
        )
        input_serializer = PostPromptApprovalSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        prompt_items = input_serializer.validated_data["posts"]
        prompt_items_by_id = {
            item["id"]: item
            for item in prompt_items
        }
        posts = list(
            Post.objects.select_related("batch")
            .filter(
                id__in=prompt_items_by_id.keys(),
                user=request.user,
                status=GenerationStatus.PENDING_REVIEW,
                batch__status=GenerationStatus.PENDING_REVIEW,
            )
        )
        batches_by_id = {
            post.batch_id: post.batch
            for post in posts
            if post.batch_id
        }

        if anchor_batch.id not in batches_by_id:
            batches_by_id[anchor_batch.id] = anchor_batch

        for post in posts:
            post.image_prompt = prompt_items_by_id[post.id]["image_prompt"]
            post.save(update_fields=["image_prompt"])

        ai_posts_count = sum(
            batch.posts.filter(status=GenerationStatus.PENDING_REVIEW).count()
            for batch in batches_by_id.values()
            if batch.image_source == "ai"
        )

        if ai_posts_count:
            try:
                ensure_ai_image_quota(request.user, ai_posts_count)
            except ValueError as error:
                return Response(
                    {"detail": str(error)},
                    status=status.HTTP_403_FORBIDDEN,
                )

        jobs = []

        for batch in batches_by_id.values():
            mark_batch_pending(batch)

            Thread(
                target=run_post_image_generation_job,
                args=(request.user.id, batch.id),
                daemon=True,
            ).start()
            jobs.append({
                "job_id": batch.id,
                "batch_id": batch.id,
                "status": batch.status,
                "progress": batch.progress,
            })

        anchor_batch.refresh_from_db()

        return Response(
            {
                "job_id": anchor_batch.id,
                "batch_id": anchor_batch.id,
                "status": anchor_batch.status,
                "progress": anchor_batch.progress,
                "jobs": jobs,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class ContentAgentUsageAPIView(APIView):
    def get(self, request):
        return Response(
            {
                "ai_images": get_monthly_ai_image_usage(request.user),
            }
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


class DeletePostAPIView(APIView):
    def delete(self, request, post_id):
        post_generation = get_object_or_404(
            Post,
            id=post_id,
            user=request.user,
        )

        delete_post_generation(post_generation)

        return Response(status=status.HTTP_204_NO_CONTENT)


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
