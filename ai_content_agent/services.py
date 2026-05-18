from ai_core.clients import generate_image_file, generate_structured_content
from ai_core.prompts import build_post_prompt


def generate_post_content(data):
    prompt = build_post_prompt(data)

    result = generate_structured_content(prompt)

    image_data = generate_image_file(result["image_prompt"])

    return {
        "caption": result["caption"],
        "hashtags": result["hashtags"],
        "image_prompt": result["image_prompt"],
        "image_url": image_data["image_url"],
    }