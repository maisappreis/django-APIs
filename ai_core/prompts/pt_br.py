CONTENT_SYSTEM_PROMPT = (
    "Você é um especialista em marketing de conteúdo para redes sociais. "
    "Responda sempre em português do Brasil."
)

VISUAL_IDENTITY_SYSTEM_PROMPT = (
    "Você é um diretor de arte especializado em identidade visual para "
    "redes sociais."
)

IMAGE_FORMAT_LABELS = {
    "square": "quadrada",
    "portrait": "vertical em formato retrato",
    "landscape": "horizontal em formato paisagem",
}


def _format_brand_visual_identity(value):
    value = (value or "").strip()

    if not value:
        return ""

    return f"        Identidade visual da marca: {value}\n"


def _format_brand_visual_identity_block(value):
    value = (value or "").strip()

    if not value:
        return ""

    return f"""
        Identidade visual da marca:
        {value}
"""


def build_post_plan_prompt(data):
    quantity = data["quantity"]
    brand_visual_identity = _format_brand_visual_identity(
        data.get("brand_visual_identity", "")
    )

    return f"""
        Crie um calendário editorial com exatamente {quantity} ideias distintas
        para posts de rede social com base nas informações abaixo.

        Negócio: {data["business_name"]}
        Nicho: {data["niche"]}
        Objetivo geral: {data["objective"]}
        Tom de voz: {data["tone"]}
        Tema/campanha principal: {data["theme"]}
        {brand_visual_identity}

        Prioridade estratégica:
        - O tema/campanha principal deve guiar todos os posts.
        - Cada ideia deve explorar um subtema diretamente conectado ao tema
          principal, evitando ideias genéricas que serviriam para qualquer
          campanha.
        - Se o tema mencionar uma data, oferta, dor, produto, serviço, rotina,
          evento ou transformação, isso deve aparecer claramente no objetivo,
          ângulo e direção visual de cada post.

        Regras:
        - Responda em português do Brasil.
        - As ideias não podem ser repetidas nem variações óbvias da mesma ideia.
        - Distribua os posts entre educação, autoridade, prova social,
          engajamento, objeções, oferta e relacionamento.
        - Cada ideia deve ter um ângulo criativo próprio.
        - O campo visual_direction deve orientar uma imagem publicitária
          coerente com aquela ideia.
        - Cada visual_direction deve ser substancialmente diferente dos demais
          em cena, sujeito principal, composição, distância da câmera, ambiente,
          objetos de apoio e energia visual.
        - Não repita a mesma fórmula visual em posts diferentes, como sempre
          "pessoa sorrindo olhando para câmera" ou "produto em fundo limpo".
        - Varie entre pessoa em ação, detalhe de produto ou serviço, bastidor,
          ambiente, objeto simbólico, antes/depois conceitual, cena de uso,
          composição still life, perspectiva de cliente, processo ou resultado.
        - Quando houver identidade visual da marca, use-a como referência
          principal para cores, composição, estilo e clima visual.
        - Use cores da marca como acentos ou elementos gráficos, nunca como
          filtro ou overlay translúcido sobre toda a imagem.
        - Retorne exatamente {quantity} itens em posts.
        """


def build_post_from_idea_prompt(data, idea, index, total):
    brand_visual_identity = _format_brand_visual_identity(
        data.get("brand_visual_identity", "")
    )

    return f"""
        Transforme a ideia editorial abaixo em um post pronto para publicação.

        Negócio: {data["business_name"]}
        Nicho: {data["niche"]}
        Objetivo geral: {data["objective"]}
        Tom de voz: {data["tone"]}
        Campanha principal: {data["theme"]}
        {brand_visual_identity}

        Post {index} de {total}
        Título da ideia: {idea["title"]}
        Tema específico: {idea["theme"]}
        Objetivo específico: {idea["objective"]}
        Formato editorial: {idea["format"]}
        Ângulo criativo: {idea["angle"]}
        Direção visual: {idea["visual_direction"]}

        Gere uma legenda, hashtags, um prompt visual, um título curto e um
        subtítulo curto para a imagem.

        Regras:
        - Responda em português do Brasil.
        - A legenda deve ser clara, atrativa e alinhada ao objetivo.
        - Evite repetir chamadas, frases e estruturas comuns de outros posts.
        - As hashtags devem começar com #.
        - O prompt visual deve ser objetivo e preservar a identidade da marca.
        - Use cores da marca como acentos ou elementos de composição, sem
          filtros ou overlays translúcidos sobre toda a imagem.
        - Peça uma imagem publicitária sem título ou texto principal na arte.
        - Permita palavras curtas em português somente como parte natural da
          cena, como etiquetas, placas, etapas ou elementos de interface.
        - Não peça frases em inglês.
        - Não inclua image_title nem image_subtitle no prompt visual.
        - image_title deve ter no máximo 5 palavras.
        - image_subtitle deve ter no máximo 10 palavras.
        - Ambos devem estar sem hashtags, emojis ou aspas.

        Direção opcional de texto: {data.get("image_text_direction", "")}
        """


def _format_plan(ideas):
    blocks = []
    for index, idea in enumerate(ideas, start=1):
        blocks.append("\n".join([
            f"Post {index}",
            f"Título: {idea['title']}",
            f"Tema: {idea['theme']}",
            f"Objetivo: {idea['objective']}",
            f"Formato: {idea['format']}",
            f"Ângulo: {idea['angle']}",
            f"Direção visual: {idea['visual_direction']}",
        ]))
    return "\n\n".join(blocks)


def build_posts_from_plan_prompt(data, ideas):
    quantity = data["quantity"]
    brand_visual_identity = _format_brand_visual_identity(
        data.get("brand_visual_identity", "")
    )

    return f"""
        Transforme o plano editorial abaixo em exatamente {quantity} posts
        prontos para publicação.

        Negócio: {data["business_name"]}
        Nicho: {data["niche"]}
        Objetivo geral: {data["objective"]}
        Tom de voz: {data["tone"]}
        Campanha principal: {data["theme"]}
        {brand_visual_identity}

        Plano editorial:
        {_format_plan(ideas)}

        Prioridade estratégica:
        - Dê peso alto ao tema principal.
        - Mantenha a campanha coesa, com cenas e abordagens diferentes.
        - Não produza prompts visuais intercambiáveis entre os posts.
        - Especifique o subtema, o sujeito principal da imagem, o ambiente, a
          ação, o enquadramento, os objetos de apoio e o clima visual.

        Para cada item, gere order, legenda, hashtags, prompt visual,
        image_title e image_subtitle.

        Regras:
        - Responda em português do Brasil.
        - Retorne exatamente {quantity} itens e mantenha a ordem do plano.
        - Varie a estrutura e a chamada de cada legenda.
        - As hashtags devem começar com #.
        - Faça cada prompt visual objetivo, específico e diferente em
          composição, enquadramento, ambiente, objeto, ação e atmosfera.
        - Inclua detalhes concretos do tema e do ângulo de cada post.
        - Preserve a identidade visual e use cores da marca como acentos, sem
          filtro ou overlay translúcido sobre toda a imagem.
        - Peça imagem publicitária sem título ou texto principal na arte.
        - Permita palavras curtas em português somente como parte natural da
          cena. Não peça frases em inglês.
        - Não inclua image_title nem image_subtitle no prompt visual.
        - image_title deve ter no máximo 5 palavras e image_subtitle, 10.
        - Ambos devem estar sem hashtags, emojis ou aspas.

        Direção opcional de texto: {data.get("image_text_direction", "")}
        """


def build_post_prompt(data):
    return f"""
        Crie um post para rede social.
        Negócio: {data["business_name"]}
        Nicho: {data["niche"]}
        Objetivo: {data["objective"]}
        Tom de voz: {data["tone"]}
        Tema: {data["theme"]}

        Responda em português do Brasil com legenda, hashtags, prompt visual,
        image_title de até 5 palavras e image_subtitle de até 10 palavras.
        Não use hashtags, emojis ou aspas no título e subtítulo.
        Direção opcional: {data.get("image_text_direction", "")}
        """


def build_brand_visual_identity_prompt(business_name, niche):
    return f"""
        Analise as imagens da marca abaixo e extraia sua identidade visual para
        orientar futuras artes de redes sociais.

        Negócio: {business_name}
        Nicho: {niche}

        Observe paleta, composição, fundos, estilo de fotos ou ilustrações,
        densidade de texto, formas, bordas, hierarquia e clima geral.

        Regras:
        - Responda em português do Brasil e retorne cores em hexadecimal.
        - visual_identity_prompt deve ser uma instrução prática para imagens
          publicitárias coerentes com a marca.
        - Use cores como acentos ou áreas pontuais, nunca como filtro, película,
          gradiente ou overlay translúcido sobre toda a imagem.
        - Não copie textos específicos nem recomende manchetes na imagem.
        """


def build_image_generation_prompt(prompt, image_format="square"):
    label = IMAGE_FORMAT_LABELS.get(image_format, IMAGE_FORMAT_LABELS["square"])
    return f"""
        Gere uma imagem publicitária {label} para rede social com base na
        direção visual abaixo.

        Direção visual:
        {prompt}

        Prioridades:
        - Siga fielmente tema, subtema e detalhes concretos.
        - Crie uma cena específica, não uma imagem genérica de banco.
        - Defina sujeito, ambiente, ação, objeto focal, composição e clima.
        - Evite a fórmula visual de retrato frontal, pessoa sorrindo, fundo
          neutro e elementos gráficos genéricos, salvo quando a direção pedir.
        - Prefira objetos, contexto, materiais, gestos, textura, luz,
          perspectiva e situações de uso relevantes ao tema.
        - Varie entre close-up, plano médio, cena ampla, perspectiva superior,
          detalhe de mãos, ambiente em uso, bastidor e composição de objetos.

        Regras obrigatórias:
        - Não coloque título, manchete, slogan ou chamada grande na imagem.
        - Se houver texto natural na cena, use apenas palavras curtas em
          português do Brasil. Não escreva em inglês.
        - Não inclua texto promocional sobreposto.
        - Use cores da marca como acentos, nunca como filtro ou overlay global.
        - Preserve textura, luz, contraste e cores naturais.
        - Reserve espaço limpo no centro para o texto aplicado pelo backend.
        - Priorize composição profissional, moderna e coerente com o negócio.
        """


def build_user_image_edit_prompt(prompt, brand_visual_identity=""):
    brand_visual_identity_block = _format_brand_visual_identity_block(
        brand_visual_identity
    )

    return f"""
        Edite a imagem enviada pelo usuario em modo conservador para uso em um
        post de rede social. Esta e uma tarefa de retoque localizado, nao de
        recriacao da imagem.

        Pedido do usuario:
        {prompt}
        {brand_visual_identity_block}

        Instrucoes obrigatorias:
        - Preserve o conteudo principal da imagem enviada com alta fidelidade.
        - Nao recrie a foto do zero, nao substitua o sujeito principal e nao
          transforme a imagem em uma nova cena.
        - Se houver uma pessoa, preserve identidade, rosto, idade aparente,
          tom de pele, corpo, pose, expressao, e cabelo. Nao transforme
          a pessoa em outra pessoa.
        - Se houver produto, ambiente, objeto principal, logo ou texto
          essencial, preserve sua forma, posicao e informacao.
        - Altere somente o fundo, a iluminacao, contraste, cor, nitidez,
          exposicao, sombras, acabamento visual ou elementos perifericos que
          nao sejam o sujeito principal.
        - Nao edite rosto, cabelo, corpo, roupa, maos, produto ou objeto
          principal, mesmo que o pedido do usuario seja amplo.
        - Use a identidade visual apenas como referencia sutil de clima,
          acabamento, temperatura de cor e acentos no fundo.
        - Nao adicione objetos novos ao redor do sujeito principal, salvo se o
          pedido mencionar claramente elementos de fundo.
        - Nao adicione titulo, chamada, slogan ou texto promocional.
        - Mantenha aparencia natural, profissional e adequada para publicidade.
        - Se o pedido do usuario exigir alterar o sujeito principal, ignore
          essa parte e preserve a imagem original.
        """
