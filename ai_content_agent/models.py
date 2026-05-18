from django.db import models
from django.conf import settings


class PostGeneration(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

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

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.business_name} - {self.theme}"