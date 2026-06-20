from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .firebase_cleanup import delete_firebase_file
from .models import Brand


@receiver(pre_delete, sender=Brand)
def delete_brand_storage_files(sender, instance, **kwargs):
    """Remove persistent brand assets before the database row disappears."""
    for public_url in {
        instance.logo_url,
        instance.reference_image_1_url,
        instance.reference_image_2_url,
    }:
        delete_firebase_file(public_url)
