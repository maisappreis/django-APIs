from django.contrib import admin

from .models import PostGeneration, PostGenerationBatch


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
