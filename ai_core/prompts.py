from ai_core.clients import generate_structured_content


def build_post_prompt(data):
    return f"""
        Crie um conteúdo para post de rede social com base nas informações abaixo.

        Negócio: {data["business_name"]}
        Nicho: {data["niche"]}
        Objetivo: {data["objective"]}
        Tom de voz: {data["tone"]}
        Tema do post: {data["theme"]}

        Gere:
        - uma legenda pronta para publicação;
        - uma lista de hashtags relevantes;
        - um prompt visual para futura geração de imagem.

        Regras:
        - Responda em português do Brasil.
        - A legenda deve ser clara, atrativa e alinhada ao objetivo.
        - As hashtags devem começar com #.
        - O prompt visual deve descrever a imagem de forma objetiva.

        Texto sugerido para a imagem: {data.get("image_text_direction", "")}

        Gere também um texto curto para aparecer sobre a imagem.

        Regras do image_text:
        - máximo de 6 palavras;
        - tom de anúncio;
        - modo imperativo quando fizer sentido;
        - sem hashtags;
        - sem emojis;
        - sem aspas;
        - deve funcionar como chamada visual curta.
        """
