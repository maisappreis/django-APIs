from django.db import models


class ContactMessage(models.Model):
    email = models.EmailField()
    message = models.TextField()
    source = models.CharField(max_length=80, default="axis")
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.email} - {self.created_at:%Y-%m-%d %H:%M}"