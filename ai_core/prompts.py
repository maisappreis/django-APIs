def build_post_plan_prompt(data):
    quantity = data["quantity"]
    brand_visual_identity = data.get("brand_visual_identity", "")

    return f"""
        Crie um calendario editorial com exatamente {quantity} ideias distintas
        para posts de rede social com base nas informacoes abaixo.

        Negocio: {data["business_name"]}
        Nicho: {data["niche"]}
        Objetivo geral: {data["objective"]}
        Tom de voz: {data["tone"]}
        Tema/campanha principal: {data["theme"]}
        Identidade visual da marca: {brand_visual_identity}

        Prioridade estrategica:
        - O tema/campanha principal deve guiar todos os posts.
        - Cada ideia deve explorar um subtema diretamente conectado ao tema
          principal, evitando ideias genericas que serviriam para qualquer
          campanha.
        - Se o tema mencionar uma data, oferta, dor, produto, servico, rotina,
          evento ou transformacao, isso deve aparecer claramente no objetivo,
          angulo e direcao visual de cada post.

        Regras:
        - Responda em portugues do Brasil.
        - As ideias nao podem ser repetidas nem variacoes obvias da mesma ideia.
        - Distribua os posts entre educacao, autoridade, prova social,
          engajamento, objecoes, oferta e relacionamento.
        - Cada ideia deve ter um angulo criativo proprio.
        - O campo visual_direction deve orientar uma imagem publicitaria
          coerente com aquela ideia.
        - Cada visual_direction deve ser substancialmente diferente dos demais
          em cena, sujeito principal, composicao, distancia da camera, ambiente,
          objetos de apoio e energia visual.
        - Nao repita a mesma formula visual em posts diferentes, como sempre
          "pessoa sorrindo olhando para camera" ou sempre "produto em fundo
          limpo".
        - Varie entre tipos de imagem quando fizer sentido: pessoa em acao,
          detalhe de produto/servico, bastidor, ambiente, objeto simbolico,
          antes/depois conceitual, cena de uso, composicao still life,
          perspectiva de cliente, processo ou resultado.
        - Quando houver identidade visual da marca, use essa identidade como
          referencia principal para cores, composicao, estilo e clima visual.
        - Cores da marca devem aparecer como acentos, elementos graficos ou
          composicao; nao use como filtro/overlay translucido em toda imagem.
        - Retorne exatamente {quantity} itens em posts.
        """


def build_post_from_idea_prompt(data, idea, index, total):
    image_text_direction = data.get("image_text_direction", "")
    brand_visual_identity = data.get("brand_visual_identity", "")

    return f"""
        Transforme a ideia editorial abaixo em um post pronto para publicacao.

        Negocio: {data["business_name"]}
        Nicho: {data["niche"]}
        Objetivo geral: {data["objective"]}
        Tom de voz: {data["tone"]}
        Campanha principal: {data["theme"]}
        Identidade visual da marca: {brand_visual_identity}

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
        - Quando houver identidade visual da marca, o prompt visual deve
          preservar cores, composicao, estilo e clima visual dessa identidade.
        - O prompt visual deve usar cores da marca como acentos, elementos
          graficos ou composicao, sem pedir filtro, pelicula ou overlay
          translucido cobrindo toda a imagem.
        - O prompt visual deve pedir imagem publicitaria sem titulo, cabecalho,
          manchete ou texto principal dentro da arte.
        - O prompt visual pode permitir palavras curtas em portugues somente
          quando forem parte natural do desenho, como etiquetas, placas, etapas
          de processo ou elementos de interface.
        - O prompt visual nao deve pedir frases em ingles.
        - O prompt visual nao deve incluir o image_text como texto dentro da
          imagem, pois esse texto sera aplicado pelo backend depois.
        - O image_text deve ter no maximo 6 palavras.
        - O image_text deve ter tom de anuncio.
        - O image_text deve usar modo imperativo quando fizer sentido.
        - O image_text nao deve ter hashtags, emojis nem aspas.

        Direcao opcional de texto para imagem: {image_text_direction}
        """


def build_posts_from_plan_prompt(data, ideas):
    quantity = data["quantity"]
    image_text_direction = data.get("image_text_direction", "")
    brand_visual_identity = data.get("brand_visual_identity", "")
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
        Identidade visual da marca: {brand_visual_identity}

        Plano editorial:
        {plan_text}

        Prioridade estrategica:
        - O tema/campanha principal deve ter peso alto no resultado final.
        - Cada post deve parecer parte da mesma campanha, mas com cena,
          composicao e abordagem visual diferentes.
        - Nao produza prompts visuais intercambiaveis entre os posts.
        - O prompt visual de cada post deve deixar claro o subtema especifico,
          o sujeito principal da imagem, o ambiente, a acao, o enquadramento,
          os objetos de apoio e o clima visual.

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
        - O prompt visual deve descrever a imagem de forma objetiva e especifica.
        - O prompt visual deve ser diferente dos demais em composicao,
          enquadramento, ambiente, objeto principal, gesto/acao e atmosfera.
        - Evite repetir estilo, pose, fundo, enquadramento ou estrutura visual
          entre posts.
        - Inclua no prompt visual detalhes concretos do tema/campanha principal
          e do angulo daquele post.
        - Quando houver identidade visual da marca, o prompt visual deve
          preservar cores, composicao, estilo e clima visual dessa identidade.
        - O prompt visual deve usar cores da marca como acentos, elementos
          graficos ou composicao, sem pedir filtro, pelicula ou overlay
          translucido cobrindo toda a imagem.
        - O prompt visual deve pedir imagem publicitaria sem titulo, cabecalho,
          manchete ou texto principal dentro da arte.
        - O prompt visual pode permitir palavras curtas em portugues somente
          quando forem parte natural do desenho, como etiquetas, placas, etapas
          de processo ou elementos de interface.
        - O prompt visual nao deve pedir frases em ingles.
        - O prompt visual nao deve incluir o image_text como texto dentro da
          imagem, pois esse texto sera aplicado pelo backend depois.
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
