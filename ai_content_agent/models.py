from django.conf import settings
from django.db import models


class Brand(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="content_agent_brands",
    )
    business_name = models.CharField(max_length=120)
    niche = models.CharField(max_length=120)
    reference_image_1 = models.ImageField(
        upload_to="content_agent/brand_references/",
        null=True,
        blank=True,
    )
    reference_image_2 = models.ImageField(
        upload_to="content_agent/brand_references/",
        null=True,
        blank=True,
    )
    reference_image_1_url = models.CharField(max_length=500, blank=True)
    reference_image_2_url = models.CharField(max_length=500, blank=True)
    logo = models.ImageField(
        upload_to="content_agent/logos/",
        null=True,
        blank=True,
    )
    logo_url = models.CharField(max_length=500, blank=True)
    visual_identity_summary = models.TextField(blank=True)
    visual_identity_prompt = models.TextField(blank=True)
    primary_color = models.CharField(max_length=7, default="#006C44")
    secondary_color = models.CharField(max_length=7, default="#1FD794")
    tertiary_color = models.CharField(max_length=7, default="#98C8B6")
    text_color = models.CharField(max_length=7, default="#FFFFFF")
    text_font = models.CharField(max_length=80, blank=True)
    logo_position = models.CharField(max_length=20, default="bottom_right")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "business_name", "niche"]),
        ]

    def __str__(self):
        return f"{self.business_name} - {self.niche}"


class GenerationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class PostBatch(models.Model):
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        related_name="batches",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="post_batches",
    )

    objective = models.CharField(max_length=160)
    tone = models.CharField(max_length=80)
    theme = models.CharField(max_length=160)
    quantity = models.PositiveSmallIntegerField(default=1)
    use_templates = models.BooleanField(default=True)
    strategy_summary = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=GenerationStatus.choices,
        default=GenerationStatus.PENDING,
    )

    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        brand_name = self.brand.business_name if self.brand else "No brand"
        return f"{brand_name} - {self.quantity} posts"


class Post(models.Model):
    batch = models.ForeignKey(
        PostBatch,
        on_delete=models.CASCADE,
        related_name="posts",
        null=True,
        blank=True,
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        related_name="posts",
        null=True,
        blank=True,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
    )

    caption = models.TextField(blank=True)
    hashtags = models.JSONField(default=list, blank=True)
    image_prompt = models.TextField(blank=True)
    image_text = models.CharField(max_length=120, blank=True)
    base_image_url = models.CharField(max_length=500, blank=True)
    image_url = models.CharField(max_length=500, blank=True)
    template = models.CharField(max_length=40, blank=True)
    primary_color = models.CharField(max_length=7, default="#006C44")
    secondary_color = models.CharField(max_length=7, default="#1FD794")
    tertiary_color = models.CharField(max_length=7, default="#98C8B6")
    text_color = models.CharField(max_length=7, default="#FFFFFF")
    text_font = models.CharField(max_length=80, blank=True)
    logo_position = models.CharField(max_length=20, default="bottom_right")
    post_order = models.PositiveSmallIntegerField(default=1)
    scheduled_date = models.DateField(null=True, blank=True)
    idea = models.JSONField(default=dict, blank=True)

    status = models.CharField(
        max_length=20,
        choices=GenerationStatus.choices,
        default=GenerationStatus.PENDING,
    )

    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        brand_name = self.brand.business_name if self.brand else "No brand"
        return f"{brand_name} - post {self.post_order}"
