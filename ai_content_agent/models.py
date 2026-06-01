from django.db import models
from django.conf import settings


class GenerationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class PostGenerationBatch(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="post_generation_batches",
    )

    business_name = models.CharField(max_length=120)
    niche = models.CharField(max_length=120)
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
        return f"{self.business_name} - {self.quantity} posts"


class PostGeneration(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    batch = models.ForeignKey(
        PostGenerationBatch,
        on_delete=models.CASCADE,
        related_name="posts",
        null=True,
        blank=True,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="post_generation",
    )

    business_name = models.CharField(max_length=120)
    niche = models.CharField(max_length=120)
    objective = models.CharField(max_length=160)
    tone = models.CharField(max_length=80)
    theme = models.CharField(max_length=160)

    caption = models.TextField(blank=True)
    hashtags = models.JSONField(default=list, blank=True)
    image_prompt = models.TextField(blank=True)
    image_text = models.CharField(max_length=120, blank=True)
    image_url = models.CharField(max_length=500, blank=True)
    template = models.CharField(max_length=40, blank=True)
    post_order = models.PositiveSmallIntegerField(default=1)
    scheduled_date = models.DateField(null=True, blank=True)
    idea = models.JSONField(default=dict, blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.business_name} - {self.theme}"
