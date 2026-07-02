# Agente de Conteúdo - Regras de Negócio

## Brand - Marca

### Criação de Marca

- Todos os usuários autenticados podem criar uma marca

# Free
- Sem captura de identidade visual
- Gere até 3 posts com imagens criadas pela IA por mês
- Gere até 3 posts com imagens editadas pela IA por mês
- Gere até 5 posts com imagens próprias por mês
- Pode criar apenas 1 post por vez

# Plus
- Com captura de identidade visual para 1 marca
- Gere até 15 posts com imagens criadas pela IA por mês
- Gere até 15 posts com imagens editadas pela IA por mês
- Gere até 30 posts com imagens próprias por mês
- Pode criar vários post por vez

# Pro
- Com captura de identidade visual para 3 marcas
- Gere até 30 posts com imagens criadas pela IA por mês
- Gere até 30 posts com imagens editadas pela IA por mês
- Gere até 30 posts com imagens próprias por mês
- Pode criar vários post por vez


Talvez, futuramente, limitar a quantidade de vezes que o usuário captura identidade visual.

## Firebase

## Rotinas de limpeza:

- Apenas 1 logo por marca deve ficar salva no Firebase.
- Apenas 2 imagens de referência da identidade visual por marca devem ficar salvas do Firebase.
- Imagem base do post: mantém salvo apenas os posts do intervalo: de 30 dias atrás até 30 dias na frente. (data de hoje como referência)
- Imagem/post final: mantém salvo apenas os posts do intervalo: de 30 dias atrás até 30 dias na frente. (data de hoje como referência). E se usuário editar a imagem/post final, essa deve ser substituida no firebase, não será mantido histórico de edição de post.
- Manter caption/dados no bancopara ter histórico textual.

- Vercel Cron chama endpoint de limpeza 1x por semana. Se tiver muitos usuários, chamar 1x por dia.


# Processo de criação de posts

Vercel recebe a request do usuário e responde rápido.
QStash publica o job.
QStash chama o worker no Cloud Run
