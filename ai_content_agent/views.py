from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
import httpx
import logging
from secrets import compare_digest

from .firebase_cleanup import (
    cleanup_post_images_outside_retention_window,
    delete_replaced_firebase_file,
)
from .jobs import (
    generate_post_review_batch,
    run_brand_visual_identity_job,
    run_post_generation_job,
    run_post_image_generation_job,
)
from .models import GenerationStatus, Post, PostBatch
from .operations import (
    apply_brand_defaults,
    build_post_visual_settings,
    create_post_batch,
    delete_post_generation,
    ensure_ai_image_edit_quota,
    ensure_brand_quota,
    ensure_ai_image_quota,
    ensure_post_batch_quantity_allowed,
    ensure_user_image_quota,
    ensure_user_image_ai_edit_allowed,
    ensure_visual_identity_capture_allowed,
    get_brand_by_id_for_user,
    get_future_scheduled_posts,
    get_monthly_ai_image_edit_usage,
    get_monthly_ai_image_usage,
    get_monthly_user_image_usage,
    get_or_create_brand,
    get_pending_review_posts_for_user,
    get_user_brands,
    mark_batch_pending,
    mark_batch_failed,
    prepare_post_download,
    save_brand_reference_images,
    serialize_pending_review_posts_for_user,
    sync_brand_logo,
    update_brand_manual_identity,
)
from .presenters import (
    serialize_brand,
    serialize_post_batch,
    serialize_post_generation,
)
from .queue import (
    enqueue_brand_visual_identity,
    enqueue_post_generation,
    enqueue_post_image_generation,
)
from .serializers import (
    BrandInputSerializer,
    BrandOutputSerializer,
    BrandPatchSerializer,
    BrandReferenceUploadCompleteOutputSerializer,
    BrandReferenceUploadCompleteSerializer,
    BrandReferenceUploadSignOutputSerializer,
    BrandReferenceUploadSignSerializer,
    CalendarPostsQuerySerializer,
    PostGenerationInputSerializer,
    PostImageRenderInputSerializer,
    PostPromptApprovalSerializer,
    PostSourceUploadSignOutputSerializer,
    PostSourceUploadSignSerializer,
)
from .storage import (
    finalize_brand_reference_upload,
    generate_brand_reference_upload_url,
    generate_post_source_upload_url,
    is_firebase_storage_enabled,
)
from .services import (
    analyze_brand_visual_identity,
    prepare_private_merge_image_files,
    prepare_private_post_source_image_files,
    prepare_uploaded_merge_image_files,
    prepare_uploaded_post_image_files,
    rerender_post_image,
)
from .view_helpers import (
    delete_expired_incomplete_batches,
    fail_stale_pending_batch,
    get_brand_message,
    is_valid_maintenance_request,
    restore_manual_font_choices,
    serialize_batch_status,
)


logger = logging.getLogger(__name__)


class PostSourceUploadSignAPIView(APIView):
    @extend_schema(
        summary="Gera URL assinada para imagem fornecida pelo usuário",
        request=PostSourceUploadSignSerializer,
        responses={status.HTTP_200_OK: PostSourceUploadSignOutputSerializer},
    )
    def post(self, request):
        serializer = PostSourceUploadSignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not is_firebase_storage_enabled():
            return Response(
                {"detail": "Firebase Storage não está habilitado."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            generate_post_source_upload_url(
                request.user.id,
                serializer.validated_data["content_type"],
            )
        )


class BrandReferenceUploadSignAPIView(APIView):
    @extend_schema(
        summary="Gera uma URL assinada para upload de referência visual",
        description=(
            "Valida os metadados da imagem e retorna uma URL temporária "
            "para upload direto e privado no Firebase Storage. O arquivo "
            "não deve ser enviado a este endpoint."
        ),
        request=BrandReferenceUploadSignSerializer,
        responses={
            status.HTTP_200_OK: BrandReferenceUploadSignOutputSerializer,
        },
    )
    def post(self, request):
        serializer = BrandReferenceUploadSignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not is_firebase_storage_enabled():
            return Response(
                {"detail": "Firebase Storage não está habilitado."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        upload = generate_brand_reference_upload_url(
            user_id=request.user.id,
            content_type=serializer.validated_data["content_type"],
        )

        return Response(upload, status=status.HTTP_200_OK)


class BrandReferenceUploadCompleteAPIView(APIView):
    @extend_schema(
        summary="Confirma e associa uma referência visual privada",
        description=(
            "Valida no Firebase o upload direto, move o objeto temporário "
            "para o caminho definitivo da marca e associa a referência ao "
            "usuário autenticado."
        ),
        request=BrandReferenceUploadCompleteSerializer,
        responses={
            status.HTTP_200_OK: BrandReferenceUploadCompleteOutputSerializer,
        },
    )
    def post(self, request):
        serializer = BrandReferenceUploadCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if not is_firebase_storage_enabled():
            return Response(
                {"detail": "Firebase Storage não está habilitado."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        brand = get_object_or_404(
            get_user_brands(request.user),
            id=data["brand_id"],
        )

        try:
            ensure_visual_identity_capture_allowed(request.user)
        except ValueError as error:
            return Response(
                {"detail": str(error)},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            confirmed = finalize_brand_reference_upload(
                user_id=request.user.id,
                brand_id=brand.id,
                slot=data["slot"],
                object_path=data["object_path"],
            )
        except FileNotFoundError as error:
            return Response(
                {"detail": str(error)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as error:
            return Response(
                {"detail": str(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        slot = data["slot"]
        url_field = f"reference_image_{slot}_url"
        image_field = f"reference_image_{slot}"
        previous_url = getattr(brand, url_field)
        setattr(brand, url_field, confirmed["storage_url"])
        setattr(brand, image_field, None)
        brand.save(update_fields=[url_field, image_field, "updated_at"])
        delete_replaced_firebase_file(
            previous_url,
            confirmed["storage_url"],
        )

        if data["analyze"]:
            brand.visual_identity_status = "pending"
            brand.visual_identity_error = ""
            brand.save(
                update_fields=[
                    "visual_identity_status",
                    "visual_identity_error",
                    "updated_at",
                ]
            )
            try:
                enqueue_brand_visual_identity(request.user.id, brand.id)
            except Exception as error:
                brand.visual_identity_status = "failed"
                brand.visual_identity_error = str(error)[:1000]
                brand.save(
                    update_fields=[
                        "visual_identity_status",
                        "visual_identity_error",
                        "updated_at",
                    ]
                )
                response_data = {
                    "detail": "Erro ao captar identidade visual da marca.",
                }

                if settings.DEBUG:
                    response_data["error"] = str(error)

                return Response(
                    response_data,
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        response_data = {
            "brand_id": brand.id,
            "slot": slot,
            "object_path": confirmed["object_path"],
            "content_type": confirmed["content_type"],
            "size": confirmed["size"],
            "visual_identity_status": brand.visual_identity_status,
        }

        return Response(response_data, status=status.HTTP_200_OK)


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
                brand = restore_manual_font_choices(brand, data, request.data)
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
                brand = restore_manual_font_choices(brand, data, request.data)
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

    def delete(self, request, brand_id):
        return Response(
            {"detail": "Marcas não podem ser excluídas; apenas atualizadas."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class CalendarPostsAPIView(APIView):
    def get(self, request):
        input_serializer = CalendarPostsQuerySerializer(data=request.query_params)
        input_serializer.is_valid(raise_exception=True)

        data = input_serializer.validated_data
        brand = get_object_or_404(
            get_user_brands(request.user),
            id=data["brand_id"],
        )
        start_date, posts = get_future_scheduled_posts(
            request.user,
            brand,
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
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


class FirebaseCleanupMaintenanceAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if not is_valid_maintenance_request(request):
            return Response(
                {"detail": "Unauthorized maintenance request."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        cleaned_count = cleanup_post_images_outside_retention_window()

        return Response(
            {
                "status": "ok",
                "cleaned_posts": cleaned_count,
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
            data["brand_id"],
        )

        if not brand:
            return Response(
                {
                    "detail": "Marca não encontrada.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if brand.visual_identity_status == "pending":
            return Response(
                {
                    "detail": get_brand_message(
                        brand,
                        "visual_identity_pending",
                    ),
                    "visual_identity_status": brand.visual_identity_status,
                },
                status=status.HTTP_409_CONFLICT,
            )

        data = apply_brand_defaults(data, brand, request.data)
        data["images"] = request.FILES.getlist("images")
        image_object_paths = request.data.getlist("image_object_paths")
        received_images = image_object_paths or data["images"]
        image_edit_mode = data.get("image_edit_mode", "none")
        data["image_edit_mode"] = image_edit_mode
        has_image_edit = image_edit_mode != "none"
        merge_images = image_edit_mode == "merge_images"

        try:
            ensure_post_batch_quantity_allowed(request.user, data["quantity"])
        except ValueError as error:
            return Response(
                {"detail": str(error)},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not merge_images and data["my_images_or_ai"] == "user" and (
            len(received_images) != data["quantity"]
        ):
            return Response(
                {
                    "detail": (
                        "Envie exatamente uma imagem para cada post "
                        "solicitado."
                    ),
                    "expected": data["quantity"],
                    "received": len(received_images),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        queue_backend = getattr(settings, "CONTENT_AGENT_QUEUE_BACKEND", "inline")

        if has_image_edit and data["my_images_or_ai"] != "user":
            return Response(
                {
                    "detail": (
                        "A edicao de imagem com IA esta disponivel apenas "
                        "para imagens proprias."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if merge_images and data["quantity"] != 1:
            return Response(
                {
                    "detail": (
                        "A mesclagem de duas imagens esta disponivel apenas "
                        "para um post por vez."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if merge_images and len(received_images) not in {2, 3}:
            return Response(
                {
                    "detail": (
                        "Envie duas ou tres imagens para mesclar: a imagem "
                        "principal, a imagem de referencia e, opcionalmente, "
                        "a imagem de foco."
                    ),
                    "expected": "2 or 3",
                    "received": len(received_images),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if has_image_edit and not data.get("image_editing_prompt", "").strip():
            return Response(
                {
                    "detail": (
                        "Informe o prompt de edicao da imagem."
                    )
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
            try:
                ensure_user_image_quota(request.user, data["quantity"])
                if has_image_edit:
                    ensure_user_image_ai_edit_allowed(request.user)
                    ensure_ai_image_edit_quota(request.user, data["quantity"])
            except ValueError as error:
                return Response(
                    {"detail": str(error)},
                    status=status.HTTP_403_FORBIDDEN,
                )

            if queue_backend == "qstash" and not image_object_paths:
                return Response(
                    {
                        "detail": (
                            "Envie as imagens usando upload assinado antes "
                            "de gerar posts em producao."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if queue_backend == "qstash":
                data["image_object_paths"] = list(image_object_paths)
            else:
                try:
                    if merge_images:
                        data["image_files"] = (
                            prepare_private_merge_image_files(
                                request.user.id,
                                image_object_paths,
                            )
                            if image_object_paths
                            else prepare_uploaded_merge_image_files(data["images"])
                        )
                    else:
                        data["image_files"] = (
                            prepare_private_post_source_image_files(
                                request.user.id,
                                image_object_paths,
                            )
                            if image_object_paths
                            else prepare_uploaded_post_image_files(data["images"])
                        )
                except FileNotFoundError as error:
                    return Response(
                        {"detail": str(error)},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                except ValueError as error:
                    return Response(
                        {"detail": str(error)},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        batch = create_post_batch(request.user, brand, data)
        sync_brand_logo(brand, data, request.user)

        if queue_backend == "qstash":
            job_data = {
                key: value
                for key, value in data.items()
                if key not in {"images", "image_files"}
            }

            try:
                enqueue_post_generation(
                    request.user.id,
                    brand.id,
                    batch.id,
                    job_data,
                )
            except (httpx.HTTPError, ImproperlyConfigured, RuntimeError) as error:
                logger.exception(
                    "Failed to enqueue post generation batch %s.",
                    batch.id,
                )
                mark_batch_failed(batch, error)
                response_data = {
                    "detail": "Nao foi possivel enfileirar a geracao.",
                }

                if settings.DEBUG:
                    response_data["error"] = str(error)

                return Response(
                    response_data,
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            return Response(
                serialize_batch_status(batch),
                status=status.HTTP_202_ACCEPTED,
            )

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
        batch = fail_stale_pending_batch(batch)
        if batch is None:
            return Response(
                {"detail": "Geracao nao encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        response_data = serialize_batch_status(batch)

        if batch.status in {"completed", "pending_review"}:
            response_data.update(serialize_post_batch(batch))

        return Response(response_data)


class PendingReviewPostBatchAPIView(APIView):
    def get(self, request):
        posts = list(get_pending_review_posts_for_user(request.user))

        if not posts:
            delete_expired_incomplete_batches(request.user)
            latest_batch = (
                PostBatch.objects.filter(
                    user=request.user,
                    status__in=[
                        GenerationStatus.PENDING,
                        GenerationStatus.FAILED,
                    ],
                )
                .order_by("-created_at")
                .first()
            )

            if latest_batch:
                latest_batch = fail_stale_pending_batch(latest_batch)
                if latest_batch is None:
                    return Response({
                        "batch": None,
                        "failed_batch": None,
                        "posts": [],
                    })

                serialized_batch = {
                    **serialize_batch_status(latest_batch),
                    "posts": [],
                }

                if latest_batch.status == GenerationStatus.PENDING:
                    return Response(
                        {
                            "batch": serialized_batch,
                            "failed_batch": None,
                            "posts": [],
                        }
                    )

                return Response(
                    {
                        "batch": None,
                        "failed_batch": serialized_batch,
                        "posts": [],
                    }
                )

            return Response({"batch": None, "failed_batch": None, "posts": []})

        latest_batch = max(posts, key=lambda post: post.batch.created_at).batch
        serialized_posts = [
            serialize_post_generation(post)
            for post in posts
        ]

        return Response({
            "batch": {
                **serialize_batch_status(latest_batch),
                "quantity": len(serialized_posts),
                "posts": serialized_posts,
            },
            "failed_batch": None,
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

        ai_posts_count = 0
        ai_edit_posts_count = 0
        user_posts_count = 0

        for batch in batches_by_id.values():
            pending_posts_count = batch.posts.filter(
                status=GenerationStatus.PENDING_REVIEW
            ).count()

            if batch.image_source == "ai":
                ai_posts_count += pending_posts_count
            elif batch.image_source == "user":
                user_posts_count += pending_posts_count
                ai_edit_posts_count += pending_posts_count

        if ai_posts_count:
            try:
                ensure_ai_image_quota(request.user, ai_posts_count)
            except ValueError as error:
                return Response(
                    {"detail": str(error)},
                    status=status.HTTP_403_FORBIDDEN,
                )

        if ai_edit_posts_count:
            try:
                ensure_ai_image_edit_quota(request.user, ai_edit_posts_count)
            except ValueError as error:
                return Response(
                    {"detail": str(error)},
                    status=status.HTTP_403_FORBIDDEN,
                )

        if user_posts_count:
            try:
                ensure_user_image_quota(request.user, user_posts_count)
            except ValueError as error:
                return Response(
                    {"detail": str(error)},
                    status=status.HTTP_403_FORBIDDEN,
                )

        jobs = []

        for batch in batches_by_id.values():
            mark_batch_pending(batch)

            try:
                enqueue_post_image_generation(request.user.id, batch.id)
            except (httpx.HTTPError, ImproperlyConfigured, RuntimeError) as error:
                logger.exception(
                    "Failed to enqueue post image generation batch %s.",
                    batch.id,
                )
                mark_batch_failed(batch, error)
                response_data = {
                    "detail": "Nao foi possivel enfileirar a geracao.",
                }

                if settings.DEBUG:
                    response_data["error"] = str(error)

                return Response(
                    response_data,
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            batch.refresh_from_db()
            jobs.append(serialize_batch_status(batch))

        anchor_batch.refresh_from_db()

        return Response(
            {
                **serialize_batch_status(anchor_batch),
                "jobs": jobs,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class PostGenerationJobAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        expected_token = getattr(settings, "CONTENT_AGENT_JOB_TOKEN", "")
        received_token = request.headers.get(
            "X-Content-Agent-Job-Token",
            "",
        )
        if not expected_token or not compare_digest(received_token, expected_token):
            return Response(
                {"detail": "Unauthorized job request."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user_id = request.data.get("user_id")
        brand_id = request.data.get("brand_id")
        batch_id = request.data.get("batch_id")
        data = request.data.get("data")
        if (
            not isinstance(user_id, int)
            or not isinstance(brand_id, int)
            or not isinstance(batch_id, int)
            or not isinstance(data, dict)
        ):
            return Response(
                {"detail": "Invalid job payload."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not run_post_generation_job(user_id, brand_id, batch_id, data):
            return Response(
                {"detail": "Job processing failed."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"status": "completed"})


class BrandVisualIdentityJobAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        expected_token = getattr(settings, "CONTENT_AGENT_JOB_TOKEN", "")
        received_token = request.headers.get(
            "X-Content-Agent-Job-Token",
            "",
        )
        if not expected_token or not compare_digest(received_token, expected_token):
            return Response(
                {"detail": "Unauthorized job request."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user_id = request.data.get("user_id")
        brand_id = request.data.get("brand_id")
        if not isinstance(user_id, int) or not isinstance(brand_id, int):
            return Response(
                {"detail": "Invalid job payload."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not run_brand_visual_identity_job(user_id, brand_id):
            return Response(
                {"detail": "Job processing failed."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"status": "completed"})


class PostImageGenerationJobAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        expected_token = getattr(settings, "CONTENT_AGENT_JOB_TOKEN", "")
        received_token = request.headers.get(
            "X-Content-Agent-Job-Token",
            "",
        )
        if not expected_token or not compare_digest(received_token, expected_token):
            return Response(
                {"detail": "Unauthorized job request."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user_id = request.data.get("user_id")
        batch_id = request.data.get("batch_id")
        if not isinstance(user_id, int) or not isinstance(batch_id, int):
            return Response(
                {"detail": "Invalid job payload."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not run_post_image_generation_job(user_id, batch_id):
            return Response(
                {"detail": "Job processing failed."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"status": "completed"})


class ContentAgentUsageAPIView(APIView):
    def get(self, request):
        return Response(
            {
                "ai_images": get_monthly_ai_image_usage(request.user),
                "user_images": get_monthly_user_image_usage(request.user),
                "ai_image_edits": get_monthly_ai_image_edit_usage(request.user),
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
