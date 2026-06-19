from .registry import get_prompt_set


def _for_data(data):
    return get_prompt_set(data.get("content_language", "pt-BR"))


def build_post_plan_prompt(data):
    return _for_data(data).build_post_plan_prompt(data)


def build_post_from_idea_prompt(data, idea, index, total):
    return _for_data(data).build_post_from_idea_prompt(data, idea, index, total)


def build_posts_from_plan_prompt(data, ideas):
    return _for_data(data).build_posts_from_plan_prompt(data, ideas)


def build_post_prompt(data):
    return _for_data(data).build_post_prompt(data)


def get_content_system_prompt(content_language="pt-BR"):
    return get_prompt_set(content_language).CONTENT_SYSTEM_PROMPT


def get_visual_identity_system_prompt(content_language="pt-BR"):
    return get_prompt_set(content_language).VISUAL_IDENTITY_SYSTEM_PROMPT


def build_brand_visual_identity_prompt(
    business_name,
    niche,
    content_language="pt-BR",
):
    return get_prompt_set(content_language).build_brand_visual_identity_prompt(
        business_name,
        niche,
    )


def build_image_generation_prompt(
    prompt,
    image_format="square",
    content_language="pt-BR",
):
    return get_prompt_set(content_language).build_image_generation_prompt(
        prompt,
        image_format,
    )
