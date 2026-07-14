CONTENT_SYSTEM_PROMPT = (
    "You are a social media content marketing specialist. "
    "Always respond in natural American English."
)

VISUAL_IDENTITY_SYSTEM_PROMPT = (
    "You are an art director specializing in visual identity for social media."
)

IMAGE_FORMAT_LABELS = {
    "square": "in a square format",
    "portrait": "in a vertical portrait format",
    "landscape": "in a horizontal landscape format",
}


def _format_brand_visual_identity(value):
    value = (value or "").strip()

    if not value:
        return ""

    return f"        Brand visual identity: {value}\n"


def _format_brand_visual_identity_block(value):
    value = (value or "").strip()

    if not value:
        return ""

    return f"""
        Brand visual identity:
        {value}
"""


def build_post_plan_prompt(data):
    quantity = data["quantity"]
    brand_visual_identity = _format_brand_visual_identity(
        data.get("brand_visual_identity", "")
    )

    return f"""
        Create an editorial calendar with exactly {quantity} distinct social
        media post ideas based on the information below.

        Business: {data["business_name"]}
        Niche: {data["niche"]}
        Primary objective: {data["objective"]}
        Tone of voice: {data["tone"]}
        Main theme or campaign: {data["theme"]}
        {brand_visual_identity}

        Strategic priorities:
        - The main theme or campaign must guide every post.
        - Each idea must explore a subtopic directly connected to the main
          theme instead of a generic idea that could fit any campaign.
        - If the theme mentions a date, offer, pain point, product, service,
          routine, event, or transformation, clearly reflect it in each post's
          objective, angle, and visual direction.

        Rules:
        - Respond in natural American English.
        - Ideas must not repeat or be obvious variations of one another.
        - Balance education, authority, social proof, engagement, objection
          handling, offers, and relationship-building.
        - Give each idea its own creative angle.
        - visual_direction must guide a coherent advertising image.
        - Make every visual_direction substantially different in scene,
          subject, composition, camera distance, setting, supporting objects,
          and visual energy.
        - Do not repeat stock formulas such as a smiling person facing the
          camera or a product against a clean background.
        - Vary among action, product or service details, behind-the-scenes,
          environments, symbolic objects, conceptual before-and-after, usage
          scenes, still life, customer perspective, process, and outcome.
        - Treat the brand identity as the main reference for color,
          composition, style, and mood.
        - Use brand colors as accents or graphic elements, never as a
          translucent filter or overlay across the entire image.
        - Return exactly {quantity} items in posts.
        """


def build_post_from_idea_prompt(data, idea, index, total):
    brand_visual_identity = _format_brand_visual_identity(
        data.get("brand_visual_identity", "")
    )

    return f"""
        Turn the editorial idea below into a publication-ready social post.

        Business: {data["business_name"]}
        Niche: {data["niche"]}
        Primary objective: {data["objective"]}
        Tone of voice: {data["tone"]}
        Main campaign: {data["theme"]}
        {brand_visual_identity}

        Post {index} of {total}
        Idea title: {idea["title"]}
        Specific theme: {idea["theme"]}
        Specific objective: {idea["objective"]}
        Editorial format: {idea["format"]}
        Creative angle: {idea["angle"]}
        Visual direction: {idea["visual_direction"]}

        Generate a caption, relevant hashtags, a visual generation prompt, a
        short image title, and a short image subtitle.

        Rules:
        - Respond in natural American English.
        - Make the caption clear, engaging, and aligned with the objective.
        - Avoid calls to action, phrases, and structures reused in other posts.
        - Every hashtag must begin with #.
        - Keep the visual prompt objective and faithful to the brand identity.
        - Use brand colors as accents or compositional elements, without a
          translucent filter or overlay across the entire image.
        - Request an advertising image without a headline or primary text.
        - Allow short English words only when they naturally belong in the
          scene, such as labels, signs, steps, or interface elements.
        - Do not request Portuguese text.
        - Do not place image_title or image_subtitle inside the visual prompt.
        - image_title must contain no more than 5 words.
        - image_subtitle must contain no more than 10 words.
        - Both must exclude hashtags, emojis, and quotation marks.

        Optional image text direction: {data.get("image_text_direction", "")}
        """


def _format_plan(ideas):
    blocks = []
    for index, idea in enumerate(ideas, start=1):
        blocks.append("\n".join([
            f"Post {index}",
            f"Title: {idea['title']}",
            f"Theme: {idea['theme']}",
            f"Objective: {idea['objective']}",
            f"Format: {idea['format']}",
            f"Angle: {idea['angle']}",
            f"Visual direction: {idea['visual_direction']}",
        ]))
    return "\n\n".join(blocks)


def build_posts_from_plan_prompt(data, ideas):
    quantity = data["quantity"]
    brand_visual_identity = _format_brand_visual_identity(
        data.get("brand_visual_identity", "")
    )

    return f"""
        Turn the editorial plan below into exactly {quantity} publication-ready
        social media posts.

        Business: {data["business_name"]}
        Niche: {data["niche"]}
        Primary objective: {data["objective"]}
        Tone of voice: {data["tone"]}
        Main campaign: {data["theme"]}
        {brand_visual_identity}

        Editorial plan:
        {_format_plan(ideas)}

        Strategic priorities:
        - Give the main theme substantial weight in every result.
        - Keep the campaign cohesive while varying scenes and approaches.
        - Do not produce interchangeable visual prompts.
        - Specify each image's subtopic, main subject, setting, action,
          framing, supporting objects, and mood.

        For each item, generate order, caption, hashtags, image_prompt,
        image_title, and image_subtitle.

        Rules:
        - Respond in natural American English.
        - Return exactly {quantity} items in the original plan order.
        - Give each caption a different structure and call to action.
        - Every hashtag must begin with #.
        - Make each visual prompt objective, specific, and distinct in
          composition, framing, setting, focal object, action, and atmosphere.
        - Include concrete details from the campaign and each post's angle.
        - Preserve the brand identity and use brand colors as accents, without
          a translucent filter or overlay across the entire image.
        - Request an advertising image without a headline or primary text.
        - Allow short English words only as a natural part of the scene. Do not
          request Portuguese text.
        - Do not place image_title or image_subtitle inside image_prompt.
        - image_title must have at most 5 words and image_subtitle at most 10.
        - Both must exclude hashtags, emojis, and quotation marks.

        Optional image text direction: {data.get("image_text_direction", "")}
        """


def build_post_prompt(data):
    return f"""
        Create a social media post.
        Business: {data["business_name"]}
        Niche: {data["niche"]}
        Objective: {data["objective"]}
        Tone of voice: {data["tone"]}
        Theme: {data["theme"]}

        Respond in natural American English with a caption, hashtags, visual
        prompt, image_title of up to 5 words, and image_subtitle of up to 10
        words. Do not use hashtags, emojis, or quotation marks in the title or
        subtitle.
        Optional direction: {data.get("image_text_direction", "")}
        """


def build_brand_visual_identity_prompt(business_name, niche):
    return f"""
        Analyze the brand images below and extract a visual identity that can
        guide future social media artwork.

        Business: {business_name}
        Niche: {niche}

        Study recurring color palettes, composition, backgrounds, photography
        or illustration style, text density, shapes, borders, hierarchy, and
        overall mood.

        Rules:
        - Respond in natural American English and return colors as hex codes.
        - visual_identity_prompt must be a practical instruction for creating
          advertising images that remain coherent with the brand.
        - Use brand colors as accents or localized areas, never as a filter,
          tint, gradient, or translucent overlay across the whole image.
        - Do not copy specific post text or recommend headlines in the image.
        """


def build_image_generation_prompt(prompt, image_format="square"):
    label = IMAGE_FORMAT_LABELS.get(image_format, IMAGE_FORMAT_LABELS["square"])
    return f"""
        Create a professional social media advertising image {label} based on
        the visual direction below.

        Visual direction:
        {prompt}

        Visual priorities:
        - Follow the theme, subtopic, and concrete details faithfully.
        - Create a specific scene rather than generic stock imagery.
        - Define a clear subject, setting, action, focal object, composition,
          and mood.
        - Avoid the default formula of a front-facing portrait, smiling person,
          neutral background, and generic graphics unless explicitly requested.
        - Favor theme-specific objects, context, materials, gestures, texture,
          light, perspective, and real usage situations.
        - Vary among close-ups, medium shots, wide scenes, overhead views, hand
          details, environments in use, behind-the-scenes, and object layouts.

        Mandatory rules:
        - Do not add a headline, title, main slogan, or large callout.
        - If natural scene text is necessary, use only short English words. Do
          not write in Portuguese.
        - Do not add overlaid promotional copy.
        - Use brand colors as accents, never as a global filter or overlay.
        - Preserve natural texture, light, contrast, and color.
        - Leave clean space in the center for text added by the backend.
        - Favor a modern, professional composition appropriate for the business.
        """


def build_user_image_edit_prompt(prompt, brand_visual_identity=""):
    brand_visual_identity_block = _format_brand_visual_identity_block(
        brand_visual_identity
    )

    return f"""
        Edit the user-provided image in conservative mode for a social media
        post. This is a localized retouching task, not an image recreation task.

        User request:
        {prompt}
        {brand_visual_identity_block}

        Mandatory instructions:
        - Preserve the main content of the uploaded image with high fidelity.
        - Do not recreate the photo from scratch, do not replace the main
          subject, and do not turn the image into a new scene.
        - If there is a person, preserve identity, face, apparent age, skin
          tone, body, pose, expression, and hair. Do not turn the
          person into another person.
        - If there is a product, environment, main object, logo, or essential
          text, preserve its shape, position, and information.
        - Change only the background, lighting, contrast, color, sharpness,
          exposure, shadows, visual finish, or peripheral elements that are not
          the main subject.
        - Do not edit the face, hair, body, hands, product, or main
          object, even if the user's request is broad.
        - Use the visual identity only as a subtle reference for mood, finish,
          color temperature, and background accents.
        - Do not add new objects around the main subject unless the request
          clearly mentions background elements.
        - Do not add a title, headline, slogan, or promotional copy.
        - Keep the result natural, professional, and suitable for advertising.
        - If the user's request requires changing the main subject, ignore that
          part and preserve the original image.
        """


def build_user_background_replace_prompt(
    prompt,
    idea,
    image_prompt,
    brand_visual_identity="",
):
    brand_visual_identity_block = _format_brand_visual_identity_block(
        brand_visual_identity
    )

    return f"""
        Create a new background for the user-provided image while keeping the
        original main subject ready to be composited on top afterward.

        User's mandatory background request:
        {prompt}

        Light context for this post:
        - Idea title: {idea.get("title", "")}
        - Specific theme: {idea.get("theme", "")}
        - Specific objective: {idea.get("objective", "")}
        - Editorial format: {idea.get("format", "")}
        - Creative angle: {idea.get("angle", "")}
        {brand_visual_identity_block}

        Background instructions:
        - The user's mandatory background request is the primary source of
          truth. Follow the requested background type, setting, elements,
          colors, and objects faithfully.
        - Do not replace the requested background with another environment,
          concept, visual metaphor, editorial scene, or campaign idea.
        - Use the light post context only to tune mood, lighting, framing,
          sophistication, and small supporting details.
        - If the post context conflicts with the user's request, ignore the
          context and preserve the exact background the user requested.
        - When there are multiple posts, vary only within the same requested
          background: light, perspective, depth of field, element arrangement,
          distance, texture, and clean space for the subject.
        - Generate only the setting/background, without people, faces, bodies,
          hands, the main product, logos, text, or promotional copy.
        - Use brand colors only as subtle accents in the environment.
        - Leave natural space for the original subject to sit in the foreground.
        - Avoid generic backdrops, but do not abandon the requested background.
        """


def build_user_merge_images_prompt(prompt):
    return f"""
        {prompt}

        Mandatory instructions:
        - Use the first image as the main base for the edit.
        - Use the second image only as a reference to satisfy the user's
          request.
        - If a third image is provided, treat it as the highest-priority
          preservation reference for the face, body shape, pose, hair, product,
          object, or detail that must stay as exact as possible.
        - If there is a person in the main image, preserve the face, identity,
          body shape, pose, proportions, hair, skin tone, and expression with
          high fidelity.
        - If there is an object, product, setting, outfit, or accessory in the
          main image, preserve its shape, position, proportions, texture, and
          essential information unless the user's request clearly asks to
          change it.
        - Apply only the references from the second image that are relevant to
          the user's request.
        - Do not add promotional text, logos, captions, or slogans.
        """
