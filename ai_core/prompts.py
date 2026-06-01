def build_post_plan_prompt(data):
    quantity = data["quantity"]

    return f"""
        Crie um calendario editorial com exatamente {quantity} ideias distintas
        para posts de rede social com base nas informacoes abaixo.

        Negocio: {data["business_name"]}
        Nicho: {data["niche"]}
        Objetivo geral: {data["objective"]}
        Tom de voz: {data["tone"]}
        Tema/campanha principal: {data["theme"]}

        Regras:
        - Responda em portugues do Brasil.
        - As ideias nao podem ser repetidas nem variacoes obvias da mesma ideia.
        - Distribua os posts entre educacao, autoridade, prova social,
          engajamento, objecoes, oferta e relacionamento.
        - Cada ideia deve ter um angulo criativo proprio.
        - O campo visual_direction deve orientar uma imagem publicitaria
          coerente com aquela ideia.
        - Retorne exatamente {quantity} itens em posts.
        """


def build_post_from_idea_prompt(data, idea, index, total):
    image_text_direction = data.get("image_text_direction", "")

    return f"""
        Transforme a ideia editorial abaixo em um post pronto para publicacao.

        Negocio: {data["business_name"]}
        Nicho: {data["niche"]}
        Objetivo geral: {data["objective"]}
        Tom de voz: {data["tone"]}
        Campanha principal: {data["theme"]}

        Post {index} de {total}
        Titulo da ideia: {idea["title"]}
        Tema especifico: {idea["theme"]}
        Objetivo especifico: {idea["objective"]}
        Formato editorial: {idea["format"]}
        Angulo criativo: {idea["angle"]}
        Direcao visual: {idea["visual_direction"]}

        Gere:
        - uma legenda pronta para publicacao;
        - uma lista de hashtags relevantes;
        - um prompt visual para geracao de imagem;
        - um texto curto para aparecer sobre a imagem.

        Regras:
        - Responda em portugues do Brasil.
        - A legenda deve ser clara, atrativa e alinhada ao objetivo.
        - Evite repetir chamadas, frases e estruturas comuns de outros posts.
        - As hashtags devem comecar com #.
        - O prompt visual deve descrever a imagem de forma objetiva.
        - O image_text deve ter no maximo 6 palavras.
        - O image_text deve ter tom de anuncio.
        - O image_text deve usar modo imperativo quando fizer sentido.
        - O image_text nao deve ter hashtags, emojis nem aspas.

        Direcao opcional de texto para imagem: {image_text_direction}
        """


def build_posts_from_plan_prompt(data, ideas):
    quantity = data["quantity"]
    image_text_direction = data.get("image_text_direction", "")
    idea_lines = []

    for index, idea in enumerate(ideas, start=1):
        idea_lines.append(
            "\n".join(
                [
                    f"Post {index}",
                    f"Titulo: {idea['title']}",
                    f"Tema: {idea['theme']}",
                    f"Objetivo: {idea['objective']}",
                    f"Formato: {idea['format']}",
                    f"Angulo: {idea['angle']}",
                    f"Direcao visual: {idea['visual_direction']}",
                ]
            )
        )

    plan_text = "\n\n".join(idea_lines)

    return f"""
        Transforme o plano editorial abaixo em exatamente {quantity} posts
        prontos para publicacao.

        Negocio: {data["business_name"]}
        Nicho: {data["niche"]}
        Objetivo geral: {data["objective"]}
        Tom de voz: {data["tone"]}
        Campanha principal: {data["theme"]}

        Plano editorial:
        {plan_text}

        Para cada item, gere:
        - order correspondente ao numero do post;
        - uma legenda pronta para publicacao;
        - uma lista de hashtags relevantes;
        - um prompt visual para geracao de imagem;
        - um texto curto para aparecer sobre a imagem.

        Regras:
        - Responda em portugues do Brasil.
        - Retorne exatamente {quantity} itens em posts.
        - Mantenha a ordem do plano editorial.
        - Cada legenda deve ter estrutura e chamada diferentes.
        - As hashtags devem comecar com #.
        - O prompt visual deve descrever a imagem de forma objetiva.
        - O image_text deve ter no maximo 6 palavras.
        - O image_text deve ter tom de anuncio.
        - O image_text deve usar modo imperativo quando fizer sentido.
        - O image_text nao deve ter hashtags, emojis nem aspas.

        Direcao opcional de texto para imagem: {image_text_direction}
        """


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
