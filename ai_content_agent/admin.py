from django.contrib import admin

from .models import Brand, Post, PostBatch, UsageEvent


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
                    "logo",
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


@admin.register(PostBatch)
class PostBatchAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "brand",
        "theme",
        "quantity",
        "image_source",
        "use_templates",
        "status",
        "created_at",
    )
    list_filter = ("status", "image_source", "created_at", "user", "brand")
    search_fields = (
        "brand__business_name",
        "brand__niche",
        "objective",
        "tone",
        "theme",
    )


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "brand",
        "batch",
        "post_order",
        "scheduled_date",
        "template",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at", "user", "brand", "batch")
    search_fields = (
        "brand__business_name",
        "brand__niche",
        "caption",
        "image_prompt",
    )


@admin.register(UsageEvent)
class UsageEventAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "kind",
        "quantity",
        "batch",
        "created_at",
    )
    list_filter = ("kind", "created_at", "user")
    search_fields = ("user__username", "user__email", "batch__theme")
