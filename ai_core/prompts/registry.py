from . import en_us, pt_br


PROMPT_SETS = {
    "pt-BR": pt_br,
    "en-US": en_us,
}


def get_prompt_set(content_language="pt-BR"):
    return PROMPT_SETS.get(content_language, pt_br)
