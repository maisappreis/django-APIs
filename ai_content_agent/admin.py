from django.contrib import admin
from .models import Brand, PostGeneration, PostGenerationBatch


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "business_name",
        "niche",
        "primary_color",
        "secondary_color",
        "tertiary_color",
        "logo_position",
        "updated_at",
    )
    list_filter = ("created_at", "updated_at", "user")
    search_fields = (
        "business_name",
        "niche",
        "visual_identity_summary",
        "visual_identity_prompt",
    )
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Marca",
            {
                "fields": (
                    "user",
                    "business_name",
                    "niche",
                    "logo_url",
                )
            },
        ),
        (
            "Referencias",
            {
                "fields": (
                    "reference_image_1",
                    "reference_image_1_url",
                    "reference_image_2",
                    "reference_image_2_url",
                )
            },
        ),
        (
            "Identidade visual",
            {
                "fields": (
                    "visual_identity_summary",
                    "visual_identity_prompt",
                    "primary_color",
                    "secondary_color",
                    "tertiary_color",
                    "text_color",
                    "text_font",
                    "logo_position",
                )
            },
        ),
        (
            "Datas",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@admin.register(PostGenerationBatch)
class PostGenerationBatchAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "business_name",
        "quantity",
        "use_templates",
        "text_font",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at", "user")
    search_fields = ("business_name", "niche", "theme")


@admin.register(PostGeneration)
class PostGenerationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "business_name",
        "batch",
        "post_order",
        "scheduled_date",
        "template",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at", "user", "batch")
    search_fields = ("business_name", "niche", "theme", "caption")
