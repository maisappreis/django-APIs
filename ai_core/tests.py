from django.test import SimpleTestCase

from ai_core.clients import _build_image_generation_prompt
from ai_core.prompts import build_post_plan_prompt, build_posts_from_plan_prompt
from ai_core.prompts.registry import PROMPT_SETS, get_prompt_set


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
        self.assertIn("cena, sujeito principal, composição", prompt)

    def test_english_brand_uses_english_content_rules(self):
        data = self.get_data()
        data["content_language"] = "en-US"

        plan_prompt = build_post_plan_prompt(data)
        image_prompt = _build_image_generation_prompt(
            "A customer using the product",
            content_language="en-US",
        )

        self.assertIn("Respond in natural American English", plan_prompt)
        self.assertIn("use only short English words", image_prompt)
        self.assertIn("not write in Portuguese", image_prompt)

    def test_prompt_sets_expose_the_same_complete_interface(self):
        required_builders = {
            "build_post_plan_prompt",
            "build_post_from_idea_prompt",
            "build_posts_from_plan_prompt",
            "build_post_prompt",
            "build_brand_visual_identity_prompt",
            "build_image_generation_prompt",
        }

        for language, prompt_set in PROMPT_SETS.items():
            with self.subTest(language=language):
                for builder in required_builders:
                    self.assertTrue(callable(getattr(prompt_set, builder)))

        self.assertIs(get_prompt_set("unsupported"), PROMPT_SETS["pt-BR"])

    def test_english_prompt_has_no_portuguese_instruction_scaffold(self):
        data = {
            **self.get_data(),
            "content_language": "en-US",
            "niche": "fitness center",
            "objective": "attract new members",
            "tone": "motivational",
            "theme": "back to fitness",
            "brand_visual_identity": "modern look with green accents",
        }
        prompt = build_post_plan_prompt(data)

        for portuguese_instruction in (
            "Negócio:",
            "Objetivo geral:",
            "Regras:",
            "Responda em",
            "Retorne exatamente",
        ):
            self.assertNotIn(portuguese_instruction, prompt)

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

        self.assertIn("Não produza prompts visuais intercambiáveis", prompt)
        self.assertIn("sujeito principal da imagem", prompt)
        self.assertIn("detalhes concretos do tema", prompt)

    def test_image_generation_prompt_avoids_generic_stock_style(self):
        prompt = _build_image_generation_prompt(
            "Aluno amarrando tenis antes do treino matinal"
        )

        self.assertIn("não uma imagem genérica de banco", prompt)
        self.assertIn("Evite a fórmula visual", prompt)
        self.assertIn("situações de uso relevantes ao tema", prompt)

    def test_image_generation_prompt_can_request_portrait_format(self):
        prompt = _build_image_generation_prompt(
            "Aluno amarrando tenis antes do treino matinal",
            image_format="portrait",
        )

        self.assertIn("vertical em formato retrato", prompt)
