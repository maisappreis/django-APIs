from django.test import SimpleTestCase

from ai_core.clients import _build_image_generation_prompt
from ai_core.prompts import build_post_plan_prompt, build_posts_from_plan_prompt


class PromptQualityTestCase(SimpleTestCase):
    def get_data(self):
        return {
            "quantity": 2,
            "business_name": "UpFit Gym",
            "niche": "academia",
            "objective": "atrair alunos",
            "tone": "motivacional",
            "theme": "volta a rotina fitness",
            "brand_visual_identity": "visual moderno com verde como acento",
        }

    def test_plan_prompt_prioritizes_theme_and_visual_variety(self):
        prompt = build_post_plan_prompt(self.get_data())

        self.assertIn("tema/campanha principal deve guiar", prompt)
        self.assertIn("substancialmente diferente", prompt)
        self.assertIn("cena, sujeito principal, composicao", prompt)

    def test_batch_prompt_requires_specific_non_interchangeable_image_prompts(self):
        prompt = build_posts_from_plan_prompt(
            self.get_data(),
            [
                {
                    "title": "Post 1",
                    "theme": "Rotina",
                    "objective": "Atrair",
                    "format": "educativo",
                    "angle": "Recomeco",
                    "visual_direction": "Pessoa preparando mochila de treino",
                },
                {
                    "title": "Post 2",
                    "theme": "Treino",
                    "objective": "Converter",
                    "format": "oferta",
                    "angle": "Aula experimental",
                    "visual_direction": "Recepcao da academia com convite",
                },
            ],
        )

        self.assertIn("Nao produza prompts visuais intercambiaveis", prompt)
        self.assertIn("sujeito principal da imagem", prompt)
        self.assertIn("detalhes concretos do tema/campanha principal", prompt)

    def test_image_generation_prompt_avoids_generic_stock_style(self):
        prompt = _build_image_generation_prompt(
            "Aluno amarrando tenis antes do treino matinal"
        )

        self.assertIn("nao uma imagem generica de banco de imagens", prompt)
        self.assertIn("Evite repetir a formula visual padrao", prompt)
        self.assertIn("detalhes visuais relevantes ao tema", prompt)

    def test_image_generation_prompt_can_request_portrait_format(self):
        prompt = _build_image_generation_prompt(
            "Aluno amarrando tenis antes do treino matinal",
            image_format="portrait",
        )

        self.assertIn("vertical em formato retrato", prompt)
