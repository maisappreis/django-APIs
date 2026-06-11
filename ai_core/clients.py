import json
import base64
import mimetypes

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from openai import OpenAI
from pathlib import Path
from shutil import copyfile
from uuid import uuid4


IMAGE_FORMATS = {
    "square": {
        "size": "1024x1024",
        "prompt_label": "quadrada",
    },
    "portrait": {
        "size": "1024x1536",
        "prompt_label": "vertical em formato retrato",
    },
    "landscape": {
        "size": "1536x1024",
        "prompt_label": "horizontal em formato paisagem",
    },
}


POST_CONTENT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "caption": {
            "type": "string",
            "description": "Legenda pronta para um post de rede social.",
        },
        "hashtags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Lista de hashtags relevantes, começando com #.",
        },
        "image_prompt": {
            "type": "string",
            "description": "Prompt visual para futura geração de imagem.",
        },
        "image_title": {
            "type": "string",
            "description": "Titulo curto para aparecer em destaque sobre a imagem.",
        },
        "image_subtitle": {
            "type": "string",
            "description": "Subtitulo curto para aparecer abaixo do titulo.",
        },
    },
    "required": [
        "caption",
        "hashtags",
        "image_prompt",
        "image_title",
        "image_subtitle",
    ],
}


POST_IDEA_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {
            "type": "string",
            "description": "Titulo curto da ideia do post.",
        },
        "theme": {
            "type": "string",
            "description": "Tema especifico do post.",
        },
        "objective": {
            "type": "string",
            "description": "Objetivo especifico do post.",
        },
        "format": {
            "type": "string",
            "description": "Formato editorial sugerido para o post.",
        },
        "angle": {
            "type": "string",
            "description": "Angulo criativo que diferencia este post dos demais.",
        },
        "visual_direction": {
            "type": "string",
            "description": "Direcao visual para a arte do post.",
        },
    },
    "required": [
        "title",
        "theme",
        "objective",
        "format",
        "angle",
        "visual_direction",
    ],
}


POST_PLAN_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "strategy_summary": {
            "type": "string",
            "description": "Resumo curto da estrategia editorial.",
        },
        "posts": {
            "type": "array",
            "items": POST_IDEA_SCHEMA,
            "description": "Ideias distintas para posts do calendario editorial.",
        },
    },
    "required": ["strategy_summary", "posts"],
}


POST_BATCH_CONTENT_ITEM_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "order": {
            "type": "integer",
            "description": "Numero sequencial do post dentro do lote.",
        },
        "caption": {
            "type": "string",
            "description": "Legenda pronta para um post de rede social.",
        },
        "hashtags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Lista de hashtags relevantes, comecando com #.",
        },
        "image_prompt": {
            "type": "string",
            "description": "Prompt visual para futura geracao de imagem.",
        },
        "image_title": {
            "type": "string",
            "description": "Titulo curto para aparecer em destaque sobre a imagem.",
        },
        "image_subtitle": {
            "type": "string",
            "description": "Subtitulo curto para aparecer abaixo do titulo.",
        },
    },
    "required": [
        "order",
        "caption",
        "hashtags",
        "image_prompt",
        "image_title",
        "image_subtitle",
    ],
}


POST_BATCH_CONTENT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "posts": {
            "type": "array",
            "items": POST_BATCH_CONTENT_ITEM_SCHEMA,
            "description": "Conteudos finais para todos os posts do lote.",
        },
    },
    "required": ["posts"],
}


BRAND_VISUAL_IDENTITY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "visual_identity_summary": {
            "type": "string",
            "description": "Resumo curto da identidade visual observada.",
        },
        "visual_identity_prompt": {
            "type": "string",
            "description": (
                "Instrucao visual reutilizavel para prompts de imagem."
            ),
        },
        "primary_color": {
            "type": "string",
            "description": "Cor principal em hexadecimal.",
        },
        "secondary_color": {
            "type": "string",
            "description": "Cor secundaria em hexadecimal.",
        },
        "tertiary_color": {
            "type": "string",
            "description": "Cor de apoio em hexadecimal.",
        },
        "text_color": {
            "type": "string",
            "description": "Cor recomendada para texto em hexadecimal.",
        },
        "title_font": {
            "type": "string",
            "description": "Fonte sugerida para titulos.",
        },
        "subtitle_font": {
            "type": "string",
            "description": "Fonte sugerida para subtitulos.",
        },
    },
    "required": [
        "visual_identity_summary",
        "visual_identity_prompt",
        "primary_color",
        "secondary_color",
        "tertiary_color",
        "text_color",
        "title_font",
        "subtitle_font",
    ],
}


def get_openai_client():
    api_key = getattr(settings, "OPENAI_API_KEY", None)

    if not api_key:
        raise ImproperlyConfigured("OPENAI_API_KEY is not configured.")

    return OpenAI(api_key=api_key)


def generate_structured_content(
    prompt,
    schema=POST_CONTENT_SCHEMA,
    schema_name="post_content",
):
    client = get_openai_client()

    response = client.responses.create(
        model=settings.OPENAI_MODEL,
        input=[
            {
                "role": "system",
                "content": (
                    "Você é um especialista em marketing de conteúdo para redes sociais. "
                    "Responda sempre em português do Brasil."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "strict": True,
                "schema": schema,
            }
        },
    )

    return json.loads(response.output_text)


def _build_image_data_url(image_path):
    mime_type = mimetypes.guess_type(str(image_path))[0] or "image/png"
    with open(image_path, "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    return f"data:{mime_type};base64,{image_base64}"


def generate_brand_visual_identity(business_name, niche, image_paths):
    client = get_openai_client()
    content = [
        {
            "type": "input_text",
            "text": f"""
                Analise os prints do Instagram da marca abaixo e extraia a
                identidade visual para guiar futuras artes de posts.

                Negocio: {business_name}
                Nicho: {niche}

                Foque em padroes visuais recorrentes: paleta de cores,
                composicao, fundos, estilo de fotos ou ilustracoes, densidade
                de texto, formas, bordas, hierarquia visual e clima geral.

                Regras:
                - Responda em portugues do Brasil.
                - Retorne cores em hexadecimal.
                - O visual_identity_prompt deve ser uma instrucao pratica para
                  geracao de imagens publicitarias coerentes com a marca.
                - Use as cores da marca como acentos, elementos graficos,
                  fundos pontuais, detalhes de layout ou areas de composicao.
                - Nao transforme a cor principal em uma camada, filtro,
                  gradiente ou overlay translucido cobrindo toda a imagem.
                - Nao sugira aplicar uma pelicula colorida uniforme sobre
                  fotos, pessoas, produtos ou cenarios.
                - Nao copie textos especificos dos posts.
                - Nao recomende titulo ou manchete dentro da imagem; o backend
                  aplica o texto principal depois.
                """,
        }
    ]

    for image_path in image_paths:
        content.append(
            {
                "type": "input_image",
                "image_url": _build_image_data_url(image_path),
            }
        )

    response = client.responses.create(
        model=settings.OPENAI_MODEL,
        input=[
            {
                "role": "system",
                "content": (
                    "Voce e um diretor de arte especializado em identidade "
                    "visual para redes sociais."
                ),
            },
            {
                "role": "user",
                "content": content,
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "brand_visual_identity",
                "strict": True,
                "schema": BRAND_VISUAL_IDENTITY_SCHEMA,
            }
        },
    )

    return json.loads(response.output_text)


def _build_generated_image_data(relative_path):
    absolute_path = Path(settings.MEDIA_ROOT) / relative_path
    normalized_path = str(relative_path).replace("\\", "/")

    return {
        "image_path": normalized_path,
        "absolute_path": str(absolute_path),
        "image_url": f"{settings.MEDIA_URL}{normalized_path}",
    }


def _get_image_format_config(image_format):
    return IMAGE_FORMATS.get(image_format, IMAGE_FORMATS["square"])


def _generate_image_bytes(prompt, image_format="square"):
    client = get_openai_client()
    format_config = _get_image_format_config(image_format)
    image_prompt = _build_image_generation_prompt(
        prompt,
        image_format=image_format,
    )

    response = client.images.generate(
        model=settings.OPENAI_IMAGE_MODEL,
        prompt=image_prompt,
        size=format_config["size"],
        quality="medium",
        output_format="png",
    )

    image_base64 = response.data[0].b64_json
    return base64.b64decode(image_base64)


def _build_image_generation_prompt(prompt, image_format="square"):
    format_config = _get_image_format_config(image_format)

    return f"""
        Gere uma imagem publicitaria {format_config["prompt_label"]} para rede
        social a partir da direcao visual abaixo.

        Direcao visual:
        {prompt}

        Prioridade visual:
        - Siga com alta fidelidade o tema, o subtema e os detalhes concretos
          descritos na direcao visual.
        - Crie uma cena especifica, nao uma imagem generica de banco de imagens.
        - A imagem deve ter sujeito principal claro, ambiente definido, acao ou
          objeto focal, composicao intencional e clima visual coerente com o
          objetivo do post.
        - Evite repetir a formula visual padrao de retrato frontal, pessoa
          sorrindo, fundo neutro e elementos graficos genericos, a menos que a
          direcao visual peca isso explicitamente.
        - Prefira detalhes visuais relevantes ao tema: objetos, contexto,
          materiais, gestos, textura, luz, perspectiva e situacao de uso.
        - Use variedade de enquadramento quando a direcao permitir: close-up,
          plano medio, cena ampla, perspectiva superior, detalhe de maos,
          ambiente em uso, bastidor ou composicao de objetos.

        Regras obrigatorias:
        - Nao coloque titulo, cabecalho, manchete, slogan principal ou chamada
          grande dentro da imagem.
        - Nao escreva texto em ingles.
        - Se houver texto na cena, use apenas palavras curtas em portugues do
          Brasil e somente como parte natural do desenho, por exemplo etiquetas,
          placas, botoes, etapas de processo, quadros ou elementos de interface.
        - Nao inclua texto promocional sobreposto; o backend aplicara o texto
          principal depois.
        - Use cores da marca como acentos, blocos, detalhes, objetos, fundos
          parciais ou elementos graficos; nao aplique uma camada colorida
          translucida, filtro uniforme, overlay ou pelicula sobre toda a imagem.
        - Preserve textura, luz, contraste e cores naturais de fotos, pessoas,
          produtos e ambientes quando esses elementos aparecerem.
        - Reserve espaco visual limpo no centro para receber texto aplicado
          posteriormente.
        - Priorize composicao profissional, moderna e coerente com o negocio.
        """


def generate_image_file(prompt, image_format="square"):
    image_bytes = _generate_image_bytes(prompt, image_format=image_format)
    relative_path = Path("generated_posts") / f"{uuid4()}.png"
    image_data = _build_generated_image_data(relative_path)
    absolute_path = Path(image_data["absolute_path"])
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_bytes(image_bytes)

    return image_data


def generate_image_files(prompt, image_format="square"):
    image_bytes = _generate_image_bytes(prompt, image_format=image_format)

    image_id = uuid4()
    base_relative_path = Path("generated_posts") / f"base-{image_id}.png"
    final_relative_path = Path("generated_posts") / f"final-{image_id}.png"
    base_data = _build_generated_image_data(base_relative_path)
    final_data = _build_generated_image_data(final_relative_path)
    base_absolute_path = Path(base_data["absolute_path"])
    final_absolute_path = Path(final_data["absolute_path"])

    base_absolute_path.parent.mkdir(parents=True, exist_ok=True)
    base_absolute_path.write_bytes(image_bytes)
    copyfile(base_absolute_path, final_absolute_path)

    return {
        "base": base_data,
        "final": final_data,
    }
