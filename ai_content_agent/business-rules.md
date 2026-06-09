# Agente de Conteúdo - Regras de Negócio

## Brand - Marca

### Criação de Marca

- Todos os usuários autenticados podem criar uma marca

# Free
- Pode ter apenas 1 marca
- Não possui direito a Identidade Visual capturada pela IA
- Pode criar apenas 1 post por vez
- Pode gerar apenas 2 imagens com IA para os posts por mês

# Plus
- Pode ter apenas 1 marca
- Possui direito a Identidade Visual capturada pela IA
- Pode criar vários post por vez
- Pode gerar 30 imagens com IA para os posts por mês

# Pro
- Pode ter apenas 3 marcas ou 3
- Possui direito a Identidade Visual capturada pela IA
- Pode criar vários post por vez
- Pode gerar 50 imagens com IA para os posts por mês

Talvez, futuramente, limitar a quantidade de vezes que o usuário captura identidade visual.

## Firebase

## Rotinas de limpeza:

- Apenas 1 logo por marca deve ficar salva no Firebase.
- Apenas 2 imagens de referência da identidade visual por marca devem ficar salvas do Firebase.
- Imagem base do post: mantém salvo apenas os posts do intervalo: de 7 dias atrás até 30 dias na frente. (data de hoje como referência)
- Imagem/post final: mantém salvo apenas os posts do intervalo: de 7 dias atrás até 30 dias na frente. (data de hoje como referência). E se usuário editar a imagem/post final, essa deve ser substituida no firebase, não será mantido histórico de edição de post.
- Manter caption/dados no bancopara ter histórico textual.
