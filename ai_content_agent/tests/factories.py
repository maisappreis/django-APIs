from django.contrib.auth.models import User
from uuid import uuid4

from accounts.models import Plan, Subscription
from ai_content_agent.models import Brand, GenerationStatus, Post, PostBatch


def create_user(username=None, password="password"):
    username = username or f"content-owner-{uuid4()}"
    return User.objects.create_user(username=username, password=password)


def create_subscription(user, tier=Plan.Tier.FREE, status=Subscription.Status.ACTIVE):
    plan = Plan.objects.create(
        name=tier.title(),
        tier=tier,
        is_active=True,
    )
    return Subscription.objects.create(
        user=user,
        plan=plan,
        status=status,
    )


def create_brand(user=None, **kwargs):
    user = user or create_user()
    defaults = {
        "business_name": "Test Brand",
        "niche": "Fitness",
        "primary_color": "#111111",
        "secondary_color": "#222222",
        "tertiary_color": "#333333",
        "text_color": "#FFFFFF",
        "title_font": "inter",
        "subtitle_font": "inter",
    }
    defaults.update(kwargs)
    return Brand.objects.create(user=user, **defaults)


def create_batch(user=None, brand=None, **kwargs):
    user = user or create_user()
    brand = brand or create_brand(user=user)
    defaults = {
        "objective": "Attract leads",
        "tone": "Friendly",
        "theme": "Summer",
        "quantity": 1,
        "use_templates": True,
        "image_source": "ai",
        "image_format": "square",
    }
    defaults.update(kwargs)
    return PostBatch.objects.create(user=user, brand=brand, **defaults)


def create_post(user=None, brand=None, batch=None, **kwargs):
    user = user or create_user()
    brand = brand or create_brand(user=user)
    defaults = {
        "batch": batch,
        "brand": brand,
        "caption": "Caption",
        "hashtags": ["#tag"],
        "image_prompt": "Prompt",
        "image_title": "TITLE",
        "image_subtitle": "SUBTITLE",
        "base_image_url": "/media/generated_posts/base.png",
        "image_url": "/media/generated_posts/final.png",
        "template": "none",
        "primary_color": "#111111",
        "secondary_color": "#222222",
        "tertiary_color": "#333333",
        "text_color": "#FFFFFF",
        "title_font": "inter",
        "subtitle_font": "inter",
        "logo_position": "bottom_right",
        "image_format": "square",
        "post_order": 1,
        "idea": {"title": "Idea"},
        "status": GenerationStatus.PENDING,
    }
    defaults.update(kwargs)
    return Post.objects.create(user=user, **defaults)
